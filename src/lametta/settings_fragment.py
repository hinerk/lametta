from logging import getLogger
from pathlib import Path
from types import UnionType, NoneType
from typing import (
    Any,
    Optional,
    Type,
    TypeVar,
    get_args,
    get_origin,
    Union,
    Iterable, Generator,
)
from collections.abc import Mapping

from .field import Field
from .settings_fragment_protocol import SettingsFragment

IS_SETTINGS_FRAGMENT_FLAG = "__settings_fragment__"


logger = getLogger(__name__)


def is_settings_fragment(obj: Any) -> bool:
    return hasattr(obj, IS_SETTINGS_FRAGMENT_FLAG)


# *** validation **************************************************************

def discriminating_field_names_of_union_members(union: UnionType):
    # filter for those union members, which are actually setting fragments
    setting_fragments: list[SettingsFragment] = [
        dtype for dtype in get_args(union) if is_settings_fragment(dtype)]
    return {field_info.name for sf in setting_fragments
            if (field_info := sf.get_discriminating_field()) is not None}


def validate_union_fields(cls: SettingsFragment):
    for field in cls._fields.values():
        if get_origin(field.type) in [Union, UnionType]:
            names = discriminating_field_names_of_union_members(field.type)
            if len(names) > 1:
                raise TypeError(
                    f"{cls.__name__}.{field.name}: {field.type!r} ambiguous "
                    f"discriminating field names: {', '.join(names)}!")


def ensure_unions_exclusively_contain_setting_fragments(cls: SettingsFragment):
    for field in cls._fields.values():
        if get_origin(field.type) not in [Union, UnionType]:
            continue

        if len(args := get_args(field.type)) == 2 and args[1] is NoneType:
            # is optional type
            continue

        if all(is_settings_fragment(d) for d in args):
            continue

        inappropriate_types = [repr(d) for d in get_args(field.type)
                               if not is_settings_fragment(d)]
        raise TypeError(
            "fields which declare union types must exclusively contain "
            f"settings fragments! {cls!r}.{field.name}: {field.type!r} has "
            f"inappropriate types: {', '.join(inappropriate_types)}!")


def ensure_there_is_at_most_one_discriminating_field(
        cls: SettingsFragment):
    """only one discriminating field per setting fragment is allowed"""
    discriminating_fields: list[Field] = []
    for field in cls._fields.values():
        if field.discriminates:
            logger.debug(f"{cls!r} has discriminating field {field.name!r}")
            discriminating_fields.append(field)

    if len(discriminating_fields) > 1:
        raise TypeError(
            f"Only one discriminating field is allowed! {cls!r} discriminates "
            f"{', '.join([d.name for d in discriminating_fields])}!")


def validate_settings_fragment_class(cls: SettingsFragment):
    ensure_there_is_at_most_one_discriminating_field(cls)
    ensure_unions_exclusively_contain_setting_fragments(cls)


    validate_union_fields(cls)


# *** monkey-patched methods **************************************************

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


def try_load_as_setting_fragment(
        dtypes: Iterable[Union[SettingsFragment, type]],
        value: Any
) -> Optional[SettingsFragment]:
    if not isinstance(value, Mapping):
        logger.debug("value isn't a mapping - no need to continue!")
        return None

    setting_fragments: list[SettingsFragment] = [
        dtype for dtype in dtypes if is_settings_fragment(dtype)]

    if len(setting_fragments) == 0:
        return None

    # all settings fragments are expected to have the same discriminating field
    discriminating_field = setting_fragments[0].get_discriminating_field().name

    if discriminating_field not in value:
        logger.warning("got embedded data structure which cannot be casted to "
                       "any of the allowed setting fragments! "
                       f"data structure: {value!r}, "
                       f"allowed setting fragments: {setting_fragments!r}")
        return None

    discriminating_value = value[discriminating_field]
    logger.debug(f"discriminating_field={discriminating_field!r}, "
                 f"discriminating_value={discriminating_value!r}")

    matching_config_fragments = [
        sf for sf in setting_fragments
        if sf.get_discriminating_field().default_value == discriminating_value]

    if len(matching_config_fragments) == 0:
        logger.warning(f"no settings fragment which loads "
                       f"{discriminating_value} available!")
        return None

    return matching_config_fragments[0]


_V = TypeVar("_V")
def coerce_types(value: Any, dtype: Type[_V]) -> _V:
    if dtype is float and isinstance(value, int):
        return float(value)

    if dtype is Path and isinstance(value, str):
        return Path(value)

    return value


