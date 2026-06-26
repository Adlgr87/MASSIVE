"""
Factbook to MASSIVE Parameter Mappings

Defines the mapping between CIA World Factbook fields and MASSIVE simulation parameters.

Author: MASSIVE Research
"""

from typing import Dict, List, Any
import numpy as np

# =============================================================================
# COUNTRY CODE MAPPINGS
# =============================================================================

# Mapping between different country code systems
# Format: {cia_code: {iso2: str, iso3: str, name: str, numeric: int}}
COUNTRY_CODES: Dict[str, Dict[str, Any]] = {
    "US": {"iso2": "US", "iso3": "USA", "name": "United States", "numeric": 840},
    "CH": {"iso2": "CN", "iso3": "CHN", "name": "China", "numeric": 156},
    "GM": {"iso2": "DE", "iso3": "DEU", "name": "Germany", "numeric": 276},
    "UK": {"iso2": "GB", "iso3": "GBR", "name": "United Kingdom", "numeric": 826},
    "FR": {"iso2": "FR", "iso3": "FRA", "name": "France", "numeric": 250},
    "JP": {"iso2": "JP", "iso3": "JPN", "name": "Japan", "numeric": 392},
    "IN": {"iso2": "IN", "iso3": "IND", "name": "India", "numeric": 356},
    "BR": {"iso2": "BR", "iso3": "BRA", "name": "Brazil", "numeric": 76},
    "RU": {"iso2": "RU", "iso3": "RUS", "name": "Russia", "numeric": 643},
    "IT": {"iso2": "IT", "iso3": "ITA", "name": "Italy", "numeric": 380},
    "CA": {"iso2": "CA", "iso3": "CAN", "name": "Canada", "numeric": 124},
    "AU": {"iso2": "AU", "iso3": "AUS", "name": "Australia", "numeric": 36},
    "MX": {"iso2": "MX", "iso3": "MEX", "name": "Mexico", "numeric": 484},
    "KR": {"iso2": "KR", "iso3": "KOR", "name": "South Korea", "numeric": 410},
    "SP": {"iso2": "ES", "iso3": "ESP", "name": "Spain", "numeric": 724},
}

# Reverse mappings for lookup
ISO2_TO_CIA: Dict[str, str] = {v["iso2"]: k for k, v in COUNTRY_CODES.items()}
ISO3_TO_CIA: Dict[str, str] = {v["iso3"]: k for k, v in COUNTRY_CODES.items()}
NAME_TO_CIA: Dict[str, str] = {v["name"].lower(): k for k, v in COUNTRY_CODES.items()}

# =============================================================================
# DEMOGRAPHIC FIELD MAPPINGS
# =============================================================================

