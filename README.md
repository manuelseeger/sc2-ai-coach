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

This is my personal research project to explore the latest in LLM based agents.

![Alt text](archive/aicoach-replaydb-example.png "a title")

## Minimal Setup

Instructions for a minimal setup without voice integration. Text only, "chat with your replays". Some Python experience required.

### Python environment

Setup a minimal python environment with Anaconda:

```sh
> conda env create --name aicoach311 --file=environment-cp311-minimal.yml
> conda activate aicoach311
```

Python 3.11 is the only version that works with all dependencies at this point.

### Configuration

All settings can be done in `config.yml`, or better in a `config.yourname.yml` file in the same directory. Any config.xx.yml file overwrites values from config.yml. So you can simply add a `config.yourname.yml` file and only overwrite your student settings.

Set `replay_folder` to point to where your SC2 ladder replays are being saved.

```yaml
# config.yourname.yml

replay_folder: "C:\\Users\\yourname\\Documents\\StarCraft II\\Accounts\\1234\\2-S2-1-1234\\Replays\\Multiplayer"
student:
  name: "yourname"
  race: "Terran"
```

The rest of the settings will be taken from `config.yml`.

Secrets are configured with environment variables. Either provide them at runtime or put them in a dotenv file, like [.env.example](.env.example). (But copy to `.env` since the example file is ignored).

### OpenAI

Prerequisites:

- Setup an OpenAI account and fund with credits
- Create an OpenAI Assistant
- Create an API key.

Add your OpenAI organization, Assistant ID, and API key to the env variables, `AICOACH_ASSISTANT_ID`, `AICOACH_OPENAI_API_KEY`, `AICOACH_OPENAI_ORG_ID`.

Note on cost: Long conversations can cost up to one dollar ($1.00) in OpenAI API usage. AICoach will not incur API costs until one of the wake events is triggered - see below.

If you just want a database with your replays you can skip this step and the next or do it later.

### Build and deploy assistant

```sh
> python build.py
```

to build the assistant. You should have a new file [aicoach/assistant.json](aicoach/assistant.json).

```sh
> python build.py --deploy
```

to deploy the assistant to OpenAI. Check on https://platform.openai.com/playground if the assistant is initialized with tools and instructions.

### Database

Any MongoDB > 4.5 will do. Either setup one by yourself, or follow the instructions in [mongodb/](mongodb/README.md) on how to setup a local database for dev/testing.

If you setup your own MongoDB, create a database, and add 3 collections `replays`, `replays.meta`, `replays.players`.

Add the DB name to settings:

```yaml
# config.yourname.yml

replay_folder: "C:\\Users\\yourname\\MyReplays"
student:
  name: "yourname"
  race: "Terran"
db_name: "YOURDB"
```

and add the MongoDB connection string to the env variable `AICOACH_MONGO_DSN`.

### Populate DB

Use the tool [repcli.py](repcli.py) to populate your DB with replays. The tools offers a few options:

```sh
> python repcli.py --help
```

```text
Usage: repcli.py [OPTIONS] COMMAND [ARGS]...

Options:
  --clean       Delete replays from instant-leave games
  --debug       Print debug messages, including replay parser
  --simulation  Run in simulation mode, don't actually insert to DB
  --help        Show this message and exit.

Commands:
  deamon  Monitor replay folder, add new replays to MongoDB
  echo    Echo pretty-printed parsed replay data from a .SC2Replay file
  sync    Sync replays from replay folder to MongoDB
```

Run

```sh
> python repcli.py --simulation sync --from=2024-01-01
```

to read all 1v1 ladder replays from beginning of 2024. With the `--simulation` flag the replays will not actually be commited to DB. Remove the `--simulation` flag and run again to store all replay in DB.

The `replays` collection of the DB should now be populated with replay documents.

See `python repcli.py sync --help` for more options. You can always repopulate the DB from replay files without destroying anything. AICoach does not change anything on the replay data in the DB.

### (Optional) Additional settings

Configure a wake hotkey. On pressing this key (combination) AICoach will wake up and ask for input. Default: `ctrl+alt+w`.

Configure student.emoji if you want to show a [different icon](./playground/emojis.txt) in the terminal output.

```yaml
# config.yourname.yml

replay_folder: "C:\\Users\\yourname\\MyReplays"
student:
  name: "yourname"
  race: "Terran"
  emoji: ":woman_student:"
db_name: "YOURDB"
wake_key: "ctrl+alt+w"
```

## Run AICoach

```sh
> python coach.py
```

This will start a listener which reacts on different events. For each event, AICoach will perform an action and ask the student for input. Input can be typed into the terminal prompt.

Student can now chat with AICoach. As long as the conversation is kept going, AICoach will ask for input after it gave an answer.

AICoach determines by itself when the conversation is over. To end a conversation, simply thank AICoach.

### Wake event

Invoked when the wake key is pressed. AICoach does nothing initially and simply asks for a question.

### New replay event

When a new replay is added to the replay folder while AICoach is running, AICoach will:

- Add the replay to replay DB
- Offer to discuss the replay

On closing of the conversation, AICoach will save the conversation in `replays.meta` along with a summary and some keywords which characterize the game.

### New game event

This is invoked at the very start of an SC2 game (when the in-game clock hits 1 second). AICoach will:

- Look in the DB for existing replays of the opponent
- Summarize past strategies of the opponent
- Ask for follow up questions

You can configure which events AICoach should react to with the `coach_events` option.

```yaml
# config.yourname.yml

replay_folder: "C:\\Users\\yourname\\MyReplays"
student:
  name: "yourname"
  race: "Terran"
  emoji: ":woman_student:"
db_name: "YOURDB"
wake_key: "ctrl+alt+w"
coach_events:
  - game_start
  - wake
  - new_replay
```

## Advanced setup

Please understand that this is a hobby project and not ready to run without some technical setup. You will need Python experience to get this running. This code is presented as-is and I can't provide support for it.

Prerequisites:

- (all from minimal setup)
- NVidia GPU
- Microphone

Set up all dependencies from `environment-cp311.yml`. Review [Installation.md](Installation.md) for manual steps required. This will need Python experience and ideally some experience with machine learning with Python.

[parse_map_loading_screen.py](obs_tools/parse_map_loading_screen.py) needs you to setup OBS to take a screenshot when the maploading screen is showing in SC2. This is done to read the opponents name faster (before the game clock starts).

The OBS setup is not documented here and you can skip this part by keeping `obs_integration=False`.

## Limitations

Probably a lot...

This is meant for competitives 1v1 ladder. Team games, arcade, customs are not supported and explicidely excluded from all replay processing.

This has only been tested with replays starting from early 2023. Much older replays will likely throw errors.

## SC2 map stats

[parse_map_loading_screen.py](obs_tools/parse_map_loading_screen.py) can parse the currently played map from a screenshot and provide a stream overlay with this season's map win/loss statistics by matchup. The statistics are taken from https://sc2replaystats.com/ if a public account exists for the player.
