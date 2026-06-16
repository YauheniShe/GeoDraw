import math
import os
import xml.etree.ElementTree as ET
import zipfile

import pytest
from compiler.generator import GeoDraftGenerator
from compiler.parser import GeoDraftParser
from compiler.sampler import (
    centroid,
    circumcircle,
    dist,
    incenter,
    intersect_circle_circle,
    intersect_line_circle,
    orthocenter,
    sample_and_evaluate,
)
from compiler.translator import GeoDraftTranslator

TEST_PROBLEMS = {
    "test1": {
        "problem_name": "Convex Quadrilateral and Tangents Intersection",
        "constraints": [
            {"type": "Convex", "args": ["A", "B", "C", "D"]},
            {
                "type": "DistanceInequality",
                "args": [
                    {"type": "Distance", "points": ["A", "D"]},
                    ">",
                    {"type": "Distance", "points": ["A", "B"]},
                ],
            },
        ],
        "construction": [
            {
                "name": "A",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [0, 0]},
            },
            {
                "name": "B",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [2, 3]},
            },
            {
                "name": "D",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [4, 0]},
            },
            {
                "name": "ApoCircle",
                "type": "Circle",
                "method": "ApolloniusCircle",
                "args": {
                    "points": ["D", "B"],
                    "ratio": {
                        "type": "MathExpression",
                        "expression": "d_AD / d_AB",
                        "variables": {
                            "d_AD": {"type": "Distance", "points": ["A", "D"]},
                            "d_AB": {"type": "Distance", "points": ["A", "B"]},
                        },
                    },
                },
                "hidden": True,
            },
            {
                "name": "C",
                "type": "Point",
                "method": "PointOnObject",
                "args": {"object": "ApoCircle"},
            },
            {
                "name": "Circ_ABD",
                "type": "Circle",
                "method": "Circumcircle",
                "args": {"triangle": ["A", "B", "D"]},
            },
            {
                "name": "Circ_BCD",
                "type": "Circle",
                "method": "Circumcircle",
                "args": {"triangle": ["B", "C", "D"]},
            },
            {
                "name": "Circ_ABC",
                "type": "Circle",
                "method": "Circumcircle",
                "args": {"triangle": ["A", "B", "C"]},
            },
            {
                "name": "Circ_ACD",
                "type": "Circle",
                "method": "Circumcircle",
                "args": {"triangle": ["A", "C", "D"]},
            },
            {
                "name": "Tangent_F1",
                "type": "Line",
                "method": "CommonTangent",
                "args": {"circle1": "Circ_ABD", "circle2": "Circ_BCD"},
                "disambiguation": {"direction": "external", "algebraic_index": 1},
                "hidden": True,
            },
            {
                "name": "Tangent_F2",
                "type": "Line",
                "method": "CommonTangent",
                "args": {"circle1": "Circ_ABD", "circle2": "Circ_BCD"},
                "disambiguation": {"direction": "external", "algebraic_index": 2},
                "hidden": True,
            },
            {
                "name": "F",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Tangent_F1", "obj2": "Tangent_F2"},
            },
            {
                "name": "Tangent_E1",
                "type": "Line",
                "method": "CommonTangent",
                "args": {"circle1": "Circ_ABC", "circle2": "Circ_ACD"},
                "disambiguation": {"direction": "external", "algebraic_index": 1},
                "hidden": True,
            },
            {
                "name": "Tangent_E2",
                "type": "Line",
                "method": "CommonTangent",
                "args": {"circle1": "Circ_ABC", "circle2": "Circ_ACD"},
                "disambiguation": {"direction": "external", "algebraic_index": 2},
                "hidden": True,
            },
            {
                "name": "E",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Tangent_E1", "obj2": "Tangent_E2"},
            },
            {
                "name": "Line_AC",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["A", "C"]},
                "hidden": True,
            },
            {
                "name": "Line_BD",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["B", "D"]},
                "hidden": True,
            },
        ],
        "goals": [
            {"type": "Belongs", "args": ["F", "Line_AC"]},
            {"type": "Belongs", "args": ["E", "Line_BD"]},
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C", "D"]},
            {
                "action": "Show",
                "targets": ["Circ_ABD", "Circ_BCD", "Circ_ABC", "Circ_ACD"],
            },
            {"action": "Clip", "target": "Line_AC", "endpoints": ["A", "F"]},
            {"action": "Clip", "target": "Line_BD", "endpoints": ["B", "E"]},
        ],
    },
    "test2": {
        "problem_name": "Parallelogram and Two Circumcircles",
        "constraints": [
            {"type": "IsAcute", "args": ["D", "A", "B"]},
            {
                "type": "DistanceInequality",
                "args": [
                    {"type": "Distance", "points": ["A", "D"]},
                    ">",
                    {"type": "Distance", "points": ["A", "B"]},
                ],
            },
        ],
        "construction": [
            {
                "names": ["A", "B", "C", "D"],
                "type": "Point",
                "method": "Parallelogram",
                "args": None,
            },
            {
                "name": "Line_BC",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["B", "C"]},
                "hidden": True,
            },
            {
                "name": "Circle_B",
                "type": "Circle",
                "method": "CenterRadius",
                "args": {
                    "center": "B",
                    "radius": {"type": "Distance", "points": ["A", "B"]},
                },
                "hidden": True,
            },
            {
                "name": "Circle_C",
                "type": "Circle",
                "method": "CenterRadius",
                "args": {
                    "center": "C",
                    "radius": {"type": "Distance", "points": ["A", "B"]},
                },
                "hidden": True,
            },
            {
                "name": "M",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Circle_B", "obj2": "Circle_C"},
                "disambiguation": {
                    "rule": "same_side_of_line",
                    "line": "Line_BC",
                    "point": "A",
                },
            },
            {
                "name": "Line_CM",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["C", "M"]},
                "hidden": True,
            },
            {
                "name": "Line_AD",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["A", "D"]},
                "hidden": True,
            },
            {
                "name": "N",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Line_CM", "obj2": "Line_AD"},
            },
            {
                "name": "Line_MD",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["M", "D"]},
                "hidden": True,
            },
            {
                "name": "K",
                "type": "Point",
                "method": "Reflection",
                "args": {"target": "N", "axis": "Line_MD"},
            },
            {
                "name": "Line_MK",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["M", "K"]},
                "hidden": True,
            },
            {
                "name": "L",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Line_MK", "obj2": "Line_AD"},
            },
            {
                "name": "Circumcircle_AMD",
                "type": "Circle",
                "method": "Circumcircle",
                "args": {"triangle": ["A", "M", "D"]},
            },
            {
                "name": "Circumcircle_CNK",
                "type": "Circle",
                "method": "Circumcircle",
                "args": {"triangle": ["C", "N", "K"]},
            },
            {
                "name": "P",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Circumcircle_AMD", "obj2": "Circumcircle_CNK"},
                "disambiguation": {
                    "rule": "same_side_of_line",
                    "line": "Line_MK",
                    "point": "A",
                },
            },
        ],
        "goals": [
            {
                "type": "Equal",
                "args": [
                    {"type": "AngleMeasure", "vertex": "P", "ends": ["C", "M"]},
                    {"type": "AngleMeasure", "vertex": "P", "ends": ["D", "L"]},
                ],
            }
        ],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C", "D"]},
            {"action": "DrawSegment", "endpoints": ["C", "N"]},
            {"action": "DrawSegment", "endpoints": ["M", "K"]},
            {"action": "DrawSegment", "endpoints": ["N", "K"]},
            {"action": "DrawSegment", "endpoints": ["M", "D"]},
            {"action": "DrawSegment", "endpoints": ["C", "P"]},
            {"action": "DrawSegment", "endpoints": ["M", "P"]},
            {"action": "DrawSegment", "endpoints": ["D", "P"]},
            {"action": "DrawSegment", "endpoints": ["L", "P"]},
            {"action": "DrawAngle", "vertex": "P", "ends": ["C", "M"]},
            {"action": "DrawAngle", "vertex": "P", "ends": ["D", "L"]},
        ],
    },
    "test3": {
        "problem_name": "Harmonic Quadrilateral Tangent Circle",
        "constraints": [{"type": "Convex", "args": ["A", "B", "C", "D"]}],
        "construction": [
            {
                "name": "A",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [0, 0]},
            },
            {
                "name": "B",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [1, 3]},
            },
            {
                "name": "C",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [4, 2]},
            },
            {
                "name": "Circum_ABC",
                "type": "Circle",
                "method": "Circumcircle",
                "args": {"triangle": ["A", "B", "C"]},
            },
            {
                "name": "Line_AC",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["A", "C"]},
                "hidden": True,
            },
            {
                "name": "Apo_AC",
                "type": "Circle",
                "method": "ApolloniusCircle",
                "args": {
                    "points": ["A", "C"],
                    "ratio": {
                        "type": "MathExpression",
                        "expression": "d_AB / d_BC",
                        "variables": {
                            "d_AB": {"type": "Distance", "points": ["A", "B"]},
                            "d_BC": {"type": "Distance", "points": ["B", "C"]},
                        },
                    },
                },
                "hidden": True,
            },
            {
                "name": "D",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Circum_ABC", "obj2": "Apo_AC"},
                "disambiguation": {"rule": "not_equal", "target": "B"},
            },
            {
                "name": "B_prime",
                "type": "Point",
                "method": "Reflection",
                "args": {"target": "B", "axis": "Line_AC"},
            },
            {
                "name": "Circ_ABpD",
                "type": "Circle",
                "method": "Circumcircle",
                "args": {"triangle": ["A", "B_prime", "D"]},
            },
        ],
        "goals": [{"type": "Tangent", "args": ["Line_AC", "Circ_ABpD"]}],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C", "D"]},
            {"action": "DrawSegment", "endpoints": ["A", "C"]},
            {"action": "DrawSegment", "endpoints": ["A", "B_prime"]},
            {"action": "DrawSegment", "endpoints": ["D", "B_prime"]},
            {"action": "Show", "targets": ["Circum_ABC", "Circ_ABpD"]},
        ],
    },
    "test4": {
        "problem_name": "Bisectors in a Cyclic Quadrilateral",
        "constraints": [
            {"type": "Convex", "args": ["A", "B", "C", "D"]},
            {
                "type": "DistanceInequality",
                "args": [
                    {"type": "Distance", "points": ["A", "B"]},
                    ">",
                    {"type": "Distance", "points": ["C", "D"]},
                ],
            },
        ],
        "construction": [
            {
                "names": ["A", "B", "C", "D"],
                "type": "Point",
                "method": "CyclicQuadrilateral",
                "args": None,
            },
            {
                "name": "Circumcircle_ABCD",
                "type": "Circle",
                "method": "Circumcircle",
                "args": {"triangle": ["A", "B", "C"]},
            },
            {
                "name": "Line_AC",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["A", "C"]},
                "hidden": True,
            },
            {
                "name": "Line_BD",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["B", "D"]},
                "hidden": True,
            },
            {
                "name": "E",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Line_AC", "obj2": "Line_BD"},
            },
            {
                "name": "Line_AD",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["A", "D"]},
                "hidden": True,
            },
            {
                "name": "Line_BC",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["B", "C"]},
                "hidden": True,
            },
            {
                "name": "F",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Line_AD", "obj2": "Line_BC"},
            },
            {
                "name": "Bisector_F",
                "type": "Line",
                "method": "AngleBisector",
                "args": {"vertex": "F", "ends": ["A", "B"]},
                "hidden": True,
            },
            {
                "name": "Bisector_E",
                "type": "Line",
                "method": "AngleBisector",
                "args": {"vertex": "E", "ends": ["A", "B"]},
                "hidden": True,
            },
            {
                "name": "Line_CD",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["C", "D"]},
                "hidden": True,
            },
            {
                "name": "X",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Bisector_F", "obj2": "Line_CD"},
            },
            {
                "name": "Y",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Bisector_E", "obj2": "Line_CD"},
            },
        ],
        "goals": [{"type": "Concyclic", "args": ["A", "B", "X", "Y"]}],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C", "D"]},
            {"action": "DrawSegment", "endpoints": ["A", "C"]},
            {"action": "DrawSegment", "endpoints": ["B", "D"]},
            {"action": "DrawSegment", "endpoints": ["D", "F"]},
            {"action": "DrawSegment", "endpoints": ["C", "F"]},
            {"action": "DrawSegment", "endpoints": ["F", "X"]},
            {"action": "DrawSegment", "endpoints": ["E", "Y"]},
            {"action": "DrawSegment", "endpoints": ["C", "X"]},
            {"action": "DrawSegment", "endpoints": ["D", "Y"]},
            {"action": "DrawSegment", "endpoints": ["X", "Y"]},
        ],
    },
    "test5": {
        "problem_name": "Midpoints and Concyclicity in a Quadrilateral",
        "constraints": [{"type": "Convex", "args": ["A", "B", "C", "D"]}],
        "construction": [
            {
                "name": "B",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [0, 0]},
            },
            {
                "name": "D",
                "type": "Point",
                "method": "Free",
                "args": {"approx_position": [6, 0]},
            },
            {
                "name": "Circumcircle_BD",
                "type": "Circle",
                "method": "DiameterCircle",
                "args": {"points": ["B", "D"]},
                "hidden": True,
            },
            {
                "name": "C",
                "type": "Point",
                "method": "PointOnObject",
                "args": {"object": "Circumcircle_BD"},
            },
            {
                "name": "M_BC",
                "type": "Point",
                "method": "Midpoint",
                "args": {"points": ["B", "C"]},
            },
            {
                "name": "Line_DM_BC",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["D", "M_BC"]},
                "hidden": True,
            },
            {
                "name": "Line_AC",
                "type": "Line",
                "method": "PerpendicularLine",
                "args": {"point": "C", "line": "Line_DM_BC"},
                "hidden": True,
            },
            {
                "name": "A",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Line_AC", "obj2": "Circumcircle_BD"},
                "disambiguation": {"rule": "not_equal", "target": "C"},
            },
            {
                "name": "M_AB",
                "type": "Point",
                "method": "Midpoint",
                "args": {"points": ["A", "B"]},
            },
            {
                "name": "M_AD",
                "type": "Point",
                "method": "Midpoint",
                "args": {"points": ["A", "D"]},
            },
            {
                "name": "M_DC",
                "type": "Point",
                "method": "Midpoint",
                "args": {"points": ["D", "C"]},
            },
            {
                "name": "Circle_Premise",
                "type": "Circle",
                "method": "Circumcircle",
                "args": {"triangle": ["A", "D", "M_AB"]},
            },
        ],
        "goals": [{"type": "Concyclic", "args": ["M_AD", "M_DC", "B", "C"]}],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C", "D"]},
            {"action": "DrawAngle", "vertex": "A", "ends": ["D", "B"]},
            {"action": "DrawAngle", "vertex": "C", "ends": ["B", "D"]},
        ],
    },
    "test6": {
        "problem_name": "Collinearity from two circumcircles in an acute triangle",
        "constraints": [
            {"type": "IsAcute", "args": ["A", "B", "C"]},
            {"type": "IsAcute", "args": ["B", "C", "A"]},
            {"type": "IsAcute", "args": ["C", "A", "B"]},
        ],
        "construction": [
            {
                "names": ["A", "B", "C"],
                "type": "Point",
                "method": "FreeTriangle",
                "args": None,
            },
            {
                "name": "D",
                "type": "Point",
                "method": "PointOnObject",
                "args": {"object": {"type": "Segment", "points": ["A", "B"]}},
            },
            {
                "name": "Line_BC",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["B", "C"]},
                "hidden": True,
            },
            {
                "name": "Line_DE_parallel",
                "type": "Line",
                "method": "ParallelLine",
                "args": {"point": "D", "line": "Line_BC"},
                "hidden": True,
            },
            {
                "name": "Line_AC",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["A", "C"]},
                "hidden": True,
            },
            {
                "name": "E",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Line_DE_parallel", "obj2": "Line_AC"},
            },
            {
                "name": "P",
                "type": "Point",
                "method": "PointOnObject",
                "args": {"object": {"type": "Segment", "points": ["B", "C"]}},
            },
            {
                "name": "Q",
                "type": "Point",
                "method": "PointOnObject",
                "args": {"object": {"type": "Segment", "points": ["B", "P"]}},
            },
            {
                "name": "Line_DP",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["D", "P"]},
                "hidden": True,
            },
            {
                "name": "Line_EQ",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["E", "Q"]},
                "hidden": True,
            },
            {
                "name": "X",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Line_DP", "obj2": "Line_EQ"},
            },
            {
                "name": "Circ_BQX",
                "type": "Circle",
                "method": "Circumcircle",
                "args": {"triangle": ["B", "Q", "X"]},
            },
            {
                "name": "Circ_CPX",
                "type": "Circle",
                "method": "Circumcircle",
                "args": {"triangle": ["C", "P", "X"]},
            },
            {
                "name": "Y",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Circ_BQX", "obj2": "Circ_CPX"},
                "disambiguation": {"rule": "not_equal", "target": "X"},
            },
        ],
        "goals": [{"type": "Collinear", "args": ["A", "X", "Y"]}],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "DrawSegment", "endpoints": ["D", "E"]},
            {"action": "DrawSegment", "endpoints": ["D", "P"]},
            {"action": "DrawSegment", "endpoints": ["E", "Q"]},
            {"action": "DrawSegment", "endpoints": ["A", "X"]},
            {"action": "DrawSegment", "endpoints": ["X", "Y"]},
        ],
    },
    "test7": {
        "problem_name": "Tangent to Circumcircle Meets Bisector",
        "constraints": [
            {"type": "IsAcute", "args": ["B", "A", "C"]},
            {"type": "IsAcute", "args": ["A", "B", "C"]},
            {"type": "IsAcute", "args": ["A", "C", "B"]},
            {
                "type": "DistanceInequality",
                "args": [
                    {"type": "Distance", "points": ["A", "C"]},
                    ">",
                    {"type": "Distance", "points": ["A", "B"]},
                ],
            },
        ],
        "construction": [
            {
                "names": ["A", "B", "C"],
                "type": "Point",
                "method": "FreeTriangle",
                "args": None,
            },
            {
                "name": "Line_BC",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["B", "C"]},
                "hidden": True,
            },
            {
                "name": "Omega",
                "type": "Circle",
                "method": "Circumcircle",
                "args": {"triangle": ["A", "B", "C"]},
            },
            {
                "name": "PerpBisector_BC",
                "type": "Line",
                "method": "PerpendicularBisector",
                "args": {"points": ["B", "C"]},
                "hidden": True,
            },
            {
                "name": "S",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "PerpBisector_BC", "obj2": "Omega"},
                "disambiguation": {
                    "rule": "same_side_of_line",
                    "line": "Line_BC",
                    "point": "A",
                },
            },
            {
                "name": "Perp_A_BC",
                "type": "Line",
                "method": "PerpendicularLine",
                "args": {"point": "A", "line": "Line_BC"},
                "hidden": True,
            },
            {
                "name": "Line_BS",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["B", "S"]},
                "hidden": True,
            },
            {
                "name": "D",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Perp_A_BC", "obj2": "Line_BS"},
            },
            {
                "name": "E",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Perp_A_BC", "obj2": "Omega"},
                "disambiguation": {"rule": "not_equal", "target": "A"},
            },
            {
                "name": "Line_D_parallel",
                "type": "Line",
                "method": "ParallelLine",
                "args": {"point": "D", "line": "Line_BC"},
                "hidden": True,
            },
            {
                "name": "Line_BE",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["B", "E"]},
                "hidden": True,
            },
            {
                "name": "L",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Line_D_parallel", "obj2": "Line_BE"},
            },
            {
                "name": "omega",
                "type": "Circle",
                "method": "Circumcircle",
                "args": {"triangle": ["B", "D", "L"]},
            },
            {
                "name": "P",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "omega", "obj2": "Omega"},
                "disambiguation": {"rule": "not_equal", "target": "B"},
            },
            {
                "name": "Center_omega",
                "type": "Point",
                "method": "Center",
                "args": {"object": "omega"},
                "hidden": True,
            },
            {
                "name": "Line_Center_P",
                "type": "Line",
                "method": "LineThrough",
                "args": {"points": ["Center_omega", "P"]},
                "hidden": True,
            },
            {
                "name": "Tangent_P",
                "type": "Line",
                "method": "PerpendicularLine",
                "args": {"point": "P", "line": "Line_Center_P"},
                "hidden": True,
            },
            {
                "name": "X",
                "type": "Point",
                "method": "Intersection",
                "args": {"obj1": "Tangent_P", "obj2": "Line_BS"},
            },
            {
                "name": "Bisector_A",
                "type": "Line",
                "method": "AngleBisector",
                "args": {"vertex": "A", "ends": ["B", "C"]},
                "hidden": True,
            },
        ],
        "goals": [{"type": "Belongs", "args": ["X", "Bisector_A"]}],
        "view": [
            {"action": "DrawPolygon", "vertices": ["A", "B", "C"]},
            {"action": "DrawSegment", "endpoints": ["A", "E"]},
            {"action": "DrawSegment", "endpoints": ["B", "E"]},
            {"action": "DrawSegment", "endpoints": ["D", "L"]},
            {"action": "DrawSegment", "endpoints": ["B", "S"]},
            {"action": "DrawSegment", "endpoints": ["C", "S"]},
            {"action": "DrawSegment", "endpoints": ["P", "X"]},
        ],
    },
}


