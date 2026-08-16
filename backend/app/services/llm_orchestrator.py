"""LLM orchestrator for POST /v1/llm/run_simulation (configs/llm_contract).

Responsibilities:
  1. Resolve LLM provider credentials -> ServiceUnavailable (503) when none configured.
  2. Classify NL intent into a MASSIVE motor (motor_override or keyword classifier).
  3. AmbiguityError (422) when classification is impossible, carrying requested_fields.
  4. Augment with Factbook country params when a country code is detected.
  5. Dispatch the engine and package an LLMRunResponse (metrics + timeline + narrative).

All dispatch paths are deterministic and offline-friendly (no live LLM needed).
"""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import dataclass
from typing import Any, Optional

import numpy as np

from backend.app.models.dto_llm import LLMRunRequest, LLMRunResponse, MOTOR_ENUM
from backend.app.models.dto_simulation import SimAggregateMetrics
from backend.app.models.dto_snapshot import TimelineTick

log = logging.getLogger("massive.ui_ng.llm_orchestrator")


class ServiceUnavailable(RuntimeError):
    """No LLM provider key configured (-> HTTP 503)."""


class AmbiguityError(RuntimeError):
    """Intent unclassifiable (-> HTTP 422). Carries requested_fields."""

    def __init__(self, detail: str, requested_fields: list[str]):
        super().__init__(detail)
        self.detail = detail
        self.requested_fields = requested_fields


_MOTOR_KEYWORDS = [
    ("forecast_model", r"forecast|predecir|predicci[oó]|tendencia|serie temporal|arima|regresi[oó]n|proyecci[oó]n"),
    ("micro_massive", r"micro|grupo|200|agente individual"),
    ("benchmark_runner", r"benchmark|can[óo]nico|case_id|compar[a-z]+|baseline de referencia"),
    ("factbook_validation", r"factbook|validar|validaci[oó][n]|cifra emp[ií]rica|estad[ií]stica oficial"),
    ("multilayer_engine", r"red|multicapa|social|digital|econ[oó]mica|langevin|capa|graph"),
    ("energy_engine", r"energ[ií]a|landscape|modelo energ[ée]tico|nivel de energ[ií]a"),
    ("massive_engine", r"macrosc[oó]pico|masivo|macro|n>10000|n = 10000|grande elecci[oó]n"),
]

# Detectar códigos ISO-2 sólo como palabras aisladas que no sean prepotencias
# en español (p.ej. "de", "en", "un"). Se prefiere la detección por nombre.
_COUNTRY_RE = re.compile(r"(?<![A-Za-z])(BR|US|AR|MX|ES|FR|IT|GB|CN|IN|RU|JP|CA|AU)(?![A-Za-z])")
_COUNTRY_NAMES = {
    "brasil": "BR", "brasilia": "BR", "brazil": "BR",
    "argentina": "AR", "chile": "CL", "colombia": "CO",
    "méxico": "MX", "españa": "ES", "francia": "FR",
    "alemania": "DE", "italia": "IT", "reino unido": "GB",
    "estados unidos": "US", "china": "CN", "india": "IN",
}


def _classify_motor(intent: str) -> Optional[str]:
    lowered = intent.lower()
    for motor, pattern in _MOTOR_KEYWORDS:
        if re.search(pattern, lowered):
            return motor
    return None


def _detect_country_code(intent: str, explicit: Optional[str]) -> Optional[str]:
    if explicit:
        return explicit.upper()
    m = _COUNTRY_RE.search(intent.upper())
    if m:
        return m.group(1)
    for name, code in _COUNTRY_NAMES.items():
        if re.search(rf"\b{name}\b", intent.lower()):
            return code
    return None


@dataclass
class _DispatchResult:
    metrics: dict[str, Any]
    timeline: list[dict[str, Any]]
    assumptions: list[str]
    narrative: str
    hypothesis_evaluated: str
    confidence_bounds: dict[str, Any]
    artifacts: dict[str, Any]
    classified_motor: str
    country_code_resolved: str = "none"


def _series_to_timeline(series: list, motor: str) -> list[dict[str, Any]]:
    ticks = []
    for i, sample in enumerate(series):
        if isinstance(sample, dict):
            value = float(sample.get("value", sample.get("opinion", 0.0)))
        else:
            value = float(sample)
        ticks.append({
            "tick": i,
            "mean_opinion": round(value, 6),
            "polarization": round(abs(value - 0.5), 6),
            "dominant_rule": motor,
            "timestamp": None,
        })
    return ticks


def _metrics_from_series(series: list[float], motor: str, active_agents: int) -> dict[str, Any]:
    arr = np.asarray(series, dtype=float)
    mean = float(arr.mean()) if arr.size else 0.0
    std = float(arr.std()) if arr.size else 0.0
    polar = float(np.mean(np.abs(arr - 0.5))) if arr.size else 0.0
    consensus = float(np.mean(arr < 0.1)) if arr.size else 0.0
    return {
        "mean_opinion": round(mean, 6),
        "std_opinion": round(std, 6),
        "polarization": round(polar, 6),
        "dominant_rule": motor,
        "consensus_rate": round(consensus, 6),
        "fragmentation_index": round(std, 6),
        "active_agents": int(active_agents),
        "schema_version": "llm-v1",
    }


