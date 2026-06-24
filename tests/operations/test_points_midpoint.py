import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import dist
from compiler.models import GeoDraftDocument
from compiler.operations.points import MidpointOp


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


@pytest.mark.parametrize(
    "coord_a, coord_b, expected",
    [
        ((0.0, 0.0), (4.0, 6.0), (2.0, 3.0)),
        (
            (-2.5, 3.0),
            (2.5, -3.0),
            (0.0, 0.0),
        ),
        (
            (-10.0, -5.5),
            (-2.0, 1.5),
            (-6.0, -2.0),
        ),
    ],
)
def test_midpoint_compile_sample(coord_a, coord_b, expected):
    args = {"points": ["A", "B"]}
    step_func = MidpointOp.compile_sample(args=args, name="M", disambiguation=None)

    env = {"A": coord_a, "B": coord_b}
    step_func(env)

    assert env["M"] == pytest.approx(expected), (
        f"Ошибка вычисления середины для {coord_a} и {coord_b}"
    )


def test_midpoint_to_ggb():
    args = {"points": ["X", "Y"]}
    ggb_expr = MidpointOp.to_ggb(args=args, name="M", disambiguation=None)
    assert ggb_expr == "Midpoint(X, Y)"


def test_problem_triangle_midline():
    doc_data = {
        "problem_name": "Triangle Midline Theorem",
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
                "args": {"approx_position": [5, 0]},
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
                "name": "P",
                "type": "Point",
                "method": "Midpoint",
                "args": {"points": ["B", "C"]},
            },
        ],
        "goals": [
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "Distance", "points": ["M", "N"]},
                        {"type": "Distance", "points": ["B", "P"]},
                    ]
                },
            }
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "DrawSegment", "endpoints": ["M", "N"]},
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
    output_path = os.path.join(output_dir, "triangle_midline.ggb")

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

    print(f"\n[+] Сгенерированный файл: {os.path.abspath(output_path)}")
    assert os.path.exists(output_path)
