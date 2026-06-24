import math
import random

from compiler.core.evaluators import compile_value_argument
from compiler.math_lib.barycentric import isogonal_conjugate, isotomic_conjugate
from compiler.math_lib.base import (
    centroid,
    circumcenter,
    dist,
    get_line_eq,
    incenter,
    orthocenter,
    project_point_on_line,
)
from compiler.operations.registry import register


@register("Point", "Free")
class FreePointOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        approx = args.get("approx_position") if args else None

        def step(env):
            if approx:
                bx, by = approx[0], approx[1]
            else:
                bx, by = random.uniform(-2, 2), random.uniform(-2, 2)

            env[name] = (bx + random.uniform(-1.2, 1.2), by + random.uniform(-1.2, 1.2))

        return step

    @staticmethod
    def to_ggb(args, name: str, disambiguation, sampled_state, **kwargs) -> str:
        if sampled_state and name in sampled_state:
            pos = sampled_state[name]
            return f"({pos[0]:.3f}, {pos[1]:.3f})"

        approx = args.get("approx_position") if args else (0, 0)
        return f"({approx[0]}, {approx[1]})"


@register("Point", "PointOnSegment")
class PointOnSegmentOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        p0, p1 = args["points"]

        r_eval = compile_value_argument(args.get("ratio"))

        def step(env):
            pa, pb = env[p0], env[p1]
            ratio = r_eval(env)
            env[name] = (
                pa[0] + ratio * (pb[0] - pa[0]),
                pa[1] + ratio * (pb[1] - pa[1]),
            )

        return step

    @staticmethod
    def to_ggb(args, name: str, disambiguation, translator, **kwargs) -> str:
        ratio_str = translator._var_to_ggb(args.get("ratio"))
        return f"(1 - ({ratio_str})) * {args['points'][0]} + ({ratio_str}) * {args['points'][1]}"


@register("Point", "PointOnRay")
class PointOnRayOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        p0, p1 = args["points"]

        d_eval = compile_value_argument(args.get("distance"))

        def step(env):
            pa, pb = env[p0], env[p1]
            dist_val = d_eval(env)
            d_ab = dist(pa, pb)
            if d_ab < 1e-9:
                raise ValueError("Точки для луча совпадают")
            env[name] = (
                pa[0] + dist_val * (pb[0] - pa[0]) / d_ab,
                pa[1] + dist_val * (pb[1] - pa[1]) / d_ab,
            )

        return step

    @staticmethod
    def to_ggb(args, name: str, disambiguation, translator, **kwargs) -> str:
        dist_str = translator._var_to_ggb(args.get("distance"))
        return f"{args['points'][0]} + ({dist_str}) * UnitVector({args['points'][1]} - {args['points'][0]})"


@register("Point", "Midpoint")
class MidpointOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        p0, p1 = args["points"]

        def step(env):
            env[name] = ((env[p0][0] + env[p1][0]) / 2, (env[p0][1] + env[p1][1]) / 2)

        return step

    @staticmethod
    def to_ggb(args, name: str, disambiguation, **kwargs) -> str:
        return f"Midpoint({args['points'][0]}, {args['points'][1]})"


@register("Point", "Projection")
class ProjectionOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        pt, line = args.get("point"), args.get("line")

        def step(env):
            env[name] = project_point_on_line(env[pt], env[line])

        return step

    @staticmethod
    def to_ggb(args, name: str, disambiguation, **kwargs) -> str:
        return f"ClosestPoint({args.get('line')}, {args.get('point')})"


@register("Point", "Center")
class CenterOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        obj_ref = args.get("object")

        def step(env):
            env[name] = env[obj_ref][0]

        return step

    @staticmethod
    def to_ggb(args, name: str, disambiguation, **kwargs) -> str:
        return f"Center({args.get('object')})"


@register("Point", "PointOnObject")
class PointOnObjectOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        obj_ref = args.get("object")

        def step(env):
            ref = env[obj_ref]
            param = random.uniform(0.01, 0.99)

            if type(ref) is tuple and len(ref) == 3 and type(ref[0]) is str:
                p1, p2 = ref[1], ref[2]
                if ref[0] == "segment":
                    env[name] = (
                        p1[0] + param * (p2[0] - p1[0]),
                        p1[1] + param * (p2[1] - p1[1]),
                    )
                else:  # ray
                    env[name] = (
                        p1[0] + param * 5 * (p2[0] - p1[0]),
                        p1[1] + param * 5 * (p2[1] - p1[1]),
                    )
            else:
                l_eq = get_line_eq(ref)
                if l_eq:
                    a, b, c = l_eq
                    proj = project_point_on_line((0, 0), l_eq)
                    env[name] = (proj[0] - b * param * 5, proj[1] + a * param * 5)
                else:
                    if isinstance(ref, tuple) and len(ref) == 2:
                        center, radius = ref
                        theta = 2 * math.pi * param
                        env[name] = (
                            center[0] + radius * math.cos(theta),
                            center[1] + radius * math.sin(theta),
                        )

        return step

    @staticmethod
    def to_ggb(args, name: str, disambiguation, **kwargs) -> str:
        return f"Point({args.get('object')})"


# Центры треугольников
@register("Point", "Incenter")
class IncenterOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        t0, t1, t2 = args["triangle"]

        def step(env):
            env[name] = incenter(env[t0], env[t1], env[t2])

        return step

    @staticmethod
    def to_ggb(args, name, **kwargs):
        return f"TriangleCenter({args['triangle'][0]}, {args['triangle'][1]}, {args['triangle'][2]}, 1)"


@register("Point", "Centroid")
class CentroidOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        t0, t1, t2 = args["triangle"]

        def step(env):
            env[name] = centroid(env[t0], env[t1], env[t2])

        return step

    @staticmethod
    def to_ggb(args, name, **kwargs):
        return f"TriangleCenter({args['triangle'][0]}, {args['triangle'][1]}, {args['triangle'][2]}, 2)"


