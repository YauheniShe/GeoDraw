import math
import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import dist
from compiler.models import GeoDraftDocument
from compiler.operations.intersections import IntersectionOp


def assert_point_approx(pt1, pt2, abs_tol=1e-7):
    assert pt1[0] == pytest.approx(pt2[0], abs=abs_tol)
    assert pt1[1] == pytest.approx(pt2[1], abs=abs_tol)


def test_math_line_line_normal():
    """Нормальное пересечение двух перпендикулярных прямых в (2, -3)"""
    args = {"obj1": "L1", "obj2": "L2"}
    step = IntersectionOp.compile_sample(args, "P", disambiguation=None)
    env = {"L1": (1, 0, -2), "L2": (0, 1, 3)}
    step(env)
    assert_point_approx(env["P"], (2.0, -3.0))


def test_math_line_line_parallel():
    """Параллельные прямые — должны вызывать ValueError для сброса семплера"""
    args = {"obj1": "L1", "obj2": "L2"}
    step = IntersectionOp.compile_sample(args, "P", disambiguation=None)
    env = {"L1": (1, 0, -1), "L2": (1, 0, -2)}
    with pytest.raises(ValueError, match="Прямые параллельны"):
        step(env)


def test_math_line_line_coincident():
    """Совпадающие прямые — определитель 0, должны вызывать ValueError"""
    args = {"obj1": "L1", "obj2": "L2"}
    step = IntersectionOp.compile_sample(args, "P", disambiguation=None)
    env = {"L1": (1, -1, 0), "L2": (1, -1, 0)}  # Обе y = x
    with pytest.raises(ValueError, match="Прямые параллельны"):
        step(env)


def test_math_line_circle_two_points():
    """Прямая пересекает окружность в двух точках"""
    args = {"obj1": "L1", "obj2": "C1"}
    step_idx1 = IntersectionOp.compile_sample(
        args, "P", {"rule": "algebraic_index", "index": 1}
    )
    step_idx2 = IntersectionOp.compile_sample(
        args, "P", {"rule": "algebraic_index", "index": 2}
    )

    env = {"L1": (0, 1, 0), "C1": ((0, 0), 2.0)}

    step_idx1(env)
    p1 = env["P"]

    step_idx2(env)
    p2 = env["P"]
    assert dist(p1, p2) == pytest.approx(4.0)
    assert p1[1] == pytest.approx(0.0)
    assert p2[1] == pytest.approx(0.0)


def test_math_line_circle_tangent():
    """Прямая касается окружности (ровно 1 точка пересечения)"""
    args = {"obj1": "L1", "obj2": "C1"}
    step = IntersectionOp.compile_sample(args, "P", disambiguation=None)
    env = {"L1": (1, 0, -2), "C1": ((0, 0), 2.0)}

    step(env)
    assert_point_approx(env["P"], (2.0, 0.0))


def test_math_line_circle_no_intersection():
    """Прямая не пересекает окружность — должна выбрасываться ошибка"""
    args = {"obj1": "L1", "obj2": "C1"}
    step = IntersectionOp.compile_sample(args, "P", disambiguation=None)
    env = {"L1": (1, 0, -5), "C1": ((0, 0), 2.0)}

    with pytest.raises(ValueError, match="Точки пересечения не найдены"):
        step(env)


def test_math_circle_circle_two_points():
    """Пересечение двух окружностей в двух точках"""
    args = {"obj1": "C1", "obj2": "C2"}
    step_idx1 = IntersectionOp.compile_sample(
        args, "P", {"rule": "algebraic_index", "index": 1}
    )
    step_idx2 = IntersectionOp.compile_sample(
        args, "P", {"rule": "algebraic_index", "index": 2}
    )

    env = {"C1": ((0, 0), 2.0), "C2": ((3, 0), 2.0)}

    step_idx1(env)
    p1 = env["P"]

    step_idx2(env)
    p2 = env["P"]

    assert p1[0] == pytest.approx(1.5)
    assert p2[0] == pytest.approx(1.5)
    assert abs(p1[1]) == pytest.approx(math.sqrt(1.75))
    assert p1[1] * p2[1] < 0


def test_math_circle_circle_tangent():
    """Окружности касаются внешним образом (ровно 1 точка)"""
    args = {"obj1": "C1", "obj2": "C2"}
    step = IntersectionOp.compile_sample(args, "P", disambiguation=None)
    env = {"C1": ((0, 0), 1.0), "C2": ((2, 0), 1.0)}

    step(env)
    assert_point_approx(env["P"], (1.0, 0.0))


def test_math_circle_circle_no_intersection():
    """Окружности не пересекаются (слишком далеко друг от друга)"""
    args = {"obj1": "C1", "obj2": "C2"}
    step = IntersectionOp.compile_sample(args, "P", disambiguation=None)
    env = {"C1": ((0, 0), 1.0), "C2": ((5, 0), 1.0)}

    with pytest.raises(ValueError, match="Точки пересечения не найдены"):
        step(env)


