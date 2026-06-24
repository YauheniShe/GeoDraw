# Спецификация языка GeoDraft (v1.0)

## Оглавление
1. Базовая структура документа и Видимость
2. Типы объектов (`type`) и Скаляры
3. Блок `construction`: Каталог методов (Полный)
4. Разрешение неоднозначностей (`disambiguation`)
5. Ограничения (`constraints`)
6. Целевые предикаты (`goals`)
7. Блок визуализации (`view`)
8. Примеры использования

---

## 1. Базовая структура документа
Каждая задача описывается JSON-объектом с пятью обязательными ключами:
```json
{
  "problem_name": "Название задачи",
  "constraints": [], 
  "construction": [],
  "goals": [],
  "view": []
}
```
* **`constraints`** — глобальные ограничения для рандомизатора (отсев некорректных базовых конфигураций).
* **`construction`** — строгий математический процесс построения. Все объекты здесь математически полные (бесконечные прямые, целые окружности).
* **`goals`** — логические предикаты, которые нужно доказать.
* **`view`** — визуальные инструкции (отрисовка отрезков, контуров, обрезка прямых). Чертеж генерируется в строгом академическом стиле (черный цвет, тонкие линии).

### 1.1. Ссылки на объекты и Правило видимости
Любой аргумент может принимать либо **строку** (имя ранее созданного объекта), либо **анонимный объект** (словарь с ключами `type` и параметрами).

> **Базовое правило видимости:**
> 1. Все **анонимные** объекты скрыты по умолчанию (они нужны только для математических вычислений).
> 2. Все **именованные** объекты (имеющие ключ `name` или `names`) видимы по умолчанию, если не указано иное. Их отображение можно переопределить в блоке `view`.
> 3. Именованному объекту можно задать флаг **`"hidden": true`** прямо в блоке `construction`. Это позволяет разбивать сложные вычисления на простые шаги без необходимости использовать громоздкие вложенные анонимные объекты, не загрязняя при этом итоговый чертеж.

---

## 2. Типы объектов (`type`)
* `Point` — Точка.
* `Line` — Прямая (бесконечная).
* `Segment` — Отрезок (имеет длину и концы).
* `Ray` — Луч (имеет начало и направление).
* `Circle` — Окружность.
* `Conic` — Коническое сечение.
* `Curve` — Кривая (геометрическое место точек).
* `Polygon` — Многоугольник.

### 2.1. Скаляры и Математические выражения
* `{"type": "Number", "value": <float>}` — конкретное число.
* `{"type": "Distance", "points": ["A", "B"]}` — длина $AB$.
* `{"type": "AngleMeasure", "vertex": "B", "ends": ["A", "C"]}` — мера $\angle ABC$. *(Вершина строго вынесена в отдельный ключ `vertex`).*
* **`{"type": "MathExpression"}`** — арифметическое выражение.
  ```json
  {
    "type": "MathExpression",
    "expression": "90 - alpha / 2",
    "variables": {
      "alpha": {"type": "AngleMeasure", "vertex": "A", "ends": ["B", "C"]}
    }
  }
  ```

---

## 3. Блок `construction`: Каталог методов

### 3.1. Базовые точки (Point)
| `method` | `args` | Описание |
| :--- | :--- | :--- |
| `Free` | `{"approx_position": [<x>, <y>]}*` | Свободная точка. Опциональный `approx_position` — подсказка. |
| `PointOnObject` | `{"object": "<Obj>"}` | Свободная точка на объекте (прямой, окружности, **отрезке** и т.д.). Используется для построения **произвольной** точки. |
| `PointOnSegment`| `{"points": ["A", "B"], "ratio": "<Scalar>"}` | Точка на отрезке $AB$, делящая его в **строго заданном** отношении (от 0 до 1, где 0.5 — середина). |
| `PointOnRay` | `{"points": ["A", "B"], "distance": "<Scalar>"}` | Точка на луче $AB$ на заданном расстоянии от $A$. |
| `Intersection` | `{"obj1": "<Obj>", "obj2": "<Obj>"}` | Пересечение объектов. **Требует `disambiguation` при >1 корне!** |
| `Projection` | `{"point": "<Point>", "line": "<Line>"}` | Основание перпендикуляра из точки на прямую. |
| `Midpoint` | `{"points": ["<Point>", "<Point>"]}` | Середина отрезка (алиас). |
| `Center` | `{"object": "<Circle/Conic>"}` | Центр кривой. |

