"""Walk-forward / rolling-origin validation helpers for short series."""

from __future__ import annotations

from typing import Callable, Iterator

import numpy as np


def rolling_origin_splits(
    series: np.ndarray,
    min_train: int = 4,
    horizon: int = 1,
) -> Iterator[tuple[np.ndarray, np.ndarray]]:
    """
    Yield (train, test) windows for walk-forward validation.

    train grows by one step each fold; test is the next ``horizon`` points.
    """
    y = np.asarray(series, dtype=float).ravel()
    n = len(y)
    if n < min_train + horizon:
        return
    for end in range(min_train, n - horizon + 1):
        yield y[:end], y[end : end + horizon]


def walk_forward_scores(
    series: np.ndarray,
    predict_fn: Callable[[np.ndarray, int], np.ndarray],
    min_train: int = 4,
    horizon: int = 1,
) -> dict[str, float]:
    """
    Evaluate a forecaster with rolling-origin MAE / RMSE.

    Args:
        series: 1-D observations.
        predict_fn: ``predict(train, horizon) -> preds``.
        min_train: Minimum training length.
        horizon: Forecast horizon per fold.
    """
    maes: list[float] = []
    rmses: list[float] = []
    for train, test in rolling_origin_splits(series, min_train=min_train, horizon=horizon):
        pred = np.asarray(predict_fn(train, horizon), dtype=float).ravel()
        if pred.shape != test.shape:
            pred = pred[: len(test)]
        err = pred - test
        maes.append(float(np.mean(np.abs(err))))
        rmses.append(float(np.sqrt(np.mean(err ** 2))))
    if not maes:
        return {"n_folds": 0, "mae": float("nan"), "rmse": float("nan")}
    return {
        "n_folds": len(maes),
        "mae": float(np.mean(maes)),
        "rmse": float(np.mean(rmses)),
    }