def test_math_dist():
    assert math.isclose(dist((0, 0), (3, 4)), 5.0)
    assert math.isclose(dist((1, 1), (1, 1)), 0.0)


def test_math_circumcircle():
    center, radius = circumcircle((0, 0), (4, 0), (0, 3))
    assert math.isclose(center[0], 2.0)
    assert math.isclose(center[1], 1.5)
    assert math.isclose(radius, 2.5)


def test_math_incenter():
    p1 = (0, 0)
    p2 = (4, 0)
    p3 = (0, 3)
    inc = incenter(p1, p2, p3)
    assert math.isclose(inc[0], 1.0)
    assert math.isclose(inc[1], 1.0)


def test_math_centroid():
    p1, p2, p3 = (0, 0), (3, 0), (0, 3)
    cen = centroid(p1, p2, p3)
    assert math.isclose(cen[0], 1.0)
    assert math.isclose(cen[1], 1.0)


def test_math_orthocenter():
    p1, p2, p3 = (0, 0), (4, 0), (0, 3)
    orth = orthocenter(p1, p2, p3)
    assert math.isclose(orth[0], 0.0, abs_tol=1e-7)
    assert math.isclose(orth[1], 0.0, abs_tol=1e-7)


def test_intersect_line_circle():
    line = (0, 1, -1)
    circle = ((0, 0), 1.0)
    pts = intersect_line_circle(line, circle)
    assert len(pts) == 1
    assert math.isclose(pts[0][0], 0.0, abs_tol=1e-7)
    assert math.isclose(pts[0][1], 1.0)

    line_axis = (0, 1, 0)
    pts_two = intersect_line_circle(line_axis, circle)
    assert len(pts_two) == 2
    x_coords = sorted([p[0] for p in pts_two])
    assert math.isclose(x_coords[0], -1.0)
    assert math.isclose(x_coords[1], 1.0)


