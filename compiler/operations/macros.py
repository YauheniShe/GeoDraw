import math
import random

from compiler.math_lib.base import perpendicular_bisector, reflect_point_on_line
from compiler.operations.registry import register


@register("Point", "FreeTriangle")
class FreeTriangleOp:
    @staticmethod
    def compile_sample(args, name: tuple, disambiguation):
        def step(env):
            for i in range(3):
                if name[i] not in env:
                    env[name[i]] = (random.uniform(-2, 2), random.uniform(-2, 2))

        return step

    @staticmethod
    def to_ggb(
        args, name: tuple, disambiguation, translator, sampled_state, **kwargs
    ) -> str:
        for i in range(3):
            c = sampled_state[name[i]] if sampled_state else (i * 2, i % 2)
            translator._emit(
                name=name[i], expression=f"({c[0]:.3f}, {c[1]:.3f})", ggb_type="point"
            )
        return ""


@register("Point", "RightTriangle")
class RightTriangleOp:
    @staticmethod
    def compile_sample(args, name: tuple, disambiguation):
        def step(env):
            for i in range(2):
                if name[i] not in env:
                    env[name[i]] = (random.uniform(-2, 2), random.uniform(-2, 2))
            A, B = env[name[0]], env[name[1]]
            dx, dy = B[0] - A[0], B[1] - A[1]
            k = random.uniform(0.5, 1.5) * random.choice([-1, 1])
            env[name[2]] = (B[0] - k * dy, B[1] + k * dx)

        return step

    @staticmethod
    def to_ggb(
        args, name: tuple, disambiguation, translator, sampled_state, **kwargs
    ) -> str:
        for i in range(2):
            c = sampled_state[name[i]] if sampled_state else (i * 2, 0)
            translator._emit(
                name=name[i], expression=f"({c[0]:.3f}, {c[1]:.3f})", ggb_type="point"
            )

        perp = translator._emit(
            name=f"perp_{name[1]}",
            expression=f"PerpendicularLine({name[1]}, Line({name[0]}, {name[1]}))",
            ggb_type="line",
            hidden=True,
        )
        c2 = sampled_state[name[2]] if sampled_state else (2, 2)
        translator._emit(
            name=name[2], expression=f"Point({perp})", ggb_type="point", coords=c2
        )
        return ""


@register("Point", "IsoscelesTriangle")
class IsoscelesTriangleOp:
    @staticmethod
    def compile_sample(args, name: tuple, disambiguation):
        def step(env):
            for i in range(2):
                if name[i] not in env:
                    env[name[i]] = (random.uniform(-2, 2), random.uniform(-2, 2))
            A, B = env[name[0]], env[name[1]]
            mid = ((A[0] + B[0]) / 2, (A[1] + B[1]) / 2)
            dx, dy = B[0] - A[0], B[1] - A[1]
            k = random.uniform(0.5, 1.5) * random.choice([-1, 1])
            env[name[2]] = (mid[0] - k * dy, mid[1] + k * dx)

        return step

    @staticmethod
    def to_ggb(
        args, name: tuple, disambiguation, translator, sampled_state, **kwargs
    ) -> str:
        for i in range(2):
            c = sampled_state[name[i]] if sampled_state else (i * 2, 0)
            translator._emit(
                name=name[i], expression=f"({c[0]:.3f}, {c[1]:.3f})", ggb_type="point"
            )

        pb = translator._emit(
            name=f"pb_{name[0]}{name[1]}",
            expression=f"PerpendicularBisector({name[0]}, {name[1]})",
            ggb_type="line",
            hidden=True,
        )
        c2 = sampled_state[name[2]] if sampled_state else (1, 2)
        translator._emit(
            name=name[2], expression=f"Point({pb})", ggb_type="point", coords=c2
        )
        return ""


@register("Point", "EquilateralTriangle")
class EquilateralTriangleOp:
    @staticmethod
    def compile_sample(args, name: tuple, disambiguation):
        def step(env):
            for i in range(2):
                if name[i] not in env:
                    env[name[i]] = (random.uniform(-2, 2), random.uniform(-2, 2))
            A, B = env[name[0]], env[name[1]]
            dx, dy = B[0] - A[0], B[1] - A[1]
            env[name[2]] = (
                A[0] + dx * 0.5 - dy * 0.8660254037844386,
                A[1] + dx * 0.8660254037844386 + dy * 0.5,
            )

        return step

    @staticmethod
    def to_ggb(
        args, name: tuple, disambiguation, translator, sampled_state, **kwargs
    ) -> str:
        for i in range(2):
            c = sampled_state[name[i]] if sampled_state else (i * 2, 0)
            translator._emit(
                name=name[i], expression=f"({c[0]:.3f}, {c[1]:.3f})", ggb_type="point"
            )

        translator._emit(
            name=name[2],
            expression=f"Rotate({name[1]}, 60°, {name[0]})",
            ggb_type="point",
        )
        return ""


