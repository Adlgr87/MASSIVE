"""CfC training-data adapters for MASSIVE-generated trajectories."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

import numpy as np

Array = np.ndarray
_STATE_KEYS = (
    "opinion",
    "propaganda",
    "confianza",
    "opinion_grupo_a",
    "opinion_grupo_b",
    "pertenencia_grupo",
    "ews_variance",
    "ews_autocorr",
)


@dataclass(frozen=True)
class CfCTrainingDataset:
    """In-memory dataset compatible with ``CfCRegimeSelector`` inputs.

    Args:
        X_hist: Recent opinion windows, shape ``(samples, window_size)``.
        X_state: State feature matrix, shape ``(samples, 8)``.
        y_regime: Regime labels, shape ``(samples,)``.
    """

    X_hist: Array
    X_state: Array
    y_regime: Array

    def to_dict(self) -> dict[str, list]:
        """Convert arrays to JSON-friendly lists.

        Returns:
            Serializable dataset payload.
        """

        return {
            "X_hist": self.X_hist.tolist(),
            "X_state": self.X_state.tolist(),
            "y_regime": self.y_regime.astype(int).tolist(),
        }


def build_cfc_regime_dataset_from_history(
    history: Sequence[dict[str, Any]],
    window_size: int = 6,
) -> CfCTrainingDataset:
    """Build CfC selector training samples from a MASSIVE history.

    This adapter makes the reasoning traces produced by MASSIVE usable for CfC
    distillation or future empirical fine-tuning.  It does not train a model;
    it prepares the tensors needed by the existing CfC trainer.

    Args:
        history: Legacy MASSIVE history containing ``opinion`` and optional
            ``_regla`` labels.
        window_size: Number of recent opinions per sample.

    Returns:
        In-memory CfC training dataset.
    """

    if window_size < 1:
        raise ValueError("window_size must be positive")
    if len(history) <= window_size:
        raise ValueError("history is too short for the requested window_size")

    X_hist = []
    X_state = []
    labels = []
    opinions = [float(item["opinion"]) for item in history]
    for index in range(window_size, len(history)):
        current = history[index]
        if "_regla" not in current:
            continue
        X_hist.append(opinions[index - window_size:index])
        X_state.append(_state_vector(current))
        labels.append(int(current.get("_regla", 0)))

    if not labels:
        raise ValueError("history does not contain regime labels after the warmup window")
    return CfCTrainingDataset(
        X_hist=np.asarray(X_hist, dtype=np.float32),
        X_state=np.asarray(X_state, dtype=np.float32),
        y_regime=np.asarray(labels, dtype=np.int64),
    )


def build_cfc_regime_dataset_from_histories(
    histories: Sequence[Sequence[dict[str, Any]]],
    window_size: int = 6,
) -> CfCTrainingDataset:
    """Combine multiple histories into one CfC selector dataset.

    Args:
        histories: Collection of MASSIVE histories.
        window_size: Number of recent opinions per sample.

    Returns:
        Combined in-memory CfC training dataset.
    """

    datasets = [build_cfc_regime_dataset_from_history(history, window_size) for history in histories]
    return CfCTrainingDataset(
        X_hist=np.vstack([dataset.X_hist for dataset in datasets]),
        X_state=np.vstack([dataset.X_state for dataset in datasets]),
        y_regime=np.concatenate([dataset.y_regime for dataset in datasets]),
    )


def save_cfc_regime_dataset(dataset: CfCTrainingDataset, path: str) -> str:
    """Save a CfC dataset in the format expected by ``cfc_trainer``.

    Args:
        dataset: In-memory CfC dataset.
        path: Destination ``.pt`` file.

    Returns:
        Destination path as a string.
    """

    try:
        import torch
    except ImportError as exc:
        raise ImportError("PyTorch is required to save CfC datasets") from exc
    torch.save(
        {
            "X_hist": torch.tensor(dataset.X_hist, dtype=torch.float32),
            "X_state": torch.tensor(dataset.X_state, dtype=torch.float32),
            "Y": torch.tensor(dataset.y_regime, dtype=torch.long),
        },
        path,
    )
    return path


def _state_vector(state: dict[str, Any]) -> list[float]:
    ews = state.get("ews", {}) if isinstance(state.get("ews", {}), dict) else {}
    metrics = ews.get("metrics", {}) if isinstance(ews.get("metrics", {}), dict) else {}
    enriched = {
        **state,
        "ews_variance": _last_metric(metrics.get("variance"), default=0.0),
        "ews_autocorr": _last_metric(metrics.get("autocorr"), default=0.0),
    }
    return [float(enriched.get(key, 0.0)) for key in _STATE_KEYS]


def _last_metric(value: Any, default: float) -> float:
    if value is None:
        return default
    arr = np.asarray(value, dtype=float).reshape(-1)
    if arr.size == 0:
        return default
    return float(arr[-1])
