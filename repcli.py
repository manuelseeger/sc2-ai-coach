from dotenv import load_dotenv

load_dotenv()

import glob
import os
import click
import datetime
from replays.replaydb import ReplayDB

from os.path import join, basename, getmtime
from datetime import datetime
import logging
import sys
from time import sleep
from datetime import date
from rich import print

from config import config

log = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
log.addHandler(handler)

db = ReplayDB()


@click.group()
@click.option("--clean", is_flag=True, default=False, help="Delete filtered replays")
@click.option("--debug", is_flag=True, default=False, help="Print debug messages")
@click.pass_context
def cli(ctx, clean, debug):
    ctx.ensure_object(dict)
    ctx.obj["CLEAN"] = clean
    ctx.obj["DEBUG"] = debug

    print("Debug mode is %s" % ("on" if debug else "off"))
    print("Clean mode is %s" % ("on" if clean else "off"))

    log.setLevel(logging.DEBUG)


@cli.command()
@click.pass_context
def deamon(ctx):
    print("Monitoring folder for new replays")
    print("Press Ctrl+C to exit")
    list_of_files = glob.glob(join(config.replay_folder, "*.SC2Replay"))

    try:
        while True:
            new_list_of_files = glob.glob(join(config.replay_folder, "*.SC2Replay"))
            new_list_of_files = [f for f in new_list_of_files if f not in list_of_files]
            for file_path in new_list_of_files:
                sleep(5)
                replay = db.load_replay(file_path)
                if db.apply_filters(replay):
                    print(f"Adding {basename(file_path)}")
                    db.upsert_replay(replay)
                else:
                    print(f"Filtered {basename(file_path)}")
                    if db.is_instant_leave(replay) and ctx.obj["CLEAN"]:
                        os.remove(file_path)
                        print(f"Deleted {basename(file_path)}")
            list_of_files = new_list_of_files + list_of_files
            sleep(config.deamon_polling_rate)
    except KeyboardInterrupt:
        print("Exiting")


@cli.command()
@click.pass_context
@click.option(
    "--delta", "-d", default=True, help="Only parse and push delta compared to upstream"
)
def sync(ctx, delta):
    most_recent = db.get_most_recent()
    most_recent_date = most_recent["unix_timestamp"]

    # get date from timestamp:
    sync_date = datetime.fromtimestamp(most_recent_date).strftime("%Y-%m-%d %H:%M:%S")
    print(f"Syncing from most recent replay in DB {sync_date}")

    list_of_files = glob.glob(join(config.replay_folder, "*.SC2Replay"))
    list_of_files = [f for f in list_of_files if most_recent_date <= getmtime(f)]

    list_of_files.sort(key=getmtime)

    print(f"Found {len(list_of_files)} replays to sync")

    for file_path in list_of_files:
        replay = db.load_replay(file_path)
        if db.apply_filters(replay):
            print(f"Adding {basename(file_path)}")
            db.upsert_replay(replay)
        else:
            print(f"Filtered {basename(file_path)}")
            if db.is_instant_leave(replay) and ctx.obj["CLEAN"]:
                os.remove(file_path)
                print(f"Deleted {basename(file_path)}")


@cli.command()
@click.pass_context
@click.option(
    "--from",
    "-f",
    "from_",
    help="Start date for replay search",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=str(date.today()),
)
@click.option(
    "--to",
    "-t",
    "to_",
    help="End date for replay search",
    type=click.DateTime(formats=["%Y-%m-%d"]),
    default=str(date.today()),
)
@click.argument("replay", type=click.Path(exists=True), required=False)
def echo(ctx, from_: datetime, to_: datetime, replay: str):
    print(f"Syncing from most recent replay in DB {from_}")

    if replay:
        list_of_files = [replay]
    else:
        list_of_files = glob.glob(join(config.replay_folder, "*.SC2Replay"))
        list_of_files = [
            f
            for f in list_of_files
            if from_.timestamp() <= getmtime(f) and to_.timestamp() >= getmtime(f)
        ]

    list_of_files.sort(key=getmtime)

    print(f"Found {len(list_of_files)} replays to echo")

    for file_path in list_of_files:
        replay = db.load_replay(file_path)
        if db.apply_filters(replay):
            print(f"Adding {basename(file_path)}")
            print(replay)
        else:
            print(f"Filtered {basename(file_path)}")


@cli.command()
def clean():
    pass


if __name__ == "__main__":
    try:
        cli(obj={})
    finally:
        db.close()
