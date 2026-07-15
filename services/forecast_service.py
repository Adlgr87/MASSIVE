"""Forecast service — baselines, walk-forward, and target metadata."""

from __future__ import annotations

from typing import Any, Optional, Sequence, Union

import numpy as np

from benchmarks.baselines import get_all_baselines
from benchmarks.walk_forward import walk_forward_scores
from forecast.targets import all_targets, resolve_target

ArrayLike = Union[Sequence[float], np.ndarray]


def list_targets() -> list[dict[str, Any]]:
    """Return all registered forecast target definitions as dicts."""
    return [t.to_dict() for t in all_targets()]


def target_for_case(
    cluster_id: Optional[str] = None,
    scenario_type: Optional[str] = None,
) -> dict[str, Any]:
    """Resolve the semantic target for a PVU cluster / scenario.

    Args:
        cluster_id: Explicit cluster id from case metadata.
        scenario_type: Fallback scenario label.

    Returns:
        TargetDefinition serialized as a dict.
    """
    return resolve_target(cluster_id, scenario_type).to_dict()


def baseline_forecast(
    series: ArrayLike,
    horizon: int,
    baseline_name: str = "naive",
) -> dict[str, Any]:
    """Run a named baseline forecaster on a 1-D series.

    Args:
        series: Historical observations.
        horizon: Forecast horizon.
        baseline_name: Registered baseline name (e.g. ``naive``, ``ar1``).

    Returns:
        Dict with prediction list, baseline name, and default target metadata.

    Raises:
        ValueError: If ``baseline_name`` is not registered.
    """
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
    series: ArrayLike,
    baseline_name: str = "naive",
    min_train: int = 4,
    horizon: int = 1,
) -> dict[str, Any]:
    """Evaluate a baseline with rolling-origin walk-forward scores.

    Args:
        series: Full observation series.
        baseline_name: Baseline to evaluate.
        min_train: Minimum training length per fold.
        horizon: Forecast horizon per fold.

    Returns:
        Dict with baseline name, MAE/RMSE scores, and target metadata.
    """
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
