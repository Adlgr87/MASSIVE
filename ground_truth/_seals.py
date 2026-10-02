"""Split sealing and hash-lock management for the Ground Truth layer.

The historical-test split is **sealed** — its actual timestep indices are
not stored in ``splits.json``.  Only a SHA-256 hash lock and a sample
count are persisted.  The indices are derivable deterministically from
the seed but are only returned when the caller supplies a valid *unlock
key*.

Design
------
* ``seal_splits()`` re-reads ``splits.json``, recomputes every hash lock
  and the overall seal hash, then writes them back.  This is the
  "sealing" operation that locks the splits.
* ``get_split()`` returns train / validation splits in plaintext.
* ``get_split(..., "historical_test")`` without an unlock key raises
  :class:`HistoricalTestSealedError`.
* ``unlock_historical_test()`` verifies the caller-supplied key against
  the stored ``unlock_hash`` and, on success, returns the indices.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from ground_truth._constants import (
    DATASETS_DIR,
    SPLITS_PATH,
    SPLITS_SEED,
    TRAIN_FRACTION,
    VAL_FRACTION,
)

__all__ = [
    "HistoricalTestSealedError",
    "seal_splits",
    "verify_seal",
    "unlock_historical_test",
    "get_split",
    "derive_unlock_key",
]


class HistoricalTestSealedError(RuntimeError):
    """Raised when accessing the historical-test split without an unlock key."""


# ── Key derivation ─────────────────────────────────────────────────────


def derive_unlock_key(case_id: str, seed: int = SPLITS_SEED) -> str:
    """Derive the deterministic unlock key for a given seed + case_id.

    The key is a deterministic SHA-256 derivative.  It is designed so
    that:

    * It can be computed by anyone who knows the seed (which is a public
      constant in this module).
    * It is **not** stored in ``splits.json`` — only its SHA-256 hash is.
    * The split data itself is never stored in plaintext.

    This design enforces an **explicit unlock step** (Layer 4 handoff)
    rather than a hard cryptographic barrier: a motivated party *could*
    derive the key, but the split is sealed by default and the unlock
    is a deliberate action.

    Args:
        case_id: The event case identifier
            (e.g. ``"brexit_referendum_2016"``).
        seed: The splits RNG seed.

    Returns:
        A 32-character hex-string unlock key.
    """
    return hashlib.sha256(f"{seed}:{case_id}:historical_test".encode()).hexdigest()[:32]


# ── Internal helpers ───────────────────────────────────────────────────


def _load_splits() -> dict[str, Any]:
    """Load the splits definition from disk."""
    if not SPLITS_PATH.exists():
        raise FileNotFoundError(
            f"splits.json not found at {SPLITS_PATH}. "
            "Run `python -m ground_truth._generate` first."
        )
    with open(SPLITS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _save_splits(data: dict[str, Any]) -> None:
    """Save the splits definition to disk."""
    SPLITS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SPLITS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _sha256_str(data: str) -> str:
    """SHA-256 hex digest of a string."""
    return hashlib.sha256(data.encode()).hexdigest()


def _compute_test_indices(case_id: str, n_timesteps: int) -> list[int]:
    """Deterministically compute historical-test indices for an event.

    Uses the same chronological split logic as ``_generate.py``.
    The indices themselves are **not** stored in splits.json — they are
    recomputed here so that ``unlock_historical_test`` can return them
    after key verification.

    Args:
        case_id: Event case identifier.
        n_timesteps: Total number of timesteps for the event.

    Returns:
        List of integer timestep indices belonging to the historical-test split.
    """
    rng = np.random.default_rng(SPLITS_SEED)

    # Mirror the generation logic: chronological split
    # Train = first 60 %, val = next 25 %, test = last 15 %.
    n_train = max(1, int(round(n_timesteps * TRAIN_FRACTION)))
    n_val = max(1, int(round(n_timesteps * VAL_FRACTION)))
    n_test = n_timesteps - n_train - n_val
    if n_test <= 0:
        n_test = 1
        n_val = n_timesteps - n_train - n_test

    all_indices = np.arange(n_timesteps, dtype=np.int64)
    test_indices = all_indices[n_train + n_val :].tolist()
    _ = rng  # seed is consumed by generate_splits but not needed here
    return test_indices


# ── Public API ─────────────────────────────────────────────────────────


def seal_splits() -> dict[str, Any]:
    """Compute and store hash locks for all splits.

    This function re-reads ``splits.json``, recomputes the SHA-256 hash
    of every split definition, updates the overall seal hash, and writes
    the result back to disk.

    Returns:
        The updated splits definition with fresh hash locks.
    """
    splits = _load_splits()

    # Recompute hash locks for each event's train and validation splits
    for case_id, event_data in splits["events"].items():
        train_indices = event_data["train"]["indices"]
        val_indices = event_data["validation"]["indices"]

        event_data["train"]["hash"] = _sha256_str(json.dumps(train_indices, sort_keys=True))
        event_data["validation"]["hash"] = _sha256_str(json.dumps(val_indices, sort_keys=True))

        # Recompute the historical-test hash (indices not stored in plaintext)
        n_ts = event_data["n_timesteps"]
        test_indices = _compute_test_indices(case_id, n_ts)
        test_hash = _sha256_str(json.dumps(test_indices, sort_keys=True))
        event_data["historical_test"]["hash"] = test_hash

        # Recompute unlock hash
        unlock_key = derive_unlock_key(case_id, SPLITS_SEED)
        event_data["historical_test"]["unlock_hash"] = _sha256_str(unlock_key)
        event_data["historical_test"]["sealed"] = True
        event_data["historical_test"]["unlock_required"] = True

    # Recompute overall seal hash
    seal_payload = json.dumps(
        splits["events"],
        sort_keys=True,
    )
    splits["seal"]["seal_hash"] = _sha256_str(seal_payload)
    splits["seal"]["sealed_at"] = _sha256_str  # placeholder; updated below

    from datetime import datetime, timezone

    splits["seal"]["sealed_at"] = datetime.now(timezone.utc).isoformat()

    _save_splits(splits)
    return splits


def verify_seal() -> bool:
    """Verify the integrity of the sealed splits file.

    Checks that:
    * The seal hash matches the current event definitions.
    * The overall file structure is valid.

    Returns:
        ``True`` if the seal is valid.
    """
    splits = _load_splits()

    # Recompute seal hash from events
    seal_payload = json.dumps(splits["events"], sort_keys=True)
    expected_hash = _sha256_str(seal_payload)

    if splits["seal"]["seal_hash"] != expected_hash:
        return False

    # Verify each event's train/val hashes
    for case_id, event_data in splits["events"].items():
        train_h = _sha256_str(json.dumps(event_data["train"]["indices"], sort_keys=True))
        val_h = _sha256_str(json.dumps(event_data["validation"]["indices"], sort_keys=True))
        if train_h != event_data["train"]["hash"]:
            return False
        if val_h != event_data["validation"]["hash"]:
            return False

    return True


def unlock_historical_test(
    case_id: str,
    unlock_key: str | None = None,
) -> dict[str, Any]:
    """Unlock the historical-test split for a given event.

    The historical-test split is sealed — its indices are not stored in
    ``splits.json``.  To access it, the caller must supply a valid
    *unlock key*.

    Args:
        case_id: Event case identifier.
        unlock_key: Unlock key string.  If ``None``, a
            :class:`HistoricalTestSealedError` is raised.

    Returns:
        Dict with ``indices`` and ``dates`` for the historical-test split.

    Raises:
        HistoricalTestSealedError: If no unlock key is provided or the
            key does not match the stored hash.
        FileNotFoundError: If splits.json does not exist.
        KeyError: If the event is not found in splits.
    """
    if unlock_key is None:
        raise HistoricalTestSealedError(
            f"Historical-test split for '{case_id}' is sealed. "
            "Call unlock_historical_test(case_id, unlock_key=...) with "
            "the correct key to access it."
        )

    splits = _load_splits()

    if case_id not in splits["events"]:
        raise KeyError(f"Event '{case_id}' not found in splits.")

    event_data = splits["events"][case_id]
    stored_hash = event_data["historical_test"]["unlock_hash"]

    # Verify unlock key
    provided_hash = _sha256_str(unlock_key)
    if not _constant_time_compare(provided_hash, stored_hash):
        raise HistoricalTestSealedError(
            f"Unlock key does not match for '{case_id}'. "
            "The historical-test split remains sealed."
        )

    # Key verified — compute the indices deterministically
    n_ts = event_data["n_timesteps"]
    test_indices = _compute_test_indices(case_id, n_ts)

    # Load the timeseries to get dates
    ts_path = DATASETS_DIR / f"timeseries_{case_id}.parquet"
    if ts_path.exists():
        df = _read_parquet_dates(ts_path)
        test_dates = [df["date"].iloc[i] for i in test_indices]
    else:
        test_dates = []

    return {
        "indices": test_indices,
        "dates": test_dates,
        "n_samples": len(test_indices),
        "hash": event_data["historical_test"]["hash"],
    }


def get_split(
    case_id: str,
    split_name: str,
    unlock_key: str | None = None,
) -> dict[str, Any]:
    """Access a split for a given event.

    Train and validation splits are returned directly.  The historical-
    test split is sealed and requires a valid unlock key.

    Args:
        case_id: Event case identifier.
        split_name: One of ``"train"``, ``"validation"``, ``"historical_test"``.
        unlock_key: Required only for ``"historical_test"``.

    Returns:
        Dict with ``indices``, ``dates``, and ``hash``.

    Raises:
        HistoricalTestSealedError: If accessing ``historical_test``
            without a valid unlock key.
        ValueError: If split_name is not recognised.
    """
    if split_name not in ("train", "validation", "historical_test"):
        raise ValueError(
            f"Unknown split '{split_name}'. "
            "Must be one of: 'train', 'validation', 'historical_test'."
        )

    if split_name == "historical_test":
        return unlock_historical_test(case_id, unlock_key)

    splits = _load_splits()

    if case_id not in splits["events"]:
        raise KeyError(f"Event '{case_id}' not found in splits.")

    event_data = splits["events"][case_id]
    split_data = event_data[split_name]

    return {
        "indices": split_data["indices"],
        "dates": split_data["dates"],
        "n_samples": len(split_data["indices"]),
        "hash": split_data["hash"],
    }


# ── Utilities ──────────────────────────────────────────────────────────


def _constant_time_compare(a: str, b: str) -> bool:
    """Constant-time string comparison to prevent timing attacks."""
    if len(a) != len(b):
        return False
    result = 0
    for x, y in zip(a, b):
        result |= ord(x) ^ ord(y)
    return result == 0


def _read_parquet_dates(path: Path) -> "pd.DataFrame":  # noqa: F821
    """Read date column from a parquet file (lazy import to avoid hard dep)."""
    import pandas as pd

    return pd.read_parquet(path)
