"""PVU-BS benchmark runner — CLI entry point.

Usage (offline mode, no LLM required):
    python -m benchmarks.runner --cases datasets/pvu_cases --offline \\
           --out reports/validation/ci --seed 42

Usage (LLM mode, requires OPENROUTER_API_KEY or equivalent):
    python -m benchmarks.runner --cases datasets/pvu_cases --llm \\
           --out reports/validation/ci

Design principles
-----------------
- Deterministic: controlled by --seed / PYTHONHASHSEED.
- Fast: default CI run completes in seconds (no network calls in offline mode).
- No heavy new dependencies: uses stdlib + numpy + scipy (already required).
- LLM mode gracefully skips and warns when secrets are absent.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from benchmarks.baselines import get_all_baselines
from benchmarks.io import load_cases
from benchmarks.metrics import (
    compute_all_metrics,
    dm_test,
    holm_bonferroni,
)
from benchmarks.turning_points import detect as detect_turning_points
from benchmarks.turning_points import score_turning_points

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Train / test split ratio ──────────────────────────────────────────────────
TRAIN_RATIO = 0.7  # 70 % train, 30 % test (no val in offline mode)


# ── MASSIVE offline forecast (deterministic proxy) ───────────────────────

def _massive_offline_forecast(
    train: np.ndarray,
    horizon: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Deterministic proxy for MASSIVE in offline (no-LLM) mode.

    Combines AR(1) trend with a damped EWS-inspired noise term — mimicking
    the engine's regime-awareness without requiring a live LLM call.

    This is *not* the real MASSIVE prediction; it exists solely so CI
    can measure the benchmark pipeline end-to-end without API keys.
    """
    from benchmarks.baselines import AR1Baseline

    ar1 = AR1Baseline()
    ar1.fit(train)

    # Damped noise: std decays over forecast horizon (captures CSD-inspired
    # "slowing down" near the mean reversion point).
    diff_std = float(np.std(np.diff(train))) if len(train) > 1 else 0.01
    decay = np.exp(-np.arange(horizon) / max(horizon, 1))
    noise = rng.normal(0, diff_std * decay)

    preds = np.empty(horizon)
    last = float(train[-1])
    for i in range(horizon):
        last = ar1.phi0 + ar1.phi1 * last + noise[i]
        preds[i] = last
    return preds


def _massive_llm_forecast(
    train: np.ndarray,
    horizon: int,
    case: dict,
) -> np.ndarray | None:
    """Attempt a real MASSIVE LLM-backed forecast.

    Returns None (with a warning) if the required environment variables are
    absent, so the run degrades gracefully instead of crashing CI.
    """
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        log.warning(
            "LLM mode requested but no API key found "
            "(OPENROUTER_API_KEY / OPENAI_API_KEY). "
            "Skipping LLM forecast for case '%s'.",
            case.get("name", "?"),
        )
        return None

    # Lazy import so offline mode has zero overhead.
    try:
        from simulator import simular  # type: ignore[import]
    except ImportError:
        log.warning("Cannot import simulator — skipping LLM forecast.")
        return None

    # Build a minimal initial state from the last training observation.
    estado = {
        "opinion": float(train[-1]),
        "propaganda": 0.0,
        "red_type": case.get("meta", {}).get("network_type", "watts_strogatz"),
    }
    try:
        historial = simular(estado, pasos=horizon, verbose=False)
        return np.array([h["opinion"] for h in historial[-horizon:]])
    except Exception as exc:  # noqa: BLE001
        log.warning("LLM forecast failed for '%s': %s", case.get("name", "?"), exc)
        return None


# ── Per-case evaluation ───────────────────────────────────────────────────────

