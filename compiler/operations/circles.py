from compiler.core.evaluators import compile_value_argument
from compiler.math_lib.base import (
    apollonius_circle,
    circumcircle,
    dist,
)
from compiler.operations.registry import register


@register("Circle", "CenterRadius")
class CenterRadiusOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        c = args.get("center")

        r_eval = compile_value_argument(args.get("radius"))

        def step(env):
            env[name] = (env[c], r_eval(env))

        return step

    @staticmethod
    def to_ggb(args, name, translator, **kwargs):
        r_str = translator._var_to_ggb(args.get("radius"))
        return f"Circle({args.get('center')}, {r_str})"


@register("Circle", "DiameterCircle")
class DiameterCircleOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        p0, p1 = args["points"]

        def step(env):
            pa, pb = env[p0], env[p1]
            env[name] = (((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2), dist(pa, pb) / 2)

        return step

    @staticmethod
    def to_ggb(args, name, **kwargs):
        return f"Circle(Midpoint({args['points'][0]}, {args['points'][1]}), {args['points'][0]})"


@register("Circle", "Circumcircle")
class CircumcircleOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        t0, t1, t2 = args["triangle"]

        def step(env):
            env[name] = circumcircle(env[t0], env[t1], env[t2])

        return step

    @staticmethod
    def to_ggb(args, name, **kwargs):
        return f"Circle({args['triangle'][0]}, {args['triangle'][1]}, {args['triangle'][2]})"


@register("Circle", "ApolloniusCircle")
class ApolloniusCircleOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        p0, p1 = args["points"]

        k_eval = compile_value_argument(args.get("ratio"))

        def step(env):
            env[name] = apollonius_circle(env[p0], env[p1], k_eval(env))

        return step

    @staticmethod
    def to_ggb(args, name, translator, **kwargs):
        p0, p1 = args["points"][0], args["points"][1]
        ratio = args.get("ratio")
        ratio_str = translator._var_to_ggb(ratio)
        translator._emit(
            name=f"{name}In",
            expression=f"({p0} + ({ratio_str}) * {p1}) / (1 + ({ratio_str}))",
            ggb_type="point",
            hidden=True,
        )
        translator._emit(
            name=f"{name}Out",
            expression=f"({p0} - ({ratio_str}) * {p1}) / (1 - ({ratio_str}))",
            ggb_type="point",
            hidden=True,
        )
        return f"Circle(Midpoint({name}In, {name}Out), {name}In)"


@register("Segment", "Free")
@register("Segment", "LineThrough")
class SegmentOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        p0, p1 = args["points"]

        def step(env):
            env[name] = ("segment", env[p0], env[p1])

        return step

    @staticmethod
    def to_ggb(args, name, **kwargs):
        return f"Segment({args['points'][0]}, {args['points'][1]})"


@register("Ray", "Free")
@register("Ray", "LineThrough")
class RayOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        p0, p1 = args["points"]

        def step(env):
            env[name] = ("ray", env[p0], env[p1])

        return step

    @staticmethod
    def to_ggb(args, name, **kwargs):
        return f"Ray({args['points'][0]}, {args['points'][1]})"
