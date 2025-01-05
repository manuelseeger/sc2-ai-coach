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


def test_twitch_result_types():
    from obs_tools.types import TwitchChatResult, TwitchFollowResult, TwitchRaidResult

    chat_result = TwitchChatResult(message="test", user="test", channel="test")
    assert chat_result.message == "test"

    follow_result = TwitchFollowResult(user="test", event={"test": "test"})
    assert follow_result.user == "test"
    assert follow_result.event == {"test": "test"}

    raid_result = TwitchRaidResult(user="test", viewers=11)
    assert raid_result.user == "test"
    assert raid_result.viewers == 11
