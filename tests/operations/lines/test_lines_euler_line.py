import math
import os
from typing import Any, Dict

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import dist
from compiler.models import GeoDraftDocument
from compiler.operations.lines import EulerLineOp
from compiler.operations.transformations import ReflectionOp


def assert_point_approx(pt1, pt2, abs_tol=1e-7):
    assert pt1[0] == pytest.approx(pt2[0], abs=abs_tol)
    assert pt1[1] == pytest.approx(pt2[1], abs=abs_tol)


def test_euler_line_compile_sample():
    """
    Юнит-тест математического ядра.
    Возьмем прямоугольный треугольник A(0, 3), B(0, 0), C(4, 0).
    - Центроид G = (4/3, 1).
    - Центр описанной окружности O = (2, 1.5).
    Прямая Эйлера проходит через (4/3, 1) и (2, 1.5).
    Уравнение прямой: -3x + 4y = 0.
    Нормализованный вектор коэффициентов (a, b, c): (-0.6, 0.8, 0.0) или (0.6, -0.8, 0.0).
    """
    args = {"triangle": ["A", "B", "C"]}
    step_func = EulerLineOp.compile_sample(args=args, name="EL", disambiguation=None)

    env: Dict[str, Any] = {"A": (0.0, 3.0), "B": (0.0, 0.0), "C": (4.0, 0.0)}
    step_func(env)

    a, b, c = env["EL"]
    assert abs(a * 2.0 + b * 1.5 + c) == pytest.approx(0.0, abs=1e-7)
    assert abs(a * (4 / 3) + b * 1.0 + c) == pytest.approx(0.0, abs=1e-7)
    assert abs(c) == pytest.approx(0.0, abs=1e-7)


def test_euler_line_to_ggb():
    """
    Юнит-тест трансляции в GGB.
    Должен генерировать скрытые вспомогательные точки Centroid (2) и Circumcenter (3).
    """
    translator = GeoDraftTranslator()
    args = {"triangle": ["A", "B", "C"]}
    expr = EulerLineOp.to_ggb(args, "EL", translator)

    assert expr == "Line(helper_centroid_EL, helper_cc_EL)"

    instructions = {inst.name: inst for inst in translator.instructions}
    assert "helper_centroid_EL" in instructions
    assert "helper_cc_EL" in instructions

    assert instructions["helper_centroid_EL"].expression == "TriangleCenter(A, B, C, 2)"
    assert instructions["helper_cc_EL"].expression == "TriangleCenter(A, B, C, 3)"
    assert instructions["helper_centroid_EL"].hidden is True
    assert instructions["helper_cc_EL"].hidden is True


def test_euler_line_equilateral_raises():
    """Граничный случай: для правильного треугольника центры совпадают, прямая не определена."""
    args = {"triangle": ["A", "B", "C"]}
    step_func = EulerLineOp.compile_sample(args=args, name="EL", disambiguation=None)

    env = {"A": (0.0, math.sqrt(3)), "B": (-1.0, 0.0), "C": (1.0, 0.0)}
    with pytest.raises(ValueError, match="Точки для построения прямой совпадают"):
        step_func(env)


def test_euler_line_collinear_raises():
    """Граничный случай: вырожденный (плоский) треугольник."""
    args = {"triangle": ["A", "B", "C"]}
    step_func = EulerLineOp.compile_sample(args=args, name="EL", disambiguation=None)

    env = {"A": (0.0, 0.0), "B": (1.0, 0.0), "C": (2.0, 0.0)}
    with pytest.raises(ValueError, match="Точки лежат на одной прямой"):
        step_func(env)


def test_euler_line_reflection_transformation():
    """Проверка взаимодействия: Отражение прямой Эйлера относительно другой прямой."""
    env = {
        "A": (0.0, 3.0),
        "B": (0.0, 0.0),
        "C": (4.0, 0.0),
        "Axis": (1.0, 0.0, -5.0),
    }

    EulerLineOp.compile_sample({"triangle": ["A", "B", "C"]}, "EL", None)(env)

    ReflectionOp.compile_sample({"target": "EL", "axis": "Axis"}, "EL_refl", None)(env)

    a, b, c = env["EL_refl"]
    assert abs(a * 8.0 + b * 1.5 + c) == pytest.approx(0.0, abs=1e-7)
    assert abs(a * (26 / 3) + b * 1.0 + c) == pytest.approx(0.0, abs=1e-7)


