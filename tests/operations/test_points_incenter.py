import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import dist
from compiler.models import GeoDraftDocument
from compiler.operations.points import IncenterOp


def assert_goals(doc: GeoDraftDocument, env: dict):
    for goal in doc.goals:
        g_type = goal.type
        args = goal.args

        if g_type == "Equal":
            vals = args["values"]
            p1, p2 = vals[0]["points"]
            p3, p4 = vals[1]["points"]
            d1 = dist(env[p1], env[p2])
            d2 = dist(env[p3], env[p4])
            assert d1 == pytest.approx(d2, abs=1e-7), (
                f"Равенство расстояний провалено: {d1:.6f} != {d2:.6f}"
            )


def test_incenter_compile_sample():
    """Проверка математического вычисления инцентра на прямоугольном треугольнике 3-4-5"""
    args = {"triangle": ["A", "B", "C"]}
    step_func = IncenterOp.compile_sample(args=args, name="I", disambiguation=None)

    env = {"A": (0.0, 0.0), "B": (3.0, 0.0), "C": (0.0, 4.0)}
    step_func(env)
    assert env["I"][0] == pytest.approx(1.0, abs=1e-7)
    assert env["I"][1] == pytest.approx(1.0, abs=1e-7)


def test_incenter_to_ggb():
    """Проверка генерации GeoGebra-кода для инцентра"""
    args = {"triangle": ["A", "B", "C"]}
    ggb_expr = IncenterOp.to_ggb(args=args, name="I", disambiguation=None)

    assert ggb_expr == "TriangleCenter(A, B, C, 1)"


def test_problem_incenter_equidistant():
    """
    Доказывает равноудаленность инцентра от трех сторон треугольника.
    Экспортирует результат в tests_output/incenter_equidistant.ggb.
    """
    doc_data = {
        "problem_name": "Incenter Equidistance Theorem",
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
                "args": {"approx_position": [1, 3]},
            },
            {
                "name": "I",
                "type": "Point",
                "method": "Incenter",
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
                "name": "Line_CA",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["C", "A"]},
                "hidden": True,
            },
            {
                "name": "Line_AB",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["A", "B"]},
                "hidden": True,
            },
            {
                "name": "D",
                "type": "Point",
                "method": "Projection",
                "args": {"point": "I", "line": "Line_BC"},
            },
            {
                "name": "E",
                "type": "Point",
                "method": "Projection",
                "args": {"point": "I", "line": "Line_CA"},
            },
            {
                "name": "F",
                "type": "Point",
                "method": "Projection",
                "args": {"point": "I", "line": "Line_AB"},
            },
        ],
        "goals": [
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "Distance", "points": ["I", "D"]},
                        {"type": "Distance", "points": ["I", "E"]},
                    ]
                },
            },
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "Distance", "points": ["I", "E"]},
                        {"type": "Distance", "points": ["I", "F"]},
                    ]
                },
            },
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "DrawSegment", "endpoints": ["I", "D"]},
            {"action": "DrawSegment", "endpoints": ["I", "E"]},
            {"action": "DrawSegment", "endpoints": ["I", "F"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать конфигурацию"

    assert_goals(doc, env)

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0, "Транслятор не сгенерировал цели в GGB"

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "incenter_equidistant.ggb")

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

    print(f"\n[+] Файл инцентра успешно сохранен: {os.path.abspath(output_path)}")
    assert os.path.exists(output_path), "Файл .ggb не был записан"
