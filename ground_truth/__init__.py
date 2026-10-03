"""Ground Truth Data Layer — Layer 1 of the MASSIVE calibration pipeline.

This package provides access to empirically-grounded data artefacts used
to calibrate the MASSIVE opinion-dynamics engine:

* **Synthetic census microdata** — 10 000 agents generated via Iterative
  Proportional Fitting (IPF / SAFE), with a bipolar opinion baseline.
* **Network topology metrics** — degree distribution, clustering,
  modularity, echo-chamber density, influence asymmetry (all with
  academic source citations).
* **Historical timeseries** — 11 real-world protest / election events
  converted from CSV to Parquet with embedded metadata.
* **Sealed splits** — deterministic train / validation / historical-test
  partitions with SHA-256 hash locks.  The historical-test split is sealed
  and requires an explicit unlock.

Public API
----------
::

    from ground_truth import (
        load_microdata,
        load_network_topology,
        load_timeseries,
        get_split,
        seal_splits,
        unlock_historical_test,
        HistoricalTestSealedError,
    )

All empirical values are cited in ``_constants.py``.
"""

from __future__ import annotations

import json
from typing import Any

import pandas as pd
import pyarrow.parquet as pq

from ground_truth._constants import (
    DATASETS_DIR,
    MICRODATA_DICT_PATH,
    MICRODATA_N_AGENTS,
    MICRODATA_PATH,
    MICRODATA_SEED,
    NETWORK_PATH,
    PROVENANCE_PATH,
    REFERENCES,
    SPLITS_PATH,
    SPLITS_SEED,
)
from ground_truth._seals import (
    HistoricalTestSealedError,
    derive_unlock_key,
    get_split,
    seal_splits,
    unlock_historical_test,
    verify_seal,
)

__all__ = [
    # Loaders
    "load_microdata",
    "load_network_topology",
    "load_variable_dictionary",
    "load_timeseries",
    "load_timeseries_metadata",
    "list_timeseries_events",
    # Split accessors
    "get_split",
    "seal_splits",
    "unlock_historical_test",
    "verify_seal",
    "derive_unlock_key",
    "HistoricalTestSealedError",
    # Constants / metadata
    "DATASETS_DIR",
    "MICRODATA_PATH",
    "NETWORK_PATH",
    "SPLITS_PATH",
    "SPLITS_SEED",
    "PROVENANCE_PATH",
    "MICRODATA_N_AGENTS",
    "MICRODATA_SEED",
    "REFERENCES",
    "LAYER_VERSION",
]

LAYER_VERSION = "1.0.0"


# ── Loaders ────────────────────────────────────────────────────────────


def load_microdata() -> pd.DataFrame:
    """Load the synthetic census microdata as a DataFrame.

    The microdata is generated via Iterative Proportional Fitting (IPF /
    SAFE) and stored as a Parquet file with embedded metadata.

    Returns:
        DataFrame with columns: ``agent_id``, ``age_group``,
        ``education_level``, ``income_quintile``, ``gender``, ``region``,
        ``cultural_profile``, ``opinion_baseline``.

    Raises:
        FileNotFoundError: If the microdata parquet has not been generated.
    """
    if not MICRODATA_PATH.exists():
        raise FileNotFoundError(
            f"Microdata not found at {MICRODATA_PATH}. "
            "Run `python -m ground_truth._generate` first."
        )
    return pd.read_parquet(MICRODATA_PATH)


def load_variable_dictionary() -> dict[str, Any]:
    """Load the microdata variable dictionary.

    Returns:
        Dictionary mapping each column name to its type, description,
        categories (if categorical), and academic source.
    """
    if not MICRODATA_DICT_PATH.exists():
        raise FileNotFoundError(
            f"Variable dictionary not found at {MICRODATA_DICT_PATH}. "
            "Run `python -m ground_truth._generate` first."
        )
    with open(MICRODATA_DICT_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_network_topology() -> dict[str, Any]:
    """Load the empirical network topology metrics.

    Returns:
        Dictionary with keys: ``degree_distribution``,
        ``clustering_coefficient``, ``modularity``,
        ``echo_chamber_density``, ``influence_asymmetry``, and ``metadata``.
    """
    if not NETWORK_PATH.exists():
        raise FileNotFoundError(
            f"Network topology not found at {NETWORK_PATH}. "
            "Run `python -m ground_truth._generate` first."
        )
    with open(NETWORK_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_timeseries(case_id: str) -> pd.DataFrame:
    """Load a historical event's timeseries as a DataFrame.

    Args:
        case_id: Event identifier, e.g. ``"brexit_referendum_2016"``.

    Returns:
        DataFrame with columns: ``timestep``, ``date``, ``P`` (polarization
        or participation rate depending on scenario type).

    Raises:
        FileNotFoundError: If the parquet file does not exist.
    """
    ts_path = DATASETS_DIR / f"timeseries_{case_id}.parquet"
    if not ts_path.exists():
        # Try with the full case_id from real_cases directory
        available = list_timeseries_events()
        raise FileNotFoundError(
            f"Timeseries for '{case_id}' not found. " f"Available events: {available}"
        )
    return pd.read_parquet(ts_path)


def list_timeseries_events() -> list[str]:
    """List all available historical event identifiers.

    Returns:
        Sorted list of event case_id strings derived from
        ``timeseries_*.parquet`` files.
    """
    if not DATASETS_DIR.exists():
        return []
    return sorted(
        p.stem.replace("timeseries_", "") for p in DATASETS_DIR.glob("timeseries_*.parquet")
    )


def load_timeseries_metadata(case_id: str) -> dict[str, Any]:
    """Load embedded metadata for a historical event's timeseries.

    Args:
        case_id: Event identifier.

    Returns:
        Dictionary of metadata key-value pairs embedded in the parquet
        file (e.g. ``title``, ``country``, ``scenario_type``).
    """
    ts_path = DATASETS_DIR / f"timeseries_{case_id}.parquet"
    if not ts_path.exists():
        raise FileNotFoundError(f"Timeseries for '{case_id}' not found.")

    table = pq.read_table(str(ts_path))
    meta = table.schema.metadata
    if meta is None:
        return {}

    # Parquet metadata is bytes → bytes; decode UTF-8
    return {
        k.decode("utf-8") if isinstance(k, bytes) else k: (
            v.decode("utf-8") if isinstance(v, bytes) else v
        )
        for k, v in meta.items()
    }


# ── Re-export seal utilities ───────────────────────────────────────────

__doc__ += """

Split Management
----------------

The historical-test split is **sealed** — its indices are not stored in
plaintext in ``splits.json``.  Use :func:`get_split` for train/validation,
and :func:`unlock_historical_test` with a valid key for the sealed split::

    # Train split — directly accessible
    train = get_split("brexit_referendum_2016", "train")

    # Validation split — directly accessible
    val = get_split("brexit_referendum_2016", "validation")

    # Historical-test — sealed, requires unlock key
    key = derive_unlock_key()  # uses default seed
    test = unlock_historical_test("brexit_referendum_2016", unlock_key=key)
"""
