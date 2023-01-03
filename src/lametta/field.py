from dataclasses import dataclass
from typing import (
    TypeVar,
    Generic,
    Type,
)


_T = TypeVar("_T")
@dataclass
class Field(Generic[_T]):
    name: str
    type: Type[_T]
    has_default: bool
    default_value: _T
    discriminates: bool = False
