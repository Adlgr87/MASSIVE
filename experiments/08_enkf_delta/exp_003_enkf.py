#!/usr/bin/env python3
"""
EXP-003: EnKF Delta Measurement

Measure the improvement (Δ) from applying Ensemble Kalman Filter (post-processing)
on MASSIVE real forecasts, using sparse observations from the real-world series.

Protocol (per case):
- Load polarization series P[0..N-1]
- Split train/test = 70/30 (n_train, horizon)
- Run MASSIVE real engine (heurístico, no LLM) to produce a full history of dicts
  of length n_total = n_train + horizon
- Fit linear map a,b on train_opinions -> train_P
- Pre-forecast (baseline): P_pred_pre = clip(a * opinions_test + b)
- Build sparse observations: every K steps on the test window, map observed
  polarization to the opinion space via inverse (P - b)/a (clipped)
- Run EnKF over the whole trajectory with these observations
- Post-forecast: P_pred_post = clip(a * opinion_assimilated_test + b)
- Compute metrics vs ground truth P_test (MAE, RMSE, directional accuracy with threshold)

Outputs
- {out}/metrics_pre.json     # per-case pre-assim metrics
- {out}/metrics_post.json    # per-case post-assim metrics
- {out}/delta.json           # per-case deltas (pre - post)
- {out}/report.md            # human-readable summary

Reproducibility
- Controlled by --seed and PYTHONHASHSEED from the shell

"""
from __future__ import annotations

import argparse
import csv
import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np

from massive_core.data_assimilation.workflow import assimilate_history_observations

# Import MASSIVE real integration
from benchmarks.massive_real import _fit_linear, _seed_everything
from simulator import simular


@dataclass
class CaseMeta:
    name: str
    cultural_profile: str = "mixed"
    network_type: str = "watts_strogatz"
    cluster_id: str | None = None


@dataclass
class CaseData:
    name: str
    P: List[float]
    meta: CaseMeta


def read_case(case_dir: Path) -> CaseData:
    name = case_dir.name
    # Load meta.json if present
    meta_path = case_dir / "meta.json"
    meta_obj: Dict[str, Any] = {}
    if meta_path.exists():
        meta_obj = json.loads(meta_path.read_text(encoding="utf-8"))
    meta = CaseMeta(
        name=name,
        cultural_profile=meta_obj.get("cultural_profile", "mixed"),
        network_type=meta_obj.get("network_type", "watts_strogatz"),
        cluster_id=meta_obj.get("cluster_id"),
    )
    # Load timeseries.csv (find "P" column, case-insensitive)
    ts_path = case_dir / "timeseries.csv"
    if not ts_path.exists():
        raise FileNotFoundError(f"Missing timeseries.csv in {case_dir}")
    with ts_path.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader)
        cols = [h.strip() for h in header]
        try:
            p_idx = next(i for i, h in enumerate(cols) if h.lower() == "p")
        except StopIteration:
            raise ValueError(f"timeseries.csv must contain column 'P' in {case_dir}")
        P = []
        for row in reader:
            if not row:
                continue
            try:
                val = float(row[p_idx])
                P.append(val)
            except Exception:
                continue
    if len(P) < 6:
        raise ValueError(f"Series too short for case {name}: {len(P)}")
    return CaseData(name=name, P=P, meta=meta)


def directional_accuracy(y_true: np.ndarray, y_pred: np.ndarray, threshold: float = 0.02) -> float:
    """Directional accuracy with deadband threshold to avoid flat noise.

    Returns fraction of steps in which sign(Δy) matches, ignoring |Δ| <= threshold.
    """
    if len(y_true) != len(y_pred):
        raise ValueError("directional_accuracy requires same-length arrays")
    if len(y_true) < 2:
        return 0.0
    t = y_true
    p = y_pred
    d_t = np.diff(t)
    d_p = np.diff(p)
    mask = (np.abs(d_t) > threshold) | (np.abs(d_p) > threshold)
    if not np.any(mask):
        return 0.0
    return float(np.mean(np.sign(d_t[mask]) == np.sign(d_p[mask])))


def mae(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.mean(np.abs(a - b)))


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    return float(math.sqrt(np.mean((a - b) ** 2)))


