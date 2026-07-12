"""@deprecated — re-export only. Use massive.core.empirical_config directly."""

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
