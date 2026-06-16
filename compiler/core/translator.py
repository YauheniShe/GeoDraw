import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union

from compiler.models import GeoDraftDocument, GeoObject
from compiler.operations import *  # noqa
from compiler.operations.registry import GGB_REGISTRY


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
        "Curve": "locus",
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
        name = kwargs["name"]
        self.instructions.append(GGBInstruction(**kwargs))
        return name

    def translate_document(self, doc: GeoDraftDocument) -> List[GGBInstruction]:
        self.instructions.clear()
        doc_obj_types = self._build_doc_types(doc)
        for obj in doc.construction:
            self._translate_object(obj, None, doc_obj_types)
        return self.instructions

    def translate_project(
        self, doc: GeoDraftDocument, sampled_state: Optional[Dict[str, Any]] = None
    ) -> CompiledProject:
        self.instructions.clear()
        doc_obj_types = self._build_doc_types(doc)

        for obj in doc.construction:
            self._translate_object(obj, sampled_state, doc_obj_types)

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

        for idx, goal in enumerate(doc.goals):
            g_type = goal.get("type")
            g_args = goal.get("args", [])
            if g_type == "Belongs" and len(g_args) >= 2:
                point_name, obj_name = g_args[0], g_args[1]
                obj_type_raw = doc_obj_types.get(obj_name, "Line")
                obj_type = self.GOAL_OBJ_TYPE_MAP.get(obj_type_raw, "line")
                name_obj = self._emit(
                    name=f"goalBelongsObj_{point_name}_{obj_name}_{idx}",
                    expression=obj_name,
                    ggb_type=obj_type,
                    is_goal=True,
                )
                visibility[name_obj] = True
                name_pt = self._emit(
                    name=f"goalBelongsPt_{point_name}_{obj_name}_{idx}",
                    expression=point_name,
                    ggb_type="point",
                    is_goal=True,
                    coords=sampled_state.get(point_name) if sampled_state else None,
                )
                visibility[name_pt] = True
            elif g_type == "Collinear" and len(g_args) >= 2:
                name = self._emit(
                    name=f"goalCollinear_{idx}",
                    expression=f"Line({g_args[0]}, {g_args[1]})",
                    ggb_type="line",
                    is_goal=True,
                )
                visibility[name] = True
            elif g_type == "Concyclic" and len(g_args) >= 3:
                name = self._emit(
                    name=f"goalConcyclic_{idx}",
                    expression=f"Circle({g_args[0]}, {g_args[1]}, {g_args[2]})",
                    ggb_type="conic",
                    is_goal=True,
                )
                visibility[name] = True
            elif g_type == "Equal":
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
            elif g_type == "Concurrent" and len(g_args) >= 2:
                name = self._emit(
                    name=f"goalConcurrent_{idx}",
                    expression=f"Intersect({g_args[0]}, {g_args[1]})",
                    ggb_type="point",
                    is_goal=True,
                )
                visibility[name] = True
        return CompiledProject(instructions=self.instructions, visibility=visibility)

    def _build_doc_types(self, doc: GeoDraftDocument) -> Dict[str, str]:
        doc_types = {}
        for obj in doc.construction:
            if obj.name:
                doc_types[obj.name] = obj.type
            elif obj.names:
                for n in obj.names:
                    doc_types[n] = obj.type
        return doc_types

    def _translate_object(
        self,
        obj: GeoObject,
        sampled_state: Optional[Dict[str, Any]] = None,
        doc_obj_types: Optional[Dict[str, str]] = None,
    ):
        doc_obj_types = doc_obj_types or {}

        if obj.names:
            self._map_method_to_ggb(
                obj.type,
                obj.method or "Free",
                obj.args or {},
                obj.disambiguation,
                obj.names,
                sampled_state,
                doc_obj_types,
            )
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

        if obj.type == "MathExpression":
            translated_expr = self._translate_math_expression(
                args.get("expression", ""), args.get("variables", {})
            )
            self._emit(
                name=name, expression=translated_expr, ggb_type="numeric", hidden=hidden
            )
            return
        elif obj.type == "Distance":
            pts = args.get("points", [])
            self._emit(
                name=name,
                expression=f"Distance({pts[0]}, {pts[1]})",
                ggb_type="numeric",
                hidden=hidden,
            )
            return
        elif obj.type == "AngleMeasure":
            ends = args.get("ends", [])
            raw_ang = f"Angle({ends[0]}, {args.get('vertex')}, {ends[1]})"
            self._emit(
                name=name,
                expression=f"If({raw_ang} > 180°, 360° - {raw_ang}, {raw_ang})",
                ggb_type="numeric",
                hidden=hidden,
            )
            return
        elif obj.type == "Number":
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
            sampled_state,
            doc_obj_types,
        )
        ggb_type = self.GGB_TYPE_MAP.get(obj.type, "numeric")
        crd = sampled_state.get(name) if (sampled_state and name is not None) else None

        if expr_str:
            self._emit(
                name=name,
                expression=expr_str,
                ggb_type=ggb_type,
                hidden=hidden,
                coords=crd,
            )

    def _var_to_ggb(self, var_obj: Any) -> str:
        if isinstance(var_obj, str):
            return var_obj
        if isinstance(var_obj, dict):
            v_type = var_obj.get("type")
            if v_type == "Distance":
                pts = var_obj.get("points", ["", ""])
                return f"Distance({pts[0]}, {pts[1]})"
            elif v_type == "AngleMeasure":
                ends = var_obj.get("ends", ["", ""])
                v = var_obj.get("vertex", "")
                raw_ang = f"Angle({ends[0]}, {v}, {ends[1]})"
                return f"If({raw_ang} > 180°, 360° - {raw_ang}, {raw_ang})"
            elif v_type == "Number":
                return str(var_obj.get("value"))
        return str(var_obj)

    def _translate_math_expression(self, expression: str, variables: dict) -> str:
        if not variables:
            return expression
        sorted_vars = sorted(variables.keys(), key=len, reverse=True)
        pattern = re.compile(rf"\b({'|'.join(map(re.escape, sorted_vars))})\b")
        return pattern.sub(
            lambda m: self._var_to_ggb(variables[m.group(0)]), expression
        )

    def _map_method_to_ggb(
        self,
        obj_type: str,
        method: str,
        args: dict,
        disambig: dict | None,
        name: Union[str, List[str], tuple, None],
        sampled_state: dict | None,
        doc_obj_types: dict,
    ) -> str:
        registry_key = (obj_type, method)
        if registry_key in GGB_REGISTRY:
            ggb_func = GGB_REGISTRY[registry_key]
            return ggb_func(
                args=args,
                name=name,
                disambiguation=disambig,
                sampled_state=sampled_state,
                doc_obj_types=doc_obj_types,
                translator=self,
            )
        return "UNDEFINED"
