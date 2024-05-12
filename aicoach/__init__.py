from config import config

from .util import get_prompt

if config.aibackend == "Mocked":
    from .aicoach_mock import AICoachMock as AICoach
else:
    from .aicoach import AICoach
