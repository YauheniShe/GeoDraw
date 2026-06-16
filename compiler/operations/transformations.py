import math

from compiler.core.evaluators import compile_value_argument
from compiler.math_lib.base import (
    apply_transform,
    reflect_point_on_line,
)
from compiler.operations.registry import register


@register("Point", "Reflection")
@register("Line", "Reflection")
@register("Circle", "Reflection")
@register("Segment", "Reflection")
@register("Ray", "Reflection")
class ReflectionOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        t, ax = args.get("target"), args.get("axis")

        def step(env):
            env[name] = apply_transform(
                env[t], lambda p: reflect_point_on_line(p, env[ax]), 1.0
            )

        return step

    @staticmethod
    def to_ggb(args, name, **kwargs):
        return f"Reflect({args.get('target')}, {args.get('axis')})"


@register("Point", "PointReflection")
class PointReflectionOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        t, c = args.get("target"), args.get("center")

        def step(env):
            env[name] = apply_transform(
                env[t], lambda p: (2 * env[c][0] - p[0], 2 * env[c][1] - p[1]), 1.0
            )

        return step

    @staticmethod
    def to_ggb(args, name, **kwargs):
        return f"Reflect({args.get('target')}, {args.get('center')})"


@register("Point", "Translation")
class TranslationOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        t, (v0, v1) = args.get("target"), args["vector"]

        def step(env):
            env[name] = apply_transform(
                env[t],
                lambda p: (
                    p[0] + env[v1][0] - env[v0][0],
                    p[1] + env[v1][1] - env[v0][1],
                ),
                1.0,
            )

        return step

    @staticmethod
    def to_ggb(args, name, **kwargs):
        return f"Translate({args.get('target')}, Vector({args['vector'][0]}, {args['vector'][1]}))"


@register("Point", "Rotation")
class RotationOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        t, c = args.get("target"), args.get("center")

        ang_eval = compile_value_argument(args.get("angle"))
        orient = "counterclockwise"
        if disambiguation:
            orient = disambiguation.get(
                "value", disambiguation.get("orientation", "counterclockwise")
            )

        def step(env):
            center, angle = env[c], ang_eval(env)
            if orient == "clockwise":
                angle = -angle
            cos_a, sin_a = math.cos(angle), math.sin(angle)

            def rot_pt(p):
                dx, dy = p[0] - center[0], p[1] - center[1]
                return (
                    center[0] + dx * cos_a - dy * sin_a,
                    center[1] + dx * sin_a + dy * cos_a,
                )

            env[name] = apply_transform(env[t], rot_pt, 1.0)

        return step

    @staticmethod
    def to_ggb(args, name, disambiguation, translator, **kwargs) -> str:
        angle_str = translator._var_to_ggb(args.get("angle"))
        orient = "counterclockwise"
        if disambiguation:
            orient = disambiguation.get(
                "value", disambiguation.get("orientation", "counterclockwise")
            )
        if orient == "clockwise":
            angle_str = f"-({angle_str})"
        return f"Rotate({args.get('target')}, {angle_str}, {args.get('center')})"


@register("Point", "Homothety")
class HomothetyOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        t, c = args.get("target"), args.get("center")

        r_eval = compile_value_argument(args.get("ratio"))

        def step(env):
            center, ratio = env[c], r_eval(env)

            def hom_pt(p):
                return (
                    center[0] + ratio * (p[0] - center[0]),
                    center[1] + ratio * (p[1] - center[1]),
                )

            env[name] = apply_transform(env[t], hom_pt, ratio)

        return step

    @staticmethod
    def to_ggb(args, name, translator, **kwargs) -> str:
        ratio_str = translator._var_to_ggb(args.get("ratio"))
        return f"Dilate({args.get('target')}, {ratio_str}, {args.get('center')})"
