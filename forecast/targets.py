"""Forecast target definitions for MASSIVE validation.

Separates semantic targets so opinion_mean is not mixed with
polarization_index / protest_participation without metadata.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any


@dataclass(frozen=True)
class TargetDefinition:
    """Unit-aware forecast target metadata."""

    name: str
    range: tuple[float, float]
    unit: str
    semantics: str
    source: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["range"] = list(self.range)
        return d


OPINION_MEAN = TargetDefinition(
    name="opinion_mean",
    range=(-1.0, 1.0),
    unit="bipolar_score",
    semantics="Mean agent opinion on the primary bipolar axis.",
    source="simulator_state.opinion",
)

POLARIZATION_INDEX = TargetDefinition(
    name="polarization_index",
    range=(0.0, 1.0),
    unit="index",
    semantics="Mean absolute deviation from neutrality (polarization).",
    source="mean(|opinion|)",
)

PROTEST_PARTICIPATION = TargetDefinition(
    name="protest_participation",
    range=(0.0, 1.0),
    unit="rate",
    semantics="Fraction of population participating in protest (SIR-like cases).",
    source="case_timeseries.P",
)

TURNING_POINT = TargetDefinition(
    name="turning_point",
    range=(0.0, 1.0),
    unit="indicator",
    semantics="Binary/soft indicator of regime inflection in the series.",
    source="derived_from_series",
)

REGIME_TRANSITION = TargetDefinition(
    name="regime_transition",
    range=(0.0, 1.0),
    unit="probability",
    semantics="Probability of transitioning between social regimes.",
    source="regime_model",
)

# Map PVU scenario_type / cluster_id → primary validation target
CLUSTER_TARGET_MAP: dict[str, TargetDefinition] = {
    "polarization_spike": POLARIZATION_INDEX,
    "polarization_escalation": POLARIZATION_INDEX,
    "contagion_sir": PROTEST_PARTICIPATION,
    "consensus_cascade": OPINION_MEAN,
}


def resolve_target(cluster_id: str | None, scenario_type: str | None = None) -> TargetDefinition:
    """Resolve the semantic target for a validation case."""
    key = cluster_id or scenario_type or ""
    return CLUSTER_TARGET_MAP.get(key, POLARIZATION_INDEX)


def all_targets() -> list[TargetDefinition]:
    return [
        OPINION_MEAN,
        POLARIZATION_INDEX,
        PROTEST_PARTICIPATION,
        TURNING_POINT,
        REGIME_TRANSITION,
    ]
