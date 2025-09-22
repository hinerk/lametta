from logging import getLogger
from pathlib import Path
from types import UnionType
from typing import (
    Any,
    Optional,
    Type,
    TypeVar,
    get_args,
    get_origin,
    Union,
    Iterable,
    Generator,
    Literal,
    overload,
)
from collections.abc import Mapping

from ..field import Field
from .protocol import SettingsFragment, is_settings_fragment_type

logger = getLogger(__name__)


_V = TypeVar("_V")

@overload
def coerce_types(value: int, dtype: type[float]) -> float: ...
@overload
def coerce_types(value: str, dtype: type[Path]) -> Path: ...
@overload
def coerce_types(value: _V, dtype: type[_V]) -> _V: ...

def coerce_types(value, dtype):
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
    if origin is None:
        raise TypeError(f"got unsupported type spec: {dtype!r}!")

    if origin in [UnionType, Union]:
        if any(isinstance(value, arg) for arg in args):
            return
        raise TypeError(f"got {value!r} ({type(value)!r}) not found amongst legit types: {args!r}!")

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
        return

    if origin is Literal:
        if value in args:
            return

        raise TypeError(f"got {value!r}, but expected {args!r}!")

    raise TypeError(f"got {value!r} ({type(value)!r}) instead of {dtype!r}!")


def try_load_as_setting_fragment(
        dtypes: Iterable[Union[SettingsFragment, type]],
        value: Any
) -> Optional[type[SettingsFragment]]:
    if not isinstance(value, Mapping):
        logger.debug("value isn't a mapping - no need to continue!")
        return None

    setting_fragments: list[type[SettingsFragment]] = [
        dtype for dtype in dtypes if is_settings_fragment_type(dtype)]

    if len(setting_fragments) == 0:
        return None

    # all settings fragments are expected to have the same discriminating field
    discriminating_field = setting_fragments[0].get_discriminating_field()
    field_name = discriminating_field.alias or discriminating_field.name

    if field_name not in value:
        logger.warning("got embedded data structure which cannot be casted to "
                       "any of the allowed setting fragments! "
                       f"data structure: {value!r}, "
                       f"allowed setting fragments: {setting_fragments!r}")
        return None

    discriminating_value = value[field_name]
    logger.debug(f"discriminating_field={discriminating_field.name!r} "
                 f"(alias={discriminating_field.alias!r}) "
                 f"discriminating_value={discriminating_value!r}")

    matching_config_fragments = [
        sf for sf in setting_fragments
        if sf.get_discriminating_field().default_value == discriminating_value]

    if len(matching_config_fragments) == 0:
        logger.warning(f"no settings fragment which loads "
                       f"{discriminating_value} available!")
        return None

    return matching_config_fragments[0]


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
        if is_settings_fragment_type(dtype):
            # already tried that ...
            continue
        try:
            # TODO: cast as dtype(*value), dtype(**value)
            return load_arbitrary(dtype, value)
        except Exception as e:
            logger.debug(f"failed casting {value!r} as {dtype!r}: {e!r}")

    types = ', '.join(repr(t) for t in get_args(field.type))
    raise TypeError(f"failed casting {value!r} to any type of {types}")


def load_arbitrary(dtype: Type[_V], value: Any):
    if isinstance(value, Mapping):
        return dtype(**value)
    if isinstance(value, Iterable):
        return dtype(*value)
    return coerce_types(value, dtype)


def load(
        cls: Type[SettingsFragment],
        **raw_data: Any,
) -> Generator[tuple[str, Any], None, None]:
    """used to load initialize settings fragment with data"""
    for field in cls._fields.values():
        field_name = field.alias or field.name
        if not field.has_default and field_name not in raw_data:
            raise AttributeError(f"Missing value for {field_name!r} in"
                                 f" {cls.__name__!r}")

        # 1. initialize value with default:
        value = field.default_value

        # 2. if data (that) has a key matching this field, set (this) value
        #    to (that) value:
        if field_name in raw_data:
            value = raw_data[field_name]

        # cast if the type of this field is declared a settings fragment
        if is_settings_fragment_type(field.type):
            value = field.type(**dict(load(field.type, **value)))

        # select matching setting fragment for the content if the field is a
        # union type:
        if (origin := get_origin(field.type)) in [Union, UnionType]:
            value = load_from_union_type(field, value)
        elif origin is list:
            embedded_types = get_args(field.type)
            assert len(embedded_types) == 1, "list type declaration allows for exactly one embedded type!"
            assert isinstance(value, Iterable)
            embedded_type = embedded_types[0]
            if is_settings_fragment_type(embedded_type):
                value = [embedded_type(**elem) for elem in value]

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
