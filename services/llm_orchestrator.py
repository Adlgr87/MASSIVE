"""LLM Orchestrator Service — `services.llm_orchestrator`.

Single entrypoint used by ``POST /v1/llm/run_simulation``. This module wires
together the MASSIVE-LLM contract (intent → motor), the LLM wizard layer
(natural-language → structured config), Factbook augmentation (country params),
engine dispatch, and result narration (result → narrative summary).

Design notes
------------
* **No hard LLM dependency.** The LLM (wizard_config / narrate) is only invoked
  when ``provider``/``api_key`` is resolvable or the caller explicitly requests
  it via ``llm``. When absent, the orchestrator either (a) proceeds with
  documented defaults for the dispatched engine, or (b) raises a ``503`` when
  the flow is inherently LLM-driven and cannot fall back.
* **Contract validation.** Motor classification is driven *directly* from the
  ``supported_flows`` and ``llm_guidelines`` sections of
  ``configs/llm_contract/massive_llm_contract.json`` (loaded via
  ``services.llm_service`` patterns), keeping a single source of truth.
* **Factbook augmentation is lazy** — only called when ``country`` is present.
* **All engines reused in-place** from the service layer to avoid divergence.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any, cast

from services.factbook_service import country_params as _factbook_params
from services.llm_service import resolve_llm_credentials, wizard_config

log = logging.getLogger("massive.services.llm_orchestrator")

# Default step counts per contract "assumption_defaults".
_DEFAULT_STEPS = {
    "energy_engine": 100,
    "social_architect": 100,
    "forecast": 14,  # interpreted as days for viral_online
    "multilayer_engine": 50,
    "massive_engine": 50,
}


def _load_contract() -> dict[str, Any]:
    """Load the MASSIVE-LLM contract from the canonical config path."""
    import json

    env_path = os.getenv("MASSIVE_CONTRACT_PATH")
    candidates = []
    if env_path:
        candidates.append(env_path)
    candidates.extend(
        [
            "configs/llm_contract/massive_llm_contract.json",
            os.path.join(
                os.path.dirname(__file__),
                "..",
                "configs",
                "llm_contract",
                "massive_llm_contract.json",
            ),
            os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "configs",
                "llm_contract",
                "massive_llm_contract.json",
            ),
        ]
    )
    for c in candidates:
        c = os.path.normpath(c)
        if os.path.isfile(c):
            try:
                with open(c, encoding="utf-8") as fh:
                    return json.load(fh)
            except Exception as exc:
                log.warning("Could not load contract from %s (%s)", c, exc)
    log.warning("MASSIVE-LLM contract not found; using inline defaults")
    return {}


# ---------------------------------------------------------------------------
# Intent classification
# ---------------------------------------------------------------------------


def classify_motor(intent: str, motor_hint: str | None = None) -> tuple[str, list[str]]:
    """Select the engine family for a given intent.

    Mirrors the ``llm_guidelines`` rules in the contract. If ``motor_hint`` is
    supplied and valid, it takes precedence.

    Returns:
        ``(motor, ambiguities)`` — motor name and list of fields that should be
        re-confirmed with the user (country, horizon, ...) when absent.
    """
    _VALID_MOTORS = {
        "energy_engine",
        "social_architect",
        "forecast",
        "multilayer_engine",
        "massive_engine",
        "micro_massive",
        "benchmark_offline",
        "factbook_validation",
    }
    if motor_hint and motor_hint in _VALID_MOTORS:
        return motor_hint, []

    it = (intent or "").lower()
    ambiguities: list[str] = []

    # Factbook country detection (contract: mention of a country → augment).
    country = _detect_country(it)
    if country is None:
        ambiguities.append("country")

    if any(
        w in it
        for w in (
            "estrategia inversa",
            "cómo llegar",
            "qué intervención",
            "intervención",
            "reducir polarización",
            "objetivo",
        )
    ):
        return "social_architect", ambiguities
    if any(
        w in it for w in ("energía", "desigualdad", "conflict", "polarización", "conflicto social")
    ):
        return "energy_engine", ambiguities
    if any(
        w in it for w in ("pronosticar", "predecir", "probabilidad", "viral", "2 semanas", "semana")
    ):
        ambiguities.append("temporal_horizon_days")
        return "forecast", ambiguities
    if any(w in it for w in ("múltiples escalas", "millones de agentes", "gran escala", "masivo")):
        return "massive_engine", ambiguities
    if any(w in it for w in ("familias de futuros", "grupo pequeño", "amigos", "organizacional")):
        return "micro_massive", ambiguities
    if any(w in it for w in ("benchmark", "validación ci", "puntos de inflexión")):
        return "benchmark_offline", ambiguities
    if any(w in it for w in ("validar", "validación", "datos reales")):
        return "factbook_validation", ambiguities
    # Default: standard opinion dynamics.
    return "multilayer_engine", ambiguities


def _detect_country(intent: str) -> str | None:
    """Best-effort country detection from an intent string.

    Reuses the contract's ``supported_countries`` list. Returns the canonical
    name as listed in the contract or ``None``. Spanish-localized names
    (Brasil, México, etc.) are matched against a small alias map that resolves
    to the contract's canonical spelling.
    """
    import functools
    import re

    @functools.lru_cache(maxsize=1)
    def _aliases() -> dict[str, str]:
        contract = _load_contract()
        countries = contract.get("supported_countries", [])
        if not countries:
            countries = [
                "US",
                "United States",
                "CH",
                "China",
                "GM",
                "Germany",
                "UK",
                "United Kingdom",
                "FR",
                "France",
                "JP",
                "Japan",
                "IN",
                "India",
                "BR",
                "Brazil",
                "RU",
                "Russia",
                "IT",
                "Italy",
                "CA",
                "Canada",
                "AU",
                "Australia",
                "MX",
                "Mexico",
                "KR",
                "South Korea",
                "SP",
                "Spain",
            ]
        # Spanish aliases → canonical contract spelling.
        span = {
            "brasil": "Brazil",
            "méxico": "Mexico",
            "españa": "Spain",
            "alemania": "Germany",
            "francia": "France",
            "italia": "Italy",
            "rusia": "Russia",
            "china": "China",
            "japón": "Japan",
            "india": "India",
            "canadá": "Canada",
            "reino unido": "United Kingdom",
            "estados unidos": "United States",
        }
        aliases = {c.lower(): c for c in countries}
        aliases.update(span)
        return aliases

    aliases = _aliases()
    lowered = intent.lower()
    # Sort by length desc so multi-word names match before codes.
    for name in sorted(aliases, key=len, reverse=True):
        if re.search(rf"\b{name}\b", lowered):
            return aliases[name]
    return None


# ---------------------------------------------------------------------------
# Config assembly
# ---------------------------------------------------------------------------


def _wizard_translate(intent: str, llm_creds: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Translate *intent* to a flat config dict and assumptions list.

    Uses LLM when configured, otherwise returns sensible defaults keyed by the
    classified motor so non-LLM callers still get a runnable config.
    """
    assumptions: list[str] = []
    config: dict[str, Any] = {}
    if llm_creds.get("configured"):
        try:
            config = wizard_config(
                intent,
                provider=llm_creds["provider"],
                api_key=llm_creds.get("api_key"),
            )
        except Exception as exc:  # pragma: no cover - logged, fall back
            log.warning("wizard_config failed (%s); falling back to defaults", exc)
    # Merge documented defaults for fields the LLM omitted.
    assumptions.append("seed=42 (reproducible)")
    assumptions.append("horizonte por defecto según motor (contract.llm_guidelines)")
    return config, assumptions


