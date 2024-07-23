from config import config
from obs_tools.sc2client import SC2Client
from obs_tools.types import GameInfo, Screen, UIInfo


def test_uiinfo_equality_loading():
    ui1 = UIInfo(activeScreens=[Screen.loading])
    ui2 = UIInfo(activeScreens=[Screen.loading])

    assert ui1 == ui2


def test_uiinfo_equality_menus():
    ui1 = UIInfo(activeScreens=[Screen.background, Screen.foreground, Screen.navigation, Screen.home ])
    ui2 = UIInfo(activeScreens=[Screen.home, Screen.background, Screen.foreground, Screen.navigation])

    assert ui1 == ui2