def test_intersect_circle_circle():
    c1 = ((0, 0), 2.0)
    c2 = ((2, 0), 2.0)
    pts = intersect_circle_circle(c1, c2)

    assert len(pts) == 2

    y_coords = sorted([p[1] for p in pts])

    assert math.isclose(pts[0][0], 1.0)
    assert math.isclose(pts[1][0], 1.0)
    assert math.isclose(y_coords[0], -math.sqrt(3))
    assert math.isclose(y_coords[1], math.sqrt(3))


@pytest.mark.parametrize("prob_key", TEST_PROBLEMS.keys())
def test_full_pipeline(prob_key, tmp_path):
    """
    Интеграционный тест:
    1. Парсит JSON структуру в объект документа.
    2. Производит геометрическое семплирование (поиск устойчивой конфигурации координат).
    3. Транслирует абстрактные инструкции в команды GeoGebra.
    4. Генерирует итоговый .ggb архив.
    """
    raw_data = TEST_PROBLEMS[prob_key]
    parser = GeoDraftParser()

    doc = parser.parse_dict(raw_data)
    assert doc is not None
    assert doc.problem_name == raw_data["problem_name"]
    assert len(doc.construction) > 0

    state = sample_and_evaluate(doc, max_attempts=500)
    assert len(state) > 0, (
        f"Не удалось найти валидную конфигурацию для {prob_key} за 500 итераций"
    )

    for obj in doc.construction:
        if obj.type == "Point":
            if obj.name:
                assert obj.name in state, (
                    f"Точка {obj.name} отсутствует в рассчитанном состоянии"
                )
                assert isinstance(state[obj.name], tuple)
                assert len(state[obj.name]) == 2
            elif obj.names:
                for n in obj.names:
                    assert n in state, (
                        f"Точка {n} из макроса отсутствует в рассчитанном состоянии"
                    )

    translator = GeoDraftTranslator()
    project = translator.translate_project(doc, state)
    assert project is not None
    assert len(project.instructions) > 0

    for view_act in doc.view:
        if view_act["action"] == "Show":
            for target in view_act["targets"]:
                if target in project.visibility:
                    assert project.visibility[target] is True

    generator = GeoDraftGenerator()
    out_file_path = os.path.join(tmp_path, f"{prob_key}_output.ggb")

    orig_types = {instr.name: instr.ggb_type for instr in project.instructions}
    generator.create_ggb(project, orig_types, out_file_path)

    assert os.path.exists(out_file_path)
    assert zipfile.is_zipfile(out_file_path)

    with zipfile.ZipFile(out_file_path, "r") as archive:
        assert "geogebra.xml" in archive.namelist()
        xml_data = archive.read("geogebra.xml")
        xml_root = ET.fromstring(xml_data)

        assert xml_root.tag == "geogebra"
        assert xml_root.find(".//construction") is not None


def test_parser_missing_keys():
    bad_json = {
        "problem_name": "Bad Problem",
        "construction": [],
    }
    parser = GeoDraftParser()
    with pytest.raises(ValueError, match="Missing keys"):
        parser.parse_dict(bad_json)


def test_sampler_degenerate_circumcircle():

    p1 = (0, 0)
    p2 = (1, 1)
    p3 = (2, 2)
    with pytest.raises(ValueError, match="Точки лежат на одной прямой"):
        circumcircle(p1, p2, p3)
