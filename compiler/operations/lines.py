from compiler.math_lib.base import (
    angle_bisector,
    common_tangents,
    line_from_points,
    perpendicular_bisector,
)
from compiler.operations.registry import register


@register("Line", "LineThrough")
class LineThroughOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        p0, p1 = args["points"]

        def step(env):
            env[name] = line_from_points(env[p0], env[p1])

        return step

    @staticmethod
    def to_ggb(args, name, **kwargs):
        return f"Line({args['points'][0]}, {args['points'][1]})"


@register("Line", "ParallelLine")
class ParallelLineOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        pt, line = args.get("point"), args.get("line")

        def step(env):
            lp, ll = env[pt], env[line]
            env[name] = (ll[0], ll[1], -(ll[0] * lp[0] + ll[1] * lp[1]))

        return step

    @staticmethod
    def to_ggb(args, name, **kwargs):
        return f"Line({args.get('point')}, {args.get('line')})"


@register("Line", "PerpendicularLine")
class PerpendicularLineOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        pt, line = args.get("point"), args.get("line")

        def step(env):
            lp, ll = env[pt], env[line]
            a_new, b_new = -ll[1], ll[0]
            env[name] = (a_new, b_new, -(a_new * lp[0] + b_new * lp[1]))

        return step

    @staticmethod
    def to_ggb(args, name, **kwargs):
        return f"PerpendicularLine({args.get('point')}, {args.get('line')})"


@register("Line", "AngleBisector")
class AngleBisectorOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        v, e0, e1 = args.get("vertex"), args["ends"][0], args["ends"][1]

        def step(env):
            env[name] = angle_bisector(env[v], env[e0], env[e1])

        return step

    @staticmethod
    def to_ggb(args, name, **kwargs):
        return (
            f"AngleBisector({args['ends'][0]}, {args.get('vertex')}, {args['ends'][1]})"
        )


@register("Line", "PerpendicularBisector")
class PerpendicularBisectorOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        p0, p1 = args["points"]

        def step(env):
            env[name] = perpendicular_bisector(env[p0], env[p1])

        return step

    @staticmethod
    def to_ggb(args, name, **kwargs):
        return f"PerpendicularBisector({args['points'][0]}, {args['points'][1]})"


@register("Line", "CommonTangent")
class CommonTangentOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        c1, c2 = args.get("circle1"), args.get("circle2")
        is_ext = (
            (disambiguation.get("direction", "external") == "external")
            if disambiguation
            else True
        )
        idx = disambiguation.get("algebraic_index", 1) if disambiguation else 1

        def step(env):
            tangents = common_tangents(env[c1], env[c2], external=is_ext)
            if not tangents or idx > len(tangents):
                raise ValueError("Касательные не найдены")
            env[name] = tangents[idx - 1]

        return step

    @staticmethod
    def to_ggb(args, name, disambiguation, **kwargs) -> str:
        idx = disambiguation.get("algebraic_index", 1) if disambiguation else 1
        return (
            f"Element({{Tangent({args.get('circle1')}, {args.get('circle2')})}}, {idx})"
        )
