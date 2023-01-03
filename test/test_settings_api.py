from pathlib import Path

import pytest
from datetime import datetime
from lametta import settings


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
    @settings
    class Settings:
        field: list

    assert Settings(field=[1, 2, 3]).field == [1, 2, 3]


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


def test_embedded_instantiation():
    ...
