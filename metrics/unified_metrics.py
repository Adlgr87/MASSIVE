"""
unified_metrics.py — Single source of truth for MASSIVE social metrics.

All engines in MASSIVE previously computed polarization differently:

    Engine              | Old formula                    | Meaning
    ------------------- | ------------------------------ | -------------------------
    energy_engine.py    | std / half_range               | Normalized dispersion
    multilayer_engine.py| mean(|opinion|)               | Mean abs deviation from 0
    massive_engine.py   | weighted mean(|opinion|)      | Pop-weighted abs deviation
    micro_engine.py     | std(final_opinions)           | Absolute std
    simulator.py        | mean(|opinion - neutral|)     | Avg dist from neutral pt

This module unifies them under the URCC (Unified Reactive Coupling Contract):

    polarization = std(opinions) / half_range

where half_range = (max_val - min_val) / 2. For bipolar [-1, 1] this is 1.0;
for unipolar [0, 1] this is 0.5. This normalises to [0, 1] so polarization
is comparable across range types.

Why std / half_range (not mean(|x|))?
  - std captures *dispersion*, which is what polarization means sociologically
  - mean(|x|) conflates *bias* (systematic lean) with *polarization* (spread)
  - dividing by half_range makes the metric range-independent and bounded [0, 1]
"""

from __future__ import annotations

import numpy as np


def _get_range_bounds(range_type: str = "bipolar") -> tuple[float, float, float]:
    """Return (min_val, max_val, half_range) for the given range type.

    Args:
        range_type: 'bipolar' → [-1, 1], 'unipolar' → [0, 1].

    Returns:
        Tuple of (min, max, half_range).
    """
    if range_type == "bipolar":
        return -1.0, 1.0, 1.0
    return 0.0, 1.0, 0.5


def calculate_polarization(
    opinions: np.ndarray,
    range_type: str = "bipolar",
    neutral: float | None = None,
) -> float:
    """Compute normalized opinion polarization.

    Uses the URCC standard: polarization = std(opinions) / half_range.

    Args:
        opinions: 1-D array of agent opinions in the declared range.
        range_type: 'bipolar' or 'unipolar'.
        neutral:   Deprecated; kept for backward-compat. The mean is used
                   internally because polarization is about dispersion, not
                   distance from a point.

    Returns:
        Polarization index in [0, 1] (0 = perfect consensus, 1 = maximally split).
    """
    del neutral  # accepted but unused; std is shift-invariant
    _, max_val, half_range = _get_range_bounds(range_type)
    if half_range <= 0:
        return 0.0
    std = float(np.std(opinions)) if opinions.size > 0 else 0.0
    pol = std / half_range
    # Clamp to [0, 1]: a std > half_range is possible with pathological clipping
    return float(np.clip(pol, 0.0, 1.0))


def calculate_polarization_index(
    opinions: np.ndarray,
    range_type: str = "bipolar",
) -> float:
    """Alias for :func:`calculate_polarization` (keeps naming consistent
    with benchmarks/io.py and forecast/targets.py conventions)."""
    return calculate_polarization(opinions, range_type)


def calculate_partisanship(
    opinions: np.ndarray,
    neutral: float = 0.0,
    range_type: str = "bipolar",
) -> float:
    """Compute partisan polarization (mean distance from neutral).

    Unlike :func:`calculate_polarization` (which measures dispersion via std),
    partisanship measures how far the group sits from the neutral point.
    This is the metric used by the Social Architect's scoring function —
    when the objective is "despolarizar", high partisanship should score low.

    Args:
        opinions: 1-D array of opinions.
        neutral:  Neutral point (0.0 for bipolar, 0.5 for unipolar).
        range_type: 'bipolar' or 'unipolar'.

    Returns:
        Mean absolute distance from neutral, normalised to [0, 1].
    """
    if opinions.size == 0:
        return 0.0
    min_val, max_val, half_range = _get_range_bounds(range_type)
    if half_range <= 0:
        return 0.0
    partisanship = float(np.mean(np.abs(opinions - neutral))) / half_range
    return float(np.clip(partisanship, 0.0, 1.0))


def calculate_mean_opinion(
    opinions: np.ndarray,
    range_type: str = "bipolar",
) -> float:
    """Compute mean opinion, clipped to valid range.

    Args:
        opinions: 1-D array of opinions.
        range_type: 'bipolar' or 'unipolar'.

    Returns:
        Mean opinion clamped to [min_val, max_val].
    """
    min_val, max_val, _ = _get_range_bounds(range_type)
    if opinions.size == 0:
        _, _, half_range = _get_range_bounds(range_type)
        return min_val + half_range  # neutral point
    return float(np.clip(np.mean(opinions), min_val, max_val))


def calculate_std_opinion(opinions: np.ndarray) -> float:
    """Compute standard deviation of opinions (raw, unbounded)."""
    return float(np.std(opinions)) if opinions.size > 0 else 0.0


def calculate_cooperation(cooperation_values: np.ndarray) -> float:
    """Compute mean cooperation level.

    Args:
        cooperation_values: 1-D array of cooperation scores in [0, 1].

    Returns:
        Mean cooperation in [0, 1].
    """
    if cooperation_values.size == 0:
        return 0.0
    return float(np.clip(np.mean(cooperation_values), 0.0, 1.0))


def polarization_velocity(
    polarization_history: list[float] | np.ndarray,
    n_steps: int = 5,
) -> float:
    """Compute the rate of change of polarization over the last n steps.

    This is a key reactive signal: when polarization accelerates, the system
    is approaching a bifurcation point and should trigger corrective action.

    Args:
        polarization_history: Time-ordered polarization values.
        n_steps: Window over which to compute the velocity.

    Returns:
        Δpolarization / Δt over the window (positive = polarizing, negative = depolarizing).
    """
    hist = np.asarray(polarization_history, dtype=np.float64).ravel()
    if hist.size < 2:
        return 0.0
    n = min(n_steps, hist.size - 1)
    return float(hist[-1] - hist[-1 - n])


def polarization_gradient(
    opinions: np.ndarray,
    range_type: str = "bipolar",
) -> np.ndarray:
    """Compute the per-agent contribution to polarization.

    Each agent's contribution is how far it is from the mean, normalised.

    Args:
        opinions: 1-D array of opinions.
        range_type: 'bipolar' or 'unipolar'.

    Returns:
        Array of per-agent gradient contributions in [-1, 1].
    """
    _, _, half_range = _get_range_bounds(range_type)
    if opinions.size == 0 or half_range <= 0:
        return np.array([], dtype=np.float64)
    mean_op = float(np.mean(opinions))
    return (opinions - mean_op) / half_range
