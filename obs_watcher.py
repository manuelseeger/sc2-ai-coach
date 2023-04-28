import os
from parse_map_loading_screen import parse_map_loading_screen, parse_map_stats
import click
from time import sleep
from aicoach import AICoach

coach = AICoach()


@click.command()
@click.option("--screenshot", help="Screenshow file to look for")
@click.option("--runfor", help="Player to start conversation about")
@click.option("--harstem", is_flag=True, help="Harstem voice mode")
def main(screenshot, runfor, harstem):
    harstem = True
    coach.init(harstem)

    if screenshot:
        watch(screenshot)

    if runfor:
        replays = coach.get_replays(runfor)
        coach.start_conversation(runfor, replays)


def watch(filename):
    print("watching for map loading screen")
    stamp = os.stat(filename).st_mtime
    while True:
        mtime = os.stat(filename).st_mtime
        if mtime != stamp and mtime - stamp > 1:
            print("map loading screen detected")
            stamp = os.stat(filename).st_mtime
            map = None
            while map == None:
                (
                    map,
                    player1,
                    player2,
                ) = parse_map_loading_screen(filename)

            stats = None
            while stats == None:
                stats = parse_map_stats(map)

            with open("obs/map_stats.html", "w") as f:
                f.write(stats.prettify())

            if player1.lower() == "zatic":
                opponent = player2
            if player2.lower() == "zatic":
                opponent = player1
            else:
                continue

            replays = coach.get_replays(opponent)

            coach.start_conversation(opponent, replays)
        sleep(0.3)


if __name__ == "__main__":
    main()
