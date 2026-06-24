import math

from compiler.core.evaluators import compile_value_argument
from compiler.math_lib.base import (
    angle_bisector,
    centroid,
    circumcenter,
    common_tangents,
    get_line_eq,
    line_from_points,
    perpendicular_bisector,
    project_point_on_line,
    reflect_point_on_line,
    tangents_from_point_to_circle,
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

        is_ext = True
        idx = 1
        if disambiguation:
            if disambiguation.get("rule") == "tangent_direction":
                is_ext = disambiguation.get("value", "external") == "external"
                idx = disambiguation.get("index", 1)
            else:
                is_ext = disambiguation.get("direction", "external") == "external"
                idx = disambiguation.get("algebraic_index", 1)

        def step(env):
            tangents = common_tangents(env[c1], env[c2], external=is_ext)
            if not tangents or idx > len(tangents):
                raise ValueError("Касательные не найдены")
            env[name] = tangents[idx - 1]

        return step

    @staticmethod
    def to_ggb(args, name, disambiguation, **kwargs) -> str:
        idx = 1
        if disambiguation:
            if disambiguation.get("rule") == "tangent_direction":
                idx = disambiguation.get("index", 1)
            else:
                idx = disambiguation.get("algebraic_index", 1)
        return (
            f"Element({{Tangent({args.get('circle1')}, {args.get('circle2')})}}, {idx})"
        )


@register("Line", "LineByAngle")
class LineByAngleOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        pt, line_ref = args["point"], args["line"]
        ang_eval = compile_value_argument(args["angle"])

        def step(env):
            l_eq = get_line_eq(env[line_ref])
            if l_eq is None:
                raise ValueError(
                    f"Объект '{line_ref}' не является валидной прямой, отрезком или лучом."
                )
            p = env[pt]
            theta = ang_eval(env)
            a, b, c = l_eq
            cos_t, sin_t = math.cos(theta), math.sin(theta)
            ap = a * cos_t - b * sin_t
            bp = a * sin_t + b * cos_t
            env[name] = (ap, bp, -(ap * p[0] + bp * p[1]))

        return step

    @staticmethod
    def to_ggb(args, name, translator, **kwargs):
        ang_str = translator._var_to_ggb(args["angle"])
        return f"Rotate({args['line']}, {ang_str}, {args['point']})"


@register("Line", "TangentLine")
class TangentLineOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        pt, circle_ref = args["point"], args["object"]

        idx = 1
        if disambiguation:
            if disambiguation.get("rule") == "algebraic_index":
                idx = disambiguation.get("index", 1)
            else:
                idx = disambiguation.get("algebraic_index", 1)

        def step(env):
            tangents = tangents_from_point_to_circle(env[pt], env[circle_ref])
            if not tangents or idx > len(tangents):
                raise ValueError("Касательные не найдены")
            env[name] = tangents[idx - 1]

        return step

    @staticmethod
    def to_ggb(args, name, disambiguation, **kwargs):
        idx = 1
        if disambiguation:
            if disambiguation.get("rule") == "algebraic_index":
                idx = disambiguation.get("index", 1)
            else:
                idx = disambiguation.get("algebraic_index", 1)
        return f"Element({{Tangent({args['point']}, {args['object']})}}, {idx})"


@register("Line", "RadicalAxis")
class RadicalAxisOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        c1_ref, c2_ref = args["circle1"], args["circle2"]

        def step(env):
            (x1, y1), r1 = env[c1_ref]
            (x2, y2), r2 = env[c2_ref]
            a = 2 * (x2 - x1)
            b = 2 * (y2 - y1)
            c = (x1**2 + y1**2 - r1**2) - (x2**2 + y2**2 - r2**2)
            norm = math.hypot(a, b)
            if norm < 1e-9:
                raise ValueError("Окружности концентрические")
            env[name] = (a / norm, b / norm, c / norm)

        return step

    @staticmethod
    def to_ggb(args, name, translator, **kwargs):
        c1, c2 = args["circle1"], args["circle2"]

        d_name = translator._emit(
            name=f"dist_{name}",
            expression=f"Distance(Center({c1}), Center({c2}))",
            ggb_type="numeric",
            hidden=True,
        )

        r1_name = translator._emit(
            name=f"r1_{name}",
            expression=f"Radius({c1})",
            ggb_type="numeric",
            hidden=True,
        )

        r2_name = translator._emit(
            name=f"r2_{name}",
            expression=f"Radius({c2})",
            ggb_type="numeric",
            hidden=True,
        )

        x1_name = translator._emit(
            name=f"x1_{name}",
            expression=f"({d_name}^2 + {r1_name}^2 - {r2_name}^2) / (2 * {d_name})",
            ggb_type="numeric",
            hidden=True,
        )

        T_name = translator._emit(
            name=f"T_{name}",
            expression=f"Center({c1}) + {x1_name} * UnitVector(Center({c2}) - Center({c1}))",
            ggb_type="point",
            hidden=True,
        )

        return f"PerpendicularLine({T_name}, Line(Center({c1}), Center({c2})))"


@register("Line", "PolarLine")
class PolarLineOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        pt, circ_ref = args["point"], args["object"]

        def step(env):
            p = env[pt]
            (xc, yc), r = env[circ_ref]
            a = p[0] - xc
            b = p[1] - yc
            c = -(p[0] - xc) * xc - (p[1] - yc) * yc - r**2
            norm = math.hypot(a, b)
            if norm < 1e-9:
                raise ValueError("Точка в центре окружности")
            env[name] = (a / norm, b / norm, c / norm)

        return step

    @staticmethod
    def to_ggb(args, name, **kwargs):
        return f"Polar({args['point']}, {args['object']})"


@register("Line", "EulerLine")
class EulerLineOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        triangle = args["triangle"]

        def step(env):
            A, B, C = env[triangle[0]], env[triangle[1]], env[triangle[2]]
            env[name] = line_from_points(centroid(A, B, C), circumcenter(A, B, C))

        return step

    @staticmethod
    def to_ggb(args, name, translator, **kwargs):
        A, B, C = args["triangle"][0], args["triangle"][1], args["triangle"][2]
        g_name, cc_name = f"helper_centroid_{name}", f"helper_cc_{name}"
        translator._emit(
            name=g_name,
            expression=f"TriangleCenter({A}, {B}, {C}, 2)",
            ggb_type="point",
            hidden=True,
        )
        translator._emit(
            name=cc_name,
            expression=f"TriangleCenter({A}, {B}, {C}, 3)",
            ggb_type="point",
            hidden=True,
        )
        return f"Line({g_name}, {cc_name})"


@register("Line", "SimsonLine")
class SimsonLineOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        pt, triangle = args["point"], args["triangle"]

        def step(env):
            P = env[pt]
            A, B, C = env[triangle[0]], env[triangle[1]], env[triangle[2]]
            p1 = project_point_on_line(P, line_from_points(A, B))
            p2 = project_point_on_line(P, line_from_points(B, C))
            env[name] = line_from_points(p1, p2)

        return step

    @staticmethod
    def to_ggb(args, name, translator, **kwargs):
        P = args["point"]
        A, B, C = args["triangle"][0], args["triangle"][1], args["triangle"][2]
        p1_name, p2_name = f"proj1_{name}", f"proj2_{name}"
        translator._emit(
            name=p1_name,
            expression=f"ClosestPoint(Line({A}, {B}), {P})",
            ggb_type="point",
            hidden=True,
        )
        translator._emit(
            name=p2_name,
            expression=f"ClosestPoint(Line({B}, {C}), {P})",
            ggb_type="point",
            hidden=True,
        )
        return f"Line({p1_name}, {p2_name})"


@register("Line", "Symmedian")
class SymmedianOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        triangle = args["triangle"]
        v = args["vertex"]
        ends = [p for p in triangle if p != v]

        def step(env):
            va, eb, ec = env[v], env[ends[0]], env[ends[1]]
            mid = ((eb[0] + ec[0]) / 2, (eb[1] + ec[1]) / 2)
            env[name] = line_from_points(
                va, reflect_point_on_line(mid, angle_bisector(va, eb, ec))
            )

        return step

    @staticmethod
    def to_ggb(args, name, translator, **kwargs):
        triangle = args["triangle"]
        v = args["vertex"]
        ends = [p for p in triangle if p != v]
        med_name, bis_name = f"med_{name}", f"bis_{name}"
        translator._emit(
            name=med_name,
            expression=f"Line({v}, Midpoint({ends[0]}, {ends[1]}))",
            ggb_type="line",
            hidden=True,
        )
        translator._emit(
            name=bis_name,
            expression=f"AngleBisector({ends[0]}, {v}, {ends[1]})",
            ggb_type="line",
            hidden=True,
        )
        return f"Reflect({med_name}, {bis_name})"
