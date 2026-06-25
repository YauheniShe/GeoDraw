import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.models import GeoDraftDocument
from compiler.operations.lines import PerpendicularLineOp


def assert_line_approx(line1, line2, abs_tol=1e-7):
    """
    Проверяет совпадение уравнений прямых Ax + By + C = 0.
    Прямые эквивалентны, если их коэффициенты пропорциональны.
    """
    a1, b1, c1 = line1
    norm1 = (a1**2 + b1**2) ** 0.5
    if a1 < 0 or (abs(a1) < 1e-9 and b1 < 0):
        norm1 = -norm1

    a2, b2, c2 = line2
    norm2 = (a2**2 + b2**2) ** 0.5
    if a2 < 0 or (abs(a2) < 1e-9 and b2 < 0):
        norm2 = -norm2

    assert a1 / norm1 == pytest.approx(a2 / norm2, abs=abs_tol)
    assert b1 / norm1 == pytest.approx(b2 / norm2, abs=abs_tol)
    assert c1 / norm1 == pytest.approx(c2 / norm2, abs=abs_tol)


def test_perpendicular_compile_sample():
    """
    Юнит-тест математического вычисления перпендикулярной прямой.
    Возьмем исходную прямую 2x - y + 1 = 0 (коэффициенты A=2, B=-1, C=1).
    И точку P(1, 1), не лежащую на ней.
    Перпендикулярная прямая, проходящая через P, должна иметь уравнение:
    1x + 2y - 3 = 0 (коэффициенты A=1, B=2, C=-3).
    """
    args = {"point": "P", "line": "L"}
    step_func = PerpendicularLineOp.compile_sample(
        args=args, name="Perp", disambiguation=None
    )

    env = {"L": (2.0, -1.0, 1.0), "P": (1.0, 1.0)}
    step_func(env)
    assert_line_approx(env["Perp"], (1.0, 2.0, -3.0))


def test_perpendicular_to_ggb():
    """Юнит-тест трансляции метода PerpendicularLine в синтаксис GeoGebra"""
    args = {"point": "A", "line": "Line_BC"}
    ggb_expr = PerpendicularLineOp.to_ggb(args=args, name="Alt_A")

    assert ggb_expr == "PerpendicularLine(A, Line_BC)"


def test_problem_altitudes_concurrency():
    """
    Интеграционный тест:
    Доказывает теорему о пересечении трех высот треугольника в одной точке.
    Высоты строятся вручную через PerpendicularLine к противоположным сторонам.
    Результат сохраняется в файл tests_output/altitudes_concurrency.ggb.
    """
    doc_data = {
        "problem_name": "Concurrency of Triangle Altitudes",
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
                "args": {"approx_position": [-4, -2]},
            },
            {
                "name": "C",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [4, -2]},
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
                "name": "Alt_A",
                "type": "Line",
                "method": "PerpendicularLine",
                "args": {"point": "A", "line": "Line_BC"},
            },
            {
                "name": "Alt_B",
                "type": "Line",
                "method": "PerpendicularLine",
                "args": {"point": "B", "line": "Line_CA"},
            },
            {
                "name": "Alt_C",
                "type": "Line",
                "method": "PerpendicularLine",
                "args": {"point": "C", "line": "Line_AB"},
            },
            {
                "name": "D",
                "type": "Point",
                "method": "Projection",
                "args": {"point": "A", "line": "Line_BC"},
                "hidden": True,
            },
            {
                "name": "E",
                "type": "Point",
                "method": "Projection",
                "args": {"point": "B", "line": "Line_CA"},
                "hidden": True,
            },
            {
                "name": "F",
                "type": "Point",
                "method": "Projection",
                "args": {"point": "C", "line": "Line_AB"},
                "hidden": True,
            },
        ],
        "goals": [
            {"type": "Concurrent", "args": {"objects": ["Alt_A", "Alt_B", "Alt_C"]}}
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "Clip", "target": "Alt_A", "endpoints": ["A", "D"]},
            {"action": "Clip", "target": "Alt_B", "endpoints": ["B", "E"]},
            {"action": "Clip", "target": "Alt_C", "endpoints": ["C", "F"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать корректный треугольник"
    la = env["Alt_A"]
    lb = env["Alt_B"]
    lc = env["Alt_C"]

    det = (
        la[0] * (lb[1] * lc[2] - lb[2] * lc[1])
        - la[1] * (lb[0] * lc[2] - lb[2] * lc[0])
        + la[2] * (lb[0] * lc[1] - lb[1] * lc[0])
    )

    assert det == pytest.approx(0.0, abs=1e-8), (
        f"Высоты не пересекаются в одной точке, det = {det}"
    )

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)
    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0
    assert any(
        inst.ggb_type == "point" and "Intersect" in inst.expression
        for inst in goal_instructions
    )

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "altitudes_concurrency.ggb")

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
        f"\n[+] Интерактивный чертеж пересечения высот успешно сохранен: {os.path.abspath(output_path)}"
    )
    assert os.path.exists(output_path), "Файл .ggb не был сгенерирован"
