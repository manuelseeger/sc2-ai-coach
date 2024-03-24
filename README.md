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

### How to run

Please understand that this is a hobby project and not ready to run without some technical setup. You will need Python experience to get this running. This code is presented as-is and I can't provide support for it.

Prerequisites:

- A GPT4 account (API access)
- MongoDB for replays
- A NVidia GPU
- A microphone

Set up all dependencies from environment-cp311.yml (I prefer conda, but venv/pip should work too). This will need Python experience and ideally some experience with machine learning with Python.
Configure environment variables to point to your OpenAI accounts and MongoDB.
Adjust config.yml with your personal details or add your own config.custom.yml to overwrite default settings.

[parse_map_loading_screen.py](obs_tools/parse_map_loading_screen.py) needs you to setup OBS to take a screenshot when the maploading screen is showing in SC2. This is done to read the opponents name. It's possible to adjust the code to skip this but this needs some coding.

## SC2 map stats

[parse_map_loading_screen.py](obs_tools/parse_map_loading_screen.py) can parse the currently played map from a screenshot and provide a stream overlay with this season's map win/loss statistics by matchup. The statistics are taken from https://sc2replaystats.com/ if a public account exists for the player.
