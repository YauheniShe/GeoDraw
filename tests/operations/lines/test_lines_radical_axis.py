import math
import os
from typing import Any, Dict

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import dist_sq
from compiler.models import GeoDraftDocument
from compiler.operations.lines import RadicalAxisOp


def assert_line_approx(line1, line2, abs_tol=1e-7):
    """
    Вспомогательная функция для проверки близости уравнений прямых ax + by + c = 0.
    Учитывает возможное противоположное направление нормали.
    """
    assert len(line1) == 3
    assert len(line2) == 3

    n1 = math.hypot(line1[0], line1[1])
    n2 = math.hypot(line2[0], line2[1])
    l1 = (line1[0] / n1, line1[1] / n1, line1[2] / n1)
    l2 = (line2[0] / n2, line2[1] / n2, line2[2] / n2)

    sign = 1.0 if (l1[0] * l2[0] + l1[1] * l2[1]) > 0 else -1.0
    assert l1[0] == pytest.approx(sign * l2[0], abs=abs_tol)
    assert l1[1] == pytest.approx(sign * l2[1], abs=abs_tol)
    assert l1[2] == pytest.approx(sign * l2[2], abs=abs_tol)


def calculate_power_of_point(pt, circle):
    """Вычисляет степень точки pt относительно окружности circle: d^2 - R^2"""
    center, r = circle
    return dist_sq(pt, center) - (r**2)


def test_radical_axis_intersecting_circles():
    """
    Математический тест: Окружности пересекаются.
    Радикальная ось должна проходить строго через их точки пересечения.
    """
    args = {"circle1": "C1", "circle2": "C2"}
    step = RadicalAxisOp.compile_sample(args, "L", disambiguation=None)

    env = {"C1": ((0.0, 0.0), 2.0), "C2": ((2.0, 0.0), 2.0)}
    step(env)
    assert_line_approx(env["L"], (1.0, 0.0, -1.0))


def test_radical_axis_disjoint_equal_power():
    """
    Математический тест: Окружности не пересекаются (внешние).
    Для любой точки на радикальной оси степени относительно обеих окружностей должны быть равны.
    """
    args = {"circle1": "C1", "circle2": "C2"}
    step = RadicalAxisOp.compile_sample(args, "L", disambiguation=None)

    env: Dict[str, Any] = {"C1": ((-3.0, 2.0), 1.5), "C2": ((4.0, -1.0), 3.0)}
    step(env)
    a, b, c = env["L"]

    if abs(b) > 1e-5:
        test_pts = [(-2.0, (2.0 * a - c) / b), (0.0, -c / b), (3.0, (-3.0 * a - c) / b)]
    else:
        test_pts = [(-c / a, -2.0), (-c / a, 0.0), (-c / a, 3.0)]

    for pt in test_pts:
        power1 = calculate_power_of_point(pt, env["C1"])
        power2 = calculate_power_of_point(pt, env["C2"])
        assert power1 == pytest.approx(power2, abs=1e-8), (
            f"Степени точки {pt} не совпадают: {power1:.6f} != {power2:.6f}"
        )


def test_radical_axis_nested_circles():
    """
    Математический тест: Окружности вложены одна в другую, но не концентричны.
    Радикальная ось находится вне обеих окружностей, но степени точек на ней все равно равны.
    """
    args = {"circle1": "C1", "circle2": "C2"}
    step = RadicalAxisOp.compile_sample(args, "L", disambiguation=None)

    env: Dict[str, Any] = {
        "C1": ((0.0, 0.0), 5.0),
        "C2": ((1.0, 0.0), 2.0),
    }
    step(env)
    a, b, c = env["L"]

    assert_line_approx(env["L"], (1.0, 0.0, -11.0))


def test_radical_axis_concentric_raises():
    """Исключительная ситуация: Концентрические окружности должны выбрасывать ValueError"""
    args = {"circle1": "C1", "circle2": "C2"}
    step = RadicalAxisOp.compile_sample(args, "L", disambiguation=None)

    env = {
        "C1": ((1.0, -2.0), 3.0),
        "C2": ((1.0, -2.0), 1.0),
    }
    with pytest.raises(ValueError, match="Окружности концентрические"):
        step(env)


