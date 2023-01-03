from typing import TypeVar, Generic, Type, Iterable
from dataclasses import dataclass

from .settings_fragment import SettingsFragment


_T = TypeVar("_T")
@dataclass
class DiscriminatorField(Generic[_T]):
    name: str
    default_value: _T

    @classmethod
    def new(cls, name: str, default_value: _T) -> "DiscriminatorField[_T]":
        return cls(name, default_value)

    @property
    def type(self) -> Type[_T]:
        return type(self.default_value)

    def __iter__(self) -> Iterable[_T]:
        yield self.name
        yield self.default_value


def monkeypatch_discriminator_field(
        cls: Type[SettingsFragment],
        df: DiscriminatorField | tuple):
    df = DiscriminatorField.new(*df)
    cls._add_field(
        name=df.name,
        dtype=type(df.default_value),
        has_default=True,
        default_value=df.default_value)
    cls._fields[df.name].discriminates = True
    return cls
