"""Simulation service — UI/API-facing wrapper around core simulators."""

from __future__ import annotations

import datetime
import logging
import os
import uuid
from pathlib import Path
from typing import Any

from simulator import DEFAULT_CONFIG, resumen_historial, save_checkpoint, simular

log = logging.getLogger("massive.simulation_service")


def run_scalar_simulation(
    estado_inicial: dict[str, Any] | None = None,
    *,
    escenario: str = "campana",
    pasos: int = 50,
    config: dict[str, Any] | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Run the legacy scalar ``simular`` engine and return history + summary.

    Args:
        estado_inicial: Initial state dict (defaults to neutral opinion).
        escenario: Scenario key in the rule registry.
        pasos: Number of simulation steps.
        config: Optional overrides for ``DEFAULT_CONFIG`` (may include ``seed``).
        verbose: Whether to emit step logs.

    Returns:
        Dict with keys ``history``, ``summary``, ``config``, ``escenario``.
    """
    estado = estado_inicial or {"opinion": 0.0, "propaganda": 0.0}
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    history = simular(
        estado,
        escenario=escenario,
        pasos=pasos,
        config=cfg,
        verbose=verbose,
    )
    return {
        "history": history,
        "summary": resumen_historial(history, cfg),
        "config": cfg,
        "escenario": escenario,
    }


def run_multilayer_simulation(
    *,
    n_agents: int = 100,
    steps: int = 50,
    seed: int = 42,
    layer_weights: tuple[float, float, float] = (0.4, 0.3, 0.3),
) -> dict[str, Any]:
    """Run ``MultilayerEngine`` via the service boundary.

    Args:
        n_agents: Population size N.
        steps: Integration steps.
        seed: RNG seed for reproducibility.
        layer_weights: Relative weights of social/digital/economic layers.

    Returns:
        Dict with landscape metrics, step count, and agent count.
    """
    from multilayer_engine import MultilayerEngine

    engine = MultilayerEngine(N=n_agents, seed=seed, layer_weights=layer_weights)
    history = engine.run(steps=steps)
    return {
        "landscape": engine.get_landscape(),
        "n_steps": len(history) - 1,
        "n_agents": n_agents,
    }


def run_massive_sim(
    *,
    n_agents: int = 10_000,
    m_clusters: int | None = None,
    steps: int = 50,
    seed: int = 42,
    quantize: bool = True,
    event_driven: bool = True,
) -> dict[str, Any]:
    """Run ``MassiveSimEngine`` (LOD / event-driven path).

    Args:
        n_agents: Real agent count N.
        m_clusters: Super-agent count M (auto if None).
        steps: Simulation steps.
        seed: RNG seed.
        quantize: Enable uint8 state storage.
        event_driven: Enable sparse active-set updates.

    Returns:
        Result dict from ``MassiveSimEngine.run`` plus memory report.
    """
    from massive_engine import MassiveSimEngine

    engine = MassiveSimEngine(
        N=n_agents,
        M=m_clusters,
        seed=seed,
        quantize=quantize,
        event_driven=event_driven,
    )
    result = engine.run(steps=steps)
    result["memory_report"] = engine.memory_report
    return result


# ── Supported engine identifiers ─────────────────────────────────────
_SUPPORTED_ENGINES = frozenset({"scalar", "multilayer", "massive"})

# Directory where checkpoints are persisted. Configurable via MASSIVE_REPORTS_DIR.
_REPORTS_DIR = Path(os.getenv("MASSIVE_REPORTS_DIR", "reports"))


def run_from_spec(spec: dict[str, Any]) -> dict[str, Any]:
    """Execute a validated ``ResolvedRunSpec`` and return a ``RunReceipt``.

    This is the single authorised entry point for the Execution Gateway agent.
    It dispatches to the correct engine, persists a checkpoint, and always
    returns a structured receipt — whether the run succeeded or failed.

    Args:
        spec: A ``ResolvedRunSpec``-shaped dict with the keys ``engine``,
            ``params``, ``seed``, and optionally ``spec_id``.  The ``params``
            sub-dict is forwarded verbatim to the chosen service function.

    Returns:
        A ``RunReceipt``-shaped dict with ``status``, ``sim_id``,
        ``summary``, ``checkpoint_path``, and ``error``.
    """
    sim_id = "sim-" + str(uuid.uuid4())
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    engine = str(spec.get("engine", "scalar")).lower()
    params: dict[str, Any] = dict(spec.get("params") or {})
    seed: int = int(spec.get("seed", 42))

    # Inject seed into scalar config overrides when using scalar engine
    if engine == "scalar":
        params["config"] = {**(params.get("config") or {}), "seed": seed}

    try:
        if engine == "scalar":
            result = run_scalar_simulation(**params)
        elif engine == "multilayer":
            result = run_multilayer_simulation(seed=seed, **params)
        elif engine == "massive":
            result = run_massive_sim(seed=seed, **params)
        else:
            return {
                "sim_id": sim_id,
                "spec_id": spec.get("spec_id"),
                "status": "failed",
                "started_at": started_at,
                "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "seed_used": seed,
                "engine": engine,
                "summary": None,
                "checkpoint_path": None,
                "error": f"unsupported_engine: {engine!r}. Supported: {sorted(_SUPPORTED_ENGINES)}",
            }

        checkpoint_path_attempted = str(_REPORTS_DIR / f"{sim_id}.json")
        checkpoint_path: str | None = None
        try:
            save_checkpoint(result.get("history") or [], checkpoint_path_attempted)
            checkpoint_path = checkpoint_path_attempted
        except Exception:
            log.warning("Checkpoint write failed for %s", sim_id, exc_info=True)

        return {
            "sim_id": sim_id,
            "spec_id": spec.get("spec_id"),
            "status": "success",
            "started_at": started_at,
            "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "seed_used": seed,
            "engine": engine,
            "summary": result.get("summary"),
            "checkpoint_path": checkpoint_path,
            "error": None,
        }

    except Exception as exc:
        log.exception("run_from_spec failed for sim_id=%s", sim_id)
        return {
            "sim_id": sim_id,
            "spec_id": spec.get("spec_id"),
            "status": "failed",
            "started_at": started_at,
            "finished_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "seed_used": seed,
            "engine": engine,
            "summary": None,
            "checkpoint_path": None,
            "error": type(exc).__name__,
        }
