"""Engine router — ``POST /v1/engine/energy``, ``POST /v1/engine/architect``.

Exposes the energy-landscape engine and the social architect inverse-search
behind a single versioned surface.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import ValidationError

from backend.app.models import (
    ArchitectRequest,
    EngineEnergyRequest,
    MultilayerRequest,
)
from backend.app.security import get_api_key, rate_limit_dependency

router = APIRouter(
    prefix="/engine",
    tags=["engine"],
)


@router.post(
    "/energy",
    name="energy",
    dependencies=[Depends(get_api_key), Depends(rate_limit_dependency)],
)
async def v1_energy(
    request: Request,
    payload: Annotated[EngineEnergyRequest, Body()],
) -> dict[str, Any]:
    """Run the Langevin energy-landscape engine from a user goal.

    Payload fields:
        user_goal: str       (required)
        n_agents: int          (default 50, bounded 1–200 000)
        steps: int             (default 100, bounded 1–10 000)
        connectivity: float    (default 0.3)
        range_type: str        (default ``"bipolar"``)
        seed: int              (default 42)
        config_overrides: dict (optional)
    """
    from energy_runner import run_energy_simulation

    try:
        return run_energy_simulation(
            user_goal=payload.user_goal,
            n_agents=payload.n_agents,
            steps=payload.steps,
            connectivity=payload.connectivity,
            range_type=payload.range_type,
            seed=payload.seed,
            config_overrides=payload.config_overrides,
        )
    except ValidationError:
        raise
    except Exception as _exc:
        import logging

        logging.getLogger(__name__).exception("v1/engine/energy error")
        raise HTTPException(status_code=500, detail="Internal engine error") from _exc


@router.post(
    "/architect",
    name="architect",
    dependencies=[Depends(get_api_key), Depends(rate_limit_dependency)],
)
async def v1_architect(
    request: Request,
    payload: Annotated[ArchitectRequest, Body()],
) -> dict[str, Any]:
    """Social Architect inverse-strategy search.

    Payload fields:
        estado_inicial: dict  – initial simulator state (required).
        objetivo_usuario: str – desired end-state description (required).
        max_intentos: int      (default 3, bounded 1–10)
        config: dict           (optional overrides)
        modo_simulacion: str   (default ``"macro"``)
        metricas_red: str      (optional)
    """
    from social_architect import buscar_estrategia_inversa

    try:
        estrategia, narrativa, intentos, historial = buscar_estrategia_inversa(
            estado_inicial=payload.estado_inicial,
            objetivo_usuario=payload.objetivo_usuario,
            max_intentos=payload.max_intentos,
            config=payload.config,
            modo_simulacion=payload.modo_simulacion,
            metricas_red=payload.metricas_red,
        )
    except HTTPException:
        raise
    except ValidationError:
        raise
    except Exception as _exc:
        import logging

        logging.getLogger(__name__).exception("v1/engine/architect error")
        raise HTTPException(status_code=500, detail="Internal engine error") from _exc

    history = historial if isinstance(historial, list) else []
    return {
        "strategy": estrategia,
        "narrative": narrativa,
        "attempts": intentos,
        "history_summary": history[:5],
        "history_length": len(history),
    }


@router.post(
    "/multilayer",
    name="multilayer",
    dependencies=[Depends(get_api_key), Depends(rate_limit_dependency)],
)
async def v1_multilayer(
    request: Request,
    payload: Annotated[MultilayerRequest, Body()],
) -> dict[str, Any]:
    """Run the multilayer Langevin engine and return its real per-layer series.

    This endpoint exists because the dials with a measurable effect on the model
    were not reachable over HTTP: ``n_agents``, ``steps`` and ``seed`` do not move
    the output, while ``coupling`` — the actual phase dial — and the declared
    coupling matrix were inaccessible.

    Payload fields:
        n_agents: int          (default 500, bounded 2–200 000)
        steps: int             (default 400, bounded 1–10 000)
        seed: int              (default 42)
        dt: float              (default 0.02, bounded to the explicit-Euler limit)
        coupling: float        (default 0.3, bounded 0–5)
        layer_weights: list    (default ``[0.4, 0.3, 0.3]``)
        coupling_gains: dict   (optional) ``"source->target"`` overrides

    Returns:
        Dict with ``landscape``, ``series`` (``opinion`` + real ``layer_signal``
        per layer), ``diagnostics`` and the resolved ``parameters``.
    """
    from services.simulation_service import run_multilayer_simulation

    try:
        return run_multilayer_simulation(
            n_agents=payload.n_agents,
            steps=payload.steps,
            seed=payload.seed,
            layer_weights=tuple(payload.layer_weights),  # type: ignore[arg-type]
            coupling=payload.coupling,
            dt=payload.dt,
            coupling_gains=payload.coupling_gains,
        )
    except HTTPException:
        raise
    except ValidationError:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as _exc:
        import logging

        logging.getLogger(__name__).exception("v1/engine/multilayer error")
        raise HTTPException(status_code=500, detail="internal error") from _exc
