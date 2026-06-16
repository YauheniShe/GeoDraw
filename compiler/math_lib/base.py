import math


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


def get_two_points_on_line(line):
    a, b, c = line
    if abs(a) > abs(b):
        return ((-c) / a, 0), ((-b - c) / a, 1)
    else:
        return (0, (-c) / b), (1, (-a - c) / b)


def apply_transform(obj, transform_pt, scale=1.0):
    if isinstance(obj, tuple):
        if (
            len(obj) == 2
            and isinstance(obj[0], tuple)
            and isinstance(obj[1], (int, float))
        ):
            return (transform_pt(obj[0]), obj[1] * abs(scale))
        elif len(obj) == 3 and isinstance(obj[0], str):
            return (obj[0], transform_pt(obj[1]), transform_pt(obj[2]))
        elif len(obj) == 3 and isinstance(obj[0], (int, float)):
            p1, p2 = get_two_points_on_line(obj)
            return line_from_points(transform_pt(p1), transform_pt(p2))
    return transform_pt(obj)