@register("Point", "Square")
class SquareOp:
    @staticmethod
    def compile_sample(args, name: tuple, disambiguation):
        def step(env):
            for i in range(2):
                if name[i] not in env:
                    env[name[i]] = (random.uniform(-2, 2), random.uniform(-2, 2))
            A, B = env[name[0]], env[name[1]]
            dx, dy = A[0] - B[0], A[1] - B[1]
            env[name[2]] = (B[0] + dy, B[1] - dx)
            dx2, dy2 = B[0] - A[0], B[1] - A[1]
            env[name[3]] = (A[0] - dy2, A[1] + dx2)

        return step

    @staticmethod
    def to_ggb(
        args, name: tuple, disambiguation, translator, sampled_state, **kwargs
    ) -> str:
        for i in range(2):
            c = sampled_state[name[i]] if sampled_state else (i * 2, 0)
            translator._emit(
                name=name[i], expression=f"({c[0]:.3f}, {c[1]:.3f})", ggb_type="point"
            )

        translator._emit(
            name=name[2],
            expression=f"Rotate({name[0]}, -90°, {name[1]})",
            ggb_type="point",
        )
        translator._emit(
            name=name[3],
            expression=f"Rotate({name[1]}, 90°, {name[0]})",
            ggb_type="point",
        )
        return ""


@register("Point", "Rectangle")
class RectangleOp:
    @staticmethod
    def compile_sample(args, name: tuple, disambiguation):
        def step(env):
            for i in range(2):
                if name[i] not in env:
                    env[name[i]] = (random.uniform(-2, 2), random.uniform(-2, 2))
            A, B = env[name[0]], env[name[1]]
            dx, dy = B[0] - A[0], B[1] - A[1]
            k = random.uniform(0.5, 1.5) * random.choice([-1, 1])
            C = (B[0] - k * dy, B[1] + k * dx)
            env[name[2]] = C
            env[name[3]] = (A[0] + C[0] - B[0], A[1] + C[1] - B[1])

        return step

    @staticmethod
    def to_ggb(
        args, name: tuple, disambiguation, translator, sampled_state, **kwargs
    ) -> str:
        for i in range(2):
            c = sampled_state[name[i]] if sampled_state else (i * 3, 0)
            translator._emit(
                name=name[i], expression=f"({c[0]:.3f}, {c[1]:.3f})", ggb_type="point"
            )

        perp = translator._emit(
            name=f"perp_{name[1]}",
            expression=f"PerpendicularLine({name[1]}, Line({name[0]}, {name[1]}))",
            ggb_type="line",
            hidden=True,
        )
        c2 = sampled_state[name[2]] if sampled_state else (3, 2)
        translator._emit(
            name=name[2], expression=f"Point({perp})", ggb_type="point", coords=c2
        )
        translator._emit(
            name=name[3],
            expression=f"{name[0]} + {name[2]} - {name[1]}",
            ggb_type="point",
        )
        return ""


@register("Point", "Parallelogram")
class ParallelogramOp:
    @staticmethod
    def compile_sample(args, name: tuple, disambiguation):
        def step(env):
            for i in range(3):
                if name[i] not in env:
                    env[name[i]] = (random.uniform(-2, 2), random.uniform(-2, 2))
            A, B, C = env[name[0]], env[name[1]], env[name[2]]
            env[name[3]] = (A[0] + C[0] - B[0], A[1] + C[1] - B[1])

        return step

    @staticmethod
    def to_ggb(
        args, name: tuple, disambiguation, translator, sampled_state, **kwargs
    ) -> str:
        for i in range(3):
            c = sampled_state[name[i]] if sampled_state else (i * 2, i % 2)
            translator._emit(
                name=name[i], expression=f"({c[0]:.3f}, {c[1]:.3f})", ggb_type="point"
            )

        translator._emit(
            name=name[3],
            expression=f"{name[0]} + {name[2]} - {name[1]}",
            ggb_type="point",
        )
        return ""


