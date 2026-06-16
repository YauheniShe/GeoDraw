from compiler.math_lib.base import dist


def cartesian_to_barycentric(P, A, B, C):
    """
    Переводит декартовы координаты точки P(x, y)
    в барицентрические координаты (u, v, w) относительно треугольника ABC.
    Использует отношение ориентированных площадей (area coordinates).
    """

    def signed_area(p1, p2, p3):
        return 0.5 * (
            p1[0] * (p2[1] - p3[1]) + p2[0] * (p3[1] - p1[1]) + p3[0] * (p1[1] - p2[1])
        )

    sa = signed_area(P, B, C)
    sb = signed_area(P, C, A)
    sc = signed_area(P, A, B)
    total = sa + sb + sc

    if abs(total) < 1e-9:
        return (0.0, 0.0, 0.0)
    return (sa / total, sb / total, sc / total)


def barycentric_to_cartesian(coords, A, B, C):
    """
    Переводит барицентрические координаты (u, v, w) в декартовы координаты (x, y).
    """
    u, v, w = coords
    total = u + v + w
    if abs(total) < 1e-9:
        return (0.0, 0.0)
    return (
        (u * A[0] + v * B[0] + w * C[0]) / total,
        (u * A[1] + v * B[1] + w * C[1]) / total,
    )


def isogonal_conjugate(P, A, B, C):
    """
    Вычисляет изогонально сопряженную точку.
    Формула в барицентриках: (x : y : z) -> (a^2/x : b^2/y : c^2/z)
    """
    u, v, w = cartesian_to_barycentric(P, A, B, C)
    epsilon = 1e-9
    # Если точка на вершине, возвращаем саму вершину
    if abs(u) < epsilon:
        return A
    if abs(v) < epsilon:
        return B
    if abs(w) < epsilon:
        return C

    a = dist(B, C)
    b = dist(C, A)
    c = dist(A, B)

    return barycentric_to_cartesian((a**2 / u, b**2 / v, c**2 / w), A, B, C)


def isotomic_conjugate(P, A, B, C):
    """
    Вычисляет изотомически сопряженную точку.
    Формула в барицентриках: (x : y : z) -> (1/x : 1/y : 1/w)
    """
    u, v, w = cartesian_to_barycentric(P, A, B, C)
    epsilon = 1e-9
    if abs(u) < epsilon:
        return A
    if abs(v) < epsilon:
        return B
    if abs(w) < epsilon:
        return C

    return barycentric_to_cartesian((1.0 / u, 1.0 / v, 1.0 / w), A, B, C)