def run_case(case: CaseData, *, seed: int, obs_interval: int, sigma_obs: float, n_ensemble: int) -> Dict[str, Any]:
    _seed_everything(seed)

    series = np.asarray(case.P, dtype=float)
    n = len(series)
    n_train = max(int(0.7 * n), 2)
    horizon = n - n_train
    train = series[:n_train]
    test = series[n_train:]

    # Build initial state from train (mirror massive_real_forecast_with_calibration)
    # Local mapping of polarization->initial group opinions/opinion
    last_pol = float(np.clip(train[-1], 0.0, 1.0))
    mean_pol = float(np.mean(train))
    var_pol = float(np.var(train)) if len(train) > 1 else 0.0
    gap = 0.5 * last_pol
    op_a = float(np.clip(0.5 + gap, 0.0, 1.0))
    op_b = float(np.clip(0.5 - gap, 0.0, 1.0))

    estado = {
        "opinion": last_pol,
        "propaganda": float(np.clip(0.5 + (last_pol - 0.5) * 0.6, 0.0, 1.0)),
        "confianza": float(np.clip(0.6 - 0.3 * var_pol, 0.0, 1.0)),
        "opinion_grupo_a": op_a,
        "opinion_grupo_b": op_b,
        "pertenencia_grupo": float(np.clip(0.5 + 0.3 * (mean_pol - 0.5), 0.0, 1.0)),
        "red_type": case.meta.network_type,
        "cultural_profile": case.meta.cultural_profile,
    }

    # Simulate full window (train + test)
    n_total = n
    history = simular(estado, pasos=n_total, cada_n_pasos=1, verbose=False)

    # Extract opinions and fit mapping on train
    opinions = np.asarray([float(h.get("opinion", last_pol)) for h in history], dtype=float)
    train_opinions = opinions[:n_train]
    a, b = _fit_linear(train_opinions.tolist(), train.tolist())
    if not np.isfinite(a) or not np.isfinite(b):
        a, b = 1.0, 0.0

    # Pre-forecast (baseline): mapped test opinions
    pre_pred = np.clip(a * opinions[n_train:n_total] + b, 0.0, 1.0)

    # Build sparse observations on test window every obs_interval
    obs: Dict[int, np.ndarray] = {}
    for i in range(0, horizon, obs_interval):
        step = n_train + i
        # Map polarization observation to "opinion-equivalent"
        if abs(a) < 1e-8:
            obs_op = opinions[step]  # fallback
        else:
            obs_op = float(np.clip((series[step] - b) / a, 0.0, 1.0))
        obs[step] = np.array([obs_op], dtype=float)

    # Assimilate
    assimilation = assimilate_history_observations(
        history,
        observations=obs,
        fields=("opinion",),
        observation_variance=float(sigma_obs ** 2),
        n_ensemble=int(n_ensemble),
        ensemble_spread=0.01,
        seed=seed,
    )

    post_opinions = assimilation.assimilated_mean[:, 0]
    post_pred = np.clip(a * post_opinions[n_train:n_total] + b, 0.0, 1.0)

    # Metrics
    y_true = test
    pre_mae = mae(y_true, pre_pred)
    post_mae = mae(y_true, post_pred)
    pre_rmse = rmse(y_true, pre_pred)
    post_rmse = rmse(y_true, post_pred)
    pre_dir = directional_accuracy(y_true, pre_pred, threshold=0.02)
    post_dir = directional_accuracy(y_true, post_pred, threshold=0.02)

    return {
        "case": case.name,
        "n_total": int(n),
        "n_train": int(n_train),
        "horizon": int(horizon),
        "meta": asdict(case.meta),
        "enkf": {
            "n_ensemble": int(n_ensemble),
            "sigma_obs": float(sigma_obs),
            "obs_interval": int(obs_interval),
        },
        "metrics_pre": {
            "mae": pre_mae,
            "rmse": pre_rmse,
            "directional_accuracy": pre_dir,
        },
        "metrics_post": {
            "mae": post_mae,
            "rmse": post_rmse,
            "directional_accuracy": post_dir,
        },
        "delta": {
            "mae": float(pre_mae - post_mae),
            "rmse": float(pre_rmse - post_rmse),
            "directional_accuracy": float(post_dir - pre_dir),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="EXP-003: EnKF delta on MASSIVE real forecasts")
    ap.add_argument("--cases", required=True, help="Path to datasets/real_cases root")
    ap.add_argument("--cases-filter", default="", help="Comma-separated subset of case directory names")
    ap.add_argument("--out", required=True, help="Output directory for metrics and report")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--n-ensemble", type=int, default=32)
    ap.add_argument("--sigma-obs", type=float, default=0.05)
    ap.add_argument("--interval", type=int, default=5, help="Observation interval on test window (steps)")
    args = ap.parse_args()

    _seed_everything(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    root = Path(args.cases)
    names = [p.name for p in root.iterdir() if p.is_dir()]
    if args.cases_filter:
        allow = set(n.strip() for n in args.cases_filter.split(",") if n.strip())
        names = [n for n in names if n in allow]
    names = sorted(names)

    results: List[Dict[str, Any]] = []
    for name in names:
        try:
            case = read_case(root / name)
            res = run_case(case, seed=args.seed, obs_interval=args.interval, sigma_obs=args.sigma_obs, n_ensemble=args.n_ensemble)
            results.append(res)
            print(f"[OK] {name}: ΔMAE={res['delta']['mae']:+.4f}, Δdir={res['delta']['directional_accuracy']:+.3f}")
        except Exception as e:
            print(f"[FAIL] {name}: {e}")

    # Save metrics
    pre = [{"case": r["case"], **r["metrics_pre"]} for r in results]
    post = [{"case": r["case"], **r["metrics_post"]} for r in results]
    delta = [{"case": r["case"], **r["delta"]} for r in results]

    (out / "metrics_pre.json").write_text(json.dumps(pre, indent=2), encoding="utf-8")
    (out / "metrics_post.json").write_text(json.dumps(post, indent=2), encoding="utf-8")
    (out / "delta.json").write_text(json.dumps(delta, indent=2), encoding="utf-8")

    # Build report
    wins = sum(1 for r in results if r["delta"]["mae"] > 0)
    report = [
        f"# EXP-003: EnKF Delta (seed={args.seed}, n_ensemble={args.n_ensemble}, "+
        f"sigma_obs={args.sigma_obs}, interval={args.interval})\n",
        f"Cases: {len(results)}\n",
        "\n## Summary\n",
        f"Wins (ΔMAE>0): {wins}/{len(results)}\n\n",
        "| Case | ΔMAE | ΔRMSE | ΔDirAcc |\n|---|---:|---:|---:|\n",
    ]
    for r in results:
        report.append(f"| {r['case']} | {r['delta']['mae']:+.4f} | {r['delta']['rmse']:+.4f} | {r['delta']['directional_accuracy']:+.3f} |\n")
    (out / "report.md").write_text("".join(report), encoding="utf-8")

    print(f"Saved metrics to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
