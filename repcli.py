import datetime
import glob
import json
import logging
import os
from datetime import date, datetime, timedelta
from io import BytesIO
from os.path import basename, getmtime, join

import click
import climage
import numpy as np
from PIL import Image
from pydantic import BaseModel, Field
from rich.console import Console
from rich.logging import RichHandler
from rich.table import Table
from rich.theme import Theme

from aicoach.utils import force_valid_json_string
from config import config
from obs_tools.playerinfo import save_player_info
from replays.db import replaydb
from replays.reader import ReplayReader
from replays.types import PlayerInfo, Replay

custom_theme = Theme(
    {
        "on": "bold green",
        "off": "bold red",
    }
)

console = Console(theme=custom_theme)

log = logging.getLogger()
log.setLevel(logging.WARNING)
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
@click.option(
    "--verbose", "-v", is_flag=True, default=False, help="Print verbose output"
)
@click.pass_context
def cli(ctx, clean, debug, simulation, verbose):
    ctx.ensure_object(dict)
    ctx.obj["CLEAN"] = clean
    ctx.obj["DEBUG"] = debug
    ctx.obj["SIMULATION"] = simulation
    ctx.obj["VERBOSE"] = verbose

    console.print("Debug mode is %s" % ("[on]on[/on]" if debug else "[off]off[/off]"))
    console.print("Clean mode is %s" % ("[on]on[/on]" if clean else "[off]off[/off]"))
    console.print(
        "Simulation mode is %s" % ("[on]on[/on]" if simulation else "[off]off[/off]")
    )
    console.print(
        "Verbose mode is %s" % ("[on]on[/on]" if verbose else "[off]off[/off]")
    )

    if debug:
        log.setLevel(logging.DEBUG)
    else:
        logging.getLogger("sc2reader").setLevel(logging.CRITICAL)


class SyncSummary(BaseModel):
    afk_replays: int = Field(title="Replays with AFK players", default=0)
    instant_leave_replays: int = Field(title="Instant leave replays", default=0)
    deleted_replays: int = Field(title="Deleted replays", default=0)
    total_replays: int = Field(title="Total replays", default=0)
    players_added: int = Field(title="Players added", default=0)
    replays_added: int = Field(title="Replays added", default=0)
    portraits_added: int = Field(title="Portraits added", default=0)
    portraits_constructed: int = Field(title="Portraits constructed", default=0)
    filtered_replays: int = Field(title="Filtered replays", default=0)
    players: list[str] = []


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
@click.argument("entity", nargs=2, type=click.Choice(["players", "replays"]))
def sync(
    ctx,
    from_: datetime,
    to_: datetime,
    from_most_recent: bool,
    entity: tuple[str, str],
):
    """Sync replays and players from replay folder to MongoDB"""

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

    console.print(f"Found {len(list_of_files)} potential replays to sync")

    summary = SyncSummary()
    summary.total_replays = len(list_of_files)

    for file_path in list_of_files:
        replay_raw = reader.load_replay_raw(file_path)
        if reader.apply_filters(replay_raw):
            console.print(f"Adding {basename(file_path)}")
            replay = reader.to_typed_replay(replay_raw)

            if "replays" in entity:
                syncreplay(ctx, replay, summary)

            if "players" in entity:
                syncplayer(ctx, replay, summary)
        else:
            console.print(f"Filtered {basename(file_path)}")
            summary.filtered_replays += 1
            if reader.is_archon_mode(replay_raw):
                console.print(
                    f":couple: Archon mode is not supported {basename(file_path)}"
                )
                continue
            if reader.is_instant_leave(replay_raw):
                summary.instant_leave_replays += 1
                if ctx.obj["CLEAN"]:
                    summary.deleted_replays += 1
                    os.remove(file_path)
                    console.print(f":litter_in_bin_sign: Deleted {basename(file_path)}")
                    continue
            if reader.has_afk_player(replay_raw):
                summary.afk_replays += 1
                if ctx.obj["CLEAN"]:
                    summary.deleted_replays += 1
                    os.remove(file_path)
                    console.print(f":litter_in_bin_sign: Deleted {basename(file_path)}")
                    continue

    table = Table(title="Summary")
    table.add_column("Stat", justify="left", style="bold", no_wrap=True)
    table.add_column("Value", justify="left", style="cyan")

    for field_name, field_info in summary.model_fields.items():
        if field_name == "players":
            continue
        table.add_row(field_info.title, str(getattr(summary, field_name)))

    console.print(table)


@cli.group()
@click.pass_context
def query(ctx):
    "Query the DB for replays and players"
    pass


@query.command()
@click.pass_context
@click.option("--query", "-q", type=str, prompt="MongoDB Query")
def players(ctx, query):
    """Query the DB for players"""
    query = force_valid_json_string(query)
    query = json.loads(query)

    players = replaydb.db.find_many(PlayerInfo, raw_query=query)
    for player in players:
        console.print_json(str(player))
        if ctx.obj["VERBOSE"]:
            print_player_portrait(player)


@cli.command()
@click.pass_context
@click.argument("replay", type=click.Path(exists=True), required=True)
@click.option("--json", "-j", is_flag=True, default=False, help="Print in JSON")
def echo(ctx, replay, json):
    """Echo pretty-printed parsed replay data from a .SC2Replay file"""
    rep = reader.load_replay(replay)
    if json:
        console.print_json(rep.default_projection_json())
    else:
        console.print(rep)


def print_player_portrait(player: PlayerInfo):
    portrait = player.portrait or player.portrait_constructed
    if portrait:
        img = Image.open(BytesIO(portrait)).resize((40, 40))
        arr = np.array(img)
        output = climage.convert_array(
            arr, is_unicode=True, is_256color=False, is_truecolor=True
        )
        print(output)


def syncplayer(ctx, replay: Replay, summary: SyncSummary):
    opponent = replay.get_opponent_of(config.student.name)

    if ctx.obj["SIMULATION"]:
        console.print(f"Simulation, would add {opponent.name} ({opponent.toon_handle})")
    else:
        result, player_info = save_player_info(replay)

        if result.acknowledged:
            console.print(
                f":white_heavy_check_mark: {opponent.name} ({opponent.toon_handle}) added to DB from {replay}"
            )
            if player_info.toon_handle not in summary.players:
                summary.players.append(player_info.toon_handle)
                summary.players_added += 1
                summary.portraits_added += 1 if player_info.portrait else 0
                summary.portraits_constructed += (
                    1 if player_info.portrait_constructed else 0
                )
            if ctx.obj["VERBOSE"]:
                print_player_portrait(player_info)
        else:
            console.print(
                f":x: {opponent.name} ({opponent.toon_handle}) not added to DB"
            )


def syncreplay(ctx, replay: Replay, summary: SyncSummary):
    if ctx.obj["SIMULATION"]:
        console.print(f"Simulation, would add {replay}")
    else:
        result = replaydb.upsert(replay)
        if result.acknowledged:
            console.print(f":white_heavy_check_mark: {replay} added to DB")
            summary.replays_added += 1
        else:
            console.print(f":x: {replay} not added to DB")


if __name__ == "__main__":
    try:
        cli(obj={})
    finally:
        pass
