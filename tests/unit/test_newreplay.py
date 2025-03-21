import shutil
from pathlib import Path
from time import sleep

import pytest

from config import config
from src.events.newreplay import NewReplayHandler, NewReplayListener


@pytest.mark.parametrize(
    "replay_file",
    [
        "Equilibrium LE (84).SC2Replay",
    ],
    indirect=True,
)
def test_new_replay_added(replay_file, tmp_path: Path, mocker):
    # arrange
    config.replay_folder = tmp_path.absolute().as_posix()
    process_new_file = mocker.patch.object(NewReplayHandler, "process_new_file")
    new_replay_observer = NewReplayListener()
    new_replay_observer.start()

    # act
    shutil.copy(replay_file, tmp_path)

    # unix doesn't dispatch file created immeditely
    sleep(1)

    # assert
    process_new_file.assert_called_once()

    # cleanup
    new_replay_observer.stop()
    new_replay_observer.join()
