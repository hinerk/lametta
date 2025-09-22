from typing import (
    TypeVar,
    Generic,
    Type,
    get_origin,
    Annotated,
    get_args
)
from dataclasses import dataclass

from .settings_fragments import SettingsFragment


type Name = str
type DefaultValue = str


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

    def __iter__(self):
        yield self.name
        yield self.default_value


def monkeypatch_discriminator_field(
        cls: type[SettingsFragment],
        df: DiscriminatorField | tuple[Name, DefaultValue]):
    if isinstance(df, tuple):
        df = DiscriminatorField.new(*df)
    if df.name in cls._fields:
        # validate, that type isn't defined for field in settings class body
        if df.name in cls.__annotations__:
            type_from_class_body = cls.__annotations__[df.name]
            if get_origin(type_from_class_body) is Annotated:
                type_from_class_body = get_args(type_from_class_body)[0]
            if type_from_class_body is not df.type:
                raise TypeError(
                    f"missmatch for {cls.__name__}.{df.name} types defined in "
                    f"decorator and class body! (decorator: {df.type}, "
                    f"class body: {type_from_class_body})")
        cls._fields[df.name].default_value = df.default_value
    else:
        cls._add_field(
            name=df.name,
            dtype=type(df.default_value),
            has_default=True,
            default_value=df.default_value)

    cls._fields[df.name].discriminates = True
    return cls
