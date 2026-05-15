import os
import pathlib
import sys
import time
from dataclasses import dataclass
from os.path import exists, join
from unittest.mock import MagicMock
from urllib.parse import urljoin
from uuid import uuid4

import docker
import httpx
import pytest
from pydantic import BaseModel, ValidationError
from pymongo import MongoClient
from pytest_mock import MockerFixture

from src.persistence.conversation_store import ConversationStore
from src.persistence.database import MongoDatabase, MongoDatabaseConfig
from src.persistence.replay_store import ReplayStore
from src.persistence.session_store import SessionStore
from src.runtime.settings import (
    AIBackend,
    AudioMode,
    CoachEvent,
    Config,
    RecognizerConfig,
    SC2Region,
    StudentConfig,
    TranscriberBackend,
    TTSConfig,
    WakeWordConfig,
)
from tests.support import pytest_services
from tests.support.container_services import MongoServiceHandle, start_mongo_service

pytest_services.bootstrap_test_services()

from src.lib.sc2client import NORMAL_MAP as race_map  # noqa: E402
from src.lib.sc2client import GameInfo, Race, Result  # noqa: E402
from src.lib.sc2client import Player as ApiPlayer  # noqa: E402
from src.replays.reader import ReplayReader  # noqa: E402
from src.replays.types import Player as ReplayPlayer  # noqa: E402
from tests.critic import LmmCritic  # noqa: E402

TESTDATA_DIR = "tests/testdata"


@dataclass
class SeededReplayMongoContainer:
    service: MongoServiceHandle
    settings: Config
    database: MongoDatabase
    replay_store: ReplayStore
    seeded_replays: list


def load_test_settings(**_) -> Config:
    return Config.model_construct(
        name="AICoach",
        replay_folder="tests/testdata/replays",
        instant_leave_max=50,
        deamon_polling_rate=1,
        audiomode=AudioMode.text,
        microphone_index=None,
        wakeword=WakeWordConfig(
            engine="openwakeword", model="hey_jarvis", sensitivity=0.65
        ),
        speech_recognition_model="openai/whisper-large-v3",
        transcriber_backend=TranscriberBackend.xai,
        xai_stt_language="en",
        recognizer=RecognizerConfig(
            energy_threshold=300,
            pause_threshold=0.9,
            phrase_threshold=0.3,
            non_speaking_duration=0.3,
            speech_threshold=0.3,
        ),
        wake_key="ctrl+alt+w",
        interactive=True,
        tts=TTSConfig(engine="kokoro", voice="af_heart", speed=1.25),
        student=StudentConfig(name="zatic", race="Zerg"),
        aibackend=AIBackend.openai,
        openai_endpoint=os.environ.get("AICOACH_OPENAI_ENDPOINT") or None,
        openai_api_key=os.environ.get("AICOACH_OPENAI_API_KEY", "test-api-key"),
        openai_org_id=os.environ.get("AICOACH_OPENAI_ORG_ID", "test-org-id"),
        gpt_model="gpt-5.4",
        reasoning_effort="medium",
        reasoning_continuity_enabled=False,
        coach_events=[CoachEvent.game_start, CoachEvent.wake, CoachEvent.new_replay],
        obs_integration=False,
        sc2_client_url="http://127.0.0.1:6119",
        blizzard_region=SC2Region.EU,
        include_map_details=True,
        rating_delta_max=750,
        rating_delta_max_barcode=500,
        last_played_ago_max=2400,
        match_history_depth=100,
        tessdata_dir=os.environ.get(
            "AICOACH_TESSDATA_DIR", "/usr/share/tesseract-ocr/5/tessdata/"
        ),
        log_dir=pathlib.Path("logs"),
        obs_dir=pathlib.Path("obs"),
        season=67,
        season_start=None,
        ladder_maps=[
            "Celestial Enclave LE",
            "10000 Feet LE",
            "Old Republic LE",
            "White Rabbit LE",
            "Tourmaline LE",
            "Ruby Rock LE",
            "Winter Madness LE",
            "Taito Citadel LE",
            "Mothership LE",
        ],
        default_projection={
            "id": 1,
            "date": 1,
            "game_length": 1,
            "map_name": 1,
            "players.avg_apm": 1,
            "players.highest_league": 1,
            "players.name": 1,
            "players.messages": 1,
            "players.pick_race": 1,
            "players.pid": 1,
            "players.play_race": 1,
            "players.result": 1,
            "players.scaled_rating": 1,
            "players.stats.avg_unspent_resources": 1,
            "players.toon_handle": 1,
            "players.build_order.time": 1,
            "players.build_order.name": 1,
            "players.build_order.supply": 1,
            "players.build_order.is_chronoboosted": 1,
            "players.worker_stats.worker_micro": 1,
            "players.worker_stats.worker_split": 1,
            "players.worker_stats.worker_trained_total": 1,
            "real_length": 1,
            "stats": 1,
            "unix_timestamp": 1,
        },
        db_name=os.environ.get("AICOACH_DB_NAME", "SC2AICOACH_TEST"),
        mongo_dsn=os.environ.get("AICOACH_MONGO_DSN", "mongodb://localhost:27018"),
    )


