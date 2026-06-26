"""
FactbookContext Module

Main context class for CIA World Factbook integration in MASSIVE.

This module provides country-specific context that can be used to:
1. Initialize agents with realistic demographic distributions
2. Calculate social pressure using actual ethnic/religious group data
3. Modulate energy landscapes with real economic inequality data
4. Optimize interventions with real economic constraints
5. Validate simulation results against real-world metrics

Author: MASSIVE Research
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import warnings

import numpy as np

from massive.core.factbook.mappings import (
    COUNTRY_CODES,
    ISO2_TO_CIA,
    ISO3_TO_CIA,
    NAME_TO_CIA,
    DEMOGRAPHIC_FIELDS,
    ECONOMIC_FIELDS,
    SOCIAL_FIELDS,
    FACTBOOK_TO_MASSIVE,
    normalize_0_100_to_0_1,
    normalize_dict,
    herfindahl_index,
    diversity_index,
    create_5d_demographic_matrix,
    create_wealth_potential,
    scale_to_max,
)

log = logging.getLogger("massive.factbook")


@dataclass
class CountryData:
    """
    Container for a country's Factbook data.
    
    Stores both raw Factbook data and derived MASSIVE parameters.
    """
    
    # Country identification
    cia_code: str = ""
    iso2_code: str = ""
    iso3_code: str = ""
    country_name: str = ""
    numeric_code: int = 0
    
    # Raw demographic data from Factbook
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    # Extracted demographic fields
    population: int = 1000
    age_structure: Dict[str, float] = field(default_factory=dict)
    ethnic_groups: Dict[str, float] = field(default_factory=dict)
    religions: Dict[str, float] = field(default_factory=dict)
    languages: Dict[str, float] = field(default_factory=dict)
    literacy_rate: float = 95.0
    sex_ratio: float = 1.05
    urbanization: Dict[str, float] = field(default_factory=dict)
    life_expectancy: float = 75.0
    fertility_rate: float = 2.1
    
    # Extracted economic fields
    gdp_ppp: float = 1e12
    gdp_per_capita: float = 20000.0
    gini_index: float = 35.0
    income_distribution: Dict[str, float] = field(default_factory=dict)
    agriculture_share: float = 5.0
    industry_share: float = 25.0
    services_share: float = 70.0
    labor_force: int = 50000000
    unemployment_rate: float = 5.0
    budget_revenues: float = 1e12
    budget_expenditures: float = 1.1e12
    budget_surplus_deficit: float = -0.1e12
    
    # Extracted political fields
    government_type: str = "democratic"
    political_parties: Dict[str, Any] = field(default_factory=dict)
    suffrage: str = "18 years of age; universal"
    
    # Derived MASSIVE parameters
    massive_params: Dict[str, Any] = field(default_factory=dict)
    
    # Calculated indices
    ethnic_diversity: float = 0.0
    religious_diversity: float = 0.0
    language_diversity: float = 0.0
    gini_coefficient: float = 0.35
    
    def __post_init__(self):
        """Initialize derived parameters after data loading."""
        self._calculate_indices()
        self._derive_massive_params()
    
    def _calculate_indices(self):
        """Calculate diversity and inequality indices."""
        self.ethnic_diversity = diversity_index(self.ethnic_groups) if self.ethnic_groups else 0.0
        self.religious_diversity = diversity_index(self.religions) if self.religions else 0.0
        self.language_diversity = diversity_index(self.languages) if self.languages else 0.0
        self.gini_coefficient = normalize_0_100_to_0_1(self.gini_index)
    
    def _derive_massive_params(self):
        """Derive MASSIVE-specific parameters from raw data."""
        # Agent initialization parameters
        self.massive_params["n_agents"] = scale_to_max(self.population, 100000)
        
        # Age distribution for demographic matrix
        age_order = ["age_0_14", "age_15_24", "age_25_54", "age_55_64", "age_65_plus"]
        age_percentages = [self.age_structure.get(age, 0.0) for age in age_order]
        self.massive_params["demographic_matrix"] = create_5d_demographic_matrix(age_percentages)
        
        # Social groups
        self.massive_params["social_groups"] = {
            "ethnic": normalize_dict(self.ethnic_groups) if self.ethnic_groups else {},
            "religion": normalize_dict(self.religions) if self.religions else {},
            "language": normalize_dict(self.languages) if self.languages else {},
        }
        
        # Social pressure weights based on diversity
        self.massive_params["social_pressure_weights"] = {
            "ethnic": 1.0 - self.ethnic_diversity,
            "religious": 1.0 - self.religious_diversity,
            "language": 1.0 - self.language_diversity,
        }
        
        # Economic parameters
        self.massive_params["gini_coefficient"] = self.gini_coefficient
        self.massive_params["inequality_factor"] = 1.0 + (self.gini_index / 100.0) * 2.0
        
        # Wealth potential for energy landscape
        wealth_params = create_wealth_potential(self.gini_index, self.gdp_per_capita)
        self.massive_params["economic_potential"] = wealth_params
        
        # Cost scale factor for interventions
        self.massive_params["cost_scale_factor"] = np.log1p(self.gdp_per_capita) / 10.0
        
        # Fiscal constraint
        if self.budget_surplus_deficit != 0:
            self.massive_params["fiscal_constraint"] = max(
                0, min(1, 1 - (self.budget_surplus_deficit / abs(self.budget_surplus_deficit)) * 0.1)
            )
        else:
            self.massive_params["fiscal_constraint"] = 0.5
        
        # Sector multipliers
        total_sector = self.agriculture_share + self.industry_share + self.services_share
        if total_sector > 0:
            self.massive_params["sector_multipliers"] = {
                "agriculture": self.agriculture_share / total_sector,
                "industry": self.industry_share / total_sector,
                "services": self.services_share / total_sector,
            }
        else:
            self.massive_params["sector_multipliers"] = {"agriculture": 0.33, "industry": 0.33, "services": 0.34}
        
        # Urban/rural split
        self.massive_params["urban_rural_split"] = self.urbanization
        
        # Health index (normalized life expectancy)
        self.massive_params["health_index"] = min(self.life_expectancy / 100.0, 1.0)


class FactbookContext:
    """
    Main context class for CIA World Factbook integration.
    
    This class manages country data and provides methods to integrate
    Factbook data into MASSIVE simulations.
    
    Usage:
        # Create context
        context = FactbookContext()
        
        # Load country data
        context.load_country("US")  # By CIA code
        context.load_country("United States")  # By name
        context.load_country(iso2="US")  # By ISO2 code
        
        # Get country data
        country = context.get_country("US")
        
        # Get MASSIVE parameters
        params = country.massive_params
        
        # Use in simulation
        n_agents = params["n_agents"]
        demographic_matrix = params["demographic_matrix"]
    
    Author: MASSIVE Research
    """
    
    def __init__(self, data_path: Optional[str] = None):
        """
        Initialize FactbookContext.
        
        Args:
            data_path: Optional path to Factbook JSON file.
                      If None, uses default path.
        """
        self.countries: Dict[str, CountryData] = {}
        self.current_country: Optional[CountryData] = None
        self.data_loader: Optional[Any] = None
        self._initialized: bool = False
        
        # Set up data loader
        self.data_path = data_path or "data/factbook/factbook.json"
        self._try_load_data()
    
    def _try_load_data(self):
        """Attempt to load Factbook data from the specified path."""
        try:
            from massive.core.factbook.loader import FactbookDataLoader
            self.data_loader = FactbookDataLoader(self.data_path)
            self._initialized = True
            log.info(f"[FactbookContext] Inicializado. Datos cargados desde: {self.data_path}")
        except ImportError:
            log.warning("[FactbookContext] FactbookDataLoader no disponible. Usando datos por defecto.")
            self._initialized = True
        except Exception as e:
            log.warning(f"[FactbookContext] Error cargando datos: {e}. Usando datos por defecto.")
            self._initialized = True
    
    def load_country(
        self,
        country_identifier: str,
        iso2: Optional[str] = None,
        iso3: Optional[str] = None,
        force_reload: bool = False,
    ) -> CountryData:
        """
        Load country data from Factbook.
        
        Args:
            country_identifier: Country identifier (CIA code, name, ISO2, or ISO3)
            iso2: Optional ISO2 code
            iso3: Optional ISO3 code
            force_reload: Force reload from data source
            
        Returns:
            CountryData object with all available data
        """
        # Normalize identifier
        identifier = country_identifier.strip().upper()
        
        # Check if already loaded
        if not force_reload and identifier in self.countries:
            self.current_country = self.countries[identifier]
            return self.current_country
        
        # Try to resolve country code
        cia_code = self._resolve_country_code(identifier, iso2, iso3)
        if not cia_code:
            raise ValueError(f"Cannot resolve country: {country_identifier}")
        
        # Create or update country data
        if force_reload or cia_code not in self.countries:
            country_data = self._load_country_data(cia_code)
            self.countries[cia_code] = country_data
            self.countries[country_data.country_name.lower()] = country_data
            
            # Also index by ISO codes
            if country_data.iso2_code:
                self.countries[country_data.iso2_code] = country_data
            if country_data.iso3_code:
                self.countries[country_data.iso3_code] = country_data
        
        self.current_country = self.countries[cia_code]
        return self.current_country
    
    def _resolve_country_code(
        self,
        identifier: str,
        iso2: Optional[str] = None,
        iso3: Optional[str] = None,
    ) -> Optional[str]:
        """Resolve country identifier to CIA code."""
        # Direct CIA code lookup
        if identifier in COUNTRY_CODES:
            return identifier
        
        # ISO2 code
        if iso2:
            return ISO2_TO_CIA.get(iso2.upper())
        if identifier in ISO2_TO_CIA:
            return ISO2_TO_CIA[identifier]
        
        # ISO3 code
        if iso3:
            return ISO3_TO_CIA.get(iso3.upper())
        if identifier in ISO3_TO_CIA:
            return ISO3_TO_CIA[identifier]
        
        # Country name
        if identifier.lower() in NAME_TO_CIA:
            return NAME_TO_CIA[identifier.lower()]
        
        # Try data loader
        if self.data_loader:
            cia_code = self.data_loader.resolve_country_code(identifier)
            if cia_code:
                return cia_code
        
        return None
    
    def _load_country_data(self, cia_code: str) -> CountryData:
        """Load country data for a specific CIA code."""
        # Get country metadata from codes
        country_info = COUNTRY_CODES.get(cia_code, {})
        
        # Create base CountryData
        country = CountryData(
            cia_code=cia_code,
            iso2_code=country_info.get("iso2", ""),
            iso3_code=country_info.get("iso3", ""),
            country_name=country_info.get("name", cia_code),
            numeric_code=country_info.get("numeric", 0),
        )
        
        # Try to load data from loader
        if self.data_loader:
            try:
                raw_data = self.data_loader.get_country_data(cia_code)
                if raw_data:
                    country.raw_data = raw_data
                    self._extract_data(country)
            except Exception as e:
                log.warning(f"[FactbookContext] Error cargando datos para {cia_code}: {e}")
        
        return country
    
    def _extract_data(self, country: CountryData):
        """Extract structured data from raw Factbook data."""
        raw = country.raw_data
        
        # Helper to safely get nested values
        def get_nested(data: Dict, path: List[str], default: Any = None) -> Any:
            for key in path:
                if isinstance(data, dict) and key in data:
                    data = data[key]
                else:
                    return default
            return data
        
        # Extract demographic data
        country.population = int(get_nested(raw, ["people", "population"], 1000))
        
        # Age structure
        age_paths = {
            "age_0_14": ["people", "age_structure", "0-14_years"],
            "age_15_24": ["people", "age_structure", "15-24_years"],
            "age_25_54": ["people", "age_structure", "25-54_years"],
            "age_55_64": ["people", "age_structure", "55-64_years"],
            "age_65_plus": ["people", "age_structure", "65_years_and_over"],
        }
        for key, path in age_paths.items():
            value = get_nested(raw, path, 0.0)
            if isinstance(value, str):
                # Parse percentage string like "25.3%"
                value = float(value.replace("%", "").strip()) if "%" in value else 0.0
            country.age_structure[key] = float(value)
        
        # Ethnic groups
        ethnic_data = get_nested(raw, ["people", "ethnic_groups"], {})
        if isinstance(ethnic_data, dict):
            country.ethnic_groups = {k: float(v.replace("%", "").strip() if isinstance(v, str) else v) 
                                    for k, v in ethnic_data.items()}
        elif isinstance(ethnic_data, str):
            # Parse comma-separated string like "white 72.4%, black 12.6%, ..."
            country.ethnic_groups = self._parse_percentage_string(ethnic_data)
        
        # Religions
        religion_data = get_nested(raw, ["people", "religions"], {})
        if isinstance(religion_data, dict):
            country.religions = {k: float(v.replace("%", "").strip() if isinstance(v, str) else v) 
                               for k, v in religion_data.items()}
        elif isinstance(religion_data, str):
            country.religions = self._parse_percentage_string(religion_data)
        
        # Languages
        language_data = get_nested(raw, ["people", "languages"], {})
        if isinstance(language_data, dict):
            country.languages = {k: float(v.replace("%", "").strip() if isinstance(v, str) else v) 
                               for k, v in language_data.items()}
        elif isinstance(language_data, str):
            country.languages = self._parse_percentage_string(language_data)
        
        # Other demographic data
        country.literacy_rate = float(get_nested(raw, ["people", "literacy"], 95.0))
        country.sex_ratio = float(get_nested(raw, ["people", "sex_ratio"], 1.05))
        
        # Urbanization
        urban_data = get_nested(raw, ["people", "urbanization"], {})
        if isinstance(urban_data, dict):
            country.urbanization = {k: float(v) for k, v in urban_data.items()}
        
        country.life_expectancy = float(get_nested(raw, ["people", "life_expectancy_at_birth"], 75.0))
        country.fertility_rate = float(get_nested(raw, ["people", "fertility_rate"], 2.1))
        
        # Extract economic data
        country.gdp_ppp = float(get_nested(raw, ["economy", "gdp_purchasing_power_parity"], 1e12))
        country.gdp_per_capita = float(get_nested(raw, ["economy", "gdp_per_capita"], 20000.0))
        country.gini_index = float(get_nested(raw, ["economy", "gini_index"], 35.0))
        
        # Sector shares
        country.agriculture_share = float(get_nested(raw, ["economy", "gdp_composition_by_sector", "agriculture"], 5.0))
        country.industry_share = float(get_nested(raw, ["economy", "gdp_composition_by_sector", "industry"], 25.0))
        country.services_share = float(get_nested(raw, ["economy", "gdp_composition_by_sector", "services"], 70.0))
        
        country.labor_force = int(get_nested(raw, ["economy", "labor_force"], 50000000))
        country.unemployment_rate = float(get_nested(raw, ["economy", "unemployment_rate"], 5.0))
        
        # Budget data
        country.budget_revenues = float(get_nested(raw, ["economy", "budget", "revenues"], 1e12))
        country.budget_expenditures = float(get_nested(raw, ["economy", "budget", "expenditures"], 1.1e12))
        country.budget_surplus_deficit = float(get_nested(raw, ["economy", "budget", "surplus_or_deficit"], -0.1e12))
        
        # Political data
        country.government_type = str(get_nested(raw, ["government", "country_name", "conventional_long_form"], "democratic"))
    
    def _parse_percentage_string(self, text: str) -> Dict[str, float]:
        """Parse a percentage string like 'white 72.4%, black 12.6%' into a dict."""
        import re
        pattern = r'([a-zA-Z\s]+)\s+([\d.]+)%?'
        matches = re.findall(pattern, text)
        return {name.strip(): float(value) for name, value in matches}
    
    def get_country(self, country_identifier: str) -> Optional[CountryData]:
        """
        Get country data by identifier.
        
        Args:
            country_identifier: Country identifier (CIA code, name, ISO2, or ISO3)
            
        Returns:
            CountryData object or None if not found
        """
        identifier = country_identifier.upper()
        
        # Direct lookup
        if identifier in self.countries:
            self.current_country = self.countries[identifier]
            return self.current_country
        
        # Try to resolve and load
        try:
            return self.load_country(country_identifier)
        except ValueError:
            return None
    
    def get_massive_params(self, country_identifier: str) -> Dict[str, Any]:
        """
        Get MASSIVE parameters for a specific country.
        
        Args:
            country_identifier: Country identifier
            
        Returns:
            Dictionary of MASSIVE parameters derived from Factbook data
        """
        country = self.get_country(country_identifier)
        if country:
            return country.massive_params
        return {}
    
    def get_social_pressure_weights(self, country_identifier: str) -> Dict[str, float]:
        """
        Get social pressure weights based on ethnic/religious/language diversity.
        
        Args:
            country_identifier: Country identifier
            
        Returns:
            Dictionary with keys 'ethnic', 'religious', 'language' and values [0, 1]
            where higher values indicate less diversity (more social pressure)
        """
        params = self.get_massive_params(country_identifier)
        return params.get("social_pressure_weights", {"ethnic": 0.5, "religious": 0.5, "language": 0.5})
    
    def get_gini_coefficient(self, country_identifier: str) -> float:
        """
        Get Gini coefficient (normalized to [0, 1]) for a country.
        
        Args:
            country_identifier: Country identifier
            
        Returns:
            Gini coefficient normalized to [0, 1]
        """
        params = self.get_massive_params(country_identifier)
        return params.get("gini_coefficient", 0.35)
    
    def get_inequality_factor(self, country_identifier: str) -> float:
        """
        Get inequality amplification factor for energy landscape.
        
        Args:
            country_identifier: Country identifier
            
        Returns:
            Inequality factor > 1.0 (higher for more unequal societies)
        """
        params = self.get_massive_params(country_identifier)
        return params.get("inequality_factor", 1.35)
    
    def get_demographic_matrix(self, country_identifier: str) -> np.ndarray:
        """
        Get 5D demographic sensitivity matrix for a country.
        
        Args:
            country_identifier: Country identifier
            
        Returns:
            5x5 numpy array representing demographic sensitivities
        """
        params = self.get_massive_params(country_identifier)
        return params.get("demographic_matrix", np.eye(5) * 0.2)
    
    def get_economic_potential(self, country_identifier: str) -> Dict[str, Any]:
        """
        Get economic potential parameters for energy landscape.
        
        Args:
            country_identifier: Country identifier
            
        Returns:
            Dictionary with polarization_factor, income_scale, attractor_strength, repeller_strength
        """
        params = self.get_massive_params(country_identifier)
        return params.get("economic_potential", {
            "polarization_factor": 0.35,
            "income_scale": 1.0,
            "attractor_strength": 1.35,
            "repeller_strength": 0.75,
        })
    
    def get_intervention_constraints(self, country_identifier: str) -> Dict[str, Any]:
        """
        Get intervention optimization constraints for a country.
        
        Args:
            country_identifier: Country identifier
            
        Returns:
            Dictionary with cost_scale_factor, fiscal_constraint, sector_multipliers
        """
        params = self.get_massive_params(country_identifier)
        return {
            "cost_scale_factor": params.get("cost_scale_factor", 1.0),
            "fiscal_constraint": params.get("fiscal_constraint", 0.5),
            "sector_multipliers": params.get("sector_multipliers", {}),
        }
    
    def list_loaded_countries(self) -> List[str]:
        """Return list of loaded country CIA codes."""
        return [code for code in self.countries if code in COUNTRY_CODES]
    
    def list_available_countries(self) -> List[Dict[str, Any]]:
        """Return list of all available countries with metadata."""
        return [
            {
                "cia_code": code,
                "iso2": data["iso2"],
                "iso3": data["iso3"],
                "name": data["name"],
                "numeric": data["numeric"],
            }
            for code, data in COUNTRY_CODES.items()
        ]
    
    def reset(self):
        """Reset all loaded country data."""
        self.countries.clear()
        self.current_country = None
    
    def __repr__(self) -> str:
        return (
            f"FactbookContext("
            f"countries={len(self.countries)}, "
            f"current={self.current_country.country_name if self.current_country else 'None'})"
        )


# Global context instance for convenience
_factbook_context: Optional[FactbookContext] = None


def get_factbook_context(data_path: Optional[str] = None) -> FactbookContext:
    """
    Get global FactbookContext instance.
    
    Args:
        data_path: Optional path to Factbook data
        
    Returns:
        Global FactbookContext instance
    """
    global _factbook_context
    if _factbook_context is None:
        _factbook_context = FactbookContext(data_path)
    return _factbook_context


def reset_factbook_context():
    """Reset global FactbookContext instance."""
    global _factbook_context
    if _factbook_context is not None:
        _factbook_context.reset()
    _factbook_context = None
