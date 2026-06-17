import json
from typing import Literal, Tuple

from pydantic import BaseModel, Field

RGB = Tuple[int, int, int]

LabelStyleType = Literal["latex", "name", "none"]


class ElementStyle(BaseModel):
    color: RGB = Field(default=(0, 0, 0), description="Цвет RGB")
    alpha: float = Field(default=0.0, description="Непрозрачность заливки")
    line_thickness: int = Field(default=5, description="Толщина линии")
    line_style: int = Field(
        default=0, description="Тип линии (0 - сплошная, 15 - пунктир)"
    )
    point_size: int = Field(default=4, description="Размер точки")
    point_style: int = Field(default=0, description="Стиль точки (0 - круг)")
    label_style: LabelStyleType = Field(
        default="none", description="Стиль подписи (latex, name, none)"
    )


class GeoDrawConfig(BaseModel):
    show_axes: bool = False
    show_grid: bool = False

    point: ElementStyle = ElementStyle(
        color=(0, 100, 0), point_size=4, label_style="latex"
    )
    line: ElementStyle = ElementStyle(
        color=(50, 50, 50), line_thickness=5, label_style="none"
    )
    polygon: ElementStyle = ElementStyle(
        color=(153, 51, 0), alpha=0.1, line_thickness=5, label_style="none"
    )
    angle: ElementStyle = ElementStyle(
        color=(0, 100, 0), alpha=0.1, line_thickness=5, label_style="none"
    )

    goal: ElementStyle = ElementStyle(
        color=(255, 0, 0),
        alpha=0.1,
        line_thickness=5,
        line_style=15,
        point_size=5,
        label_style="latex",
    )

    @classmethod
    def load_from_file(cls, filepath: str) -> "GeoDrawConfig":
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls(**data)
        except Exception as e:
            print(f"[-] Ошибка загрузки конфига: {e}")
            return cls()
