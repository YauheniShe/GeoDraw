import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.models import GeoDraftDocument
from compiler.operations.points import ETCOp


def assert_point_approx(pt1, pt2, abs_tol=1e-7):
    assert pt1[0] == pytest.approx(pt2[0], abs=abs_tol)
    assert pt1[1] == pytest.approx(pt2[1], abs=abs_tol)


def assert_goals(doc: GeoDraftDocument, env: dict):
    for goal in doc.goals:
        if goal.type == "Collinear":
            pts = goal.args["points"]
            assert len(pts) >= 3, "Цель Collinear требует минимум 3 точки"
            p1, p2, p3 = env[pts[0]], env[pts[1]], env[pts[2]]
            area = (
                p1[0] * (p2[1] - p3[1])
                + p2[0] * (p3[1] - p1[1])
                + p3[0] * (p1[1] - p2[1])
            )
            assert abs(area) < 1e-8, (
                f"Цель Collinear провалена для точек {pts}. Отклонение: {area}"
            )


def test_etc_centroid_math():
    """Проверка математики: ETC(2) должен совпадать с обычным центроидом (A+B+C)/3"""
    args = {"triangle": ["A", "B", "C"], "index": 2}
    step = ETCOp.compile_sample(args, "G", disambiguation=None)

    env = {"A": (0.0, 3.0), "B": (-3.0, 0.0), "C": (3.0, 0.0)}
    step(env)
    assert_point_approx(env["G"], (0.0, 1.0))


def test_etc_ggb_translation_builtin():
    """Для индексов <= 3000 транслятор должен использовать нативную функцию GeoGebra"""
    translator = GeoDraftTranslator()
    args = {"triangle": ["A", "B", "C"], "index": 8}

    expr = ETCOp.to_ggb(args, "X8", translator=translator, sampled_state=None)
    assert expr == "TriangleCenter(A, B, C, 8)"


def test_etc_ggb_translation_custom():
    """Для индексов > 3000 транслятор должен генерировать явную алгебраическую конструкцию"""
    translator = GeoDraftTranslator()
    args = {"triangle": ["A", "B", "C"], "index": 3001}

    expr = ETCOp.to_ggb(args, "P_custom", translator=translator, sampled_state=None)
    emitted_expressions = [inst.expression for inst in translator.instructions]
    assert "Distance(B, C)" in emitted_expressions
    assert "Distance(C, A)" in emitted_expressions
    assert "Distance(A, B)" in emitted_expressions

    assert ") * A +" in expr
    assert ") * B +" in expr
    assert ") * C)" in expr
    assert " / " in expr


def test_problem_nagel_line():
    """
    Интеграционный тест: Прямая Нагеля.
    Доказывает, что Инцентр (X_1), Центроид (X_2) и Точка Нагеля (X_8)
    всегда лежат на одной прямой для любого треугольника.
    """
    doc_data = {
        "problem_name": "Nagel Line Theorem",
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
                "args": {"approx_position": [1, 4]},
            },
            {
                "name": "B",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [-3, -1]},
            },
            {
                "name": "C",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [4, -2]},
            },
            {
                "name": "X1",
                "type": "Point",
                "method": "ETC",
                "args": {"triangle": ["A", "B", "C"], "index": 1},
            },
            {
                "name": "X2",
                "type": "Point",
                "method": "ETC",
                "args": {"triangle": ["A", "B", "C"], "index": 2},
            },
            {
                "name": "X8",
                "type": "Point",
                "method": "ETC",
                "args": {"triangle": ["A", "B", "C"], "index": 8},
            },
        ],
        "goals": [{"type": "Collinear", "args": {"points": ["X1", "X2", "X8"]}}],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "DrawSegment", "endpoints": ["X1", "X8"]},
            {"action": "Show", "targets": ["X1", "X2", "X8"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)

    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать невырожденный треугольник"

    assert_goals(doc, env)
    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0, "Транслятор не сгенерировал GGB-код для целей"
    assert any(inst.ggb_type == "line" for inst in goal_instructions)

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "nagel_line.ggb")

    original_types = {obj.name: obj.type for obj in doc.construction if obj.name}

    config = GeoDrawConfig()
    config.show_axes = False
    config.show_grid = False

    generator = GeoDraftGenerator(config=config)
    generator.create_ggb(project, original_types, output_path)

    print(
        f"\n[+] Файл теоремы о Прямой Нагеля успешно сохранен: {os.path.abspath(output_path)}"
    )
    assert os.path.exists(output_path), "Файл .ggb не был создан на диске"
