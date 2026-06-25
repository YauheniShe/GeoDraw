import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import dist
from compiler.models import GeoDraftDocument
from compiler.operations.circles import (
    SegmentOp,
)


def assert_point_approx(pt1, pt2, abs_tol=1e-7):
    assert pt1[0] == pytest.approx(pt2[0], abs=abs_tol)
    assert pt1[1] == pytest.approx(pt2[1], abs=abs_tol)


def test_segment_by_points_compile_sample():
    """
    Юнит-тест математического ядра для построения отрезка по двум точкам.
    Проверяет, что SegmentOp возвращает кортеж ("segment", p0, p1).
    """
    args = {"points": ["P", "Q"]}
    step_func = SegmentOp.compile_sample(args=args, name="Seg_PQ", disambiguation=None)

    env = {"P": (1.0, 2.0), "Q": (4.0, 6.0)}
    step_func(env)

    assert env["Seg_PQ"] == ("segment", (1.0, 2.0), (4.0, 6.0))


def test_segment_by_points_to_ggb():
    """Юнит-тест трансляции метода SegmentByPoints в синтаксис GeoGebra"""
    args = {"points": ["A", "B"]}
    ggb_expr = SegmentOp.to_ggb(args=args, name="Seg_AB", disambiguation=None)

    assert ggb_expr == "Segment(A, B)"


def test_problem_triangle_midsegment():
    """
    Интеграционный тест:
    Строит треугольник ABC, находит середины M и N сторон AB и AC.
    Соединяет их отрезком MN (средняя линия) и строит основание BC.
    Доказывает теорему: длина MN равна половине длины BC.
    Экспортирует результат в tests_output/triangle_midsegment.ggb.
    """
    doc_data = {
        "problem_name": "Triangle Midsegment Theorem",
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
                "name": "M",
                "type": "Point",
                "method": "Midpoint",
                "args": {"points": ["A", "B"]},
            },
            {
                "name": "N",
                "type": "Point",
                "method": "Midpoint",
                "args": {"points": ["A", "C"]},
            },
            {
                "name": "Seg_MN",
                "type": "Segment",
                "method": "SegmentByPoints",
                "args": {"points": ["M", "N"]},
            },
            {
                "name": "Seg_BC",
                "type": "Segment",
                "method": "SegmentByPoints",
                "args": {"points": ["B", "C"]},
            },
        ],
        "goals": [
            {
                "type": "Equal",
                "args": {"values": [{"type": "Distance", "points": ["M", "N"]}]},
            }
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "Show", "targets": ["Seg_MN", "Seg_BC"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать базовый треугольник"

    pt_m = env["M"]
    pt_n = env["N"]
    pt_b = env["B"]
    pt_c = env["C"]

    len_mn = dist(pt_m, pt_n)
    len_bc = dist(pt_b, pt_c)

    assert len_mn == pytest.approx(len_bc / 2.0, abs=1e-8), (
        f"Теорема провалена: длина средней линии {len_mn:.6f} не равна половине основания {len_bc / 2:.6f}"
    )

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0
    assert any(inst.ggb_type == "segment" for inst in goal_instructions)

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "triangle_midsegment.ggb")

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
        f"\n[+] Чертеж средней линии треугольника сохранен в: {os.path.abspath(output_path)}"
    )
    assert os.path.exists(output_path), "Файл .ggb не был создан на диске"
