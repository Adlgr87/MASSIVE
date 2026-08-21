"""Unit coverage for the canonical ``services/llm_orchestrator``.

Covers intent→motor classification for every contract family, motor-override
precedence, country detection, offline (no-LLM) dispatch, and seed
reproducibility. Hermetic: provider keys cleared — no network calls.

Regression note (2026-08-20): the previous revision targeted a divergent
``classified_motor`` contract from a UI-NG draft (never wired into the
``/v1`` router). This version targets ``services/llm_orchestrator.py``
directly, which implements contract v1.1.0.
"""

from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from services.llm_orchestrator import (  # noqa: E402
    _detect_country,
    classify_motor,
    run_llm_simulation,
)

_PROVIDER_KEY_VARS = ("GROQ_API_KEY", "OPENAI_API_KEY", "OPENROUTER_API_KEY")


@pytest.fixture(autouse=True)
def _hermetic(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in _PROVIDER_KEY_VARS:
        monkeypatch.delenv(var, raising=False)


# ---------------------------------------------------------------- classification


@pytest.mark.parametrize(
    ("intent", "expected"),
    [
        ("Estrategia inversa para reducir la polarización", "social_architect"),
        ("Paisaje de energía social y desigualdad", "energy_engine"),
        ("Predecir la viralidad de un contenido", "forecast"),
        ("Simula millones de agentes a gran escala masivo", "massive_engine"),
        ("Analiza familias de futuros de un grupo pequeño", "micro_massive"),
        ("Corre el benchmark offline", "benchmark_offline"),
        ("Validar contra datos reales", "factbook_validation"),
        ("Dinámica de opinión social en una red", "multilayer_engine"),
    ],
)
def test_classify_motor_families(intent: str, expected: str):
    motor, _ambiguities = classify_motor(intent)
    assert motor == expected, f"intent={intent!r} classified as {motor}, expected {expected}"


def test_classify_motor_override_takes_precedence():
    motor, ambiguities = classify_motor("lo que sea", "energy_engine")
    assert motor == "energy_engine"
    assert ambiguities == []


def test_classify_motor_invalid_override_falls_back_to_rules():
    # An unknown override is ignored (DTO layer rejects it earlier with 422).
    motor, _ = classify_motor("Dinámica de opinión en una red", "not_a_motor")
    assert motor == "multilayer_engine"


def test_classify_motor_reports_missing_country_as_ambiguity():
    _motor, ambiguities = classify_motor("Dinámica de opinión en una red")
    assert "country" in ambiguities


# ------------------------------------------------------------ country detection


@pytest.mark.parametrize(
    ("intent", "expected"),
    [
        ("opinión en brasil", "Brazil"),
        ("méxico en crisis", "Mexico"),
        ("estados unidos", "United States"),  # Spanish alias resolves to canonical name
        ("un país inventado zzx", None),
    ],
)
def test_detect_country(intent: str, expected: str | None):
    assert _detect_country(intent) == expected


# ------------------------------------------------------------- offline dispatch


@pytest.mark.parametrize(
    "motor",
    ["multilayer_engine", "massive_engine", "micro_massive", "energy_engine"],
)
def test_run_llm_simulation_offline_dispatch(motor: str):
    """Without provider keys the orchestrator must still dispatch engines
    using documented defaults (LLM-optional degradation)."""
    result = run_llm_simulation("Simula la dinámica", motor=motor, simulation_steps=10, seed=7)
    assert set(result) >= {
        "sim_id",
        "motor",
        "config",
        "summary",
        "narrative",
        "results",
        "assumptions",
        "factbook_params",
    }
    assert result["motor"] == motor
    assert result["results"]["motor"] == motor
    assert result["sim_id"].startswith("sim_")


def test_run_llm_simulation_requires_intent():
    with pytest.raises(ValueError):
        run_llm_simulation("")


def test_run_llm_simulation_seed_reproducibility():
    """Same seed → identical abridged timeline (regression guard for RNG fixes)."""
    kwargs = {
        "intent": "Simula la dinámica de opinión en una red",
        "simulation_steps": 15,
        "seed": 42,
    }
    a = run_llm_simulation(**kwargs)
    b = run_llm_simulation(**kwargs)
    ta = [(p["tick"], p["mean_opinion"], p["polarization"]) for p in a["results"]["timeline"]]
    tb = [(p["tick"], p["mean_opinion"], p["polarization"]) for p in b["results"]["timeline"]]
    assert ta == tb
    assert ta, "timeline should not be empty for multilayer dispatch"


def test_run_llm_simulation_unknown_motor_falls_back_to_classification():
    """Unknown overrides are ignored at orchestrator level (the /v1 DTO layer
    rejects them earlier with 422) — fallback keeps the pipeline running."""
    result = run_llm_simulation("Dinámica de opinión en una red", motor="not_a_motor")
    assert result["motor"] == "multilayer_engine"
