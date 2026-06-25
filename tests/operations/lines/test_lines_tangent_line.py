import math
import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import dist
from compiler.models import GeoDraftDocument
from compiler.operations.lines import TangentLineOp


def assert_line_approx(line1, line2, abs_tol=1e-7):
    factor = 1.0 if (line1[0] * line2[0] + line1[1] * line2[1]) > 0 else -1.0
    assert line1[0] == pytest.approx(factor * line2[0], abs=abs_tol)
    assert line1[1] == pytest.approx(factor * line2[1], abs=abs_tol)
    assert line1[2] == pytest.approx(factor * line2[2], abs=abs_tol)


def test_tangent_line_compile_multiple_names():
    """Тестирование множественного возврата обеих касательных за один шаг"""
    args = {"point": "P", "object": "Circ"}

    # Задаем имена массивом
    step = TangentLineOp.compile_sample(args, ["Tangent_A", "Tangent_B"], None)

    env = {"P": (13.0, 0.0), "Circ": ((0.0, 0.0), 5.0)}
    step(env)

    # Должны успешно рассчитаться обе касательные
    assert "Tangent_A" in env
    assert "Tangent_B" in env
    assert dist(env["P"], (0, 0)) == pytest.approx(13.0)

    # Проверяем, что обе прямые касаются окружности (расстояние до центра = 5.0)
    for t_name in ["Tangent_A", "Tangent_B"]:
        a, b, c = env[t_name]
        d = abs(c) / math.hypot(a, b)
        assert d == pytest.approx(5.0, abs=1e-7)


def test_tangent_line_disambiguation_closest():
    """Тестирование выбора касательной, которая ближе к ориентиру T"""
    args = {"point": "P", "object": "Circ"}
    disamb = {"rule": "closest_to", "target": "T"}

    step = TangentLineOp.compile_sample(args, "Tangent_Chosen", disamb)

    # Касательные точки: (0, 5) и (0, -5) для P(5, 5) и Circ((0,0), R=5)
    # Ориентир T(0, 10) находится ближе к верхней касательной точке (0, 5)
    env = {"P": (5.0, 5.0), "Circ": ((0.0, 0.0), 5.0), "T": (0.0, 10.0)}
    step(env)

    # Ожидаем горизонтальную верхнюю касательную y = 5 (коэффициенты: 0*x + 1*y - 5 = 0)
    a, b, c = env["Tangent_Chosen"]
    norm = math.hypot(a, b)
    assert abs(a / norm) == pytest.approx(0.0, abs=1e-7)
    assert abs(b / norm) == pytest.approx(1.0, abs=1e-7)
    assert abs(c / norm) == pytest.approx(5.0, abs=1e-7)


def test_tangent_line_disambiguation_side_of_line():
    """Тестирование выбора касательной по знаку полуплоскости"""
    args = {"point": "P", "object": "Circ"}
    disamb = {"rule": "same_side_of_line", "line": "X_Axis", "point": "Ref"}

    step = TangentLineOp.compile_sample(args, "Tangent_Chosen", disamb)

    # Точки касания: (0, 5) и (0, -5). X_Axis - это прямая y = 0.
    # Референсная точка Ref(0, 100) лежит в верхней полуплоскости (y > 0).
    env = {
        "P": (5.0, 5.0),
        "Circ": ((0.0, 0.0), 5.0),
        "X_Axis": (0, 1, 0),
        "Ref": (0.0, 100.0),
    }
    step(env)

    # Должна быть выбрана верхняя касательная (точка касания (0, 5) лежит выше оси X)
    a, b, c = env["Tangent_Chosen"]
    norm = math.hypot(a, b)
    assert abs(c / norm) == pytest.approx(5.0, abs=1e-7)


