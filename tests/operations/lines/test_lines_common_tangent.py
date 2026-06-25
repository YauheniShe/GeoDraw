import math
import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.models import GeoDraftDocument
from compiler.operations.lines import CommonTangentOp


def assert_is_tangent(line, circle, abs_tol=1e-7):
    """
    Математическая проверка того, что прямая line (a, b, c)
    является касательной к окружности circle ((xc, yc), radius).
    Расстояние от центра окружности до прямой должно быть строго равно ее радиусу.
    """
    a, b, c = line
    (xc, yc), r = circle
    norm = math.hypot(a, b)
    assert norm > 1e-9, "Вектор нормали прямой вырожден"
    dist_to_line = abs(a * xc + b * yc + c) / norm
    assert dist_to_line == pytest.approx(r, abs=abs_tol)


def test_common_tangent_external_compile():
    """Тест построения внешних касательных для окружностей разных радиусов"""
    args = {"circle1": "C1", "circle2": "C2"}

    env = {"C1": ((0.0, 0.0), 1.0), "C2": ((4.0, 0.0), 2.0)}

    step_ext1 = CommonTangentOp.compile_sample(
        args, "T1", {"rule": "tangent_direction", "value": "external", "index": 1}
    )
    step_ext1(env)
    assert_is_tangent(env["T1"], env["C1"])
    assert_is_tangent(env["T1"], env["C2"])

    step_ext2 = CommonTangentOp.compile_sample(
        args, "T2", {"rule": "tangent_direction", "value": "external", "index": 2}
    )
    step_ext2(env)
    assert_is_tangent(env["T2"], env["C1"])
    assert_is_tangent(env["T2"], env["C2"])

    assert env["T1"] != pytest.approx(env["T2"])


def test_common_tangent_internal_compile():
    """Тест построения внутренних касательных для непересекающихся окружностей"""
    args = {"circle1": "C1", "circle2": "C2"}
    env = {"C1": ((0.0, 0.0), 1.0), "C2": ((4.0, 0.0), 1.0)}

    step_int1 = CommonTangentOp.compile_sample(
        args, "T1", {"rule": "tangent_direction", "value": "internal", "index": 1}
    )
    step_int1(env)
    assert_is_tangent(env["T1"], env["C1"])
    assert_is_tangent(env["T1"], env["C2"])

    step_int2 = CommonTangentOp.compile_sample(
        args, "T2", {"rule": "tangent_direction", "value": "internal", "index": 2}
    )
    step_int2(env)
    assert_is_tangent(env["T2"], env["C1"])
    assert_is_tangent(env["T2"], env["C2"])

    assert env["T1"] != pytest.approx(env["T2"])


def test_common_tangent_invalid_cases():
    """Проверка генерации ошибок при невозможности построить касательные (отсев некорректных чертежей)"""
    args = {"circle1": "C1", "circle2": "C2"}

    env_concentric = {"C1": ((0.0, 0.0), 1.0), "C2": ((0.0, 0.0), 2.0)}
    step = CommonTangentOp.compile_sample(args, "T", None)
    with pytest.raises(ValueError, match="Касательные не найдены"):
        step(env_concentric)

    env_inside = {"C1": ((0.0, 0.0), 3.0), "C2": ((1.0, 0.0), 1.0)}
    with pytest.raises(ValueError, match="Касательные не найдены"):
        step(env_inside)

    env_intersecting = {
        "C1": ((0.0, 0.0), 2.0),
        "C2": ((3.0, 0.0), 2.0),
    }
    step_internal = CommonTangentOp.compile_sample(
        args, "T", {"rule": "tangent_direction", "value": "internal", "index": 1}
    )
    with pytest.raises(ValueError, match="Касательные не найдены"):
        step_internal(env_intersecting)


def test_common_tangent_to_ggb():
    """Тест трансляции метода CommonTangent в синтаксис GeoGebra для разных правил disambiguation"""
    args = {"circle1": "CircA", "circle2": "CircB"}

    disamb_dir = {"rule": "tangent_direction", "value": "external", "index": 2}
    expr_dir = CommonTangentOp.to_ggb(args, "T", disamb_dir)
    assert expr_dir == "Element({Tangent(CircA, CircB)}, 2)"

    disamb_alg = {"rule": "algebraic_index", "algebraic_index": 1}
    expr_alg = CommonTangentOp.to_ggb(args, "T", disamb_alg)
    assert expr_alg == "Element({Tangent(CircA, CircB)}, 1)"


