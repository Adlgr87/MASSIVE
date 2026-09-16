"""MASSIVE configuration package.

Exports:
    ScientificRuntimeConfig — opt-in scientific engine flags (legacy module path)
    AppSettings / get_app_settings — application YAML settings
    configure_logging / get_logger — centralized logging
"""

from massive_core.config.api_auth import (
    DEV_FALLBACK_API_KEY,
    api_key_matches,
    is_dev_env,
    is_dev_fallback_allowed,
)
from massive_core.config.logging_setup import configure_logging, get_logger
from massive_core.config.rate_limit import (
    FileRateLimiter,
    InMemoryRateLimiter,
    RateLimiter,
    build_rate_limiter,
)
from massive_core.config.scientific import ScientificRuntimeConfig
from massive_core.config.settings import (
    AppSettings,
    LLMProviderSettings,
    LoggingSettings,
    SimulationDefaults,
    clear_settings_cache,
    get_app_settings,
    get_llm_base_url,
    load_yaml_defaults,
)

__all__ = [
    "ScientificRuntimeConfig",
    "AppSettings",
    "LLMProviderSettings",
    "LoggingSettings",
    "SimulationDefaults",
    "get_app_settings",
    "get_llm_base_url",
    "load_yaml_defaults",
    "clear_settings_cache",
    "configure_logging",
    "get_logger",
    "RateLimiter",
    "InMemoryRateLimiter",
    "FileRateLimiter",
    "build_rate_limiter",
    "DEV_FALLBACK_API_KEY",
    "api_key_matches",
    "is_dev_env",
    "is_dev_fallback_allowed",
]
