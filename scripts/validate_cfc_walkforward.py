#!/usr/bin/env python3
"""Out-of-sample validation of the CfC residual corrector against baselines.

Audit finding C-03 was that the corrector's reported accuracy came from label
leakage: ``corrected = 0.5*sim + 0.5*actual`` interpolates toward the answer,
which halves the error *arithmetically* no matter how good the model is. That
is visible in the shipped ``validation.json``: all ten stress-test seeds report
``improvement_pct`` of exactly 50.000. The leakage was removed, which left the
real question open — is the model worth applying at all?

This script answers it the only way that counts: score the model on held-out
data and put it next to baselines a reviewer would reach for anyway. A
corrector that cannot beat "repeat the last residual" is not a corrector.

Baselines:
  zero         apply no correction (what shipping nothing does)
  train_mean   a constant, the training residual mean
  oracle_mean  the mean of the evaluation set itself (unbeatable constant,
               R^2 = 0 by construction — the bar any model must clear)
  persistence  last observed residual, the standard time-series yardstick

Usage:
    python scripts/validate_cfc_walkforward.py            # table to stdout
    python scripts/validate_cfc_walkforward.py --json     # machine-readable
    python scripts/validate_cfc_walkforward.py --write    # update the report
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "models" / "cfc_calibrated"
PREDICTIONS = MODEL_DIR / "predictions.npz"
CONFIG = MODEL_DIR / "config.json"
REPORT = ROOT / "reports" / "cfc_validation.json"


@dataclass
class Score:
    strategy: str
    rmse: float
    mae: float
    r2: float
    beats_no_correction: bool
    note: str = ""


def _score(name: str, yhat: np.ndarray, y: np.ndarray, zero_rmse: float, note: str = "") -> Score:
    err = yhat - y
    rmse = float(np.sqrt(np.mean(err**2)))
    mae = float(np.mean(np.abs(err)))
    ss_res = float(np.sum(err**2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    # R^2 against the evaluation set's own variance: "did we explain the
    # variation", not merely "are we close on average".
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0 else float("nan")
    return Score(name, rmse, mae, r2, rmse < zero_rmse, note)


def evaluate() -> dict:
    """Score the shipped model and the baselines on the held-out split."""
    if not PREDICTIONS.exists():
        raise FileNotFoundError(
            f"{PREDICTIONS} not found — it holds the held-out predictions "
            "produced during training and is required for validation"
        )

    data = np.load(PREDICTIONS)
    predicted = np.asarray(data["predicted"], dtype=np.float64)
    actual = np.asarray(data["actual"], dtype=np.float64)

    train_mean = float("nan")
    if CONFIG.exists():
        cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
        train_mean = float(cfg.get("residual_stats_reference", {}).get("mean", float("nan")))

    zero_rmse = float(np.sqrt(np.mean(actual**2)))

    scores = [
        _score("cfc_model", predicted, actual, zero_rmse, "the shipped corrector"),
        _score("zero", np.zeros_like(actual), actual, zero_rmse, "apply no correction at all"),
        _score(
            "train_mean",
            np.full_like(actual, train_mean),
            actual,
            zero_rmse,
            "a single constant from training",
        ),
        _score(
            "oracle_mean",
            np.full_like(actual, actual.mean()),
            actual,
            zero_rmse,
            "best possible constant; R^2 = 0 by construction",
        ),
        # Walk-forward: at step t only residuals up to t-1 are observable.
        _score(
            "persistence",
            np.concatenate([[actual[0]], actual[:-1]]),
            actual,
            zero_rmse,
            "repeat the last observed residual",
        ),
    ]

    model = next(s for s in scores if s.strategy == "cfc_model")
    rivals = [s for s in scores if s.strategy not in {"cfc_model", "zero"}]
    better = [s.strategy for s in rivals if s.rmse < model.rmse]

    return {
        "n_eval_points": int(actual.size),
        "actual_residual": {
            "mean": float(actual.mean()),
            "std": float(actual.std()),
            "min": float(actual.min()),
            "max": float(actual.max()),
        },
        "model_prediction": {
            "mean": float(predicted.mean()),
            "std": float(predicted.std()),
            "min": float(predicted.min()),
            "max": float(predicted.max()),
        },
        "scores": [asdict(s) for s in scores],
        "model_beats_no_correction": model.beats_no_correction,
        "baselines_beating_the_model": better,
        "verdict": _verdict(model, better),
    }


def _verdict(model: Score, better: list[str]) -> str:
    if not model.beats_no_correction:
        return (
            "REJECT — the model is worse than applying no correction at all. "
            "It must not be enabled."
        )
    if better:
        return (
            f"NOT FIT FOR PURPOSE — the model reduces error versus doing nothing "
            f"(RMSE {model.rmse:.5f}), but is beaten out-of-sample by: "
            f"{', '.join(better)}. A trained neural ODE that loses to a trivial "
            f"baseline should not be presented as a calibrated corrector."
        )
    return f"ACCEPT — the model beats every baseline tested (RMSE {model.rmse:.5f})."


def _print_table(result: dict) -> None:
    a, p = result["actual_residual"], result["model_prediction"]
    print(f"Out-of-sample evaluation — n = {result['n_eval_points']}\n")
    print(
        f"  actual residual   mean={a['mean']:+.5f}  std={a['std']:.5f}  "
        f"range=[{a['min']:+.4f}, {a['max']:+.4f}]"
    )
    print(
        f"  model prediction  mean={p['mean']:+.5f}  std={p['std']:.5f}  "
        f"range=[{p['min']:+.4f}, {p['max']:+.4f}]"
    )
    if p["std"] < a["std"] / 2:
        print("  -> the model barely varies: it is behaving like a biased constant.\n")
    else:
        print()

    print(f"  {'strategy':<14}{'RMSE':>10}{'MAE':>10}{'R^2':>10}   note")
    print(f"  {'-' * 14}{'-' * 10:>10}{'-' * 10:>10}{'-' * 10:>10}   {'-' * 40}")
    for s in sorted(result["scores"], key=lambda s: s["rmse"]):
        print(
            f"  {s['strategy']:<14}{s['rmse']:>10.5f}{s['mae']:>10.5f}"
            f"{s['r2']:>10.3f}   {s['note']}"
        )
    print(f"\n  VERDICT: {result['verdict']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a table")
    parser.add_argument("--write", action="store_true", help=f"also write {REPORT}")
    args = parser.parse_args()

    result = evaluate()

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        _print_table(result)

    if args.write:
        REPORT.parent.mkdir(parents=True, exist_ok=True)
        REPORT.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        print(f"\n  wrote {REPORT.relative_to(ROOT)}")

    # Exit non-zero when the model is actively harmful; "beaten by a baseline"
    # is reported but does not fail the run, so this stays usable in CI as a
    # regression guard rather than a permanent red.
    return 0 if result["model_beats_no_correction"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
