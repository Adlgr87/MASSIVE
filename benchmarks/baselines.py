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


class ETSBaseline:
    """Exponential Smoothing (ETS) via statsmodels.

    Uses additive trend/no seasonal (suitable for short social series).
    """

    name = "ets"

    def __init__(self):
        import statsmodels.api as sm  # lazy import
        self.sm = sm

    def predict(self, train: np.ndarray, horizon: int) -> np.ndarray:
        if len(train) < 3:
            return np.full(horizon, float(train[-1]))
        # Simple ETS(A,Ad,N) to avoid overfitting
        model = self.sm.tsa.ExponentialSmoothing(
            train, trend="add", seasonal=None, initialization_method="estimated"
        )
        fit = model.fit(optimized=True)
        fc = fit.forecast(horizon)
        return np.asarray(fc, dtype=float)


class ARIMABaseline:
    """ARIMA(1,1,1) via statsmodels SARIMAX (fallback if fails)."""

    name = "arima"

    def __init__(self):
        import statsmodels.api as sm
        self.sm = sm

    def predict(self, train: np.ndarray, horizon: int) -> np.ndarray:
        if len(train) < 5:
            return np.full(horizon, float(train[-1]))
        try:
            model = self.sm.tsa.SARIMAX(
                train, order=(1, 1, 1), enforce_stationarity=False, enforce_invertibility=False
            )
            fit = model.fit(disp=False)
            fc = fit.forecast(horizon)
            return np.asarray(fc, dtype=float)
        except Exception:
            # Fallback to AR(1)
            return AR1Baseline().predict(train, horizon)


class ThresholdLogisticBaseline:
    """Sigmoid fit on the training window (logistic threshold).

    Fits y = 1 / (1 + exp(-(a*t + b))) on normalized time, then extrapolates.
    """

    name = "threshold_logistic"

    def __init__(self):
        import numpy as _np
        self._np = _np

    def predict(self, train: np.ndarray, horizon: int) -> np.ndarray:
        n = len(train)
        if n < 6:
            return np.full(horizon, float(train[-1]))
        t = self._np.linspace(0, 1, n)
        y = self._np.asarray(train, dtype=float)

        # Simple logistic fit via least squares on logit(y) clipped to (0,1)
        eps = 1e-4
        y_clip = self._np.clip(y, eps, 1 - eps)
        logit = self._np.log(y_clip / (1 - y_clip))
        X = self._np.column_stack([t, self._np.ones(n)])
        a, b = self._np.linalg.lstsq(X, logit, rcond=None)[0]

        # Forecast on t beyond train
        t_future = self._np.linspace(1, 1 + horizon / max(1, n), horizon)
        logit_future = a * t_future + b
        y_future = 1 / (1 + self._np.exp(-logit_future))
        return y_future.astype(float)

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


class RidgeLagsBaseline:
    """Ridge regression with lag features (tabular ML baseline).

    X = [P(t-1), P(t-2), ..., P(t-L)] -> predict P(t)
    Multi-step via recursive forecasting.
    """

    name = "ridge_lags"

    def __init__(self, lags: int = 4, alpha: float = 1.0):
        from sklearn.linear_model import Ridge
        self.Ridge = Ridge
        self.lags = lags
        self.alpha = alpha

    def _build_xy(self, series: np.ndarray):
        X, y = [], []
        for i in range(self.lags, len(series)):
            X.append(series[i - self.lags : i])
            y.append(series[i])
        return np.asarray(X, dtype=float), np.asarray(y, dtype=float)

    def predict(self, train: np.ndarray, horizon: int) -> np.ndarray:
        if len(train) <= self.lags + 1:
            return np.full(horizon, float(train[-1]))
        X, y = self._build_xy(train)
        model = self.Ridge(alpha=self.alpha)
        model.fit(X, y)
        hist = train.copy().astype(float)
        preds = []
        for _ in range(horizon):
            x = hist[-self.lags :]
            yhat = float(model.predict(x.reshape(1, -1))[0])
            preds.append(yhat)
            hist = np.append(hist, yhat)
        return np.asarray(preds, dtype=float)


def get_all_baselines() -> list:
    """Return one instance of each baseline available in this environment.

    Baselines with missing optional dependencies (e.g., statsmodels,
    scikit-learn, torch) are skipped gracefully.
    """
    baselines = [
        NaiveBaseline(),
        MovingAverageBaseline(window=4),
        AR1Baseline(),
        RandomRegimeBaseline(),
    ]
    # Optional: statsmodels-based baselines
    try:
        baselines.append(ETSBaseline())
    except Exception:
        pass
    try:
        baselines.append(ARIMABaseline())
    except Exception:
        pass
    # Optional: sklearn-based baseline
    try:
        baselines.append(RidgeLagsBaseline(lags=4, alpha=1.0))
    except Exception:
        pass
    # Optional: Mamba SSM baseline (requires torch)
    try:
        from mamba_engine import MambaBaseline
        baselines.append(MambaBaseline())
    except Exception:
        pass
    return baselines

