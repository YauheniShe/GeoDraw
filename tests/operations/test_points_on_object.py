import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import dist, get_line_eq
from compiler.models import GeoDraftDocument
from compiler.operations.points import PointOnObjectOp


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

        elif g_type == "Collinear":
            pts = args["points"]
            if len(pts) >= 3:
                p1, p2, p3 = env[pts[0]], env[pts[1]], env[pts[2]]
                dx1, dy1 = p2[0] - p1[0], p2[1] - p1[1]
                dx2, dy2 = p3[0] - p1[0], p3[1] - p1[1]
                cross_product = dx1 * dy2 - dy1 * dx2
                assert abs(cross_product) < 1e-7, f"Цель Collinear провалена для {pts}"


def test_point_on_segment():
    env = {"Seg": ("segment", (0.0, 0.0), (10.0, 10.0))}

    step_func = PointOnObjectOp.compile_sample(
        args={"object": "Seg"}, name="P", disambiguation=None
    )

    for _ in range(10):
        step_func(env)
        px, py = env["P"]
        assert 0.0 < px < 10.0
        assert 0.0 < py < 10.0
        assert px == pytest.approx(py, abs=1e-9)


def test_point_on_line():
    env = {"Line": (2.0, -3.0, 6.0)}

    step_func = PointOnObjectOp.compile_sample(
        args={"object": "Line"}, name="P", disambiguation=None
    )

    for _ in range(10):
        step_func(env)
        px, py = env["P"]
        eq_val = 2.0 * px - 3.0 * py + 6.0
        assert eq_val == pytest.approx(0.0, abs=1e-8)


def test_point_on_circle():
    env = {"Circ": ((3.0, 4.0), 5.0)}

    step_func = PointOnObjectOp.compile_sample(
        args={"object": "Circ"}, name="P", disambiguation=None
    )

    for _ in range(10):
        step_func(env)
        d = dist((3.0, 4.0), env["P"])
        assert d == pytest.approx(5.0, abs=1e-9)


def test_point_on_object_to_ggb():
    args = {"object": "Circumcircle_ABC"}
    ggb_expr = PointOnObjectOp.to_ggb(args=args, name="P", disambiguation=None)
    assert ggb_expr == "Point(Circumcircle_ABC)"


def test_problem_simson_line():
    """
    Теорема о прямой Симсона: Проекции точки P, лежащей на описанной окружности
    треугольника ABC, на его стороны, лежат на одной прямой.
    Экспортирует результат в tests_output/simson_line.ggb.
    """
    doc_data = {
        "problem_name": "Simson Line Theorem",
        "constraints": [
            {
                "type": "Inequality",
                "operator": ">",
                "left": {"type": "Distance", "points": ["A", "B"]},
                "right": {"type": "Number", "value": 1.5},
            }
        ],
        "construction": [
            {
                "name": "A",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [-1, -2]},
            },
            {
                "name": "B",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [5, -2]},
            },
            {
                "name": "C",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [1, 4]},
            },
            {
                "name": "Circum",
                "type": "Circle",
                "method": "Circumcircle",
                "args": {"triangle": ["A", "B", "C"]},
            },
            {
                "name": "P",
                "type": "Point",
                "method": "PointOnObject",
                "args": {"object": "Circum"},
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
                "name": "Proj_AB",
                "type": "Point",
                "method": "Projection",
                "args": {"point": "P", "line": "Line_AB"},
            },
            {
                "name": "Proj_BC",
                "type": "Point",
                "method": "Projection",
                "args": {"point": "P", "line": "Line_BC"},
            },
            {
                "name": "Proj_CA",
                "type": "Point",
                "method": "Projection",
                "args": {"point": "P", "line": "Line_CA"},
            },
        ],
        "goals": [
            {"type": "Collinear", "args": {"points": ["Proj_AB", "Proj_BC", "Proj_CA"]}}
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "Show", "targets": ["Circum"]},
            {"action": "DrawSegment", "endpoints": ["P", "Proj_AB"]},
            {"action": "DrawSegment", "endpoints": ["P", "Proj_BC"]},
            {"action": "DrawSegment", "endpoints": ["P", "Proj_CA"]},
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
    output_path = os.path.join(output_dir, "simson_line.ggb")

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
