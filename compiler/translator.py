import math
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .models import GeoDraftDocument, GeoObject


@dataclass
class GGBInstruction:
    name: str
    expression: str
    hidden: bool = False
    ggb_type: str = "numeric"
    coords: Optional[tuple] = None
    is_goal: bool = False


@dataclass
class CompiledProject:
    instructions: List[GGBInstruction]
    visibility: Dict[str, bool]


class GeoDraftTranslator:
    GGB_TYPE_MAP = {
        "Point": "point",
        "Line": "line",
        "Segment": "segment",
        "Ray": "ray",
        "Circle": "conic",
        "Angle": "angle",
        "Number": "numeric",
        "Distance": "numeric",
        "AngleMeasure": "numeric",
        "MathExpression": "numeric",
    }

    GOAL_OBJ_TYPE_MAP = {
        "Line": "line",
        "Circle": "conic",
        "Segment": "segment",
        "Ray": "ray",
    }

    def __init__(self):
        self.instructions: List[GGBInstruction] = []

    def _emit(self, **kwargs) -> str:
        """Вспомогательный метод для добавления инструкции."""
        name = kwargs["name"]
        self.instructions.append(GGBInstruction(**kwargs))
        return name

    def translate_document(self, doc: GeoDraftDocument) -> List[GGBInstruction]:
        self.instructions.clear()
        for obj in doc.construction:
            self._translate_object(obj)
        return self.instructions

    def translate_project(
        self, doc: GeoDraftDocument, sampled_state: Optional[Dict[str, Any]] = None
    ) -> CompiledProject:
        """Полная компиляция проекта: construction + view"""
        self.instructions.clear()

        for obj in doc.construction:
            self._translate_object(obj, sampled_state)

        visibility: Dict[str, bool] = {
            instr.name: not instr.hidden for instr in self.instructions if instr.name
        }

        for action_data in doc.view:
            action = action_data.get("action")
            targets = action_data.get("targets", [])

            if action in ("Hide", "Show"):
                state = action == "Show"
                for t in targets:
                    if t in visibility:
                        visibility[t] = state

            elif action == "Clip":
                target = action_data.get("target")
                if target in visibility:
                    visibility[target] = False

                new_name = f"view{target}"
                if "endpoints" in action_data:
                    ep = action_data["endpoints"]
                    self._emit(
                        name=new_name,
                        expression=f"Segment({ep[0]}, {ep[1]})",
                        ggb_type="segment",
                    )
                    visibility[new_name] = True
                elif "ray_from" in action_data:
                    self._emit(
                        name=new_name,
                        expression=f"Ray({action_data['ray_from']}, {action_data['towards']})",
                        ggb_type="ray",
                    )
                    visibility[new_name] = True

            elif action == "DrawSegment":
                ep = action_data.get("endpoints", [])
                new_name = self._emit(
                    name=f"drawSeg{ep[0]}{ep[1]}",
                    expression=f"Segment({ep[0]}, {ep[1]})",
                    ggb_type="segment",
                )
                visibility[new_name] = True

            elif action == "DrawPolygon":
                v = action_data.get("vertices", [])
                new_name = self._emit(
                    name=f"drawPoly{''.join(v)}",
                    expression=f"Polygon({', '.join(v)})",
                    ggb_type="polygon",
                )
                visibility[new_name] = True

            elif action == "DrawAngle":
                v = action_data.get("vertex")
                ends = action_data.get("ends", [])
                new_name = self._emit(
                    name=f"drawAngle{ends[0]}{v}{ends[1]}",
                    expression=f"Angle({ends[0]}, {v}, {ends[1]})",
                    ggb_type="angle",
                )
                visibility[new_name] = True

        doc_obj_types = {obj.name: obj.type for obj in doc.construction}

        for idx, goal in enumerate(doc.goals):
            g_type = goal.get("type")
            g_args = goal.get("args", [])

            match g_type:
                case "Belongs" if len(g_args) >= 2:
                    point_name, obj_name = g_args[0], g_args[1]
                    obj_type_raw = doc_obj_types.get(obj_name, "Line")
                    obj_type = self.GOAL_OBJ_TYPE_MAP.get(obj_type_raw, "line")

                    name = self._emit(
                        name=f"goalBelongs_{point_name}_{obj_name}_{idx}",
                        expression=obj_name,
                        ggb_type=obj_type,
                        is_goal=True,
                    )
                    visibility[name] = True

                case "Collinear" if len(g_args) >= 2:
                    name = self._emit(
                        name=f"goalCollinear_{idx}",
                        expression=f"Line({g_args[0]}, {g_args[1]})",
                        ggb_type="line",
                        is_goal=True,
                    )
                    visibility[name] = True

                case "Concyclic" if len(g_args) >= 3:
                    name = self._emit(
                        name=f"goalConcyclic_{idx}",
                        expression=f"Circle({g_args[0]}, {g_args[1]}, {g_args[2]})",
                        ggb_type="conic",
                        is_goal=True,
                    )
                    visibility[name] = True

                case "Equal":
                    for arg in g_args:
                        if isinstance(arg, dict):
                            if arg.get("type") == "Distance":
                                pts = arg["points"]
                                name = self._emit(
                                    name=f"goalSeg_{pts[0]}{pts[1]}_{idx}",
                                    expression=f"Segment({pts[0]}, {pts[1]})",
                                    ggb_type="segment",
                                    is_goal=True,
                                )
                                visibility[name] = True
                            elif arg.get("type") == "AngleMeasure":
                                v, ends = arg["vertex"], arg["ends"]
                                name = self._emit(
                                    name=f"goalAng_{ends[0]}{v}{ends[1]}_{idx}",
                                    expression=f"Angle({ends[0]}, {v}, {ends[1]})",
                                    ggb_type="angle",
                                    is_goal=True,
                                )
                                visibility[name] = True

                case "Concurrent" if len(g_args) >= 2:
                    name = self._emit(
                        name=f"goalConcurrent_{idx}",
                        expression=f"Intersect({g_args[0]}, {g_args[1]})",
                        ggb_type="point",
                        is_goal=True,
                    )
                    visibility[name] = True

        return CompiledProject(instructions=self.instructions, visibility=visibility)

    def _translate_object(
        self, obj: GeoObject, sampled_state: Optional[Dict[str, Any]] = None
    ):
        if obj.names:
            self._translate_macro(obj, sampled_state)
            return

        name = obj.name
        args = obj.args or {}
        hidden = obj.hidden

        if (
            obj.type == "Point"
            and obj.method == "Free"
            and sampled_state
            and name in sampled_state
        ):
            pos = sampled_state[name]
            self._emit(
                name=name,
                expression=f"({pos[0]:.3f}, {pos[1]:.3f})",
                ggb_type="point",
                hidden=hidden,
            )
            return

        match obj.type:
            case "MathExpression":
                translated_expr = self._translate_math_expression(
                    args.get("expression", ""), args.get("variables", {})
                )
                self._emit(
                    name=name,
                    expression=translated_expr,
                    ggb_type="numeric",
                    hidden=hidden,
                )
                return
            case "Distance":
                pts = args.get("points", [])
                self._emit(
                    name=name,
                    expression=f"Distance({pts[0]}, {pts[1]})",
                    ggb_type="numeric",
                    hidden=hidden,
                )
                return
            case "AngleMeasure":
                self._emit(
                    name=name,
                    expression=f"Angle({args.get('ends', [])[0]}, {args.get('vertex')}, {args.get('ends', [])[1]})",
                    ggb_type="numeric",
                    hidden=hidden,
                )
                return
            case "Number":
                self._emit(
                    name=name,
                    expression=str(args.get("value")),
                    ggb_type="numeric",
                    hidden=hidden,
                )
                return

        method = obj.method or "Free"
        expr_str = self._map_method_to_ggb(
            obj.type,
            method,
            args,
            obj.disambiguation,
            name,
            sampled_state,  # type: ignore
        )

        ggb_type = self.GGB_TYPE_MAP.get(obj.type, "numeric")
        crd = sampled_state[name] if sampled_state else None  # type: ignore

        self._emit(
            name=name, expression=expr_str, ggb_type=ggb_type, hidden=hidden, coords=crd
        )

    def _translate_math_expression(self, expression: str, variables: dict) -> str:
        """Однопроходная регулярка (вместо N-проходов) для молниеносной замены."""
        if not variables:
            return expression

        sorted_vars = sorted(variables.keys(), key=len, reverse=True)
        pattern = re.compile(rf"\b({'|'.join(map(re.escape, sorted_vars))})\b")
        return pattern.sub(lambda m: variables[m.group(0)], expression)

    def _map_method_to_ggb(
        self,
        obj_type: str,
        method: str,
        args: dict,
        disambig: dict | None,
        name: str | None,
        sampled_state: dict,
    ) -> str:

        match method:
            case "Reflection":
                return f"Reflect({args.get('target')}, {args.get('axis')})"
            case "PointReflection":
                return f"Reflect({args.get('target')}, {args.get('center')})"
            case "Translation":
                return f"Translate({args.get('target')}, Vector({args['vector'][0]}, {args['vector'][1]}))"
            case "Rotation":
                return f"Rotate({args.get('target')}, {args.get('angle')}, {args.get('center')})"
            case "Homothety":
                return f"Dilate({args.get('target')}, {args.get('ratio')}, {args.get('center')})"
            case "Inversion":
                return f"Reflect({args.get('target')}, {args.get('circle')})"

        if obj_type == "Point":
            match method:
                case "Free":
                    pos = args.get("approx_position", [0, 0])
                    return f"({pos[0]}, {pos[1]})"
                case "PointOnObject":
                    return f"Point({args.get('object')})"
                case "PointOnSegment":
                    return f"(1 - {args.get('ratio')}) * {args['points'][0]} + {args.get('ratio')} * {args['points'][1]}"
                case "PointOnRay":
                    return f"{args['points'][0]} + {args.get('distance')} * UnitVector({args['points'][1]} - {args['points'][0]})"
                case "Midpoint":
                    return f"Midpoint({args['points'][0]}, {args['points'][1]})"
                case "Center":
                    return f"Center({args.get('object')})"
                case "Incenter" | "Centroid" | "Circumcenter" | "Orthocenter":
                    idx = {
                        "Incenter": 1,
                        "Centroid": 2,
                        "Circumcenter": 3,
                        "Orthocenter": 4,
                    }[method]
                    return f"TriangleCenter({args['triangle'][0]}, {args['triangle'][1]}, {args['triangle'][2]}, {idx})"
                case "ETC":
                    return f"TriangleCenter({args['triangle'][0]}, {args['triangle'][1]}, {args['triangle'][2]}, {args.get('index')})"
                case "Projection":
                    return f"ClosestPoint({args.get('line')}, {args.get('point')})"
                case "Intersection":
                    obj1, obj2 = args.get("obj1"), args.get("obj2")
                    if not disambig:
                        return f"Intersect({obj1}, {obj2}, 1)"

                    rule = disambig.get("rule")
                    if rule == "algebraic_index":
                        return f"Intersect({obj1}, {obj2}, {disambig.get('index', 1)})"

                    self._emit(
                        name=f"{name}I1",
                        expression=f"Intersect({obj1}, {obj2}, 1)",
                        ggb_type="point",
                        hidden=True,
                    )
                    self._emit(
                        name=f"{name}I2",
                        expression=f"Intersect({obj1}, {obj2}, 2)",
                        ggb_type="point",
                        hidden=True,
                    )

                    if rule in ("closest_to", "furthest_from"):
                        tgt = disambig.get("target")
                        op = "<" if rule == "closest_to" else ">"
                        return f"If(Distance({name}I1, {tgt}) {op} Distance({name}I2, {tgt}), {name}I1, {name}I2)"

                    elif rule == "not_equal":
                        return f"If({name}I1 == {disambig.get('target')}, {name}I2, {name}I1)"

                    elif rule in ("same_side_of_line", "opposite_side_of_line"):
                        ln, pt = disambig.get("line"), disambig.get("point")
                        cond = f"(({pt} - ClosestPoint({ln}, {pt})) * ({name}I1 - ClosestPoint({ln}, {name}I1)))"
                        op = ">" if rule == "same_side_of_line" else "<"
                        return f"If({cond} {op} 0, {name}I1, {name}I2)"

        elif obj_type == "Line":
            match method:
                case "LineThrough":
                    return f"Line({args['points'][0]}, {args['points'][1]})"
                case "ParallelLine":
                    return f"Line({args.get('point')}, {args.get('line')})"
                case "PerpendicularLine":
                    return f"PerpendicularLine({args.get('point')}, {args.get('line')})"
                case "PerpendicularBisector":
                    return f"PerpendicularBisector({args['points'][0]}, {args['points'][1]})"
                case "AngleBisector":
                    return f"AngleBisector({args['ends'][0]}, {args.get('vertex')}, {args['ends'][1]})"
                case "CommonTangent":
                    idx = disambig.get("algebraic_index", 1) if disambig else 1
                    return f"Element({{Tangent({args.get('circle1')}, {args.get('circle2')})}}, {idx})"

        elif obj_type == "Circle":
            match method:
                case "CenterRadius":
                    return f"Circle({args.get('center')}, {args.get('radius')})"
                case "DiameterCircle":
                    return f"Circle(Midpoint({args['points'][0]}, {args['points'][1]}), {args['points'][0]})"
                case "Circumcircle":
                    return f"Circle({args['triangle'][0]}, {args['triangle'][1]}, {args['triangle'][2]})"
                case "Incircle":
                    return f"Incircle({args['triangle'][0]}, {args['triangle'][1]}, {args['triangle'][2]})"
                case "ApolloniusCircle":
                    p0, p1, ratio = (
                        args["points"][0],
                        args["points"][1],
                        args.get("ratio"),
                    )
                    self._emit(
                        name=f"{name}In",
                        expression=f"({p0} + ({ratio}) * {p1}) / (1 + ({ratio}))",
                        ggb_type="point",
                        hidden=True,
                    )
                    self._emit(
                        name=f"{name}Out",
                        expression=f"({p0} - ({ratio}) * {p1}) / (1 - ({ratio}))",
                        ggb_type="point",
                        hidden=True,
                    )
                    return f"Circle(Midpoint({name}In, {name}Out), {name}In)"

        elif obj_type in ("Segment", "Ray"):
            return f"{obj_type}({args['points'][0]}, {args['points'][1]})"

        return "UNDEFINED"

    def _get_sampled_points(
        self, names: List[str], state: Optional[Dict[str, Any]]
    ) -> Optional[List[tuple]]:
        """Удобная выжимка всех требуемых координат."""
        if state and all(n in state for n in names):
            return [state[n] for n in names]
        return None

    def _translate_macro(
        self, obj: GeoObject, sampled_state: Optional[Dict[str, Any]] = None
    ):
        names = obj.names

        if names is None:
            return None

        match obj.method:
            case "Parallelogram":
                pts = self._get_sampled_points(names[:3], sampled_state) or [
                    (0, 0),
                    (3, 0),
                    (4, 3),
                ]
                for i in range(3):
                    self._emit(
                        name=names[i],
                        expression=f"({pts[i][0]:.3f}, {pts[i][1]:.3f})",
                        ggb_type="point",
                    )
                self._emit(
                    name=names[3],
                    expression=f"{names[0]} + {names[2]} - {names[1]}",
                    ggb_type="point",
                )

            case "FreeTriangle":
                pts = self._get_sampled_points(names[:3], sampled_state) or [
                    (0, 0),
                    (4, 0),
                    (1, 3),
                ]
                for i in range(3):
                    self._emit(
                        name=names[i],
                        expression=f"({pts[i][0]:.3f}, {pts[i][1]:.3f})",
                        ggb_type="point",
                    )

            case "Square":
                self._emit(name=names[0], expression="(0, 0)", ggb_type="point")
                self._emit(name=names[1], expression="(3, 0)", ggb_type="point")
                self._emit(
                    name=names[2],
                    expression=f"Rotate({names[0]}, -90°, {names[1]})",
                    ggb_type="point",
                )
                self._emit(
                    name=names[3],
                    expression=f"Rotate({names[1]}, 90°, {names[0]})",
                    ggb_type="point",
                )

            case "EquilateralTriangle":
                self._emit(name=names[0], expression="(0, 0)", ggb_type="point")
                self._emit(name=names[1], expression="(3, 0)", ggb_type="point")
                self._emit(
                    name=names[2],
                    expression=f"Rotate({names[1]}, 60°, {names[0]})",
                    ggb_type="point",
                )

            case "CyclicQuadrilateral":
                pts = self._get_sampled_points(names[:4], sampled_state)
                if not pts:
                    pts = [
                        (
                            3 * math.cos(math.radians(ang)),
                            3 * math.sin(math.radians(ang)),
                        )
                        for ang in (0.0, 70.0, 140.0, 240.0)
                    ]

                for i in range(3):
                    self._emit(
                        name=names[i],
                        expression=f"({pts[i][0]:.3f}, {pts[i][1]:.3f})",
                        ggb_type="point",
                    )

                circ_name = f"circ_{names[0]}{names[1]}{names[2]}"
                self._emit(
                    name=circ_name,
                    expression=f"Circle({names[0]}, {names[1]}, {names[2]})",
                    ggb_type="conic",
                    hidden=True,
                )
                self._emit(
                    name=names[3],
                    expression=f"Point({circ_name})",
                    ggb_type="point",
                    coords=(pts[3][0], pts[3][1]),
                )
