from time import sleep

import click
import obsws_python as obs
from rich import print

from config import config
from obs_tools.sc2client import sc2client
from obs_tools.types import Screen, UIInfo


@click.command()
def main():
    """Monitor SC2 UI through client API and let OBS know when loading screen is active"""
    with obs.ReqClient(
        host="localhost", port=4455, password=config.obs_ws_pw, timeout=3
    ) as cl:
        resp = cl.get_version()
        print(f"OBS Version: {resp.obs_version}")

        while True:
            ui = sc2client.get_screens()

            if ui is None:
                print("SC2 not running?")
                sleep(5)
                continue

            if len(ui.activeScreens) and Screen.loading in ui.activeScreens:
                print(Screen.loading)

                data = {"message": Screen.loading}

                cl.call_vendor_request(
                    vendor_name="AdvancedSceneSwitcher",
                    request_type="AdvancedSceneSwitcherMessage",
                    request_data=data,
                )
                sleep(5)
            elif len(ui.activeScreens) == 0:
                print("In game")
                sleep(10)
            else:
                sleep(0.25)


if __name__ == "__main__":
    main()