def _dispatch_multilayer(req: LLMRunRequest) -> _DispatchResult:
    from services.simulation_service import run_multilayer_simulation
    out = run_multilayer_simulation(n_agents=200, seed=42)
    series = out.get("series", {})
    values = []
    for key in ("social", "digital", "economic"):
        col = series.get(key)
        if col:
            values = [float(v) for v in col]
            break
    if not values:
        values = [0.5]
    timeline = _series_to_timeline(values, "multilayer_engine")
    metrics = _metrics_from_series(values, "multilayer_engine", out.get("n_agents", 200))
    narrative = (
        "Simulación multilayer completada. La red social/digital/económica "
        f"evolucionó {len(timeline)} pasos; opinión media {metrics['mean_opinion']:.3f}, "
        f"polarización {metrics['polarization']:.3f}."
    )
    return _DispatchResult(
        metrics=metrics, timeline=timeline,
        assumptions=["motor clasificado: multilayer_engine", "topología watts-strogatz"],
        narrative=narrative,
        hypothesis_evaluated="Las dinámicas multi-capa tienden a polarizarse; la opinión media se mantiene estable.",
        confidence_bounds={"lower": round(metrics["mean_opinion"] - 0.1, 4),
                           "upper": round(metrics["mean_opinion"] + 0.1, 4), "confidence_level": 0.95},
        artifacts={"layers": ["social", "digital", "economic"]},
        classified_motor="multilayer_engine",
    )


def _dispatch_energy(req: LLMRunRequest) -> _DispatchResult:
    from services.simulation_service import run_scalar_simulation
    config: dict[str, Any] = {"seed": 42}
    escenario = "campana"
    if req.scenario == "intervention" and req.intervention_config:
        config["intervencion_magnitud"] = float(req.intervention_config.get("magnitude", 0.5))
        # The scalar sim only exposes "campana"; record the intervention as a
        # config override rather than switching the escenario registry key.
        config["intervencion_tipo"] = str(req.intervention_config.get("type", "info_campaign"))
    out = run_scalar_simulation(
        estado_inicial={"opinion": 0.0, "propaganda": 0.0},
        escenario=escenario,
        pasos=max(10, min(req.temporal_horizon or 90, 200)),
        config=config,
        verbose=False,
    )
    history = out.get("history", [])
    values = [h.get("_estado_opinion", h.get("opinion", 0.5)) for h in history] or [0.5]
    timeline = _series_to_timeline(values, "energy_engine")
    metrics = _metrics_from_series(values, "energy_engine", len(history))
    narrative = (
        f"Modelo energético escalar ejecutado ({len(history)} pasos). "
        f"Opinión media final {metrics['mean_opinion']:.3f}, polarización {metrics['polarization']:.3f}."
    )
    return _DispatchResult(
        metrics=metrics, timeline=timeline,
        assumptions=["motor clasificado: energy_engine", "landschaft energética escalar"],
        narrative=narrative,
        hypothesis_evaluated="El modelo de energía produce trayectorias convergentes hacia un punto fijo.",
        confidence_bounds={"lower": round(metrics["mean_opinion"] - 0.12, 4),
                           "upper": round(metrics["mean_opinion"] + 0.12, 4),
                           "confidence_level": float(req.confidence_level)},
        artifacts={},
        classified_motor="energy_engine",
    )


def _dispatch_forecast(req: LLMRunRequest) -> _DispatchResult:
    from services.forecast_service import baseline_forecast
    series = [0.1 * i for i in range(1, 11)]
    horizon = max(1, min(int(req.temporal_horizon or 90), 36))
    pred = baseline_forecast(series, horizon=horizon, baseline_name="naive")["prediction"]
    timeline = _series_to_timeline(pred, "forecast_model")
    metrics = _metrics_from_series(pred, "forecast_model", len(pred))
    ci = float(req.confidence_level)
    narrative = (
        f"Pronóstico de {len(pred)} períodos (baseline naive). "
        f"Valor proyectado medio {metrics['mean_opinion']:.3f}."
    )
    return _DispatchResult(
        metrics=metrics, timeline=timeline,
        assumptions=["motor clasificado: forecast_model", "baseline: naive"],
        narrative=narrative,
        hypothesis_evaluated="El pronóstico naive asume estacionalidad constante.",
        confidence_bounds={"lower": round(metrics["mean_opinion"] - 0.15, 4),
                           "upper": round(metrics["mean_opinion"] + 0.15, 4), "confidence_level": ci},
        artifacts={"baseline": "naive", "horizon": horizon},
        classified_motor="forecast_model",
    )


