import os
from typing import Any, Dict

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import dist
from compiler.models import GeoDraftDocument
from compiler.operations.lines import SymmedianOp


def assert_point_approx(pt1, pt2, abs_tol=1e-7):
    assert pt1[0] == pytest.approx(pt2[0], abs=abs_tol)
    assert pt1[1] == pytest.approx(pt2[1], abs=abs_tol)


def test_symmedian_compile_sample():
    """
    Юнит-тест математического ядра для симедианы.
    Возьмем египетский треугольник: A(0, 3), B(0, 0), C(4, 0).
    Построим симедиану из вершины B.
    - Медиана из B(0,0) идет в середину AC, точку M(2, 1.5).
    - Биссектриса угла B (между осями X и Y) лежит на прямой y = x.
    - Отражение точки M(2, 1.5) относительно y = x дает точку M'(1.5, 2.0).
    - Симедиана должна проходить через B(0,0) и M'(1.5, 2.0).
    - Уравнение прямой: -2x + 1.5y = 0. Нормированные коэффициенты (a, b, c) -> (-0.8, 0.6, 0.0) или (0.8, -0.6, 0.0).
    """
    args = {"triangle": ["A", "B", "C"], "vertex": "B"}
    step_func = SymmedianOp.compile_sample(args=args, name="SymB", disambiguation=None)

    env: Dict[str, Any] = {"A": (0.0, 3.0), "B": (0.0, 0.0), "C": (4.0, 0.0)}
    step_func(env)

    a, b, c = env["SymB"]

    assert abs(c) == pytest.approx(0.0, abs=1e-7)

    assert abs(a * 1.5 + b * 2.0) == pytest.approx(0.0, abs=1e-7)


def test_symmedian_to_ggb():
    """
    Юнит-тест трансляции в GGB.
    Проверяем, что симедиана транслируется в отражение медианы относительно биссектрисы
    с созданием двух скрытых вспомогательных линий.
    """
    translator = GeoDraftTranslator()
    args = {"triangle": ["A", "B", "C"], "vertex": "B"}
    expr = SymmedianOp.to_ggb(args, "SymB", translator)

    assert expr == "Reflect(med_SymB, bis_SymB)"

    instructions = {inst.name: inst for inst in translator.instructions}
    assert "med_SymB" in instructions
    assert "bis_SymB" in instructions

    assert "Line(B, Midpoint(" in instructions["med_SymB"].expression
    assert "AngleBisector(" in instructions["bis_SymB"].expression

    assert instructions["med_SymB"].hidden is True
    assert instructions["bis_SymB"].hidden is True


def test_problem_symmedian_lemoine_point():
    """
    Интеграционный тест: "Точка Лемуана".
    Доказывает, что:
    1. Три симедианы треугольника пересекаются в одной точке (Точка Лемуана).
    2. Эта точка в точности совпадает с изогонально сопряженной точкой центроида (G).
    """
    doc_data = {
        "problem_name": "Lemoine Point and Symmedians",
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
                "args": {"approx_position": [4, -2]},
            },
            {
                "name": "Sym_A",
                "type": "Line",
                "method": "Symmedian",
                "args": {"triangle": ["A", "B", "C"], "vertex": "A"},
            },
            {
                "name": "Sym_B",
                "type": "Line",
                "method": "Symmedian",
                "args": {"triangle": ["A", "B", "C"], "vertex": "B"},
            },
            {
                "name": "Sym_C",
                "type": "Line",
                "method": "Symmedian",
                "args": {"triangle": ["A", "B", "C"], "vertex": "C"},
            },
            {
                "name": "L",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Sym_A", "obj2": "Sym_B"},
            },
            {
                "name": "G",
                "type": "Point",
                "method": "Centroid",
                "args": {"triangle": ["A", "B", "C"]},
                "hidden": True,
            },
            {
                "name": "K",
                "type": "Point",
                "method": "IsogonalConjugate",
                "args": {"point": "G", "triangle": ["A", "B", "C"]},
            },
        ],
        "goals": [
            {"type": "Belongs", "args": {"point": "L", "object": "Sym_C"}},
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "Distance", "points": ["L", "K"]},
                        {"type": "Number", "value": 0.0},
                    ]
                },
            },
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "Clip", "target": "Sym_A", "endpoints": ["A", "L"]},
            {"action": "Clip", "target": "Sym_B", "endpoints": ["B", "L"]},
            {"action": "Clip", "target": "Sym_C", "endpoints": ["C", "L"]},
            {"action": "Show", "targets": ["K"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не подобрал конфигурацию"

    a, b, c = env["Sym_C"]
    lx, ly = env["L"]
    assert abs(a * lx + b * ly + c) == pytest.approx(0.0, abs=1e-8), (
        "Третья симедиана не проходит через пересечение первых двух!"
    )

    dist_LK = dist(env["L"], env["K"])
    assert dist_LK == pytest.approx(0.0, abs=1e-8), (
        f"Точка Лемуана не совпала с изогонально сопряженным центроидом. Расстояние: {dist_LK:.6f}"
    )

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "symmedian_lemoine.ggb")

    original_types = {obj.name: obj.type for obj in doc.construction if obj.name}

    config = GeoDrawConfig()
    config.show_axes = False
    config.show_grid = False

    generator = GeoDraftGenerator(config=config)
    generator.create_ggb(project, original_types, output_path)

    print(
        f"\n[+] Свойства симедианы и точки Лемуана успешно сохранены: {os.path.abspath(output_path)}"
    )
    assert os.path.exists(output_path)