def test_disambiguation_not_equal():
    """Исключение тривиального корня (не равен заданной точке)"""
    args = {"obj1": "L1", "obj2": "C1"}
    disamb = {"rule": "not_equal", "target": "A"}
    step = IntersectionOp.compile_sample(args, "P", disamb)

    env = {"L1": (0, 1, 0), "C1": ((0, 0), 1.0), "A": (1.0, 0.0)}
    step(env)
    assert_point_approx(env["P"], (-1.0, 0.0))


def test_disambiguation_side_of_line():
    """Выбор корня в заданной полуплоскости (same_side / opposite_side)"""
    args = {"obj1": "L1", "obj2": "C1"}

    step_same = IntersectionOp.compile_sample(
        args, "P", {"rule": "same_side_of_line", "line": "Line_X", "point": "Ref"}
    )
    step_opp = IntersectionOp.compile_sample(
        args, "P", {"rule": "opposite_side_of_line", "line": "Line_X", "point": "Ref"}
    )

    env = {"L1": (1, 0, 0), "C1": ((0, 0), 1.0), "Line_X": (0, 1, 0), "Ref": (5.0, 5.0)}

    step_same(env)
    assert_point_approx(env["P"], (0.0, 1.0))

    step_opp(env)
    assert_point_approx(env["P"], (0.0, -1.0))


def test_disambiguation_closest_furthest():
    """Выбор ближайшего / наиболее удаленного корня"""
    args = {"obj1": "L1", "obj2": "C1"}
    # Корни (-1,0) и (1,0). Таргет T(10, 0)
    step_close = IntersectionOp.compile_sample(
        args, "P", {"rule": "closest_to", "target": "T"}
    )
    step_far = IntersectionOp.compile_sample(
        args, "P", {"rule": "furthest_from", "target": "T"}
    )

    env = {"L1": (0, 1, 0), "C1": ((0, 0), 1.0), "T": (10.0, 0.0)}

    step_close(env)
    assert_point_approx(env["P"], (1.0, 0.0))

    step_far(env)
    assert_point_approx(env["P"], (-1.0, 0.0))


def test_disambiguation_order_on_line():
    """Задание строгого порядка расположения точек на прямой"""
    args = {"obj1": "L1", "obj2": "C1"}

    disamb = {"rule": "order_on_line", "order": ["Ref1", "Ref2", "P"]}
    step = IntersectionOp.compile_sample(args, "P", disamb)

    env = {
        "L1": (1, -1, 0),
        "C1": ((0, 0), math.sqrt(8)),
        "Ref1": (-3.0, -3.0),
        "Ref2": (-1.0, -1.0),
    }
    step(env)
    assert_point_approx(env["P"], (2.0, 2.0))


def test_disambiguation_inside_circumcircle():
    """Выбор корня строго внутри описанной окружности треугольника"""
    args = {"obj1": "L1", "obj2": "C1"}

    disamb = {"rule": "inside_circumcircle", "triangle": ["T1", "T2", "T3"]}
    step = IntersectionOp.compile_sample(args, "P", disamb)

    env = {
        "L1": (0, 1, 0),
        "C1": ((2.75, 0), 2.25),
        "T1": (0.0, 0.0),
        "T2": (2.0, 0.0),
        "T3": (0.0, 2.0),
    }
    step(env)
    assert_point_approx(env["P"], (0.5, 0.0))


def test_disambiguation_inside_angle():
    """Выбор корня строго внутри заданного угла"""
    args = {"obj1": "L1", "obj2": "C1"}

    disamb = {"rule": "inside_angle", "vertex": "V", "ends": ["E1", "E2"]}
    step = IntersectionOp.compile_sample(args, "P", disamb)

    env = {
        "L1": (1, -1, 0),
        "C1": ((0, 0), math.sqrt(2)),
        "V": (0.0, 0.0),
        "E1": (1.0, 0.0),
        "E2": (0.0, 1.0),
    }
    step(env)
    assert_point_approx(env["P"], (1.0, 1.0))


def test_disambiguation_inside_outside_polygon():
    """Выбор корня внутри / снаружи многоугольника (треугольника)"""
    args = {"obj1": "L1", "obj2": "C1"}

    step_in = IntersectionOp.compile_sample(
        args, "P", {"rule": "inside_polygon", "polygon": ["T1", "T2", "T3"]}
    )
    step_out = IntersectionOp.compile_sample(
        args, "P", {"rule": "outside_polygon", "polygon": ["T1", "T2", "T3"]}
    )

    env = {
        "L1": (1, -1, 0),
        "C1": ((2.5, 2.5), math.sqrt(4.5)),
        "T1": (0.0, 0.0),
        "T2": (3.0, 0.0),
        "T3": (0.0, 3.0),
    }

    step_in(env)
    assert_point_approx(env["P"], (1.0, 1.0))

    step_out(env)
    assert_point_approx(env["P"], (4.0, 4.0))


