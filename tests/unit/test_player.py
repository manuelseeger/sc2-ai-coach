from datetime import datetime, timedelta, timezone

import pytest

from obs_tools.playerinfo import is_portrait_match


@pytest.mark.parametrize(
    "portrait_file, map_name, replay_date, expected",
    [
        (
            "Alcyone LE - Atreyu vs zatic 2024-06-07 17-07-24_portrait.png",
            "Alcyone LE",
            datetime(2024, 6, 7, 17, 7, 24),
            True,
        ),
        (
            "Alcyone LE - Atreyu vs zatic 2024-06-07 17-07-24_portrait.png",
            "Different Map",
            datetime(2024, 6, 7, 17, 7, 24),
            False,  # Different map
        ),
        (
            "Alcyone LE - Atreyu vs zatic 2024-06-07 17-07-24_portrait.png",
            "Alcyone LE",
            datetime(2024, 6, 7, 17, 7, 24),
            True,
        ),
        (
            "Alcyone LE - Atreyu vs zatic 2024-06-07 17-07-24_portrait.png",
            "Alcyone LE",
            datetime(2024, 6, 7, 17, 15, 0),
            False,  # 8 minutes difference
        ),
        (
            "Different filename.png",
            "Alcyone LE",
            datetime(2024, 6, 7, 17, 7, 24),
            False,  # Filename doeesn't match
        ),
        (
            "solaris le - Zatic vs BARCODE 2024-01-14 20-32-50.png",
            "Solaris LE",
            datetime(2024, 1, 14, 20, 32, 50),
            True,
        ),
    ],
)
def test_match_portrait_filename(portrait_file, map_name, replay_date, expected):
    assert is_portrait_match(portrait_file, map_name, replay_date) == expected
