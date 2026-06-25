import math
import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import dist
from compiler.models import GeoDraftDocument
from compiler.operations.lines import LineByAngleOp


def assert_line_approx(line1, line2, abs_tol=1e-7):
    assert line1[0] == pytest.approx(line2[0], abs=abs_tol)
    assert line1[1] == pytest.approx(line2[1], abs=abs_tol)
    assert line1[2] == pytest.approx(line2[2], abs=abs_tol)


def test_line_by_angle_compile_sample():
    """
    Юнит-тест математического ядра LineByAngleOp.compile_sample.
    Поворачиваем ось X (y = 0, коэффициенты: 0*x + 1*y + 0 = 0)
    вокруг начала координат (0, 0) на угол 30 градусов (pi / 6 радиан) против часовой стрелки.
    Ожидаемые коэффициенты новой прямой:
    a = -sin(30) = -0.5
    b = cos(30) = sqrt(3)/2 ≈ 0.8660254
    c = 0
    """
    args = {
        "line": "L_init",
        "point": "P_center",
        "angle": {"type": "Number", "value": math.pi / 6.0},
    }
    step_func = LineByAngleOp.compile_sample(
        args=args, name="L_rotated", disambiguation=None
    )

    env = {
        "L_init": (0.0, 1.0, 0.0),  # y = 0
        "P_center": (0.0, 0.0),
    }
    step_func(env)

    expected_line = (-0.5, math.sqrt(3.0) / 2.0, 0.0)
    assert_line_approx(env["L_rotated"], expected_line)


def test_line_by_angle_to_ggb():
    """Юнит-тест генерации GGB-кода для метода LineByAngle (Rotate в GeoGebra)"""

    class MockTranslator:
        def _var_to_ggb(self, var_obj):
            return "alpha"

    translator = MockTranslator()
    args = {
        "line": "Line_AB",
        "point": "A",
        "angle": {"type": "Number", "value": 1.047},
    }
    ggb_expr = LineByAngleOp.to_ggb(args=args, name="Line_AC", translator=translator)

    assert ggb_expr == "Rotate(Line_AB, alpha, A)"


def test_problem_equilateral_triangle_by_angles():
    """
    Интеграционный тест:
    Строит правильный треугольник ABC с использованием поворотов прямых на +60 и -60 градусов.
    Проверяет равенство сторон AB = AC = BC и экспортирует чертеж в .ggb.
    """
    doc_data = {
        "problem_name": "Equilateral Triangle via Rotated Lines",
        "constraints": [
            {
                "type": "Inequality",
                "operator": ">",
                "left": {"type": "Distance", "points": ["A", "B"]},
                "right": {"type": "Number", "value": 1.5},
            }
        ],
        "construction": [
            {
                "name": "A",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [-1.5, 0.0]},
            },
            {
                "name": "B",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [1.5, 0.0]},
            },
            {
                "name": "Line_AB",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["A", "B"]},
                "hidden": True,
            },
            {
                "name": "Line_AC",
                "type": "Line",
                "method": "LineByAngle",
                "args": {
                    "line": "Line_AB",
                    "point": "A",
                    "angle": {"type": "Number", "value": math.pi / 3.0},
                },
            },
            {
                "name": "Line_BC",
                "type": "Line",
                "method": "LineByAngle",
                "args": {
                    "line": "Line_AB",
                    "point": "B",
                    "angle": {
                        "type": "Number",
                        "value": -math.pi / 3.0,
                    },
                },
            },
            {
                "name": "C",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Line_AC", "obj2": "Line_BC"},
            },
        ],
        "goals": [
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "Distance", "points": ["A", "B"]},
                        {"type": "Distance", "points": ["A", "C"]},
                    ]
                },
            },
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "Distance", "points": ["A", "B"]},
                        {"type": "Distance", "points": ["B", "C"]},
                    ]
                },
            },
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "Hide", "targets": ["Line_AC", "Line_BC"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог построить треугольник по ограничениям"

    d_ab = dist(env["A"], env["B"])
    d_ac = dist(env["A"], env["C"])
    d_bc = dist(env["B"], env["C"])

    assert d_ab == pytest.approx(d_ac, abs=1e-7), (
        f"Стороны не равны: AB={d_ab:.6f}, AC={d_ac:.6f}"
    )
    assert d_ab == pytest.approx(d_bc, abs=1e-7), (
        f"Стороны не равны: AB={d_ab:.6f}, BC={d_bc:.6f}"
    )

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0, (
        "Цели равенства не были сгенерированы в трансляторе"
    )

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "equilateral_triangle_by_angles.ggb")

    original_types = {}
    for obj in doc.construction:
        if obj.name:
            original_types[obj.name] = obj.type

    generator = GeoDraftGenerator(config=GeoDrawConfig())
    generator.create_ggb(project, original_types, output_path)

    print(
        f"\n[+] Сценарий правильного треугольника успешно сохранен: {os.path.abspath(output_path)}"
    )
    assert os.path.exists(output_path), "Файл .ggb не был сохранен"
