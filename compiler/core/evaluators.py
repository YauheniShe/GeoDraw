import math
from typing import Any, Callable

from simpleeval import DEFAULT_FUNCTIONS, simple_eval

from compiler.math_lib.base import dist

SAFE_MATH_GLOBALS = DEFAULT_FUNCTIONS.copy()
SAFE_MATH_GLOBALS.update(
    {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
)


def compile_var_evaluators(variables_dict):
    evaluators = {}
    for var_name, var_obj in variables_dict.items():
        if isinstance(var_obj, str):
            evaluators[var_name] = lambda env, n=var_obj: env[n]
        elif isinstance(var_obj, dict):
            v_type = var_obj.get("type")
            if v_type == "Distance":
                p0, p1 = var_obj["points"]
                evaluators[var_name] = lambda env, a=p0, b=p1: dist(env[a], env[b])
            elif v_type == "Number":
                v = var_obj.get("value")
                evaluators[var_name] = lambda env, val=v: val
            elif v_type == "AngleMeasure":
                vt = var_obj.get("vertex")
                e0, e1 = var_obj["ends"]

                def angle_eval(env, v=vt, e0=e0, e1=e1):
                    vertex, end1, end2 = env[v], env[e0], env[e1]
                    dx1, dy1 = end1[0] - vertex[0], end1[1] - vertex[1]
                    dx2, dy2 = end2[0] - vertex[0], end2[1] - vertex[1]
                    raw_ang = abs(
                        math.atan2(dx1 * dy2 - dy1 * dx2, dx1 * dx2 + dy1 * dy2)
                    )
                    return raw_ang if raw_ang <= math.pi else (2 * math.pi - raw_ang)

                evaluators[var_name] = angle_eval
    return evaluators


def compile_value_argument(arg: Any) -> Callable[[Any], float]:
    if isinstance(arg, str):
        return lambda env, n=arg: env[n]
    elif isinstance(arg, dict):
        t = arg.get("type")
        if t == "MathExpression":
            expression_str = arg["expression"]
            var_evals = compile_var_evaluators(arg.get("variables", {}))
            return lambda env, expr=expression_str, ve=var_evals: simple_eval(
                expr,
                names={k: f(env) for k, f in ve.items()},
                functions=SAFE_MATH_GLOBALS,
            )
        elif t == "Distance":
            p0, p1 = arg["points"]
            return lambda env, a=p0, b=p1: dist(env[a], env[b])
        elif t == "Number":
            v = arg.get("value")
            return lambda env, val=v: val  # type: ignore
    if isinstance(arg, (int, float)):
        v = float(arg)
    else:
        raise TypeError("arg has invalid type")
    return lambda env, val=v: val