def test_radical_axis_to_ggb_translation():
    """
    Тест транслятора: Проверка корректности генерации вспомогательных сущностей в GGB.
    Должна быть сгенерирована цепочка вычислений (расстояние, радиусы, проекция T и перпендикулярная прямая).
    """
    translator = GeoDraftTranslator()
    args = {"circle1": "Circ1", "circle2": "Circ2"}

    expr = RadicalAxisOp.to_ggb(args, "RadAxis", translator)

    assert expr == "PerpendicularLine(T_RadAxis, Line(Center(Circ1), Center(Circ2)))"

    helper_names = [inst.name for inst in translator.instructions]
    assert "dist_RadAxis" in helper_names
    assert "r1_RadAxis" in helper_names
    assert "r2_RadAxis" in helper_names
    assert "x1_RadAxis" in helper_names
    assert "T_RadAxis" in helper_names

    for inst in translator.instructions:
        if inst.name != "RadAxis":
            assert inst.hidden is True


def test_problem_radical_center_concurrency():
    """
    Интеграционный (E2E) тест: Теорема о радикальном центре.
    Для трех окружностей с невырожденными центрами три радикальные оси пересекаются в одной точке (радикальном центре).
    Экспортирует результат в tests_output/radical_center.ggb.
    """
    doc_data = {
        "problem_name": "Radical Center Concurrency",
        "constraints": [
            {
                "type": "Inequality",
                "operator": ">",
                "left": {
                    "type": "MathExpression",
                    "expression": "abs(x(O1)*(y(O2) - y(O3)) + x(O2)*(y(O3) - y(O1)) + x(O3)*(y(O1) - y(O2)))",
                    "variables": {"O1": "O1", "O2": "O2", "O3": "O3"},
                },
                "right": {"type": "Number", "value": 2.0},
            }
        ],
        "construction": [
            {
                "name": "O1",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [-2, 3]},
            },
            {
                "name": "O2",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [4, 1]},
            },
            {
                "name": "O3",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [0, -3]},
            },
            {
                "name": "C1",
                "type": "Circle",
                "method": "CenterRadius",
                "args": {"center": "O1", "radius": {"type": "Number", "value": 2.5}},
            },
            {
                "name": "C2",
                "type": "Circle",
                "method": "CenterRadius",
                "args": {"center": "O2", "radius": {"type": "Number", "value": 1.8}},
            },
            {
                "name": "C3",
                "type": "Circle",
                "method": "CenterRadius",
                "args": {"center": "O3", "radius": {"type": "Number", "value": 2.2}},
            },
            {
                "name": "L12",
                "type": "Line",
                "method": "RadicalAxis",
                "args": {"circle1": "C1", "circle2": "C2"},
            },
            {
                "name": "L23",
                "type": "Line",
                "method": "RadicalAxis",
                "args": {"circle1": "C2", "circle2": "C3"},
            },
            {
                "name": "L31",
                "type": "Line",
                "method": "RadicalAxis",
                "args": {"circle1": "C3", "circle2": "C1"},
            },
            {
                "name": "RC",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "L12", "obj2": "L23"},
            },
        ],
        "goals": [{"type": "Concurrent", "args": {"objects": ["L12", "L23", "L31"]}}],
        "view": [
            {"action": "Show", "targets": ["C1", "C2", "C3"]},
            {"action": "Show", "targets": ["L12", "L23", "L31"]},
            {"action": "DrawSegment", "endpoints": ["O1", "O2"]},
            {"action": "DrawSegment", "endpoints": ["O2", "O3"]},
            {"action": "DrawSegment", "endpoints": ["O3", "O1"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать невырожденную конфигурацию окружностей"

    rc_pt = env["RC"]
    a31, b31, c31 = env["L31"]
    dist_to_l31 = abs(a31 * rc_pt[0] + b31 * rc_pt[1] + c31) / math.hypot(a31, b31)
    assert dist_to_l31 == pytest.approx(0.0, abs=1e-8), (
        f"Радикальный центр не лежит на третьей оси. Отклонение: {dist_to_l31:.6f}"
    )

    power1 = calculate_power_of_point(rc_pt, env["C1"])
    power2 = calculate_power_of_point(rc_pt, env["C2"])
    power3 = calculate_power_of_point(rc_pt, env["C3"])

    assert power1 == pytest.approx(power2, abs=1e-8)
    assert power2 == pytest.approx(power3, abs=1e-8)

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0, "Цель Concurrent не была транслирована"
    assert any(
        inst.ggb_type == "point" and "goalConcurrent" in inst.name
        for inst in goal_instructions
    )

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "radical_center.ggb")

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
        f"\n[+] Теорема о радикальном центре успешно сохранена: {os.path.abspath(output_path)}"
    )
    assert os.path.exists(output_path), "Файл .ggb не был создан на диске"