> **Примечание:** Если вам нужна случайная (свободная) точка на отрезке $AB$, используйте метод `PointOnObject` с передачей отрезка в качестве аргумента. Метод `PointOnSegment` предназначен исключительно для фиксации точки в конкретной пропорции.

### 3.2. Центры треугольника и сопряжения (Advanced Point)
| `method` | `args` | Описание |
| :--- | :--- | :--- |
| `ETC` | `{"index": <Int>, "triangle": ["A", "B", "C"]}` | Точка из Энциклопедии Кимберлинга (1 - Инцентр, и т.д.). |
| `Incenter` / `Orthocenter` / `Centroid` / `Circumcenter` | `{"triangle": ["A", "B", "C"]}` | Алиасы для частых центров. |
| `IsogonalConjugate`| `{"point": "<Point>", "triangle": [...]}` | Изогонально сопряженная точка. |
| `IsotomicConjugate`| `{"point": "<Point>", "triangle": [...]}` | Изотомически сопряженная точка. |
| `HarmonicConjugate`| `{"points": ["A", "B"], "conjugate_to": "C"}`| Точка $D$, такая что двойное отношение $(A,B; C,D) = -1$. |

### 3.3. Линии, Лучи и Отрезки
| `method` | `args` | Описание |
| :--- | :--- | :--- |
| `LineThrough` | `{"points": ["A", "B"]}` | Прямая через две точки. |
| `SegmentByPoints` | `{"points": ["A", "B"]}` | Отрезок по двум точкам. |
| `RayByPoints` | `{"origin": "A", "direction_point": "B"}` | Луч из точки $A$ через точку $B$. |
| `ParallelLine` / `PerpendicularLine` | `{"point": "<Point>", "line": "<Line>"}` | Параллельная / перпендикулярная прямая. |
| `LineByAngle` | `{"line": "<Line>", "point": "<Point>", "angle": "<Scalar>"}` | Прямая через точку под углом к другой прямой. *(По умолчанию угол откладывается против часовой стрелки, CCW)* |
| `RayByAngle` | `{"ray": "<Ray>", "angle": "<Scalar>"}` | Луч под заданным углом к исходному. *(По умолчанию угол CCW. Отрицательные значения — по часовой)* |
| `PerpendicularBisector`| `{"points": ["A", "B"]}` | Серединный перпендикуляр к отрезку. |
| `AngleBisector` | `{"vertex": "B", "ends": ["A", "C"]}` | Биссектриса угла $\angle ABC$. |
| `TangentLine` | `{"point": "<Point>", "object": "<Circle>"}`| Касательная из точки к кривой. *(Требует `disambiguation`)* |
| `CommonTangent` | `{"circle1": "<Circle>", "circle2": "<Circle>"}`| Общая касательная. *(Требует `disambiguation`)* |
| `RadicalAxis` | `{"circle1": "<Circle>", "circle2": "<Circle>"}` | Радикальная ось двух окружностей. |
| `PolarLine` | `{"point": "<Point>", "object": "<Circle/Conic>"}` | Поляра точки относительно кривой. |
| `EulerLine` | `{"triangle": ["A", "B", "C"]}` | Прямая Эйлера для треугольника. |
| `SimsonLine` | `{"point": "<Point>", "triangle": ["A", "B", "C"]}` | Прямая Симсона (требует точку на описанной окружности). |
| `Symmedian` | `{"triangle": ["A", "B", "C"], "vertex": "B"}` | Симедиана (луч/прямая). |

