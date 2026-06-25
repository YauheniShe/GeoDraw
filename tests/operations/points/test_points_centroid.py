import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import dist
from compiler.models import GeoDraftDocument
from compiler.operations.points import CentroidOp


def assert_point_approx(pt1, pt2, abs_tol=1e-7):
    assert pt1[0] == pytest.approx(pt2[0], abs=abs_tol)
    assert pt1[1] == pytest.approx(pt2[1], abs=abs_tol)


def test_centroid_compile_sample():
    """
    Юнит-тест для CentroidOp.compile_sample на треугольнике с известными координатами.
    Возьмем треугольник A(0, 6), B(-3, 0), C(3, 0).
    Координаты центроида G должны быть равны среднему арифметическому координат вершин:
    Gx = (0 - 3 + 3) / 3 = 0
    Gy = (6 + 0 + 0) / 3 = 2
    """
    args = {"triangle": ["A", "B", "C"]}
    step_func = CentroidOp.compile_sample(args=args, name="G", disambiguation=None)

    env = {"A": (0.0, 6.0), "B": (-3.0, 0.0), "C": (3.0, 0.0)}
    step_func(env)

    assert_point_approx(env["G"], (0.0, 2.0))


def test_centroid_to_ggb():
    """Юнит-тест трансляции метода Centroid в синтаксис GeoGebra (TriangleCenter с индексом 2)"""
    args = {"triangle": ["A", "B", "C"]}
    ggb_expr = CentroidOp.to_ggb(args=args, name="G_node", disambiguation=None)

    assert ggb_expr == "TriangleCenter(A, B, C, 2)"


def test_problem_centroid_median():
    """
    Интеграционный E2E тест:
    Проверяет, что центроид G треугольника ABC лежит на медиане AM_a (где M_a — середина BC)
    и делит её в отношении 2:1, считая от вершины A (AG = 2 * G_Ma).
    Экспортирует результат в tests_output/centroid_median.ggb.
    """
    doc_data = {
        "problem_name": "Centroid and Median Concurrency",
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
                "args": {"approx_position": [-3, 0]},
            },
            {
                "name": "C",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [3, 0]},
            },
            {
                "name": "G",
                "type": "Point",
                "method": "Centroid",
                "args": {"triangle": ["A", "B", "C"]},
            },
            {
                "name": "M_a",
                "type": "Point",
                "method": "Midpoint",
                "args": {"points": ["B", "C"]},
            },
        ],
        "goals": [{"type": "Collinear", "args": {"points": ["A", "G", "M_a"]}}],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "Show", "targets": ["G", "M_a"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать невырожденную конфигурацию треугольника"

    p_a, p_g, p_ma = env["A"], env["G"], env["M_a"]
    area_2 = abs(
        p_a[0] * (p_g[1] - p_ma[1])
        + p_g[0] * (p_ma[1] - p_a[1])
        + p_ma[0] * (p_a[1] - p_g[1])
    )
    assert area_2 == pytest.approx(0.0, abs=1e-8), (
        f"Точки не коллинеарны. Удвоенная площадь: {area_2}"
    )

    d_ag = dist(p_a, p_g)
    d_gma = dist(p_g, p_ma)
    assert d_ag == pytest.approx(2.0 * d_gma, rel=1e-7), (
        f"Отношение медиан нарушено: AG={d_ag:.6f}, G_Ma={d_gma:.6f} (должно быть AG = 2 * G_Ma)"
    )
    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0
    assert any(inst.ggb_type == "line" for inst in goal_instructions)

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "centroid_median.ggb")

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
        f"\n[+] Файл центроида медианы успешно сохранен: {os.path.abspath(output_path)}"
    )
    assert os.path.exists(output_path)
