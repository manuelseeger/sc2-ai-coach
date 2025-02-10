import pytest

from src.ai.functions import AddMetadata


@pytest.mark.parametrize(
    "replay_id, tags",
    [
        (
            "684ace3ae5e9e40efe50342b1f7ab15611a0bbdbcc03cfc4b2e2b908b35e0a70",
            "2 rax reaper",
        ),
    ],
)
def test_function_meta_to_existing(replay_id, tags):
    response = AddMetadata(replay_id=replay_id, tags=tags)
    assert response is True