### 3.4. Окружности (Circle)
| `method` | `args` | Описание |
| :--- | :--- | :--- |
| `CenterRadius` | `{"center": "<Point>", "radius": "<Scalar>"}` | Окружность по центру и радиусу. |
| `DiameterCircle`| `{"points": ["A", "B"]}` | Окружность на $AB$ как на диаметре. |
| `Circumcircle` | `{"triangle": ["A", "B", "C"]}` | Описанная окружность. |
| `Incircle` / `NinePointCircle` | `{"triangle": ["A", "B", "C"]}` | Вписанная окружность и окружность Эйлера. |
| `Excircle` | `{"triangle": ["A", "B", "C"], "vertex": "A"}` | Вневписанная окружность, касающаяся стороны напротив вершины $A$. |
| `MixtilinearIncircle` | `{"triangle": ["A", "B", "C"], "vertex": "A"}` | Микстилинейная вписанная окружность для угла $A$. |
| `ApolloniusCircle`| `{"points": ["A", "B"], "ratio": "<Scalar>"}` | Окружность Аполлония (ГМТ с заданным отношением). |

### 3.5. Макросы (Множественное присваивание)
Макросы генерируют **массив базовых точек (вершин)**, не создавая визуальных отрезков (сторон). Для их вызова на верхнем уровне объекта используется ключ `"names"` (массив строк) вместо `"name"`. 

| `method` | `args` | Описание |
| :--- | :--- | :--- |
| `FreeTriangle` / `RightTriangle` / `IsoscelesTriangle` / `EquilateralTriangle` | `None` | Генерирует 3 точки соответствующего треугольника. |
| `Square` / `Rectangle` / `Parallelogram` / `Trapezoid` / `IsoscelesTrapezoid` / `RightTrapezoid` | `None` | Генерирует 4 точки соответствующего четырехугольника. |
| `CyclicQuadrilateral` | `{"approx_radius": <Scalar>}*`| Генерирует 4 точки, лежащие на одной окружности. |
| `RegularPolygon` | `{"points": ["A", "B"], "vertices": <Int>}` | Генерирует массив вершин правильного многоугольника, построенного на отрезке $AB$. |

### 3.6. Преобразования плоскости (Transformations)
*Методы возвращают объект того же типа, что и аргумент `target`.*
| `method` | `args` | Описание |
| :--- | :--- | :--- |
| `Reflection` | `{"target": "<Obj>", "axis": "<Line>"}` | Осевая симметрия. |
| `PointReflection`| `{"target": "<Obj>", "center": "<Point>"}`| Центральная симметрия. |
| `Translation` | `{"target": "<Obj>", "vector": ["A", "B"]}` | Параллельный перенос на вектор $\vec{AB}$. |
| `Rotation` | `{"target": "<Obj>", "center": "<Point>", "angle": "<Scalar>"}` | Поворот вокруг точки. *(Требует `disambiguation: orientation`)* |
| `Homothety` | `{"target": "<Obj>", "center": "<Point>", "ratio": "<Scalar>"}` | Гомотетия. |
| `Inversion` | `{"target": "<Obj>", "circle": "<Circle>"}` **ИЛИ** `{"target": "<Obj>", "center": "<Point>", "radius": "<Scalar>"}` | Инверсия. Можно передать либо готовую окружность, либо центр и радиус. |

### 3.7. Геометрические места точек (Curve)
| `method` | `args` | Описание |
| :--- | :--- | :--- |
| `Locus` | `{"target_point": "<Point>", "moving_point": "<Point>"}` | След (кривая), который оставляет `target_point` при движении `moving_point` по объекту. |

---