@register("Point", "Circumcenter")
class CircumcenterOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        t0, t1, t2 = args["triangle"]

        def step(env):
            env[name] = circumcenter(env[t0], env[t1], env[t2])

        return step

    @staticmethod
    def to_ggb(args, name, **kwargs):
        return f"TriangleCenter({args['triangle'][0]}, {args['triangle'][1]}, {args['triangle'][2]}, 3)"


@register("Point", "Orthocenter")
class OrthocenterOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        t0, t1, t2 = args["triangle"]

        def step(env):
            env[name] = orthocenter(env[t0], env[t1], env[t2])

        return step

    @staticmethod
    def to_ggb(args, name, **kwargs):
        return f"TriangleCenter({args['triangle'][0]}, {args['triangle'][1]}, {args['triangle'][2]}, 4)"


@register("Point", "ETC")
class ETCOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        triangle = args["triangle"]
        idx = args["index"]

        def step(env):
            p1, p2, p3 = env[triangle[0]], env[triangle[1]], env[triangle[2]]
            if idx == 1:
                env[name] = incenter(p1, p2, p3)
            elif idx == 2:
                env[name] = centroid(p1, p2, p3)
            elif idx == 3:
                env[name] = circumcenter(p1, p2, p3)
            elif idx == 4:
                env[name] = orthocenter(p1, p2, p3)
            elif idx == 5:
                o = orthocenter(p1, p2, p3)
                c = circumcenter(p1, p2, p3)
                env[name] = ((o[0] + c[0]) / 2, (o[1] + c[1]) / 2)
            else:
                env[name] = centroid(p1, p2, p3)

        return step

    @staticmethod
    def to_ggb(args, name, **kwargs):
        return f"TriangleCenter({args['triangle'][0]}, {args['triangle'][1]}, {args['triangle'][2]}, {args['index']})"


@register("Point", "IsogonalConjugate")
class IsogonalConjugateOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        pt, triangle = args["point"], args["triangle"]

        def step(env):
            env[name] = isogonal_conjugate(
                env[pt], env[triangle[0]], env[triangle[1]], env[triangle[2]]
            )

        return step

    @staticmethod
    def to_ggb(args, name, **kwargs):
        pt, triangle = args["point"], args["triangle"]
        A, B, C = triangle[0], triangle[1], triangle[2]

        line_ap = f"Line({A}, {pt})"
        bis_a = f"AngleBisector({B}, {A}, {C})"
        ref_ap = f"Reflect({line_ap}, {bis_a})"

        line_bp = f"Line({B}, {pt})"
        bis_b = f"AngleBisector({A}, {B}, {C})"
        ref_bp = f"Reflect({line_bp}, {bis_b})"

        return f"Intersect({ref_ap}, {ref_bp})"


@register("Point", "IsotomicConjugate")
class IsotomicConjugateOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        pt, triangle = args["point"], args["triangle"]

        def step(env):
            env[name] = isotomic_conjugate(
                env[pt], env[triangle[0]], env[triangle[1]], env[triangle[2]]
            )

        return step

    @staticmethod
    def to_ggb(args, name, translator, **kwargs):
        pt, triangle = args["point"], args["triangle"]
        A, B, C = triangle[0], triangle[1], triangle[2]
        d_name, dp_name = f"helper_D_{name}", f"helper_Dp_{name}"
        e_name, ep_name = f"helper_E_{name}", f"helper_Ep_{name}"

        translator._emit(
            name=d_name,
            expression=f"Intersect(Line({A}, {pt}), Line({B}, {C}))",
            ggb_type="point",
            hidden=True,
        )
        translator._emit(
            name=dp_name,
            expression=f"{B} + {C} - {d_name}",
            ggb_type="point",
            hidden=True,
        )
        translator._emit(
            name=e_name,
            expression=f"Intersect(Line({B}, {pt}), Line({A}, {C}))",
            ggb_type="point",
            hidden=True,
        )
        translator._emit(
            name=ep_name,
            expression=f"{A} + {C} - {e_name}",
            ggb_type="point",
            hidden=True,
        )
        return f"Intersect(Line({A}, {dp_name}), Line({B}, {ep_name}))"


@register("Point", "HarmonicConjugate")
class HarmonicConjugateOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        pts, conj = args["points"], args["conjugate_to"]

        def step(env):
            A, B, C = env[pts[0]], env[pts[1]], env[conj]
            dx_ab, dy_ab = B[0] - A[0], B[1] - A[1]
            dx_ac, dy_ac = C[0] - A[0], C[1] - A[1]
            t = dx_ac / dx_ab if abs(dx_ab) > abs(dy_ab) else dy_ac / dy_ab
            s = t / (2 * t - 1) if abs(2 * t - 1) > 1e-9 else 1e9
            env[name] = (A[0] + s * dx_ab, A[1] + s * dy_ab)

        return step

    @staticmethod
    def to_ggb(args, name, translator, **kwargs):
        pts, conj = args["points"], args["conjugate_to"]
        A, B, C = pts[0], pts[1], conj
        t_name, s_name = f"t_{name}", f"s_{name}"
        translator._emit(
            name=t_name,
            expression=f"If(x({A}) != x({B}), (x({C}) - x({A})) / (x({B}) - x({A})), (y({C}) - y({A})) / (y({B}) - y({A})))",
            ggb_type="numeric",
            hidden=True,
        )
        translator._emit(
            name=s_name,
            expression=f"{t_name} / (2 * {t_name} - 1)",
            ggb_type="numeric",
            hidden=True,
        )
        return f"{A} + {s_name} * ({B} - {A})"
