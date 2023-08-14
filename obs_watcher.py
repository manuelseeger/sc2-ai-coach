from dotenv import load_dotenv

load_dotenv()
import os
from parse_map_loading_screen import (
    parse_map_loading_screen,
    parse_map_stats,
    clean_map_name,
)
import click
from time import sleep
from aicoach import AICoach
import datetime
import re
import yaml
import logging
import sys
from time import sleep

config = yaml.safe_load(open("config.yml"))

log = logging.getLogger(__name__)
handler = logging.StreamHandler(sys.stdout)
log.addHandler(handler)


coach = AICoach()

cleanf = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
clean_clan = re.compile(r"<(.+)>\s+(.*)")

barcode = "llllllllll"


@click.command()
@click.option("--screenshot", help="Screenshow file to look for")
@click.option("--runfor", help="Player to start conversation about")
@click.option("--harstem", is_flag=True, help="Harstem voice mode")
@click.option("--debug", is_flag=True, help="Debug mode")
def main(screenshot, runfor, harstem, debug):
    if debug:
        log.setLevel(logging.INFO)
        handler.setLevel(logging.INFO)
        log.debug("debugging on")

    coach.init(config=config, harstem=harstem, log=log, debug=debug)

    if screenshot:
        watch(screenshot)

    if runfor:
        replays = coach.get_replays(runfor)
        coach.start_conversation(runfor, replays)


def watch(filename):
    print("watching for map loading screen")
    while True:
        if os.path.exists(filename):
            print("map loading screen detected")
            sleep(0.1)

            path, name = os.path.split(filename)
            parse = None
            while parse == None:
                parse = parse_map_loading_screen(filename)
            map, player1, player2 = parse

            map = clean_map_name(map, config["ladder_maps"])

            print(f"found: {map}, {player1}, {player2}")
            if len(player1) == 0:
                player1 = barcode
            if len(player2) == 0:
                player2 = barcode

            clan1, player1 = strip_clan_tag(player1)
            clan2, player2 = strip_clan_tag(player2)
            now = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
            new_name = f"{map} - {cleanf.sub('', player1)} vs {cleanf.sub('', player2)} {now}.png"
            new_name = re.sub(r"[^\w_. -]", "_", new_name)

            if player1.lower() == config["student"]:
                opponent = player2
            elif player2.lower() == config["student"]:
                opponent = player1
            else:
                print(f"not {config['student']}, I'll keep looking")
                continue

            write_map_stats(map)

            replays = list(coach.get_replays(opponent))

            os.rename(filename, os.path.join(path, new_name))

            if len(replays) == 0:
                print("no replays found")
                coach.say(f"Sorry, I don't have any replays of {opponent}.")
                sleep(5)
                continue

            build_orders = coach.write_replay_summary(replays, opponent)
            smurf_stats = coach.write_smurf_summary(replays, opponent)
            coach.start_conversation(opponent, build_orders, smurf_stats)
        sleep(0.3)


def strip_clan_tag(name):
    result = clean_clan.search(name)
    if result is not None:
        return result.group(1), result.group(2)
    else:
        return None, name


def write_map_stats(map):
    stats = None
    while stats == None:
        stats = parse_map_stats(map)

    with open("obs/map_stats.html", "w") as f:
        f.write(stats.prettify())


if __name__ == "__main__":
    main()
