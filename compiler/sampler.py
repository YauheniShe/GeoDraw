import math
import random
from typing import Any, Dict

from .models import GeoDraftDocument

MATH_GLOBALS = {"__builtins__": None}
MATH_GLOBALS.update({k: v for k, v in math.__dict__.items() if not k.startswith("__")})


class GeometryEvaluator:
    @staticmethod
    def distance(p1, p2):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    @staticmethod
    def is_convex(a, b, c, d):
        points = [a, b, c, d]
        signs = []
        for i in range(4):
            p1 = points[i]
            p2 = points[(i + 1) % 4]
            p3 = points[(i + 2) % 4]
            dx1, dy1 = p2[0] - p1[0], p2[1] - p1[1]
            dx2, dy2 = p3[0] - p2[0], p3[1] - p2[1]
            cross = dx1 * dy2 - dy1 * dx2
            signs.append(cross > 0)
        return all(signs) or not any(signs)

    @staticmethod
    def is_acute(v, a, ends):
        dx1, dy1 = v[0] - a[0], v[1] - a[1]
        dx2, dy2 = ends[0] - a[0], ends[1] - a[1]
        return (dx1 * dx2 + dy1 * dy2) > 0


def dist(p1, p2):
    return math.hypot(p1[0] - p2[0], p1[1] - p2[1])