def test_problem_euler_line_complex_properties():
    """
    Широкий интеграционный тест.
    Доказывает комплексные свойства прямой Эйлера:
    1) Коллинеарность O, G, H, N (все лежат на EL).
    2) Euler distance ratio: HG = 2 * GO.
    3) EL пересекает описанную окружность в U и V. Точка O является серединой UV (UO = OV).
    """
    doc_data = {
        "problem_name": "Euler Line Complex Properties",
        "constraints": [
            {
                "type": "Inequality",
                "operator": ">",
                "left": {
                    "type": "MathExpression",
                    "expression": "abs(x(A)*(y(B) - y(C)) + x(B)*(y(C) - y(A)) + x(C)*(y(A) - y(B)))",
                    "variables": {"A": "A", "B": "B", "C": "C"},
                },
                "right": {"type": "Number", "value": 2.0},
            },
            {
                "type": "Inequality",
                "operator": ">",
                "left": {
                    "type": "MathExpression",
                    "expression": "abs(d_AB - d_BC) * abs(d_BC - d_CA) * abs(d_CA - d_AB)",
                    "variables": {
                        "d_AB": {"type": "Distance", "points": ["A", "B"]},
                        "d_BC": {"type": "Distance", "points": ["B", "C"]},
                        "d_CA": {"type": "Distance", "points": ["C", "A"]},
                    },
                },
                "right": {"type": "Number", "value": 0.5},
            },
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
                "args": {"approx_position": [-4, -2]},
            },
            {
                "name": "C",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [4, -1]},
            },
            {
                "name": "EL",
                "type": "Line",
                "method": "EulerLine",
                "args": {"triangle": ["A", "B", "C"]},
            },
            {
                "name": "O",
                "type": "Point",
                "method": "Circumcenter",
                "args": {"triangle": ["A", "B", "C"]},
            },
            {
                "name": "G",
                "type": "Point",
                "method": "Centroid",
                "args": {"triangle": ["A", "B", "C"]},
            },
            {
                "name": "H",
                "type": "Point",
                "method": "Orthocenter",
                "args": {"triangle": ["A", "B", "C"]},
            },
            {
                "name": "NPC",
                "type": "Circle",
                "method": "NinePointCircle",
                "args": {"triangle": ["A", "B", "C"]},
                "hidden": True,
            },
            {
                "name": "N",
                "type": "Point",
                "method": "Center",
                "args": {"object": "NPC"},
            },
            {
                "name": "Circ_ABC",
                "type": "Circle",
                "method": "Circumcircle",
                "args": {"triangle": ["A", "B", "C"]},
            },
            {
                "name": "U",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "EL", "obj2": "Circ_ABC"},
                "disambiguation": {"rule": "algebraic_index", "index": 1},
            },
            {
                "name": "V",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "EL", "obj2": "Circ_ABC"},
                "disambiguation": {"rule": "algebraic_index", "index": 2},
            },
        ],
        "goals": [
            {"type": "Collinear", "args": {"points": ["O", "G", "H", "N"]}},
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "Distance", "points": ["H", "G"]},
                        {
                            "type": "MathExpression",
                            "expression": "2 * GO",
                            "variables": {
                                "GO": {"type": "Distance", "points": ["G", "O"]}
                            },
                        },
                    ]
                },
            },
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "Distance", "points": ["U", "O"]},
                        {"type": "Distance", "points": ["O", "V"]},
                    ]
                },
            },
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "Show", "targets": ["Circ_ABC"]},
            {"action": "Clip", "target": "EL", "endpoints": ["U", "V"]},
            {"action": "Show", "targets": ["O", "G", "H", "N"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать подходящую конфигурацию треугольника"

    a, b, c = env["EL"]
    for pt_name in ["O", "G", "H", "N"]:
        x, y = env[pt_name]
        assert abs(a * x + b * y + c) == pytest.approx(0.0, abs=1e-8), (
            f"Точка {pt_name} не лежит на прямой Эйлера!"
        )

    d_hg = dist(env["H"], env["G"])
    d_go = dist(env["G"], env["O"])
    assert d_hg == pytest.approx(2 * d_go, abs=1e-8), (
        f"Отношение расстояний нарушено: HG = {d_hg:.6f}, 2*GO = {2 * d_go:.6f}"
    )

    d_uo = dist(env["U"], env["O"])
    d_ov = dist(env["O"], env["V"])
    assert d_uo == pytest.approx(d_ov, abs=1e-8), (
        f"Точка O не является серединой хорды UV: UO = {d_uo:.6f}, OV = {d_ov:.6f}"
    )

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0, "Транслятор не сгенерировал GGB-код для целей"

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "euler_line_properties.ggb")

    original_types = {obj.name: obj.type for obj in doc.construction if obj.name}

    config = GeoDrawConfig()
    config.show_axes = False
    config.show_grid = False

    generator = GeoDraftGenerator(config=config)
    generator.create_ggb(project, original_types, output_path)

    print(
        f"\n[+] Свойства прямой Эйлера успешно сохранены: {os.path.abspath(output_path)}"
    )
    assert os.path.exists(output_path), "Файл .ggb не был записан на диск"
