"""Capabilities endpoint — tells the frontend which modes are live."""

from __future__ import annotations

import logging

from fastapi import APIRouter

from backend.app.llm_chat import resolve_provider
from backend.app.models.dto_ui import CFCStatus, LLMStatus, StatusResponse

log = logging.getLogger("massive.ui_ng.status")

router = APIRouter(tags=["status"])


@router.get("/api/status", response_model=StatusResponse)
def api_status() -> StatusResponse:
    """Report backend capabilities: LLM provider, CfC, engines, Factbook."""
    llm = resolve_provider()

    cfc = CFCStatus()
    try:
        from cfc_router import CfCRouter

        raw = CfCRouter.get().status
        cfc = CFCStatus(
            regime_selector=bool(raw.get("regime_selector", False)),
            tau_matrix=bool(raw.get("tau_matrix", False)),
            architect_policy=bool(raw.get("architect_policy", False)),
        )
    except Exception:  # noqa: BLE001
        pass

    rust_available = False
    try:
        from massive_core.rust_core import RUST_CORE_AVAILABLE

        rust_available = bool(RUST_CORE_AVAILABLE)
    except Exception:  # noqa: BLE001
        pass

    factbook_countries: list[str] = []
    try:
        from massive.core.factbook import FactbookContext

        ctx = FactbookContext()
        factbook_countries = sorted(ctx.list_countries())[:10]
    except Exception:  # noqa: BLE001
        pass

    return StatusResponse(
        service="MASSIVE UI-NG",
        version="2.0.0",
        llm=LLMStatus(
            configured=llm["configured"] or llm["provider"] == "ollama",
            provider=llm["provider"],
            model=llm["model"],
        ),
        cfc=cfc,
        rust_available=rust_available,
        engines=["scalar", "energy", "multilayer", "massive"],
        factbook_countries=factbook_countries,
        languages=["es", "en"],
    )
