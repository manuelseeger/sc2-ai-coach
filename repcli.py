from dotenv import load_dotenv

load_dotenv()

import glob
import os
import click
import datetime
from replaydb import ReplayDB

from os.path import join, basename, getmtime
from datetime import datetime
import logging
import sys
from time import sleep
import yaml

config = yaml.safe_load(open("config.yml"))

log = logging.getLogger()
handler = logging.StreamHandler(sys.stdout)
log.addHandler(handler)

db = ReplayDB(config=config, log=log)

REPLAY_FOLDER = config.get("replay_folder")


@click.group()
@click.option("--clean", is_flag=True, default=False, help="Harstem voice mode")
@click.option("--debug", is_flag=True, default=False, help="Harstem voice mode")
@click.pass_context
def cli(ctx, clean, debug):
    ctx.ensure_object(dict)
    ctx.obj["CLEAN"] = clean
    ctx.obj["DEBUG"] = debug

    if debug:
        click.echo("Debug mode is %s" % ("on" if debug else "off"))
        click.echo("Clean mode is %s" % ("on" if clean else "off"))
        db.set_debug(debug)
        log.setLevel(logging.DEBUG)


@cli.command()
@click.pass_context
def deamon(ctx):
    click.echo("Monitoring folder for new replays")
    click.echo("Press Ctrl+C to exit")
    list_of_files = glob.glob(join(REPLAY_FOLDER, "*.SC2Replay"))

    try:
        while True:
            new_list_of_files = glob.glob(join(REPLAY_FOLDER, "*.SC2Replay"))
            new_list_of_files = [f for f in new_list_of_files if f not in list_of_files]
            for file_path in new_list_of_files:
                sleep(5)
                replay = db.load_replay(file_path)
                if db.apply_filters(replay):
                    click.echo(f"Adding {basename(file_path)}")
                    db.upsert_replay(replay)
                else:
                    click.echo(f"Filtered {basename(file_path)}")
                    if db.is_instant_leave(replay) and ctx.obj["CLEAN"]:
                        os.remove(file_path)
                        click.echo(f"Deleted {basename(file_path)}")
            list_of_files = new_list_of_files + list_of_files
            sleep(config.get("deamon_polling_rate"))
    except KeyboardInterrupt:
        click.echo("Exiting")


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
    click.echo(f"Syncing from most recent replay in DB {sync_date}")

    list_of_files = glob.glob(join(REPLAY_FOLDER, "*.SC2Replay"))
    list_of_files = [f for f in list_of_files if most_recent_date <= getmtime(f)]

    list_of_files.sort(key=getmtime)

    click.echo(f"Found {len(list_of_files)} replays to sync")

    for file_path in list_of_files:
        replay = db.load_replay(file_path)
        if db.apply_filters(replay):
            click.echo(f"Adding {basename(file_path)}")
            db.upsert_replay(replay)
        else:
            click.echo(f"Filtered {basename(file_path)}")
            if db.is_instant_leave(replay) and ctx.obj["CLEAN"]:
                os.remove(file_path)
                click.echo(f"Deleted {basename(file_path)}")


@cli.command()
def clean():
    pass


if __name__ == "__main__":
    cli(obj={})