@register("Point", "Trapezoid")
class TrapezoidOp:
    @staticmethod
    def compile_sample(args, name: tuple, disambiguation):
        def step(env):
            for i in range(3):
                if name[i] not in env:
                    env[name[i]] = (random.uniform(-2, 2), random.uniform(-2, 2))
            A, B, C = env[name[0]], env[name[1]], env[name[2]]
            k = random.uniform(0.5, 1.5) * random.choice([-1, 1])
            env[name[3]] = (A[0] + k * (C[0] - B[0]), A[1] + k * (C[1] - B[1]))

        return step

    @staticmethod
    def to_ggb(
        args, name: tuple, disambiguation, translator, sampled_state, **kwargs
    ) -> str:
        for i in range(3):
            c = sampled_state[name[i]] if sampled_state else (i * 2, i % 2)
            translator._emit(
                name=name[i], expression=f"({c[0]:.3f}, {c[1]:.3f})", ggb_type="point"
            )

        par = translator._emit(
            name=f"par_{name[0]}",
            expression=f"Line({name[0]}, Line({name[1]}, {name[2]}))",
            ggb_type="line",
            hidden=True,
        )
        c3 = sampled_state[name[3]] if sampled_state else (0, 1)
        translator._emit(
            name=name[3], expression=f"Point({par})", ggb_type="point", coords=c3
        )
        return ""


@register("Point", "IsoscelesTrapezoid")
class IsoscelesTrapezoidOp:
    @staticmethod
    def compile_sample(args, name: tuple, disambiguation):
        def step(env):
            for i in range(3):
                if name[i] not in env:
                    env[name[i]] = (random.uniform(-2, 2), random.uniform(-2, 2))
            A, B, C = env[name[0]], env[name[1]], env[name[2]]
            line_pb = perpendicular_bisector(B, C)
            env[name[3]] = reflect_point_on_line(A, line_pb)

        return step

    @staticmethod
    def to_ggb(
        args, name: tuple, disambiguation, translator, sampled_state, **kwargs
    ) -> str:
        for i in range(3):
            c = sampled_state[name[i]] if sampled_state else (i * 2, i % 2)
            translator._emit(
                name=name[i], expression=f"({c[0]:.3f}, {c[1]:.3f})", ggb_type="point"
            )

        pb = translator._emit(
            name=f"pb_{name[1]}{name[2]}",
            expression=f"PerpendicularBisector({name[1]}, {name[2]})",
            ggb_type="line",
            hidden=True,
        )
        translator._emit(
            name=name[3], expression=f"Reflect({name[0]}, {pb})", ggb_type="point"
        )
        return ""


@register("Point", "RightTrapezoid")
class RightTrapezoidOp:
    @staticmethod
    def compile_sample(args, name: tuple, disambiguation):
        def step(env):
            for i in range(2):
                if name[i] not in env:
                    env[name[i]] = (random.uniform(-2, 2), random.uniform(-2, 2))
            A, B = env[name[0]], env[name[1]]
            dx, dy = B[0] - A[0], B[1] - A[1]
            k1 = random.uniform(0.5, 1.5) * random.choice([-1, 1])
            k2 = random.uniform(0.5, 1.5) * random.choice([-1, 1])
            env[name[2]] = (B[0] - k1 * dy, B[1] + k1 * dx)
            env[name[3]] = (A[0] - k2 * dy, A[1] + k2 * dx)

        return step

    @staticmethod
    def to_ggb(
        args, name: tuple, disambiguation, translator, sampled_state, **kwargs
    ) -> str:
        for i in range(2):
            c = sampled_state[name[i]] if sampled_state else (i * 2, 0)
            translator._emit(
                name=name[i], expression=f"({c[0]:.3f}, {c[1]:.3f})", ggb_type="point"
            )

        p1 = translator._emit(
            name=f"perp_{name[1]}",
            expression=f"PerpendicularLine({name[1]}, Line({name[0]}, {name[1]}))",
            ggb_type="line",
            hidden=True,
        )
        p2 = translator._emit(
            name=f"perp_{name[0]}",
            expression=f"PerpendicularLine({name[0]}, Line({name[0]}, {name[1]}))",
            ggb_type="line",
            hidden=True,
        )

        c2 = sampled_state[name[2]] if sampled_state else (2, 2)
        c3 = sampled_state[name[3]] if sampled_state else (0, 2)
        translator._emit(
            name=name[2], expression=f"Point({p1})", ggb_type="point", coords=c2
        )
        translator._emit(
            name=name[3], expression=f"Point({p2})", ggb_type="point", coords=c3
        )
        return ""


