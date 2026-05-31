"""Temporal forecast engine (analytical + Monte Carlo modes)."""

from __future__ import annotations

import logging
import math
from statistics import median
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field

from empirical_config import MASSIVE_EMPIRICAL_MASTER
from simulator import DEFAULT_CONFIG

from .temporal_config import TemporalConfig

log = logging.getLogger("massive")
_VELOCITY_LOOKBACK_WINDOW = 8


class ForecastResult(BaseModel):
    """Unified output for temporal forecasts."""

    model_config = {"extra": "forbid"}

    p_event: float = Field(..., ge=0.0, le=1.0)
    steps_to_event: int | None = Field(default=None, ge=1)
    days_to_event: int | None = Field(default=None, ge=1)
    confidence: str | None = None
    p_ci_low: float | None = Field(default=None, ge=0.0, le=1.0)
    p_ci_high: float | None = Field(default=None, ge=0.0, le=1.0)
    median_steps: int | None = Field(default=None, ge=1)
    median_days: int | None = Field(default=None, ge=1)
    n_runs: int | None = Field(default=None, ge=1)
    mode: Literal["analytical", "monte_carlo"]


def _sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _extract_ews(simulation_state: dict) -> tuple[float, float, float]:
    ews = simulation_state.get("ews", {}) if isinstance(simulation_state, dict) else {}
    metrics = ews.get("metrics", {}) if isinstance(ews, dict) else {}

    variance = metrics.get("variance", [0.0])
    autocorr = metrics.get("autocorr", [0.0])
    skewness = metrics.get("skewness", [0.0])

    var_v = float(np.mean(np.atleast_1d(variance)))
    ac_v = float(np.mean(np.atleast_1d(autocorr)))
    sk_v = float(np.mean(np.abs(np.atleast_1d(skewness))))
    return var_v, ac_v, sk_v


def _extract_series(simulation_state: dict) -> list[float]:
    if not isinstance(simulation_state, dict):
        return []
    if "historial" in simulation_state and isinstance(simulation_state["historial"], list):
        return [float(h.get("opinion", 0.0)) for h in simulation_state["historial"] if isinstance(h, dict)]
    if "opinions" in simulation_state and isinstance(simulation_state["opinions"], list):
        return [float(v) for v in simulation_state["opinions"]]
    if "opinion" in simulation_state:
        return [float(simulation_state["opinion"])]
    return []


def _event_threshold(temporal_config: TemporalConfig, simulation_state: dict) -> float:
    if temporal_config.event_type in {"viral_online", "protest_campaign"}:
        return 0.70
    if temporal_config.event_type in {"policy_adoption", "cultural_shift"}:
        return 0.60
    return float(simulation_state.get("event_threshold", 0.65))


def _compute_analytical(
    simulation_state: dict,
    temporal_config: TemporalConfig,
) -> ForecastResult:
    var_v, ac_v, sk_v = _extract_ews(simulation_state)

    temporal_block = MASSIVE_EMPIRICAL_MASTER.get("temporal", {})
    cycle_speed = float(temporal_block.get("CICLO_ATENCION", {}).get("value", 0.42))
    trust_elasticity = abs(float(temporal_block.get("ELASTICIDAD_CONFIANZA", {}).get("value", -0.25)))

    beta0 = -1.20
    beta_var = 2.10
    beta_autocorr = 1.65 + (0.35 * cycle_speed)
    beta_skew = 1.35 + (0.25 * trust_elasticity)

    score = beta0 + beta_var * var_v + beta_autocorr * ac_v + beta_skew * sk_v
    p_event = float(np.clip(_sigmoid(score), 0.0, 1.0))

    series = _extract_series(simulation_state)
    threshold = _event_threshold(temporal_config, simulation_state)

    steps_to_event = None
    days_to_event = None
    if len(series) >= 2:
        velocity = float(np.mean(np.diff(series[-min(_VELOCITY_LOOKBACK_WINDOW, len(series)):])))
        current = float(series[-1])
        if velocity > 1e-6 and current < threshold:
            est_steps = int(math.ceil((threshold - current) / velocity))
            if est_steps > 0:
                steps_to_event = est_steps
                days_to_event = est_steps * temporal_config.step_duration_days

    if p_event >= 0.75:
        confidence = "high"
    elif p_event >= 0.45:
        confidence = "medium"
    else:
        confidence = "low"

    return ForecastResult(
        p_event=p_event,
        steps_to_event=steps_to_event,
        days_to_event=days_to_event,
        confidence=confidence,
        mode="analytical",
    )


