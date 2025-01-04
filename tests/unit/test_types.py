import pytest

from replays.types import FieldTypeValidator, ToonHandle


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
