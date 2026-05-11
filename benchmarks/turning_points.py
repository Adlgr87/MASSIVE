"""Turning-point detection and scoring for PVU-BS benchmark.

A "turning point" is a local extremum in the polarization time series P(t).
The scorer compares detected turning points in predictions vs ground truth.

Usage
-----
    from benchmarks.turning_points import detect, score_turning_points
    events_true = detect(y_true)
    events_pred = detect(y_pred)
    result = score_turning_points(events_true, events_pred, n=len(y_true))
"""
from __future__ import annotations

import numpy as np


def detect(
    series: np.ndarray,
    order: int = 2,
    min_prominence: float = 0.02,
) -> np.ndarray:
    """Detect turning-point indices in *series* using local extrema.

    A point ``i`` is a turning point if it is a local maximum **or** minimum
    with respect to its ``order`` neighbours on each side, and the absolute
    difference from each neighbour is at least ``min_prominence``.

    Parameters
    ----------
    series          : 1-D array of polarization values
    order           : number of neighbour steps to compare (window half-width)
    min_prominence  : minimum absolute height difference from any neighbour

    Returns
    -------
    1-D integer array of turning-point indices (sorted).
    """
    s = np.asarray(series, float)
    n = len(s)
    if n < 2 * order + 1:
        return np.array([], dtype=int)

    indices = []
    for i in range(order, n - order):
        window = s[i - order : i + order + 1]
        centre = s[i]
        is_max = centre == window.max() and (centre - window.min()) >= min_prominence
        is_min = centre == window.min() and (window.max() - centre) >= min_prominence
        if is_max or is_min:
            indices.append(i)

    return np.array(indices, dtype=int)


def score_turning_points(
    true_indices: np.ndarray,
    pred_indices: np.ndarray,
    n: int,
    tolerance: int = 3,
) -> dict[str, float]:
    """Compute precision, recall, F1 and mean timing error for turning points.

    A predicted turning point is a *true positive* if it falls within
    ±``tolerance`` steps of any ground-truth turning point (each GT point
    matched at most once).

    Parameters
    ----------
    true_indices : 1-D int array of ground-truth turning point indices
    pred_indices : 1-D int array of predicted turning point indices
    n            : total length of the series (used for context only)
    tolerance    : maximum allowed timing offset for a match (timesteps)

    Returns
    -------
    dict with keys: precision, recall, f1, mean_timing_error, n_true, n_pred
    """
    true_idx = list(true_indices)
    pred_idx = list(pred_indices)

    matched_gt: set[int] = set()
    tp = 0
    timing_errors: list[float] = []

    for p in pred_idx:
        best_dist = tolerance + 1
        best_gt = -1
        for i, t in enumerate(true_idx):
            d = abs(p - t)
            if d <= tolerance and d < best_dist and i not in matched_gt:
                best_dist = d
                best_gt = i
        if best_gt >= 0:
            tp += 1
            matched_gt.add(best_gt)
            timing_errors.append(float(best_dist))

    precision = tp / len(pred_idx) if pred_idx else float("nan")
    recall = tp / len(true_idx) if true_idx else float("nan")
    if precision + recall > 0:
        f1 = 2 * precision * recall / (precision + recall)
    else:
        f1 = 0.0
    mean_te = float(np.mean(timing_errors)) if timing_errors else float("nan")

    return {
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "mean_timing_error": mean_te,
        "n_true": len(true_idx),
        "n_pred": len(pred_idx),
    }