def _wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total <= 0:
        return 0.0, 0.0
    p = successes / total
    denom = 1.0 + (z * z / total)
    centre = p + (z * z / (2.0 * total))
    spread = z * math.sqrt((p * (1.0 - p) / total) + (z * z / (4.0 * total * total)))
    low = max(0.0, (centre - spread) / denom)
    high = min(1.0, (centre + spread) / denom)
    return float(low), float(high)


def _compute_monte_carlo(
    simulation_state: dict,
    temporal_config: TemporalConfig,
    *,
    n_runs: int = 200,
    random_seed: int | None = None,
) -> ForecastResult:
    n_runs = max(1, int(n_runs))
    rng = np.random.default_rng(random_seed)

    series = _extract_series(simulation_state)
    current = float(series[-1]) if series else float(simulation_state.get("opinion", 0.5))
    if len(series) >= 2:
        drift = float(np.mean(np.diff(series[-min(_VELOCITY_LOOKBACK_WINDOW, len(series)):])))
    else:
        drift = float(simulation_state.get("drift", 0.0))

    cfg = simulation_state.get("config", {}) if isinstance(simulation_state, dict) else {}
    ruido_base = float(cfg.get("ruido_base", DEFAULT_CONFIG["ruido_base"]))
    ruido_desconf = float(cfg.get("ruido_desconfianza", DEFAULT_CONFIG["ruido_desconfianza"]))
    confianza = float(simulation_state.get("confianza", 0.5))
    noise_std = max(0.001, ruido_base + ruido_desconf * (1.0 - confianza))

    threshold = _event_threshold(temporal_config, simulation_state)
    steps_horizon = temporal_config.n_steps

    hit_steps: list[int] = []
    successes = 0
    for _ in range(n_runs):
        x = current
        hit = None
        for step in range(1, steps_horizon + 1):
            x = float(np.clip(x + drift + rng.normal(0.0, noise_std), -1.0, 1.0))
            if x >= threshold:
                hit = step
                break
        if hit is not None:
            successes += 1
            hit_steps.append(hit)

    p_event = successes / n_runs
    ci_low, ci_high = _wilson_interval(successes, n_runs)

    med_steps = int(median(hit_steps)) if hit_steps else None
    med_days = med_steps * temporal_config.step_duration_days if med_steps is not None else None

    return ForecastResult(
        p_event=float(np.clip(p_event, 0.0, 1.0)),
        p_ci_low=ci_low,
        p_ci_high=ci_high,
        median_steps=med_steps,
        median_days=med_days,
        n_runs=n_runs,
        mode="monte_carlo",
    )


def forecast(
    simulation_state: dict,
    temporal_config: TemporalConfig,
    mode: Literal["analytical", "monte_carlo"] = "analytical",
    **kwargs,
) -> ForecastResult:
    """Runs temporal risk forecasting over a simulation state snapshot."""
    if mode == "analytical":
        return _compute_analytical(simulation_state, temporal_config)
    if mode == "monte_carlo":
        return _compute_monte_carlo(
            simulation_state,
            temporal_config,
            n_runs=int(kwargs.get("n_runs", 200)),
            random_seed=kwargs.get("random_seed"),
        )
    raise ValueError(f"Unsupported forecast mode: {mode}")
