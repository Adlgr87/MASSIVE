"""Centralized logging configuration for MASSIVE."""

from __future__ import annotations

import logging
import logging.config
from typing import Optional

from massive_core.config.settings import LoggingSettings, get_app_settings


def configure_logging(
    level: Optional[str] = None,
    *,
    force: bool = False,
) -> None:
    """Configure root logging once for the process.

    Args:
        level: Optional override (DEBUG/INFO/…). Uses AppSettings when None.
        force: If True, reconfigure even if handlers already exist.
    """
    root = logging.getLogger()
    if root.handlers and not force:
        if level:
            root.setLevel(level.upper())
        return

    settings = get_app_settings()
    log_cfg: LoggingSettings = settings.logging
    resolved_level = (level or settings.log_level or log_cfg.level).upper()

    logging.basicConfig(
        level=resolved_level,
        format=log_cfg.format,
        datefmt=log_cfg.datefmt,
        force=force,
    )
    # Quiet noisy third-party loggers by default
    for name in ("urllib3", "httpx", "matplotlib", "asyncio"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger, ensuring base configuration exists."""
    configure_logging()
    return logging.getLogger(name)