@pytest.fixture
def runtime_settings() -> Config:
    return load_test_settings()


@pytest.fixture
def mongo_database(runtime_settings: Config) -> MongoDatabase:
    return MongoDatabase(MongoDatabaseConfig.from_config(runtime_settings))


@pytest.fixture
def conversation_store(mongo_database: MongoDatabase) -> ConversationStore:
    return ConversationStore(mongo_database)


@pytest.fixture
def replay_store(mongo_database: MongoDatabase) -> ReplayStore:
    return ReplayStore(mongo_database)


@pytest.fixture
def session_store(mongo_database: MongoDatabase) -> SessionStore:
    return SessionStore(mongo_database)


@pytest.fixture
def seeded_replay_mongo_container(
    runtime_settings: Config,
) -> SeededReplayMongoContainer:  # type: ignore[return-value]
    handle = start_mongo_service(
        mode="container",
        db_name=f"SC2AICOACH_TESTDATA_{uuid4().hex}",
    )

    database = MongoDatabase(
        MongoDatabaseConfig(mongo_uri=handle.dsn, db_name=handle.db_name)
    )
    replay_store = ReplayStore(database)
    reader = ReplayReader(settings=runtime_settings)
    seeded_replays = []

    try:
        for replay_path in sorted(
            pathlib.Path(TESTDATA_DIR, "replays").glob("*.SC2Replay")
        ):
            try:
                replay = reader.load_replay(replay_path)
            except (ValidationError, ValueError):
                continue
            replay_store.upsert(replay)
            seeded_replays.append(replay)

        assert seeded_replays

        yield SeededReplayMongoContainer(  # type: ignore[return-value]
            service=handle,
            settings=runtime_settings,
            database=database,
            replay_store=replay_store,
            seeded_replays=seeded_replays,
        )
    finally:
        handle.stop()


def pytest_addoption(parser):
    return pytest_services.pytest_addoption(parser)


def pytest_configure(config):
    return pytest_services.pytest_configure(config)


def pytest_unconfigure(config):
    return pytest_services.pytest_unconfigure(config)


def only_in_debugging(func):
    """Decorator to skip tests unless a debugger is attached."""
    if sys.gettrace() is None:  # No debugger is attached
        func = pytest.mark.skip(reason="Skipping because not in debugging mode.")(func)
    return func


def only_with_live_openai(func):
    """Decorator to skip live OpenAI tests unless explicitly enabled."""
    if not os.getenv("RUN_LIVE_OPENAI_TESTS"):
        func = pytest.mark.skip(
            reason="Skipping live OpenAI test. Set RUN_LIVE_OPENAI_TESTS=1 to enable."
        )(func)
    return func


@pytest.fixture
def replay_file(request):
    return join(TESTDATA_DIR, "replays", request.param)


@pytest.fixture
def screenshot_file(request):
    return join(TESTDATA_DIR, "screenshots", request.param)


@pytest.fixture
def portrait_file(request):
    return join(TESTDATA_DIR, "portraits", request.param)


@pytest.fixture
def resource_file(request):
    return join(TESTDATA_DIR, "resources", request.param)


@pytest.fixture
def prompt_file(request):
    if request.param is None:
        # json file with same basename as python path
        json_file = pathlib.Path(request.path).with_suffix(".json")
        if exists(json_file):
            return json_file
    else:
        return join(TESTDATA_DIR, "prompts", request.param)


class Util:
    @staticmethod
    def stream_conversation(coach):
        buffer = ""
        for message in coach.stream_conversation():
            buffer += message
        return buffer

    @staticmethod
    def make_replay_mock(replay_dict):
        return ReplayRawMock(replay_dict)


class PlayerMock:
    def __init__(self, player_dict):
        self.sid = player_dict["sid"]
        self.result = player_dict["result"]


class MessageMock:
    def __init__(self, message_dict):
        self.text = message_dict["text"]
        self.pid = message_dict["pid"]


class ReplayRawMock:
    def __init__(self, replay_dict):
        self.players = [PlayerMock(p) for p in replay_dict["players"]]
        self.messages = [MessageMock(m) for m in replay_dict["messages"]]


@pytest.fixture
def util():
    return Util


@pytest.fixture
def critic():
    return LmmCritic()