# CIA World Factbook demographic fields and their mapping to MASSIVE parameters
DEMOGRAPHIC_FIELDS: Dict[str, Dict[str, Any]] = {
    # Population data
    "population": {
        "factbook_path": ["people", "population"],
        "massive_usage": "n_agents",
        "type": "int",
        "description": "Total population",
        "scaling": "direct",
        "default": 1000,
    },
    
    # Age structure
    "age_0_14": {
        "factbook_path": ["people", "age_structure", "0-14_years"],
        "massive_usage": "demographic_matrix[0]",
        "type": "float",
        "description": "Percentage of population aged 0-14",
        "range": [0.0, 100.0],
        "default": 25.0,
    },
    "age_15_24": {
        "factbook_path": ["people", "age_structure", "15-24_years"],
        "massive_usage": "demographic_matrix[1]",
        "type": "float",
        "description": "Percentage of population aged 15-24",
        "range": [0.0, 100.0],
        "default": 15.0,
    },
    "age_25_54": {
        "factbook_path": ["people", "age_structure", "25-54_years"],
        "massive_usage": "demographic_matrix[2]",
        "type": "float",
        "description": "Percentage of population aged 25-54",
        "range": [0.0, 100.0],
        "default": 40.0,
    },
    "age_55_64": {
        "factbook_path": ["people", "age_structure", "55-64_years"],
        "massive_usage": "demographic_matrix[3]",
        "type": "float",
        "description": "Percentage of population aged 55-64",
        "range": [0.0, 100.0],
        "default": 10.0,
    },
    "age_65_plus": {
        "factbook_path": ["people", "age_structure", "65_years_and_over"],
        "massive_usage": "demographic_matrix[4]",
        "type": "float",
        "description": "Percentage of population aged 65+",
        "range": [0.0, 100.0],
        "default": 10.0,
    },
    
    # Ethnic groups - used for social pressure calculation
    "ethnic_groups": {
        "factbook_path": ["people", "ethnic_groups"],
        "massive_usage": "social_groups['ethnic']",
        "type": "dict",
        "description": "Distribution of ethnic groups",
        "format": {"group_name": "percentage"},
        "default": {},
    },
    
    # Religious groups - used for social pressure calculation
    "religions": {
        "factbook_path": ["people", "religions"],
        "massive_usage": "social_groups['religion']",
        "type": "dict",
        "description": "Distribution of religious groups",
        "format": {"religion_name": "percentage"},
        "default": {},
    },
    
    # Languages
    "languages": {
        "factbook_path": ["people", "languages"],
        "massive_usage": "social_groups['language']",
        "type": "dict",
        "description": "Distribution of languages",
        "format": {"language_name": "percentage"},
        "default": {},
    },
    
    # Education (if available)
    "literacy_rate": {
        "factbook_path": ["people", "literacy"],
        "massive_usage": "education_level",
        "type": "float",
        "description": "Adult literacy rate",
        "range": [0.0, 100.0],
        "default": 95.0,
    },
    
    # Gender ratio
    "sex_ratio": {
        "factbook_path": ["people", "sex_ratio"],
        "massive_usage": "gender_ratio",
        "type": "float",
        "description": "Sex ratio at birth (male/female)",
        "default": 1.05,
    },
}

# Economic fields
ECONOMIC_FIELDS: Dict[str, Dict[str, Any]] = {
    # GDP data
    "gdp_purchasing_power_parity": {
        "factbook_path": ["economy", "gdp_purchasing_power_parity"],
        "massive_usage": "economic_scale",
        "type": "float",
        "description": "GDP (PPP) in international dollars",
        "scaling": "log",
        "default": 1e12,
    },
    "gdp_per_capita": {
        "factbook_path": ["economy", "gdp_per_capita"],
        "massive_usage": "income_distribution['mean']",
        "type": "float",
        "description": "GDP per capita (PPP)",
        "scaling": "direct",
        "default": 20000.0,
    },
    
    # Gini index - CRITICAL for energy landscape
    "gini_index": {
        "factbook_path": ["economy", "gini_index"],
        "massive_usage": "gini_coefficient",
        "type": "float",
        "description": "Gini index of income inequality",
        "range": [0.0, 100.0],
        "scaling": "normalized",  # Convert to [0, 1] for MASSIVE
        "default": 35.0,
    },
    
    # Income distribution
    "income_distribution": {
        "factbook_path": ["economy", "income_distribution"],
        "massive_usage": "income_distribution",
        "type": "dict",
        "description": "Income distribution by percentile",
        "format": {"percentile": "share"},
        "default": {},
    },
    
    # Economic sectors
    "agriculture": {
        "factbook_path": ["economy", "gdp_composition_by_sector", "agriculture"],
        "massive_usage": "sector_weights['agriculture']",
        "type": "float",
        "description": "Agriculture share of GDP",
        "range": [0.0, 100.0],
        "default": 5.0,
    },
    "industry": {
        "factbook_path": ["economy", "gdp_composition_by_sector", "industry"],
        "massive_usage": "sector_weights['industry']",
        "type": "float",
        "description": "Industry share of GDP",
        "range": [0.0, 100.0],
        "default": 25.0,
    },
    "services": {
        "factbook_path": ["economy", "gdp_composition_by_sector", "services"],
        "massive_usage": "sector_weights['services']",
        "type": "float",
        "description": "Services share of GDP",
        "range": [0.0, 100.0],
        "default": 70.0,
    },
    
    # Labor force
    "labor_force": {
        "factbook_path": ["economy", "labor_force"],
        "massive_usage": "economic_activity_rate",
        "type": "int",
        "description": "Total labor force",
        "default": 50000000,
    },
    
    "unemployment_rate": {
        "factbook_path": ["economy", "unemployment_rate"],
        "massive_usage": "unemployment_rate",
        "type": "float",
        "description": "Unemployment rate",
        "range": [0.0, 100.0],
        "default": 5.0,
    },
    
    # Budget data
    "budget_revenues": {
        "factbook_path": ["economy", "budget", "revenues"],
        "massive_usage": "fiscal_capacity['revenues']",
        "type": "float",
        "description": "Government budget revenues",
        "default": 1e12,
    },
    "budget_expenditures": {
        "factbook_path": ["economy", "budget", "expenditures"],
        "massive_usage": "fiscal_capacity['expenditures']",
        "type": "float",
        "description": "Government budget expenditures",
        "default": 1.1e12,
    },
    "budget_surplus_deficit": {
        "factbook_path": ["economy", "budget", "surplus_or_deficit"],
        "massive_usage": "fiscal_balance",
        "type": "float",
        "description": "Budget surplus (+) or deficit (-)",
        "default": -0.1e12,
    },
}

