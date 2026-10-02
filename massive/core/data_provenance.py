"""Layer 4 — Data provenance registry for sealed historical data.

Tracks SHA-256 hashes of dataset files and provides deterministic seed
derivation so that every ABC-SMC round and backtest run is fully
reproducible.  The registry is persisted as a JSON file alongside the
modules so it survives across sessions.

Usage::

    from massive.core.data_provenance import register_dataset, verify_integrity

    register_dataset("brexit_referendum_2016", "datasets/ground_truth/brexit_referendum_2016")
    assert verify_integrity("brexit_referendum_2016")
    seeds = get_seed_sequence(42, n_rounds=3)   # → [42, 14826, 14827]
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

# ── Registry persistence ────────────────────────────────────────────────────
_REGISTRY_PATH = Path(__file__).parent / "_provenance_registry.json"
_registry: dict[str, dict[str, Any]] = {}

# Keys stored per dataset entry
_NAME = "name"
_PATH = "path"
_HASH = "sha256"
_FILE_COUNT = "file_count"
_REGISTERED_AT = "registered_at"


# ── Internal helpers ────────────────────────────────────────────────────────


def _load_registry() -> dict[str, dict[str, Any]]:
    """Load the on-disk registry, or return an empty dict."""
    global _registry
    if _registry:
        return _registry
    if _REGISTRY_PATH.exists():
        try:
            with open(_REGISTRY_PATH, encoding="utf-8") as fh:
                _registry = json.load(fh)
        except (json.JSONDecodeError, OSError):
            _registry = {}
    return _registry


def _save_registry() -> None:
    """Persist the in-memory registry to disk."""
    with open(_REGISTRY_PATH, "w", encoding="utf-8") as fh:
        json.dump(_registry, fh, indent=2, sort_keys=True)


def hash_file(path: str | Path) -> str:
    """Compute the SHA-256 hash of a single file.

    Args:
        path: Path to the file.

    Returns:
        Hexadecimal SHA-256 digest string.
    """
    path = Path(path)
    hasher = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def hash_directory(path: str | Path) -> str:
    """Compute a deterministic aggregate SHA-256 over a directory tree.

    Files are sorted by relative path so the hash is reproducible regardless
    of filesystem enumeration order.

    Args:
        path: Directory to hash.

    Returns:
        Hexadecimal SHA-256 digest combining all file hashes.
    """

    path = Path(path)
    files = sorted(p for p in path.rglob("*") if p.is_file())
    if not files:
        return hashlib.sha256(str(path).encode()).hexdigest()

    hasher = hashlib.sha256()
    file_count = 0
    for fpath in files:
        rel = fpath.relative_to(path).as_posix()
        hasher.update(rel.encode())
        hasher.update(fpath.read_bytes())
        file_count += 1

    digest = hasher.hexdigest()
    # Stash the file count as an attribute-like side effect on the returned
    # string — not thread-safe but sufficient for this single-process use.
    hash_directory._last_count = file_count  # type: ignore[attr-defined]
    return digest


# ── Public API ──────────────────────────────────────────────────────────────


def register_dataset(name: str, path: str | Path) -> dict[str, Any]:
    """Compute SHA-256 for a dataset (file or directory) and store its metadata.

    Args:
        name: Human-readable dataset identifier.
        path: Path to a single file or a directory.

    Returns:
        The metadata dict that was stored (sha256, file_count, path).

    Raises:
        FileNotFoundError: If ``path`` does not exist.
    """

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Dataset path not found: {path}")

    registry = _load_registry()

    import datetime

    if path.is_file():
        digest = hash_file(path)
        file_count = 1
    else:
        digest = hash_directory(path)
        file_count = hash_directory._last_count  # type: ignore[attr-defined]

    entry: dict[str, Any] = {
        _NAME: name,
        _PATH: str(path),
        _HASH: digest,
        _FILE_COUNT: file_count,
        _REGISTERED_AT: datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    registry[name] = entry
    _save_registry()
    return entry


def verify_integrity(name: str) -> bool:
    """Check that a registered dataset's current SHA-256 matches the stored hash.

    Args:
        name: Dataset name (as passed to :func:`register_dataset`).

    Returns:
        ``True`` if the hash matches, ``False`` otherwise.
    """

    registry = _load_registry()
    entry = registry.get(name)
    if entry is None:
        return False

    path = Path(entry[_PATH])
    if not path.exists():
        return False

    if path.is_file():
        current = hash_file(path)
    else:
        current = hash_directory(path)

    return current == entry[_HASH]


def get_seed_sequence(seed: int, n_rounds: int) -> list[int]:
    """Derive a deterministic sequence of seeds for reproducible multi-round runs.

    Uses ``np.random.SeedSequence`` (the modern, statistically robust
    spawn mechanism) so that each round gets an independent sub-seed
    while remaining fully deterministic for a given *seed*.

    Args:
        seed: Master seed (e.g. 42).
        n_rounds: Number of round seeds to generate.

    Returns:
        List of ``n_rounds`` integer seeds.
    """

    ss = np.random.SeedSequence(seed)
    children = ss.spawn(n_rounds)
    return [int(child.generate_state(1)[0]) for child in children]


def get_registry() -> dict[str, dict[str, Any]]:
    """Return a copy of the full registry (for inspection / reporting)."""
    _load_registry()
    return {k: dict(v) for k, v in _registry.items()}


__all__ = [
    "register_dataset",
    "verify_integrity",
    "get_seed_sequence",
    "hash_file",
    "hash_directory",
    "get_registry",
]
