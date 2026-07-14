"""MutaLambda adapter — expose MASSIVE simulation as an optimizable target.

This is a thin, stable interface for external multi-objective optimizers
(MutaLambda-style). It does not pull MutaLambda as a hard dependency.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np

from forecast.targets import TargetDefinition, POLARIZATION_INDEX, resolve_target


@dataclass
class MassiveTargetManifest:
    """Manifest describing what MASSIVE exposes to an external optimizer."""

    name: str = "massive_social_dynamics"
    version: str = "1.0.0"
    targets: tuple[TargetDefinition, ...] = (POLARIZATION_INDEX,)
    decision_dim: int = 8
    bounds: tuple[tuple[float, float], ...] = tuple((-1.0, 1.0) for _ in range(8))

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "version": self.version,
            "targets": [t.to_dict() for t in self.targets],
            "decision_dim": self.decision_dim,
            "bounds": [list(b) for b in self.bounds],
        }


def evaluate_massive_vector(
    decision: np.ndarray,
    *,
    n_agents: int = 100,
    steps: int = 20,
    seed: int = 0,
    cluster_id: str | None = None,
) -> dict[str, float]:
    """
    Map a decision vector into a short MASSIVE multilayer run and return metrics.

    Decision layout (length >= 5 recommended):
      [0] mean initial opinion bias
      [1] coupling
      [2] layer_weight social (renormalized with 3,4)
      [3] layer_weight digital
      [4] layer_weight economic
    """
    from multilayer_engine import MultilayerEngine, COL_OPINION

    x = np.asarray(decision, dtype=float).ravel()
    if x.size < 1:
        raise ValueError("decision vector must be non-empty")

    opinion0 = float(np.clip(x[0] if x.size > 0 else 0.0, -1.0, 1.0))
    coupling = float(np.clip(abs(x[1]) if x.size > 1 else 0.3, 0.0, 1.0))
    w = np.array(
        [
            abs(x[2]) if x.size > 2 else 0.4,
            abs(x[3]) if x.size > 3 else 0.3,
            abs(x[4]) if x.size > 4 else 0.3,
        ],
        dtype=float,
    )
    if w.sum() <= 0:
        w = np.array([0.4, 0.3, 0.3])
    w = w / w.sum()

    engine = MultilayerEngine(
        N=int(n_agents),
        layer_weights=tuple(w),
        coupling=coupling,
        seed=int(seed),
    )
    engine.x[:, COL_OPINION] = opinion0
    engine.run(steps=int(steps))
    landscape = engine.get_landscape()

    target = resolve_target(cluster_id)
    metrics = {
        "opinion_mean": float(landscape["mean_opinion"]),
        "polarization_index": float(landscape["polarization"]),
        "mean_cooperation": float(landscape["mean_cooperation"]),
        "primary_target": target.name,
        "primary_value": float(
            landscape["polarization"]
            if target.name == "polarization_index"
            else landscape["mean_opinion"]
        ),
    }
    return metrics


def make_objective(
    *,
    n_agents: int = 100,
    steps: int = 20,
    seed: int = 0,
    cluster_id: str | None = "polarization_escalation",
    minimize: bool = True,
) -> Callable[[np.ndarray], float]:
    """Return a scalar objective for black-box optimizers."""

    def objective(decision: np.ndarray) -> float:
        m = evaluate_massive_vector(
            decision,
            n_agents=n_agents,
            steps=steps,
            seed=seed,
            cluster_id=cluster_id,
        )
        val = m["primary_value"]
        return float(val if minimize else -val)

    return objective