def test_ggb_translation_linear_objects():
    """Пересечение бесконечных прямых, отрезков, лучей — всегда чистый Intersect"""
    translator = GeoDraftTranslator()
    args = {"obj1": "L1", "obj2": "Seg1"}
    doc_types = {"L1": "Line", "Seg1": "Segment"}

    expr = IntersectionOp.to_ggb(args, "P", None, doc_types, translator)
    assert expr == "Intersect(L1, Seg1)"


def test_ggb_translation_with_not_equal():
    """Трансляция правила 'not_equal'"""
    translator = GeoDraftTranslator()
    args = {"obj1": "C1", "obj2": "L1"}
    disamb = {"rule": "not_equal", "target": "A"}
    doc_types = {"C1": "Circle", "L1": "Line", "A": "Point"}

    expr = IntersectionOp.to_ggb(args, "P", disamb, doc_types, translator)
    assert expr == "If(PI1 == A, PI2, PI1)"
    assert len(translator.instructions) == 2


def test_ggb_translation_with_closest_furthest():
    """Трансляция 'closest_to' / 'furthest_from' в GGB через функцию Distance"""
    translator = GeoDraftTranslator()
    args = {"obj1": "C1", "obj2": "L1"}
    doc_types = {"C1": "Circle", "L1": "Line", "T": "Point"}

    expr_close = IntersectionOp.to_ggb(
        args, "P", {"rule": "closest_to", "target": "T"}, doc_types, translator
    )
    assert expr_close == "If(Distance(PI1, T) < Distance(PI2, T), PI1, PI2)"

    translator.instructions.clear()
    expr_far = IntersectionOp.to_ggb(
        args, "P", {"rule": "furthest_from", "target": "T"}, doc_types, translator
    )
    assert expr_far == "If(Distance(PI1, T) > Distance(PI2, T), PI1, PI2)"


def test_ggb_translation_with_side_of_line():
    """Трансляция полуплоскостей в GGB через скалярное произведение векторов"""
    translator = GeoDraftTranslator()
    args = {"obj1": "C1", "obj2": "L1"}
    disamb = {"rule": "same_side_of_line", "line": "XLine", "point": "RefPt"}
    doc_types = {"C1": "Circle", "L1": "Line", "XLine": "Line", "RefPt": "Point"}

    expr = IntersectionOp.to_ggb(args, "P", disamb, doc_types, translator)
    assert "ClosestPoint(XLine" in expr
    assert "PI1" in expr
    assert "> 0" in expr


def test_problem_incenter_excenter_lemma():
    doc_data = {
        "problem_name": "Incenter-Excenter Lemma",
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
                "args": {"approx_position": [-4, -1]},
            },
            {
                "name": "C",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [3, -1]},
            },
            {
                "name": "Line_BC",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["B", "C"]},
                "hidden": True,
            },
            {
                "name": "Circ_ABC",
                "type": "Circle",
                "method": "Circumcircle",
                "args": {"triangle": ["A", "B", "C"]},
            },
            {
                "name": "Bisector_A",
                "type": "Line",
                "method": "AngleBisector",
                "args": {"vertex": "A", "ends": ["B", "C"]},
                "hidden": True,
            },
            {
                "name": "Bisector_B",
                "type": "Line",
                "method": "AngleBisector",
                "args": {"vertex": "B", "ends": ["A", "C"]},
                "hidden": True,
            },
            {
                "name": "I",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Bisector_A", "obj2": "Bisector_B"},
            },
            {
                "name": "W",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Bisector_A", "obj2": "Circ_ABC"},
                "disambiguation": {
                    "rule": "opposite_side_of_line",
                    "line": "Line_BC",
                    "point": "A",
                },
            },
        ],
        "goals": [
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "Distance", "points": ["W", "B"]},
                        {"type": "Distance", "points": ["W", "I"]},
                    ]
                },
            },
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "Distance", "points": ["W", "C"]},
                        {"type": "Distance", "points": ["W", "I"]},
                    ]
                },
            },
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "Clip", "target": "Bisector_A", "endpoints": ["A", "W"]},
            {"action": "DrawSegment", "endpoints": ["W", "B"]},
            {"action": "DrawSegment", "endpoints": ["W", "C"]},
            {"action": "DrawSegment", "endpoints": ["W", "I"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не подобрал конфигурацию"

    for goal in doc.goals:
        vals = goal.args["values"]
        p1, p2 = vals[0]["points"]
        p3, p4 = vals[1]["points"]
        d1 = dist(env[p1], env[p2])
        d2 = dist(env[p3], env[p4])
        assert abs(d1 - d2) < 1e-8, f"Теорема провалена: {d1:.4f} != {d2:.4f}"

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "incenter_excenter_lemma.ggb")

    original_types = {obj.name: obj.type for obj in doc.construction if obj.name}
    generator = GeoDraftGenerator(config=GeoDrawConfig())
    generator.create_ggb(project, original_types, output_path)

    print(f"\n[+] Лемма о Трезубце успешно сохранена в: {output_path}")
