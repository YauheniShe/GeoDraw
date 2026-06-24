import os

from compiler.config import GeoDrawConfig
from compiler.core.sampler import sample_and_evaluate
from compiler.core.translator import GeoDraftTranslator
from compiler.generator import GeoDraftGenerator
from compiler.models import GeoDraftDocument
from compiler.operations.points import CenterOp


def assert_goals(doc: GeoDraftDocument, env: dict):
    for goal in doc.goals:
        g_type = goal.type
        args = goal.args

        if g_type == "Collinear":
            pts = args["points"]
            assert len(pts) >= 3, "Цель Collinear требует минимум 3 точки"
            p1, p2, p3 = env[pts[0]], env[pts[1]], env[pts[2]]
            area = (
                p1[0] * (p2[1] - p3[1])
                + p2[0] * (p3[1] - p1[1])
                + p3[0] * (p1[1] - p2[1])
            )
            assert abs(area) < 1e-8, (
                f"Цель Collinear провалена для точек {pts}. Отклонение: {area}"
            )


def test_center_compile_sample():
    mock_circle = ((42.0, -17.5), 10.0)

    args = {"object": "Circ_1"}
    step_func = CenterOp.compile_sample(args=args, name="P_center", disambiguation=None)

    env = {"Circ_1": mock_circle}
    step_func(env)

    assert env["P_center"] == (42.0, -17.5)


def test_center_to_ggb():
    args = {"object": "Circ_ABC"}
    ggb_expr = CenterOp.to_ggb(args=args, name="O", disambiguation=None)

    assert ggb_expr == "Center(Circ_ABC)"


def test_problem_euler_line_collinearity():
    """
    Доказывает, что центр окружности 9 точек (N9), полученный методом Center,
    лежит на одной прямой с ортоцентром (H) и circumcenter (O).
    Экспортирует результат в tests_output/euler_line.ggb.
    """
    doc_data = {
        "problem_name": "Euler Line and Nine-Point Center",
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
                "args": {"approx_position": [-2, -1]},
            },
            {
                "name": "B",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [4, -1]},
            },
            {
                "name": "C",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [1, 4]},
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
                "name": "NPC",
                "type": "Circle",
                "method": "NinePointCircle",
                "args": {"triangle": ["A", "B", "C"]},
            },
            {
                "name": "N9",
                "type": "Point",
                "method": "Center",
                "args": {"object": "NPC"},
            },
        ],
        "goals": [{"type": "Collinear", "args": {"points": ["O", "N9", "H"]}}],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "Show", "targets": ["NPC"]},
            {"action": "DrawSegment", "endpoints": ["O", "H"]},
        ],
    }

    doc = GeoDraftDocument(**doc_data)
    env = sample_and_evaluate(doc)
    assert env, "Семплер не смог подобрать конфигурацию"

    assert_goals(doc, env)

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, sampled_state=env)

    goal_instructions = [inst for inst in project.instructions if inst.is_goal]
    assert len(goal_instructions) > 0, "Транслятор не сгенерировал GGB-код для целей"

    assert any(inst.ggb_type == "line" for inst in goal_instructions)

    output_dir = "tests_output"
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "euler_line.ggb")

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

    print(f"\n[+] Файл прямой Эйлера успешно сохранен: {os.path.abspath(output_path)}")
    assert os.path.exists(output_path), "Файл .ggb не был создан на диске"
