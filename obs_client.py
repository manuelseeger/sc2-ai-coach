from time import sleep

import click
import obsws_python as obsws
from rich import print

from config import config
from obs_tools.sc2client import sc2client
from obs_tools.types import Screen


# we set this up as a standalone process so that OBS can run and react to SC2 UI changes without the need
# to run the rest of the project.
# This will send the currently visible screen(s) in SC2 menus to OBS via the AdvancedSceneSwitcher plugin
# If ingame, it will send "In game" to OBS
# AdvancedSceneSwitcher can use these messages in macro conditions
@click.command()
@click.option("--verbose", is_flag=True)
def main(verbose):
    """Monitor SC2 UI through client API and let OBS know when loading screen is active"""

    menu_screens = set([Screen.background, Screen.foreground, Screen.navigation])

    try:
        with obsws.ReqClient(
            host="localhost", port=4455, password=config.obs_ws_pw, timeout=3
        ) as obs:
            resp = obs.get_version()
            print(f"OBS Version: {resp.obs_version}")

            last_ui = None
            while True:
                ui = sc2client.get_uiinfo()

                if ui is None:
                    print(":warning: SC2 not running?")
                    sleep(5)
                    continue

                if ui == last_ui:
                    # only notify OBS on changes
                    sleep(0.5)
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
    
    except (ConnectionRefusedError, ConnectionError) as e:
        print(":x: Can't connect to OBS; Not running or web sockets off?")
    except Exception as e:
        print(":x: " + str(e))

if __name__ == "__main__":
    main()
