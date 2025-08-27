from dataclasses import dataclass
from typing import (
    TypeVar,
    Generic,
    Type,
    Optional,
)


_T = TypeVar("_T")
@dataclass
class Field(Generic[_T]):
    name: str
    type: Type[_T]
    has_default: bool
    default_value: _T
    alias: Optional[str] = None
    discriminates: bool = False


class FieldAlias:
    def __init__(self, alias: str):
        self.alias = alias