def evaluate_case(
    case: dict,
    mode: str,
    rng: np.random.Generator,
) -> dict:
    """Evaluate all baselines (and optionally MASSIVE) on one case.

    Returns a result dict ready for JSON serialisation.
    """
    P = case["timeseries"]["P"]
    n = len(P)
    split = max(2, int(n * TRAIN_RATIO))
    train, test = P[:split], P[split:]
    horizon = len(test)

    if horizon < 1:
        log.warning("Case '%s': test split is empty — skipping.", case["name"])
        return {"case": case["name"], "skipped": True, "reason": "empty test split"}

    # ── Baselines ────────────────────────────────────────────────────────────
    baselines = get_all_baselines()
    baseline_results: dict[str, dict] = {}
    baseline_preds: dict[str, np.ndarray] = {}

    for bl in baselines:
        pred = bl.predict(train, horizon)
        baseline_preds[bl.name] = pred
        baseline_results[bl.name] = compute_all_metrics(test, pred)

    # ── MASSIVE forecast ──────────────────────────────────────────────────
    if mode == "llm":
        bs_pred = _massive_llm_forecast(train, horizon, case)
    else:
        bs_pred = _massive_offline_forecast(train, horizon, rng)

    bs_metrics: dict = {}
    dm_results: dict = {}
    tp_result: dict = {}

    if bs_pred is not None:
        bs_metrics = compute_all_metrics(test, bs_pred)

        # Diebold–Mariano vs each baseline + Holm–Bonferroni correction
        p_values_raw = []
        bl_names_for_dm = []
        for bl in baselines:
            _, pv = dm_test(test, bs_pred, baseline_preds[bl.name])
            p_values_raw.append(pv)
            bl_names_for_dm.append(bl.name)

        p_adj = holm_bonferroni(p_values_raw)
        for i, bl_name in enumerate(bl_names_for_dm):
            dm_results[bl_name] = {
                "p_raw": p_values_raw[i],
                "p_adj_holm": p_adj[i],
                "significant": (p_adj[i] is not None and p_adj[i] < 0.05),
            }

        # Turning-point scoring
        tp_true = detect_turning_points(test)
        tp_pred = detect_turning_points(bs_pred)
        tp_result = score_turning_points(tp_true, tp_pred, n=len(test))

    return {
        "case": case["name"],
        "cluster_id": case.get("meta", {}).get("cluster_id"),
        "n_total": n,
        "n_train": split,
        "n_test": horizon,
        "baselines": baseline_results,
        "massive": bs_metrics,
        "dm_tests": dm_results,
        "turning_points": tp_result,
        "skipped": False,
    }


# ── Report generation ─────────────────────────────────────────────────────────

def _format_float(v) -> str:
    if v is None or (isinstance(v, float) and (v != v)):  # nan check
        return "N/A"
    return f"{v:.4f}"


