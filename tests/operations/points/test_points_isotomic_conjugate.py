import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import dist
from compiler.models import GeoDraftDocument
from compiler.operations.points import IsotomicConjugateOp


def assert_point_approx(pt1, pt2, abs_tol=1e-7):
    assert pt1[0] == pytest.approx(pt2[0], abs=abs_tol)
    assert pt1[1] == pytest.approx(pt2[1], abs=abs_tol)


def test_isotomic_conjugate_compile_sample():
    """
    Юнит-тест математического ядра для IsotomicConjugateOp.compile_sample.
    Используем свойство: изотомически сопряженной точкой для центроида (Centroid)
    является сам центроид, так как его барицентрические координаты равны (1:1:1),
    а обратные им величины (1/1 : 1/1 : 1/1) дают то же отношение.

    Возьмем треугольник A(0, 3), B(-2, 0), C(2, 0).
    Центроид G имеет координаты (0.0, 1.0).
    """
    args = {"point": "G", "triangle": ["A", "B", "C"]}
    step_func = IsotomicConjugateOp.compile_sample(
        args=args, name="G_isotomic", disambiguation=None
    )

    env = {"A": (0.0, 3.0), "B": (-2.0, 0.0), "C": (2.0, 0.0), "G": (0.0, 1.0)}
    step_func(env)

    assert_point_approx(env["G_isotomic"], (0.0, 1.0))


def test_isotomic_conjugate_to_ggb():
    """
    Юнит-тест генерации GGB-кода для IsotomicConjugate.
    Проверяет, что транслятор генерирует 4 скрытых точки-помощника
    для построения изотомически симметричных отрезков на сторонах треугольника,
    а затем пересекает прямые, соединяющие вершины с этими точками.
    """
    args = {"point": "P", "triangle": ["A", "B", "C"]}
    translator = GeoDraftTranslator()

    ggb_expr = IsotomicConjugateOp.to_ggb(
        args=args, name="P_isotomic", translator=translator
    )

    assert ggb_expr.startswith("Intersect(")
    assert "helper_Dp_P_isotomic" in ggb_expr
    assert "helper_Ep_P_isotomic" in ggb_expr

    emitted_names = [inst.name for inst in translator.instructions]
    assert "helper_D_P_isotomic" in emitted_names
    assert "helper_Dp_P_isotomic" in emitted_names
    assert "helper_E_P_isotomic" in emitted_names
    assert "helper_Ep_P_isotomic" in emitted_names


def test_problem_gergonne_nagel_isotomic_conjugacy():
    """
    Интеграционный тест:
    Доказывает теорему о том, что изотомическое сопряжение точки Жергонна (Ge, X_7)
    совпадает с точкой Нагеля (Na, X_8).
    Экспортирует результат в tests_output/isotomic_conjugate_nagel.ggb.
    """
    doc_data = {
        "problem_name": "Gergonne and Nagel Isotomic Conjugacy",
        # Ограничение: невырожденный треугольник
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
                "name": "Ge",
                "type": "Point",
                "method": "ETC",
                "args": {"index": 7, "triangle": ["A", "B", "C"]},
            },
            {
                "name": "Na",
                "type": "Point",
                "method": "ETC",
                "args": {"index": 8, "triangle": ["A", "B", "C"]},
            },
            {
                "name": "Ge_isotomic",
                "type": "Point",
                "method": "IsotomicConjugate",
                "args": {"point": "Ge", "triangle": ["A", "B", "C"]},
            },
        ],
        "goals": [
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "Distance", "points": ["Ge_isotomic", "Na"]},
                        {"type": "Number", "value": 0.0},
                    ]
                },
            }
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "DrawSegment", "endpoints": ["Ge_isotomic", "Na"]},
            {"action": "Show", "targets": ["Ge", "Na", "Ge_isotomic"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать невырожденный треугольник"
    ge_isotomic_pt = env["Ge_isotomic"]
    na_pt = env["Na"]

    distance_between = dist(ge_isotomic_pt, na_pt)
    assert distance_between == pytest.approx(0.0, abs=1e-8), (
        f"Теорема не подтвердилась: расстояние между изотомическим сопряжением Ge и точкой Na равно {distance_between:.6f} (ожидался 0)"
    )

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0, "Транслятор не сгенерировал GGB-код для целей"
    assert any(inst.ggb_type == "segment" for inst in goal_instructions)

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "isotomic_conjugate_nagel.ggb")

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
        f"\n[+] Чертеж изотомического сопряжения успешно сохранен: {os.path.abspath(output_path)}"
    )
    assert os.path.exists(output_path), "Файл .ggb не был записан на диск"
