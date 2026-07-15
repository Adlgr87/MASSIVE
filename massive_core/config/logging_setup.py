"""Centralized logging configuration for MASSIVE."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from massive_core.config.settings import LoggingSettings, get_app_settings


def configure_logging(
    level: Optional[str] = None,
    *,
    force: bool = False,
    log_file: Optional[str] = None,
) -> None:
    """Configure root logging once for the process.

    Args:
        level: Optional override (DEBUG/INFO/…). Uses AppSettings when None.
        force: If True, reconfigure even if handlers already exist.
        log_file: Optional path for a rotating file handler. Falls back to
            ``MASSIVE_LOG_FILE`` env or ``AppSettings.logging.file``.
    """
    root = logging.getLogger()
    if root.handlers and not force:
        if level:
            root.setLevel(level.upper())
        return

    settings = get_app_settings()
    log_cfg: LoggingSettings = settings.logging
    resolved_level = (level or settings.log_level or log_cfg.level).upper()

    handlers: list[logging.Handler] = [logging.StreamHandler()]
    resolved_file = (
        log_file
        or os.getenv("MASSIVE_LOG_FILE")
        or getattr(log_cfg, "file", None)
        or None
    )
    if resolved_file:
        path = Path(resolved_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            path,
            maxBytes=int(getattr(log_cfg, "max_bytes", 10_485_760) or 10_485_760),
            backupCount=int(getattr(log_cfg, "backup_count", 5) or 5),
            encoding="utf-8",
        )
        handlers.append(file_handler)

    logging.basicConfig(
        level=resolved_level,
        format=log_cfg.format,
        datefmt=log_cfg.datefmt,
        handlers=handlers,
        force=True if force or resolved_file else force,
    )
    # Quiet noisy third-party loggers by default
    for name in ("urllib3", "httpx", "matplotlib", "asyncio"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger, ensuring base configuration exists."""
    configure_logging()
    return logging.getLogger(name)
