"""Application runtime logger for deployment and troubleshooting."""
import logging
from logging.handlers import RotatingFileHandler

from config import LOGS_DIR


_APP_LOGGER_NAME = "arpm.app"
_LOGGER = None


def get_app_logger() -> logging.Logger:
    """Return a UTF-8 file logger for runtime status messages.

    app.log is for service/module status and errors. Do not write full user
    conversations, recalled context, or protocol analysis content to it.
    """
    global _LOGGER
    if _LOGGER is not None:
        return _LOGGER

    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(_APP_LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if not logger.handlers:
        handler = RotatingFileHandler(
            LOGS_DIR / "app.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter(
            fmt="%(asctime)s | %(levelname)s | %(module)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        ))
        logger.addHandler(handler)

    _LOGGER = logger
    return logger
