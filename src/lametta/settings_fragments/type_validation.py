from logging import getLogger
from types import UnionType, NoneType
from typing import (
    Any,
    get_args,
    get_origin,
    Union,
    TypeGuard,
)

from ..field import Field
from .protocol import SettingsFragment, is_settings_fragment_type


logger = getLogger(__name__)


def is_union_type_annotation(obj: Any) -> TypeGuard[UnionType]:
    return get_origin(obj) is Union


def discriminating_field_names_of_union_members(union: UnionType):
    # filter for those union members, which are actually setting fragments
    setting_fragments: list[SettingsFragment] = [
        dtype for dtype in get_args(union) if is_settings_fragment_type(dtype)]
    return {field_info.name for sf in setting_fragments
            if (field_info := sf.get_discriminating_field()) is not None}


def validate_union_fields(cls: SettingsFragment):
    for field in cls._fields.values():
        if is_union_type_annotation(field.type):
            names = discriminating_field_names_of_union_members(field.type)
            if len(names) > 1:
                raise TypeError(
                    f"{cls.__name__}.{field.name}: {field.type!r} ambiguous "
                    f"discriminating field names: {', '.join(names)}!")


def ensure_unions_exclusively_contain_setting_fragments(cls: SettingsFragment):
    for field in cls._fields.values():
        if not is_union_type_annotation(field.type):
            continue

        if len(args := get_args(field.type)) == 2 and args[1] is NoneType:
            # is optional type
            continue

        if all(is_settings_fragment_type(d) for d in args):
            continue

        inappropriate_types = [repr(d) for d in get_args(field.type)
                               if not is_settings_fragment_type(d)]
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


def ensure_list_annotation_has_embedded_type(
        cls: SettingsFragment
):
    for field in cls._fields.values():
        if field.type != list and get_origin(field.type) is not list:
            continue

        embedded_types = get_args(field.type)
        if len(embedded_types) == 0:
            raise TypeError(f"{cls!r}.{field.name} must explicitly specify "
                            f"the expected type of the content of list!")

        if len(embedded_types) > 1:
            raise TypeError(
                f"{cls!r}.{field.name} is not allowed to hold more than one "
                f"embedded type! (got {embedded_types!r})")


def validate_settings_fragment_class(cls: SettingsFragment):
    ensure_there_is_at_most_one_discriminating_field(cls)
    ensure_unions_exclusively_contain_setting_fragments(cls)
    ensure_list_annotation_has_embedded_type(cls)

    validate_union_fields(cls)
