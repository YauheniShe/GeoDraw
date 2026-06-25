import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import dist
from compiler.models import GeoDraftDocument
from compiler.operations.points import HarmonicConjugateOp


def assert_point_approx(pt1, pt2, abs_tol=1e-7):
    assert pt1[0] == pytest.approx(pt2[0], abs=abs_tol)
    assert pt1[1] == pytest.approx(pt2[1], abs=abs_tol)


class MockTranslator:
    """Вспомогательный класс для имитации транслятора при юнит-тестировании GGB-генерации"""

    def __init__(self):
        self.instructions = []

    def _emit(self, **kwargs):
        self.instructions.append(kwargs)
        return kwargs["name"]


def test_harmonic_conjugate_compile_sample():
    """
    Юнит-тест для HarmonicConjugateOp.compile_sample.
    Возьмем точки на одной прямой: A(0, 0), B(4, 0).
    Пусть точка C(1, 0) делит отрезок AB внутренним образом в отношении AC:CB = 1:3.
    Тогда гармонически сопряженная точка D должна делить отрезок AB внешним образом
    в том же отношении DA:DB = 1:3, что дает координаты D(-2, 0).
    """
    args = {"points": ["A", "B"], "conjugate_to": "C"}
    step_func = HarmonicConjugateOp.compile_sample(
        args=args, name="D", disambiguation=None
    )

    env = {"A": (0.0, 0.0), "B": (4.0, 0.0), "C": (1.0, 0.0)}
    step_func(env)
    assert_point_approx(env["D"], (-2.0, 0.0))


def test_harmonic_conjugate_to_ggb():
    """
    Юнит-тест трансляции HarmonicConjugate в GeoGebra.
    Проверяем, что создаются вспомогательные переменные проекции s_node и t_node,
    и итоговое выражение корректно строит векторное смещение.
    """
    translator = MockTranslator()
    args = {"points": ["X", "Y"], "conjugate_to": "Z"}

    expr = HarmonicConjugateOp.to_ggb(args=args, name="W", translator=translator)
    assert expr == "X + s_W * (Y - X)"
    emitted_names = [inst["name"] for inst in translator.instructions]
    assert "t_W" in emitted_names
    assert "s_W" in emitted_names


def test_problem_newton_relation():
    """
    Интеграционный E2E-тест:
    Строит гармоническую четверку точек (A, B; C, D) на одной прямой, где D — сопряжение C.
    Находит середину M отрезка AB.
    Доказывает соотношение Ньютона: MC * MD = MA^2.
    Дополнительно проверяет коллинеарность (A, B, D) в качестве цели для GGB.
    """
    doc_data = {
        "problem_name": "Harmonic Conjugate Newton Relation",
        "constraints": [
            {
                "type": "Inequality",
                "operator": ">",
                "left": {"type": "Distance", "points": ["A", "B"]},
                "right": {"type": "Number", "value": 1.0},
            }
        ],
        "construction": [
            {
                "name": "A",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [-3, 0]},
            },
            {
                "name": "B",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [3, 0]},
            },
            {
                "name": "Line_AB",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["A", "B"]},
                "hidden": True,
            },
            {
                "name": "C",
                "type": "Point",
                "method": "PointOnObject",
                "args": {"object": "Line_AB"},
            },
            {
                "name": "D",
                "type": "Point",
                "method": "HarmonicConjugate",
                "args": {"points": ["A", "B"], "conjugate_to": "C"},
            },
            {
                "name": "M",
                "type": "Point",
                "method": "Midpoint",
                "args": {"points": ["A", "B"]},
            },
        ],
        "goals": [{"type": "Collinear", "args": {"points": ["A", "B", "D"]}}],
        "view": [
            {"action": "Clip", "target": "Line_AB", "endpoints": ["D", "B"]},
            {"action": "Show", "targets": ["C", "D", "M"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать конфигурацию на прямой"

    pt_A = env["A"]
    pt_C = env["C"]
    pt_D = env["D"]
    pt_M = env["M"]

    d_MC = dist(pt_M, pt_C)
    d_MD = dist(pt_M, pt_D)
    d_MA = dist(pt_M, pt_A)

    newton_left = d_MC * d_MD
    newton_right = d_MA**2

    assert newton_left == pytest.approx(newton_right, abs=1e-8), (
        f"Соотношение Ньютона нарушено: {newton_left:.6f} != {newton_right:.6f}"
    )

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0
    assert any(inst.ggb_type == "line" for inst in goal_instructions)

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "harmonic_conjugate_newton.ggb")

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
        f"\n[+] Гармоническое сопряжение успешно протестировано. Чертеж сохранен в: {output_path}"
    )
    assert os.path.exists(output_path)
