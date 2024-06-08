from datetime import datetime

import pytest

from obs_tools.playerinfo import match_portrait_filename


@pytest.mark.parametrize(
    "portrait_file, map_name, opponent_name, replay_date, expected",
    [
        (
            "Alcyone LE - Atreyu vs zatic 2024-06-07 17-07-24_portrait.png",
            "Alcyone LE",
            "zatic",
            datetime(2024, 6, 7, 17, 7, 24),
            True,
        ),
        (
            "Alcyone LE - Atreyu vs zatic 2024-06-07 17-07-24_portrait.png",
            "Different Map",
            "zatic",
            datetime(2024, 6, 7, 17, 7, 24),
            False,
        ),
        (
            "Alcyone LE - Atreyu vs zatic 2024-06-07 17-07-24_portrait.png",
            "Alcyone LE",
            "different opponent",
            datetime(2024, 6, 7, 17, 7, 24),
            False,
        ),
        (
            "Alcyone LE - Atreyu vs zatic 2024-06-07 17-07-24_portrait.png",
            "Alcyone LE",
            "Atreyu",
            datetime(2024, 6, 7, 17, 7, 25),
            True,
        ),
        (
            "Alcyone LE - Atreyu vs zatic 2024-06-07 17-07-24_portrait.png",
            "Alcyone LE",
            "Atreyu",
            datetime(2024, 6, 7, 17, 15, 0),
            False,
        ),
        (
            "Different filename.png",
            "Alcyone LE",
            "zatic",
            datetime(2024, 6, 7, 17, 7, 24),
            False,
        ),
    ],
)
def test_match_portrait_filename(
    portrait_file, map_name, opponent_name, replay_date, expected
):
    assert (
        match_portrait_filename(portrait_file, map_name, opponent_name, replay_date)
        == expected
    )
