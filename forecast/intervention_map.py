"""Mapping helpers from intervention schedules to simulator parameter overrides."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

import numpy as np

from schemas import Intervention


def _clip_unit(value: Any) -> float:
    return float(np.clip(float(value), 0.0, 1.0))


def _clip_rate(value: Any, lower: float = 0.0, upper: float = 1.0) -> float:
    return float(np.clip(float(value), lower, upper))


def _temporal_step_multiplier(model_name: str) -> float:
    model = model_name.lower().strip()
    if model in {"contagio_competitivo", "sir"}:
        return 0.5
    if model in {"memoria", "policy_adoption", "cultural_shift"}:
        return 1.25
    return 1.0


def apply_intervention(base_config: dict, intervention: Intervention) -> dict:
    """Applies a single intervention over a base config without mutation."""
    merged = deepcopy(base_config)
    params = dict(intervention.parameters or {})
    model_name = intervention.model_name.lower().strip()

    if "propaganda" in params:
        merged["propaganda"] = _clip_unit(params["propaganda"])
    if "epsilon" in params:
        merged["hk_epsilon"] = _clip_rate(params["epsilon"], 0.1, 0.8)
    if "competencia" in params:
        merged["competencia_peso"] = _clip_unit(params["competencia"])
    if "tasa" in params:
        merged["homofilia_tasa"] = _clip_rate(params["tasa"], 0.0, 0.2)
    if "ruido_base" in params:
        merged["ruido_base"] = _clip_rate(params["ruido_base"], 0.0, 0.5)
    if "ruido_desconfianza" in params:
        merged["ruido_desconfianza"] = _clip_rate(params["ruido_desconfianza"], 0.0, 0.5)

    if "step_duration_days" in merged:
        base_days = max(1, int(merged["step_duration_days"]))
        merged["step_duration_days"] = max(
            1,
            int(round(base_days * _temporal_step_multiplier(model_name))),
        )

    return merged
