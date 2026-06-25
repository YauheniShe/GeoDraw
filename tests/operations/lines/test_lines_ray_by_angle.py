import math
import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator, GGBInstruction
from compiler.generator import GeoDraftGenerator
from compiler.models import GeoDraftDocument
from compiler.operations.circles import RayByAngleOp


def assert_point_approx(pt1, pt2, abs_tol=1e-7):
    assert pt1[0] == pytest.approx(pt2[0], abs=abs_tol)
    assert pt1[1] == pytest.approx(pt2[1], abs=abs_tol)


def test_ray_by_angle_compile_sample_ccw():
    """
    Юнит-тест для RayByAngleOp.compile_sample при повороте против часовой стрелки (CCW).
    Поворачиваем луч из (0,0) -> (1,0) на угол 90 градусов (pi/2) CCW.
    Ожидаем получить луч из (0,0) -> (0,1).
    """
    args = {"ray": "Ray_ref", "angle": {"type": "Number", "value": math.pi / 2}}
    step_func = RayByAngleOp.compile_sample(
        args=args, name="Ray_rot", disambiguation={"orientation": "counterclockwise"}
    )

    env = {"Ray_ref": ("ray", (0.0, 0.0), (1.0, 0.0))}
    step_func(env)

    ray_type, start, direction = env["Ray_rot"]
    assert ray_type == "ray"
    assert_point_approx(start, (0.0, 0.0))
    assert_point_approx(direction, (0.0, 1.0))


def test_ray_by_angle_compile_sample_cw():
    """
    Юнит-тест для RayByAngleOp.compile_sample при повороте по часовой стрелке (CW).
    Поворачиваем луч из (0,0) -> (1,0) на угол 90 градусов (pi/2) CW.
    Ожидаем получить луч из (0,0) -> (0,-1).
    """
    args = {"ray": "Ray_ref", "angle": {"type": "Number", "value": math.pi / 2}}
    step_func = RayByAngleOp.compile_sample(
        args=args, name="Ray_rot", disambiguation={"orientation": "clockwise"}
    )

    env = {"Ray_ref": ("ray", (0.0, 0.0), (1.0, 0.0))}
    step_func(env)

    ray_type, start, direction = env["Ray_rot"]
    assert ray_type == "ray"
    assert_point_approx(start, (0.0, 0.0))
    assert_point_approx(direction, (0.0, -1.0))


def test_ray_by_angle_to_ggb():
    """
    Юнит-тест трансляции RayByAngle в GeoGebra.
    Проверяет, что генерируется функция Rotate(ray, angle, origin).
    """
    translator = GeoDraftTranslator()

    translator.instructions.append(
        GGBInstruction(name="Ray_ref", expression="Ray(A, B)", ggb_type="ray")
    )

    args = {"ray": "Ray_ref", "angle": "alpha"}
    disamb = {"value": "counterclockwise"}

    expr = RayByAngleOp.to_ggb(args, "Ray_rot", translator, disamb)
    assert expr == "Rotate(Ray_ref, alpha, A)"


def test_problem_angle_trisection():
    """
    Интеграционный тест: Трисекция угла треугольника.
    Строит треугольник ABC (CCW), измеряет угол A (alpha), вычисляет alpha/3 и 2*alpha/3.
    Поворачивает луч AB на эти углы, строит точки на лучах и доказывает,
    что три получившихся угла равны между собой.
    Экспортирует результат в tests_output/angle_trisection.ggb.
    """
    doc_data = {
        "problem_name": "Angle Trisection Test",
        "constraints": [
            {
                "type": "Inequality",
                "operator": ">",
                "left": {
                    "type": "MathExpression",
                    "expression": "x(A)*(y(B) - y(C)) + x(B)*(y(C) - y(A)) + x(C)*(y(A) - y(B))",
                    "variables": {"A": "A", "B": "B", "C": "C"},
                },
                "right": {"type": "Number", "value": 2.0},
            }
        ],
        "construction": [
            {
                "name": "A",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [0, 0]},
            },
            {
                "name": "B",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [5, 0]},
            },
            {
                "name": "C",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [2, 4]},
            },
            {
                "name": "Ray_AB",
                "type": "Ray",
                "method": "RayByPoints",
                "args": {"origin": "A", "direction_point": "B"},
                "hidden": True,
            },
            {
                "name": "alpha",
                "type": "AngleMeasure",
                "method": "Free",
                "args": {"vertex": "A", "ends": ["B", "C"]},
                "hidden": True,
            },
            {
                "name": "one_third",
                "type": "MathExpression",
                "method": "Free",
                "args": {"expression": "alpha / 3", "variables": {"alpha": "alpha"}},
                "hidden": True,
            },
            {
                "name": "two_thirds",
                "type": "MathExpression",
                "method": "Free",
                "args": {
                    "expression": "2 * alpha / 3",
                    "variables": {"alpha": "alpha"},
                },
                "hidden": True,
            },
            {
                "name": "Trisector1",
                "type": "Ray",
                "method": "RayByAngle",
                "args": {"ray": "Ray_AB", "angle": "one_third"},
            },
            {
                "name": "Trisector2",
                "type": "Ray",
                "method": "RayByAngle",
                "args": {"ray": "Ray_AB", "angle": "two_thirds"},
            },
            {
                "name": "P1",
                "type": "Point",
                "method": "PointOnObject",
                "args": {"object": "Trisector1"},
            },
            {
                "name": "P2",
                "type": "Point",
                "method": "PointOnObject",
                "args": {"object": "Trisector2"},
            },
        ],
        "goals": [
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "AngleMeasure", "vertex": "A", "ends": ["B", "P1"]},
                        {"type": "AngleMeasure", "vertex": "A", "ends": ["P1", "P2"]},
                    ]
                },
            },
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "AngleMeasure", "vertex": "A", "ends": ["P1", "P2"]},
                        {"type": "AngleMeasure", "vertex": "A", "ends": ["P2", "C"]},
                    ]
                },
            },
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "Show", "targets": ["Trisector1", "Trisector2"]},
            {"action": "DrawAngle", "vertex": "A", "ends": ["B", "P1"]},
            {"action": "DrawAngle", "vertex": "A", "ends": ["P1", "P2"]},
            {"action": "DrawAngle", "vertex": "A", "ends": ["P2", "C"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать корректную конфигурацию"

    def angle_value(v, e1, e2):
        dx1, dy1 = e1[0] - v[0], e1[1] - v[1]
        dx2, dy2 = e2[0] - v[0], e2[1] - v[1]
        raw_ang = abs(math.atan2(dx1 * dy2 - dy1 * dx2, dx1 * dx2 + dy1 * dy2))
        return raw_ang if raw_ang <= math.pi else (2 * math.pi - raw_ang)

    ang1 = angle_value(env["A"], env["B"], env["P1"])
    ang2 = angle_value(env["A"], env["P1"], env["P2"])
    ang3 = angle_value(env["A"], env["P2"], env["C"])

    assert ang1 == pytest.approx(ang2, abs=1e-6)
    assert ang2 == pytest.approx(ang3, abs=1e-6)

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "angle_trisection.ggb")

    original_types = {}
    for obj in doc.construction:
        if obj.name:
            original_types[obj.name] = obj.type

    generator = GeoDraftGenerator(config=GeoDrawConfig())
    generator.create_ggb(project, original_types, output_path)

    print(f"\n[+] Трисекция угла успешно сохранена: {os.path.abspath(output_path)}")
    assert os.path.exists(output_path)
