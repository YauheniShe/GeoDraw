import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.models import GeoDraftDocument
from compiler.operations.lines import PolarLineOp


def assert_point_approx(pt1, pt2, abs_tol=1e-7):
    assert pt1[0] == pytest.approx(pt2[0], abs=abs_tol)
    assert pt1[1] == pytest.approx(pt2[1], abs=abs_tol)


def assert_line_approx(l1, l2, abs_tol=1e-7):
    """
    Сравнение двух прямых (a, b, c). Поскольку коэффициенты нормализованы,
    вектор нормали (a, b) имеет единичную длину. Прямые совпадают,
    если l1 ≈ l2 или l1 ≈ -l2.
    """
    if (l1[0] * l2[0] + l1[1] * l2[1]) < 0:
        l2 = (-l2[0], -l2[1], -l2[2])
    assert l1[0] == pytest.approx(l2[0], abs=abs_tol)
    assert l1[1] == pytest.approx(l2[1], abs=abs_tol)
    assert l1[2] == pytest.approx(l2[2], abs=abs_tol)


def test_polar_line_outside_circle():
    """
    Полюс лежит снаружи окружности.
    Окружность x^2 + y^2 = 25 (центр (0,0), R=5).
    Полюс P(10, 0).
    Поляра должна иметь уравнение x = 2.5 (коэффициенты: 1*x + 0*y - 2.5 = 0).
    """
    args = {"point": "P", "object": "C"}
    step = PolarLineOp.compile_sample(args, "L", disambiguation=None)

    env = {"C": ((0.0, 0.0), 5.0), "P": (10.0, 0.0)}
    step(env)
    assert_line_approx(env["L"], (1.0, 0.0, -2.5))


def test_polar_line_on_boundary():
    """
    Полюс лежит на окружности.
    Окружность x^2 + y^2 = 25. Полюс P(5, 0).
    Поляра должна быть касательной к окружности в этой точке: x = 5 (1*x + 0*y - 5 = 0).
    """
    args = {"point": "P", "object": "C"}
    step = PolarLineOp.compile_sample(args, "L", disambiguation=None)

    env = {"C": ((0.0, 0.0), 5.0), "P": (5.0, 0.0)}
    step(env)
    assert_line_approx(env["L"], (1.0, 0.0, -5.0))


def test_polar_line_inside_circle():
    """
    Полюс лежит внутри окружности.
    Окружность x^2 + y^2 = 25. Полюс P(2.5, 0).
    Поляра должна быть прямой x = 10 (1*x + 0*y - 10 = 0).
    """
    args = {"point": "P", "object": "C"}
    step = PolarLineOp.compile_sample(args, "L", disambiguation=None)

    env = {"C": ((0.0, 0.0), 5.0), "P": (2.5, 0.0)}
    step(env)
    assert_line_approx(env["L"], (1.0, 0.0, -10.0))


def test_polar_line_center_error():
    """
    Полюс в центре окружности.
    Поляра не определена, должен выбрасываться ValueError для корректного сброса семплера.
    """
    args = {"point": "P", "object": "C"}
    step = PolarLineOp.compile_sample(args, "L", disambiguation=None)

    env = {"C": ((1.0, -2.0), 3.0), "P": (1.0, -2.0)}
    with pytest.raises(ValueError, match="Точка в центре окружности"):
        step(env)


def test_polar_line_to_ggb():
    """Проверка генерации GeoGebra выражения Polar(point, object)"""
    args = {"point": "A", "object": "Circ"}
    expr = PolarLineOp.to_ggb(args, "L", disambiguation=None)
    assert expr == "Polar(A, Circ)"


def test_problem_polar_reciprocity_theorem():
    """
    Интеграционный тест:
    Проверяет теорему о взаимности поляр (La Hire's Reciprocity):
    Пусть P — точка пересечения поляр двух точек A и B относительно окружности C1.
    Тогда поляра точки P является прямой, проходящей через A и B.

    Цели для проверки в компиляторе:
    1. A принадлежит Polar_P.
    2. B принадлежит Polar_P.

    Экспортирует результат в tests_output/lines_polar_line.ggb.
    """
    doc_data = {
        "problem_name": "Polar Reciprocity Theorem",
        "constraints": [
            {
                "type": "Inequality",
                "operator": ">",
                "left": {
                    "type": "MathExpression",
                    "expression": "abs((x(A) - x(O)) * (y(B) - y(O)) - (y(A) - y(O)) * (x(B) - x(O)))",
                    "variables": {"A": "A", "B": "B", "O": "O"},
                },
                "right": {"type": "Number", "value": 1.5},
            }
        ],
        "construction": [
            {
                "name": "O",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [0, 0]},
                "hidden": True,
            },
            {
                "name": "C1",
                "type": "Circle",
                "method": "CenterRadius",
                "args": {"center": "O", "radius": {"type": "Number", "value": 4.0}},
            },
            {
                "name": "A",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [5, 2]},
            },
            {
                "name": "B",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [2, 6]},
            },
            {
                "name": "Polar_A",
                "type": "Line",
                "method": "PolarLine",
                "args": {"point": "A", "object": "C1"},
            },
            {
                "name": "Polar_B",
                "type": "Line",
                "method": "PolarLine",
                "args": {"point": "B", "object": "C1"},
            },
            {
                "name": "P",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Polar_A", "obj2": "Polar_B"},
            },
            {
                "name": "Polar_P",
                "type": "Line",
                "method": "PolarLine",
                "args": {"point": "P", "object": "C1"},
            },
        ],
        "goals": [
            {"type": "Belongs", "args": {"point": "A", "object": "Polar_P"}},
            {"type": "Belongs", "args": {"point": "B", "object": "Polar_P"}},
        ],
        "view": [
            {"action": "Show", "targets": ["C1", "Polar_A", "Polar_B", "Polar_P"]},
            {"action": "DrawSegment", "endpoints": ["A", "B"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать невырожденную конфигурацию для поляр"

    a, b, c = env["Polar_P"]

    for pt_name in ["A", "B"]:
        x, y = env[pt_name]
        residual = a * x + b * y + c
        assert abs(residual) < 1e-8, (
            f"Теорема взаимности не сошлась для точки {pt_name}: погрешность {residual:.8f}"
        )

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0, "Транслятор не сгенерировал GGB-код для целей"

    assert any(inst.ggb_type == "line" for inst in goal_instructions)
    assert any(inst.ggb_type == "point" for inst in goal_instructions)

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "lines_polar_line.ggb")

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
        f"\n[+] Интерактивный файл теоремы о взаимности поляр успешно сохранен: {os.path.abspath(output_path)}"
    )
    assert os.path.exists(output_path), "Файл .ggb не был сохранен на диске"