## 4. Разрешение неоднозначностей (`disambiguation`)
Указывается словарем при операциях, генерирующих несколько решений.
**Универсальное правило:** Словарь `disambiguation` всегда содержит ключ `"rule"`, определяющий тип фильтра, и дополнительные параметры, зависящие от правила.
**Множественный возврат:** Если операция (например, `Intersection`) генерирует 2 точки, и используются обе, нужно применить ключ `"names": ["X", "Y"]` вместо `"name"`. В таком случае блок `disambiguation` не используется (компилятор забирает все корни).

| `rule` | Ожидаемые параметры | Применение |
| :--- | :--- | :--- |
| `algebraic_index` | `"index": 1` или `2` | Fallback-правило. Выбор i-го корня без геом. привязки. |
| `closest_to` / `furthest_from` | `"target": "<Point>"` | Ближайшая / наиболее удаленная точка к целевой. |
| `not_equal` | `"target": "<Point>"` | Исключает тривиальное пересечение. |
| `order_on_line` | `"order": ["A", "B", "X"]` | Задает порядок расположения точек на прямой. |
| `order_on_curve` | `"center": "<Point>", "direction": "clockwise"` | Выбор корня в заданном направлении обхода окружности от референсной точки. |
| `same_side_of_line` / `opposite_side_of_line`| `"line": "<Line>", "point": "<Point>"` | В одной / разных полуплоскостях с референсной точкой. |
| `inside_circumcircle`| `"triangle": ["A", "B", "C"]` | Корень строго внутри описанной окружности. |
| `inside_angle` | `"vertex": "B", "ends": ["A", "C"]` | Корень строго внутри угла. |
| `inside_polygon` / `outside_polygon` | `"polygon": ["A", "B", "C"]` | Корень внутри или вне многоугольника. |
| `tangent` | `None` | Указывает, что решение ровно одно (фигуры касаются). |
| `tangent_direction` | `"value": "external"` или `"internal"`, опционально `"index": 1/2` | Для биссектрис или общих касательных. |
| `orientation` | `"value": "clockwise"` или `"counterclockwise"` | Направление для `Rotation`. |
| `arbitrary` | `None` | Точки равнозначны (берется любая). |

---

## 5. Ограничения (`constraints`)
Используются компилятором для Rejection Sampling базового чертежа. Аргументы передаются в виде строго типизированных словарей.
* `{"type": "IsAcute", "args": {"points": ["A", "B", "C"]}}`
* `{"type": "Inequality", "operator": ">", "left": {"type": "Distance", "points": ["A", "B"]}, "right": {"type": "Number", "value": 5}}`
* `{"type": "Convex", "args": {"points": ["A", "B", "C", "D"]}}`

---

## 6. Целевые предикаты (`goals`)
Блок `goals` — массив объектов. Задача решена, если доказаны все предикаты. Аргументы строго типизированы через ключи словаря.

| `type` | Ожидаемые `args` | Что значит |
| :--- | :--- | :--- |
| `Concurrent` | `{"objects": [<Line/Circle>, <Line/Circle>, ...]}` | Пересекаются в одной точке. |
| `Collinear` | `{"points": [<Point>, <Point>, <Point>, ...]}` | Точки лежат на одной прямой. |
| `Concyclic` | `{"points": [<Point>, <Point>, <Point>, <Point>, ...]}`| Точки лежат на одной окружности. |
| `Tangent` | `{"objects": [<Line/Circle>, <Circle/Conic>]}` | Фигуры касаются друг друга. |
| `Perpendicular`| `{"lines": [<Line>, <Line>]}` | Прямые перпендикулярны. |
| `Parallel` | `{"lines": [<Line>, <Line>]}` | Прямые параллельны. |
| `Belongs` | `{"point": "<Point>", "object": "<Obj>"}`| Точка принадлежит объекту. |
| `Equal` | `{"values": [<Scalar>, <Scalar>]}`| Равенство величин (длин, углов, отношений). |
| `Coincident` | `{"objects": [<Obj>, <Obj>]}` | Геометрическое совпадение фигур. |