def validate_type(value: Any, dtype: type):
    args = get_args(dtype)
    if args == () and isinstance(value, dtype):
        return

    origin = get_origin(dtype)
    if origin in [UnionType, Union]:
        if any(isinstance(value, arg) for arg in args):
            return
        raise TypeError(f"got {value!r} ({type(value)!r}) not found amongst legit types: {args!r}!")
    elif not isinstance(value, origin):
        raise TypeError(f"got {value!r} ({type(value)!r}) instead of {dtype!r}!")

    if origin is list:
        if len(args) != 1:
            raise TypeError(f"list generic can only handle exactly one "
                            f"argument. Got {dtype!r}!")
        inner_type = args[0]
        for element in value:
            validate_type(element, inner_type)
        return

    if origin is tuple:
        if args[-1] is ...:
            # variadic length of same type
            if len(args) != 2:
                raise TypeError("tuple of variadic length must specify exactly one type!")
            inner_type = args[0]
            for element in value:
                validate_type(element, inner_type)
            return
        if len(args) != len(value):
            raise TypeError(f"{value!r} doesn't match required size ({len(value)}) derived from {dtype!r}!")
        for embedded_value, embedded_type in zip(args, value):
            validate_type(embedded_value, embedded_type)
        return

    if origin is dict:
        if len(args) != 2:
            raise TypeError(f"dict generic must specify exactly two types (got {dtype!r})!")
        key_type, value_type = args
        for key, value in value.items():
            validate_type(key, key_type)
            validate_type(value, value_type)

    raise TypeError(f"got {value!r} ({type(value)!r}) instead of {dtype!r}!")


def load_from_union_type(field: Field, value: Any):
    assert get_origin(field.type) in [Union, UnionType]
    logger.debug(f"loading {field.name}={value!r}")

    type_of_value = type(value)
    logger.debug(f"type of value is: {type_of_value!r}")

    dtypes = get_args(field.type)

    if match := try_load_as_setting_fragment(dtypes, value):
        return match(**value)

    if matching_dtype := [dt for dt in dtypes if dt == type_of_value]:
        logger.debug(f"{field!r} has type {matching_dtype!r}!")
        return value

    for dtype in dtypes:
        if is_settings_fragment(dtype):
            # already tried that ...
            continue
        try:
            # TODO: cast as dtype(*value), dtype(**value)
            return dtype(value)
        except Exception as e:
            logger.debug(f"failed casting {value!r} as {dtype!r}: {e!r}")

    types = ', '.join(repr(t) for t in get_args(field.type))
    raise TypeError(f"failed casting {value!r} to any type of {types}")


def load(
        cls: Type[SettingsFragment],
        **raw_data: Any,
) -> Generator[tuple[str, Any], None, None]:
    """used to load initialize settings fragment with data"""
    for field in cls._fields.values():
        if not field.has_default and field.name not in raw_data:
            raise AttributeError(f"Missing value for {field.name!r} in"
                                 f" {cls.__name__!r}")

        # 1. initialize value with default:
        value = field.default_value

        # 2. if data (that) has a key matching this field, set (this) value
        #    to (that) value:
        if field.name in raw_data:
            value = raw_data[field.name]

        # cast if the type of this field is declared a settings fragment
        if is_settings_fragment(field.type):
            value = field.type(**dict(load(field.type, **value)))

        # select matching setting fragment for the content if the field is a
        # union type:
        if get_origin(field.type) in [Union, UnionType]:
            value = load_from_union_type(field, value)

        value = coerce_types(value, field.type)

        # gate-check: the type of the loaded value must match the declared one:
        try:
            validate_type(value, field.type)
        except TypeError as e:
            raise TypeError(
                f"Type violation while loading data for {cls!r}.{field.name}: "
                f"got {value!r} ({type(value)!r}) instead of {field.type!r}! "
                f"(loaded data: {raw_data!r})") from e
        yield field.name, value


# *** class initialization ****************************************************

def inspect_settings_fragment(cls) -> Iterable[Field]:
    """retrieve data type configuration from class annotations"""
    for field_name, field_type in cls.__annotations__.items():
        if field_name.startswith("_"):
            # skip private attributes
            continue

        if is_settings_fragment(field_type):
            has_default = True
            default_value = getattr(cls, field_name, {})
        else:
            has_default = hasattr(cls, field_name)
            default_value = getattr(cls, field_name, None)

        yield Field(field_name, field_type, has_default, default_value)


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


def monkeypatch_settings_fragment(cls) -> SettingsFragment:
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
