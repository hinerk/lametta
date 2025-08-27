from typing import (
    Optional,
    Type,
)
from inspect import isclass

from .discriminator_field import DiscriminatorField
from .discriminator_field import monkeypatch_discriminator_field
from .settings_fragment import monkeypatch_settings_fragment


def settings(
        # attention: changing the order of arguments, require adapting
        # first_argument variable assignment below!
        discriminator_field: Optional[DiscriminatorField | tuple] = None,
):
    """
    decorates a settings class

    :param discriminator_field: tuple of field name and default value.
    """
    first_argument = discriminator_field

    def decorator(
            _discriminator_field: Optional[DiscriminatorField | tuple] = None,
    ):
        def wrapper(cls):
            cls = monkeypatch_settings_fragment(cls)
            if _discriminator_field is not None:
                cls = monkeypatch_discriminator_field(cls, _discriminator_field)
            return cls
        return wrapper

    if isclass(first_argument):
        # when applied like:
        #     @setting
        #     class Setting:
        #         ...
        return decorator()(first_argument)
    else:
        # when applied like:
        #     @setting(key=value)
        #     class Setting:
        #         ...
        # return function which consumes "Setting" class
        return decorator(_discriminator_field=discriminator_field)
