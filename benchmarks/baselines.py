"""Baseline forecasters for PVU-BS benchmark.

Each baseline exposes a ``predict(train, horizon)`` method that returns a
1-D numpy array of ``horizon`` forecast values.

Baselines
---------
NaiveBaseline        : last observed value (random-walk / "no-change")
MovingAverageBaseline: mean of the last ``window`` observations
AR1Baseline          : AR(1) fitted by OLS on the training series
RandomRegimeBaseline : random-walk with noise calibrated from training
"""
from __future__ import annotations

import numpy as np


class NaiveBaseline:
    """Persist the last observed value for all forecast steps."""

    name = "naive"

    def predict(self, train: np.ndarray, horizon: int) -> np.ndarray:
        last = float(train[-1])
        return np.full(horizon, last)


class MovingAverageBaseline:
    """Mean of the last *window* training observations."""

    name = "moving_average"

    def __init__(self, window: int = 4):
        self.window = window

    def predict(self, train: np.ndarray, horizon: int) -> np.ndarray:
        w = min(self.window, len(train))
        mean_val = float(np.mean(train[-w:]))
        return np.full(horizon, mean_val)


class AR1Baseline:
    """AR(1) model fitted via OLS: P(t) = phi_0 + phi_1 * P(t-1).

    Iterates the fitted equation for multi-step forecasts.
    """

    name = "ar1"

    def __init__(self) -> None:
        self.phi0 = 0.0
        self.phi1 = 0.0

    def fit(self, train: np.ndarray) -> "AR1Baseline":
        y = train[1:]
        x = train[:-1]
        if len(x) < 2:
            self.phi0 = float(train[-1])
            self.phi1 = 0.0
            return self
        # OLS: [phi0, phi1] = (X^T X)^{-1} X^T y
        X = np.column_stack([np.ones(len(x)), x])
        coeffs, *_ = np.linalg.lstsq(X, y, rcond=None)
        self.phi0, self.phi1 = float(coeffs[0]), float(coeffs[1])
        return self

    def predict(self, train: np.ndarray, horizon: int) -> np.ndarray:
        self.fit(train)
        preds = np.empty(horizon)
        last = float(train[-1])
        for i in range(horizon):
            last = self.phi0 + self.phi1 * last
            preds[i] = last
        return preds


class RandomRegimeBaseline:
    """Random walk with std calibrated from training first-differences.

    Uses a fixed random seed for reproducibility (passed at call time).
    """

    name = "random_regime"

    def predict(
        self,
        train: np.ndarray,
        horizon: int,
        rng: np.random.Generator | None = None,
    ) -> np.ndarray:
        if rng is None:
            rng = np.random.default_rng(42)
        diff_std = float(np.std(np.diff(train))) if len(train) > 1 else 0.01
        last = float(train[-1])
        steps = rng.normal(0, diff_std, size=horizon)
        preds = last + np.cumsum(steps)
        return preds


def get_all_baselines() -> list:
    """Return one instance of each baseline (ready to call .predict on)."""
    return [
        NaiveBaseline(),
        MovingAverageBaseline(window=4),
        AR1Baseline(),
        RandomRegimeBaseline(),
    ]
