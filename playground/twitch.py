import sys

# add parent dir to path
sys.path.append(".")
from time import sleep

from src.events.twitch import TwitchListener

twitch = TwitchListener("twitch")

twitch.start()

while True:
    sleep(1)
