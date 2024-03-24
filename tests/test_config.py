from rich import print
from config import Config

def test_load_config(): 
    config: Config = Config()
    print(config)
    assert config.name == "AICoach"
    assert config.student.name == "zatic"
    assert config.instant_leave_max == 50
    assert config.deamon_polling_rate == 10
    assert config.microphone_index == 2
    assert config.oww_model == "hey_jarvis"
    assert config.oww_sensitivity == 0.7
    assert config.recognizer.energy_threshold == 400
    assert config.assistant_id.get_secret_value() == "1234"