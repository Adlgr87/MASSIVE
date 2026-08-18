"""massive.core — canonical home for MASSIVE domain modules.

Includes Factbook integration for CIA World Factbook data.
"""

# Core utility functions
# Factbook integration
from massive.core.factbook import (
    COUNTRY_MAPPINGS,
    DEMOGRAPHIC_FIELDS,
    FactbookContext,
    FactbookDataLoader,
    FactbookValidator,
    get_factbook_context,
    reset_factbook_context,
)
from massive.core.intervention_optimizer import (
    create_economic_aware_optimizer,
    estimate_intervention_cost,
    get_intervention_feasibility,
    optimize_interventions,
)
from massive.core.utility_logic import (
    calculate_demographic_strategic_force,
    calculate_group_cohesion,
    calculate_social_pressure,
    calculate_strategic_force,
)

__all__ = [
    # Utility logic
    "calculate_strategic_force",
    "calculate_social_pressure",
    "calculate_group_cohesion",
    "calculate_demographic_strategic_force",
    # Intervention optimizer
    "optimize_interventions",
    "create_economic_aware_optimizer",
    "estimate_intervention_cost",
    "get_intervention_feasibility",
    # Factbook integration
    "FactbookContext",
    "FactbookDataLoader",
    "FactbookValidator",
    "COUNTRY_MAPPINGS",
    "DEMOGRAPHIC_FIELDS",
    "get_factbook_context",
    "reset_factbook_context",
]

# Convenience access to global context
_factbook_context = None


def get_factbook():
    """Get the global FactbookContext instance."""
    return get_factbook_context()
