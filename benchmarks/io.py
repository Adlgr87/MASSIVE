"""Case I/O for PVU-BS benchmark runner.

Loads PVU cases from a directory. Each case is a sub-folder containing:
  - timeseries.csv  : date, P (polarization index), optional columns
  - interventions.json : list of {date, label, source} dicts
  - meta.json       : case metadata (domain, cluster_id, …)

Usage
-----
    from benchmarks.io import load_cases
    cases = load_cases("datasets/pvu_cases")
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import numpy as np

log = logging.getLogger(__name__)

# Required columns in timeseries.csv
REQUIRED_TIMESERIES_COLS = {"date", "P"}


def _load_timeseries(path: Path) -> dict[str, Any]:
    """Load timeseries.csv into parallel numpy arrays."""
    import csv

    rows: list[dict] = []
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = REQUIRED_TIMESERIES_COLS - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"{path}: missing columns {missing}")
        for row in reader:
            rows.append(row)

    dates = [r["date"] for r in rows]
    P = np.array([float(r["P"]) for r in rows])
    extra: dict[str, np.ndarray] = {}
    for col in (reader.fieldnames or []):
        if col not in ("date", "P"):
            try:
                extra[col] = np.array([float(r[col]) for r in rows])
            except (ValueError, KeyError):
                pass
    return {"dates": dates, "P": P, **extra}


def _load_json(path: Path) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_case(case_dir: str | Path) -> dict[str, Any]:
    """Load a single PVU case from *case_dir*.

    Returns a dict with keys:
      - ``name``          : folder name used as case ID
      - ``meta``          : contents of meta.json
      - ``timeseries``    : dict with ``dates``, ``P``, and optional series
      - ``interventions`` : list of intervention dicts (empty if file missing)
    """
    d = Path(case_dir)
    if not d.is_dir():
        raise FileNotFoundError(f"Case directory not found: {d}")

    ts_path = d / "timeseries.csv"
    if not ts_path.exists():
        raise FileNotFoundError(f"timeseries.csv missing in {d}")

    meta_path = d / "meta.json"
    meta: dict = _load_json(meta_path) if meta_path.exists() else {}

    interventions_path = d / "interventions.json"
    interventions: list = _load_json(interventions_path) if interventions_path.exists() else []

    return {
        "name": d.name,
        "meta": meta,
        "timeseries": _load_timeseries(ts_path),
        "interventions": interventions,
    }


def load_cases(cases_dir: str | Path) -> list[dict[str, Any]]:
    """Load all PVU cases from *cases_dir* (one sub-folder per case).

    Sub-folders are sorted alphabetically for reproducibility.
    Folders that fail to load are skipped with a warning.
    """
    root = Path(cases_dir)
    if not root.is_dir():
        raise FileNotFoundError(f"Cases directory not found: {root}")

    cases: list[dict] = []
    for sub in sorted(root.iterdir()):
        if not sub.is_dir():
            continue
        try:
            case = load_case(sub)
            cases.append(case)
            log.debug("Loaded case: %s (%d timesteps)", case["name"], len(case["timeseries"]["P"]))
        except Exception as exc:  # noqa: BLE001
            log.warning("Skipping %s: %s", sub.name, exc)

    if not cases:
        raise RuntimeError(f"No valid PVU cases found in {root}")

    return cases