# Political fields
POLITICAL_FIELDS: Dict[str, Dict[str, Any]] = {
    "government_type": {
        "factbook_path": ["government", "country_name", "conventional_long_form"],
        "massive_usage": "governance_type",
        "type": "str",
        "description": "Type of government",
        "default": "democratic",
    },
    "political_parties": {
        "factbook_path": ["government", "political_parties_and_leaders"],
        "massive_usage": "political_groups",
        "type": "dict",
        "description": "Political parties and their influence",
        "default": {},
    },
    "suffrage": {
        "factbook_path": ["government", "suffrage"],
        "massive_usage": "voting_eligibility",
        "type": "str",
        "description": "Suffrage eligibility",
        "default": "18 years of age; universal",
    },
}

# Social fields
SOCIAL_FIELDS: Dict[str, Dict[str, Any]] = {
    "urbanization": {
        "factbook_path": ["people", "urbanization"],
        "massive_usage": "urban_rural_split",
        "type": "dict",
        "description": "Urban and rural population distribution",
        "format": {"urban": 0.8, "rural": 0.2},
        "default": {"urban": 80.0, "rural": 20.0},
    },
    "migration_rate": {
        "factbook_path": ["people", "migration_rate"],
        "massive_usage": "migration_dynamics",
        "type": "float",
        "description": "Net migration rate",
        "default": 0.0,
    },
    "life_expectancy": {
        "factbook_path": ["people", "life_expectancy_at_birth"],
        "massive_usage": "health_index",
        "type": "float",
        "description": "Life expectancy at birth (years)",
        "range": [0.0, 150.0],
        "default": 75.0,
    },
    "fertility_rate": {
        "factbook_path": ["people", "fertility_rate"],
        "massive_usage": "birth_rate_factor",
        "type": "float",
        "description": "Total fertility rate (births per woman)",
        "range": [0.0, 10.0],
        "default": 2.1,
    },
}

# =============================================================================
# MASSIVE PARAMETER MAPPINGS FROM FACTBOOK
# =============================================================================

