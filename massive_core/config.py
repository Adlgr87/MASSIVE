"""Configuration flags for opt-in MASSIVE scientific extensions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ScientificRuntimeConfig:
    """Feature flags controlling scientific integrations.

    Args:
        solver: Numerical solver name. ``legacy`` keeps existing engine paths.
        enable_stability_diagnostics: Whether engines should collect stability
            diagnostics when implemented by a caller.
        enable_data_assimilation: Whether data assimilation hooks are enabled.
        enable_scientific_report: Whether callers should produce reports.
    """

    solver: str = "legacy"
    enable_stability_diagnostics: bool = False
    enable_data_assimilation: bool = False
    enable_scientific_report: bool = False

    @classmethod
    def from_dict(cls, config: dict[str, Any] | None) -> "ScientificRuntimeConfig":
        """Build config from an optional dictionary.

        Args:
            config: Optional user configuration.

        Returns:
            Runtime config with safe defaults.
        """

        if config is None:
            return cls()
        return cls(
            solver=str(config.get("solver", "legacy")),
            enable_stability_diagnostics=bool(config.get("enable_stability_diagnostics", False)),
            enable_data_assimilation=bool(config.get("enable_data_assimilation", False)),
            enable_scientific_report=bool(config.get("enable_scientific_report", False)),
        )
