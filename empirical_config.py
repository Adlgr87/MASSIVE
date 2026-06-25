"""Backward-compatible re-export — implementation lives in massive.core.empirical_config."""

from massive.core.empirical_config import (  # noqa: F401
    EMPIRICAL_BASE_LOADED,
    MASSIVE_EMPIRICAL_MASTER,
    MASSIVE_RUNTIME_PARAMS,
    get_param,
    get_runtime_params,
)

__all__ = [
    "EMPIRICAL_BASE_LOADED",
    "MASSIVE_EMPIRICAL_MASTER",
    "MASSIVE_RUNTIME_PARAMS",
    "get_param",
    "get_runtime_params",
]
