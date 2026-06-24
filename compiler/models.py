from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator


class DictModel(BaseModel):
    """
    Вспомогательный класс-обертка.
    Позволяет Pydantic-моделям вести себя как словари (dict)
    """

    model_config = {"extra": "forbid"}

    def __getitem__(self, key):
        if not hasattr(self, key):
            raise KeyError(key)
        val = getattr(self, key)
        if val is None and key not in self.model_fields_set:
            raise KeyError(key)
        return val

    def get(self, key, default=None):
        if not hasattr(self, key):
            return default
        val = getattr(self, key)
        if val is None and key not in self.model_fields_set:
            return default
        return val

    def __contains__(self, key):
        if not hasattr(self, key):
            return False
        return key in self.model_fields_set or getattr(self, key) is not None

    def keys(self):
        return [k for k in self.model_fields.keys() if self.__contains__(k)]

    def items(self):
        return [(k, getattr(self, k)) for k in self.keys()]


ConstraintType = Literal["IsAcute", "Inequality", "Convex"]
GoalType = Literal[
    "Belongs",
    "Collinear",
    "Concyclic",
    "Equal",
    "Concurrent",
    "Tangent",
    "Perpendicular",
    "Parallel",
    "Coincident",
]
ViewActionType = Literal[
    "Hide", "Show", "Clip", "DrawSegment", "DrawPolygon", "DrawAngle"
]

Ref = Union[str, Dict[str, Any]]
ScalarRef = Union[str, float, Dict[str, Any]]


class ArgsPoints(DictModel):
    points: List[Ref]


class BaseConstraint(DictModel):
    pass


class ConstraintIsAcute(BaseConstraint):
    type: Literal["IsAcute"]
    args: ArgsPoints


class ConstraintConvex(BaseConstraint):
    type: Literal["Convex"]
    args: ArgsPoints


class ConstraintInequality(BaseConstraint):
    type: Literal["Inequality"]
    operator: Literal[">", "<", ">=", "<=", "=="]
    left: ScalarRef
    right: ScalarRef


ConstraintDef = Union[ConstraintIsAcute, ConstraintConvex, ConstraintInequality]


class GoalArgsPoints(DictModel):
    points: List[Ref]


class GoalArgsLines(DictModel):
    lines: List[Ref]


class GoalArgsObjects(DictModel):
    objects: List[Ref]


class GoalArgsBelongs(DictModel):
    point: Ref
    object: Ref


class GoalArgsEqual(DictModel):
    values: List[ScalarRef]


class BaseGoal(DictModel):
    pass


class GoalBelongs(BaseGoal):
    type: Literal["Belongs"]
    args: GoalArgsBelongs


class GoalCollinearConcyclic(BaseGoal):
    type: Literal["Collinear", "Concyclic"]
    args: GoalArgsPoints


class GoalEqual(BaseGoal):
    type: Literal["Equal"]
    args: GoalArgsEqual


class GoalConcurrentTangentCoincident(BaseGoal):
    type: Literal["Concurrent", "Tangent", "Coincident"]
    args: GoalArgsObjects


class GoalPerpendicularParallel(BaseGoal):
    type: Literal["Perpendicular", "Parallel"]
    args: GoalArgsLines


GoalDef = Union[
    GoalBelongs,
    GoalCollinearConcyclic,
    GoalEqual,
    GoalConcurrentTangentCoincident,
    GoalPerpendicularParallel,
]


class ViewDef(DictModel):
    action: ViewActionType = Field(..., description="Действие визуализации")
    targets: Optional[List[str]] = None
    target: Optional[str] = None
    endpoints: Optional[List[str]] = None
    vertices: Optional[List[str]] = None
    ray_from: Optional[str] = None
    towards: Optional[str] = None
    vertex: Optional[str] = None
    ends: Optional[List[str]] = None


class ArgsTriangle(DictModel):
    triangle: List[Ref]


class ArgsVertexEnds(DictModel):
    vertex: Ref
    ends: List[Ref]


class ArgsIntersection(DictModel):
    obj1: Ref
    obj2: Ref


class ArgsPointRatio(DictModel):
    points: List[Ref]
    ratio: ScalarRef


class ArgsPointDistance(DictModel):
    points: List[Ref]
    distance: ScalarRef


class ArgsPointLine(DictModel):
    point: Ref
    line: Ref


class ArgsPointObject(DictModel):
    point: Ref
    object: Ref


