import logging
import os
import warnings
from datetime import datetime
from pathlib import Path

from rich.traceback import install

# All application output (rich console spinner/status, file logs) is routed through
# the "AICoach" logger. Rich console output is enabled by attaching RichConsoleLogHandler
# to this logger in coach.py via _install_rich_log_handler().
#
# IMPORTANT: Any module that needs to appear on the rich console MUST use a logger that
# is a child of DEFAULT_LOGGER_NAME, e.g.:
#   log = logging.getLogger(f"{DEFAULT_LOGGER_NAME}.{__name__}")
# Using plain logging.getLogger(__name__) routes records into the "src.*" hierarchy,
# which never reaches this logger and silently drops rich output.
# propagate = False (set in configure_application_logging) stops records here so they
# don't also go to the root logger.
DEFAULT_LOGGER_NAME = "AICoach"
_OWNED_HANDLER_MARKER = "_sc2_ai_coach_owned_handler"

log = logging.getLogger(DEFAULT_LOGGER_NAME)


class FlushFilter(logging.Filter):
    def filter(self, record):
        return not hasattr(record, "flush")


def _owned_file_handler(filename: str, *, mode: str = "a") -> logging.FileHandler:
    handler = logging.FileHandler(filename, mode=mode, encoding="utf-8")
    handler.setLevel(logging.DEBUG)
    handler.addFilter(FlushFilter())
    setattr(handler, _OWNED_HANDLER_MARKER, True)
    return handler


def configure_application_logging(
    *,
    logger: logging.Logger | None = None,
    level: int = logging.DEBUG,
    log_directory: str | os.PathLike[str] = "logs",
) -> logging.Logger:
    warnings.filterwarnings("ignore")
    install(show_locals=True)

    target = logger or log
    target.setLevel(level)
    target.propagate = (
        False  # keeps records in the AICoach hierarchy; root logger has no handlers
    )

    for handler in target.handlers.copy():
        if not getattr(handler, _OWNED_HANDLER_MARKER, False):
            continue
        target.removeHandler(handler)
        handler.close()

    log_path = Path(log_directory)
    log_path.mkdir(parents=True, exist_ok=True)

    target.addHandler(
        _owned_file_handler(
            os.path.join(
                log_path,
                f"{datetime.now().strftime('%Y%m%d-%H%M%S')}-obs_watcher.log",
            )
        )
    )
    target.addHandler(_owned_file_handler(os.path.join(log_path, "_obs_watcher.log")))
    return target
