import math
import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import dist
from compiler.models import GeoDraftDocument
from compiler.operations.lines import AngleBisectorOp


def assert_line_approx(line1, line2, abs_tol=1e-7):
    for coef1, coef2 in zip(line1, line2):
        if abs(coef1 - coef2) > abs_tol and abs(coef1 + coef2) > abs_tol:
            pytest.fail(f"Прямые не совпадают: {line1} != {line2}")


def test_angle_bisector_compile_sample():
    """
    Юнит-тест математического ядра для AngleBisectorOp.compile_sample.
    Возьмем прямоугольный треугольник с вершиной угла в начале координат:
    B(0, 0) - вершина угла 90 градусов.
    A(0, 3) - лежит на положительной оси Y.
    C(4, 0) - лежит на положительной оси X.
    Биссектрисой угла ABC должна быть прямая y = x (или x - y = 0).
    Нормализованный вид: (1/sqrt(2), -1/sqrt(2), 0) ≈ (0.70710678, -0.70710678, 0.0)
    """
    args = {"vertex": "B", "ends": ["A", "C"]}
    step_func = AngleBisectorOp.compile_sample(
        args=args, name="Bis_B", disambiguation=None
    )

    env = {"B": (0.0, 0.0), "A": (0.0, 3.0), "C": (4.0, 0.0)}
    step_func(env)

    val = 1.0 / math.sqrt(2.0)
    expected_line = (val, -val, 0.0)

    assert_line_approx(env["Bis_B"], expected_line)


def test_angle_bisector_to_ggb():
    """Юнит-тест трансляции метода AngleBisector в синтаксис GeoGebra"""
    args = {"vertex": "B", "ends": ["A", "C"]}
    ggb_expr = AngleBisectorOp.to_ggb(args=args, name="bis", disambiguation=None)

    assert ggb_expr == "AngleBisector(A, B, C)"


def test_problem_incenter_concurrency_and_distances():
    """
    Интеграционный тест:
    1. Доказывает, что три биссектрисы треугольника пересекаются в одной точке I.
    2. Доказывает, что расстояния от I до всех трех сторон треугольника равны (радиус вписанной окружности).
    Экспортирует чертеж в tests_output/lines_angle_bisector.ggb.
    """
    doc_data = {
        "problem_name": "Incenter Concurrency Theorem",
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
                "args": {"approx_position": [0, 4]},
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
                "args": {"approx_position": [3, -1]},
            },
            {
                "name": "Line_AB",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["A", "B"]},
                "hidden": True,
            },
            {
                "name": "Line_BC",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["B", "C"]},
                "hidden": True,
            },
            {
                "name": "Line_CA",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["C", "A"]},
                "hidden": True,
            },
            {
                "name": "Bis_A",
                "type": "Line",
                "method": "AngleBisector",
                "args": {"vertex": "A", "ends": ["B", "C"]},
                "hidden": True,
            },
            {
                "name": "Bis_B",
                "type": "Line",
                "method": "AngleBisector",
                "args": {"vertex": "B", "ends": ["A", "C"]},
                "hidden": True,
            },
            {
                "name": "Bis_C",
                "type": "Line",
                "method": "AngleBisector",
                "args": {"vertex": "C", "ends": ["A", "B"]},
                "hidden": True,
            },
            {
                "name": "I",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Bis_A", "obj2": "Bis_B"},
            },
            {
                "name": "P_AB",
                "type": "Point",
                "method": "Projection",
                "args": {"point": "I", "line": "Line_AB"},
            },
            {
                "name": "P_BC",
                "type": "Point",
                "method": "Projection",
                "args": {"point": "I", "line": "Line_BC"},
            },
            {
                "name": "P_CA",
                "type": "Point",
                "method": "Projection",
                "args": {"point": "I", "line": "Line_CA"},
            },
        ],
        "goals": [
            {"type": "Belongs", "args": {"point": "I", "object": "Bis_C"}},
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "Distance", "points": ["I", "P_AB"]},
                        {"type": "Distance", "points": ["I", "P_BC"]},
                        {"type": "Distance", "points": ["I", "P_CA"]},
                    ]
                },
            },
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "Clip", "target": "Bis_A", "endpoints": ["A", "I"]},
            {"action": "Clip", "target": "Bis_B", "endpoints": ["B", "I"]},
            {"action": "Clip", "target": "Bis_C", "endpoints": ["C", "I"]},
            {"action": "DrawSegment", "endpoints": ["I", "P_AB"]},
            {"action": "DrawSegment", "endpoints": ["I", "P_BC"]},
            {"action": "DrawSegment", "endpoints": ["I", "P_CA"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать корректную конфигурацию"

    a, b, c = env["Bis_C"]
    x_i, y_i = env["I"]
    line_eval = a * x_i + b * y_i + c
    assert abs(line_eval) < 1e-8, (
        f"Точка I не лежит на биссектрисе Bis_C. Отклонение: {line_eval:.8f}"
    )

    d_ab = dist(env["I"], env["P_AB"])
    d_bc = dist(env["I"], env["P_BC"])
    d_ca = dist(env["I"], env["P_CA"])

    assert d_ab == pytest.approx(d_bc, abs=1e-8)
    assert d_bc == pytest.approx(d_ca, abs=1e-8)

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0, "Транслятор проигнорировал цели задачи"

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "lines_angle_bisector.ggb")

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
        f"\n[+] Файл биссектрисы угла успешно сохранен: {os.path.abspath(output_path)}"
    )
    assert os.path.exists(output_path), "Файл .ggb не был сгенерирован на диске"