@pytest.fixture(scope="session")
def mongo_service():
    service = pytest_services.get_mongo_service()
    if service is None:
        pytest.skip("MongoDB test service is disabled.")
    return service


@pytest.fixture(scope="session")
def mongo_client(mongo_service) -> MongoClient:
    return mongo_service.client


@pytest.fixture(autouse=True)
def clean_mongo_test_database(request):
    if request.node.get_closest_marker("mongo") is None:
        yield
        return

    service = pytest_services.get_mongo_service()
    if service is None:
        pytest.fail("MongoDB test service is required for mongo-marked tests.")

    service.clear_database()
    yield
    service.clear_database()


@pytest.fixture(scope="session")
def sc2api_container():
    """
    Starts a docker container from the manuelseeger/sc2apiemulator image, exposing port 6119.
    Waits until a GET request to the base URL returns HTTP 200.
    Yields the base URL for the service.
    """
    client = docker.from_env()
    container = client.containers.run(
        "manuelseeger/sc2apiemulator", detach=True, ports={"6119/tcp": 6119}
    )

    base_url = "http://localhost:6119"
    # Wait until the container is ready (max 30 seconds)
    for _ in range(30):
        try:
            response = httpx.get(base_url)
            if response.status_code == 200:
                break
        except Exception:
            pass
        time.sleep(1)
    else:
        container.stop()
        container.remove(force=True)
        pytest.fail("SC2 API emulator did not start in time.")

    yield base_url

    container.stop()
    container.remove(force=True)


@pytest.fixture
def sc2apiemulator(sc2api_container):
    """
    Returns a function that sends a POST request to the emulator.
    Accepts an optional payload (defaults to empty).
    """

    def _post(payload: BaseModel):
        return httpx.post(
            urljoin(sc2api_container, "set"), json=payload.model_dump_json()
        )

    return _post


class Player(BaseModel):
    id: int
    enabled: bool
    name: str
    race: str
    result: str


class Data(BaseModel):
    state: str
    menu_state: str
    additional_menu_state: str
    replay: bool
    players: list[Player]
    displaytime: int
    autotime: bool
    set_at: int = int(time.time())


@pytest.fixture
def sc2api_set():
    return {
        "state": "ingame",
        "menu_state": "ScreenHome/ScreenHome",
        "additional_menu_state": "None",
        "replay": False,
        "autotime": True,
        "displaytime": 0,
        "players": [
            {
                "id": 1,
                "name": "player1",
                "race": "Terr",
                "result": "Victory",
                "enabled": True,
            },
            {
                "id": 2,
                "name": "player2",
                "race": "Zerg",
                "result": "Defeat",
                "enabled": True,
            },
            {
                "id": 3,
                "name": "player3",
                "race": "Terr",
                "result": "Defeat",
                "enabled": False,
            },
            {
                "id": 4,
                "name": "player4",
                "race": "Terr",
                "result": "Victory",
                "enabled": False,
            },
            {
                "id": 5,
                "name": "player5",
                "race": "Terr",
                "result": "Defeat",
                "enabled": False,
            },
            {
                "id": 6,
                "name": "player6",
                "race": "Terr",
                "result": "Defeat",
                "enabled": False,
            },
            {
                "id": 7,
                "name": "player7",
                "race": "Terr",
                "result": "Victory",
                "enabled": False,
            },
            {
                "id": 8,
                "name": "player8",
                "race": "Terr",
                "result": "Victory",
                "enabled": False,
            },
        ],
        "set_at": int(time.time()),
    }


def replay_to_api_player(replay_player: ReplayPlayer) -> ApiPlayer:
    if replay_player.result == "Win":
        result = Result.win
    elif replay_player.result == "Loss":
        result = Result.loss
    else:
        result = Result.tie

    key = next(k for k, v in race_map.items() if v == replay_player.play_race)
    race = Race(key)
    return ApiPlayer(
        id=replay_player.uid, name=replay_player.name, result=result, race=race
    )


@pytest.fixture
def sc2api_mock(mocker: MockerFixture, replay_file):
    reader = ReplayReader()
    replay = reader.load_replay(replay_file)
    gameinfo = GameInfo(
        isReplay=True,
        displayTime=replay.real_length,
        players=[replay_to_api_player(p) for p in replay.players],
    )

    mocker.patch(
        "src.ai.functions.GetCurrentGameInfo.sc2client.get_gameinfo",
        return_value=gameinfo,
    )

    def _mock(time: int | None = None) -> MagicMock:
        if time is not None:
            gameinfo.displayTime = time
        return mocker.patch(
            "src.ai.functions.GetCurrentGameInfo.sc2client.get_gameinfo",
            return_value=gameinfo,
        )

    return _mock