# How Factbook data maps to MASSIVE simulation parameters
FACTBOOK_TO_MASSIVE: Dict[str, Dict[str, Any]] = {
    # Agent initialization
    "agent_initialization": {
        "population": {
            "source": "population",
            "target": "n_agents",
            "transformation": "scale_to_max",
            "max_agents": 100000,
            "description": "Scale population to maximum agent count",
        },
        "age_distribution": {
            "source": ["age_0_14", "age_15_24", "age_25_54", "age_55_64", "age_65_plus"],
            "target": "demographic_matrix",
            "transformation": "normalize_to_5d",
            "description": "Create 5D demographic sensitivity matrix",
        },
        "ethnic_groups": {
            "source": "ethnic_groups",
            "target": "social_groups['ethnic']",
            "transformation": "normalize_dict",
            "description": "Normalize ethnic group percentages",
        },
        "religious_groups": {
            "source": "religions",
            "target": "social_groups['religion']",
            "transformation": "normalize_dict",
            "description": "Normalize religion percentages",
        },
    },
    
    # Social pressure calculation
    "social_pressure": {
        "ethnic_diversity": {
            "source": "ethnic_groups",
            "target": "social_pressure_weights['ethnic']",
            "transformation": "herfindahl_index",
            "description": "Calculate ethnic diversity index for social pressure",
        },
        "religious_diversity": {
            "source": "religions",
            "target": "social_pressure_weights['religious']",
            "transformation": "herfindahl_index",
            "description": "Calculate religious diversity index",
        },
        "language_diversity": {
            "source": "languages",
            "target": "social_pressure_weights['language']",
            "transformation": "herfindahl_index",
            "description": "Calculate language diversity index",
        },
    },
    
    # Energy engine parameters
    "energy_engine": {
        "gini_coefficient": {
            "source": "gini_index",
            "target": "gini_coefficient",
            "transformation": "normalize_0_100_to_0_1",
            "description": "Convert Gini index [0,100] to [0,1] for energy landscape",
        },
        "economic_inequality": {
            "source": "gini_index",
            "target": "inequality_factor",
            "transformation": "lambda x: 1 + (x / 100) * 2",
            "description": "Higher Gini = higher inequality amplification factor",
        },
        "wealth_distribution": {
            "source": "income_distribution",
            "target": "economic_potential",
            "transformation": "create_wealth_potential",
            "description": "Create economic potential function from income distribution",
        },
    },
    
    # Intervention optimizer
    "intervention_optimizer": {
        "gdp_per_capita": {
            "source": "gdp_per_capita",
            "target": "cost_scale_factor",
            "transformation": "lambda x: np.log1p(x) / 10",
            "description": "Scale intervention costs based on national wealth",
        },
        "budget_balance": {
            "source": "budget_surplus_deficit",
            "target": "fiscal_constraint",
            "transformation": "lambda x: max(0, min(1, 1 - (x / abs(x)) * 0.1)) if x != 0 else 0.5",
            "description": "Fiscal capacity affects intervention feasibility",
        },
        "sector_composition": {
            "source": ["agriculture", "industry", "services"],
            "target": "sector_multipliers",
            "transformation": "normalize_to_weights",
            "description": "Sector composition affects intervention effectiveness",
        },
    },
}

# =============================================================================
# TRANSFORMATION FUNCTIONS
# =============================================================================

def normalize_0_100_to_0_1(value: float) -> float:
    """Normalize value from [0, 100] to [0, 1] range."""
    return np.clip(float(value) / 100.0, 0.0, 1.0)


def normalize_0_1_to_0_100(value: float) -> float:
    """Normalize value from [0, 1] to [0, 100] range."""
    return np.clip(float(value) * 100.0, 0.0, 100.0)


def normalize_dict(percentages: Dict[str, float]) -> Dict[str, float]:
    """Normalize dictionary values to sum to 1.0."""
    total = sum(percentages.values())
    if total <= 0:
        return {k: 1.0 / len(percentages) for k in percentages}
    return {k: v / total for k, v in percentages.items()}


