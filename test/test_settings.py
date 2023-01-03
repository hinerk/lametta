import pytest
from lametta import settings


# Minimal settings fragments
@settings(discriminator_field=("kind", "Basic"))
class BasicSettings:
    url: str
    port: int

@settings(discriminator_field=("kind", "Advanced"))
class AdvancedSettings:
    url: str
    port: int
    channel: int

# Union type
EmbeddedSettings = BasicSettings | AdvancedSettings

# Top-level settings
@settings
class Settings:
    first: EmbeddedSettings
    second: EmbeddedSettings
    third: EmbeddedSettings


# --------------------------
# Tests
# --------------------------

def test_basic_instantiation():
    config = {
        "first": {"kind": "Basic", "url": "localhost", "port": 1234},
        "second": {"kind": "Basic", "url": "localhost", "port": 1235},
        "third": {"kind": "Basic", "url": "localhost", "port": 1236},
    }
    s = Settings(**config)
    assert isinstance(s.first, BasicSettings)
    assert s.first.port == 1234


def test_mixed_instantiation():
    config = {
        "first": {"kind": "Basic", "url": "x", "port": 1},
        "second": {"kind": "Advanced", "url": "x", "port": 2, "channel": 99},
        "third": {"kind": "Basic", "url": "x", "port": 3},
    }
    s = Settings(**config)
    assert isinstance(s.second, AdvancedSettings)
    assert s.second.channel == 99


def test_missing_discriminator_key_should_fail():
    config = {
        "first": {"url": "x", "port": 1},  # missing 'kind'
        "second": {"kind": "Basic", "url": "x", "port": 2},
        "third": {"kind": "Basic", "url": "x", "port": 3},
    }
    with pytest.raises(TypeError):
        Settings(**config)


def test_unknown_discriminator_value_should_warn_and_fail():
    config = {
        "first": {"kind": "Unicorn", "url": "x", "port": 1},
        "second": {"kind": "Basic", "url": "x", "port": 2},
        "third": {"kind": "Basic", "url": "x", "port": 3},
    }
    with pytest.raises(TypeError):
        Settings(**config)


def test_toml_loading():
    config = toml.loads("""
    [first]
    kind = "Basic"
    url = "localhost"
    port = 1111

    [second]
    kind = "Advanced"
    url = "localhost"
    port = 2222
    channel = 5

    [third]
    kind = "Basic"
    url = "localhost"
    port = 3333
    """)
    s = Settings(**config)
    assert isinstance(s.second, AdvancedSettings)


# 😈 Troll time — expect coercion you haven't implemented
def test_cast_string_to_int_please():
    config = {
        "first": {"kind": "Basic", "url": "x", "port": "1234"},
        "second": {"kind": "Basic", "url": "x", "port": 2},
        "third": {"kind": "Basic", "url": "x", "port": 3},
    }
    s = Settings(**config)
    assert isinstance(s.first.port, int)
    assert s.first.port == 1234  # This better not be a string, bro


def test_float_as_int_should_work_right():
    config = {
        "first": {"kind": "Basic", "url": "x", "port": 1234.0},
        "second": {"kind": "Basic", "url": "x", "port": 2},
        "third": {"kind": "Basic", "url": "x", "port": 3},
    }
    s = Settings(**config)
    assert isinstance(s.first.port, int)  # 😈 will probably fail here
    assert s.first.port == 1234


def test_inappropriate_union_types_1():
    with pytest.raises(TypeError):
        @settings
        class OtherSettings:
            value: float | str

    with pytest.raises(TypeError):
        @settings
        class OtherSettings:
            value: AdvancedSettings | str


def test_embedded_settings_fragment():
    @settings
    class EmbeddedSettings:
        field: int = 42

    @settings
    class Settings:
        field: EmbeddedSettings

    s = Settings(**{"field": {}})
    assert isinstance(s.field, EmbeddedSettings)
