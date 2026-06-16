from compiler.operations.registry import register


@register("Point", "Parallelogram")
class ParallelogramOp:
    @staticmethod
    def compile_sample(args, name: tuple, disambiguation):
        def step(env):
            if (
                name[0] in env
                and name[1] in env
                and name[2] in env
                and name[3] not in env
            ):
                A, B, C = env[name[0]], env[name[1]], env[name[2]]
                env[name[3]] = (A[0] + C[0] - B[0], A[1] + C[1] - B[1])

        return step

    @staticmethod
    def to_ggb(args, name: tuple, disambiguation, **kwargs) -> str:
        return "MACRO"


@register("Point", "Square")
class SquareOp:
    @staticmethod
    def compile_sample(args, name: tuple, disambiguation):
        def step(env):
            A, B = env[name[0]], env[name[1]]
            dx, dy = A[0] - B[0], A[1] - B[1]
            env[name[2]] = (B[0] + dy, B[1] - dx)
            dx2, dy2 = B[0] - A[0], B[1] - A[1]
            env[name[3]] = (A[0] - dy2, A[1] + dx2)

        return step


@register("Point", "EquilateralTriangle")
class EquilateralTriangleOp:
    @staticmethod
    def compile_sample(args, name: tuple, disambiguation):
        def step(env):
            A, B = env[name[0]], env[name[1]]
            dx, dy = B[0] - A[0], B[1] - A[1]
            env[name[2]] = (
                A[0] + dx * 0.5 - dy * 0.8660254037844386,
                A[1] + dx * 0.8660254037844386 + dy * 0.5,
            )

        return step
