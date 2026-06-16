from compiler.math_lib.base import dist_sq, get_line_eq


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

    return candidates[0]
