from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Union


@dataclass
class GeoObject:
    type: str
    method: Optional[str] = None
    args: Optional[Union[Dict[str, Any], Any]] = None
    name: Optional[str] = None
    names: Optional[List[str]] = None
    hidden: bool = False
    disambiguation: Optional[Dict[str, Any]] = None


@dataclass
class GeoDraftDocument:
    problem_name: str
    constraints: List[Dict[str, Any]]
    construction: List[GeoObject]
    goals: List[Dict[str, Any]]
    view: List[Dict[str, Any]]
