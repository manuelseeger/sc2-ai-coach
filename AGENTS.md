# SC2 AI coach

LLM backed "coach" to talk to during a Starcraft2 gaming session (microphone, TTS, STT). 

Backed with a replay database and integrated with the Starcraft 2 game client. 

## Developement

Use: 
- pydantic for models throughout
- uv for package management and running python
- pyodmmongo for DB. See `docs/references/pyodmongo.md`

**Always use uv to run Python or python tools**: 
```sh
uv run coach.py --repl
uv run repcli.py --help
uv run pytest tests/unit
```

## Tools

Use MongoDB MCP to inspect the local DB (readonly).

## Running the app

During developement, testing, you may run: 
- The CLI `uv run repcli.py --validate`
- The full app in text-only mode `uv run coach.py --repl`

## Agent skills

### Issue tracker

Issues for this repo are tracked in GitHub Issues for the current repository. See `docs/agents/issue-tracker.md`.

### Triage labels

This repo uses the default triage label vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, and `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

This repo uses a single-context domain-doc layout rooted at `CONTEXT.md` with ADRs under `docs/adr/`. See `docs/agents/domain.md`.

### Browser and Frontend testing

Use the playwright skill to access api / frontend during testing. 

Make sure to run playwright with the  --headed flag during tests. 
If you need to save files during a playwright session, put them into .playwright-cli/
