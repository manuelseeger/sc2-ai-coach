import os
from .util import get_prompt

if os.environ.get("MOCK_OPENAI"):
    from .aicoach_mock import AICoachMock as AICoach
else:
    from .aicoach import AICoach
