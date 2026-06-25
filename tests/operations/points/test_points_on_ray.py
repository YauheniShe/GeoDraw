import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import dist
from compiler.models import GeoDraftDocument
from compiler.operations.points import PointOnRayOp


def assert_goals(doc: GeoDraftDocument, env: dict):
    for goal in doc.goals:
        g_type = goal.type
        args = goal.args

        if g_type == "Equal":
            vals = args["values"]
            if (
                len(vals) == 2
                and vals[0]["type"] == "Distance"
                and vals[1]["type"] == "Distance"
            ):
                p1_1, p1_2 = vals[0]["points"]
                p2_1, p2_2 = vals[1]["points"]
                d1 = dist(env[p1_1], env[p1_2])
                d2 = dist(env[p2_1], env[p2_2])
                assert abs(d1 - d2) < 1e-8, (
                    f"Цель Equal (Distance) провалена: {d1:.4f} != {d2:.4f}"
                )


def test_point_on_ray_compile():
    env = {"A": (0.0, 0.0), "B": (3.0, 4.0), "my_distance": 10.0}
    args = {"points": ["A", "B"], "distance": "my_distance"}

    step_func = PointOnRayOp.compile_sample(args=args, name="D", disambiguation=None)
    step_func(env)

    assert env["D"] == pytest.approx((6.0, 8.0), abs=1e-9)


def test_point_on_ray_degenerate():
    env = {"A": (1.1, 2.2), "B": (1.1, 2.2), "my_distance": 5.0}
    args = {"points": ["A", "B"], "distance": "my_distance"}

    step_func = PointOnRayOp.compile_sample(args=args, name="D", disambiguation=None)

    with pytest.raises(ValueError, match="Точки для луча совпадают"):
        step_func(env)


def test_point_on_ray_to_ggb():
    translator = GeoDraftTranslator()
    args = {"points": ["X", "Y"], "distance": "some_var"}

    ggb_expr = PointOnRayOp.to_ggb(
        args=args, name="Z", disambiguation=None, translator=translator
    )

    assert ggb_expr == "X + (some_var) * UnitVector(Y - X)"


def test_problem_median_extension():

    doc_data = {
        "problem_name": "Rhomboid by Median Extension",
        "constraints": [],
        "construction": [
            {
                "name": "A",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [0, 5]},
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
                "args": {"points": ["B", "C"]},
            },
            {
                "name": "AM_dist",
                "type": "Distance",
                "args": {"points": ["A", "M"]},
                "hidden": True,
            },
            {
                "name": "AD_len",
                "type": "MathExpression",
                "args": {"expression": "2 * d", "variables": {"d": "AM_dist"}},
                "hidden": True,
            },
            {
                "name": "D",
                "type": "Point",
                "method": "PointOnRay",
                "args": {"points": ["A", "M"], "distance": "AD_len"},
            },
        ],
        "goals": [
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "Distance", "points": ["A", "B"]},
                        {"type": "Distance", "points": ["C", "D"]},
                    ]
                },
            },
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "Distance", "points": ["A", "C"]},
                        {"type": "Distance", "points": ["B", "D"]},
                    ]
                },
            },
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "D", "C"]},
            {"action": "DrawSegment", "endpoints": ["A", "D"]},
            {"action": "DrawSegment", "endpoints": ["B", "C"]},
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
    output_path = os.path.join(output_dir, "median_extension.ggb")

    original_types = {}
    for obj in doc.construction:
        if obj.name:
            original_types[obj.name] = obj.type
        elif obj.names:
            for name in obj.names:
                original_types[name] = obj.type

    config = GeoDrawConfig()
    config.show_axes = True
    config.show_grid = True

    generator = GeoDraftGenerator(config=config)
    generator.create_ggb(project, original_types, output_path)

    print(f"\n[+] Файл GeoGebra успешно сохранен: {os.path.abspath(output_path)}")
    assert os.path.exists(output_path), "Файл .ggb не был создан на диске"
