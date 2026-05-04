# SC2 AI coach

LLM backed "coach" to talk to during a Starcraft2 gaming session (microphone, TTS, STT). 

Backed with a replay database and integrated with the Starcraft 2 game client. 

## Developement

Use: 
- pydantic for models throughout
- uv for package management
- pytest for testing
- the mocker fixture to mock in tests

Working environment is project root. Business logic goes into src/. So make sure to import from "src.".

## Tools

Use MongoDB MCP to inspect the local DB (readonly).