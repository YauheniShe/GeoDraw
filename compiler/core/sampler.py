from typing import Any, Dict

from simpleeval import simple_eval

from compiler.core.constraints import compile_constraints
from compiler.core.evaluators import SAFE_MATH_GLOBALS, compile_var_evaluators
from compiler.math_lib.base import dist
from compiler.models import GeoDraftDocument
from compiler.operations.registry import SAMPLER_REGISTRY


def compile_execution_plan(doc: GeoDraftDocument):
    plan = []
    for obj in doc.construction:
        method = obj.method or "Free"
        args = obj.args or {}
        if obj.names:
            names = tuple(obj.names)
            registry_key = (obj.type, method)
            if registry_key in SAMPLER_REGISTRY:
                plan.append(
                    SAMPLER_REGISTRY[registry_key](
                        args=args, name=names, disambiguation=obj.disambiguation
                    )
                )
            continue

        # 2. Обработка обычных объектов
        name = obj.name
        registry_key = (obj.type, method)
        if registry_key in SAMPLER_REGISTRY:
            plan.append(
                SAMPLER_REGISTRY[registry_key](
                    args=args, name=name, disambiguation=obj.disambiguation
                )
            )
            continue

        # 3. Вспомогательные скалярные вычисления
        if obj.type == "MathExpression":
            expr_str = args.get("expression", "")
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
            val = float(args.get("value", 0))
            plan.append(lambda env, n=name, v=val: env.update({n: v}))
        elif obj.type == "AngleMeasure":
            import math

            v = args.get("vertex")
            e0, e1 = args["ends"][0], args["ends"][1]

            def step_ang(env, n=name, v_v=v, e0_v=e0, e1_v=e1):
                vertex, end1, end2 = env[v_v], env[e0_v], env[e1_v]
                dx1, dy1 = end1[0] - vertex[0], end1[1] - vertex[1]
                dx2, dy2 = end2[0] - vertex[0], end2[1] - vertex[1]
                raw_ang = abs(math.atan2(dx1 * dy2 - dy1 * dx2, dx1 * dx2 + dy1 * dy2))
                env[n] = raw_ang if raw_ang <= math.pi else (2 * math.pi - raw_ang)

            plan.append(step_ang)

    return plan


def sample_and_evaluate(doc: GeoDraftDocument, max_attempts=1000) -> Dict[str, Any]:
    execution_plan = compile_execution_plan(doc)
    constraints_plan = compile_constraints(doc)

    for attempt in range(max_attempts):
        env = {}
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