---

## 7. Блок визуализации (`view`)
Отвечает исключительно за то, какие объекты попадут на итоговый чертеж и как они будут обрезаны. **Блок не создает математических сущностей.** Чертеж по умолчанию строгий (черно-белый, тонкие линии).

### Каталог действий (`action`)
1. **`Hide` / `Show`** — принудительно скрыть или показать объект.
   `{"action": "Hide", "targets": ["Bisector_B", "EulerLine_ABC"]}`
2. **`Clip`** — заменяет бесконечную прямую на итоговом чертеже на аккуратный отрезок или луч (математически объект остается прямой).
   * `{"action": "Clip", "target": "Line_AM", "endpoints": ["A", "M"]}`
   * `{"action": "Clip", "target": "Line_AM", "ray_from": "A", "towards": "M"}`
3. **Отрисовка контуров и визуальных связей**:
   * `{"action": "DrawSegment", "endpoints": ["A", "B"]}` — рисует отрезок.
   * `{"action": "DrawPolygon", "vertices": ["A", "B", "C", "D"]}` — обводит контур многоугольника.
   * `{"action": "DrawAngle", "vertex": "B", "ends": ["A", "C"]}` — рисует дужку угла.

---

## 8. Примеры использования

**Условие:** *In parallelogram $ABCD$ with acute angle $A$ a point $N$ is chosen on the segment $AD$, and a point $M$ on the segment $CN$ so that $AB = BM = CM$. Point $K$ is the reflection of $N$ in line $MD$. The line $MK$ meets the segment $AD$ at point $L$. Let $P$ be the common point of the circumcircles of $AMD$ and $CNK$ such that $A$ and $P$ share the same side of the line $MK$. Prove that $\angle CPM = \angle DPL$.*

