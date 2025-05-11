import logging
import sys
from pathlib import Path
from time import sleep, time

import click
import obsws_python as obsws
from rich import print

from config import config
from src.lib.sc2client import SC2Client, Screen

log = logging.getLogger(__name__)
log_file = Path("logs/obs_client.log")

log.addHandler(logging.FileHandler(log_file, mode="a", encoding="utf-8"))


def log_uncaught_exceptions(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    log.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))


sys.excepthook = log_uncaught_exceptions
sys.stdout = open(log_file, "a", encoding="utf-8")


sc2client = SC2Client()


# we set this up as a standalone process so that OBS can run and react to SC2 UI changes without the need
# to run the rest of the project.
# This will send the currently visible screen(s) in SC2 menus to OBS via the AdvancedSceneSwitcher plugin
# If ingame, it will send "In game" to OBS
# AdvancedSceneSwitcher can use these messages in macro conditions
@click.command()
@click.option("--verbose", is_flag=True)
@click.option("--debug", is_flag=True)
def main(verbose, debug):
    """Monitor SC2 UI through client API and let OBS know when loading screen is active"""

    menu_screens = set([Screen.background, Screen.foreground, Screen.navigation])

    if debug:
        while True:
            ui = sc2client.get_uiinfo()
            print(ui.activeScreens)
            sleep(1)

    try:
        with obsws.ReqClient(
            host="localhost", port=4455, password=config.obs_ws_pw, timeout=3
        ) as obs:
            resp = obs.get_version()
            print(f"OBS Version: {resp.obs_version}")

            last_ui = None
            while True:
                ui = sc2client.get_uiinfo()

                with open("logs/time.log", "r") as f:
                    try:
                        last_time = float(f.read())
                    except:  # noqa: E722
                        last_time = time()
                    diff = time() - last_time
                    if diff > 15:
                        data = {"message": "fadelog"}
                    else:
                        data = {"message": "showlog"}
                    obs.call_vendor_request(
                        vendor_name="AdvancedSceneSwitcher",
                        request_type="AdvancedSceneSwitcherMessage",
                        request_data=data,
                    )

                if ui is None:
                    print(":warning: SC2 not running?")
                    sleep(5)
                    continue

                if ui == last_ui:
                    # only notify OBS on changes
                    sleep(1)
                    continue

                if verbose:
                    print(ui.activeScreens)

                if len(ui.activeScreens) == 0:
                    print("In game")
                    data = {"message": "In game"}
                    obs.call_vendor_request(
                        vendor_name="AdvancedSceneSwitcher",
                        request_type="AdvancedSceneSwitcherMessage",
                        request_data=data,
                    )
                elif Screen.loading in ui.activeScreens:
                    print(Screen.loading)

                    data = {"message": Screen.loading}
                    obs.call_vendor_request(
                        vendor_name="AdvancedSceneSwitcher",
                        request_type="AdvancedSceneSwitcherMessage",
                        request_data=data,
                    )
                elif menu_screens < ui.activeScreens:
                    menues = ui.activeScreens - menu_screens
                    print("In menues " + str(menues))
                    data = {"message": "\n".join(sorted(menues))}
                    obs.call_vendor_request(
                        vendor_name="AdvancedSceneSwitcher",
                        request_type="AdvancedSceneSwitcherMessage",
                        request_data=data,
                    )
                else:
                    pass

                last_ui = ui

    except (ConnectionRefusedError, ConnectionError):
        print(":x: Can't connect to OBS; Not running or web sockets off?")


if __name__ == "__main__":
    main()
