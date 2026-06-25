import os
from unittest.mock import patch

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import get_line_eq
from compiler.models import GeoDraftDocument
from compiler.operations.points import FreePointOp


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


@patch("random.uniform")
def test_free_point_without_approx(mock_uniform):
    mock_uniform.return_value = 1.0
    step_func = FreePointOp.compile_sample(args=None, name="A", disambiguation=None)
    env = {}
    step_func(env)
    assert env["A"] == pytest.approx((2.0, 2.0))
    assert mock_uniform.call_count == 4


@patch("random.uniform")
def test_free_point_with_approx(mock_uniform):
    mock_uniform.return_value = 0.5
    args = {"approx_position": [10.0, -5.0]}
    step_func = FreePointOp.compile_sample(args=args, name="B", disambiguation=None)
    env = {}
    step_func(env)
    assert env["B"] == pytest.approx((10.5, -4.5))
    assert mock_uniform.call_count == 2


def test_free_point_to_ggb_with_sampled_state():
    sampled_state = {"C": (3.14159, -2.71828)}
    ggb_expr = FreePointOp.to_ggb(
        args=None, name="C", disambiguation=None, sampled_state=sampled_state
    )
    assert ggb_expr == "(3.142, -2.718)"


def test_free_point_to_ggb_without_sampled_state():
    args = {"approx_position": [5.5, 6.6]}
    ggb_expr = FreePointOp.to_ggb(
        args=args, name="D", disambiguation=None, sampled_state=None
    )
    assert ggb_expr == "(5.5, 6.6)"


def test_problem_varignon_theorem():
    """
    Теорема Вариньона: Середины сторон любого четырехугольника
    образуют параллелограмм (противоположные стороны равны).
    Экспортирует результат в tests_output/varignon_theorem.ggb.
    """
    doc_data = {
        "problem_name": "Varignon's Theorem",
        "constraints": [],
        "construction": [
            {
                "name": "A",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [-3, -2]},
            },
            {
                "name": "B",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [-1, 4]},
            },
            {
                "name": "C",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [5, 3]},
            },
            {
                "name": "D",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [3, -3]},
            },
            {
                "name": "M1",
                "type": "Point",
                "method": "Midpoint",
                "args": {"points": ["A", "B"]},
            },
            {
                "name": "M2",
                "type": "Point",
                "method": "Midpoint",
                "args": {"points": ["B", "C"]},
            },
            {
                "name": "M3",
                "type": "Point",
                "method": "Midpoint",
                "args": {"points": ["C", "D"]},
            },
            {
                "name": "M4",
                "type": "Point",
                "method": "Midpoint",
                "args": {"points": ["D", "A"]},
            },
            {
                "name": "Line_M1M2",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["M1", "M2"]},
            },
            {
                "name": "Line_M3M4",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["M3", "M4"]},
            },
            {
                "name": "Line_M2M3",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["M2", "M3"]},
            },
            {
                "name": "Line_M1M4",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["M1", "M4"]},
            },
        ],
        "goals": [
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "Distance", "points": ["M1", "M2"]},
                        {"type": "Distance", "points": ["M3", "M4"]},
                    ]
                },
            },
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "Distance", "points": ["M2", "M3"]},
                        {"type": "Distance", "points": ["M1", "M4"]},
                    ]
                },
            },
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C", "D"]},
            {"action": "DrawPolygon", "vertices": ["M1", "M2", "M3", "M4"]},
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
    output_path = os.path.join(output_dir, "varignon_theorem.ggb")

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