def dist_sq(p1, p2):
    return (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2


def line_from_points(p1, p2):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        raise ValueError("Точки для построения прямой совпадают")
    a, b = -dy, dx
    norm = math.hypot(a, b)
    return (a / norm, b / norm, -(a * p1[0] + b * p1[1]) / norm)


def project_point_on_line(p, line):
    a, b, c = line
    d = a * p[0] + b * p[1] + c
    return (p[0] - a * d, p[1] - b * d)


def reflect_point_on_line(p, line):
    a, b, c = line
    d = a * p[0] + b * p[1] + c
    return (p[0] - 2 * a * d, p[1] - 2 * b * d)


def angle_bisector(v, p1, p2):
    d1, d2 = dist(v, p1), dist(v, p2)
    if d1 < 1e-9 or d2 < 1e-9:
        raise ValueError("Вершина совпадает с концами в AngleBisector")
    u1 = ((p1[0] - v[0]) / d1, (p1[1] - v[1]) / d1)
    u2 = ((p2[0] - v[0]) / d2, (p2[1] - v[1]) / d2)
    dx, dy = u1[0] + u2[0], u1[1] + u2[1]
    if abs(dx) < 1e-9 and abs(dy) < 1e-9:
        dx, dy = -u1[1], u1[0]
    return line_from_points(v, (v[0] + dx, v[1] + dy))


def perpendicular_bisector(p1, p2):
    mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
    line_ab = line_from_points(p1, p2)
    a_new, b_new = -line_ab[1], line_ab[0]
    return (a_new, b_new, -(a_new * mid[0] + b_new * mid[1]))


def circumcircle(p1, p2, p3):
    d = 2 * (
        p1[0] * (p2[1] - p3[1]) + p2[0] * (p3[1] - p1[1]) + p3[0] * (p1[1] - p2[1])
    )
    if abs(d) < 1e-9:
        raise ValueError("Точки лежат на одной прямой")
    p1sq = p1[0] ** 2 + p1[1] ** 2
    p2sq = p2[0] ** 2 + p2[1] ** 2
    p3sq = p3[0] ** 2 + p3[1] ** 2
    ux = (p1sq * (p2[1] - p3[1]) + p2sq * (p3[1] - p1[1]) + p3sq * (p1[1] - p2[1])) / d
    uy = (p1sq * (p3[0] - p2[0]) + p2sq * (p1[0] - p3[0]) + p3sq * (p2[0] - p1[0])) / d
    center = (ux, uy)
    return (center, dist(center, p1))


def apollonius_circle(pt_a, pt_c, k):
    if abs(k - 1.0) < 1e-3:
        raise ValueError("Отношение близко к 1 (прямая, а не окружность)")
    i_in = ((pt_a[0] + k * pt_c[0]) / (1 + k), (pt_a[1] + k * pt_c[1]) / (1 + k))
    i_out = ((pt_a[0] - k * pt_c[0]) / (1 - k), (pt_a[1] - k * pt_c[1]) / (1 - k))
    center = ((i_in[0] + i_out[0]) / 2, (i_in[1] + i_out[1]) / 2)
    return (center, dist(center, i_in))


def common_tangents(circle1, circle2, external=True):
    (x1, y1), r1 = circle1
    (x2, y2), r2 = circle2
    d = dist((x1, y1), (x2, y2))
    if d < 1e-9:
        return []
    theta = math.atan2(y2 - y1, x2 - x1)
    if external:
        if abs(r1 - r2) > d:
            return []
        cos_alpha = (r1 - r2) / d
    else:
        if r1 + r2 > d:
            return []
        cos_alpha = (r1 + r2) / d

    if abs(cos_alpha) > 1.0:
        return []
    alpha = math.acos(cos_alpha)
    lines = []
    for sign in [-1, 1]:
        phi = theta + sign * alpha
        nx = math.cos(phi)
        ny = math.sin(phi)
        c = -(nx * x1 + ny * y1 + r1)
        lines.append((nx, ny, c))
    return lines


def centroid(p1, p2, p3):
    return ((p1[0] + p2[0] + p3[0]) / 3, (p1[1] + p2[1] + p3[1]) / 3)


def incenter(p1, p2, p3):
    a, b, c = dist(p2, p3), dist(p1, p3), dist(p1, p2)
    total = a + b + c
    if total < 1e-9:
        raise ValueError("Вырожденный треугольник")
    return (
        (a * p1[0] + b * p2[0] + c * p3[0]) / total,
        (a * p1[1] + b * p2[1] + c * p3[1]) / total,
    )


def circumcenter(p1, p2, p3):
    return circumcircle(p1, p2, p3)[0]


def orthocenter(p1, p2, p3):
    g = centroid(p1, p2, p3)
    o = circumcenter(p1, p2, p3)
    return (3 * g[0] - 2 * o[0], 3 * g[1] - 2 * o[1])


def intersect_line_circle(line, circle):
    a, b, c = line
    (x0, y0), r = circle
    d = a * x0 + b * y0 + c
    if abs(d) > r + 1e-9:
        return []
    proj = (x0 - a * d, y0 - b * d)
    h_sq = r * r - d * d
    if h_sq < 1e-9:
        return [proj]
    h = math.sqrt(h_sq)
    return [(proj[0] - b * h, proj[1] + a * h), (proj[0] + b * h, proj[1] - a * h)]


def intersect_circle_circle(circle1, circle2):
    (x1, y1), r1 = circle1
    (x2, y2), r2 = circle2
    d = dist((x1, y1), (x2, y2))
    if d > r1 + r2 + 1e-9 or d < abs(r1 - r2) - 1e-9 or d < 1e-9:
        return []
    a = (r1**2 - r2**2 + d**2) / (2 * d)
    h_sq = r1**2 - a**2
    h = math.sqrt(max(0.0, h_sq))
    x3 = x1 + a * (x2 - x1) / d
    y3 = y1 + a * (y2 - y1) / d
    return [
        (x3 - h * (y2 - y1) / d, y3 + h * (x2 - x1) / d),
        (x3 + h * (y2 - y1) / d, y3 - h * (x2 - x1) / d),
    ]


def get_line_eq(obj_ref):
    if type(obj_ref) is tuple and len(obj_ref) == 3:
        if type(obj_ref[0]) is str and obj_ref[0] in ("segment", "ray"):
            return line_from_points(obj_ref[1], obj_ref[2])
        elif type(obj_ref[0]) is not str:
            return obj_ref
    return None


def select_disambiguation(candidates, rule, params, resolved_env):
    if not candidates:
        raise ValueError("Точки пересечения не найдены")
    if len(candidates) == 1:
        return candidates[0]

    if rule == "not_equal":
        target_val = resolved_env[params.get("target")]
        valid = [c for c in candidates if dist_sq(c, target_val) > 1e-8]
        return valid[0] if valid else candidates[0]

    elif rule == "algebraic_index":
        idx = params.get("index", 1) - 1
        return candidates[idx] if 0 <= idx < len(candidates) else candidates[0]

    elif rule in ["same_side_of_line", "opposite_side_of_line"]:
        l_eq = get_line_eq(resolved_env[params.get("line")])
        a, b, c = l_eq
        ref_pt = resolved_env[params.get("point")]
        ref_sign = a * ref_pt[0] + b * ref_pt[1] + c

        for c_pt in candidates:
            c_sign = a * c_pt[0] + b * c_pt[1] + c
            same_side = (ref_sign * c_sign) > 0
            if (rule == "same_side_of_line" and same_side) or (
                rule == "opposite_side_of_line" and not same_side
            ):
                return c_pt
        return candidates[0]

    elif rule in ["closest_to", "furthest_from"]:
        target_val = resolved_env[params.get("target")]
        candidates_sorted = sorted(candidates, key=lambda c: dist_sq(c, target_val))
        return candidates_sorted[0] if rule == "closest_to" else candidates_sorted[-1]

    return candidates[0]


def compile_var_evaluators(variables_dict):
    """Компилирует правила вычисления переменных для MathExpression, чтобы не парсить их в цикле"""
    evaluators = {}
    for var_name, var_obj in variables_dict.items():
        if isinstance(var_obj, str):
            evaluators[var_name] = lambda env, n=var_obj: env[n]
        elif isinstance(var_obj, dict):
            v_type = var_obj.get("type")
            if v_type == "Distance":
                p0, p1 = var_obj.get("points")
                evaluators[var_name] = lambda env, a=p0, b=p1: dist(env[a], env[b])
            elif v_type == "Number":
                v = var_obj.get("value")
                evaluators[var_name] = lambda env, val=v: val
            elif v_type == "AngleMeasure":
                vt = var_obj.get("vertex")
                e0, e1 = var_obj.get("ends")

                def angle_eval(env, v=vt, e0=e0, e1=e1):
                    vertex, end1, end2 = env[v], env[e0], env[e1]
                    dx1, dy1 = end1[0] - vertex[0], end1[1] - vertex[1]
                    dx2, dy2 = end2[0] - vertex[0], end2[1] - vertex[1]
                    return abs(math.atan2(dx1 * dy2 - dy1 * dx2, dx1 * dx2 + dy1 * dy2))

                evaluators[var_name] = angle_eval
    return evaluators


def compile_value_argument(arg):
    """Универсальный компилятор параметров (радиус, ratio и др.)"""
    if isinstance(arg, str):
        return lambda env, n=arg: env[n]
    elif isinstance(arg, dict):
        t = arg.get("type")
        if t == "MathExpression":
            code = compile(arg.get("expression"), "<expr>", "eval")
            var_evals = compile_var_evaluators(arg.get("variables", {}))
            return lambda env, c=code, ve=var_evals: eval(
                c, MATH_GLOBALS, {k: f(env) for k, f in ve.items()}
            )
        elif t == "Distance":
            p0, p1 = arg.get("points")
            return lambda env, a=p0, b=p1: dist(env[a], env[b])
        elif t == "Number":
            v = arg.get("value")
            return lambda env, val=v: val
    v = float(arg)
    return lambda env, val=v: val


def compile_execution_plan(doc: GeoDraftDocument):
    """
    Проходит по AST документа и генерирует плоский список замыканий (step-функций).
    Каждая step-функция принимает env и мутирует его.
    """
    plan = []

    for obj in doc.construction:
        if obj.names:
            names = tuple(obj.names)
            method = obj.method

            if method == "Parallelogram":

                def step(env, ns=names):
                    if (
                        ns[0] in env
                        and ns[1] in env
                        and ns[2] in env
                        and ns[3] not in env
                    ):
                        A, B, C = env[ns[0]], env[ns[1]], env[ns[2]]
                        env[ns[3]] = (A[0] + C[0] - B[0], A[1] + C[1] - B[1])

                plan.append(step)

            elif method == "Square":

                def step(env, ns=names):
                    A, B = env[ns[0]], env[ns[1]]
                    dx, dy = A[0] - B[0], A[1] - B[1]
                    env[ns[2]] = (B[0] + dy, B[1] - dx)
                    dx2, dy2 = B[0] - A[0], B[1] - A[1]
                    env[ns[3]] = (A[0] - dy2, A[1] + dx2)

                plan.append(step)

            elif method == "EquilateralTriangle":

                def step(env, ns=names):
                    A, B = env[ns[0]], env[ns[1]]
                    dx, dy = B[0] - A[0], B[1] - A[1]
                    env[ns[2]] = (
                        A[0] + dx * 0.5 - dy * 0.8660254037844386,
                        A[1] + dx * 0.8660254037844386 + dy * 0.5,
                    )

                plan.append(step)

            continue

        name = obj.name
        if obj.type == "Point" and obj.method == "Free":
            continue

        args = obj.args or {}
        method = obj.method or "Free"

        if obj.type == "Line":
            if method == "LineThrough":
                p0, p1 = args.get("points")
                plan.append(
                    lambda env, n=name, a=p0, b=p1: env.update(
                        {n: line_from_points(env[a], env[b])}
                    )
                )
            elif method == "ParallelLine":
                pt, line = args.get("point"), args.get("line")

                def step(env, n=name, p=pt, l=line):
                    lp = env[p]
                    ll = env[l]
                    env[n] = (ll[0], ll[1], -(ll[0] * lp[0] + ll[1] * lp[1]))

                plan.append(step)
            elif method == "PerpendicularLine":
                pt, line = args.get("point"), args.get("line")

                def step(env, n=name, p=pt, l=line):
                    lp = env[p]
                    ll = env[l]
                    a_new, b_new = -ll[1], ll[0]
                    env[n] = (a_new, b_new, -(a_new * lp[0] + b_new * lp[1]))

                plan.append(step)
            elif method == "AngleBisector":
                v, e0, e1 = args.get("vertex"), args.get("ends")[0], args.get("ends")[1]
                plan.append(
                    lambda env, n=name, v=v, e0=e0, e1=e1: env.update(
                        {n: angle_bisector(env[v], env[e0], env[e1])}
                    )
                )
            elif method == "PerpendicularBisector":
                p0, p1 = args.get("points")
                plan.append(
                    lambda env, n=name, a=p0, b=p1: env.update(
                        {n: perpendicular_bisector(env[a], env[b])}
                    )
                )
            elif method == "CommonTangent":
                c1, c2 = args.get("circle1"), args.get("circle2")
                is_ext = (
                    (obj.disambiguation.get("direction", "external") == "external")
                    if obj.disambiguation
                    else True
                )
                idx = (
                    obj.disambiguation.get("algebraic_index", 1)
                    if obj.disambiguation
                    else 1
                )

                def step(env, n=name, c1=c1, c2=c2, ext=is_ext, i=idx):
                    tangents = common_tangents(env[c1], env[c2], external=ext)
                    if not tangents or i > len(tangents):
                        raise ValueError("Касательные не найдены")
                    env[n] = tangents[i - 1]

                plan.append(step)

        elif obj.type == "Segment":
            p0, p1 = args.get("points")
            plan.append(
                lambda env, n=name, a=p0, b=p1: env.update(
                    {n: ("segment", env[a], env[b])}
                )
            )

        elif obj.type == "Ray":
            p0, p1 = args.get("points")
            plan.append(
                lambda env, n=name, a=p0, b=p1: env.update({n: ("ray", env[a], env[b])})
            )

        elif obj.type == "Circle":
            if method == "CenterRadius":
                c = args.get("center")
                r_eval = compile_value_argument(args.get("radius"))
                plan.append(
                    lambda env, n=name, c=c, r=r_eval: env.update({n: (env[c], r(env))})
                )
            elif method == "DiameterCircle":
                p0, p1 = args.get("points")

                def step(env, n=name, a=p0, b=p1):
                    pa, pb = env[a], env[b]
                    env[n] = (
                        ((pa[0] + pb[0]) / 2, (pa[1] + pb[1]) / 2),
                        dist(pa, pb) / 2,
                    )

                plan.append(step)
            elif method == "Circumcircle":
                t0, t1, t2 = args.get("triangle")
                plan.append(
                    lambda env, n=name, a=t0, b=t1, c=t2: env.update(
                        {n: circumcircle(env[a], env[b], env[c])}
                    )
                )
            elif method == "ApolloniusCircle":
                p0, p1 = args.get("points")
                k_eval = compile_value_argument(args.get("ratio"))
                plan.append(
                    lambda env, n=name, a=p0, b=p1, k=k_eval: env.update(
                        {n: apollonius_circle(env[a], env[b], k(env))}
                    )
                )

        elif obj.type == "Point":
            if method == "Intersection":
                o1, o2 = args.get("obj1"), args.get("obj2")
                rule = (
                    obj.disambiguation.get("rule", "algebraic_index")
                    if obj.disambiguation
                    else "algebraic_index"
                )
                d_params = obj.disambiguation or {}

                def step(env, n=name, o1=o1, o2=o2, r=rule, p=d_params):
                    obj1, obj2 = env[o1], env[o2]
                    l1, l2 = get_line_eq(obj1), get_line_eq(obj2)
                    if l1 and l2:
                        a1, b1, c1 = l1
                        a2, b2, c2 = l2
                        det = a1 * b2 - a2 * b1
                        if abs(det) < 1e-9:
                            raise ValueError("Прямые параллельны")
                        env[n] = ((b1 * c2 - b2 * c1) / det, (c1 * a2 - c2 * a1) / det)
                    elif l1 and not l2:
                        env[n] = select_disambiguation(
                            intersect_line_circle(l1, obj2), r, p, env
                        )
                    elif not l1 and l2:
                        env[n] = select_disambiguation(
                            intersect_line_circle(l2, obj1), r, p, env
                        )
                    else:
                        env[n] = select_disambiguation(
                            intersect_circle_circle(obj1, obj2), r, p, env
                        )

                plan.append(step)

            elif method == "Reflection":
                t, ax = args.get("target"), args.get("axis")
                plan.append(
                    lambda env, n=name, t=t, ax=ax: env.update(
                        {n: reflect_point_on_line(env[t], env[ax])}
                    )
                )
            elif method == "Midpoint":
                p0, p1 = args.get("points")
                plan.append(
                    lambda env, n=name, a=p0, b=p1: env.update(
                        {n: ((env[a][0] + env[b][0]) / 2, (env[a][1] + env[b][1]) / 2)}
                    )
                )
            elif method == "Projection":
                pt, line = args.get("point"), args.get("line")
                plan.append(
                    lambda env, n=name, p=pt, l=line: env.update(
                        {n: project_point_on_line(env[p], env[l])}
                    )
                )
            elif method == "PointOnObject":
                obj_ref = args.get("object")
                param_key = f"{name}_param"

                def step(env, n=name, o=obj_ref, pk=param_key):
                    ref = env[o]
                    param = env.get(pk, 0.35)
                    if type(ref) is tuple and len(ref) == 3 and type(ref[0]) is str:
                        p1, p2 = ref[1], ref[2]
                        if ref[0] == "segment":
                            env[n] = (
                                p1[0] + param * (p2[0] - p1[0]),
                                p1[1] + param * (p2[1] - p1[1]),
                            )
                        else:  # ray
                            env[n] = (
                                p1[0] + param * 5 * (p2[0] - p1[0]),
                                p1[1] + param * 5 * (p2[1] - p1[1]),
                            )
                    else:
                        l_eq = get_line_eq(ref)
                        if l_eq:
                            a, b, c = l_eq
                            proj = project_point_on_line((0, 0), l_eq)
                            env[n] = (proj[0] - b * param * 5, proj[1] + a * param * 5)
                        else:
                            center, radius = ref
                            theta = 2 * math.pi * param
                            env[n] = (
                                center[0] + radius * math.cos(theta),
                                center[1] + radius * math.sin(theta),
                            )

                plan.append(step)

            elif method == "Center":
                obj_ref = args.get("object")
                plan.append(lambda env, n=name, o=obj_ref: env.update({n: env[o][0]}))

            elif method in ["Incenter", "Centroid", "Circumcenter", "Orthocenter"]:
                t0, t1, t2 = args.get("triangle")
                if method == "Incenter":
                    plan.append(
                        lambda env, n=name, a=t0, b=t1, c=t2: env.update(
                            {n: incenter(env[a], env[b], env[c])}
                        )
                    )
                elif method == "Centroid":
                    plan.append(
                        lambda env, n=name, a=t0, b=t1, c=t2: env.update(
                            {n: centroid(env[a], env[b], env[c])}
                        )
                    )
                elif method == "Circumcenter":
                    plan.append(
                        lambda env, n=name, a=t0, b=t1, c=t2: env.update(
                            {n: circumcenter(env[a], env[b], env[c])}
                        )
                    )
                elif method == "Orthocenter":
                    plan.append(
                        lambda env, n=name, a=t0, b=t1, c=t2: env.update(
                            {n: orthocenter(env[a], env[b], env[c])}
                        )
                    )

        elif obj.type == "MathExpression":
            code = compile(args.get("expression"), "<expr>", "eval")
            var_evals = compile_var_evaluators(args.get("variables", {}))
            plan.append(
                lambda env, n=name, c=code, ve=var_evals: env.update(
                    {n: eval(c, MATH_GLOBALS, {k: f(env) for k, f in ve.items()})}
                )
            )

        elif obj.type == "Distance":
            p0, p1 = args.get("points")
            plan.append(
                lambda env, n=name, a=p0, b=p1: env.update({n: dist(env[a], env[b])})
            )

        elif obj.type == "Number":
            val = float(args.get("value"))
            plan.append(lambda env, n=name, v=val: env.update({n: v}))

        elif obj.type == "AngleMeasure":
            v, e0, e1 = args.get("vertex"), args.get("ends")[0], args.get("ends")[1]

            def step(env, n=name, v=v, e0=e0, e1=e1):
                vertex, end1, end2 = env[v], env[e0], env[e1]
                dx1, dy1 = end1[0] - vertex[0], end1[1] - vertex[1]
                dx2, dy2 = end2[0] - vertex[0], end2[1] - vertex[1]
                env[n] = abs(math.atan2(dx1 * dy2 - dy1 * dx2, dx1 * dx2 + dy1 * dy2))

            plan.append(step)

    return plan


def compile_constraints(doc: GeoDraftDocument):
    """
    Компилирует все проверки в список функций (env -> bool).
    """
    checks = []
    for const in doc.constraints:
        c_type = const.get("type")
        c_args = const.get("args")

        if c_type == "IsAcute":
            v, a, ends = c_args[0], c_args[1], c_args[2]

            def check_acute(env, v=v, a=a, ends=ends):
                pv, pa, pends = env.get(v), env.get(a), env.get(ends)
                if not (pv and pa and pends):
                    return False
                dx1, dy1 = pv[0] - pa[0], pv[1] - pa[1]
                dx2, dy2 = pends[0] - pa[0], pends[1] - pa[1]
                return (dx1 * dx2 + dy1 * dy2) > 0

            checks.append(check_acute)

        elif c_type == "DistanceInequality":
            lhs, op, rhs = c_args[0], c_args[1], c_args[2]

            if lhs["type"] == "Distance":
                lp0, lp1 = lhs["points"]
                lhs_eval = lambda env, a=lp0, b=lp1: dist_sq(env[a], env[b])
            else:
                lhs_eval = lambda env: 0.0

            if rhs["type"] == "Distance":
                rp0, rp1 = rhs["points"]
                rhs_eval = lambda env, a=rp0, b=rp1: dist_sq(env[a], env[b])
            else:
                r_val_sq = rhs.get("value", 0.0) ** 2
                rhs_eval = lambda env, val=r_val_sq: val

            if op == ">":
                checks.append(lambda env, le=lhs_eval, re=rhs_eval: le(env) > re(env))
            elif op == "<":
                checks.append(lambda env, le=lhs_eval, re=rhs_eval: le(env) < re(env))

        elif c_type == "Convex":
            pts_names = tuple(c_args)

            def check_convex(env, names=pts_names):
                pts = [env.get(p) for p in names]
                if any(p is None for p in pts):
                    return False
                signs = []
                for i in range(4):
                    p1, p2, p3 = pts[i], pts[(i + 1) % 4], pts[(i + 2) % 4]
                    dx1, dy1 = p2[0] - p1[0], p2[1] - p1[1]
                    dx2, dy2 = p3[0] - p2[0], p3[1] - p2[1]
                    signs.append(dx1 * dy2 - dy1 * dx2 > 0)
                return all(signs) or not any(signs)

            checks.append(check_convex)

    return checks


def sample_and_evaluate(doc: GeoDraftDocument, max_attempts=1000) -> Dict[str, Any]:
    execution_plan = compile_execution_plan(doc)
    constraints_plan = compile_constraints(doc)

    free_points_to_sample = {}
    point_on_object_params = []
    has_cyclic_quad = False
    cyclic_quad_names = []

    for obj in doc.construction:
        if obj.names:
            if obj.method == "CyclicQuadrilateral":
                has_cyclic_quad = True
                cyclic_quad_names = obj.names
            elif obj.method in ["Parallelogram", "FreeTriangle"]:
                free_points_to_sample.update(
                    {
                        obj.names[0]: (0.0, 0.0),
                        obj.names[1]: (3.0, 0.0),
                        obj.names[2]: (4.0, 3.0),
                    }
                )
            elif obj.method in ["Square", "EquilateralTriangle"]:
                free_points_to_sample.update(
                    {obj.names[0]: (0.0, 0.0), obj.names[1]: (3.0, 0.0)}
                )
        elif obj.type == "Point":
            if obj.method == "Free":
                approx = obj.args.get("approx_position") if obj.args else None
                if not approx:
                    approx = (random.uniform(-2, 2), random.uniform(-2, 2))
                free_points_to_sample[obj.name] = approx
            elif obj.method == "PointOnObject":
                point_on_object_params.append(obj.name)

    if has_cyclic_quad:
        cyclic_quad_set = set(cyclic_quad_names)
        free_points_to_sample_filtered = {
            k: v for k, v in free_points_to_sample.items() if k not in cyclic_quad_set
        }
    else:
        free_points_to_sample_filtered = free_points_to_sample

    uniform = random.uniform
    cos = math.cos
    sin = math.sin
    pi = math.pi

    for attempt in range(max_attempts):
        env = {}
        for name, approx in free_points_to_sample_filtered.items():
            env[name] = (approx[0] + uniform(-1.2, 1.2), approx[1] + uniform(-1.2, 1.2))

        if has_cyclic_quad:
            start_angle = uniform(0, 2 * pi)
            angles = [start_angle]
            for _ in range(3):
                angles.append(angles[-1] + uniform(0.6, 1.4))
            R = uniform(2.5, 3.5)
            center_x, center_y = uniform(-0.5, 0.5), uniform(-0.5, 0.5)
            for i, name in enumerate(cyclic_quad_names):
                env[name] = (
                    center_x + R * cos(angles[i]),
                    center_y + R * sin(angles[i]),
                )

        for name in point_on_object_params:
            env[f"{name}_param"] = uniform(0.01, 0.99)

        try:
            for step in execution_plan:
                step(env)
        except ValueError:
            continue

        satisfied = True
        for check in constraints_plan:
            if not check(env):
                satisfied = False
                break

        if satisfied:
            print(f"-> Конфигурация успешно подобрана за {attempt + 1} попыток!")
            return env

    print(
        "-> Предупреждение: Не удалось подобрать точную конфигурацию под ограничения."
    )
    return {}
