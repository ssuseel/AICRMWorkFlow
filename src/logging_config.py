"""Application logging configuration."""

import logging

from src.config.settings import get_settings


def configure_logging() -> logging.Logger:
    settings = get_settings()
    level = getattr(logging, settings.log_level, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return logging.getLogger("aicrm")
