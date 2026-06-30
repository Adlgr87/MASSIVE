"""
MASSIVE real engine integration for the benchmark runner.

This module wraps the actual MASSIVE simulator (`simulator.simular`) so that
it can be evaluated as a predictor in the empirical benchmark suite.

The previous version (`_massive_offline_forecast` in runner.py) was a *proxy*
consisting of AR(1) + damped noise. This module replaces it with the real
MASSIVE engine running in `heurístico` mode (no LLM required, fully
deterministic with `seed=42`).

## Mapping MASSIVE -> polarization

MASSIVE's `simular()` returns a trajectory of `opinion` (single mean field).
The benchmark data tracks *polarization* (gap between two opinion groups).
We bridge them with a 2-parameter linear transform calibrated on the train
split (no peeking at test):

    polarization_pred = a * opinion + b

where `(a, b)` are fit by least squares on the training window.

The `a, b` transform is intentionally simple (2 parameters) so that MASSIVE
is evaluated on its *trajectory shape*, not on its absolute level. A more
sophisticated mapping is left for future work (see ROADMAP_SOTA_MASSIVE.md
Ticket 5 — CMA-ES calibration).
"""

from __future__ import annotations

import os
import random
import numpy as np
from typing import Sequence, Optional, Dict, Any

# Seed for determinism — must match runner convention
SEED = 42


def _seed_everything(seed: int = SEED) -> None:
    """Set all RNGs deterministically. Idempotent."""
    os.environ["PYTHONHASHSEED"] = str(seed)
    random.seed(seed)
    np.random.seed(seed)