class ArgsTwoCircles(DictModel):
    circle1: Ref
    circle2: Ref


class ArgsLineByAngle(DictModel):
    line: Ref
    point: Ref
    angle: ScalarRef


class ArgsRayByAngle(DictModel):
    ray: Ref
    angle: ScalarRef


class ArgsCenterRadius(DictModel):
    center: Ref
    radius: ScalarRef


class ArgsPointTriangle(DictModel):
    point: Ref
    triangle: List[Ref]


class ArgsTriangleVertex(DictModel):
    triangle: List[Ref]
    vertex: Optional[Ref] = None
    angle_vertex: Optional[Ref] = None


class ArgsETC(DictModel):
    index: int
    triangle: List[Ref]


class ArgsHarmonic(DictModel):
    points: List[Ref]
    conjugate_to: Ref


class ArgsTransformReflect(DictModel):
    target: Ref
    axis: Ref


class ArgsTransformPointReflect(DictModel):
    target: Ref
    center: Ref


class ArgsTransformTranslate(DictModel):
    target: Ref
    vector: List[Ref]


class ArgsTransformRotate(DictModel):
    target: Ref
    center: Ref
    angle: ScalarRef


class ArgsTransformHomothety(DictModel):
    target: Ref
    center: Ref
    ratio: ScalarRef


class ArgsTransformInversion(DictModel):
    target: Ref
    circle: Optional[Ref] = None
    center: Optional[Ref] = None
    radius: Optional[ScalarRef] = None

    @model_validator(mode="after")
    def check_inversion_args(self):
        has_circle = self.circle is not None
        has_center_radius = self.center is not None and self.radius is not None
        if not (has_circle ^ has_center_radius):
            raise ValueError(
                "Для Inversion нужно передать либо 'circle', либо пару 'center' и 'radius'"
            )
        return self


class ArgsLocus(DictModel):
    target_point: Ref
    moving_point: Ref


class ArgsRayByPoints(DictModel):
    origin: Ref
    direction_point: Ref


class ArgsRegularPolygon(DictModel):
    points: List[Ref]
    vertices: int


class BaseGeoObject(DictModel):
    name: Optional[str] = None
    names: Optional[List[str]] = None
    hidden: bool = False
    disambiguation: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def check_name_exclusivity(self):
        if self.name and self.names:
            raise ValueError("Объект не может иметь одновременно 'name' и 'names'")
        return self

    @model_validator(mode="after")
    def check_disambiguation(self):
        if self.disambiguation is not None and "rule" not in self.disambiguation:
            raise ValueError(
                "Словарь disambiguation должен обязательно содержать ключ 'rule'"
            )
        return self


class ObjNumber(BaseGeoObject):
    type: Literal["Number"]
    method: Optional[Literal["Free"]] = "Free"
    args: Dict[Literal["value"], float]


class ObjDistance(BaseGeoObject):
    type: Literal["Distance"]
    method: Optional[Literal["Free"]] = "Free"
    args: ArgsPoints


class ObjAngleMeasure(BaseGeoObject):
    type: Literal["AngleMeasure"]
    method: Optional[Literal["Free"]] = "Free"
    args: ArgsVertexEnds


class ObjMathExpression(BaseGeoObject):
    type: Literal["MathExpression"]
    method: Optional[Literal["Free"]] = "Free"
    args: Dict[str, Any]


class ObjPointFree(BaseGeoObject):
    type: Literal["Point"]
    method: Optional[Literal["Free"]] = "Free"
    args: Optional[Dict[Literal["approx_position"], List[float]]] = None


class ObjPointIntersection(BaseGeoObject):
    type: Literal["Point"]
    method: Literal["Intersection"]
    args: ArgsIntersection


class ObjPointOnObject(BaseGeoObject):
    type: Literal["Point"]
    method: Literal["PointOnObject"]
    args: Dict[Literal["object"], Ref]


class ObjPointOnSegment(BaseGeoObject):
    type: Literal["Point"]
    method: Literal["PointOnSegment"]
    args: ArgsPointRatio


class ObjPointOnRay(BaseGeoObject):
    type: Literal["Point"]
    method: Literal["PointOnRay"]
    args: ArgsPointDistance


class ObjPointMidpoint(BaseGeoObject):
    type: Literal["Point"]
    method: Literal["Midpoint"]
    args: ArgsPoints