@register("Point", "CyclicQuadrilateral")
class CyclicQuadrilateralOp:
    @staticmethod
    def compile_sample(args, name: tuple, disambiguation):
        def step(env):
            start_angle = random.uniform(0, 2 * math.pi)
            angles = [start_angle]
            for _ in range(3):
                angles.append(angles[-1] + random.uniform(0.6, 1.4))

            R = random.uniform(2.5, 3.5)
            cx, cy = random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5)

            for i, n in enumerate(name[:4]):
                env[n] = (cx + R * math.cos(angles[i]), cy + R * math.sin(angles[i]))

        return step

    @staticmethod
    def to_ggb(
        args, name: tuple, disambiguation, translator, sampled_state, **kwargs
    ) -> str:
        for i in range(3):
            c = (
                sampled_state[name[i]]
                if sampled_state
                else (3 * math.cos(i), 3 * math.sin(i))
            )
            translator._emit(
                name=name[i], expression=f"({c[0]:.3f}, {c[1]:.3f})", ggb_type="point"
            )

        circ = translator._emit(
            name=f"circ_{name[0]}{name[1]}{name[2]}",
            expression=f"Circle({name[0]}, {name[1]}, {name[2]})",
            ggb_type="conic",
            hidden=True,
        )
        c3 = sampled_state[name[3]] if sampled_state else (3, 0)
        translator._emit(
            name=name[3], expression=f"Point({circ})", ggb_type="point", coords=c3
        )
        return ""


@register("Point", "RegularPolygon")
class RegularPolygonOp:
    @staticmethod
    def compile_sample(args, name: tuple, disambiguation):
        def step(env):
            if args and "points" in args:
                p0, p1 = args["points"]
                n = args.get("vertices", len(name))
                A, B = env[p0], env[p1]
                dx, dy = B[0] - A[0], B[1] - A[1]
                d = math.hypot(dx, dy)
                if d < 1e-9:
                    for i in range(min(n, len(name))):
                        env[name[i]] = A
                    return

                mx, my = (A[0] + B[0]) / 2, (A[1] + B[1]) / 2
                h = (d / 2) / math.tan(math.pi / n)
                nx, ny = -dy / d, dx / d
                cx, cy = mx + nx * h, my + ny * h

                radius = math.hypot(A[0] - cx, A[1] - cy)
                theta0 = math.atan2(A[1] - cy, A[0] - cx)

                for i in range(min(n, len(name))):
                    if i == 0:
                        env[name[i]] = A
                    elif i == 1:
                        env[name[i]] = B
                    else:
                        angle = theta0 + i * 2 * math.pi / n
                        env[name[i]] = (
                            cx + radius * math.cos(angle),
                            cy + radius * math.sin(angle),
                        )
            else:
                n = args.get("vertices", len(name)) if args else len(name)
                cx, cy = random.uniform(-1, 1), random.uniform(-1, 1)
                R = random.uniform(2, 4)
                start_angle = random.uniform(0, 2 * math.pi)
                for i in range(min(n, len(name))):
                    angle = start_angle + i * 2 * math.pi / n
                    env[name[i]] = (cx + R * math.cos(angle), cy + R * math.sin(angle))

        return step

    @staticmethod
    def to_ggb(
        args, name: tuple, disambiguation, translator, sampled_state, **kwargs
    ) -> str:
        if args and "points" in args:
            p0, p1 = args["points"]
            n = args.get("vertices", len(name))

            poly_name = translator._emit(
                name=f"poly_{name[0]}",
                expression=f"Polygon({p0}, {p1}, {n})",
                ggb_type="polygon",
                hidden=True,
            )
            for i in range(min(n, len(name))):
                if i == 0 and name[i] == p0:
                    continue
                if i == 1 and name[i] == p1:
                    continue

                translator._emit(
                    name=name[i],
                    expression=f"Vertex({poly_name}, {i + 1})",
                    ggb_type="point",
                )
            return ""
        else:
            n = args.get("vertices", len(name)) if args else len(name)
            for i in range(min(n, len(name))):
                c = (
                    sampled_state[name[i]]
                    if sampled_state
                    else (math.cos(i * 2 * math.pi / n), math.sin(i * 2 * math.pi / n))
                )
                translator._emit(
                    name=name[i],
                    expression=f"({c[0]:.3f}, {c[1]:.3f})",
                    ggb_type="point",
                )
            return ""
