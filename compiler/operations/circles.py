import math
import re

from compiler.core.evaluators import compile_value_argument
from compiler.math_lib.base import (
    apollonius_circle,
    circumcircle,
    dist,
    incenter,
    line_from_points,
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
@register("Segment", "SegmentByPoints")
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
@register("Ray", "RayByPoints")
class RayOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        if "origin" in args and "direction_point" in args:
            p0, p1 = args["origin"], args["direction_point"]
        else:
            p0, p1 = args["points"]

        def step(env):
            env[name] = ("ray", env[p0], env[p1])

        return step

    @staticmethod
    def to_ggb(args, name, **kwargs):
        if "origin" in args and "direction_point" in args:
            p0, p1 = args["origin"], args["direction_point"]
        else:
            p0, p1 = args["points"]
        return f"Ray({p0}, {p1})"


@register("Ray", "RayByAngle")
class RayByAngleOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        ray_ref = args["ray"]
        ang_eval = compile_value_argument(args["angle"])
        orient = (
            disambiguation.get("orientation", "counterclockwise")
            if disambiguation
            else "counterclockwise"
        )

        def step(env):
            ray = env[ray_ref]
            start, direction = ray[1], ray[2]
            theta = -ang_eval(env) if orient == "clockwise" else ang_eval(env)
            cos_t, sin_t = math.cos(theta), math.sin(theta)
            dx, dy = direction[0] - start[0], direction[1] - start[1]
            env[name] = (
                "ray",
                start,
                (
                    start[0] + dx * cos_t - dy * sin_t,
                    start[1] + dx * sin_t + dy * cos_t,
                ),
            )

        return step

    @staticmethod
    def to_ggb(args, name, translator, disambiguation, **kwargs):
        ang_str = translator._var_to_ggb(args["angle"])
        orient = "counterclockwise"
        if disambiguation:
            orient = disambiguation.get(
                "value", disambiguation.get("orientation", "counterclockwise")
            )
        if orient == "clockwise":
            ang_str = f"-({ang_str})"

        ray_name = args["ray"]
        ray_instr = next(
            (inst for inst in translator.instructions if inst.name == ray_name), None
        )
        start_pt = "A"
        if ray_instr:
            m = re.match(r"Ray\(([^,]+),", ray_instr.expression)
            if m:
                start_pt = m.group(1).strip()

        return f"Rotate({args['ray']}, {ang_str}, {start_pt})"


@register("Circle", "Incircle")
class IncircleOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        triangle = args["triangle"]

        def step(env):
            p1, p2, p3 = env[triangle[0]], env[triangle[1]], env[triangle[2]]
            inc = incenter(p1, p2, p3)
            a, b, c = line_from_points(p1, p2)
            r = abs(a * inc[0] + b * inc[1] + c) / math.hypot(a, b)
            env[name] = (inc, r)

        return step

    @staticmethod
    def to_ggb(args, name, translator, **kwargs):
        A, B, C = args["triangle"][0], args["triangle"][1], args["triangle"][2]
        inc_name = f"inc_{name}"
        translator._emit(
            name=inc_name,
            expression=f"TriangleCenter({A}, {B}, {C}, 1)",
            ggb_type="point",
            hidden=True,
        )
        return f"Circle({inc_name}, ClosestPoint(Line({A}, {B}), {inc_name}))"


@register("Circle", "Excircle")
class ExcircleOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        triangle = args["triangle"]
        v = args["vertex"]
        ends = [p for p in triangle if p != v]

        def step(env):
            pt_v, pt_b, pt_c = env[v], env[ends[0]], env[ends[1]]
            a, b, c = dist(pt_b, pt_c), dist(pt_v, pt_c), dist(pt_v, pt_b)
            total = -a + b + c
            if abs(total) < 1e-9:
                raise ValueError("Вырожденный треугольник")
            ex_center = (
                (-a * pt_v[0] + b * pt_b[0] + c * pt_c[0]) / total,
                (-a * pt_v[1] + b * pt_b[1] + c * pt_c[1]) / total,
            )
            a_eq, b_eq, c_eq = line_from_points(pt_b, pt_c)
            r = abs(a_eq * ex_center[0] + b_eq * ex_center[1] + c_eq) / math.hypot(
                a_eq, b_eq
            )
            env[name] = (ex_center, r)

        return step

    @staticmethod
    def to_ggb(args, name, translator, **kwargs):
        triangle = args["triangle"]
        v = args["vertex"]
        ends = [p for p in triangle if p != v]
        bis_ext_b, bis_ext_c = f"bis_ext_b_{name}", f"bis_ext_c_{name}"
        translator._emit(
            name=bis_ext_b,
            expression=f"PerpendicularLine({ends[0]}, AngleBisector({v}, {ends[0]}, {ends[1]}))",
            ggb_type="line",
            hidden=True,
        )
        translator._emit(
            name=bis_ext_c,
            expression=f"PerpendicularLine({ends[1]}, AngleBisector({v}, {ends[1]}, {ends[0]}))",
            ggb_type="line",
            hidden=True,
        )
        exc_center = f"exc_center_{name}"
        translator._emit(
            name=exc_center,
            expression=f"Intersect({bis_ext_b}, {bis_ext_c})",
            ggb_type="point",
            hidden=True,
        )
        return f"Circle({exc_center}, ClosestPoint(Line({ends[0]}, {ends[1]}), {exc_center}))"


@register("Circle", "NinePointCircle")
class NinePointCircleOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        triangle = args["triangle"]

        def step(env):
            p1, p2, p3 = env[triangle[0]], env[triangle[1]], env[triangle[2]]
            m1 = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
            m2 = ((p2[0] + p3[0]) / 2, (p2[1] + p3[1]) / 2)
            m3 = ((p3[0] + p1[0]) / 2, (p3[1] + p1[1]) / 2)
            env[name] = circumcircle(m1, m2, m3)

        return step

    @staticmethod
    def to_ggb(args, name, translator, **kwargs):
        A, B, C = args["triangle"][0], args["triangle"][1], args["triangle"][2]
        m1, m2, m3 = f"m1_{name}", f"m2_{name}", f"m3_{name}"
        translator._emit(
            name=m1, expression=f"Midpoint({A}, {B})", ggb_type="point", hidden=True
        )
        translator._emit(
            name=m2, expression=f"Midpoint({B}, {C})", ggb_type="point", hidden=True
        )
        translator._emit(
            name=m3, expression=f"Midpoint({C}, {A})", ggb_type="point", hidden=True
        )
        return f"Circle({m1}, {m2}, {m3})"


@register("Circle", "MixtilinearIncircle")
class MixtilinearIncircleOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        triangle = args["triangle"]
        v = args["vertex"]
        ends = [p for p in triangle if p != v]

        def step(env):
            pt_a, pt_b, pt_c = env[v], env[ends[0]], env[ends[1]]
            inc = incenter(pt_a, pt_b, pt_c)
            a_ai, b_ai, c_ai = line_from_points(pt_a, inc)
            l_perp = (-b_ai, a_ai, -(-b_ai * inc[0] + a_ai * inc[1]))
            l_ab, _l_ac = line_from_points(pt_a, pt_b), line_from_points(pt_a, pt_c)
            det1 = l_perp[0] * l_ab[1] - l_ab[0] * l_perp[1]
            pt_d = (
                (l_perp[1] * l_ab[2] - l_ab[1] * l_perp[2]) / det1,
                (l_perp[2] * l_ab[0] - l_ab[2] * l_perp[0]) / det1,
            )
            l_perp_d = (-l_ab[1], l_ab[0], -(-l_ab[1] * pt_d[0] + l_ab[0] * pt_d[1]))
            det3 = (
                l_perp_d[0] * a_ai[1] - a_ai[0] * l_perp_d[1]
                if hasattr(a_ai, "__getitem__")
                else l_perp_d[0] * b_ai - a_ai * l_perp_d[1]
            )
            # Точное аналитическое вычисление центра
            bis = line_from_points(pt_a, inc)
            det3 = l_perp_d[0] * bis[1] - bis[0] * l_perp_d[1]
            center = (
                (l_perp_d[1] * bis[2] - bis[1] * l_perp_d[2]) / det3,
                (l_perp_d[2] * bis[0] - bis[2] * l_perp_d[0]) / det3,
            )
            r = abs(l_ab[0] * center[0] + l_ab[1] * center[1] + l_ab[2]) / math.hypot(
                l_ab[0], l_ab[1]
            )
            env[name] = (center, r)

        return step

    @staticmethod
    def to_ggb(args, name, translator, **kwargs):
        triangle = args["triangle"]
        v = args["vertex"]
        ends = [p for p in triangle if p != v]
        A, B, C = v, ends[0], ends[1]
        inc_name, bis_name, l_perp_name = f"inc_{name}", f"bis_{name}", f"l_perp_{name}"
        d_name, perp_d_name, center_name = (
            f"D_{name}",
            f"perp_D_{name}",
            f"center_{name}",
        )

        translator._emit(
            name=inc_name,
            expression=f"TriangleCenter({A}, {B}, {C}, 1)",
            ggb_type="point",
            hidden=True,
        )
        translator._emit(
            name=bis_name,
            expression=f"Line({A}, {inc_name})",
            ggb_type="line",
            hidden=True,
        )
        translator._emit(
            name=l_perp_name,
            expression=f"PerpendicularLine({inc_name}, {bis_name})",
            ggb_type="line",
            hidden=True,
        )
        translator._emit(
            name=d_name,
            expression=f"Intersect({l_perp_name}, Line({A}, {B}))",
            ggb_type="point",
            hidden=True,
        )
        translator._emit(
            name=perp_d_name,
            expression=f"PerpendicularLine({d_name}, Line({A}, {B}))",
            ggb_type="line",
            hidden=True,
        )
        translator._emit(
            name=center_name,
            expression=f"Intersect({perp_d_name}, {bis_name})",
            ggb_type="point",
            hidden=True,
        )
        return f"Circle({center_name}, {d_name})"
