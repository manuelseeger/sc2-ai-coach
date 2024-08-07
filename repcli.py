import datetime
import glob
import json
import logging
import os
from datetime import date, datetime, timedelta
from io import BytesIO
from os.path import basename, getmtime, join
from time import sleep

import click
import climage
import numpy as np
from PIL import Image
from rich.console import Console
from rich.logging import RichHandler
from rich.theme import Theme

from aicoach.utils import force_valid_json_string
from config import config
from obs_tools.playerinfo import save_player_info
from replays.db import replaydb
from replays.reader import ReplayReader
from replays.types import Alias, PlayerInfo, Replay

custom_theme = Theme(
    {
        "on": "bold green",
        "off": "bold red",
    }
)

console = Console(theme=custom_theme)

log = logging.getLogger()
log.addHandler(RichHandler(show_time=False, rich_tracebacks=True))

reader = ReplayReader()

dformat = lambda x: datetime.fromtimestamp(x).strftime("%Y-%m-%d %H:%M:%S")


@click.group()
@click.option(
    "--clean",
    is_flag=True,
    default=False,
    help="Delete replays from instant-leave games",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Print debug messages, including replay parser",
)
@click.option(
    "--simulation",
    is_flag=True,
    default=False,
    help="Run in simulation mode, don't actually insert to DB",
)
@click.pass_context
def cli(ctx, clean, debug, simulation):
    ctx.ensure_object(dict)
    ctx.obj["CLEAN"] = clean
    ctx.obj["DEBUG"] = debug
    ctx.obj["SIMULATION"] = simulation

    console.print("Debug mode is %s" % ("[on]on[/on]" if debug else "[off]off[/off]"))
    console.print("Clean mode is %s" % ("[on]on[/on]" if clean else "[off]off[/off]"))
    console.print(
        "Simulation mode is %s" % ("[on]on[/on]" if simulation else "[off]off[/off]")
    )

    if debug:
        log.setLevel(logging.DEBUG)
    else:
        logging.getLogger("sc2reader").setLevel(logging.CRITICAL)


@cli.command()
@click.pass_context
def deamon(ctx):
    """Monitor replay folder, add new replays to MongoDB"""
    console.print("Monitoring folder for new replays")
    console.print("Press Ctrl+C to exit")
    list_of_files = glob.glob(join(config.replay_folder, "*.SC2Replay"))

    try:
        while True:
            new_list_of_files = glob.glob(join(config.replay_folder, "*.SC2Replay"))
            new_list_of_files = [f for f in new_list_of_files if f not in list_of_files]
            for file_path in new_list_of_files:
                sleep(5)
                replay_raw = reader.load_replay_raw(file_path)
                if reader.apply_filters(replay_raw):
                    console.print(f"Adding {basename(file_path)}")
                    replay = reader.to_typed_replay(replay_raw)
                    if ctx.obj["SIMULATION"]:
                        console.print(f"Simulation, would add {replay}")
                    else:
                        replaydb.upsert(replay)
                else:
                    console.print(f"Filtered {basename(file_path)}")
                    if reader.is_instant_leave(replay_raw) and ctx.obj["CLEAN"]:
                        os.remove(file_path)
                        console.print(f"Deleted {basename(file_path)}")
            list_of_files = new_list_of_files + list_of_files
            sleep(config.deamon_polling_rate)
    except KeyboardInterrupt:
        console.print("Exiting")


@cli.command()
@click.pass_context
@click.option(
    "--from",
    "-f",
    "from_",
    help="Start date for replay search",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=str(date.today()),
    show_default=True,
)
@click.option(
    "--to",
    "-t",
    "to_",
    help="End date for replay search",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=str(date.today()),
    show_default=True,
)
def addplayers(ctx, from_: datetime, to_: datetime):
    """Add player from repays to DB"""

    sync_from_date = from_.timestamp()

    sync_to_date = (to_ + timedelta(days=1)).timestamp()

    console.print(f"Syncing from {dformat(sync_from_date)} to {dformat(sync_to_date)}")
    list_of_files = glob.glob(join(config.replay_folder, "*.SC2Replay"))
    list_of_files = [
        f
        for f in list_of_files
        if sync_from_date <= getmtime(f) and sync_to_date > getmtime(f)
    ]

    list_of_files.sort(key=getmtime)

    console.print(f"Found {len(list_of_files)} potential replays to sync")

    for file_path in list_of_files:
        replay_raw = reader.load_replay_raw(file_path)
        if reader.apply_filters(replay_raw):

            replay = reader.to_typed_replay(replay_raw)
            opponent = replay.get_opponent_of(config.student.name)

            if ctx.obj["SIMULATION"]:
                console.print(
                    f"Simulation, would add {opponent.name} ({opponent.toon_handle})"
                )
            else:
                result = save_player_info(replay)
                if result.acknowledged:
                    console.print(
                        f":white_heavy_check_mark: {opponent.name} ({opponent.toon_handle}) added to DB from {replay}"
                    )
                else:
                    console.print(
                        f":x: {opponent.name} ({opponent.toon_handle}) not added to DB"
                    )


