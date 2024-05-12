import pytest

from config import config
from obs_tools.mapstats import get_map_stats


@pytest.mark.parametrize(
    "map_name",
    config.ladder_maps,
)
def test_save_map_stats(map_name):

    stats = get_map_stats(map_name)

    assert stats is not None
