from typing import (
    Protocol,
    Any,
    Optional,
    Type,
    TypeVar,
    TypeGuard,
)

from ..field import Field


S = TypeVar("S", bound="SettingsFragment")
_T = TypeVar("_T")



IS_SETTINGS_FRAGMENT_FLAG = "__settings_fragment__"


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


def is_settings_fragment_type(obj: Any) -> TypeGuard[type[SettingsFragment]]:
    return hasattr(obj, IS_SETTINGS_FRAGMENT_FLAG)

