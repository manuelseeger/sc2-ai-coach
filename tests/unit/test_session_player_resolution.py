from types import SimpleNamespace

from persistence.replay_store import PlayerInfo
from session import AISession


def test_initiate_from_game_start_resolves_player_then_loads_recent_replays(
    runtime_settings, mocker, monkeypatch
):
    session = object.__new__(AISession)
    session.settings = runtime_settings
    session.player_resolver = mocker.Mock()
    session.replay_store = mocker.Mock()
    session.session_store = mocker.Mock()
    session.coach = mocker.Mock()
    session.coach.create_conversation.return_value = "conversation-id"
    session.session = SimpleNamespace(current_conversation=None, conversations=[])
    session.last_rep_id = "different-replay"
    session._conversation_id = None
    session.twitch_conversation_id = None
    session.say = mocker.Mock()

    playerinfo = PlayerInfo(
        id="2-S2-1-6861867",
        name="KnownOpponent",
        toon_handle="2-S2-1-6861867",
    )
    replay = mocker.Mock()
    replay.id = "replay-1"
    replay.default_projection_json.return_value = '{"id":"replay-1"}'

    session.player_resolver.resolve_player.return_value = playerinfo
    session.replay_store.get_recent_for_player.return_value = [replay]

    monkeypatch.setattr(
        "session.get_sc2pulse_match_history",
        mocker.Mock(return_value=None),
    )
    monkeypatch.setattr(
        "session.Templates",
        SimpleNamespace(
            new_game=SimpleNamespace(
                render=mocker.Mock(return_value="new-game-prompt")
            ),
            rematch=SimpleNamespace(render=mocker.Mock(return_value="rematch-prompt")),
            new_game_empty=SimpleNamespace(
                render=mocker.Mock(return_value="empty-prompt")
            ),
        ),
    )

    session.initiate_from_game_start("Post-Youth LE", "KnownOpponent", 4000)

    session.player_resolver.resolve_player.assert_called_once_with(
        "KnownOpponent", "Post-Youth LE", 4000
    )
    session.replay_store.get_recent_for_player.assert_called_once_with(
        playerinfo.toon_handle
    )
    session.coach.create_conversation.assert_called_once()
