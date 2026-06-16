SAMPLER_REGISTRY = {}
GGB_REGISTRY = {}


def register(obj_type: str, method: str):
    """
    Декоратор для регистрации геометрической операции.
    """

    def decorator(cls):
        if hasattr(cls, "compile_sample"):
            SAMPLER_REGISTRY[(obj_type, method)] = getattr(cls, "compile_sample")

        if hasattr(cls, "to_ggb"):
            GGB_REGISTRY[(obj_type, method)] = getattr(cls, "to_ggb")
        return cls

    return decorator
