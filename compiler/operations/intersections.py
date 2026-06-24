from compiler.core.disambiguation import select_disambiguation
from compiler.math_lib.base import (
    get_line_eq,
    intersect_circle_circle,
    intersect_line_circle,
)
from compiler.operations.registry import register


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

        t1 = doc_obj_types.get(obj1, "Line")
        t2 = doc_obj_types.get(obj2, "Line")
        linear_types = {"Line", "Segment", "Ray"}

        if t1 in linear_types and t2 in linear_types:
            return f"Intersect({obj1}, {obj2})"

        if not disambiguation:
            return f"Intersect({obj1}, {obj2}, 1)"

        rule = disambiguation.get("rule")
        if rule == "algebraic_index":
            return f"Intersect({obj1}, {obj2}, {disambiguation.get('index', 1)})"

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
