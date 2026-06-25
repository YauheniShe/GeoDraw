import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import dist
from compiler.models import GeoDraftDocument
from compiler.operations.points import OrthocenterOp


def assert_point_approx(pt1, pt2, abs_tol=1e-7):
    assert pt1[0] == pytest.approx(pt2[0], abs=abs_tol)
    assert pt1[1] == pytest.approx(pt2[1], abs=abs_tol)


def test_orthocenter_compile_sample():

    args = {"triangle": ["A", "B", "C"]}
    step_func = OrthocenterOp.compile_sample(args=args, name="H", disambiguation=None)

    env = {"A": (0.0, 3.0), "B": (-2.0, 0.0), "C": (2.0, 0.0)}
    step_func(env)

    assert_point_approx(env["H"], (0.0, 4 / 3))


def test_orthocenter_to_ggb():
    args = {"triangle": ["X", "Y", "Z"]}
    ggb_expr = OrthocenterOp.to_ggb(args=args, name="H_node", disambiguation=None)

    assert ggb_expr == "TriangleCenter(X, Y, Z, 4)"


def test_problem_orthocenter_reflection():
    doc_data = {
        "problem_name": "Orthocenter Reflection Theorem",
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
                "args": {"approx_position": [-1, 3]},
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
                "name": "H",
                "type": "Point",
                "method": "Orthocenter",
                "args": {"triangle": ["A", "B", "C"]},
            },
            {
                "name": "Line_BC",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["B", "C"]},
                "hidden": True,
            },
            {
                "name": "H_refl",
                "type": "Point",
                "method": "Reflection",
                "args": {"target": "H", "axis": "Line_BC"},
            },
            {
                "name": "Circ_ABC",
                "type": "Circle",
                "method": "Circumcircle",
                "args": {"triangle": ["A", "B", "C"]},
            },
        ],
        "goals": [
            {"type": "Belongs", "args": {"point": "H_refl", "object": "Circ_ABC"}}
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "DrawSegment", "endpoints": ["H", "H_refl"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать невырожденную конфигурацию треугольника"

    center, radius = env["Circ_ABC"]
    pt_h_refl = env["H_refl"]

    distance_to_center = dist(pt_h_refl, center)
    assert distance_to_center == pytest.approx(radius, abs=1e-8), (
        f"Теорема не подтвердилась: расстояние {distance_to_center:.6f} не равно радиусу {radius:.6f}"
    )

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)
    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0, "Транслятор не сгенерировал GGB-код для целей"
    assert any(inst.ggb_type == "conic" for inst in goal_instructions)
    assert any(inst.ggb_type == "point" for inst in goal_instructions)

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "orthocenter_reflection.ggb")

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
        f"\n[+] Файл отражения ортоцентра успешно сохранен: {os.path.abspath(output_path)}"
    )
    assert os.path.exists(output_path), "Файл .ggb не был записан на диск"
