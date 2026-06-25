import os

import pytest
from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.models import GeoDraftDocument
from compiler.operations.circles import RayOp


def assert_point_approx(pt1, pt2, abs_tol=1e-7):
    assert pt1[0] == pytest.approx(pt2[0], abs=abs_tol)
    assert pt1[1] == pytest.approx(pt2[1], abs=abs_tol)


def test_raybypoints_compile_sample():
    """
    Юнит-тест математического ядра для RayByPoints.
    Проверяет, что луч из O(1.0, 2.0) через A(4.0, 6.0) корректно инициализируется.
    """
    args = {"origin": "O", "direction_point": "A"}
    step_func = RayOp.compile_sample(args=args, name="Ray_OA", disambiguation=None)

    env = {"O": (1.0, 2.0), "A": (4.0, 6.0)}
    step_func(env)

    # Тип луча представляется кортежем ("ray", origin, direction_point)
    assert env["Ray_OA"] == ("ray", (1.0, 2.0), (4.0, 6.0))


def test_raybypoints_to_ggb():
    """Юнит-тест трансляции метода RayByPoints в формат GeoGebra (Ray(origin, direction_point))"""
    args = {"origin": "O", "direction_point": "A"}
    ggb_expr = RayOp.to_ggb(args=args, name="Ray_OA", disambiguation=None)

    assert ggb_expr == "Ray(O, A)"


def test_problem_desargues_theorem():
    """
    Интеграционный тест:
    Доказывает Теорему Дезарга.
    Строит треугольники ABC и A'B'C', перспективные из центра O.
    Вершины A', B', C' лежат на лучах OA, OB, OC соответственно.
    Доказывает, что точки пересечения соответственных сторон P, Q, R коллинеарны.
    Экспортирует результат в tests_output/desargues_theorem.ggb.
    """
    doc_data = {
        "problem_name": "Desargues Theorem",
        "constraints": [
            {
                "type": "Inequality",
                "operator": ">",
                "left": {
                    "type": "MathExpression",
                    "expression": "abs(x(O)*(y(A) - y(B)) + x(A)*(y(B) - y(O)) + x(B)*(y(O) - y(A)))",
                    "variables": {"O": "O", "A": "A", "B": "B"},
                },
                "right": {"type": "Number", "value": 1.0},
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
                "name": "A",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [2, 3]},
            },
            {
                "name": "B",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [-3, 2]},
            },
            {
                "name": "C",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [1, -3]},
            },
            {
                "name": "Ray_OA",
                "type": "Ray",
                "method": "RayByPoints",
                "args": {"origin": "O", "direction_point": "A"},
                "hidden": True,
            },
            {
                "name": "Ray_OB",
                "type": "Ray",
                "method": "RayByPoints",
                "args": {"origin": "O", "direction_point": "B"},
                "hidden": True,
            },
            {
                "name": "Ray_OC",
                "type": "Ray",
                "method": "RayByPoints",
                "args": {"origin": "O", "direction_point": "C"},
                "hidden": True,
            },
            {
                "name": "Ap",
                "type": "Point",
                "method": "PointOnObject",
                "args": {"object": "Ray_OA"},
            },
            {
                "name": "Bp",
                "type": "Point",
                "method": "PointOnObject",
                "args": {"object": "Ray_OB"},
            },
            {
                "name": "Cp",
                "type": "Point",
                "method": "PointOnObject",
                "args": {"object": "Ray_OC"},
            },
            {
                "name": "Line_AB",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["A", "B"]},
                "hidden": True,
            },
            {
                "name": "Line_ApBp",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["Ap", "Bp"]},
                "hidden": True,
            },
            {
                "name": "Line_BC",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["B", "C"]},
                "hidden": True,
            },
            {
                "name": "Line_BpCp",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["Bp", "Cp"]},
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
                "name": "Line_ApCp",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["Ap", "Cp"]},
                "hidden": True,
            },
            {
                "name": "P",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Line_AB", "obj2": "Line_ApBp"},
            },
            {
                "name": "Q",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Line_BC", "obj2": "Line_BpCp"},
            },
            {
                "name": "R",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Line_AC", "obj2": "Line_ApCp"},
            },
        ],
        "goals": [{"type": "Collinear", "args": {"points": ["P", "Q", "R"]}}],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "DrawPolygon", "vertices": ["Ap", "Bp", "Cp"]},
            {"action": "DrawSegment", "endpoints": ["O", "Ap"]},
            {"action": "DrawSegment", "endpoints": ["O", "Bp"]},
            {"action": "DrawSegment", "endpoints": ["O", "Cp"]},
            {"action": "DrawSegment", "endpoints": ["B", "P"]},
            {"action": "DrawSegment", "endpoints": ["Bp", "P"]},
            {"action": "DrawSegment", "endpoints": ["C", "Q"]},
            {"action": "DrawSegment", "endpoints": ["Cp", "Q"]},
            {"action": "DrawSegment", "endpoints": ["C", "R"]},
            {"action": "DrawSegment", "endpoints": ["Cp", "R"]},
            {"action": "DrawSegment", "endpoints": ["P", "R"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать невырожденную конфигурацию Дезарга"
    p, q, r = env["P"], env["Q"], env["R"]
    area = p[0] * (q[1] - r[1]) + q[0] * (r[1] - p[1]) + r[0] * (p[1] - q[1])
    assert abs(area) < 1e-8, (
        f"Теорема провалена: ориентированная площадь {area} слишком велика"
    )

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0, "Транслятор не сгенерировал цели"
    assert any(inst.ggb_type == "line" for inst in goal_instructions)

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "desargues_theorem.ggb")

    original_types = {}
    for obj in doc.construction:
        if obj.name:
            original_types[obj.name] = obj.type

    config = GeoDrawConfig()
    config.show_axes = False
    config.show_grid = False

    generator = GeoDraftGenerator(config=config)
    generator.create_ggb(project, original_types, output_path)

    print(f"\n[+] Теорема Дезарга успешно сохранена: {os.path.abspath(output_path)}")
    assert os.path.exists(output_path), "Файл .ggb не создался"
