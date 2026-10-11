import logging
import sys

from constants import APP_ENV, SERVICE_NAME

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
VERBOSE_ENVIRONMENTS = ("LOCAL", "TEST")
NOISY_LIBRARIES = ["asyncio", "watchfiles"]


def setup_logging() -> None:
    level = logging.DEBUG if APP_ENV.upper() in VERBOSE_ENVIRONMENTS else logging.INFO

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))

    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    root_logger.handlers = [handler]

    for library in NOISY_LIBRARIES:
        logging.getLogger(library).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"{SERVICE_NAME}.{name}")
