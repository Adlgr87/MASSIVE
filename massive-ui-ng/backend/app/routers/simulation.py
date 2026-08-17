"""Simulation router — engine dispatch + narrative translation + run history.

Each engine adapter normalizes its output into the same shape:
``summary`` (opinion_inicial, opinion_final, delta_total, polarizacion_media,
regla_dominante, neutro, rango), ``series`` (time series for charts) and
``meta`` (engine facts). The template narrator then translates that into
natural language; an LLM narration is attempted in ``/api/explain`` when a
provider is configured.

Endpoints:
  - POST /api/simulate          — synchronous run
  - POST /api/simulate/stream   — SSE variant with progress events
  - POST /api/explain           — re-narrate a stored run
  - GET  /api/runs              — run history
  - GET  /api/runs/{run_id}     — full stored payload, narrated on demand
  - DELETE /api/runs/{run_id}   — remove a run
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any

import numpy as np
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse

from backend.app.llm_chat import chat_completion, resolve_provider
from backend.app.llm_prompts import build_narrator_messages
from backend.app.models.dto_ui import (
    ExplainRequest,
    ExplainResponse,
    Highlight,
    RunListItem,
    SimulateRequest,
    SimulateResponse,
)
from backend.app.narrative import build_narrative
from backend.app.run_store import RunStore
from backend.app.security import get_api_key

log = logging.getLogger("massive.ui_ng.simulation")

router = APIRouter(tags=["simulation"], dependencies=[Depends(get_api_key)])


def get_run_store(request: Request) -> RunStore:
    return request.app.state.run_store


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _jsonable(value: Any) -> Any:
    """Recursively convert numpy types to JSON-friendly Python types."""
    if isinstance(value, dict):
        return {str(k): _jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(v) for v in value]
    if isinstance(value, np.ndarray):
        return _jsonable(value.tolist())
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _series_from_scalar_history(history: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "t": [h.get("_paso", i) for i, h in enumerate(history)],
        "opinion": [h.get("opinion") for h in history],
        "propaganda": [h.get("propaganda") for h in history],
        "confianza": [h.get("confianza") for h in history],
        "regla": [h.get("_regla") for h in history],
        "regla_nombre": [h.get("_regla_nombre") for h in history],
        "razon": [h.get("_razon") for h in history],
    }


def _ews_flags_from_history(history: list[dict[str, Any]]) -> dict[str, Any]:
    for h in reversed(history):
        flags = h.get("_ews_flags")
        if flags:
            return _jsonable(flags)
    return {}


# ---------------------------------------------------------------------------
# Engine adapters
# ---------------------------------------------------------------------------


def _run_scalar(req: SimulateRequest) -> dict[str, Any]:
    estado = req.estado_inicial or {"opinion": 0.5, "propaganda": 0.6, "confianza": 0.5}
    estado.setdefault("opinion", 0.5)
    estado.setdefault("propaganda", 0.6)
    estado.setdefault("confianza", 0.5)
    cfg = dict(req.config)
    if req.seed is not None:
        cfg["seed"] = req.seed

    scientific_report: dict[str, Any] | None = None
    if req.scientific:
        from massive_core.scientific_runner import run_scientific_simulation

        result = run_scientific_simulation(
            estado,
            escenario=req.escenario,
            pasos=req.pasos,
            config=cfg,
            scientific_config={"enable_scientific_report": True},
            verbose=False,
        )
        history = result.history
        summary = dict(result.summary or {})
        if result.scientific_report is not None:
            scientific_report = result.scientific_report.to_dict()
    else:
        from services.simulation_service import run_scalar_simulation

        out = run_scalar_simulation(
            estado, escenario=req.escenario, pasos=req.pasos, config=cfg, verbose=False
        )
        history, summary = out["history"], out["summary"]

    meta: dict[str, Any] = {
        "neutro": summary.get("neutro", 0.5),
        "rango": summary.get("rango", "[0, 1]"),
    }
    scientific_report = scientific_report or {}
    scientific_report["ews_flags"] = _ews_flags_from_history(history)
    return {
        "summary": _jsonable(summary),
        "scientific_report": _jsonable(scientific_report),
        "series": _jsonable(_series_from_scalar_history(history)),
        "meta": meta,
        "proveedor": cfg.get("proveedor", "heurístico"),
    }


def _run_energy(req: SimulateRequest) -> dict[str, Any]:
    from energy_runner import run_energy_simulation

    overrides = {
        k: req.config[k]
        for k in ("temperature", "lambda_social", "eta")
        if k in req.config
    }
    n_agents = req.n_agents or 50
    out = run_energy_simulation(
        user_goal="escenario general de dinámica social",
        n_agents=n_agents,
        steps=req.pasos,
        connectivity=req.connectivity,
        range_type=req.range_type,
        seed=req.seed if req.seed is not None else 42,
        config_overrides=overrides or None,
    )
    history = out["history"]
    series = {
        "t": [h["_paso"] for h in history],
        "opinion": [h["mean_opinion"] for h in history],
        "std_opinion": [h["std_opinion"] for h in history],
    }
    archetype = out.get("archetype_info") or {}
    meta = {
        "n_agents": n_agents,
        "range_type": req.range_type,
        "archetype": archetype.get("archetype", "custom"),
        "temperature": out.get("config_used", {}).get("dynamics", {}).get("temperature"),
        "lambda_social": out.get("config_used", {}).get("dynamics", {}).get("lambda_social"),
    }
    return {
        "summary": _jsonable(out["summary"]),
        "scientific_report": None,
        "series": _jsonable(series),
        "meta": meta,
        "proveedor": "heurístico",
    }


def _run_multilayer(req: SimulateRequest) -> dict[str, Any]:
    from multilayer_engine import MultilayerEngine

    n_agents = req.n_agents or 100
    seed = req.seed if req.seed is not None else 42
    weights = tuple(req.layer_weights or (0.4, 0.3, 0.3))
    engine = MultilayerEngine(N=n_agents, seed=seed, layer_weights=weights)
    history = engine.run(steps=req.pasos)

    means = [float(np.mean(x[:, 0])) for x in history]
    stds = [float(np.std(x[:, 0])) for x in history]
    pols = [float(np.mean(np.abs(x[:, 0]))) for x in history]
    coop = [float(np.mean(x[:, 1])) for x in history] if history[0].shape[1] > 1 else None

    summary = {
        "opinion_inicial": means[0],
        "opinion_final": means[-1],
        "delta_total": means[-1] - means[0],
        "media": float(np.mean(means)),
        "desviacion": float(np.std(means)),
        "polarizacion_media": float(np.mean(pols)),
        "pasos": req.pasos,
        "regla_dominante": "multilayer_langevin",
        "neutro": 0.0,
        "rango": "[-1, 1]",
    }
    landscape = engine.get_landscape()
    meta = {
        "n_agents": n_agents,
        "layer_weights": list(weights),
        "landscape": _jsonable(landscape.get("summary", landscape)),
    }
    series = {
        "t": list(range(len(history))),
        "opinion": means,
        "std_opinion": stds,
        "polarization": pols,
    }
    if coop:
        series["cooperation"] = coop
    return {
        "summary": summary,
        "scientific_report": None,
        "series": _jsonable(series),
        "meta": meta,
        "proveedor": "heurístico",
    }


def _run_massive(req: SimulateRequest) -> dict[str, Any]:
    from massive_engine import MassiveSimEngine

    n_agents = req.n_agents or 10_000
    seed = req.seed if req.seed is not None else 42
    engine = MassiveSimEngine(
        N=n_agents,
        M=None,
        seed=seed,
        quantize=req.quantize,
        event_driven=req.event_driven,
    )
    result = engine.run(steps=req.pasos)
    opinion_history = np.asarray(result["opinion_history"], dtype=float)
    active_history = np.asarray(result["active_history"], dtype=float)
    summary = {
        "opinion_inicial": float(opinion_history[0]),
        "opinion_final": float(result["mean_opinion"]),
        "delta_total": float(result["mean_opinion"]) - float(opinion_history[0]),
        "polarizacion_media": float(result["polarization"]),
        "pasos": req.pasos,
        "regla_dominante": "super_agents_langevin",
        "neutro": 0.0,
        "rango": "[-1, 1]",
    }
    meta = {
        "n_agents": int(result["n_agents"]),
        "n_clusters": int(result["n_clusters"]),
        "memory_savings_pct": float(result.get("memory_savings_pct", 0.0)),
        "steps_per_second": float(result.get("steps_per_second", 0.0)),
        "elapsed_seconds": float(result.get("elapsed_seconds", 0.0)),
        "gpu_backend": result.get("gpu_backend", "numpy"),
        "strategies_active": result.get("strategies_active", []),
        "active_history": active_history.tolist(),
    }
    series = {
        "t": list(range(len(opinion_history))),
        "opinion": opinion_history.tolist(),
        "active_fraction": active_history.tolist(),
    }
    return {
        "summary": summary,
        "scientific_report": None,
        "series": _jsonable(series),
        "meta": meta,
        "proveedor": "heurístico",
    }


_ADAPTERS = {
    "scalar": _run_scalar,
    "energy": _run_energy,
    "multilayer": _run_multilayer,
    "massive": _run_massive,
}


# ---------------------------------------------------------------------------
# Shared execution (synchronous endpoint and SSE stream)
# ---------------------------------------------------------------------------


def _execute(req: SimulateRequest, store: RunStore) -> SimulateResponse:
    """Run the adapter, build the narrative, persist and return the response."""
    adapter = _ADAPTERS.get(req.engine)
    if adapter is None:
        raise HTTPException(status_code=400, detail=f"unknown engine: {req.engine}")
    from backend.app.metrics import registry

    registry.inc("simulations_total", {"engine": req.engine})
    try:
        out = adapter(req)
    except Exception as exc:  # noqa: BLE001
        log.exception("simulation failed for engine=%s", req.engine)
        raise HTTPException(status_code=500, detail="simulation failed") from exc

    mode = (
        "llm"
        if out.get("proveedor", "heurístico") not in ("heurístico", "", None)
        else "heuristic"
    )
    narrative, highlights = build_narrative(
        engine=req.engine,
        summary=out["summary"],
        scientific_report=out["scientific_report"],
        series=out["series"],
        meta=out["meta"],
        language=req.language,
        audience=req.audience,
        mode=mode,
    )

    payload: dict[str, Any] = {
        "engine": req.engine,
        "mode": mode,
        "language": req.language,
        "summary": out["summary"],
        "scientific_report": out["scientific_report"],
        "series": out["series"],
        "meta": out["meta"],
    }
    run_id = store.put(payload)

    return SimulateResponse(
        run_id=run_id,
        engine=req.engine,
        mode=mode,
        language=req.language,
        summary=out["summary"],
        scientific_report=out["scientific_report"],
        series=out["series"],
        narrative=narrative,
        highlights=highlights,
        meta=out["meta"],
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/api/simulate", response_model=SimulateResponse)
def api_simulate(req: SimulateRequest, store: RunStore = Depends(get_run_store)) -> SimulateResponse:
    """Run a simulation on the chosen engine and translate the results."""
    return _execute(req, store)


@router.post("/api/simulate/stream")
def api_simulate_stream(req: SimulateRequest, store: RunStore = Depends(get_run_store)) -> StreamingResponse:
    """SSE variant: progress events while the engine runs, then the full result.

    Events: ``status`` (queued/running), ``progress`` (elapsed seconds),
    ``done`` (full SimulateResponse), ``error``.
    """
    if req.engine not in _ADAPTERS:
        raise HTTPException(status_code=400, detail=f"unknown engine: {req.engine}")

    def gen():
        yield _sse("status", {"state": "queued", "engine": req.engine})
        holder: dict[str, Any] = {}
        errors: list[str] = []

        def work() -> None:
            try:
                holder["result"] = _execute(req, store)
            except HTTPException as exc:
                holder["http_error"] = exc
            except Exception as exc:  # noqa: BLE001
                log.exception("streamed simulation failed")
                errors.append(str(exc))

        thread = threading.Thread(target=work, daemon=True)
        thread.start()
        t0 = time.monotonic()
        while thread.is_alive():
            yield _sse(
                "progress",
                {"state": "running", "elapsed": round(time.monotonic() - t0, 1)},
            )
            time.sleep(0.35)
        thread.join()

        if "http_error" in holder:
            yield _sse("error", {"detail": holder["http_error"].detail})
            return
        if errors:
            yield _sse("error", {"detail": "simulation failed"})
            return
        yield _sse("done", holder["result"].model_dump())

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/api/explain", response_model=ExplainResponse)
def api_explain(req: ExplainRequest, store: RunStore = Depends(get_run_store)) -> ExplainResponse:
    """Re-narrate a stored run for a different audience/language.

    Uses an LLM when a provider is configured; otherwise the deterministic
    template narrator (which can never hallucinate).
    """
    payload = store.get(req.run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="run not found")

    cfg = resolve_provider()
    llm_enabled = cfg["configured"] or cfg["provider"] == "ollama"
    mode: str = "template"
    narrative = ""
    highlights: list[Highlight] = []

    if llm_enabled:
        summary = payload["summary"]
        series = payload["series"]
        report = payload.get("scientific_report") or {}
        data_snippet = {
            "summary": summary,
            "scientific": {
                k: report[k]
                for k in ("stability_label", "spectral_radius", "max_real_eigenvalue")
                if k in report
            },
            "trajectory": {
                "t": (series.get("t") or [])[:80],
                "opinion": (series.get("opinion") or [])[:80],
            },
        }
        try:
            text = chat_completion(
                build_narrator_messages(data_snippet, req.language, req.audience),
                temperature=0.3,
                max_tokens=900,
            )
            if text:
                narrative = text.strip()
                mode = "llm"
        except Exception as exc:  # noqa: BLE001
            log.warning("LLM narration failed: %s", exc)

    _, highlights = build_narrative(
        engine=payload["engine"],
        summary=payload["summary"],
        scientific_report=payload.get("scientific_report"),
        series=payload["series"],
        meta=payload["meta"],
        language=req.language,
        audience=req.audience,
        mode=payload.get("mode", "heuristic"),
    )
    if not narrative:
        narrative, highlights = build_narrative(
            engine=payload["engine"],
            summary=payload["summary"],
            scientific_report=payload.get("scientific_report"),
            series=payload["series"],
            meta=payload["meta"],
            language=req.language,
            audience=req.audience,
            mode=payload.get("mode", "heuristic"),
        )

    return ExplainResponse(
        run_id=req.run_id,
        language=req.language,
        audience=req.audience,
        narrative=narrative,
        highlights=highlights,
        mode=mode,
    )


@router.get("/api/runs", response_model=list[RunListItem])
def api_runs(store: RunStore = Depends(get_run_store)) -> list[RunListItem]:
    """List stored runs (most recent first)."""
    items: list[RunListItem] = []
    for entry in store.list():
        summary = entry.get("summary") or {}
        headline = entry.get("headline") or (
            f"{entry['engine']}: {summary.get('opinion_inicial', 0):+.2f} → "
            f"{summary.get('opinion_final', 0):+.2f}"
        )
        items.append(RunListItem(
            run_id=entry["run_id"],
            engine=entry["engine"],
            language=entry.get("language", "es"),
            headline=headline,
            final_opinion=summary.get("opinion_final"),
            dominant_rule=summary.get("regla_dominante"),
            mode=entry.get("mode", "heuristic"),
        ))
    return items


@router.get("/api/runs/{run_id}", response_model=SimulateResponse)
def api_run_detail(
    run_id: str,
    request: Request,
    language: str = "es",
    audience: str = "general",
    store: RunStore = Depends(get_run_store),
) -> SimulateResponse:
    """Return the full stored payload of one run, narrated on demand."""
    payload = store.get(run_id)
    if payload is None:
        raise HTTPException(status_code=404, detail="run not found")
    lang = language if language in ("es", "en") else "es"
    aud = audience if audience in ("general", "tecnico") else "general"
    narrative, highlights = build_narrative(
        engine=payload["engine"],
        summary=payload["summary"],
        scientific_report=payload.get("scientific_report"),
        series=payload["series"],
        meta=payload["meta"],
        language=lang,
        audience=aud,
        mode=payload.get("mode", "heuristic"),
    )
    return SimulateResponse(
        run_id=run_id,
        engine=payload["engine"],
        mode=payload.get("mode", "heuristic"),
        language=lang,
        summary=payload["summary"],
        scientific_report=payload.get("scientific_report"),
        series=payload["series"],
        narrative=narrative,
        highlights=highlights,
        meta=payload["meta"],
    )


@router.delete("/api/runs/{run_id}")
def api_run_delete(run_id: str, store: RunStore = Depends(get_run_store)) -> dict:
    """Delete a stored run."""
    if not store.delete(run_id):
        raise HTTPException(status_code=404, detail="run not found")
    return {"deleted": run_id}
