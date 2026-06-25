import os
from typing import Any, Dict

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.models import GeoDraftDocument
from compiler.operations.lines import LineThroughOp


def test_linethrough_compile_sample():
    """
    Юнит-тест математического ядра для LineThroughOp.compile_sample.
    Строит прямую через точки A(1, 2) и B(4, 6).
    Проверяет, что прямая нормирована (a^2 + b^2 = 1) и обе точки лежат на ней.
    """
    args = {"points": ["A", "B"]}
    step_func = LineThroughOp.compile_sample(args=args, name="L", disambiguation=None)

    env: Dict[str, Any] = {"A": (1.0, 2.0), "B": (4.0, 6.0)}
    step_func(env)

    a, b, c = env["L"]
    assert a**2 + b**2 == pytest.approx(1.0, abs=1e-7)
    assert a * 1.0 + b * 2.0 + c == pytest.approx(0.0, abs=1e-7)
    assert a * 4.0 + b * 6.0 + c == pytest.approx(0.0, abs=1e-7)


def test_linethrough_to_ggb():
    """Юнит-тест трансляции метода LineThrough в синтаксис GeoGebra"""
    args = {"points": ["A", "B"]}
    ggb_expr = LineThroughOp.to_ggb(args=args, name="L_node", disambiguation=None)

    assert ggb_expr == "Line(A, B)"


def assert_goals(doc: GeoDraftDocument, env: dict):
    """
    Проверяет математическое выполнение целей в сгенерированном окружении.
    Для цели Concurrent (пересечение трех прямых в одной точке) мы вычисляем
    определитель матрицы их коэффициентов. Если он равен 0, прямые пересекаются в одной точке.
    """
    for goal in doc.goals:
        g_type = goal.type
        args = goal.args

        if g_type == "Concurrent":
            objs = args["objects"]
            assert len(objs) == 3, "Цель Concurrent в этом тесте ожидает ровно 3 прямые"
            l1 = env[objs[0]]
            l2 = env[objs[1]]
            l3 = env[objs[2]]

            det = (
                l1[0] * (l2[1] * l3[2] - l3[1] * l2[2])
                - l1[1] * (l2[0] * l3[2] - l3[0] * l2[2])
                + l1[2] * (l2[0] * l3[1] - l3[0] * l2[1])
            )
            assert abs(det) < 1e-8, f"Цель Concurrent провалена. Определитель: {det}"


def test_problem_centroid_concurrency():
    """
    Интеграционный тест:
    Доказывает теорему о том, что три медианы треугольника пересекаются в одной точке.
    Медианы строятся через LineThrough, соединяя вершины с серединами сторон (Midpoint).
    Экспортирует результат в tests_output/centroid_concurrency.ggb.
    """
    doc_data = {
        "problem_name": "Centroid Concurrency Theorem",
        "constraints": [
            {
                "type": "Inequality",
                "operator": ">",
                "left": {
                    "type": "MathExpression",
                    "expression": "abs(x(A)*(y(B) - y(C)) + x(B)*(y(C) - y(A)) + x(C)*(y(A) - y(B)))",
                    "variables": {"A": "A", "B": "B", "C": "C"},
                },
                "right": {"type": "Number", "value": 1.0},
            }
        ],
        "construction": [
            {
                "name": "A",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [-1, 4]},
            },
            {
                "name": "B",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [-4, -1]},
            },
            {
                "name": "C",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [4, -1]},
            },
            {
                "name": "Ma",
                "type": "Point",
                "method": "Midpoint",
                "args": {"points": ["B", "C"]},
                "hidden": True,
            },
            {
                "name": "Mb",
                "type": "Point",
                "method": "Midpoint",
                "args": {"points": ["C", "A"]},
                "hidden": True,
            },
            {
                "name": "Mc",
                "type": "Point",
                "method": "Midpoint",
                "args": {"points": ["A", "B"]},
                "hidden": True,
            },
            {
                "name": "Line_AMa",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["A", "Ma"]},
            },
            {
                "name": "Line_BMb",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["B", "Mb"]},
            },
            {
                "name": "Line_CMc",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["C", "Mc"]},
            },
        ],
        "goals": [
            {
                "type": "Concurrent",
                "args": {"objects": ["Line_AMa", "Line_BMb", "Line_CMc"]},
            }
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "Clip", "target": "Line_AMa", "endpoints": ["A", "Ma"]},
            {"action": "Clip", "target": "Line_BMb", "endpoints": ["B", "Mb"]},
            {"action": "Clip", "target": "Line_CMc", "endpoints": ["C", "Mc"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать конфигурацию треугольника"

    assert_goals(doc, env)

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0, "Транслятор не сгенерировал GGB-код для целей"

    assert any(inst.ggb_type == "point" for inst in goal_instructions)

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "centroid_concurrency.ggb")

    original_types = {}
    for obj in doc.construction:
        if obj.name:
            original_types[obj.name] = obj.type

    config = GeoDrawConfig()
    config.show_axes = False
    config.show_grid = False

    generator = GeoDraftGenerator(config=config)
    generator.create_ggb(project, original_types, output_path)

    print(
        f"\n[+] Теорема о центроиде успешно сохранена: {os.path.abspath(output_path)}"
    )
    assert os.path.exists(output_path), "Файл .ggb не был создан на диске"