def herfindahl_index(distribution: Dict[str, float]) -> float:
    """
    Calculate Herfindahl index from a distribution.
    Higher values indicate less diversity (more concentration).
    """
    normalized = normalize_dict(distribution)
    return sum(p ** 2 for p in normalized.values())


def diversity_index(distribution: Dict[str, float]) -> float:
    """
    Calculate diversity index (1 - Herfindahl) from a distribution.
    Higher values indicate more diversity.
    """
    return 1.0 - herfindahl_index(distribution)


def scale_to_max(value: float, max_value: float) -> int:
    """Scale a value to a maximum cap."""
    return min(int(value), max_value)


def create_5d_demographic_matrix(age_percentages: List[float]) -> np.ndarray:
    """
    Create 5D demographic sensitivity matrix from age structure.
    
    The 5 dimensions in MASSIVE:
    0: opinion
    1: cooperation  
    2: hierarchy
    3: income
    4: access_info
    
    Age groups affect sensitivity differently.
    """
    # Ensure we have 5 values (pad if necessary)
    while len(age_percentages) < 5:
        age_percentages.append(0.0)
    
    # Normalize to sum to 1.0
    total = sum(age_percentages)
    if total > 0:
        age_percentages = [x / total for x in age_percentages]
    
    # Create 5D matrix where each age group has different sensitivities
    # Younger people are more sensitive to social influence (opinion, access_info)
    # Middle-aged are more sensitive to economic factors (income, hierarchy)
    # Elderly are more resistant to change
    
    matrix = np.zeros((5, 5))
    
    # Age group 0-14 (index 0): High social sensitivity
    matrix[0] = np.array([0.8, 0.7, 0.3, 0.2, 0.9]) * age_percentages[0]
    
    # Age group 15-24 (index 1): High social and info access
    matrix[1] = np.array([0.9, 0.6, 0.4, 0.3, 0.95]) * age_percentages[1]
    
    # Age group 25-54 (index 2): Balanced, economic focus
    matrix[2] = np.array([0.7, 0.8, 0.6, 0.8, 0.7]) * age_percentages[2]
    
    # Age group 55-64 (index 3): Lower sensitivity
    matrix[3] = np.array([0.5, 0.5, 0.5, 0.6, 0.5]) * age_percentages[3]
    
    # Age group 65+ (index 4): Lowest sensitivity
    matrix[4] = np.array([0.3, 0.4, 0.4, 0.5, 0.4]) * age_percentages[4]
    
    return matrix


def create_wealth_potential(gini: float, mean_income: float = 20000.0) -> Dict[str, Any]:
    """
    Create economic potential function parameters from Gini index and mean income.
    
    Higher Gini = more polarized economic landscape (deeper wells, higher peaks)
    Higher mean income = higher overall potential
    """
    gini_normalized = normalize_0_100_to_0_1(gini)
    
    # Calculate polarization factor
    # Gini = 0 (perfect equality) -> polarization = 0
    # Gini = 100 (maximum inequality) -> polarization = 1.0
    polarization = gini_normalized
    
    # Economic potential scale
    income_scale = np.log1p(mean_income) / 10
    
    return {
        "polarization_factor": polarization,
        "income_scale": income_scale,
        "attractor_strength": 1.0 + polarization * 2.0,
        "repeller_strength": 0.5 + polarization * 0.5,
    }


# Combined mappings for easy access
COUNTRY_MAPPINGS = {
    "codes": COUNTRY_CODES,
    "iso2_to_cia": ISO2_TO_CIA,
    "iso3_to_cia": ISO3_TO_CIA,
    "name_to_cia": NAME_TO_CIA,
    "demographic": DEMOGRAPHIC_FIELDS,
    "economic": ECONOMIC_FIELDS,
    "political": POLITICAL_FIELDS,
    "social": SOCIAL_FIELDS,
    "to_massive": FACTBOOK_TO_MASSIVE,
}
