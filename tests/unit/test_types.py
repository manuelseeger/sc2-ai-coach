import pytest

from src.replays.types import FieldTypeValidator, ToonHandle


@pytest.mark.parametrize(
    ("value", "is_valid"),
    [
        ("2-S2-1-6861867", True),
        ("2-S1-31", False),
        ("2-S1-34444-1-1-1", False),
        ([], False),
        (False, False),
        ("111111111111111111", False),
    ],
)
def test_validate_toonhandle(value, is_valid):
    assert FieldTypeValidator.validate_toon_handle(value) == is_valid


def test_toon_handle():
    toon_handle = ToonHandle("2-S2-1-6861867")
    toon_id = toon_handle.to_id()
    profile_link = toon_handle.to_profile_link()
    another_toon_handle = ToonHandle.from_id(toon_id)

    assert isinstance(toon_handle, str)
    assert toon_id == "6861867"
    assert profile_link == "https://starcraft2.com/en-us/profile/2/1/6861867"
    assert toon_handle == another_toon_handle
