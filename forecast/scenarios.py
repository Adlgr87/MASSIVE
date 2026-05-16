"""Scenario-level utilities for temporal forecast comparisons."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from schemas import StrategyMatrix
from simulator import run_with_schedule

from .engine import ForecastResult, forecast
from .intervention_map import apply_intervention
from .temporal_config import TemporalConfig


class ScenarioSpec(BaseModel):
    """Single scenario definition for comparison runs."""

    model_config = {"extra": "forbid"}

    label: str
    strategy: StrategyMatrix | None = None
    overrides: dict[str, Any] = Field(default_factory=dict)


class ScenarioRow(BaseModel):
    """Row-level result for scenario ranking."""

    model_config = {"extra": "forbid"}

    label: str
    p_event: float = Field(..., ge=0.0, le=1.0)
    days_to_event: int | None = Field(default=None, ge=1)
    forecast: ForecastResult


class ScenarioReport(BaseModel):
    """Scenario comparison report."""

    model_config = {"extra": "forbid"}

    ranked: list[ScenarioRow]
    best_scenario: str
    baseline_delta: float
    min_expected_effect_days: int | None = Field(default=None, ge=1)


class InterventionReport(BaseModel):
    """Specialized report for intervention-plan comparisons."""

    model_config = {"extra": "forbid"}

    p_event_no_intervention: float = Field(..., ge=0.0, le=1.0)
    p_event_best_plan: float = Field(..., ge=0.0, le=1.0)
    min_effect_time_days: int | None = Field(default=None, ge=1)
    feasibility_vs_deadline: bool
    scenario_report: ScenarioReport


def _state_for_strategy(base_state: dict, strategy: StrategyMatrix) -> dict:
    cfg = dict(base_state.get("config", {}))
    hist = run_with_schedule(
        estado_inicial=base_state,
        strategy_schedule=strategy.model_dump(),
        config=cfg,
        verbose=False,
    )
    return {
        "historial": hist,
        "opinion": hist[-1].get("opinion", base_state.get("opinion", 0.5)) if hist else base_state.get("opinion", 0.5),
        "confianza": base_state.get("confianza", 0.5),
        "config": cfg,
    }


def compare_scenarios(
    base_state: dict,
    temporal_config: TemporalConfig,
    scenarios: list[ScenarioSpec],
    mode: Literal["analytical", "monte_carlo"] = "analytical",
    rank_direction: Literal["desc", "asc"] = "desc",
    **kwargs,
) -> ScenarioReport:
    """Runs and ranks multiple scenarios by event probability."""
    if not scenarios:
        raise ValueError("scenarios cannot be empty")

    rows: list[ScenarioRow] = []
    for spec in scenarios:
        state = dict(base_state)
        if spec.overrides:
            state.update(spec.overrides)
        if spec.strategy is not None:
            state = _state_for_strategy(state, spec.strategy)
        if spec.strategy is None and spec.overrides:
            state = apply_intervention(state, Intervention(
                time_start=1,
                time_end=max(1, temporal_config.n_steps),
                model_name="lineal",
                parameters=spec.overrides,
                fase_rationale="scenario override",
            ))

        result = forecast(state, temporal_config, mode=mode, **kwargs)
        rows.append(
            ScenarioRow(
                label=spec.label,
                p_event=result.p_event,
                days_to_event=result.days_to_event or result.median_days,
                forecast=result,
            )
        )

    reverse = rank_direction == "desc"
    ranked = sorted(rows, key=lambda r: r.p_event, reverse=reverse)

    baseline = next((r for r in rows if r.label == "baseline"), ranked[0])
    best = ranked[0]

    effect_days = [r.days_to_event for r in ranked if r.days_to_event is not None]
    min_effect_days = min(effect_days) if effect_days else None

    return ScenarioReport(
        ranked=ranked,
        best_scenario=best.label,
        baseline_delta=float(best.p_event - baseline.p_event),
        min_expected_effect_days=min_effect_days,
    )


def run_intervention_comparison(
    base_state: dict,
    temporal_config: TemporalConfig,
    strategies: list[StrategyMatrix],
    mode: Literal["analytical", "monte_carlo"] = "analytical",
    **kwargs,
) -> InterventionReport:
    """Compares no-intervention baseline against candidate intervention plans."""
    scenario_specs = [ScenarioSpec(label="baseline")]
    for idx, strategy in enumerate(strategies, start=1):
        scenario_specs.append(ScenarioSpec(label=f"plan_{idx}", strategy=strategy))

    report = compare_scenarios(
        base_state=base_state,
        temporal_config=temporal_config,
        scenarios=scenario_specs,
        mode=mode,
        rank_direction="desc",
        **kwargs,
    )

    baseline_row = next(row for row in report.ranked if row.label == "baseline")
    best_row = report.ranked[0]
    min_days = report.min_expected_effect_days

    return InterventionReport(
        p_event_no_intervention=baseline_row.p_event,
        p_event_best_plan=best_row.p_event,
        min_effect_time_days=min_days,
        feasibility_vs_deadline=(min_days is not None and min_days <= temporal_config.time_horizon_days),
        scenario_report=report,
    )