class ObjPointProjection(BaseGeoObject):
    type: Literal["Point"]
    method: Literal["Projection"]
    args: ArgsPointLine


class ObjPointCenter(BaseGeoObject):
    type: Literal["Point"]
    method: Literal["Center"]
    args: Dict[Literal["object"], Ref]


class ObjPointTriangleCenter(BaseGeoObject):
    type: Literal["Point"]
    method: Literal["Incenter", "Centroid", "Circumcenter", "Orthocenter"]
    args: ArgsTriangle


class ObjPointETC(BaseGeoObject):
    type: Literal["Point"]
    method: Literal["ETC"]
    args: ArgsETC


class ObjPointConjugate(BaseGeoObject):
    type: Literal["Point"]
    method: Literal["IsogonalConjugate", "IsotomicConjugate"]
    args: ArgsPointTriangle


class ObjPointHarmonic(BaseGeoObject):
    type: Literal["Point"]
    method: Literal["HarmonicConjugate"]
    args: ArgsHarmonic


class ObjMacroNoArgs(BaseGeoObject):
    type: Literal["Point", "Polygon"]
    method: Literal[
        "FreeTriangle",
        "RightTriangle",
        "IsoscelesTriangle",
        "EquilateralTriangle",
        "Square",
        "Rectangle",
        "Parallelogram",
        "Trapezoid",
        "IsoscelesTrapezoid",
        "RightTrapezoid",
    ]
    args: Optional[Dict[str, Any]] = None


class ObjMacroCyclic(BaseGeoObject):
    type: Literal["Point", "Polygon"]
    method: Literal["CyclicQuadrilateral"]
    args: Optional[Dict[Literal["approx_radius"], float]] = None


class ObjMacroRegular(BaseGeoObject):
    type: Literal["Point", "Polygon"]
    method: Literal["RegularPolygon"]
    args: ArgsRegularPolygon


class ObjLineSegmentPoints(BaseGeoObject):
    type: Literal["Line", "Segment"]
    method: Literal["LineThrough", "SegmentByPoints"]
    args: ArgsPoints


class ObjRayByPoints(BaseGeoObject):
    type: Literal["Ray"]
    method: Literal["RayByPoints"]
    args: ArgsRayByPoints


class ObjLinearFree(BaseGeoObject):
    type: Literal["Segment", "Ray"]
    method: Optional[Literal["Free"]] = "Free"
    args: ArgsPoints


class ObjLineParallelPerp(BaseGeoObject):
    type: Literal["Line"]
    method: Literal["ParallelLine", "PerpendicularLine"]
    args: ArgsPointLine


class ObjLineByAngle(BaseGeoObject):
    type: Literal["Line"]
    method: Literal["LineByAngle"]
    args: ArgsLineByAngle


class ObjRayByAngle(BaseGeoObject):
    type: Literal["Ray"]
    method: Literal["RayByAngle"]
    args: ArgsRayByAngle


class ObjPerpBisector(BaseGeoObject):
    type: Literal["Line"]
    method: Literal["PerpendicularBisector"]
    args: ArgsPoints


class ObjAngleBisector(BaseGeoObject):
    type: Literal["Line"]
    method: Literal["AngleBisector"]
    args: ArgsVertexEnds


class ObjTangentLine(BaseGeoObject):
    type: Literal["Line"]
    method: Literal["TangentLine", "PolarLine"]
    args: ArgsPointObject


class ObjCommonTangent(BaseGeoObject):
    type: Literal["Line"]
    method: Literal["CommonTangent", "RadicalAxis"]
    args: ArgsTwoCircles


class ObjEulerLine(BaseGeoObject):
    type: Literal["Line"]
    method: Literal["EulerLine"]
    args: ArgsTriangle


class ObjSimsonLine(BaseGeoObject):
    type: Literal["Line"]
    method: Literal["SimsonLine"]
    args: ArgsPointTriangle


class ObjSymmedian(BaseGeoObject):
    type: Literal["Line"]
    method: Literal["Symmedian"]
    args: ArgsTriangleVertex


class ObjCenterRadius(BaseGeoObject):
    type: Literal["Circle"]
    method: Literal["CenterRadius"]
    args: ArgsCenterRadius


class ObjDiameterCircle(BaseGeoObject):
    type: Literal["Circle"]
    method: Literal["DiameterCircle"]
    args: ArgsPoints


