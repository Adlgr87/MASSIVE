#!/usr/bin/env python3
"""G4: Run historical backtests on ≥3 cases with pre-registration.

Executes blind backtests from day-0 conditions only, comparing against
sealed historical data. Writes results to reports/backtest_results.json.

Usage:
    python scripts/run_backtests.py                    # all 12 cases
    python scripts/run_backtests.py --cases 3          # quick test (3 cases)
    python scripts/run_backtests.py --cases brexit_referendum_2016,egypt_arab_spring_2011,us_election_2020
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from massive.core.backtesting import Backtester

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "reports" / "backtest_results.json"
DEFAULT_CASES = [
    "brexit_referendum_2016",     # polarization_spike, leave_vote_share
    "egypt_arab_spring_2011",     # contagion_sir, fraction_participating
    "us_election_2020",           # polarization_escalation, polarization_index
    "south_korea_candlelight_2016",  # consensus_cascade
]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cases", type=str, default="",
        help="comma-separated case IDs (default: 4 representative cases)",
    )
    parser.add_argument("--n-agents", type=int, default=80)
    parser.add_argument("--ensemble", type=int, default=20)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=str, default=str(OUTPUT))
    args = parser.parse_args()

    case_ids = args.cases.split(",") if args.cases else DEFAULT_CASES

    bt = Backtester(n_agents=args.n_agents, ensemble_size=args.ensemble, seed=args.seed)

    results: list[dict] = []
    for case_id in case_ids:
        print(f"\n{'='*60}")
        print(f"Backtest: {case_id}")
        print(f"{'='*60}")
        result = bt.run_backtest(case_id, seed=args.seed)

        summary = {
            "case_id": result.case_id,
            "seed": result.seed,
            "n_timesteps": len(result.observed_trajectory),
            "metrics": {
                "wasserstein": round(result.metrics.wasserstein, 6),
                "kl_divergence": round(result.metrics.kl_divergence, 6),
                "dtw_rmse": round(result.metrics.dtw_rmse, 6),
                "direction_error": round(result.metrics.direction_error, 6),
                "coverage_90ci": round(result.metrics.coverage_90ci, 6),
                "passed_all": result.metrics.passed_all,
            },
            "gates": result.gates,
            "elapsed_seconds": round(result.elapsed_seconds, 2),
        }
        results.append(summary)
        print(f"  Wasserstein:     {result.metrics.wasserstein:.4f}")
        print(f"  KL divergence:   {result.metrics.kl_divergence:.4f}")
        print(f"  DTW-RMSE:        {result.metrics.dtw_rmse:.4f}")
        print(f"  Direction error: {result.metrics.direction_error:.4f}")
        print(f"  Coverage 90%CI:  {result.metrics.coverage_90ci:.4f}")
        print(f"  Passed all:      {result.metrics.passed_all}")
        print(f"  Gates: {result.gates}")

    # Summary
    passed = sum(1 for r in results if r["gates"]["G3"])
    total = len(results)
    print(f"\n{'='*60}")
    print(f"SUMMARY: {passed}/{total} cases passed G3 (metrics within thresholds)")
    print("Best overall baseline MAE (from baselines_12cases.json): 0.0482")
    print(f"{'='*60}")

    report = {
        "description": "Blind historical backtests from day-0 conditions only",
        "method": "Backtester with ensemble_size, seeded params from physics_params_v1.0.0.yaml",
        "n_cases": total,
        "n_passed_g3": passed,
        "cases": results,
        "thresholds": bt.thresholds,
    }

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"\nReport written to: {out_path}")


if __name__ == "__main__":
    main()
