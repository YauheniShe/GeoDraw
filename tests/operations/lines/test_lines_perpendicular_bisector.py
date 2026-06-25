import math
import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.models import GeoDraftDocument
from compiler.operations.lines import PerpendicularBisectorOp


def assert_line_approx(line1, line2, abs_tol=1e-7):
    """
    Вспомогательный метод для сравнения двух прямых.
    Прямые в math_lib представляются кортежем коэффициентов (a, b, c) уравнения ax + by + c = 0.
    Поскольку они нормализованы (a^2 + b^2 = 1), они могут отличаться только знаком.
    """
    if (line1[0] * line2[0] + line1[1] * line2[1]) < 0:
        line2 = (-line2[0], -line2[1], -line2[2])

    assert line1[0] == pytest.approx(line2[0], abs=abs_tol)
    assert line1[1] == pytest.approx(line2[1], abs=abs_tol)
    assert line1[2] == pytest.approx(line2[2], abs=abs_tol)


def test_perpendicular_bisector_compile_sample():
    """
    Юнит-тест для PerpendicularBisector.compile_sample.
    Выберем отрезок с концами A(0, 0) и B(4, 2).
    - Середина отрезка M(2, 1).
    - Направляющий вектор AB равен (4, 2). Угловой коэффициент k = 0.5.
    - Перпендикулярный угловой коэффициент k_perp = -2.
    - Уравнение серединного перпендикуляра: y - 1 = -2(x - 2) => 2x + y - 5 = 0.
    - В нормализованном виде (коэффициенты делятся на sqrt(5)):
      a = 2/sqrt(5), b = 1/sqrt(5), c = -5/sqrt(5).
    """
    args = {"points": ["A", "B"]}
    step_func = PerpendicularBisectorOp.compile_sample(
        args=args, name="PB", disambiguation=None
    )

    env = {"A": (0.0, 0.0), "B": (4.0, 2.0)}
    step_func(env)

    sqrt_5 = math.sqrt(5.0)
    expected_line = (2.0 / sqrt_5, 1.0 / sqrt_5, -5.0 / sqrt_5)

    assert_line_approx(env["PB"], expected_line)


def test_perpendicular_bisector_to_ggb():
    """Юнит-тест трансляции метода PerpendicularBisector в синтаксис GeoGebra"""
    args = {"points": ["A", "B"]}
    ggb_expr = PerpendicularBisectorOp.to_ggb(args=args, name="PB_AB")

    assert ggb_expr == "PerpendicularBisector(A, B)"


def test_problem_perpendicular_bisectors_concurrency():
    """
    E2E-тест: Доказывает теорему о конкурентности (пересечении в одной точке)
    трех серединных перпендикуляров к сторонам произвольного треугольника ABC.
    Экспортирует результат в tests_output/perpendicular_bisectors_concurrency.ggb.
    """
    doc_data = {
        "problem_name": "Triangle Perpendicular Bisectors Concurrency",
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
                "name": "PB_AB",
                "type": "Line",
                "method": "PerpendicularBisector",
                "args": {"points": ["A", "B"]},
            },
            {
                "name": "PB_BC",
                "type": "Line",
                "method": "PerpendicularBisector",
                "args": {"points": ["B", "C"]},
            },
            {
                "name": "PB_CA",
                "type": "Line",
                "method": "PerpendicularBisector",
                "args": {"points": ["C", "A"]},
            },
        ],
        "goals": [
            {"type": "Concurrent", "args": {"objects": ["PB_AB", "PB_BC", "PB_CA"]}}
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "Show", "targets": ["PB_AB", "PB_BC", "PB_CA"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать корректную конфигурацию треугольника"

    l1 = env["PB_AB"]
    l2 = env["PB_BC"]
    l3 = env["PB_CA"]

    det = l1[0] * l2[1] - l2[0] * l1[1]
    assert abs(det) > 1e-9, (
        "Серединные перпендикуляры параллельны (чего не может быть для невырожденного треугольника)"
    )

    intersection_x = (l1[1] * l2[2] - l2[1] * l1[2]) / det
    intersection_y = (l1[2] * l2[0] - l2[2] * l1[0]) / det
    residual = l3[0] * intersection_x + l3[1] * intersection_y + l3[2]

    assert abs(residual) < 1e-8, (
        f"Теорема не подтвердилась: точка пересечения не лежит на третьей прямой. Невязка: {residual}"
    )

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)
    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0, "Транслятор не сгенерировал GGB-код для целей"

    assert any(inst.ggb_type == "point" for inst in goal_instructions)
    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "perpendicular_bisectors_concurrency.ggb")

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
        f"\n[+] Сценарий пересечения серединных перпендикуляров успешно сохранен в: {output_path}"
    )
    assert os.path.exists(output_path), "Файл .ggb не был создан на диске"
