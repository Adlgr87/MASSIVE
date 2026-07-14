"""Simulation service — UI/API-facing wrapper around core simulators."""

from __future__ import annotations

from typing import Any

from simulator import DEFAULT_CONFIG, simular, resumen_historial


def run_scalar_simulation(
    estado_inicial: dict[str, Any] | None = None,
    *,
    escenario: str = "campana",
    pasos: int = 50,
    config: dict[str, Any] | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Run legacy scalar ``simular`` and return history + summary."""
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
    """Run MultilayerEngine via service boundary."""
    from multilayer_engine import MultilayerEngine

    engine = MultilayerEngine(N=n_agents, seed=seed, layer_weights=layer_weights)
    history = engine.run(steps=steps)
    return {
        "landscape": engine.get_landscape(),
        "n_steps": len(history) - 1,
        "n_agents": n_agents,
    }
