from typing import (
    Protocol,
    Any,
    Optional,
    Type,
    TypeVar,
)

from .field import Field


_T = TypeVar("_T")
class SettingsFragment(Protocol):
    __name__: str
    def __init__(self, **kwargs: Any): ...
    def __repr__(self) -> str: ...
    _fields: dict[str, Field]
    @classmethod
    def _update_field_info(cls) -> dict[str, Field]: ...
    @classmethod
    def _add_field(
            cls,
            name: str,
            alias: Optional[str] = None,
            dtype: Optional[Type[_T]] = None,
            has_default: bool = False,
            default_value: _T = None,
    ): ...
    @classmethod
    def get_field_info(cls) -> dict[str, Field]: ...
    @classmethod
    def get_discriminating_field(cls) -> Field: ...
