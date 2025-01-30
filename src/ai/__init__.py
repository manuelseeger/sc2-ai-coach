from config import config

if config.aibackend == "Mocked":
    from .aicoach_mock import AICoachMock as AICoach
else:
    from .aicoach import AICoach
