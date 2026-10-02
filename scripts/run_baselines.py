#!/usr/bin/env python3
"""G0-quater: Run baselines on all 12 historical cases.

Establishes the baseline that any calibration must beat. Uses walk-forward
(rolling-origin) validation so each case contributes multiple folds without
leakage.

Baselines:
  persistence: last observed value (random walk / naive)
  mean_reverting: AR(1) fitted via OLS (Ornstein-Uhlenbeck discretization)
  train_mean: constant = mean of training window
  linear: OLS linear trend extrapolation

Usage:
    python scripts/run_baselines.py                     # writes reports/baselines_12cases.json
    python scripts/run_baselines.py --cases 3           # only first 3 cases (quick test)
"""
from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

from benchmarks.baselines import (
    AR1Baseline,
    MovingAverageBaseline,
    NaiveBaseline,
    SeasonalNaiveBaseline,
)
from benchmarks.metrics import directional_accuracy, mae, rmse
from benchmarks.walk_forward import rolling_origin_splits
from benchmarks.io import load_cases

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports" / "baselines_12cases.json"
CASES_DIR = ROOT / "datasets" / "real_cases"


@dataclass
class BaselineResult:
    name: str
    mae: float
    rmse: float
    directional_accuracy: float
    n_folds: int
    per_fold_mae: list[float]
    per_fold_rmse: list[float]


@dataclass
class CaseBaseline:
    case_id: str
    target_variable: str
    target_units: str
    n_observations: int
    baselines: list[BaselineResult]
    best_baseline: str
    best_mae: float


def _linear_predict(train: np.ndarray, horizon: int) -> np.ndarray:
    """OLS linear trend extrapolation."""
    y = np.asarray(train, dtype=float).ravel()
    x = np.arange(len(y), dtype=float)
    if len(y) < 2:
        return np.full(horizon, float(y[-1]))
    X = np.column_stack([np.ones(len(x)), x])
    coeffs, *_ = np.linalg.lstsq(X, y, rcond=None)
    future_x = np.arange(len(y), len(y) + horizon, dtype=float)
    return coeffs[0] + coeffs[1] * future_x


def _train_mean_predict(train: np.ndarray, horizon: int) -> np.ndarray:
    """Constant prediction = mean of training window."""
    return np.full(horizon, float(np.mean(train)))


def _eval_case(case: dict) -> CaseBaseline:
    """Run all baselines on a single case with walk-forward validation."""
    y = case["timeseries"]["P"]
    meta = case["meta"]

    baseline_fns = {
        "persistence": NaiveBaseline().predict,
        "mean_reverting": AR1Baseline().predict,
        "train_mean": _train_mean_predict,
        "linear": _linear_predict,
        "seasonal_naive": SeasonalNaiveBaseline(season=4).predict,
        "moving_average": MovingAverageBaseline(window=4).predict,
    }

    results: list[BaselineResult] = []
    for name, predict_fn in baseline_fns.items():
        fold_maes: list[float] = []
        fold_rmses: list[float] = []
        fold_das: list[float] = []

        for train, test in rolling_origin_splits(y, min_train=3, horizon=1):
            pred = np.asarray(predict_fn(train, 1), dtype=float).ravel()
            if pred.shape != test.shape:
                pred = pred[: len(test)]
            fold_maes.append(float(mae(test, pred)))
            fold_rmses.append(float(rmse(test, pred)))
            # directional_accuracy is NaN for single-point test sets (horizon=1);
            # accumulate only non-NaN values and guard the aggregate
            da = directional_accuracy(test, pred)
            if not np.isnan(da):
                fold_das.append(float(da))

        if not fold_maes:
            continue

        results.append(BaselineResult(
            name=name,
            mae=float(np.mean(fold_maes)),
            rmse=float(np.mean(fold_rmses)),
            directional_accuracy=float(np.mean(fold_das)) if fold_das else 0.0,
            n_folds=len(fold_maes),
            per_fold_mae=fold_maes,
            per_fold_rmse=fold_rmses,
        ))

    # Sort by MAE (lower is better)
    results.sort(key=lambda r: r.mae)
    best = results[0] if results else BaselineResult("", 0.0, 0.0, 0.0, 0, [], [])

    return CaseBaseline(
        case_id=case["name"],
        target_variable=meta.get("target_variable", "unknown"),
        target_units=meta.get("target_units", "unknown"),
        n_observations=len(y),
        baselines=results,
        best_baseline=best.name,
        best_mae=best.mae,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=int, default=0,
                        help="limit to first N cases (0 = all)")
    parser.add_argument("--out", type=str, default=str(OUTPUT))
    args = parser.parse_args()

    cases = load_cases(CASES_DIR)
    if args.cases > 0:
        cases = cases[: args.cases]

    print(f"Running baselines on {len(cases)} cases...")
    case_results: list[CaseBaseline] = []
    for case in cases:
        result = _eval_case(case)
        case_results.append(result)
        print(f"  {result.case_id}: best={result.best_baseline} "
              f"(MAE={result.best_mae:.4f})")

    # Aggregate summary
    all_baselines = {}
    for cr in case_results:
        for b in cr.baselines:
            if b.name not in all_baselines:
                all_baselines[b.name] = []
            all_baselines[b.name].append(b)

    aggregated = {}
    for name, results_list in all_baselines.items():
        mae_vals = [r.mae for r in results_list]
        rmse_vals = [r.rmse for r in results_list]
        da_vals = [r.directional_accuracy for r in results_list]
        aggregated[name] = {
            "mean_mae": float(np.mean(mae_vals)),
            "std_mae": float(np.std(mae_vals)),
            "mean_rmse": float(np.mean(rmse_vals)),
            "mean_directional_accuracy": float(np.mean(da_vals)) if da_vals else 0.0,
            "n_cases": len(results_list),
        }

    report = {
        "description": "Baseline forecasters evaluated via walk-forward (rolling-origin) validation on all 12 historical cases.",
        "method": "rolling_origin_splits(min_train=3, horizon=1)",
        "baselines": sorted(aggregated.keys()),
        "aggregated": aggregated,
        "cases": [asdict(cr) for cr in case_results],
        "best_overall_baseline": min(
            aggregated.keys(),
            key=lambda k: aggregated[k]["mean_mae"],
        ),
        "best_overall_mae": min(
            aggregated[k]["mean_mae"] for k in aggregated
        ),
        "total_observations": sum(cr.n_observations for cr in case_results),
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nReport written to: {out_path}")
    print(f"Best overall baseline: {report['best_overall_baseline']} "
          f"(mean MAE = {report['best_overall_mae']:.4f})")


if __name__ == "__main__":
    main()
