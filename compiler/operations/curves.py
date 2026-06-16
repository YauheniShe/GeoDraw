from compiler.operations.registry import register


@register("Curve", "Locus")
class LocusOp:
    @staticmethod
    def compile_sample(args, name: str, disambiguation):
        return lambda env: None

    @staticmethod
    def to_ggb(args, name, **kwargs):
        return f"Locus({args['target_point']}, {args['moving_point']})"