class ObjCircumcircle(BaseGeoObject):
    type: Literal["Circle"]
    method: Literal["Circumcircle", "Incircle", "NinePointCircle"]
    args: ArgsTriangle


class ObjExcircle(BaseGeoObject):
    type: Literal["Circle"]
    method: Literal["Excircle", "MixtilinearIncircle"]
    args: ArgsTriangleVertex


class ObjApollonius(BaseGeoObject):
    type: Literal["Circle"]
    method: Literal["ApolloniusCircle"]
    args: ArgsPointRatio


class ObjTransformReflect(BaseGeoObject):
    type: Literal[
        "Point",
        "Line",
        "Segment",
        "Ray",
        "Circle",
        "Curve",
        "Polygon",
        "Conic",
        "Angle",
    ]
    method: Literal["Reflection"]
    args: ArgsTransformReflect


class ObjTransformPointReflect(BaseGeoObject):
    type: Literal[
        "Point",
        "Line",
        "Segment",
        "Ray",
        "Circle",
        "Curve",
        "Polygon",
        "Conic",
        "Angle",
    ]
    method: Literal["PointReflection"]
    args: ArgsTransformPointReflect


class ObjTransformTranslate(BaseGeoObject):
    type: Literal[
        "Point",
        "Line",
        "Segment",
        "Ray",
        "Circle",
        "Curve",
        "Polygon",
        "Conic",
        "Angle",
    ]
    method: Literal["Translation"]
    args: ArgsTransformTranslate


class ObjTransformRotate(BaseGeoObject):
    type: Literal[
        "Point",
        "Line",
        "Segment",
        "Ray",
        "Circle",
        "Curve",
        "Polygon",
        "Conic",
        "Angle",
    ]
    method: Literal["Rotation"]
    args: ArgsTransformRotate


class ObjTransformHomothety(BaseGeoObject):
    type: Literal[
        "Point",
        "Line",
        "Segment",
        "Ray",
        "Circle",
        "Curve",
        "Polygon",
        "Conic",
        "Angle",
    ]
    method: Literal["Homothety"]
    args: ArgsTransformHomothety


class ObjTransformInversion(BaseGeoObject):
    type: Literal[
        "Point",
        "Line",
        "Segment",
        "Ray",
        "Circle",
        "Curve",
        "Polygon",
        "Conic",
        "Angle",
    ]
    method: Literal["Inversion"]
    args: ArgsTransformInversion


class ObjLocus(BaseGeoObject):
    type: Literal["Curve"]
    method: Literal["Locus"]
    args: ArgsLocus


GeoObject = Union[
    ObjNumber,
    ObjDistance,
    ObjAngleMeasure,
    ObjMathExpression,
    ObjPointFree,
    ObjPointIntersection,
    ObjPointOnObject,
    ObjPointOnSegment,
    ObjPointOnRay,
    ObjPointMidpoint,
    ObjPointProjection,
    ObjPointCenter,
    ObjPointTriangleCenter,
    ObjPointETC,
    ObjPointConjugate,
    ObjPointHarmonic,
    ObjMacroNoArgs,
    ObjMacroCyclic,
    ObjMacroRegular,
    ObjLineSegmentPoints,
    ObjRayByPoints,
    ObjLinearFree,
    ObjLineParallelPerp,
    ObjLineByAngle,
    ObjRayByAngle,
    ObjPerpBisector,
    ObjAngleBisector,
    ObjTangentLine,
    ObjCommonTangent,
    ObjEulerLine,
    ObjSimsonLine,
    ObjSymmedian,
    ObjCenterRadius,
    ObjDiameterCircle,
    ObjCircumcircle,
    ObjExcircle,
    ObjApollonius,
    ObjTransformReflect,
    ObjTransformPointReflect,
    ObjTransformTranslate,
    ObjTransformRotate,
    ObjTransformHomothety,
    ObjTransformInversion,
    ObjLocus,
]


class GeoDraftDocument(BaseModel):
    problem_name: str = Field(..., description="Короткое название задачи")
    constraints: List[ConstraintDef] = Field(
        default_factory=list, description="Ограничения для сэмплера"
    )
    construction: List[GeoObject] = Field(
        default_factory=list, description="Пошаговое построение"
    )
    goals: List[GoalDef] = Field(
        default_factory=list, description="Цели (утверждения) для доказательства"
    )
    view: List[ViewDef] = Field(
        default_factory=list, description="Инструкции по визуализации (отрезки, цвета)"
    )