```json
{
  "problem_name": "Parallelogram and Two Circumcircles",
  "constraints": [
    {
      "type": "IsAcute",
      "args": {"points": ["D", "A", "B"]}
    },
    {
      "type": "Inequality",
      "operator": ">",
      "left": {"type": "Distance", "points": ["A", "D"]},
      "right": {"type": "Distance", "points": ["A", "B"]}
    }
  ],
  "construction": [
    {
      "names": ["A", "B", "C", "D"],
      "type": "Point",
      "method": "Parallelogram",
      "args": null
    },
    {
      "name": "Line_BC",
      "type": "Line",
      "method": "LineThrough",
      "args": {"points": ["B", "C"]},
      "hidden": true
    },
    {
      "name": "Circle_B",
      "type": "Circle",
      "method": "CenterRadius",
      "args": {
        "center": "B",
        "radius": {"type": "Distance", "points": ["A", "B"]}
      },
      "hidden": true
    },
    {
      "name": "Circle_C",
      "type": "Circle",
      "method": "CenterRadius",
      "args": {
        "center": "C",
        "radius": {"type": "Distance", "points": ["A", "B"]}
      },
      "hidden": true
    },
    {
      "name": "M",
      "type": "Point",
      "method": "Intersection",
      "args": {"obj1": "Circle_B", "obj2": "Circle_C"},
      "disambiguation": {
        "rule": "same_side_of_line",
        "line": "Line_BC",
        "point": "A"
      }
    },
    {
      "name": "Line_CM",
      "type": "Line",
      "method": "LineThrough",
      "args": {"points": ["C", "M"]},
      "hidden": true
    },
    {
      "name": "Line_AD",
      "type": "Line",
      "method": "LineThrough",
      "args": {"points": ["A", "D"]},
      "hidden": true
    },
    {
      "name": "N",
      "type": "Point",
      "method": "Intersection",
      "args": {"obj1": "Line_CM", "obj2": "Line_AD"}
    },
    {
      "name": "Line_MD",
      "type": "Line",
      "method": "LineThrough",
      "args": {"points": ["M", "D"]},
      "hidden": true
    },
    {
      "name": "K",
      "type": "Point",
      "method": "Reflection",
      "args": {
        "target": "N", 
        "axis": "Line_MD"
      }
    },
    {
      "name": "Line_MK",
      "type": "Line",
      "method": "LineThrough",
      "args": {"points": ["M", "K"]},
      "hidden": true
    },
    {
      "name": "L",
      "type": "Point",
      "method": "Intersection",
      "args": {"obj1": "Line_MK", "obj2": "Line_AD"}
    },
    {
      "name": "Circumcircle_AMD",
      "type": "Circle",
      "method": "Circumcircle",
      "args": {"triangle": ["A", "M", "D"]}
    },
    {
      "name": "Circumcircle_CNK",
      "type": "Circle",
      "method": "Circumcircle",
      "args": {"triangle": ["C", "N", "K"]}
    },
    {
      "name": "P",
      "type": "Point",
      "method": "Intersection",
      "args": {
        "obj1": "Circumcircle_AMD", 
        "obj2": "Circumcircle_CNK"
      },
      "disambiguation": {
        "rule": "same_side_of_line",
        "line": "Line_MK",
        "point": "A"
      }
    }
  ],
  "goals": [
    {
      "type": "Equal",
      "args": {
        "values": [
          {
            "type": "AngleMeasure",
            "vertex": "P",
            "ends": ["C", "M"]
          },
          {
            "type": "AngleMeasure",
            "vertex": "P",
            "ends": ["D", "L"]
          }
        ]
      }
    }
  ],
  "view": [
    {
      "action": "DrawPolygon",
      "vertices": ["A", "B", "C", "D"]
    },
    {
      "action": "DrawSegment",
      "endpoints": ["C", "N"]
    },
    {
      "action": "DrawSegment",
      "endpoints": ["M", "K"]
    },
    {
      "action": "DrawSegment",
      "endpoints": ["N", "K"]
    },
    {
      "action": "DrawSegment",
      "endpoints": ["M", "D"]
    },
    {
      "action": "DrawSegment",
      "endpoints": ["C", "P"]
    },
    {
      "action": "DrawSegment",
      "endpoints": ["M", "P"]
    },
    {
      "action": "DrawSegment",
      "endpoints": ["D", "P"]
    },
    {
      "action": "DrawSegment",
      "endpoints": ["L", "P"]
    },
    {
      "action": "DrawAngle",
      "vertex": "P",
      "ends": ["C", "M"]
    },
    {
      "action": "DrawAngle",
      "vertex": "P",
      "ends": ["D", "L"]
    }
  ]
}
```

**Условие:** *Пусть $ABCD$ — выпуклый четырехугольник. Общие внешние касательные к окружностям $(ABC)$ и $(ACD)$ пересекаются в точке $E$, а общие внешние касательные к окружностям $(ABD)$ и $(BCD)$ пересекаются в точке $F$. Пусть $F$ лежит на прямой $AC$. Докажите, что $E$ лежит на прямой $BD$.*

