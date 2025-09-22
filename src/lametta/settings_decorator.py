from typing import overload, Callable, TypeVar, Any, cast, dataclass_transform

from .discriminator_field import AllowedDiscriminatorFieldTypes
from .discriminator_field import monkeypatch_discriminator_field
from .settings_fragment import monkeypatch_settings_fragment


C = TypeVar("C", bound=type[Any])


@overload
def settings(__cls: C, /) -> C: ...
@overload
def settings(*,
             discriminator_field: AllowedDiscriminatorFieldTypes | None = ...
             ) -> Callable[[C], C]: ...


@dataclass_transform(kw_only_default=True)
def settings(
        __cls: C | None = None,
        *, discriminator_field: AllowedDiscriminatorFieldTypes | None = None,
) -> C | Callable[[C], C]:
    """
    decorates a settings class

    :param discriminator_field: tuple of field name and default value.
    """
    def decorator(cls: C) -> C:
        out = monkeypatch_settings_fragment(cls)
        if discriminator_field is not None:
            out = monkeypatch_discriminator_field(out, discriminator_field)
        return cast(C, out)

    if __cls is not None:
        # when applied like:
        #     @setting
        #     class Setting:
        #         ...
        return decorator(__cls)
    else:
        # when applied like:
        #     @setting(key=value)
        #     class Setting:
        #         ...
        # return function which consumes "Setting" class
        return decorator
