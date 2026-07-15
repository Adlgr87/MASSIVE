"""MASSIVE configuration package.

Exports:
    ScientificRuntimeConfig — opt-in scientific engine flags (legacy module path)
    AppSettings / get_app_settings — application YAML settings
    configure_logging / get_logger — centralized logging
"""

from massive_core.config.logging_setup import configure_logging, get_logger
from massive_core.config.scientific import ScientificRuntimeConfig
from massive_core.config.settings import (
    AppSettings,
    LoggingSettings,
    SimulationDefaults,
    clear_settings_cache,
    get_app_settings,
    load_yaml_defaults,
)

__all__ = [
    "ScientificRuntimeConfig",
    "AppSettings",
    "LoggingSettings",
    "SimulationDefaults",
    "get_app_settings",
    "load_yaml_defaults",
    "clear_settings_cache",
    "configure_logging",
    "get_logger",
]
