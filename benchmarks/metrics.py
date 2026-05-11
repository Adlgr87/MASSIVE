"""Evaluation metrics for PVU-BS benchmark.

All functions operate on 1-D numpy arrays.

Metrics
-------
mae          : Mean Absolute Error
rmse         : Root Mean Squared Error
mape         : Mean Absolute Percentage Error (robust, skips near-zero actuals)
directional_accuracy : fraction of correct sign predictions
dm_test      : Diebold–Mariano test statistic and p-value (two-sided)
holm_bonferroni : Holm–Bonferroni correction for a list of p-values
"""
from __future__ import annotations

import math
from typing import Sequence

import numpy as np
from scipy import stats as _scipy_stats


# ── point forecast metrics ────────────────────────────────────────────────────

def mae(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Mean Absolute Error."""
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    return float(np.mean(np.abs(y_true - y_pred)))


def rmse(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Root Mean Squared Error."""
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    return float(np.sqrt(np.mean((y_true - y_pred) ** 2)))


def mape(y_true: np.ndarray, y_pred: np.ndarray, eps: float = 1e-3) -> float:
    """Robust MAPE: skips timesteps where |y_true| < eps.

    Returns NaN if all actuals are near zero.
    """
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    mask = np.abs(y_true) >= eps
    if not mask.any():
        return float("nan")
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)


def directional_accuracy(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Fraction of timesteps where predicted direction matches actual direction.

    Direction is the sign of the first difference.  The metric is computed
    on the *changes* (length n-1), not the levels.
    """
    y_true, y_pred = np.asarray(y_true, float), np.asarray(y_pred, float)
    if len(y_true) < 2:
        return float("nan")
    true_dir = np.sign(np.diff(y_true))
    pred_dir = np.sign(np.diff(y_pred))
    return float(np.mean(true_dir == pred_dir))


# ── Diebold–Mariano test ──────────────────────────────────────────────────────

def dm_test(
    y_true: np.ndarray,
    y_pred_a: np.ndarray,
    y_pred_b: np.ndarray,
    h: int = 1,
) -> tuple[float, float]:
    """Two-sided Diebold–Mariano test: model A vs model B.

    Uses squared-error loss.  Returns (DM statistic, p-value).
    H0: equal predictive accuracy.  H1: A ≠ B.

    Parameters
    ----------
    y_true   : actual values
    y_pred_a : forecasts from model A (MASSIVE)
    y_pred_b : forecasts from baseline B
    h        : forecast horizon (for variance correction)
    """
    y_true = np.asarray(y_true, float)
    ea = (y_true - np.asarray(y_pred_a, float)) ** 2
    eb = (y_true - np.asarray(y_pred_b, float)) ** 2
    d = ea - eb
    n = len(d)
    if n < 2:
        return float("nan"), float("nan")

    d_bar = d.mean()
    # Harvey, Leybourne & Newbold (1997) variance with lag h-1 autocovariances
    gamma0 = np.var(d, ddof=0)
    gamma_sum = 0.0
    for k in range(1, h):
        gamma_sum += (1 - k / h) * np.cov(d[k:], d[:-k], ddof=0)[0, 1]
    var_d = (gamma0 + 2 * gamma_sum) / n
    if var_d <= 0:
        return float("nan"), float("nan")

    dm_stat = d_bar / math.sqrt(var_d)
    p_value = float(2 * _scipy_stats.t.sf(abs(dm_stat), df=n - 1))
    return float(dm_stat), p_value


# ── Multiple-comparison correction ───────────────────────────────────────────

def holm_bonferroni(p_values: Sequence[float]) -> list[float]:
    """Return Holm–Bonferroni adjusted p-values (same order as input).

    The adjusted p-value for rank i (1-indexed, sorted ascending) is:
        p_adj_i = min(p_i * (n - i + 1), 1)
    with the constraint that p_adj is non-decreasing.
    """
    n = len(p_values)
    if n == 0:
        return []
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    adjusted = [0.0] * n
    running_max = 0.0
    for rank, (orig_idx, p) in enumerate(indexed):
        adj = min(p * (n - rank), 1.0)
        running_max = max(running_max, adj)
        adjusted[orig_idx] = running_max
    return adjusted


# ── Aggregate helper ──────────────────────────────────────────────────────────

def compute_all_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    """Return a dict of all point-forecast metrics."""
    return {
        "mae": mae(y_true, y_pred),
        "rmse": rmse(y_true, y_pred),
        "mape": mape(y_true, y_pred),
        "directional_accuracy": directional_accuracy(y_true, y_pred),
    }
