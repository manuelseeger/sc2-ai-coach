# SC2 AI coach and streaming tools

## AI Coach

[coach.py](coach.py) and [aicoach/aicoach.py](aicoach/aicoach.py) is a GPT-4 powered coach that can help a StarCraft ladder player. It's set up to run with a voice interface during a gaming session and can answer questions from replay history and about opponents such as

- When did I last play againt this player?
- What was the opening build order of this player, in summary?
- Is this player a smurf?
- Translate the ingame conversion to English please.

The AI coach is embedded with a voice engine and can be interacted with live during gameplay via microphone.

New chat sessions with the AI coach are initiated when a new ladder game is starting ([obs_tools/](obs_tools/)), when a game just finished, or on voice command ("hey jarvis").

The GPT assistant behind AI coach can use mulitple high level capabilities like query a MongoDB replay database, lookup a player's battle net profile, or add data such as comments to a replay. The assistant decides autonomously without explicit programming when to employ a capability.

![Alt text](archive/aicoach-replaydb-example.png "a title")

## SC2 map stats

[parse_map_loading_screen.py](parse_map_loading_screen.py) can parse the currently played map from a screenshot and provide a stream overlay with this season's map win/loss statistics by matchup. The statistics are taken from https://sc2replaystats.com/ if a public account exists for the player.

## SC2 replay stats

This is a quick hack to show the players 1v1 win/loss stats of the current season. The stats are serves as a simple HTML table via localhost:8080 and can be included in a stream overlay in OBS.

#### How to embed

Embed in OBS as a browser source with a local file for map stats, and on localhost:8080 for replay stats. Adapt template.html to change the styling of the result table.

Note: scanning replays is slow (~0.2-0.5 seconds per replay). Per default this auto-refreshes every 30 seconds. This can be adjusted in template.html as well.

![example](example.png)
