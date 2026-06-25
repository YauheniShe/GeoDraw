import math
import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.models import GeoDraftDocument
from compiler.operations.lines import SimsonLineOp


def assert_line_approx(l1, l2, abs_tol=1e-7):
    """
    Сравнивает уравнения двух прямых (a, b, c).
    Так как вектор нормали может быть направлен в противоположную сторону,
    мы проверяем оба варианта (совпадение знаков или их инверсию).
    """
    a1, b1, c1 = l1
    a2, b2, c2 = l2

    match_direct = (
        math.isclose(a1, a2, abs_tol=abs_tol)
        and math.isclose(b1, b2, abs_tol=abs_tol)
        and math.isclose(c1, c2, abs_tol=abs_tol)
    )

    match_inverse = (
        math.isclose(a1, -a2, abs_tol=abs_tol)
        and math.isclose(b1, -b2, abs_tol=abs_tol)
        and math.isclose(c1, -c2, abs_tol=abs_tol)
    )

    assert match_direct or match_inverse, f"Прямая {l1} не совпадает с {l2}"


def test_simson_line_compile_sample():
    """
    Юнит-тест математического ядра.
    Возьмем прямоугольный треугольник A(0, 4), B(0, 0), C(3, 0).
    Его описанная окружность имеет центр (1.5, 2) и радиус 2.5.
    Возьмем точку P(3, 4), которая лежит на этой описанной окружности.
    Проекции P на стороны:
    - на AB (ось Y): (0, 4)
    - на BC (ось X): (3, 0)
    Прямая Симсона должна проходить через (0, 4) и (3, 0).
    Уравнение: 4x + 3y - 12 = 0.
    Нормализованный вид: (0.8, 0.6, -2.4).
    """
    args = {"point": "P", "triangle": ["A", "B", "C"]}
    step_func = SimsonLineOp.compile_sample(args=args, name="SimL", disambiguation=None)

    env = {"A": (0.0, 4.0), "B": (0.0, 0.0), "C": (3.0, 0.0), "P": (3.0, 4.0)}

    step_func(env)

    expected_line = (0.8, 0.6, -2.4)
    assert_line_approx(env["SimL"], expected_line)


def test_simson_line_vertex_raises():
    """
    Граничный случай: Если точка P совпадает с вершиной треугольника (например, P = B),
    то её проекции на стороны AB и BC совпадут (это будет сама точка B).
    Построение прямой Симсона должно выбросить ValueError для отсева такой конфигурации.
    """
    args = {"point": "P", "triangle": ["A", "B", "C"]}
    step_func = SimsonLineOp.compile_sample(args=args, name="SimL", disambiguation=None)

    env = {
        "A": (0.0, 4.0),
        "B": (0.0, 0.0),
        "C": (3.0, 0.0),
        "P": (0.0, 0.0),
    }

    with pytest.raises(ValueError, match="Точки для построения прямой совпадают"):
        step_func(env)


def test_simson_line_to_ggb():
    """
    Юнит-тест трансляции в GGB.
    Должен генерировать скрытые точки проекции на две стороны и прямую через них.
    """
    translator = GeoDraftTranslator()
    args = {"point": "P", "triangle": ["A", "B", "C"]}
    expr = SimsonLineOp.to_ggb(args, "SimL", translator)

    assert expr == "Line(proj1_SimL, proj2_SimL)"

    instructions = {inst.name: inst for inst in translator.instructions}
    assert "proj1_SimL" in instructions
    assert "proj2_SimL" in instructions

    assert instructions["proj1_SimL"].expression == "ClosestPoint(Line(A, B), P)"
    assert instructions["proj2_SimL"].expression == "ClosestPoint(Line(B, C), P)"
    assert instructions["proj1_SimL"].hidden is True
    assert instructions["proj2_SimL"].hidden is True


def test_problem_simson_line_and_orthocenter():
    """
    Интеграционный тест классической теоремы:
    Прямая Симсона точки P делит пополам отрезок между точкой P и ортоцентром H.
    (Т.е. середина PH принадлежит прямой Симсона).
    """
    doc_data = {
        "problem_name": "Simson Line bisects PH",
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
                "args": {"approx_position": [0, 4]},
            },
            {
                "name": "B",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [-3, -2]},
            },
            {
                "name": "C",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [4, -1]},
            },
            {
                "name": "Circ_ABC",
                "type": "Circle",
                "method": "Circumcircle",
                "args": {"triangle": ["A", "B", "C"]},
            },
            {
                "name": "P",
                "type": "Point",
                "method": "PointOnObject",
                "args": {"object": "Circ_ABC"},
            },
            {
                "name": "H",
                "type": "Point",
                "method": "Orthocenter",
                "args": {"triangle": ["A", "B", "C"]},
            },
            {
                "name": "SimL",
                "type": "Line",
                "method": "SimsonLine",
                "args": {"point": "P", "triangle": ["A", "B", "C"]},
            },
            {
                "name": "M",
                "type": "Point",
                "method": "Midpoint",
                "args": {"points": ["P", "H"]},
            },
        ],
        "goals": [{"type": "Belongs", "args": {"point": "M", "object": "SimL"}}],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "Show", "targets": ["Circ_ABC"]},
            {"action": "DrawSegment", "endpoints": ["P", "H"]},
            {"action": "Show", "targets": ["SimL", "M", "P", "H"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать невырожденную конфигурацию"

    m_x, m_y = env["M"]
    a, b, c = env["SimL"]

    residual = a * m_x + b * m_y + c
    assert abs(residual) == pytest.approx(0.0, abs=1e-8), (
        f"Теорема провалена: точка M не лежит на прямой Симсона (погрешность {residual})"
    )

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0, "Транслятор не сгенерировал GGB-код для целей"

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "simson_line.ggb")

    original_types = {obj.name: obj.type for obj in doc.construction if obj.name}

    config = GeoDrawConfig()
    config.show_axes = False
    config.show_grid = False

    generator = GeoDraftGenerator(config=config)
    generator.create_ggb(project, original_types, output_path)

    print(
        f"\n[+] Файл теоремы о прямой Симсона успешно сохранен: {os.path.abspath(output_path)}"
    )
    assert os.path.exists(output_path), "Файл .ggb не был записан на диск"
