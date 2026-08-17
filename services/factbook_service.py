"""Factbook service — country params for engines and interventions."""

from __future__ import annotations

from typing import Any


def get_context(data_path: str | None = None) -> Any:
    """Return a FactbookContext instance.

    Args:
        data_path: Optional path to Factbook JSON; uses shared singleton if None.

    Returns:
        FactbookContext ready for country lookups.
    """
    from massive.core.factbook import FactbookContext, get_factbook_context

    if data_path:
        return FactbookContext(data_path=data_path)
    return get_factbook_context()


def country_params(country: str, data_path: str | None = None) -> dict[str, Any]:
    """Derive MASSIVE parameters for a country code or name.

    Args:
        country: CIA code, ISO, or country name.
        data_path: Optional Factbook data path.

    Returns:
        Dict of derived massive parameters (may be empty if unknown).
    """
    ctx = get_context(data_path)
    raw = ctx.get_massive_params(country) or {}
    # Sanitize numpy types (ndarrays/np.float64) so downstream Pydantic
    # models (LLMRunResponse) never raise PydanticSerializationError. Fixes BUG-02.
    from massive.core.utils.serialize import to_jsonable

    return to_jsonable(dict(raw))


def intervention_constraints(
    country: str,
    data_path: str | None = None,
) -> dict[str, Any]:
    """Load economic constraints for intervention optimization.

    Args:
        country: Country identifier.
        data_path: Optional Factbook data path.

    Returns:
        Constraint dict (cost scale, fiscal feasibility, sectors, …).
    """
    ctx = get_context(data_path)
    return dict(ctx.get_intervention_constraints(country) or {})


def build_engine_from_country(
    country: str,
    *,
    n_agents: int | None = None,
    seed: int = 42,
    data_path: str | None = None,
    **overrides: Any,
) -> Any:
    """Construct ``MassiveEngine.from_factbook`` for UI/API callers.

    Args:
        country: Country identifier.
        n_agents: Optional agent count override.
        seed: RNG seed.
        data_path: Optional Factbook data path.
        **overrides: Extra config keys for the engine.

    Returns:
        Configured ``MassiveEngine`` instance.
    """
    from massive_engine import MassiveEngine

    ctx = get_context(data_path)
    return MassiveEngine.from_factbook(
        country,
        context=ctx,
        n_agents=n_agents,
        seed=seed,
        **overrides,
    )