def test_problem_monges_three_circles_theorem():
    """
    Интеграционный тест: Теорема Монжа о трех окружностях.
    Строит три непересекающиеся окружности разных радиусов,
    находит пересечения внешних касательных для каждой пары окружностей (X, Y, Z)
    и доказывает их коллинеарность.
    Результат сохраняется в tests_output/monges_theorem.ggb.
    """
    doc_data = {
        "problem_name": "Monge Three Circles Theorem",
        "constraints": [
            {
                "type": "Inequality",
                "operator": ">",
                "left": {"type": "Distance", "points": ["A", "B"]},
                "right": {"type": "Number", "value": 3.0},
            },
            {
                "type": "Inequality",
                "operator": ">",
                "left": {"type": "Distance", "points": ["B", "C"]},
                "right": {"type": "Number", "value": 4.5},
            },
            {
                "type": "Inequality",
                "operator": ">",
                "left": {"type": "Distance", "points": ["C", "A"]},
                "right": {"type": "Number", "value": 4.5},
            },
        ],
        "construction": [
            {
                "name": "A",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [0, 0]},
            },
            {
                "name": "B",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [5, 0]},
            },
            {
                "name": "C",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [2, 5]},
            },
            {
                "name": "C1",
                "type": "Circle",
                "method": "CenterRadius",
                "args": {"center": "A", "radius": {"type": "Number", "value": 0.5}},
            },
            {
                "name": "C2",
                "type": "Circle",
                "method": "CenterRadius",
                "args": {"center": "B", "radius": {"type": "Number", "value": 1.0}},
            },
            {
                "name": "C3",
                "type": "Circle",
                "method": "CenterRadius",
                "args": {"center": "C", "radius": {"type": "Number", "value": 1.5}},
            },
            {
                "name": "T12_1",
                "type": "Line",
                "method": "CommonTangent",
                "args": {"circle1": "C1", "circle2": "C2"},
                "disambiguation": {
                    "rule": "tangent_direction",
                    "value": "external",
                    "index": 1,
                },
            },
            {
                "name": "T12_2",
                "type": "Line",
                "method": "CommonTangent",
                "args": {"circle1": "C1", "circle2": "C2"},
                "disambiguation": {
                    "rule": "tangent_direction",
                    "value": "external",
                    "index": 2,
                },
            },
            {
                "name": "X",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "T12_1", "obj2": "T12_2"},
            },
            {
                "name": "T23_1",
                "type": "Line",
                "method": "CommonTangent",
                "args": {"circle1": "C2", "circle2": "C3"},
                "disambiguation": {
                    "rule": "tangent_direction",
                    "value": "external",
                    "index": 1,
                },
            },
            {
                "name": "T23_2",
                "type": "Line",
                "method": "CommonTangent",
                "args": {"circle1": "C2", "circle2": "C3"},
                "disambiguation": {
                    "rule": "tangent_direction",
                    "value": "external",
                    "index": 2,
                },
            },
            {
                "name": "Y",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "T23_1", "obj2": "T23_2"},
            },
            {
                "name": "T31_1",
                "type": "Line",
                "method": "CommonTangent",
                "args": {"circle1": "C3", "circle2": "C1"},
                "disambiguation": {
                    "rule": "tangent_direction",
                    "value": "external",
                    "index": 1,
                },
            },
            {
                "name": "T31_2",
                "type": "Line",
                "method": "CommonTangent",
                "args": {"circle1": "C3", "circle2": "C1"},
                "disambiguation": {
                    "rule": "tangent_direction",
                    "value": "external",
                    "index": 2,
                },
            },
            {
                "name": "Z",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "T31_1", "obj2": "T31_2"},
            },
        ],
        "goals": [{"type": "Collinear", "args": {"points": ["X", "Y", "Z"]}}],
        "view": [
            {
                "action": "Show",
                "targets": [
                    "C1",
                    "C2",
                    "C3",
                    "T12_1",
                    "T12_2",
                    "T23_1",
                    "T23_2",
                    "T31_1",
                    "T31_2",
                ],
            },
            {"action": "DrawSegment", "endpoints": ["X", "Y"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать конфигурацию непересекающихся окружностей"

    px, py, pz = env["X"], env["Y"], env["Z"]

    area = abs(
        px[0] * (py[1] - pz[1]) + py[0] * (pz[1] - px[1]) + pz[0] * (px[1] - py[1])
    )
    assert area == pytest.approx(0.0, abs=1e-7), (
        f"Теорема Монжа провалена: ориентированная площадь треугольника XYZ {area:.6f} не равна нулю"
    )

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0, "Транслятор не сгенерировал GGB-код для целей"

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "monges_theorem.ggb")

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
        f"\n[+] Теорема Монжа о трех окружностях успешно сохранена: {os.path.abspath(output_path)}"
    )
    assert os.path.exists(output_path), "Файл .ggb не был создан на диске"
