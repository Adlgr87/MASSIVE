from __future__ import annotations

from copy import deepcopy

from forecast import TemporalConfig, forecast, apply_intervention, compare_scenarios
from forecast.scenarios import ScenarioSpec
from massive.core.schemas import Intervention


def _sample_historical() -> list[dict]:
    return [
        {"opinion": 0.30},
        {"opinion": 0.34},
        {"opinion": 0.39},
        {
            "opinion": 0.45,
            "ews": {
                "metrics": {
                    "variance": [0.18],
                    "autocorr": [0.72],
                    "skewness": [0.41],
                },
                "flags": {
                    "high_variance": True,
                    "high_autocorr": True,
                    "high_skewness": False,
                },
            },
        },
    ]


def test_temporal_config_defaults() -> None:
    events = [
        "viral_online",
        "protest_campaign",
        "labor_conflict",
        "electoral_campaign",
        "policy_adoption",
        "cultural_shift",
    ]
    for event in events:
        cfg = TemporalConfig.from_event_type(event)
        assert cfg.event_type == event
        assert cfg.step_duration_days >= 1
        assert cfg.time_horizon_days >= 1
        assert cfg.n_steps >= 1


def test_analytical_forecast_smoke() -> None:
    historial = _sample_historical()
    state = dict(historial[-1])
    state["historial"] = historial
    state["confianza"] = 0.5
    cfg = TemporalConfig.from_event_type("labor_conflict")

    result = forecast(state, cfg, mode="analytical")

    assert 0.0 <= result.p_event <= 1.0
    assert result.mode == "analytical"


def test_monte_carlo_forecast_smoke() -> None:
    historial = _sample_historical()
    state = dict(historial[-1])
    state["historial"] = historial
    state["confianza"] = 0.6
    state["config"] = {"ruido_base": 0.02, "ruido_desconfianza": 0.05}

    cfg = TemporalConfig.from_event_type("protest_campaign")
    result = forecast(state, cfg, mode="monte_carlo", n_runs=10, random_seed=42)

    assert result.mode == "monte_carlo"
    assert 0.0 <= result.p_event <= 1.0
    assert result.p_ci_low is not None and result.p_ci_high is not None
    assert result.p_ci_low <= result.p_event <= result.p_ci_high


def test_scenario_ranking() -> None:
    base_state = {
        "opinion": 0.40,
        "confianza": 0.5,
        "ews": {
            "metrics": {
                "variance": [0.10],
                "autocorr": [0.55],
                "skewness": [0.20],
            }
        },
    }
    cfg = TemporalConfig.from_event_type("labor_conflict")

    scenarios = [
        ScenarioSpec(label="baseline"),
        ScenarioSpec(
            label="high_risk",
            overrides={
                "ews": {
                    "metrics": {
                        "variance": [0.35],
                        "autocorr": [0.85],
                        "skewness": [0.60],
                    }
                }
            },
        ),
    ]

    report = compare_scenarios(base_state, cfg, scenarios, mode="analytical")

    assert report.ranked[0].label == "high_risk"
    assert report.ranked[0].p_event >= report.ranked[-1].p_event


def test_intervention_map_clips() -> None:
    base = {
        "propaganda": 0.5,
        "step_duration_days": 10,
    }
    intervention = Intervention(
        time_start=1,
        time_end=5,
        model_name="contagio_competitivo",
        parameters={
            "propaganda": 3.2,
            "epsilon": -4,
            "competencia": 2.5,
            "tasa": 0.99,
        },
        fase_rationale="test",
    )

    merged = apply_intervention(base, intervention)

    assert merged["propaganda"] == 1.0
    assert 0.1 <= merged["hk_epsilon"] <= 0.8
    assert 0.0 <= merged["competencia_peso"] <= 1.0
    assert 0.0 <= merged["homofilia_tasa"] <= 0.2
    assert merged["step_duration_days"] == 5


def test_apply_intervention_pure() -> None:
    base = {"propaganda": 0.4, "step_duration_days": 7}
    base_copy = deepcopy(base)

    intervention = Intervention(
        time_start=1,
        time_end=2,
        model_name="lineal",
        parameters={"propaganda": 0.8},
        fase_rationale="purity",
    )

    _ = apply_intervention(base, intervention)

    assert base == base_copy
