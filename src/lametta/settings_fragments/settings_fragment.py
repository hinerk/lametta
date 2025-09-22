from logging import getLogger
from typing import (
    Optional,
    Type,
    TypeVar,
    get_args,
    get_origin,
    Iterable,
    Annotated,
)

from ..field import Field, FieldAlias
from .protocol import (
    SettingsFragment,
    is_settings_fragment_type,
    IS_SETTINGS_FRAGMENT_FLAG,
)
from .type_validation import validate_settings_fragment_class
from .instantiation import load


logger = getLogger(__name__)


def _settings_fragment_repr(self: SettingsFragment):
    repr_fractions = []
    for name, field in self._fields.items():
        if hasattr(self, name):
            value = getattr(self, name)
            repr_fractions.append(f"{name}={value!r}")
        else:
            repr_fractions.append(f"<missing value for {name!r}>")
    return f"{self.__class__.__name__}({', '.join(repr_fractions)})"


def _settings_fragment_init(self: SettingsFragment, **kwargs):
    for field, value in load(self.__class__, **kwargs):
        setattr(self, field, value)


# *** monkey-patched class-methods ********************************************

_U = TypeVar("_U")
def add_field(
        cls: Type[SettingsFragment],
        name: str,
        dtype: Optional[type] = None,
        has_default: bool = False,
        default_value: _U = None,
):
    # inject type annotation for discriminating field
    cls.__annotations__[name] = dtype

    # set the default value for discriminating field
    if has_default:
        setattr(cls, name, default_value)

    # re-run self-inspection:
    cls._update_field_info()


def update_fields(cls: Type[SettingsFragment]):
    cls._fields = {x.name: x for x in inspect_settings_fragment(cls)}
    return cls._fields


def get_discriminating_field(cls: Type[SettingsFragment]):
    for name, field in cls._fields.items():
        if field.discriminates:
            return field
    return None


# *** class initialization ****************************************************

def inspect_settings_fragment(cls) -> Iterable[Field]:
    """retrieve data type configuration from class annotations"""
    for field_name, field_type in cls.__annotations__.items():
        field_alias = None
        # gather additional field info from annotation
        if get_origin(field_type) is Annotated:
            field_type, *annotations = get_args(field_type)
            for annotation in annotations:
                if isinstance(annotation, FieldAlias):
                    field_alias = annotation.alias
        if field_name.startswith("_"):
            # skip private attributes
            continue

        if is_settings_fragment_type(field_type):
            has_default = True
            default_value = getattr(cls, field_name, {})
        else:
            has_default = hasattr(cls, field_name)
            default_value = getattr(cls, field_name, None)

        yield Field(name=field_name,
                    type=field_type,
                    has_default=has_default,
                    default_value=default_value,
                    alias=field_alias)


def _attribute_is_overloaded(obj, attribute):
    """test whether an attribute is overloaded

    NOTE: if `obj` doesn't contain `attribute` it is technically not
    overloaded! So this function returns False in that case. Like it or not
    """
    if not hasattr(obj, attribute):
        return False

    if not hasattr(object, attribute):
        return True

    return getattr(obj, attribute) is not getattr(object, attribute)


def safely_setattr(obj, attr, value, dont_touch_overloaded_attributes: bool = True):
    if dont_touch_overloaded_attributes and _attribute_is_overloaded(obj, attr):
        logger.debug(f"overloaded attribute {attr!r} in object {obj!r}")
        return

    setattr(obj, attr, value)


def monkeypatch_settings_fragment(cls) -> type[SettingsFragment]:
    safely_setattr(cls, IS_SETTINGS_FRAGMENT_FLAG, ...)
    safely_setattr(cls, "__init__", _settings_fragment_init, True)
    safely_setattr(cls, "__repr__", _settings_fragment_repr, True)
    safely_setattr(cls, "_update_field_info", lambda: update_fields(cls))
    update_fields(cls)
    safely_setattr(cls, "_add_field", lambda *args, **kwargs: add_field(cls,
                                                                  *args, **kwargs))
    safely_setattr(cls, "get_field_info", lambda: cls._fields)
    safely_setattr(cls, "get_discriminating_field", lambda:
    get_discriminating_field(cls))

    validate_settings_fragment_class(cls)
    return cls
