from types import SimpleNamespace

from pyodmongo.queries import eq, sort

from src.persistence.replay_store import ReplayStore
from src.replays.types import Replay


def test_list_replays_uses_pyodmongo_pagination(mocker):
    expected = SimpleNamespace(
        current_page=2,
        page_quantity=3,
        docs_quantity=5,
        docs=[Replay.model_construct(id="b" * 64)],
    )
    engine = mocker.Mock()
    engine.find_many.return_value = expected
    database = SimpleNamespace(engine=engine)

    store = ReplayStore(database)

    response = store.list_replays(
        current_page=2,
        docs_per_page=10,
        player="Maru",
        map_name="Acropolis",
        race="Terran",
        result="Win",
        raw_sort={"date": -1},
    )

    assert response is expected
    engine.find_many.assert_called_once_with(
        Model=Replay,
        paginate=True,
        current_page=2,
        docs_per_page=10,
        raw_query={
            "players.name": {"$regex": "Maru", "$options": "i"},
            "map_name": {"$regex": "Acropolis", "$options": "i"},
            "players.play_race": "Terran",
            "players.result": "Win",
        },
        raw_sort={"date": -1},
    )


def test_get_replay_returns_pyodmongo_result_without_raw_fallback(mocker):
    expected = Replay.model_construct(id="c" * 64)
    engine = mocker.Mock()
    engine.find_one.return_value = expected
    database = SimpleNamespace(engine=engine)

    store = ReplayStore(database)

    replay = store.get_replay(str(expected.id))

    assert replay is expected
    engine.find_one.assert_called_once_with(
        Model=Replay,
        query=eq(Replay.id, expected.id),  # type: ignore[arg-type]
    )


def test_create_replay_saves_replay_model(mocker):
    engine = mocker.Mock()
    database = SimpleNamespace(engine=engine)
    replay = Replay.model_validate(
        {
            "id": "d" * 64,
            "build": 1,
            "category": "Ladder",
            "date": "2026-01-01T00:00:00Z",
            "expansion": "LotV",
            "filehash": "e" * 64,
            "filename": "validated.SC2Replay",
            "frames": 1,
            "game_fps": 16,
            "game_length": 1,
            "game_type": "1v1",
            "is_ladder": True,
            "is_private": False,
            "map_name": "Validation LE",
            "map_size": [100, 100],
            "observers": [],
            "players": [],
            "region": "eu",
            "release": "5.0",
            "real_length": 1,
            "real_type": "1v1",
            "release_string": "5.0",
            "speed": "Faster",
            "stats": {"loserDoesGG": False},
            "time_zone": 0,
            "type": "1v1",
            "unix_timestamp": 1,
            "versions": [],
        }
    )

    store = ReplayStore(database)

    created = store.create_replay(replay)

    assert created is replay
    assert created.filename == "validated.SC2Replay"
    saved = (
        engine.save.call_args.kwargs["model"]
        if "model" in engine.save.call_args.kwargs
        else engine.save.call_args.args[0]
    )
    assert saved is replay


def test_get_recent_for_player_queries_by_toon_handle_with_default_depth(mocker):
    expected = [Replay.model_construct(id="a" * 64)]
    engine = mocker.Mock()
    engine.find_many.return_value = SimpleNamespace(docs=expected)
    database = SimpleNamespace(engine=engine)

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