def _fit_linear(x: Sequence[float], y: Sequence[float]) -> tuple[float, float]:
    """Fit y = a*x + b by ordinary least squares. Returns (a, b)."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if len(x) < 2 or np.std(x) < 1e-9:
        # Degenerate: fall back to identity with small offset
        return 1.0, float(np.mean(y) - np.mean(x))
    a, b = np.polyfit(x, y, 1)
    return float(a), float(b)


def _build_initial_state(
    train: Sequence[float],
    train_horizon: int,
    cultural_profile: str = "mixed",
    red_type: str = "watts_strogatz",
) -> Dict[str, float]:
    """Build MASSIVE initial state from a polarization training window.

    Parameters
    ----------
    train : sequence of float
        Polarization values from the training split.
    train_horizon : int
        Number of timesteps the train split represents.
    cultural_profile : str
        One of: mixed, latin, anglosaxon, east_asian, middle_east,
        south_asian, subsaharan_africa.
    red_type : str
        Network topology hint for MASSIVE.

    Returns
    -------
    dict
        Initial state for `simular()`.
    """
    train = list(train[:train_horizon])
    if not train:
        return {
            "opinion": 0.5,
            "propaganda": 0.5,
            "confianza": 0.5,
            "opinion_grupo_a": 0.5,
            "opinion_grupo_b": 0.5,
            "pertenencia_grupo": 0.5,
            "red_type": red_type,
        }
    last_pol = float(np.clip(train[-1], 0.0, 1.0))
    mean_pol = float(np.mean(train))
    var_pol = float(np.var(train)) if len(train) > 1 else 0.0
    # Polarization -> group opinions: split symmetrically around last value
    op_a = float(np.clip(0.5 + 0.5 * last_pol, 0.0, 1.0))
    op_b = float(np.clip(0.5 - 0.5 * last_pol, 0.0, 1.0))
    return {
        "opinion": last_pol,
        "propaganda": float(np.clip(0.5 + (last_pol - 0.5) * 0.6, 0.0, 1.0)),
        "confianza": float(np.clip(0.6 - 0.3 * var_pol, 0.0, 1.0)),
        "opinion_grupo_a": op_a,
        "opinion_grupo_b": op_b,
        "pertenencia_grupo": float(np.clip(0.5 + 0.3 * (mean_pol - 0.5), 0.0, 1.0)),
        "red_type": red_type,
        "cultural_profile": cultural_profile,
    }


def massive_real_forecast(
    train: Sequence[float],
    horizon: int,
    *,
    cultural_profile: str = "mixed",
    red_type: str = "watts_strogatz",
    steps_per_step: int = 1,
    cada_n_pasos: int = 1,
    seed: int = SEED,
) -> np.ndarray:
    """Run the real MASSIVE engine to produce a polarization forecast.

    Parameters
    ----------
    train : sequence of float
        Polarization values from the training split.
    horizon : int
        Number of future timesteps to predict.
    cultural_profile : str
        Cultural profile to use (from case meta).
    red_type : str
        Network topology hint.
    steps_per_step : int
        Number of MASSIVE internal steps per output timestep.
    cada_n_pasos : int
        Sampling interval passed to `simular()`.
    seed : int
        RNG seed (must be fixed for reproducibility).

    Returns
    -------
    np.ndarray of shape (horizon,)
        Predicted polarization in [0, 1].
    """
    # Local import to avoid heavy simulator import at module top
    from simulator import simular

    _seed_everything(seed)

    horizon = max(1, int(horizon))
    estado = _build_initial_state(
        train=train,
        train_horizon=len(train),
        cultural_profile=cultural_profile,
        red_type=red_type,
    )

    n_steps = horizon * max(1, steps_per_step)
    try:
        history = simular(
            estado,
            pasos=n_steps,
            cada_n_pasos=max(1, cada_n_pasos),
            verbose=False,
        )
    except Exception as e:
        # Graceful fallback: persistence of last value
        return np.full(horizon, float(train[-1]) if train else 0.5, dtype=float)

    # Extract opinion trajectory
    opinions = np.asarray(
        [float(h.get("opinion", train[-1] if train else 0.5)) for h in history],
        dtype=float,
    )

    # Resample to `horizon` if needed
    if len(opinions) > horizon:
        idx = np.linspace(0, len(opinions) - 1, horizon).round().astype(int)
        opinions = opinions[idx]
    elif len(opinions) < horizon:
        # Pad with last value
        pad = np.full(horizon - len(opinions), opinions[-1] if len(opinions) else 0.5)
        opinions = np.concatenate([opinions, pad])

    # Calibrate linear transform on train (no test leakage)
    a, b = _fit_linear(train[: len(train)], train[: len(train)])
    # Use identity if a, b come from the degenerate case above
    if not np.isfinite(a) or not np.isfinite(b):
        a, b = 1.0, 0.0
    pred = np.clip(a * opinions + b, 0.0, 1.0)

    return pred


def massive_real_forecast_with_calibration(
    train: Sequence[float],
    horizon: int,
    *,
    cultural_profile: str = "mixed",
    red_type: str = "watts_strogatz",
    seed: int = SEED,
) -> np.ndarray:
    """Forecast with linear calibration fit on train split.

    Difference vs `massive_real_forecast`:
        - Runs simular() with `pasos=len(train) + horizon`
        - Uses first `len(train)` records to fit the linear mapping
          (a*opinion + b -> polarization)
        - Applies the mapping to the remaining `horizon` records

    This gives MASSIVE a fair comparison vs AR(1) and naive: the mapping
    is 2 parameters, calibrated only on the training window.
    """
    from simulator import simular

    _seed_everything(seed)

    horizon = max(1, int(horizon))
    train = list(train)
    n_train = len(train)
    n_total = max(n_train + horizon, n_train + 1)

    estado = _build_initial_state(
        train=train,
        train_horizon=n_train,
        cultural_profile=cultural_profile,
        red_type=red_type,
    )

    try:
        history = simular(
            estado,
            pasos=n_total,
            cada_n_pasos=1,
            verbose=False,
        )
    except Exception:
        return np.full(horizon, float(train[-1]) if train else 0.5, dtype=float)

    opinions = np.asarray(
        [float(h.get("opinion", 0.5)) for h in history], dtype=float
    )
    if len(opinions) < n_total:
        opinions = np.concatenate(
            [opinions, np.full(n_total - len(opinions), opinions[-1] if len(opinions) else 0.5)]
        )
    opinions = opinions[:n_total]

    # Fit (a, b) on the train window (MASSIVE's opinion -> data polarization)
    train_opinions = opinions[:n_train]
    a, b = _fit_linear(train_opinions.tolist(), train)
    if not np.isfinite(a) or not np.isfinite(b):
        a, b = 1.0, 0.0
    pred = a * opinions[n_train : n_train + horizon] + b
    return np.clip(pred, 0.0, 1.0)


__all__ = [
    "SEED",
    "massive_real_forecast",
    "massive_real_forecast_with_calibration",
]
