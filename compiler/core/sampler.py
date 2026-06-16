import math
import random
from typing import Any, Dict

from simpleeval import simple_eval

from compiler.core.constraints import compile_constraints
from compiler.core.evaluators import SAFE_MATH_GLOBALS, compile_var_evaluators
from compiler.math_lib.base import dist
from compiler.models import GeoDraftDocument
from compiler.operations import *  # noqa
from compiler.operations.registry import SAMPLER_REGISTRY


def compile_execution_plan(doc: GeoDraftDocument):
    plan = []
    for obj in doc.construction:
        if obj.names:
            names = tuple(obj.names)
            method = obj.method
            registry_key = (obj.type, method)
            if registry_key in SAMPLER_REGISTRY:
                plan.append(
                    SAMPLER_REGISTRY[registry_key](
                        args=obj.args, name=names, disambiguation=obj.disambiguation
                    )
                )
            continue

        name = obj.name
        if obj.type == "Point" and obj.method == "Free":
            continue

        args = obj.args or {}
        method = obj.method or "Free"

        registry_key = (obj.type, method)
        if registry_key in SAMPLER_REGISTRY:
            step_func = SAMPLER_REGISTRY[registry_key](
                args=args, name=name, disambiguation=obj.disambiguation
            )
            plan.append(step_func)
            continue

        # Вспомогательные скалярные вычисления
        if obj.type == "MathExpression":
            expr_str = args["expression"]
            var_evals = compile_var_evaluators(args.get("variables", {}))
            plan.append(
                lambda env, n=name, expr=expr_str, ve=var_evals: env.update(
                    {
                        n: simple_eval(
                            expr,
                            names={k: f(env) for k, f in ve.items()},
                            functions=SAFE_MATH_GLOBALS,
                        )
                    }
                )
            )
        elif obj.type == "Distance":
            p0, p1 = args["points"]
            plan.append(
                lambda env, n=name, a=p0, b=p1: env.update({n: dist(env[a], env[b])})
            )
        elif obj.type == "Number":
            val = float(args["value"])
            plan.append(lambda env, n=name, v=val: env.update({n: v}))
        elif obj.type == "AngleMeasure":
            v, e0, e1 = args.get("vertex"), args["ends"][0], args["ends"][1]

            def step_ang(env, n=name, v=v, e0=e0, e1=e1):
                vertex, end1, end2 = env[v], env[e0], env[e1]
                dx1, dy1 = end1[0] - vertex[0], end1[1] - vertex[1]
                dx2, dy2 = end2[0] - vertex[0], end2[1] - vertex[1]
                raw_ang = abs(math.atan2(dx1 * dy2 - dy1 * dx2, dx1 * dx2 + dy1 * dy2))
                env[n] = raw_ang if raw_ang <= math.pi else (2 * math.pi - raw_ang)

            plan.append(step_ang)

    return plan


def sample_and_evaluate(doc: GeoDraftDocument, max_attempts=1000) -> Dict[str, Any]:
    execution_plan = compile_execution_plan(doc)
    constraints_plan = compile_constraints(doc)
    free_points_to_sample = {}
    point_on_object_params = []
    cyclic_quads_list = []

    for obj in doc.construction:
        if obj.names:
            if obj.method == "CyclicQuadrilateral":
                cyclic_quads_list.append(obj.names)
            elif obj.method in ["Parallelogram", "FreeTriangle"]:
                free_points_to_sample.update(
                    {
                        obj.names[0]: (0.0, 0.0),
                        obj.names[1]: (3.0, 0.0),
                        obj.names[2]: (4.0, 3.0),
                    }
                )
            elif obj.method in ["Square", "EquilateralTriangle"]:
                free_points_to_sample.update(
                    {obj.names[0]: (0.0, 0.0), obj.names[1]: (3.0, 0.0)}
                )
        elif obj.type == "Point":
            if obj.method == "Free":
                approx = obj.args.get("approx_position") if obj.args else None
                if not approx:
                    approx = (random.uniform(-2, 2), random.uniform(-2, 2))
                free_points_to_sample[obj.name] = approx
            elif obj.method == "PointOnObject":
                point_on_object_params.append(obj.name)

    cyclic_quad_set = {name for quad in cyclic_quads_list for name in quad}
    free_points_to_sample_filtered = {
        k: v for k, v in free_points_to_sample.items() if k not in cyclic_quad_set
    }

    for attempt in range(max_attempts):
        env = {}
        for name, approx in free_points_to_sample_filtered.items():
            env[name] = (
                approx[0] + random.uniform(-1.2, 1.2),
                approx[1] + random.uniform(-1.2, 1.2),
            )
        for quad_names in cyclic_quads_list:
            start_angle = random.uniform(0, 2 * math.pi)
            angles = [start_angle]
            for _ in range(3):
                angles.append(angles[-1] + random.uniform(0.6, 1.4))
            R = random.uniform(2.5, 3.5)
            cx, cy = random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5)
            for i, name in enumerate(quad_names):
                env[name] = (cx + R * math.cos(angles[i]), cy + R * math.sin(angles[i]))
        for name in point_on_object_params:
            env[f"{name}_param"] = random.uniform(0.01, 0.99)

        try:
            for step in execution_plan:
                step(env)
        except ValueError:
            continue

        satisfied = True
        for check in constraints_plan:
            if not check(env):
                satisfied = False
                break
        if satisfied:
            print(f"-> Конфигурация успешно подобрана за {attempt + 1} попыток!")
            return env
    print("-> Предупреждение: Не удалось подобрать конфигурацию.")
    return {}