```json
{
  "problem_name": "Convex Quadrilateral and Tangents Intersection",
  "constraints": [
    {
      "type": "Convex",
      "args": {"points": ["A", "B", "C", "D"]}
    },
    {
      "type": "Inequality",
      "operator": ">",
      "left": {"type": "Distance", "points": ["A", "D"]},
      "right": {"type": "Distance", "points": ["A", "B"]}
    }
  ],
  "construction": [
    {
      "name": "A",
      "type": "Point",
      "method": "Free",
      "args": {"approx_position": [0, 0]}
    },
    {
      "name": "B",
      "type": "Point",
      "method": "Free",
      "args": {"approx_position": [2, 3]}
    },
    {
      "name": "D",
      "type": "Point",
      "method": "Free",
      "args": {"approx_position": [4, 0]}
    },
    {
      "name": "ApoCircle",
      "type": "Circle",
      "method": "ApolloniusCircle",
      "args": {
        "points": ["D", "B"],
        "ratio": {
          "type": "MathExpression",
          "expression": "d_AD / d_AB",
          "variables": {
            "d_AD": {"type": "Distance", "points": ["A", "D"]},
            "d_AB": {"type": "Distance", "points": ["A", "B"]}
          }
        }
      },
      "hidden": true
    },
    {
      "name": "C",
      "type": "Point",
      "method": "PointOnObject",
      "args": {"object": "ApoCircle"}
    },
    {
      "name": "Circ_ABD",
      "type": "Circle",
      "method": "Circumcircle",
      "args": {"triangle": ["A", "B", "D"]}
    },
    {
      "name": "Circ_BCD",
      "type": "Circle",
      "method": "Circumcircle",
      "args": {"triangle": ["B", "C", "D"]}
    },
    {
      "name": "Circ_ABC",
      "type": "Circle",
      "method": "Circumcircle",
      "args": {"triangle": ["A", "B", "C"]}
    },
    {
      "name": "Circ_ACD",
      "type": "Circle",
      "method": "Circumcircle",
      "args": {"triangle": ["A", "C", "D"]}
    },
    {
      "name": "Tangent_F1",
      "type": "Line",
      "method": "CommonTangent",
      "args": {"circle1": "Circ_ABD", "circle2": "Circ_BCD"},
      "disambiguation": {
        "rule": "tangent_direction",
        "value": "external",
        "index": 1
      },
      "hidden": true
    },
    {
      "name": "Tangent_F2",
      "type": "Line",
      "method": "CommonTangent",
      "args": {"circle1": "Circ_ABD", "circle2": "Circ_BCD"},
      "disambiguation": {
        "rule": "tangent_direction",
        "value": "external",
        "index": 2
      },
      "hidden": true
    },
    {
      "name": "F",
      "type": "Point",
      "method": "Intersection",
      "args": {"obj1": "Tangent_F1", "obj2": "Tangent_F2"}
    },
    {
      "name": "Tangent_E1",
      "type": "Line",
      "method": "CommonTangent",
      "args": {"circle1": "Circ_ABC", "circle2": "Circ_ACD"},
      "disambiguation": {
        "rule": "tangent_direction",
        "value": "external",
        "index": 1
      },
      "hidden": true
    },
    {
      "name": "Tangent_E2",
      "type": "Line",
      "method": "CommonTangent",
      "args": {"circle1": "Circ_ABC", "circle2": "Circ_ACD"},
      "disambiguation": {
        "rule": "tangent_direction",
        "value": "external",
        "index": 2
      },
      "hidden": true
    },
    {
      "name": "E",
      "type": "Point",
      "method": "Intersection",
      "args": {"obj1": "Tangent_E1", "obj2": "Tangent_E2"}
    },
    {
      "name": "Line_AC",
      "type": "Line",
      "method": "LineThrough",
      "args": {"points": ["A", "C"]},
      "hidden": true
    },
    {
      "name": "Line_BD",
      "type": "Line",
      "method": "LineThrough",
      "args": {"points": ["B", "D"]},
      "hidden": true
    }
  ],
  "goals": [
    {
      "type": "Belongs",
      "args": {
        "point": "F",
        "object": "Line_AC"
      }
    },
    {
      "type": "Belongs",
      "args": {
        "point": "E",
        "object": "Line_BD"
      }
    }
  ],
  "view": [
    {
      "action": "DrawPolygon",
      "vertices": ["A", "B", "C", "D"]
    },
    {
      "action": "Show",
      "targets": ["Circ_ABD", "Circ_BCD", "Circ_ABC", "Circ_ACD"]
    },
    {
      "action": "Clip",
      "target": "Line_AC",
      "endpoints": ["A", "F"]
    },
    {
      "action": "Clip",
      "target": "Line_BD",
      "endpoints": ["B", "E"]
    }
  ]
}
```