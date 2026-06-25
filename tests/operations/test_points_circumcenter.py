import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import dist
from compiler.models import GeoDraftDocument
from compiler.operations.points import CircumcenterOp


def assert_point_approx(pt1, pt2, abs_tol=1e-7):
    assert pt1[0] == pytest.approx(pt2[0], abs=abs_tol)
    assert pt1[1] == pytest.approx(pt2[1], abs=abs_tol)


def test_circumcenter_compile_sample():
    """
    Юнит-тест для CircumcenterOp.compile_sample.
    Возьмем прямоугольный треугольник A(0, 4), B(0, 0), C(6, 0).
    В прямоугольном треугольнике центр описанной окружности всегда лежит
    на середине гипотенузы (отрезка AC):
    Ox = (0 + 6) / 2 = 3
    Oy = (4 + 0) / 2 = 2
    """
    args = {"triangle": ["A", "B", "C"]}
    step_func = CircumcenterOp.compile_sample(args=args, name="O", disambiguation=None)

    env = {"A": (0.0, 4.0), "B": (0.0, 0.0), "C": (6.0, 0.0)}
    step_func(env)

    assert_point_approx(env["O"], (3.0, 2.0))


def test_circumcenter_to_ggb():
    """Юнит-тест трансляции метода Circumcenter в синтаксис GeoGebra (TriangleCenter с индексом 3)"""
    args = {"triangle": ["A", "B", "C"]}
    ggb_expr = CircumcenterOp.to_ggb(args=args, name="O_node", disambiguation=None)

    assert ggb_expr == "TriangleCenter(A, B, C, 3)"


def test_problem_circumcenter_equidistance():
    """
    Интеграционный E2E тест:
    Проверяет равноудаленность центра описанной окружности O от вершин A, B, C (OA = OB = OC).
    Экспортирует результат в tests_output/circumcenter_equidistance.ggb.
    """
    doc_data = {
        "problem_name": "Circumcenter Equidistance Theorem",
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
                "args": {"approx_position": [3, -1]},
            },
            {
                "name": "O",
                "type": "Point",
                "method": "Circumcenter",
                "args": {"triangle": ["A", "B", "C"]},
            },
        ],
        "goals": [
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "Distance", "points": ["O", "A"]},
                        {"type": "Distance", "points": ["O", "B"]},
                    ]
                },
            },
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "Distance", "points": ["O", "A"]},
                        {"type": "Distance", "points": ["O", "C"]},
                    ]
                },
            },
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "Show", "targets": ["O"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать невырожденную конфигурацию треугольника"

    p_a, p_b, p_c, p_o = env["A"], env["B"], env["C"], env["O"]

    d_oa = dist(p_o, p_a)
    d_ob = dist(p_o, p_b)
    d_oc = dist(p_o, p_c)

    assert d_oa == pytest.approx(d_ob, abs=1e-8), f"OA != OB: {d_oa:.6f} != {d_ob:.6f}"
    assert d_oa == pytest.approx(d_oc, abs=1e-8), f"OA != OC: {d_oa:.6f} != {d_oc:.6f}"

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)
    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0
    assert any(inst.ggb_type == "segment" for inst in goal_instructions)

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "circumcenter_equidistance.ggb")

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
        f"\n[+] Файл центра описанной окружности успешно сохранен: {os.path.abspath(output_path)}"
    )
    assert os.path.exists(output_path)
