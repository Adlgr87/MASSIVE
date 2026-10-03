#!/usr/bin/env python3
"""Validate the calibration corpus under ``datasets/``.

Written after an audit of `datasets/real_cases/` found problems that silently
invalidate calibration rather than crashing it:

* **`P` is undefined in every case.** All twelve `timeseries.csv` files use the
  column `P`, but no `meta.json` says what it measures — and it demonstrably
  measures different things: Brexit's `P` is a Leave vote share, Egypt's is an
  SIR-shaped protest participation fraction, South Korea's is a consensus
  cascade. Pooling those as if they were one observable is meaningless.
* **No observation operator.** Nothing states how the simulator's state maps to
  the measured quantity, so a distance like RMSE or Wasserstein between "sim"
  and "real" is not well defined.
* **Scalars, not distributions.** Each row is one number with no sample size or
  variance, which bounds what is identifiable: distributional parameters
  cannot be estimated from a scalar series.
* **Estimated, not measured.** `data_type` is `empirical_estimated`: the series
  were reconstructed from published sources by hand. That is legitimate, but it
  must be declared, never silently mixed with directly measured data.
* **Tiny series.** 11-15 points per case, ~170 observations total.

This script makes each of those explicit and machine-checkable, so a dataset
either carries the metadata needed to calibrate against it or fails loudly.

Usage:
    python scripts/validate_dataset.py                    # validate everything
    python scripts/validate_dataset.py --root datasets/real_cases
    python scripts/validate_dataset.py --json             # machine-readable
    python scripts/validate_dataset.py --strict           # warnings are errors
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

# Minimum series length for a case to carry weight in calibration. Below this a
# case is kept but flagged: it can still anchor a prior, it cannot identify a
# parameter on its own.
MIN_OBSERVATIONS = 30

# Fields that must be present for a case to be usable in calibration at all.
REQUIRED_META = ("case_id", "title", "country", "scenario_type", "sources")

# Fields the audit showed to be missing everywhere, and without which the
# calibration cannot be posed correctly.
REQUIRED_FOR_CALIBRATION = (
    "target_variable",  # what P actually measures, in words
    "target_units",  # share | fraction_participating | index | ...
    "observation_operator",  # how simulator state maps to the measurement
    "data_type",  # measured | empirical_estimated | synthetic
)

RECOMMENDED_META = (
    "source_license",
    "question_wording",
    "sampling_error",
    "n_sample",
    "data_confidence",
)

VALID_DATA_TYPES = {"measured", "empirical_estimated", "synthetic"}


@dataclass
class CaseReport:
    case_id: str
    path: str
    n_observations: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    info: dict[str, Any] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    @property
    def calibration_ready(self) -> bool:
        """Usable as a calibration target, not merely well-formed."""
        return not self.errors and self.n_observations >= MIN_OBSERVATIONS


def _parse_date(raw: str) -> date | None:
    """Accept ISO dates and ISO week notation (`2016-W23`), which this corpus uses."""
    raw = raw.strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            pass
    if "-W" in raw:
        try:
            year, week = raw.split("-W")
            return date.fromisocalendar(int(year), int(week), 1)
        except (ValueError, TypeError):
            return None
    return None


def _validate_timeseries(path: Path, report: CaseReport) -> list[float]:
    if not path.exists():
        report.errors.append("timeseries.csv missing")
        return []

    with path.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))

    if not rows:
        report.errors.append("timeseries.csv has no data rows")
        return []

    columns = set(rows[0])
    if "date" not in columns:
        report.errors.append("timeseries.csv has no 'date' column")
    if "P" not in columns:
        report.errors.append("timeseries.csv has no 'P' column")
    if report.errors:
        return []

    # A series with only (date, P) is a scalar observable. Say so explicitly,
    # because it caps what can ever be identified from this case.
    distributional = {"P_std", "P_var", "n_sample", "P_lower", "P_upper"} & columns
    report.info["shape"] = "distributional" if distributional else "scalar"
    if not distributional:
        report.warnings.append(
            "scalar observable (only date,P): no dispersion information, so "
            "distributional parameters are not identifiable from this case"
        )

    values: list[float] = []
    previous: date | None = None
    seen: set[str] = set()

    for i, row in enumerate(rows, start=2):  # header is line 1
        raw_date = (row.get("date") or "").strip()
        parsed = _parse_date(raw_date)
        if parsed is None:
            report.errors.append(f"line {i}: unparseable date {raw_date!r}")
            continue
        if raw_date in seen:
            report.errors.append(f"line {i}: duplicate date {raw_date!r}")
        seen.add(raw_date)
        if previous and parsed < previous:
            report.errors.append(f"line {i}: date {raw_date!r} goes backwards")
        previous = parsed

        raw_value = (row.get("P") or "").strip()
        try:
            value = float(raw_value)
        except ValueError:
            report.errors.append(f"line {i}: P is not a number: {raw_value!r}")
            continue
        if not 0.0 <= value <= 1.0:
            report.errors.append(f"line {i}: P={value} outside [0, 1]")
        values.append(value)

    report.n_observations = len(values)
    if values:
        report.info["P_min"] = min(values)
        report.info["P_max"] = max(values)
        if max(values) == min(values):
            report.warnings.append("P is constant: nothing to calibrate against")
    return values


def _validate_meta(path: Path, report: CaseReport) -> dict[str, Any]:
    if not path.exists():
        report.errors.append("meta.json missing")
        return {}
    try:
        meta = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        report.errors.append(f"meta.json is not valid JSON: {exc}")
        return {}

    for key in REQUIRED_META:
        if not meta.get(key):
            report.errors.append(f"meta.json missing required field {key!r}")

    # The audit findings, promoted to hard requirements.
    for key in REQUIRED_FOR_CALIBRATION:
        if not meta.get(key):
            report.errors.append(
                f"meta.json missing {key!r} — required before this case can be "
                "used as a calibration target"
            )

    data_type = meta.get("data_type")
    if data_type and data_type not in VALID_DATA_TYPES:
        report.errors.append(
            f"data_type {data_type!r} invalid; use one of {sorted(VALID_DATA_TYPES)}"
        )
    if data_type == "synthetic" or meta.get("is_synthetic"):
        report.warnings.append(
            "synthetic case: valid for stress-testing only, never for calibration"
        )
    if data_type == "empirical_estimated":
        report.warnings.append(
            "series reconstructed from published sources rather than measured "
            "directly; keep separate from measured data and weight accordingly"
        )

    for key in RECOMMENDED_META:
        if not meta.get(key):
            report.warnings.append(f"meta.json missing recommended field {key!r}")

    sources = meta.get("sources")
    if isinstance(sources, list) and not sources:
        report.errors.append("meta.json 'sources' is empty")

    declared = meta.get("n_timesteps") or meta.get("n_observations")
    if declared is not None and report.n_observations and int(declared) != report.n_observations:
        report.errors.append(
            f"meta.json declares {declared} timesteps but timeseries.csv has "
            f"{report.n_observations}"
        )

    report.info["scenario_type"] = meta.get("scenario_type")
    report.info["target_variable"] = meta.get("target_variable")
    report.info["data_type"] = data_type
    return meta


def validate_case(case_dir: Path) -> CaseReport:
    report = CaseReport(case_id=case_dir.name, path=str(case_dir))
    _validate_timeseries(case_dir / "timeseries.csv", report)
    _validate_meta(case_dir / "meta.json", report)

    if 0 < report.n_observations < MIN_OBSERVATIONS:
        report.warnings.append(
            f"only {report.n_observations} observations (< {MIN_OBSERVATIONS}): "
            "too short to identify parameters on its own; usable for pooling"
        )
    return report


def validate_corpus(root: Path) -> dict[str, Any]:
    case_dirs = sorted(d for d in root.iterdir() if d.is_dir() and not d.name.startswith("."))
    reports = [validate_case(d) for d in case_dirs]

    total_obs = sum(r.n_observations for r in reports)
    ready = [r for r in reports if r.calibration_ready]

    # Different observables cannot be pooled as if they were one. Group by the
    # declared target so the mismatch is visible instead of implicit.
    by_target: dict[str, list[str]] = {}
    for r in reports:
        key = r.info.get("target_variable") or "UNDECLARED"
        by_target.setdefault(key, []).append(r.case_id)

    return {
        "root": str(root),
        "n_cases": len(reports),
        "n_cases_valid": sum(1 for r in reports if r.ok),
        "n_cases_calibration_ready": len(ready),
        "total_observations": total_obs,
        "observations_in_ready_cases": sum(r.n_observations for r in ready),
        "targets": by_target,
        "capacity_tier": _capacity_tier(total_obs),
        "cases": [asdict(r) for r in reports],
    }


def _capacity_tier(n_obs: int) -> dict[str, Any]:
    """Which modelling tier the evidence currently supports.

    A staircase, not a wall: scarce data still permits aggregate calibration
    with strong priors — it just does not permit a 10k-parameter network.
    """
    if n_obs < 500:
        return {
            "tier": 1,
            "permitted": "baselines + aggregate parameters (sigma, mean epsilon) "
            "with strong priors",
            "forbidden": "neural correctors, per-segment or per-edge parameters",
        }
    if n_obs < 2000:
        return {
            "tier": 2,
            "permitted": "simple parametric calibration via SBI/ABC with hierarchical "
            "pooling across cases",
            "forbidden": "neural residual correctors",
        }
    return {
        "tier": 3,
        "permitted": "neural residual correction (CfC) with capacity matched to "
        "the observation count",
        "forbidden": "nothing by data volume; identifiability still applies",
    }


def _print_human(result: dict[str, Any]) -> None:
    print(f"Corpus: {result['root']}\n")
    for case in result["cases"]:
        mark = "OK  " if not case["errors"] else "FAIL"
        ready = "" if case["n_observations"] >= MIN_OBSERVATIONS else "  [short]"
        print(f"  {mark} {case['case_id']:<32} {case['n_observations']:>3} obs{ready}")
        for err in case["errors"]:
            print(f"         ERROR   {err}")
        for warn in case["warnings"]:
            print(f"         warn    {warn}")

    print(f"\n  cases                     {result['n_cases']}")
    print(f"  structurally valid        {result['n_cases_valid']}")
    print(f"  calibration-ready         {result['n_cases_calibration_ready']}")
    print(f"  total observations        {result['total_observations']}")

    print("\n  Declared target variables:")
    for target, cases in sorted(result["targets"].items()):
        print(f"    {target:<28} {len(cases)} case(s)")
    if "UNDECLARED" in result["targets"]:
        print(
            "\n  WARNING: cases with an undeclared target cannot be pooled. The\n"
            "  same column name does not make two series the same observable."
        )

    tier = result["capacity_tier"]
    print(f"\n  Capacity tier {tier['tier']} for {result['total_observations']} observations")
    print(f"    permitted: {tier['permitted']}")
    print(f"    forbidden: {tier['forbidden']}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=str(ROOT / "datasets" / "real_cases"),
        help="directory containing one subdirectory per case",
    )
    parser.add_argument("--json", action="store_true", help="emit JSON")
    parser.add_argument("--strict", action="store_true", help="exit non-zero on warnings too")
    args = parser.parse_args()

    root = Path(args.root)
    if not root.is_dir():
        print(f"not a directory: {root}", file=sys.stderr)
        return 2

    result = validate_corpus(root)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        _print_human(result)

    errors = sum(len(c["errors"]) for c in result["cases"])
    warnings = sum(len(c["warnings"]) for c in result["cases"])
    if errors:
        return 1
    if args.strict and warnings:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
