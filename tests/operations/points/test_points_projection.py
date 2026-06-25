import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import get_line_eq
from compiler.models import GeoDraftDocument
from compiler.operations.points import ProjectionOp


def assert_goals(doc: GeoDraftDocument, env: dict):
    from compiler.math_lib.base import dist

    for goal in doc.goals:
        g_type = goal.type
        args = goal.args

        if g_type == "Parallel":
            l1_ref, l2_ref = args["lines"]
            l1, l2 = get_line_eq(env[l1_ref]), get_line_eq(env[l2_ref])
            assert l1 is not None and l2 is not None
            det = l1[0] * l2[1] - l2[0] * l1[1]
            assert abs(det) < 1e-8, f"Цель Parallel провалена для {l1_ref} и {l2_ref}"

        elif g_type == "Equal":
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

        elif g_type == "Collinear":
            pts = args["points"]
            assert len(pts) >= 3, "Для проверки коллинеарности нужно минимум 3 точки"
            p0, p1, p2 = env[pts[0]], env[pts[1]], env[pts[2]]

            dx1, dy1 = p1[0] - p0[0], p1[1] - p0[1]
            dx2, dy2 = p2[0] - p0[0], p2[1] - p0[1]
            cross_product = dx1 * dy2 - dy1 * dx2

            assert abs(cross_product) < 1e-8, (
                f"Цель Collinear провалена для {pts}: {cross_product:.8f} != 0"
            )


def test_projection_math_evaluation():
    """
    Проверяем чистую математику проекции.
    Спроецируем точку (1, 5) на горизонтальную прямую y = 0 (ось X).
    """
    args = {"point": "P", "line": "L"}
    step_func = ProjectionOp.compile_sample(args=args, name="Proj", disambiguation=None)

    env = {
        "P": (1.0, 5.0),
        "L": (0.0, 1.0, 0.0),
    }

    step_func(env)

    assert env["Proj"] == pytest.approx((1.0, 0.0))


def test_projection_to_ggb_translation():
    args = {"point": "A", "line": "Line_BC"}
    ggb_expr = ProjectionOp.to_ggb(
        args=args, name="Proj_A", disambiguation=None, translator=None
    )

    assert ggb_expr == "ClosestPoint(Line_BC, A)"


def test_problem_simson_line():
    doc_data = {
        "problem_name": "Simson Line Theorem",
        "constraints": [],
        "construction": [
            {
                "name": "A",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [-2, -1]},
            },
            {
                "name": "B",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [2, -2]},
            },
            {
                "name": "C",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [0, 3]},
            },
            {
                "name": "Circ",
                "type": "Circle",
                "method": "Circumcircle",
                "args": {"triangle": ["A", "B", "C"]},
            },
            {
                "name": "P",
                "type": "Point",
                "method": "PointOnObject",
                "args": {"object": "Circ"},
            },
            {
                "name": "Line_AB",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["A", "B"]},
            },
            {
                "name": "Line_BC",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["B", "C"]},
            },
            {
                "name": "Line_CA",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["C", "A"]},
            },
            {
                "name": "Pa",
                "type": "Point",
                "method": "Projection",
                "args": {"point": "P", "line": "Line_BC"},
            },
            {
                "name": "Pb",
                "type": "Point",
                "method": "Projection",
                "args": {"point": "P", "line": "Line_CA"},
            },
            {
                "name": "Pc",
                "type": "Point",
                "method": "Projection",
                "args": {"point": "P", "line": "Line_AB"},
            },
        ],
        "goals": [{"type": "Collinear", "args": {"points": ["Pa", "Pb", "Pc"]}}],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "Show", "targets": ["Circ", "P"]},
            {"action": "DrawSegment", "endpoints": ["P", "Pa"]},
            {"action": "DrawSegment", "endpoints": ["P", "Pb"]},
            {"action": "DrawSegment", "endpoints": ["P", "Pc"]},
            {"action": "Hide", "targets": ["Line_AB", "Line_BC", "Line_CA"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)

    env = sample_and_evaluate(doc)
    assert env, "Семплер застрял при расчете прямой Симсона"
    assert_goals(doc, env)

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0, "Транслятор пропустил цель Collinear"
    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "simson_line.ggb")

    original_types = {obj.name: obj.type for obj in doc.construction if obj.name}

    config = GeoDrawConfig()
    config.show_axes = True
    config.show_grid = True

    generator = GeoDraftGenerator(config=config)
    generator.create_ggb(project, original_types, output_path)

    print(f"\n[+] Файл GeoGebra успешно сохранен: {os.path.abspath(output_path)}")
    assert os.path.exists(output_path), "Файл .ggb не был записан"
