from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field


class GeoObject(BaseModel):
    type: str = Field(..., description="Тип объекта (Point, Line, Circle и т.д.)")
    method: Optional[str] = Field("Free", description="Метод построения")
    args: Optional[Union[Dict[str, Any], Any]] = Field(default=None)
    name: Optional[str] = Field(default=None)
    names: Optional[List[str]] = Field(default=None)
    hidden: bool = Field(default=False)
    disambiguation: Optional[Dict[str, Any]] = Field(default=None)


class GeoDraftDocument(BaseModel):
    problem_name: str
    constraints: List[Dict[str, Any]] = Field(default_factory=list)
    construction: List[GeoObject] = Field(default_factory=list)
    goals: List[Dict[str, Any]] = Field(default_factory=list)
    view: List[Dict[str, Any]] = Field(default_factory=list)
