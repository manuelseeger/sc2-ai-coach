import importlib
import logging
from types import SimpleNamespace

from src.playeridentity import PlayerIdentityEnrichmentError
from src.replays.types import Replay


def test_process_new_file_logs_and_continues_on_player_identity_enrichment_failure(
    mocker, runtime_settings, caplog
):
    newreplay = importlib.import_module("src.events.newreplay")

    replay = Replay.model_construct(id="a" * 64)
    reader = mocker.Mock()
    reader.load_replay_raw.return_value = object()
    reader.apply_filters.return_value = True
    reader.to_typed_replay.return_value = replay
    mocker.patch.object(newreplay, "ReplayReader", return_value=reader)

    replay_store = mocker.Mock()
    replay_store.upsert.return_value = SimpleNamespace(acknowledged=True)
    signal_put = mocker.patch.object(newreplay.signal_queue, "put")

    player_identity_enricher = mocker.Mock()
    player_identity_enricher.save_from_replay.side_effect = (
        PlayerIdentityEnrichmentError(
            "Failed to persist player identity",
            opponent_name="KnownOpponent",
            toon_handle="2-S2-1-6861867",
        )
    )

    handler = newreplay.NewReplayHandler(
        replay_store=replay_store,
        player_identity_enricher=player_identity_enricher,
        settings=runtime_settings,
    )

    with caplog.at_level(logging.ERROR):
        handler.process_new_file("example.SC2Replay")

    signal_put.assert_called_once()
    assert signal_put.call_args.args[0].replay is replay
    assert "Failed to persist player identity" in caplog.text
    assert "KnownOpponent" in caplog.text
