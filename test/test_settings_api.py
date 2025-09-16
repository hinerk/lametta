from pathlib import Path
from typing import Optional, Annotated, Literal, List

import pytest
from datetime import datetime
from lametta import settings
from lametta.field import FieldAlias


def test_instantiation_int():
    @settings
    class Settings:
        field: int

    assert Settings(field=1).field == 1
    with pytest.raises(TypeError):
        Settings(field="1")
    with pytest.raises(TypeError):
        Settings(field=1.5)


def test_instantiation_float():
    @settings
    class Settings:
        field: float

    assert Settings(field=1.5).field == 1.5
    # int to float coercion is legit:
    assert Settings(field=1).field == 1.0, "int-to-float coercion is broken!"

    with pytest.raises(TypeError):
        Settings(field="1.5")


def test_instantiation_str():
    @settings
    class Settings:
        field: str

    assert Settings(field="1.5").field == "1.5"
    with pytest.raises(TypeError):
        Settings(field=1.5)


def test_instantiation_list():
    with pytest.raises(TypeError):
        @settings
        class Settings:
            field: list

    @settings
    class Settings:
        field: list[int]

    assert Settings(field=[1, 2, 3]).field == [1, 2, 3]

    with pytest.raises(TypeError):
        Settings(field=[1, 2, "3"])


def test_instantiation_list_2():
    with pytest.raises(TypeError):
        @settings
        class Settings:
            field: List

    @settings
    class Settings:
        field: List[int]

    assert Settings(field=[1, 2, 3]).field == [1, 2, 3]

    with pytest.raises(TypeError):
        Settings(field=[1, 2, "3"])


def test_instantiation_list_too_many_embedded_types():
    with pytest.raises(TypeError):
        @settings
        class Settings:
            field: List[int, str]

    with pytest.raises(TypeError):
        @settings
        class Settings:
            field: list[int, str]


def test_instantiation_list_typed():
    @settings
    class Settings:
        field: list[str]

    assert Settings(field=["1", "2", "3"]).field == ["1", "2", "3"]
    with pytest.raises(TypeError):
        # int instead of str
        Settings(field=[1, 2, 3])


def test_instantiation_datetime():
    @settings
    class Settings:
        field: datetime

    timestamp = datetime.now()
    assert Settings(field=timestamp).field == timestamp
    with pytest.raises(TypeError):
        Settings(field="2021-01-01")  # not the job of this framework


def test_instantiation_path():
    @settings
    class Settings:
        field: Path

    assert Settings(field="/home/").field == Path("/home/")


def test_instantiation_absent_embedded_setting_with_defaults():
    @settings
    class EmbeddedSettings:
        field: str = "content"

    @settings
    class Settings:
        embedded: EmbeddedSettings

    assert Settings().embedded.field == "content"


def test_instantiation_partially_customized_embedded_setting():
    @settings
    class EmbeddedSettings:
        field_1: str = "content"
        field_2: str   # has no default

    @settings
    class Settings:
        embedded: EmbeddedSettings

    with pytest.raises(AttributeError):
        Settings()

    assert Settings(embedded={"field_2": "custom"}).embedded.field_1 == "content"


def test_embedded_instantiation():
    ...


def test_partially_available_defaults():
    @settings
    class EmbeddedSettings:
        no_default: str
        default: str = "default value"

    @settings
    class Settings:
        embedded: EmbeddedSettings

    SETTINGS_RAW = {
        "embedded": {
            "no_default": "custom",
        }
    }
    s = Settings(**SETTINGS_RAW)
    assert s.embedded.no_default == "custom"
    assert s.embedded.default == "default value"


def test_optional():
    @settings
    class Credentials:
        value: str

    @settings
    class Settings:
        credentials: Optional[Credentials] = None

    Settings().credentials = None


def test_alternate_field_name():
    @settings(discriminator_field=("d", "option a"))
    class OptionA:
        d: str

    @settings(discriminator_field=("d", "option b"))
    class OptionB:
        d: str

    @settings
    class Settings:
        float_field: Annotated[float, FieldAlias("custom float field")] = 1.5
        list_field: Annotated[list[str], FieldAlias("custom list field")] = ["a", "b", "c"]
        option: Annotated[OptionA | OptionB, FieldAlias("custom option")]

    s = Settings(**{
        "custom float field": 2.6,
        "custom list field": ["a", "b", "c"][::-1],
        "custom option": {"d": "option a"},
    })
    assert s.float_field == 2.6
    assert s.list_field == ["a", "b", "c"][::-1]
    assert isinstance(s.option, OptionA)

def test_alternate_field_name_option_b():
    @settings(discriminator_field=("d", "option a"))
    class OptionA:
        d: str

    @settings(discriminator_field=("d", "option b"))
    class OptionB:
        d: str

    @settings
    class Settings:
        option: Annotated[OptionA | OptionB, FieldAlias("custom option")]

    s2 = Settings(**{
        "custom option": {"d": "option b"},
    })
    assert isinstance(s2.option, OptionB)


def test_alternate_field_name_2():
    @settings(discriminator_field=("d", "option a"))
    class OptionA:
        d: Annotated[str, FieldAlias("alias for d")]

    @settings(discriminator_field=("d", "option b"))
    class OptionB:
        d: Annotated[str, FieldAlias("alias for d")]

    @settings
    class Settings:
        option: OptionA | OptionB

    s = Settings(**{
        "option": {"alias for d": "option a"},
    })
    assert s.option.d == "option a"


def test_alternate_field_name_3():
    @settings(discriminator_field=("d", "option a"))
    class OptionA:
        d: Annotated[str, FieldAlias("alias for d")]

    @settings(discriminator_field=("d", "option b"))
    class OptionB:
        d: Annotated[str, FieldAlias("alias for d")]

    @settings
    class Settings:
        option: Annotated[OptionA | OptionB, FieldAlias("custom option")]

    s = Settings(**{
        "custom option": {"alias for d": "option a"},
    })
    assert s.option.d == "option a"


def test_list_of_embedded_settings():
    SETTINGS_RAW = {
        'embedded': [
            {'key': 'value 1'},
            {'key': 'value 2'},
        ]
    }

    @settings
    class SettingsElement:
        key: str

    @settings
    class ListOfSettings:
        embedded: list[SettingsElement]

    s = ListOfSettings(**SETTINGS_RAW)
    assert len(s.embedded) == 2
    assert s.embedded[0].key == "value 1"
    assert s.embedded[1].key == "value 2"
