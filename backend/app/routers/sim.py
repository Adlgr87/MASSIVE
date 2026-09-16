"""Simulation router — ``POST /v1/simulate``, ``POST /v1/scientific``.

Wraps the legacy ``simulator.simular`` and the scientific runner via the
service layer.  Incoming payloads are raw ``dict`` (per ADR-002) and
outgoing responses are validated against the DTO namespace.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from pydantic import ValidationError

from backend.app.models import SimRequest, SimSnapshotMessage  # noqa: F401 (re-export for routers)
from backend.app.security import get_api_key, rate_limit_dependency
from services.simulation_service import run_scalar_simulation

router = APIRouter(
    prefix="/simulate",
    tags=["simulation"],
)


@router.post(
    "",
    dependencies=[Depends(get_api_key), Depends(rate_limit_dependency)],
)
async def v1_simulate(
    request: Request,
    payload: Annotated[SimRequest, Body()],
) -> dict[str, Any]:
    """Run a scalar MASSIVE simulation.

    Payload fields (all optional except noted):
        estado_inicial: dict  – initial simulator state (optional).
        escenario: str        – scenario key (default ``campana``).
        pasos: int            – number of steps (1–10 000, default ``50``).
        config: dict          – overrides for ``DEFAULT_CONFIG``.
        verbose: bool         – emit step logs.

    Returns:
        Dict with ``history``, ``summary``, ``config``, ``escenario``.
    """
    try:
        return run_scalar_simulation(
            estado_inicial=payload.estado_inicial,
            escenario=payload.escenario,
            pasos=payload.pasos,
            config=payload.config,
            verbose=payload.verbose,
        )
    except HTTPException:
        raise
    except ValidationError:
        raise
    except Exception as _exc:
        import logging

        logging.getLogger(__name__).exception("v1/simulate error")
        raise HTTPException(status_code=500, detail="Internal simulation error") from _exc
