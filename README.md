# SC2 replay stats server

This is a quick hack to show the players 1v1 win/loss stats of the current season. The stats are serves as a simple HTML table via localhost:8080 and can be included in a stream overlay in OBS.

Limitations: 
- This is currently hardcoded to show ZvX replays. Different matchups need rewriting the code. 
- Cannot tell apart ranked and unranked, all 1v1 replays are included in the stats


# How to run

Set 2 env variables: 

PLAYER: Name of the player in game
REPLAY_FOLDER: Local directory with the replays to scan

Run [sc2stats.py](sc2stats.py) in a Python environment that has all dependencies from requirements.txt installed. 

# How to embed

Embed in OBS as a browser source on localhost:8080. Adapt template.html to change the styling of the result table. 

Note: scanning replays is slow (~0.2-0.5 seconds per replay). Per default this auto-refreshes every 30 seconds. This can be adjusted in template.html as well. 
