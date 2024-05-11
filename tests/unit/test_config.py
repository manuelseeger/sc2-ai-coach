from rich import print
from config import Config
from config import StudentConfig


def test_load_config():
    config: Config = Config()
    print(config)
    assert isinstance(config.student, StudentConfig)
    assert isinstance(config.deamon_polling_rate, int)
    assert config.assistant_id is not None
    assert config.mongo_dsn is not None
