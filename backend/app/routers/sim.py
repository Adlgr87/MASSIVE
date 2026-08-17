"""Simulation router — ``POST /v1/simulate``, ``POST /v1/scientific``.

Wraps the legacy ``simulator.simular`` and the scientific runner via the
service layer.  Incoming payloads are raw ``dict`` (per ADR-002) and
outgoing responses are validated against the DTO namespace.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError

from backend.app.models import SimSnapshotMessage  # noqa: F401 (re-export for routers)
from backend.app.security import get_api_key, rate_limit_dependency
from services.simulation_service import run_scalar_simulation

router = APIRouter(
    prefix="/simulate",
    tags=["simulation"],
)


@router.post("", dependencies=[Depends(get_api_key), Depends(rate_limit_dependency)])
async def v1_simulate(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    """Run a scalar MASSIVE simulation.

    Payload fields (all optional except noted):
        estado_inicial: dict  – initial simulator state (optional).
        escenario: str        – scenario key (default ``campana``).
        pasos: int            – number of steps (default ``50``).
        config: dict          – overrides for ``DEFAULT_CONFIG``.
        verbose: bool         – emit step logs.

    Returns:
        Dict with ``history``, ``summary``, ``config``, ``escenario``.
    """
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON body required")
    try:
        return run_scalar_simulation(
            estado_inicial=payload.get("estado_inicial"),
            escenario=payload.get("escenario", "campana"),
            pasos=int(payload.get("pasos", 50)),
            config=payload.get("config"),
            verbose=bool(payload.get("verbose", False)),
        )
    except HTTPException:
        raise
    except ValidationError:
        raise
    except Exception as _exc:
        import logging

        logging.getLogger("massive.backend.routers.simulation").exception("v1/simulate error")
        raise HTTPException(status_code=500, detail="Internal simulation error") from _exc
