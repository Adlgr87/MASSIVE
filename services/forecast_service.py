"""Forecast service — baselines, walk-forward, and target metadata."""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from benchmarks.baselines import get_all_baselines
from benchmarks.walk_forward import walk_forward_scores
from forecast.targets import resolve_target, all_targets


def list_targets() -> list[dict[str, Any]]:
    return [t.to_dict() for t in all_targets()]


def target_for_case(
    cluster_id: Optional[str] = None,
    scenario_type: Optional[str] = None,
) -> dict[str, Any]:
    return resolve_target(cluster_id, scenario_type).to_dict()


def baseline_forecast(
    series: list[float] | np.ndarray,
    horizon: int,
    baseline_name: str = "naive",
) -> dict[str, Any]:
    """Run a named baseline on a series."""
    y = np.asarray(series, dtype=float).ravel()
    baselines = {b.name: b for b in get_all_baselines()}
    if baseline_name not in baselines:
        raise ValueError(
            f"Unknown baseline '{baseline_name}'. Available: {sorted(baselines)}"
        )
    pred = baselines[baseline_name].predict(y, int(horizon))
    return {
        "baseline": baseline_name,
        "horizon": int(horizon),
        "prediction": pred.tolist(),
        "target": resolve_target(None).to_dict(),
    }


def walk_forward_evaluate(
    series: list[float] | np.ndarray,
    baseline_name: str = "naive",
    min_train: int = 4,
    horizon: int = 1,
) -> dict[str, Any]:
    """Walk-forward MAE/RMSE for a baseline."""
    y = np.asarray(series, dtype=float).ravel()
    baselines = {b.name: b for b in get_all_baselines()}
    if baseline_name not in baselines:
        raise ValueError(f"Unknown baseline '{baseline_name}'")
    bl = baselines[baseline_name]
    scores = walk_forward_scores(
        y,
        predict_fn=lambda tr, h: bl.predict(tr, h),
        min_train=min_train,
        horizon=horizon,
    )
    return {
        "baseline": baseline_name,
        "scores": scores,
        "target": resolve_target(None).to_dict(),
    }