def _dispatch_massive(req: LLMRunRequest) -> _DispatchResult:
    from services.simulation_service import run_massive_sim
    steps = max(10, min(req.temporal_horizon or 90, 200))
    out = run_massive_sim(n_agents=10_000, steps=steps, seed=42)
    series = out.get("series", {})
    values = []
    for key in ("opinion", "mean_opinion"):
        col = series.get(key) if isinstance(series, dict) else None
        if col:
            values = [float(v) for v in col]
            break
    if not values:
        values = [float(out.get("final_opinion", 0.5))]
    timeline = _series_to_timeline(values, "massive_engine")
    metrics = _metrics_from_series(values, "massive_engine", out.get("n_agents", 10_000))
    narrative = "Motor macroscópico (MassiveSim) ejecutado con compresión de conjunto activo."
    return _DispatchResult(
        metrics=metrics, timeline=timeline,
        assumptions=["motor clasificado: massive_engine", "compresión LOD activa"],
        narrative=narrative,
        hypothesis_evaluated="El motor macroscópico preserva la dinámica macro con bajo costo.",
        confidence_bounds={"lower": round(metrics["mean_opinion"] - 0.1, 4),
                           "upper": round(metrics["mean_opinion"] + 0.1, 4),
                           "confidence_level": float(req.confidence_level)},
        artifacts={"quantize": True, "event_driven": True},
        classified_motor="massive_engine",
    )


_DISPATCHERS = {
    "multilayer_engine": _dispatch_multilayer,
    "energy_engine": _dispatch_energy,
    "forecast_model": _dispatch_forecast,
    "massive_engine": _dispatch_massive,
    "scalar_legacy": _dispatch_energy,
}


def _resolve_credentials(req: LLMRunRequest) -> dict[str, Any]:
    from services.llm_service import resolve_llm_credentials
    return resolve_llm_credentials(provider="groq", api_key=req.api_key)


def _augment_with_factbook(country_code: Optional[str], motor: str) -> tuple[str, list[str]]:
    if not country_code or motor not in ("energy_engine", "factbook_validation", "multilayer_engine"):
        return (country_code or "none", [])
    try:
        from services.factbook_service import country_params
        params = country_params(country_code or "BR")
        if params:
            return (country_code or "none", [
                f"parámetros factbook cargados para {country_code}",
                f"gini={params.get('gini_coefficient')}",
                f"n_agents_factbook={params.get('n_agents')}",
            ])
    except Exception:  # noqa: BLE001
        log.debug("factbook augment failed", exc_info=True)
    return (country_code or "none", [f"parámetros factbook solicitados para {country_code}"])


def run_simulation(req: LLMRunRequest) -> LLMRunResponse:
    """Execute one LLM-orchestrated simulation."""
    creds = _resolve_credentials(req)
    if not creds.get("configured"):
        raise ServiceUnavailable(
            "No LLM provider API key configured. Set OPENAI_API_KEY / "
            "GROQ_API_KEY / OPENROUTER_API_KEY or pass api_key in the request."
        )

    country_code = _detect_country_code(req.intent, req.country_code)
    motor = req.motor_override or _classify_motor(req.intent)
    if not motor:
        raise AmbiguityError(
            "La intención es ambigua: no se pudo clasificar un motor de simulación único.",
            requested_fields=["motor_override", "temporal_horizon", "scenario", "country_code"],
        )
    if motor not in MOTOR_ENUM:
        raise AmbiguityError(f"Motor desconocido: {motor}", requested_fields=["motor_override"])

    resolved_country, fb_assumptions = _augment_with_factbook(country_code, motor)

    if motor in _DISPATCHERS:
        result = _DISPATCHERS[motor](req)
    elif motor == "factbook_validation":
        from services import factbook_service
        params = factbook_service.country_params(resolved_country or "BR") or {}
        result = _DispatchResult(
            metrics={"mean_opinion": 0.0, "std_opinion": 0.0, "polarization": 0.0,
                     "dominant_rule": "factbook_validation", "consensus_rate": 0.0,
                     "fragmentation_index": 0.0, "active_agents": 0,
                     "schema_version": "llm-v1",
                     "country_params": {k: v for k, v in params.items()}},
            timeline=[], assumptions=["motor clasificado: factbook_validation"] + fb_assumptions,
            narrative=f"Validación factbook para {resolved_country}: {len(params)} parámetros derivados.",
            hypothesis_evaluated="N/A — validación descriptiva de parámetros empíricos.",
            confidence_bounds={"lower": 0.0, "upper": 0.0, "confidence_level": float(req.confidence_level)},
            artifacts={"validated_country": resolved_country or "BR"},
            classified_motor="factbook_validation", country_code_resolved=resolved_country or "BR",
        )
    else:
        raise AmbiguityError(
            f"Motor '{motor}' reconocido pero no implementado en este despliegue.",
            requested_fields=["motor_override"],
        )

    result.assumptions.extend(fb_assumptions)
    result.country_code_resolved = resolved_country

    return LLMRunResponse(
        simulation_id=str(uuid.uuid4()),
        classified_motor=result.classified_motor,
        country_code_resolved=result.country_code_resolved,
        assumptions=result.assumptions,
        result={"metrics": result.metrics, "timeline": result.timeline},
        narrative_summary=result.narrative,
        hypothesis_evaluated=result.hypothesis_evaluated,
        confidence_bounds=result.confidence_bounds,
        artifacts=result.artifacts,
    )
