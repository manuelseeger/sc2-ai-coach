import obsws_python as obs
import click

from time import sleep

from obs_tools.sc2client import sc2client
from config import config
from obs_tools.types import UIInfo, Screen
from rich import print

@click.command()
def main():
    with obs.ReqClient(host='localhost', port=4455, password=config.obs_ws_pw, timeout=3) as cl:
        resp = cl.get_version()
        print(f"OBS Version: {resp.obs_version}")

        while True:
            ui = sc2client.get_screens()

            if len(ui.activeScreens) and Screen.loading in ui.activeScreens:
                print(Screen.loading)
    
                data = {
                    "message": Screen.loading
                }

                cl.call_vendor_request(vendor_name="AdvancedSceneSwitcher", request_type="AdvancedSceneSwitcherMessage", request_data=data)
                sleep(5)
            elif len(ui.activeScreens) == 0:
                print("In game")
                sleep(10)
            else:
                sleep(0.25)


if __name__ == '__main__':
    main()