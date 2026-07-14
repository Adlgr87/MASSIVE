"""PVU runner wiring: targets, walk-forward, JSON safety, RF/GBM baselines."""

from __future__ import annotations

import json

import numpy as np

from benchmarks.baselines import get_all_baselines, RandomForestBaseline, GradientBoostingBaseline
from benchmarks.runner import evaluate_case, _json_safe


def test_baselines_include_rf_and_gbm_when_sklearn_available():
    names = {b.name for b in get_all_baselines()}
    # sklearn is in requirements; expect both
    assert "random_forest" in names
    assert "gradient_boosting" in names
    y = np.linspace(0.1, 0.8, 12)
    rf = RandomForestBaseline(lags=3, n_estimators=10)
    pred = rf.predict(y, horizon=2)
    assert pred.shape == (2,)
    gb = GradientBoostingBaseline(lags=3, n_estimators=10)
    assert gb.predict(y, horizon=2).shape == (2,)


def test_json_safe_converts_nan():
    payload = {"a": float("nan"), "b": [1.0, float("inf")], "c": np.float64(np.nan)}
    clean = _json_safe(payload)
    assert clean["a"] is None
    assert clean["b"][1] is None
    assert clean["c"] is None
    # Must dump with allow_nan=False
    json.dumps(clean, allow_nan=False)


def test_evaluate_case_includes_target_and_walk_forward():
    case = {
        "name": "toy_case",
        "meta": {
            "cluster_id": "polarization_escalation",
            "scenario_type": "polarization_escalation",
            "network_type": "watts_strogatz",
        },
        "timeseries": {"P": list(np.linspace(0.2, 0.8, 14))},
    }
    rng = np.random.default_rng(0)
    result = evaluate_case(case, mode="offline", rng=rng)
    assert result["skipped"] is False
    assert result["target"]["name"] == "polarization_index"
    assert "walk_forward" in result
    assert isinstance(result["walk_forward"], dict)
    assert len(result["walk_forward"]) >= 1
    # at least one baseline fold
    any_folds = any(
        (v or {}).get("n_folds", 0) >= 1 for v in result["walk_forward"].values()
    )
    assert any_folds
