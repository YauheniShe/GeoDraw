from compiler.core.evaluators import compile_value_argument
from compiler.models import GeoDraftDocument


def compile_constraints(doc: GeoDraftDocument):
    checks = []
    for const in doc.constraints:
        c_type = const["type"]

        if c_type == "IsAcute":
            c_args = const["args"]
            pts = c_args["points"]
            end1, vertex, end2 = pts[0], pts[1], pts[2]

            def check_acute(env, e1=end1, v=vertex, e2=end2):
                pe1, pv, pe2 = env.get(e1), env.get(v), env.get(e2)
                if not (pe1 and pv and pe2):
                    return False
                dx1, dy1 = pe1[0] - pv[0], pe1[1] - pv[1]
                dx2, dy2 = pe2[0] - pv[0], pe2[1] - pv[1]
                return (dx1 * dx2 + dy1 * dy2) > 0

            checks.append(check_acute)

        elif c_type == "Inequality":
            lhs_eval = compile_value_argument(const["left"])
            rhs_eval = compile_value_argument(const["right"])
            op = const["operator"]

            if op == ">":
                checks.append(lambda env, le=lhs_eval, re=rhs_eval: le(env) > re(env))
            elif op == "<":
                checks.append(lambda env, le=lhs_eval, re=rhs_eval: le(env) < re(env))
            elif op == ">=":
                checks.append(lambda env, le=lhs_eval, re=rhs_eval: le(env) >= re(env))
            elif op == "<=":
                checks.append(lambda env, le=lhs_eval, re=rhs_eval: le(env) <= re(env))
            elif op == "==":
                checks.append(
                    lambda env, le=lhs_eval, re=rhs_eval: abs(le(env) - re(env)) < 1e-9
                )

        elif c_type == "Convex":
            c_args = const["args"]
            pts_names = tuple(c_args["points"])

            def check_convex(env, names=pts_names):
                pts = [env.get(p) for p in names]
                if any(p is None for p in pts):
                    return False
                n = len(pts)
                if n < 3:
                    return False
                signs = []
                for i in range(n):
                    p1, p2, p3 = pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
                    dx1, dy1 = p2[0] - p1[0], p2[1] - p1[1]
                    dx2, dy2 = p3[0] - p2[0], p3[1] - p2[1]
                    cross = dx1 * dy2 - dy1 * dx2
                    if abs(cross) < 1e-9:
                        return False
                    signs.append(cross > 0)
                return all(signs) or not any(signs)

            checks.append(check_convex)

        else:
            raise NotImplementedError(f"Неизвестный тип ограничения: {c_type}")

    return checks