@cli.command()
@click.pass_context
@click.option(
    "--from",
    "-f",
    "from_",
    help="Start date for replay search",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=str(date.today()),
    show_default=True,
)
@click.option(
    "--to",
    "-t",
    "to_",
    help="End date for replay search",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=str(date.today()),
    show_default=True,
)
@click.option(
    "-fR",
    "--from-most-recent",
    is_flag=True,
    help="Sync from the most recent replay in DB",
    default=False,
)
@click.option(
    "-d", "--delta", is_flag=True, help="Don't update existing replays", default=False
)
def sync(ctx, from_: datetime, to_: datetime, from_most_recent: bool, delta: bool):
    """Sync replays from replay folder to MongoDB"""
    if from_most_recent:
        most_recent = replaydb.get_most_recent()
        sync_from_date = most_recent.unix_timestamp
    else:
        sync_from_date = from_.timestamp()

    sync_to_date = (to_ + timedelta(days=1)).timestamp()

    console.print(f"Syncing from {dformat(sync_from_date)} to {dformat(sync_to_date)}")
    list_of_files = glob.glob(join(config.replay_folder, "*.SC2Replay"))
    list_of_files = [
        f
        for f in list_of_files
        if sync_from_date <= getmtime(f) and sync_to_date > getmtime(f)
    ]

    list_of_files.sort(key=getmtime)

    console.print("Delta mode is %s" % ("[on]on[/on]" if delta else "[off]off[/off]"))

    console.print(f"Found {len(list_of_files)} potential replays to sync")

    for file_path in list_of_files:
        replay_raw = reader.load_replay_raw(file_path)
        if reader.apply_filters(replay_raw):
            console.print(f"Adding {basename(file_path)}")
            replay = reader.to_typed_replay(replay_raw)
            if delta:
                existing = replaydb.find(replay)
                if existing:
                    console.print(f"Replay {replay} already exists in DB")
                    continue
            if ctx.obj["SIMULATION"]:
                console.print(f"Simulation, would add {replay}")
            else:
                replaydb.upsert(replay)
                console.print(f":white_heavy_check_mark: {replay} added to DB")
        else:
            console.print(f"Filtered {basename(file_path)}")
            if reader.is_instant_leave(replay_raw) and ctx.obj["CLEAN"]:
                os.remove(file_path)
                console.print(f":litter_in_bin_sign: Deleted {basename(file_path)}")
                continue
            if reader.has_afk_player(replay_raw) and ctx.obj["CLEAN"]:
                os.remove(file_path)
                console.print(f":litter_in_bin_sign: Deleted {basename(file_path)}")
                continue


@cli.group()
@click.pass_context
def query(ctx):
    pass


@query.command()
@click.pass_context
@click.argument("query", type=str, required=True)
def players(ctx, query):
    """Query the DB for players"""
    query = force_valid_json_string(query)
    query = json.loads(query)

    players = replaydb.db.find_many(PlayerInfo, raw_query=query)
    for player in players:
        console.print_json(str(player))
        if player.portrait:
            img = Image.open(BytesIO(player.portrait)).convert("RGB").resize((40, 40))
            arr = np.array(img)
            output = climage.convert_array(arr, is_unicode=True)

            print(output)


@cli.command()
@click.pass_context
@click.argument("replay", type=click.Path(exists=True), required=True)
def echo(ctx, replay):
    """Echo pretty-printed parsed replay data from a .SC2Replay file"""
    console.print(reader.load_replay(replay))


if __name__ == "__main__":
    try:
        cli(obj={})
    finally:
        pass
