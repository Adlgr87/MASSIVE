"""Application-level settings for MASSIVE (pydantic + YAML defaults)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


class LoggingSettings(BaseModel):
    """Logging configuration."""

    level: str = "INFO"
    format: str = "%(asctime)s | %(name)-28s | %(levelname)-8s | %(message)s"
    datefmt: str = "%H:%M:%S"
    file: str | None = None  # optional rotating log path (or MASSIVE_LOG_FILE)
    max_bytes: int = Field(10_485_760, ge=1024)  # 10 MiB
    backup_count: int = Field(5, ge=0)


class SimulationDefaults(BaseModel):
    """Default simulation knobs for services/UI."""

    default_steps: int = Field(50, ge=1)
    default_seed: int = 42
    train_ratio: float = Field(0.7, gt=0.0, lt=1.0)


class AppSettings(BaseModel):
    """Top-level application settings."""

    name: str = "MASSIVE"
    env: str = "development"
    log_level: str = "INFO"
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:1234", "http://localhost:3000"]
    )
    rate_limit_per_min: int = Field(60, ge=1)
    rate_limit_backend: str = "memory"  # memory | file
    rate_limit_path: str | None = None
    max_upload_mb: int = Field(10, ge=1)
    simulation: SimulationDefaults = Field(
        default_factory=lambda: SimulationDefaults(
            default_steps=50, default_seed=42, train_ratio=0.7
        )
    )
    logging: LoggingSettings = Field(
        default_factory=lambda: LoggingSettings(
            level="INFO",
            format="%(asctime)s | %(name)-28s | %(levelname)-8s | %(message)s",
            datefmt="%H:%M:%S",
            file=None,
            max_bytes=10_485_760,
            backup_count=5,
        )
    )

    model_config = {"extra": "ignore", "validate_assignment": True}


def _defaults_path() -> Path:
    return Path(__file__).parent / "defaults.yaml"


def load_yaml_defaults(path: Path | None = None) -> dict[str, Any]:
    """Load YAML defaults from disk."""
    cfg_path = path or _defaults_path()
    if not cfg_path.exists():
        return {}
    with cfg_path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    if not isinstance(data, dict):
        return {}
    return data


@lru_cache(maxsize=4)
def get_app_settings(config_path: str | None = None) -> AppSettings:
    """Load and validate application settings (cached).

    Args:
        config_path: Optional path to a YAML file. When None, uses package defaults.

    Returns:
        Validated ``AppSettings`` instance.
    """
    raw = load_yaml_defaults(Path(config_path) if config_path else None)
    app = dict(raw.get("app") or {})
    # Nested sections from YAML
    if "simulation" in raw:
        app["simulation"] = raw["simulation"]
    if "logging" in raw:
        app["logging"] = raw["logging"]
        if "level" in raw["logging"] and "log_level" not in app:
            app["log_level"] = raw["logging"]["level"]
    return AppSettings(**app)


def clear_settings_cache() -> None:
    """Clear the ``get_app_settings`` cache (for tests)."""
    get_app_settings.cache_clear()
