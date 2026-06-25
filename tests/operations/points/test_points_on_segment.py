import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import dist, get_line_eq
from compiler.models import GeoDraftDocument
from compiler.operations.points import PointOnSegmentOp


def assert_goals(doc: GeoDraftDocument, env: dict):
    for goal in doc.goals:
        g_type = goal.type
        args = goal.args

        if g_type == "Parallel":
            l1_ref, l2_ref = args["lines"]
            l1, l2 = get_line_eq(env[l1_ref]), get_line_eq(env[l2_ref])
            assert l1 is not None and l2 is not None
            det = l1[0] * l2[1] - l2[0] * l1[1]
            assert abs(det) < 1e-8, f"Цель Parallel провалена для {l1_ref} и {l2_ref}"

        elif g_type == "Belongs":
            pt_ref = args["point"]
            obj_ref = args["object"]
            pt = env[pt_ref]
            obj = env[obj_ref]

            if isinstance(obj, tuple) and len(obj) == 3 and obj[0] == "segment":
                p1, p2 = obj[1], obj[2]
                d1 = dist(p1, pt)
                d2 = dist(pt, p2)
                d_total = dist(p1, p2)
                assert abs(d1 + d2 - d_total) < 1e-8, (
                    f"Цель Belongs провалена: {pt_ref} не лежит на отрезке {obj_ref}"
                )
            else:
                l_eq = get_line_eq(obj)
                assert l_eq is not None, f"Объект {obj_ref} не распознан как линия"
                val = l_eq[0] * pt[0] + l_eq[1] * pt[1] + l_eq[2]
                assert abs(val) < 1e-8, (
                    f"Цель Belongs провалена: {pt_ref} не лежит на прямой {obj_ref}"
                )


def test_point_on_segment_math_midpoint():
    args = {"points": ["A", "B"], "ratio": 0.5}
    step_func = PointOnSegmentOp.compile_sample(
        args=args, name="M", disambiguation=None
    )

    env = {"A": (0.0, 0.0), "B": (10.0, 4.0)}
    step_func(env)

    assert env["M"] == pytest.approx((5.0, 2.0))


def test_point_on_segment_math_extremes():
    env = {"A": (2.0, 3.0), "B": (8.0, 9.0)}

    step_start = PointOnSegmentOp.compile_sample(
        args={"points": ["A", "B"], "ratio": 0.0}, name="Start", disambiguation=None
    )
    step_end = PointOnSegmentOp.compile_sample(
        args={"points": ["A", "B"], "ratio": 1.0}, name="End", disambiguation=None
    )

    step_start(env)
    step_end(env)

    assert env["Start"] == pytest.approx(env["A"])
    assert env["End"] == pytest.approx(env["B"])


def test_point_on_segment_math_custom_ratio():
    args = {"points": ["A", "B"], "ratio": 0.25}
    step_func = PointOnSegmentOp.compile_sample(
        args=args, name="P", disambiguation=None
    )

    env = {"A": (1.0, 1.0), "B": (5.0, 9.0)}
    step_func(env)
    assert env["P"] == pytest.approx((2.0, 3.0))


def test_point_on_segment_to_ggb():
    args = {"points": ["A", "B"], "ratio": 0.333}

    class MockTranslator:
        def _var_to_ggb(self, ratio):
            return str(ratio)

    translator = MockTranslator()

    ggb_expr = PointOnSegmentOp.to_ggb(
        args=args, name="P", disambiguation=None, translator=translator
    )

    assert ggb_expr == "(1 - (0.333)) * A + (0.333) * B"


def test_problem_centroid_median_intersection():
    """
    Теорема: Точка деления медианы AM в отношении 2:1 от вершины
    лежит на другой медиане BN.
    """
    doc_data = {
        "problem_name": "Centroid Intersection",
        "constraints": [],
        "construction": [
            {
                "name": "A",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [-2, -2]},
            },
            {
                "name": "B",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [4, -2]},
            },
            {
                "name": "C",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [1, 4]},
            },
            {
                "name": "M",
                "type": "Point",
                "method": "Midpoint",
                "args": {"points": ["B", "C"]},
            },
            {
                "name": "G",
                "type": "Point",
                "method": "PointOnSegment",
                "args": {
                    "points": ["A", "M"],
                    "ratio": 0.6666666666666666,
                },
            },
            {
                "name": "N",
                "type": "Point",
                "method": "Midpoint",
                "args": {"points": ["A", "C"]},
            },
            {
                "name": "Segment_BN",
                "type": "Segment",
                "method": "SegmentByPoints",
                "args": {"points": ["B", "N"]},
            },
        ],
        "goals": [{"type": "Belongs", "args": {"point": "G", "object": "Segment_BN"}}],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "DrawSegment", "endpoints": ["A", "M"]},
            {"action": "DrawSegment", "endpoints": ["B", "N"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)

    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать конфигурацию"

    assert_goals(doc, env)

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0, "Транслятор не сгенерировал GGB-код для целей"

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "median_intersection.ggb")

    original_types = {}
    for obj in doc.construction:
        if obj.name:
            original_types[obj.name] = obj.type
        elif obj.names:
            for name in obj.names:
                original_types[name] = obj.type

    config = GeoDrawConfig()
    config.show_axes = False
    config.show_grid = False

    generator = GeoDraftGenerator(config=config)
    generator.create_ggb(project, original_types, output_path)

    print(f"\n[+] Файл GeoGebra успешно сохранен: {os.path.abspath(output_path)}")
    assert os.path.exists(output_path), "Файл .ggb не был создан на диске"
