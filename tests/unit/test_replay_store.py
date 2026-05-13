from types import SimpleNamespace

from pyodmongo.queries import sort

from src.persistence.replay_store import ReplayStore
from src.replays.types import Replay


def test_get_recent_for_player_queries_by_toon_handle_with_default_depth(mocker):
    expected = [Replay.model_construct(id="a" * 64)]
    engine = mocker.Mock()
    engine.find_many.return_value = SimpleNamespace(docs=expected)
    database = SimpleNamespace(engine=engine, raw={})

    store = ReplayStore(database)

    recent_replays = store.get_recent_for_player("2-S2-1-6861867")

    assert recent_replays == expected
    engine.find_many.assert_called_once_with(
        Model=Replay,
        paginate=True,
        current_page=1,
        docs_per_page=5,
        raw_query={"players.toon_handle": "2-S2-1-6861867"},
        sort=sort((Replay.unix_timestamp, -1)),  # type: ignore[arg-type]
    )
