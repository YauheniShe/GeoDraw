import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import dist
from compiler.models import GeoDraftDocument
from compiler.operations.points import IsogonalConjugateOp


def assert_point_approx(pt1, pt2, abs_tol=1e-7):
    assert pt1[0] == pytest.approx(pt2[0], abs=abs_tol)
    assert pt1[1] == pytest.approx(pt2[1], abs=abs_tol)


def test_isogonal_conjugate_compile_sample():

    args = {"point": "I", "triangle": ["A", "B", "C"]}
    step_func = IsogonalConjugateOp.compile_sample(
        args=args, name="I_isog", disambiguation=None
    )

    env = {"A": (0.0, 4.0), "B": (0.0, 0.0), "C": (3.0, 0.0), "I": (1.0, 1.0)}
    step_func(env)

    assert_point_approx(env["I_isog"], (1.0, 1.0))


def test_isogonal_conjugate_to_ggb():
    args = {"point": "P", "triangle": ["A", "B", "C"]}
    ggb_expr = IsogonalConjugateOp.to_ggb(args=args, name="P_isog", disambiguation=None)

    assert "Line(A, P)" in ggb_expr
    assert "AngleBisector(B, A, C)" in ggb_expr
    assert "Line(B, P)" in ggb_expr
    assert "AngleBisector(A, B, C)" in ggb_expr
    assert ggb_expr.startswith("Intersect(")


def test_problem_isogonal_orthocenter_circumcenter():
    """
    Интеграционный тест:
    Доказывает, что изогональное сопряжение ортоцентра H (H_isog) совпадает
    с центром описанной окружности O (Circumcenter).
    Экспортирует чертеж в tests_output/isogonal_conjugate_euler.ggb.
    """
    doc_data = {
        "problem_name": "Isogonal Conjugate of Orthocenter",
        "constraints": [
            {
                "type": "Inequality",
                "operator": ">",
                "left": {
                    "type": "MathExpression",
                    "expression": "abs(x(A)*(y(B) - y(C)) + x(B)*(y(C) - y(A)) + x(C)*(y(A) - y(B)))",
                    "variables": {"A": "A", "B": "B", "C": "C"},
                },
                "right": {"type": "Number", "value": 1.5},
            }
        ],
        "construction": [
            {
                "name": "A",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [0, 4]},
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
                "name": "O",
                "type": "Point",
                "method": "Circumcenter",
                "args": {"triangle": ["A", "B", "C"]},
            },
            {
                "name": "H_isog",
                "type": "Point",
                "method": "IsogonalConjugate",
                "args": {"point": "H", "triangle": ["A", "B", "C"]},
            },
        ],
        "goals": [
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "Distance", "points": ["H_isog", "O"]},
                        {"type": "Number", "value": 0.0},
                    ]
                },
            }
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "DrawSegment", "endpoints": ["H_isog", "O"]},
            {"action": "Show", "targets": ["H", "O", "H_isog"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать невырожденную конфигурацию треугольника"

    h_isog_pt = env["H_isog"]
    o_pt = env["O"]

    distance_between = dist(h_isog_pt, o_pt)
    assert distance_between == pytest.approx(0.0, abs=1e-8), (
        f"Теорема не подтвердилась: расстояние между изогональным сопряжением ортоцентра и описанным центром равно {distance_between:.6f} (ожидался 0)"
    )

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0, "Транслятор не сгенерировал GGB-код для целей"

    assert any(inst.ggb_type == "segment" for inst in goal_instructions)

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "isogonal_conjugate_euler.ggb")

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
        f"\n[+] Чертеж изогонального сопряжения успешно сохранен: {os.path.abspath(output_path)}"
    )
    assert os.path.exists(output_path), "Файл .ggb не был записан на диск"