def generate_report(results: list[dict], mode: str, seed: int) -> str:
    """Build a Markdown summary report from the list of case results."""
    run_ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# PVU-BS Benchmark Report",
        "",
        f"**Run timestamp:** {run_ts}  ",
        f"**Mode:** `{mode}`  ",
        f"**Seed:** `{seed}`  ",
        f"**Cases evaluated:** {len(results)}  ",
        "",
        "> ⚠️ **Sample-case disclaimer:** results from `sample_case_*` are",
        "> synthetic and do NOT constitute PVU real-validation evidence.",
        "> Real validation requires N ≥ 10 independent cases",
        "> (see `docs/validation/PVU_MASSIVE_EN.md`).",
        "",
        "---",
        "",
    ]

    for r in results:
        lines.append(f"## Case: `{r['case']}`")
        if r.get("skipped"):
            lines += [f"_Skipped: {r.get('reason', 'unknown')}_", ""]
            continue

        lines += [
            f"- **N total / train / test:** {r['n_total']} / {r['n_train']} / {r['n_test']}",
            f"- **Cluster ID:** `{r.get('cluster_id') or 'n/a'}`",
            "",
            "### Baseline metrics (test split)",
            "",
            "| Baseline | MAE | RMSE | MAPE (%) | Dir. Acc. |",
            "|----------|-----|------|----------|-----------|",
        ]
        for bl_name, m in r.get("baselines", {}).items():
            lines.append(
                f"| {bl_name} "
                f"| {_format_float(m.get('mae'))} "
                f"| {_format_float(m.get('rmse'))} "
                f"| {_format_float(m.get('mape'))} "
                f"| {_format_float(m.get('directional_accuracy'))} |"
            )

        bs = r.get("massive", {})
        if bs:
            lines += [
                "",
                "### MASSIVE metrics (test split)",
                "",
                f"| MAE | RMSE | MAPE (%) | Dir. Acc. |",
                f"|-----|------|----------|-----------|",
                f"| {_format_float(bs.get('mae'))} "
                f"| {_format_float(bs.get('rmse'))} "
                f"| {_format_float(bs.get('mape'))} "
                f"| {_format_float(bs.get('directional_accuracy'))} |",
                "",
                "### Diebold–Mariano tests (Holm–Bonferroni adjusted)",
                "",
                "| vs Baseline | p-raw | p-adj | Significant |",
                "|-------------|-------|-------|-------------|",
            ]
            for bl_name, dm in r.get("dm_tests", {}).items():
                lines.append(
                    f"| {bl_name} "
                    f"| {_format_float(dm.get('p_raw'))} "
                    f"| {_format_float(dm.get('p_adj_holm'))} "
                    f"| {'✓' if dm.get('significant') else '✗'} |"
                )

        tp = r.get("turning_points", {})
        if tp:
            lines += [
                "",
                "### Turning-point skill",
                "",
                f"- Precision: {_format_float(tp.get('precision'))}",
                f"- Recall:    {_format_float(tp.get('recall'))}",
                f"- F1:        {_format_float(tp.get('f1'))}",
                f"- Mean timing error: {_format_float(tp.get('mean_timing_error'))} steps",
                f"- GT turning points: {tp.get('n_true', 'N/A')} | "
                f"Predicted: {tp.get('n_pred', 'N/A')}",
            ]

        lines.append("")

    lines += [
        "---",
        "",
        "_Generated by `benchmarks.runner` — MASSIVE PVU-BS_",
    ]
    return "\n".join(lines)


# ── CLI ───────────────────────────────────────────────────────────────────────

def _parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m benchmarks.runner",
        description="MASSIVE PVU-BS offline benchmark runner.",
    )
    parser.add_argument(
        "--cases",
        default="datasets/pvu_cases",
        help="Path to folder containing PVU case sub-directories.",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--offline",
        action="store_true",
        default=True,
        help="Run in offline mode (no LLM, default).",
    )
    mode_group.add_argument(
        "--llm",
        action="store_true",
        default=False,
        help="Run MASSIVE in LLM mode (requires API key).",
    )
    parser.add_argument(
        "--out",
        default="reports/validation/ci",
        help="Output directory for metrics.json and report.md.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Global random seed for reproducibility.",
    )
    return parser.parse_args(argv)


def main(argv=None) -> int:
    args = _parse_args(argv)
    mode = "llm" if args.llm else "offline"
    seed = args.seed

    # Determinism
    np.random.seed(seed)
    rng = np.random.default_rng(seed)

    log.info("PVU-BS runner | mode=%s | seed=%d | cases=%s", mode, seed, args.cases)

    # Load cases
    try:
        cases = load_cases(args.cases)
    except Exception as exc:
        log.error("Failed to load cases: %s", exc)
        return 1

    log.info("Loaded %d case(s).", len(cases))

    # Evaluate
    results = []
    for case in cases:
        log.info("Evaluating case: %s", case["name"])
        result = evaluate_case(case, mode, rng)
        results.append(result)

    # Output
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = out_dir / "metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as fh:
        json.dump(results, fh, indent=2, ensure_ascii=False)
    log.info("Metrics saved to %s", metrics_path)

    report_md = generate_report(results, mode, seed)
    report_path = out_dir / "report.md"
    with open(report_path, "w", encoding="utf-8") as fh:
        fh.write(report_md)
    log.info("Report saved to %s", report_path)

    skipped = sum(1 for r in results if r.get("skipped"))
    log.info(
        "Done. %d case(s) evaluated, %d skipped.",
        len(results) - skipped,
        skipped,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
