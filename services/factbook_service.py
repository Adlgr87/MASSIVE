"""Factbook service — country params for engines and interventions."""

from __future__ import annotations

from typing import Any, Optional


def get_context(data_path: Optional[str] = None):
    """Return a FactbookContext (shared singleton when path is default)."""
    from massive.core.factbook import get_factbook_context, FactbookContext

    if data_path:
        return FactbookContext(data_path=data_path)
    return get_factbook_context()


def country_params(country: str, data_path: Optional[str] = None) -> dict[str, Any]:
    """MASSIVE parameters derived for a country code/name."""
    ctx = get_context(data_path)
    return dict(ctx.get_massive_params(country) or {})


def intervention_constraints(country: str, data_path: Optional[str] = None) -> dict[str, Any]:
    """Economic constraints for intervention optimization."""
    ctx = get_context(data_path)
    return dict(ctx.get_intervention_constraints(country) or {})


def build_engine_from_country(
    country: str,
    *,
    n_agents: Optional[int] = None,
    seed: int = 42,
    data_path: Optional[str] = None,
    **overrides: Any,
):
    """Construct ``MassiveEngine.from_factbook`` for UI/API callers."""
    from massive_engine import MassiveEngine

    ctx = get_context(data_path)
    return MassiveEngine.from_factbook(
        country,
        context=ctx,
        n_agents=n_agents,
        seed=seed,
        **overrides,
    )
