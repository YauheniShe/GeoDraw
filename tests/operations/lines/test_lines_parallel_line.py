import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.math_lib.base import dist
from compiler.models import GeoDraftDocument
from compiler.operations.lines import ParallelLineOp


def test_parallel_line_compile_sample():
    """
    Юнит-тест математического ядра для ParallelLineOp.compile_sample.
    Даны:
    - Точка P(2.0, 3.0)
    - Прямая L: 2x - y - 5 = 0 (в формате (a, b, c) -> (2.0, -1.0, -5.0))
    Искомая параллельная прямая должна иметь вид: 2x - y + C_new = 0.
    Подставим P(2, 3): 2*(2) - 1*(3) + C_new = 0 => 4 - 3 + C_new = 0 => C_new = -1.0.
    Ожидаемый результат: (2.0, -1.0, -1.0).
    """
    args = {"point": "P", "line": "L"}
    step_func = ParallelLineOp.compile_sample(
        args=args, name="L_par", disambiguation=None
    )

    env = {"P": (2.0, 3.0), "L": (2.0, -1.0, -5.0)}
    step_func(env)

    assert env["L_par"] == (2.0, -1.0, -1.0)


def test_parallel_line_to_ggb():
    """Юнит-тест трансляции метода ParallelLine в синтаксис GeoGebra (Line(P, g))"""
    args = {"point": "A", "line": "g"}
    ggb_expr = ParallelLineOp.to_ggb(args=args, name="h", disambiguation=None)

    assert ggb_expr == "Line(A, g)"


def test_problem_trapezoid_diagonals_parallel():
    """
    Интеграционный End-to-End тест:
    Доказывает теорему о том, что в трапеции ABCD (AD || BC) прямая,
    проходящая через точку пересечения диагоналей P параллельно основаниям,
    делится этой точкой пополам на боковых сторонах AB и CD (XP = PY).
    Экспортирует результат в tests_output/trapezoid_diagonals_parallel.ggb.
    """
    doc_data = {
        "problem_name": "Trapezoid Parallel Segment through Diagonals Intersection",
        "constraints": [{"type": "Convex", "args": {"points": ["A", "B", "C", "D"]}}],
        "construction": [
            {
                "names": ["A", "B", "C", "D"],
                "type": "Point",
                "method": "Trapezoid",
                "args": None,
            },
            {
                "name": "Line_BC",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["B", "C"]},
                "hidden": True,
            },
            {
                "name": "Line_AC",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["A", "C"]},
                "hidden": True,
            },
            {
                "name": "Line_BD",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["B", "D"]},
                "hidden": True,
            },
            {
                "name": "P",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Line_AC", "obj2": "Line_BD"},
            },
            {
                "name": "Line_AB",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["A", "B"]},
                "hidden": True,
            },
            {
                "name": "Line_CD",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["C", "D"]},
                "hidden": True,
            },
            {
                "name": "Line_par",
                "type": "Line",
                "method": "ParallelLine",
                "args": {"point": "P", "line": "Line_BC"},
            },
            {
                "name": "X",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Line_par", "obj2": "Line_AB"},
            },
            {
                "name": "Y",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Line_par", "obj2": "Line_CD"},
            },
        ],
        "goals": [
            {
                "type": "Equal",
                "args": {
                    "values": [
                        {"type": "Distance", "points": ["X", "P"]},
                        {"type": "Distance", "points": ["P", "Y"]},
                    ]
                },
            }
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C", "D"]},
            {"action": "DrawSegment", "endpoints": ["A", "C"]},
            {"action": "DrawSegment", "endpoints": ["B", "D"]},
            {"action": "Clip", "target": "Line_par", "endpoints": ["X", "Y"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать выпуклую конфигурацию трапеции"

    dist_xp = dist(env["X"], env["P"])
    dist_py = dist(env["P"], env["Y"])

    assert dist_xp == pytest.approx(dist_py, abs=1e-8), (
        f"Теорема провалена: длина XP {dist_xp:.6f} не равна длине PY {dist_py:.6f}"
    )

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)
    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0, "Транслятор не сгенерировал GGB-код для целей"
    assert any("Segment" in inst.expression for inst in goal_instructions)
    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "trapezoid_diagonals_parallel.ggb")

    original_types = {}
    for obj in doc.construction:
        if obj.name:
            original_types[obj.name] = obj.type
        elif obj.names:
            for name in obj.names:
                original_types[name] = obj.type

    config = GeoDrawConfig()
    config.show_axes = False
    config.show_grid = False

    generator = GeoDraftGenerator(config=config)
    generator.create_ggb(project, original_types, output_path)

    print(f"\n[+] Свойство трапеции успешно сохранено: {os.path.abspath(output_path)}")
    assert os.path.exists(output_path), "Файл .ggb не был создан на диске"
