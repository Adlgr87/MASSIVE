"""Engine router — ``POST /v1/energy``, ``POST /v1/architect``, ``POST /v1/scientific``.

Exposes the energy-landscape engine, the social architect inverse-search,
and the scientific opt-in runner behind a single versioned surface.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request

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
async def v1_energy(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    """Run the Langevin energy-landscape engine from a user goal.

    Payload fields:
        user_goal: str       (required)
        n_agents: int          (default 50)
        steps: int             (default 100)
        connectivity: float    (default 0.3)
        range_type: str        (default ``"bipolar"``)
        seed: int              (default 42)
        config_overrides: dict (optional)
    """
    from energy_runner import run_energy_simulation

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON body required")
    user_goal = payload.get("user_goal")
    if not isinstance(user_goal, str) or not user_goal.strip():
        raise HTTPException(status_code=400, detail="'user_goal' (str) is required")
    return run_energy_simulation(
        user_goal=user_goal,
        n_agents=int(payload.get("n_agents", 50)),
        steps=int(payload.get("steps", 100)),
        connectivity=float(payload.get("connectivity", 0.3)),
        range_type=payload.get("range_type", "bipolar"),
        seed=int(payload.get("seed", 42)),
        config_overrides=payload.get("config_overrides"),
    )


@router.post(
    "/architect",
    name="architect",
    dependencies=[Depends(get_api_key), Depends(rate_limit_dependency)],
)
async def v1_architect(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    """Social Architect inverse-strategy search.

    Payload fields:
        estado_inicial: dict  – initial simulator state (required).
        objetivo_usuario: str – desired end-state description (required).
        max_intentos: int      (default 3)
        config: dict           (optional overrides)
        modo_simulacion: str   (default ``"macro"``)
        metricas_red: str      (optional)
    """
    from social_architect import buscar_estrategia_inversa

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON body required")
    estado_inicial = payload.get("estado_inicial")
    objetivo_usuario = payload.get("objetivo_usuario")
    if (
        not isinstance(estado_inicial, dict)
        or not isinstance(objetivo_usuario, str)
        or not objetivo_usuario.strip()
    ):
        raise HTTPException(
            400,
            "'estado_inicial' (dict) and 'objeto_usuario' (str) are required",
        )
    estrategia, narrativa, intentos, historial = buscar_estrategia_inversa(
        estado_inicial=estado_inicial,
        objetivo_usuario=objetivo_usuario,
        max_intentos=int(payload.get("max_intentos", 3)),
        config=payload.get("config"),
        modo_simulacion=payload.get("modo_simulacion", "macro"),
        metricas_red=payload.get("metricas_red", ""),
    )
    history = historial if isinstance(historial, list) else []
    return {
        "strategy": estrategia,
        "narrative": narrativa,
        "attempts": intentos,
        "history_summary": history[:5],
        "history_length": len(history),
    }
