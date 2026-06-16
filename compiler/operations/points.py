import math
import random

from compiler.core.disambiguation import select_disambiguation
from compiler.core.evaluators import compile_value_argument
from compiler.math_lib.base import (
    centroid,
    circumcenter,
    dist,
    get_line_eq,
    incenter,
    intersect_circle_circle,
    intersect_line_circle,
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


@register("Point", "Intersection")
class IntersectionOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        o1, o2 = args.get("obj1"), args.get("obj2")
        rule = (
            disambiguation.get("rule", "algebraic_index")
            if disambiguation
            else "algebraic_index"
        )
        d_params = disambiguation or {}

        def step(env):
            obj1, obj2 = env[o1], env[o2]
            l1, l2 = get_line_eq(obj1), get_line_eq(obj2)
            if l1 and l2:
                a1, b1, c1 = l1
                a2, b2, c2 = l2
                det = a1 * b2 - a2 * b1
                if abs(det) < 1e-9:
                    raise ValueError("Прямые параллельны")
                env[name] = ((b1 * c2 - b2 * c1) / det, (c1 * a2 - c2 * a1) / det)
            elif l1 and not l2:
                env[name] = select_disambiguation(
                    intersect_line_circle(l1, obj2), rule, d_params, env
                )
            elif not l1 and l2:
                env[name] = select_disambiguation(
                    intersect_line_circle(l2, obj1), rule, d_params, env
                )
            else:
                env[name] = select_disambiguation(
                    intersect_circle_circle(obj1, obj2), rule, d_params, env
                )

        return step

    @staticmethod
    def to_ggb(
        args, name: str, disambiguation, doc_obj_types, translator, **kwargs
    ) -> str:  # type: ignore
        obj1, obj2 = args.get("obj1"), args.get("obj2")
        if not disambiguation:
            return f"Intersect({obj1}, {obj2}, 1)"

        rule = disambiguation.get("rule")
        if rule == "algebraic_index":
            return f"Intersect({obj1}, {obj2}, {disambiguation.get('index', 1)})"

        t1 = doc_obj_types.get(obj1, "Line")
        t2 = doc_obj_types.get(obj2, "Line")
        linear_types = {"Line", "Segment", "Ray"}

        if t1 in linear_types and t2 in linear_types:
            return f"Intersect({obj1}, {obj2})"

        translator._emit(
            name=f"{name}I1",
            expression=f"Intersect({obj1}, {obj2}, 1)",
            ggb_type="point",
            hidden=True,
        )
        translator._emit(
            name=f"{name}I2",
            expression=f"Intersect({obj1}, {obj2}, 2)",
            ggb_type="point",
            hidden=True,
        )

        if rule in ("closest_to", "furthest_from"):
            tgt = disambiguation.get("target")
            op = "<" if rule == "closest_to" else ">"
            return f"If(Distance({name}I1, {tgt}) {op} Distance({name}I2, {tgt}), {name}I1, {name}I2)"

        elif rule == "not_equal":
            return f"If({name}I1 == {disambiguation.get('target')}, {name}I2, {name}I1)"

        elif rule in ("same_side_of_line", "opposite_side_of_line"):
            ln, pt = disambiguation.get("line"), disambiguation.get("point")
            cond = f"(({pt} - ClosestPoint({ln}, {pt})) * ({name}I1 - ClosestPoint({ln}, {name}I1)))"
            op = ">" if rule == "same_side_of_line" else "<"
            return f"If({cond} {op} 0, {name}I1, {name}I2)"


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