def test_tangent_line_compile_point_on_boundary():
    args = {"point": "P", "object": "Circ"}
    step = TangentLineOp.compile_sample(args, "T", None)

    env = {"P": (5.0, 0.0), "Circ": ((0.0, 0.0), 5.0)}
    step(env)

    a, b, c = env["T"]
    norm = math.hypot(a, b)
    assert abs(a / norm) == pytest.approx(1.0, abs=1e-7)
    assert abs(c / norm) == pytest.approx(5.0, abs=1e-7)


def test_tangent_line_compile_internal_point():
    args = {"point": "P", "object": "Circ"}
    step = TangentLineOp.compile_sample(args, "T", None)

    env = {"P": (2.0, 0.0), "Circ": ((0.0, 0.0), 5.0)}
    with pytest.raises(ValueError, match="Касательные не найдены"):
        step(env)


def test_tangent_line_to_ggb():
    args = {"point": "P", "object": "Circ"}
    ggb_expr = TangentLineOp.to_ggb(
        args, "T", {"rule": "algebraic_index", "index": 2}, None
    )
    assert ggb_expr == "Element({Tangent(P, Circ)}, 2)"


def test_problem_tangent_secant_theorem():
    """
    Интеграционный End-to-End тест:
    Доказывает теорему о касательной и секущей (PT^2 = PA * PB)
    """
    doc_data = {
        "problem_name": "Tangent Secant Theorem",
        "constraints": [
            {
                "type": "Inequality",
                "operator": ">",
                "left": {"type": "Distance", "points": ["P", "O"]},
                "right": {"type": "Number", "value": 5.0},
            }
        ],
        "construction": [
            {
                "name": "O",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [0, 0]},
            },
            {
                "name": "C",
                "type": "Circle",
                "method": "CenterRadius",
                "args": {"center": "O", "radius": {"type": "Number", "value": 3.0}},
            },
            {
                "name": "P",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [6, 1]},
            },
            {
                "name": "Tangent_P",
                "type": "Line",
                "method": "TangentLine",
                "args": {"point": "P", "object": "C"},
                "disambiguation": {"rule": "algebraic_index", "index": 1},
            },
            {
                "name": "T",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Tangent_P", "obj2": "C"},
            },
            {
                "name": "A",
                "type": "Point",
                "method": "PointOnObject",
                "args": {"object": "C"},
            },
            {
                "name": "Secant_P",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["P", "A"]},
                "hidden": True,
            },
            {
                "name": "B",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Secant_P", "obj2": "C"},
                "disambiguation": {"rule": "not_equal", "target": "A"},
            },
        ],
        "goals": [
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {
                            "type": "MathExpression",
                            "expression": "d_PT * d_PT",
                            "variables": {
                                "d_PT": {"type": "Distance", "points": ["P", "T"]}
                            },
                        },
                        {
                            "type": "MathExpression",
                            "expression": "d_PA * d_PB",
                            "variables": {
                                "d_PA": {"type": "Distance", "points": ["P", "A"]},
                                "d_PB": {"type": "Distance", "points": ["P", "B"]},
                            },
                        },
                    ]
                },
            }
        ],
        "view": [
            {"action": "Show", "targets": ["C", "Tangent_P"]},
            {"action": "Clip", "target": "Tangent_P", "endpoints": ["P", "T"]},
            {"action": "DrawSegment", "endpoints": ["P", "B"]},
            {"action": "DrawSegment", "endpoints": ["O", "T"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать конфигурацию для теоремы о секущей"

    d_pt_sq = dist(env["P"], env["T"]) ** 2
    d_pa_pb = dist(env["P"], env["A"]) * dist(env["P"], env["B"])
    assert d_pt_sq == pytest.approx(d_pa_pb, abs=1e-7), (
        f"{d_pt_sq:.6f} != {d_pa_pb:.6f}"
    )

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) == 2

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "tangent_secant_theorem.ggb")

    original_types = {obj.name: obj.type for obj in doc.construction if obj.name}
    generator = GeoDraftGenerator(config=GeoDrawConfig())
    generator.create_ggb(project, original_types, output_path)
