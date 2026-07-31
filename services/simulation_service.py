"""Simulation service — UI/API-facing wrapper around core simulators."""

from __future__ import annotations

from typing import Any

from simulator import DEFAULT_CONFIG, resumen_historial, simular


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
