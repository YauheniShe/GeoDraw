from compiler.math_lib.base import circumcircle, dist, dist_sq, get_line_eq


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
        if l_eq is None:
            return None
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

    elif rule == "order_on_line":
        order = params.get("order", [])
        A_pt = resolved_env[order[0]]
        B_pt = resolved_env[order[1]]
        dx, dy = B_pt[0] - A_pt[0], B_pt[1] - A_pt[1]

        def get_proj_val(p):
            return (p[0] - A_pt[0]) * dx + (p[1] - A_pt[1]) * dy

        for c_pt in candidates:
            pts_map = {
                name: resolved_env[name] if name in resolved_env else c_pt
                for name in order
            }
            vals = [get_proj_val(pts_map[n]) for n in order]
            if all(vals[i] < vals[i + 1] for i in range(len(vals) - 1)):
                return c_pt
        return candidates[0]

    elif rule == "inside_circumcircle":
        tri = params.get("triangle")
        A, B, C = resolved_env[tri[0]], resolved_env[tri[1]], resolved_env[tri[2]]
        cc, r = circumcircle(A, B, C)
        for c_pt in candidates:
            if dist(c_pt, cc) < r - 1e-9:
                return c_pt
        return candidates[0]

    elif rule == "inside_angle":
        v = params.get("vertex")
        ends = params.get("ends")
        V = resolved_env[v]
        E1 = resolved_env[ends[0]]
        E2 = resolved_env[ends[1]]
        for c_pt in candidates:
            cross1 = (E1[0] - V[0]) * (c_pt[1] - V[1]) - (E1[1] - V[1]) * (
                c_pt[0] - V[0]
            )
            cross2 = (c_pt[0] - V[0]) * (E2[1] - V[1]) - (c_pt[1] - V[1]) * (
                E2[0] - V[0]
            )
            if (cross1 * cross2) > 0:
                return c_pt
        return candidates[0]

    elif rule in ["inside_polygon", "outside_polygon"]:
        poly = params.get("polygon")
        pts = [resolved_env[p] for p in poly]

        def is_inside(p, polygon):
            n = len(polygon)
            inside = False
            p1x, p1y = polygon[0]
            for i in range(n + 1):
                p2x, p2y = polygon[i % n]
                if p[1] > min(p1y, p2y):
                    if p[1] <= max(p1y, p2y):
                        if p[0] <= max(p1x, p2x):
                            xinters = (p[1] - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                            if p1x == p2x or p[0] <= xinters:
                                inside = not inside
                p1x, p1y = p2x, p2y
            return inside

        for c_pt in candidates:
            inside = is_inside(c_pt, pts)
            if (rule == "inside_polygon" and inside) or (
                rule == "outside_polygon" and not inside
            ):
                return c_pt
        return candidates[0]

    elif rule in ["arbitrary", "order_on_curve"]:
        return candidates[0]

    raise NotImplementedError(
        f"Неизвестное правило разрешения неоднозначности (disambiguation rule): {rule}"
    )