def _augment_factbook(
    motor: str,
    country: str | None,
    partial_config: dict[str, Any],
    assumptions: list[str],
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """If *country* is present, enrich config with Factbook-derived params."""
    if not country:
        return partial_config, None
    try:
        fb = _factbook_params(country)
    except Exception as exc:  # pragma: no cover - Factbook may be absent
        log.warning("factbook lookup failed for %s (%s)", country, exc)
        assumptions.append(
            f"country '{country}' mencionado pero Factbook no disponible; usando defaults"
        )
        return partial_config, None

    assumptions.append(
        f"params de Factbook inyectados para {country}: "
        f"n_agents={fb.get('n_agents')}, gini={fb.get('gini_coefficient')}"
    )
    # Let partial_config overrides win for overlapping keys.
    merged = {**fb, **partial_config}
    # Annotate the country so downstream narration/summary can surface it.
    fb_with_country = dict(fb)
    fb_with_country["country"] = country
    return merged, fb_with_country


# ---------------------------------------------------------------------------
# Engine dispatch
# ---------------------------------------------------------------------------


def _dispatch(
    motor: str,
    config: dict[str, Any],
    intent: str,
    country: str | None,
    seed: int,
    steps: int,
    config_overrides: dict[str, Any] | None = None,
    llm_creds: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Dispatch to the correct engine given the classified *motor*."""
    from services.simulation_service import run_scalar_simulation  # local import; lazy

    overrides = config_overrides or {}
    if seed is not None:
        overrides["seed"] = seed

    if motor == "energy_engine":
        from energy_runner import run_energy_simulation

        n_steps = int(steps or config.get("pasos") or _DEFAULT_STEPS.get(motor, 100))
        n_agents = int(config.get("n_agents") or 50)
        connectivity = float(config.get("connectivity") or 0.3)
        range_type = str(config.get("range_type") or "bipolar").strip().lower()
        if range_type not in ("bipolar", "unipolar"):
            range_type = "bipolar"
        energy_overrides = {
            k: v
            for k, v in overrides.items()
            if k in ("temperature", "lambda_social", "eta") and v is not None
        }
        return run_energy_simulation(
            user_goal=intent,
            n_agents=n_agents,
            steps=n_steps,
            connectivity=connectivity,
            range_type=range_type,
            seed=seed if seed is not None else 42,
            config_overrides=energy_overrides,
        )

    if motor in ("multilayer_engine", "massive_engine", "factbook_validation"):
        # Default target engine when intent is opinion-dynamics oriented.
        # Prefer the scalar legacy engine path which is universally available.
        estado = config.get("estado_inicial", {"opinion": 0.0, "propaganda": 0.0})
        escenario = str(config.get("escenario", "campana"))
        sim_cfg = {
            key: val
            for key, val in config.items()
            if key not in ("estado_inicial", "escenario", "pasos", "motor", "country")
            and key
            in (
                "opinion",
                "propaganda",
                "confianza",
                "identidad_grupo",
                "sesgo_confirmacion",
                "homofilia_tasa",
                "ruido_base",
                "regla_sugerida",
            )
            or key in DEFAULT_CONFIG_KEYS
        }
        sim_cfg.update(overrides)
        # Map pasos/steps
        n_steps = int(steps or config.get("pasos", _DEFAULT_STEPS.get(motor, 50)))
        return run_scalar_simulation(
            estado_inicial=estado,
            escenario=escenario,
            pasos=n_steps,
            config=sim_cfg,
        )

    if motor == "social_architect":
        # This flow is LLM-driven (buscar_estrategia_inversa calls setup_client).
        if not (llm_creds or {}).get("configured"):
            raise RuntimeError(
                "social_architect motor requires an LLM API key; "
                "configure GROQ_API_KEY / OPENAI_API_KEY / OPENROUTER_API_KEY"
            )
        from social_architect import buscar_estrategia_inversa

        estado = config.get("estado_inicial", {"opinion": 0.0, "propaganda": 0.0})
        objetivo = config.get("objetivo_usuario", intent)
        estrategia, narrativa, intentos, historial = buscar_estrategia_inversa(
            estado_inicial=estado,
            objetivo_usuario=objetivo,
            max_intentos=int(config.get("max_intentos", 3)),
            config=config.get("config") or {},
            modo_simulacion=config.get("modo_simulacion", "macro"),
            metricas_red=config.get("metricas_red", ""),
        )
        return {
            "estrategia": estrategia,
            "narrativa": narrativa,
            "intentos": intentos,
            "historial": historial,
        }

    if motor == "forecast":
        from forecast.engine import forecast
        from forecast.temporal_config import TemporalConfig

        sim_state = config.get("simulation_state", {})
        temporal_raw = config.get("temporal_config", {})
        if isinstance(temporal_raw, TemporalConfig):
            temporal_cfg = temporal_raw
        elif isinstance(temporal_raw, dict):
            # Translate LLM-oriented fields → TemporalConfig fields.
            # Contract example uses {n_steps, step_duration_days, event_type};
            # TemporalConfig uses time_horizon_days (n_steps is computed).
            defaults = TemporalConfig(step_duration_days=7, time_horizon_days=90).model_dump()
            flat = {k: v for k, v in temporal_raw.items() if k != "n_steps"}
            if "n_steps" in temporal_raw and "time_horizon_days" not in flat:
                step_dur = flat.get("step_duration_days", defaults["step_duration_days"])
                flat["time_horizon_days"] = int(temporal_raw["n_steps"]) * int(step_dur)
            defaults.update(flat)
            temporal_cfg = TemporalConfig(**defaults)
        else:
            temporal_cfg = TemporalConfig(step_duration_days=7, time_horizon_days=90)
        result = forecast(
            sim_state,
            temporal_config=temporal_cfg,
            mode=config.get("mode", "analytical"),
            n_runs=int(config.get("n_runs", 200)),
        )
        return result.model_dump() if hasattr(result, "model_dump") else dict(result)

    if motor == "benchmark_offline":
        from benchmarks import runner as bench_runner

        argv = [
            "--cases",
            "datasets/pvu_cases",
            "--out",
            "reports/validation/ci",
            "--seed",
            str(seed),
        ]
        rc = bench_runner.main(argv)
        return {"return_code": rc, "mode": "offline", "seed": seed}

    if motor == "micro_massive":
        # Streamlit UI is the canonical path; orchestrator returns a stub
        # directing the LLM client to launch the micro-massive UI.
        return {
            "note": "micro_massive requiere la UI Streamlit (/ui/). Dirija al cliente a ese endpoint.",
            "payload": config,
        }

    # Fallback to scalar simulation.
    estado = config.get("estado_inicial", {"opinion": 0.0, "propaganda": 0.0})
    escenario = str(config.get("escenario", "campana"))
    n_steps = int(steps or config.get("pasos", 50))
    return run_scalar_simulation(
        estado_inicial=estado, escenario=escenario, pasos=n_steps, config=overrides or None
    )


# Keys from simulator.DEFAULT_CONFIG that are accepted as flat overrides.
DEFAULT_CONFIG_KEYS = {
    "N",
    "ruido_base",
    "red_type",
    "k",
    "p",
    "alpha_blend",
    "beta_blend",
    "gamma_blend",
    "homofilia_tasa",
    "sesgo_confirmacion",
    "lambda_ruido",
    "lambda_social",
    "temperature",
    "eta",
    "llm_temperature",
    "llm_timeout",
    "seed",
    "mu",
    "sigma",
    "t_max",
    "dt",
}

# Re-import here to avoid circular import at module load.
from simulator import DEFAULT_CONFIG as _DEFAULT_CONFIG  # noqa: E402

DEFAULT_CONFIG_KEYS |= set(_DEFAULT_CONFIG.keys())


# ---------------------------------------------------------------------------
# Narration
# ---------------------------------------------------------------------------


def _narrate(
    results: dict[str, Any],
    llm_creds: dict[str, Any] | None = None,
) -> str:
    """Produce a narrative summary; best-effort (falls back to a template)."""
    if not results:
        return "No se obtuvieron resultados."
    creds = llm_creds or resolve_llm_credentials()
    if creds.get("configured"):
        try:
            from uil_adapter import create_uil_adapter

            provider = creds["provider"]
            key = creds.get("api_key")
            adapter = create_uil_adapter(llm_provider=provider, llm_api_key=key)
            narr = adapter.interpreter.narrate(results)
            if hasattr(narr, "model_dump"):
                d = narr.model_dump()
                return "\n".join(
                    filter(
                        None,
                        [
                            d.get("diagnostico"),
                            d.get("dinamica_clave"),
                            d.get("implicaciones"),
                            *d.get("recomendaciones", []),
                        ],
                    )
                )
            return str(narr)
        except Exception as exc:
            log.warning("narrate failed (%s); using template summary", exc)
    # Fallback deterministic summary.
    summary = results.get("summary") or {}
    mean = summary.get("media") or summary.get("mean_opinion")
    polar = summary.get("polarizacion_media") or summary.get("polarizacion")
    return f"Simulación completada. Opinión media={mean}, " f"polarización={polar}."


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_llm_simulation(
    intent: str,
    *,
    motor: str | None = None,
    country: str | None = None,
    partial_config: dict[str, Any] | None = None,
    llm: dict[str, Any] | None = None,
    simulation_steps: int | None = None,
    seed: int | None = None,
    config_overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run a full LLM-orchestrated MASSIVE simulation from a natural-language intent.

    Pipeline: classify motor → translate NL→config (LLM or defaults) →
    merge partial + Factbook augmentation → dispatch engine → narrate.

    Args:
        intent: Natural-language intent from the user/LLM client.
        motor: Optional engine override (see ``supported_flows``).
        country: Optional country for Factbook augmentation.
        partial_config: Optional structured overrides merged atop the translated config.
        llm: Optional ``{"provider", "model"}`` hint; defaults to env resolution.
        simulation_steps: Optional step-count override.
        seed: Optional RNG seed (default 42).
        config_overrides: Optional extra engine config keys.

    Returns:
        Dict with ``sim_id``, ``motor``, ``config``, ``summary``,
        ``narrative``, ``results``, ``assumptions``, ``factbook_params``.
    """
    if not intent or not isinstance(intent, str):
        raise ValueError("intent (non-empty string) is required")

    provider = (llm or {}).get("provider", os.getenv("PROVIDER", "groq"))
    explicit_key = (llm or {}).get("api_key")
    llm_creds = resolve_llm_credentials(
        provider=provider,
        api_key=explicit_key,
    )

    seed = seed if seed is not None else 42
    assumptions: list[str] = []

    # 0b. Infer country from intent if not explicitly provided (Factbook path).
    if not country:
        country = _detect_country(intent)
        if country:
            assumptions.append(f"country detectado desde la intención: {country}")

    # 1. Classify motor (if not supplied).
    resolved_motor, ambiguities = classify_motor(intent, motor)
    if ambiguities:
        for amb in ambiguities:
            assumptions.append(
                f"campo no especificado por el usuario: {amb} (asumiendo default del contrato)"
            )

    log.info(
        "llm_orchestrator: intent='%s…' motor=%s country=%s", intent[:60], resolved_motor, country
    )

    # 2. Translate NL → config (LLM when available).
    nl_config, _ = _wizard_translate(intent, llm_creds)

    # 3. Merge partial + NL config.
    merged = {**nl_config, **(partial_config or {})}

    # 4. Factbook augmentation.
    merged, factbook_params = _augment_factbook(resolved_motor, country, merged, assumptions)
    # Sanitize any numpy / non-JSON-native values introduced by Factbook or
    # the wizard so the downstream response DTO can always serialize.
    merged = _sanitize_for_json(merged)
    if factbook_params is not None:
        factbook_params = _sanitize_for_json(factbook_params)

    # 5. Resolve step count.
    steps = simulation_steps or merged.get("pasos") or _DEFAULT_STEPS.get(resolved_motor, 50)
    if "pasos" not in merged:
        merged["pasos"] = steps

    # 6. Dispatch engine.
    results = _dispatch(
        resolved_motor,
        merged,
        intent,
        country,
        seed=seed,
        steps=int(steps),
        config_overrides=config_overrides,
        llm_creds=llm_creds,
    )

    # 7. Extract numerical indicators + summary.
    summary = _extract_summary(results, resolved_motor, assumptions, factbook_params)

    # 7.5. Build normalized results envelope with abridged timeline.
    timeline = _extract_timeline(results, resolved_motor)
    final_state = _extract_final_state(results)
    # Sanitize engine payloads (may carry numpy arrays) for DTO serialization.
    results_clean = _sanitize_for_json(results)

    # 8. Narrate.
    narrative = _narrate(results_clean, llm_creds)

    sim_id = f"sim_{uuid.uuid4().hex[:12]}"

    return {
        "sim_id": sim_id,
        "motor": resolved_motor,
        "config": merged,
        "summary": summary,
        "narrative": narrative,
        "results": {
            "sim_id": sim_id,
            "motor": resolved_motor,
            "payload": results_clean,
            "timeline": timeline,
            "final_state": final_state,
        },
        "assumptions": assumptions,
        "factbook_params": factbook_params,
    }


def _extract_final_state(results: dict[str, Any]) -> dict[str, Any] | None:
    """Best-effort extract of a normalized terminal state."""
    if isinstance(results.get("final_state"), dict):
        return dict(results["final_state"])
    summary = results.get("summary")
    if isinstance(summary, dict):
        return {
            "mean_opinion": summary.get("media", summary.get("mean_opinion")),
            "std_opinion": summary.get("desviacion", summary.get("std_opinion")),
            "polarizacion": summary.get("polarizacion_media", summary.get("polarizacion")),
        }
    return None


def _sanitize_for_json(obj: Any) -> Any:
    """Recursively convert numpy scalars/arrays + non-native types to JSON-safe values."""
    try:
        import numpy as np

        _NP_TYPES: tuple[type, ...] = (np.generic,)
    except Exception:  # pragma: no cover - numpy may be absent
        _NP_TYPES = ()

    if isinstance(obj, dict):
        return {k: _sanitize_for_json(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize_for_json(v) for v in obj]
    if _NP_TYPES and isinstance(obj, _NP_TYPES):
        # Narrowed by isinstance against np.generic-derived types; mypy cannot
        # narrow through the runtime tuple, hence the explicit cast.
        return cast(Any, obj).item()
    try:
        import numpy as np

        if isinstance(obj, np.ndarray):
            return [_sanitize_for_json(v) for v in obj.tolist()]
    except Exception:
        pass
    return obj


def _extract_timeline(
    results: dict[str, Any], motor: str, n_points: int = 25
) -> list[dict[str, Any]] | None:
    """Build an abridged timeline (first/last N ticks) from engine history.

    Returns ``None`` when no usable history is present.
    """
    hist = results.get("history")
    if not isinstance(hist, list) or not hist:
        return None
    pts: list[dict[str, Any]] = []
    for idx, item in enumerate(hist):
        if not isinstance(item, dict):
            continue
        # Legacy scalar history has no `_paso`/`tick`; synthesize from index.
        tick = item.get("_paso", item.get("tick"))
        if tick is None:
            tick = idx
        mean = item.get("mean_opinion") or item.get("media") or item.get("opinion")
        pts.append(
            {
                "tick": tick,
                "mean_opinion": mean,
                "polarization": item.get("polarizacion", item.get("polarizacion_media")),
                "active_agents": item.get("active_agents"),
            }
        )
    if not pts:
        return None
    # Abridge if huge.
    if len(pts) > 2 * n_points:
        return pts[:n_points] + pts[-n_points:]
    return pts


def _extract_summary(
    results: dict[str, Any],
    motor: str,
    assumptions: list[str],
    factbook_params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Normalize the varied engine outputs into the contract's ``summary`` shape."""
    # Engine-specific extraction.
    if "summary" in results and isinstance(results["summary"], dict):
        base = dict(results["summary"])
    elif "final_state" in results:
        fs = results["final_state"]
        base = {
            "media": fs.get("mean_opinion", 0.0),
            "polarizacion_media": fs.get("polarizacion", 0.0),
        }
    elif "p_event" in results:
        base = {"p_event": results["p_event"]}
    else:
        base = {}

    # Numerical indicators from contract.llm_output_fields
    indicators = {
        "mean_opinion": base.get("media", base.get("mean_opinion", 0.0)),
        "std_opinion": base.get("desviacion", base.get("std_opinion", 0.0)),
        "polarizacion": base.get("polarizacion_media", base.get("polarizacion", 0.0)),
        "consenso": base.get("consenso", 0.0),
        "delta_total": base.get("delta_total", 0.0),
        "p_event": results.get("p_event"),
        "feasibility_score": (
            results.get("feasibility", {}).get("score")
            if isinstance(results.get("feasibility"), dict)
            else None
        ),
        "n_agents": results.get("n_agents"),
        "n_steps": results.get("n_steps") or results.get("horizon_ticks"),
        "attempts": results.get("attempts"),
    }
    # Drop None values for cleanliness.
    indicators = {k: v for k, v in indicators.items() if v is not None}
    return {
        "motor": motor,
        "indicators": indicators,
        "regla_dominante": base.get("regla_dominante"),
        "factbook_country": _extract_country(factbook_params),
    }


def _extract_country(factbook_params: dict[str, Any] | None) -> str | None:
    """Best-effort extract a country reference from Factbook params."""
    if isinstance(factbook_params, dict) and "country" in factbook_params:
        return factbook_params["country"]
    return None
