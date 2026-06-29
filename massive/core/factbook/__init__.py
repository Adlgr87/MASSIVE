"""
MASSIVE Factbook Integration Module

Provides CIA World Factbook data integration for realistic social simulation.

This module enables:
- Country-specific agent initialization based on demographic data
- Social pressure calculation using ethnic/religious group distributions
- Economic inequality (Gini index) integration into energy landscapes
- Intervention optimization with real economic data
- Validation against real-world metrics

Main Components:
- FactbookContext: Main context class for country data
- FactbookDataLoader: Loads and caches Factbook datasets
- FactbookValidator: Validates simulation results against real data

Author: MASSIVE Research
"""

from massive.core.factbook.context import (
    FactbookContext,
    get_factbook_context,
    reset_factbook_context,
    CountryData,
)
from massive.core.factbook.loader import FactbookDataLoader
from massive.core.factbook.validator import (
    FactbookValidator,
    ValidationResult,
    ValidationReport,
)
from massive.core.factbook.mappings import (
    COUNTRY_MAPPINGS,
    DEMOGRAPHIC_FIELDS,
    ECONOMIC_FIELDS,
    SOCIAL_FIELDS,
    POLITICAL_FIELDS,
    COUNTRY_CODES,
    ISO2_TO_CIA,
    ISO3_TO_CIA,
    NAME_TO_CIA,
    normalize_0_100_to_0_1,
    normalize_0_1_to_0_100,
    normalize_dict,
    herfindahl_index,
    diversity_index,
    create_5d_demographic_matrix,
    create_wealth_potential,
)

__all__ = [
    "FactbookContext",
    "FactbookDataLoader", 
    "FactbookValidator",
    "COUNTRY_MAPPINGS",
    "DEMOGRAPHIC_FIELDS",
    "ECONOMIC_FIELDS",
    "SOCIAL_FIELDS",
    "POLITICAL_FIELDS",
    "COUNTRY_CODES",
    "ISO2_TO_CIA",
    "ISO3_TO_CIA",
    "NAME_TO_CIA",
    "CountryData",
    "get_factbook_context",
    "reset_factbook_context",
    "ValidationResult",
    "ValidationReport",
    "normalize_0_100_to_0_1",
    "normalize_0_1_to_0_100",
    "normalize_dict",
    "herfindahl_index",
    "diversity_index",
    "create_5d_demographic_matrix",
    "create_wealth_potential",
]

# Default Factbook data path
DEFAULT_FACTBOOK_PATH = "data/factbook/factbook.json"
