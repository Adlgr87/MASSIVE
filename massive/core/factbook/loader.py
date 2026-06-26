"""
FactbookDataLoader Module

Loads and manages CIA World Factbook data from various sources.

Supports:
- JSON files (local Factbook dataset)
- CSV files (alternative formats)
- Direct API calls to CIA website (when available)
- Caching and lazy loading

Author: MASSIVE Research
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import warnings

import numpy as np

from massive.core.factbook.mappings import COUNTRY_CODES, ISO2_TO_CIA, ISO3_TO_CIA

log = logging.getLogger("massive.factbook.loader")


@dataclass
class DataSource:
    """Information about a data source."""
    name: str
    path: str
    format: str = "json"
    priority: int = 0
    loaded: bool = False
    data: Dict[str, Any] = field(default_factory=dict)


class FactbookDataLoader:
    """
    Loads CIA World Factbook data from various sources.
    
    This class manages data loading, caching, and country code resolution.
    
    Usage:
        loader = FactbookDataLoader("data/factbook/factbook.json")
        
        # Get all country data
        all_data = loader.load_all()
        
        # Get specific country
        us_data = loader.get_country_data("US")
        
        # Resolve country code
        cia_code = loader.resolve_country_code("United States")
    
    Author: MASSIVE Research
    """
    
    def __init__(
        self,
        data_path: Optional[Union[str, Path]] = None,
        fallback_sources: Optional[List[str]] = None,
        use_cache: bool = True,
        cache_path: Optional[str] = None,
    ):
        """
        Initialize FactbookDataLoader.
        
        Args:
            data_path: Primary path to Factbook JSON file
            fallback_sources: List of fallback data source paths
            use_cache: Whether to cache loaded data
            cache_path: Path for cache file
        """
        self.data_path = Path(data_path) if data_path else None
        self.fallback_sources = fallback_sources or []
        self.use_cache = use_cache
        self.cache_path = Path(cache_path) if cache_path else Path("data/factbook/.cache.json")
        
        # Data storage
        self.countries: Dict[str, Dict[str, Any]] = {}
        self._raw_data: Dict[str, Any] = {}
        self._sources: Dict[str, DataSource] = {}
        
        # Country code mappings
        self._cia_to_iso2: Dict[str, str] = {}
        self._cia_to_iso3: Dict[str, str] = {}
        self._name_to_cia: Dict[str, str] = {}
        self._iso2_to_cia: Dict[str, str] = {}
        self._iso3_to_cia: Dict[str, str] = {}
        
        self._initialize_mappings()
        self._initialized = False
        
        # Try to load data
        self.load()
    
    def _initialize_mappings(self):
        """Initialize country code mappings."""
        for cia_code, info in COUNTRY_CODES.items():
            self._cia_to_iso2[cia_code] = info.get("iso2", "")
            self._cia_to_iso3[cia_code] = info.get("iso3", "")
            self._name_to_cia[info.get("name", "").lower()] = cia_code
            if info.get("iso2"):
                self._iso2_to_cia[info["iso2"]] = cia_code
            if info.get("iso3"):
                self._iso3_to_cia[info["iso3"]] = cia_code
    
    def load(self, force_reload: bool = False) -> bool:
        """
        Load data from all available sources.
        
        Args:
            force_reload: Force reload even if already loaded
            
        Returns:
            True if data was loaded successfully
        """
        if self._initialized and not force_reload:
            return True
        
        success = False
        
        # Try primary path
        if self.data_path and self.data_path.exists():
            try:
                self._load_json(self.data_path)
                success = True
                log.info(f"[FactbookDataLoader] Datos cargados desde: {self.data_path}")
            except Exception as e:
                log.error(f"[FactbookDataLoader] Error cargando {self.data_path}: {e}")
        
        # Try fallback sources
        for fallback_path in self.fallback_sources:
            path = Path(fallback_path)
            if path.exists() and not self.countries:
                try:
                    self._load_json(path)
                    success = True
                    log.info(f"[FactbookDataLoader] Datos cargados desde fallback: {fallback_path}")
                except Exception as e:
                    log.error(f"[FactbookDataLoader] Error cargando {fallback_path}: {e}")
        
        # Try cache
        if self.use_cache and self.cache_path.exists() and not self.countries:
            try:
                self._load_cache()
                success = True
                log.info(f"[FactbookDataLoader] Datos cargados desde caché: {self.cache_path}")
            except Exception as e:
                log.warning(f"[FactbookDataLoader] Error cargando caché: {e}")
        
        if not self.countries:
            # Load sample data if no data loaded
            self._load_sample_data()
            log.warning("[FactbookDataLoader] Usando datos de muestra. Carga el dataset completo para mejor precisión.")
        
        self._initialized = True
        return success
    
    def _load_json(self, path: Path):
        """Load data from a JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self._process_loaded_data(data, str(path))
    
    def _load_cache(self):
        """Load data from cache file."""
        with open(self.cache_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self._process_loaded_data(data, f"cache: {self.cache_path}")
    
    def _process_loaded_data(self, data: Dict[str, Any], source_name: str):
        """Process loaded data and store it."""
        if isinstance(data, dict):
            # Check if it's a flat structure (country_code -> country_data)
            for key, value in data.items():
                if isinstance(value, dict):
                    # Normalize country code to uppercase
                    cia_code = self._normalize_country_code(key)
                    if cia_code:
                        self.countries[cia_code] = value
                        self._raw_data[cia_code] = value
                    else:
                        # Try to find matching code
                        for code in COUNTRY_CODES:
                            if (key.upper() == code or 
                                key.upper() == COUNTRY_CODES[code].get("iso2", "") or
                                key.upper() == COUNTRY_CODES[code].get("iso3", "")):
                                self.countries[code] = value
                                self._raw_data[code] = value
                                break
            
            log.info(f"[FactbookDataLoader] Procesados {len(self.countries)} países desde {source_name}")
    
    def _normalize_country_code(self, code: str) -> Optional[str]:
        """Normalize country code to standard CIA code."""
        code_upper = code.upper()
        
        if code_upper in COUNTRY_CODES:
            return code_upper
        if code_upper in self._iso2_to_cia:
            return self._iso2_to_cia[code_upper]
        if code_upper in self._iso3_to_cia:
            return self._iso3_to_cia[code_upper]
        if code.lower() in self._name_to_cia:
            return self._name_to_cia[code.lower()]
        
        return None
    
    def _load_sample_data(self):
        """Load minimal sample data for 3 countries."""
        self.countries = {
            "US": {
                "name": "United States",
                "cia_code": "US",
                "iso2": "US",
                "iso3": "USA",
                "people": {
                    "population": 339996563,
                    "age_structure": {
                        "0-14_years": 18.4,
                        "15-24_years": 12.8,
                        "25-54_years": 38.9,
                        "55-64_years": 12.4,
                        "65_years_and_over": 17.5,
                    },
                    "ethnic_groups": {
                        "White": 60.1,
                        "Black": 12.5,
                        "Asian": 5.8,
                        "Hispanic": 18.7,
                        "Other": 2.9,
                    },
                    "religions": {
                        "Christian": 63.0,
                        "Protestant": 40.0,
                        "Catholic": 21.0,
                        "None": 28.0,
                        "Jewish": 2.0,
                        "Muslim": 1.0,
                        "Other": 6.0,
                    },
                    "languages": {
                        "English": 82.1,
                        "Spanish": 13.5,
                        "Other": 4.4,
                    },
                    "literacy": 99.0,
                    "urbanization": {
                        "urban": 82.8,
                        "rural": 17.2,
                    },
                    "life_expectancy_at_birth": 76.1,
                    "fertility_rate": 1.6,
                },
                "economy": {
                    "gdp_purchasing_power_parity": 2.695e13,
                    "gdp_per_capita": 70000.0,
                    "gini_index": 41.5,
                    "gdp_composition_by_sector": {
                        "agriculture": 0.9,
                        "industry": 19.1,
                        "services": 80.0,
                    },
                    "labor_force": 160800000,
                    "unemployment_rate": 3.6,
                    "budget": {
                        "revenues": 4.84e12,
                        "expenditures": 6.88e12,
                        "surplus_or_deficit": -2.04e12,
                    },
                },
                "government": {
                    "country_name": {
                        "conventional_long_form": "United States of America",
                    },
                    "government_type": "federal presidential republic",
                },
            },
            "CH": {
                "name": "China",
                "cia_code": "CH",
                "iso2": "CN",
                "iso3": "CHN",
                "people": {
                    "population": 1425671352,
                    "age_structure": {
                        "0-14_years": 17.3,
                        "15-24_years": 11.4,
                        "25-54_years": 46.8,
                        "55-64_years": 13.6,
                        "65_years_and_over": 10.9,
                    },
                    "ethnic_groups": {
                        "Han Chinese": 91.6,
                        "Zhuang": 1.3,
                        "Uyghur": 0.8,
                        "Hui": 0.8,
                        "Other": 5.5,
                    },
                    "religions": {
                        "Buddhist": 18.2,
                        "Christian": 5.1,
                        "Muslim": 2.0,
                        "None": 52.2,
                        "Folk": 21.0,
                        "Other": 1.5,
                    },
                    "languages": {
                        "Standard Chinese": 92.0,
                        "Mandarin": 70.0,
                        "Cantonese": 6.0,
                        "Other": 2.0,
                    },
                    "literacy": 96.7,
                    "urbanization": {
                        "urban": 63.9,
                        "rural": 36.1,
                    },
                    "life_expectancy_at_birth": 77.4,
                    "fertility_rate": 1.2,
                },
                "economy": {
                    "gdp_purchasing_power_parity": 3.007e13,
                    "gdp_per_capita": 18000.0,
                    "gini_index": 38.5,
                    "gdp_composition_by_sector": {
                        "agriculture": 7.7,
                        "industry": 40.5,
                        "services": 51.8,
                    },
                    "labor_force": 780000000,
                    "unemployment_rate": 5.0,
                    "budget": {
                        "revenues": 3.56e12,
                        "expenditures": 4.69e12,
                        "surplus_or_deficit": -1.13e12,
                    },
                },
                "government": {
                    "country_name": {
                        "conventional_long_form": "People's Republic of China",
                    },
                    "government_type": "communist state",
                },
            },
            "GM": {
                "name": "Germany",
                "cia_code": "GM",
                "iso2": "DE",
                "iso3": "DEU",
                "people": {
                    "population": 83294633,
                    "age_structure": {
                        "0-14_years": 13.2,
                        "15-24_years": 9.9,
                        "25-54_years": 45.3,
                        "55-64_years": 14.3,
                        "65_years_and_over": 17.3,
                    },
                    "ethnic_groups": {
                        "German": 86.7,
                        "Turkish": 3.0,
                        "Polish": 1.0,
                        "Russian": 1.0,
                        "Other": 8.3,
                    },
                    "religions": {
                        "Christian": 65.7,
                        "Roman Catholic": 27.2,
                        "Protestant": 26.0,
                        "Muslim": 4.4,
                        "None": 34.1,
                        "Other": 5.8,
                    },
                    "languages": {
                        "German": 95.0,
                        "Turkish": 1.8,
                        "English": 1.5,
                        "Other": 1.7,
                    },
                    "literacy": 99.0,
                    "urbanization": {
                        "urban": 77.5,
                        "rural": 22.5,
                    },
                    "life_expectancy_at_birth": 81.3,
                    "fertility_rate": 1.5,
                },
                "economy": {
                    "gdp_purchasing_power_parity": 4.626e12,
                    "gdp_per_capita": 58000.0,
                    "gini_index": 28.5,
                    "gdp_composition_by_sector": {
                        "agriculture": 0.6,
                        "industry": 28.6,
                        "services": 70.8,
                    },
                    "labor_force": 43900000,
                    "unemployment_rate": 3.0,
                    "budget": {
                        "revenues": 1.77e12,
                        "expenditures": 1.88e12,
                        "surplus_or_deficit": -1.10e11,
                    },
                },
                "government": {
                    "country_name": {
                        "conventional_long_form": "Federal Republic of Germany",
                    },
                    "government_type": "federal parliamentary republic",
                },
            },
        }
        
        log.info("[FactbookDataLoader] Datos de muestra cargados para 3 países (US, CH, GM)")
    
    def get_country_data(self, country_identifier: str) -> Optional[Dict[str, Any]]:
        """
        Get data for a specific country.
        
        Args:
            country_identifier: Country identifier (CIA code, ISO2, ISO3, or name)
            
        Returns:
            Country data dictionary or None if not found
        """
        # Normalize identifier
        identifier = country_identifier.strip().upper()
        
        # Direct lookup
        if identifier in self.countries:
            return self.countries[identifier]
        
        # Try with lowercase name
        identifier_lower = country_identifier.strip().lower()
        for cia_code, data in self.countries.items():
            country_name = data.get("name", "").lower()
            if identifier_lower in country_name or country_name in identifier_lower:
                return data
        
        # Try ISO2/ISO3 codes
        if identifier in self._iso2_to_cia:
            cia_code = self._iso2_to_cia[identifier]
            return self.countries.get(cia_code)
        
        if identifier in self._iso3_to_cia:
            cia_code = self._iso3_to_cia[identifier]
            return self.countries.get(cia_code)
        
        # Try name to CIA mapping
        if identifier_lower in self._name_to_cia:
            cia_code = self._name_to_cia[identifier_lower]
            return self.countries.get(cia_code)
        
        return None
    
    def resolve_country_code(self, country_identifier: str) -> Optional[str]:
        """
        Resolve a country identifier to its CIA code.
        
        Args:
            country_identifier: Country identifier (name, ISO2, ISO3, etc.)
            
        Returns:
            CIA country code (2 letters) or None if not found
        """
        identifier_upper = country_identifier.strip().upper()
        identifier_lower = country_identifier.strip().lower()
        
        # Direct CIA code
        if identifier_upper in COUNTRY_CODES:
            return identifier_upper
        
        # ISO2 code
        if identifier_upper in self._iso2_to_cia:
            return self._iso2_to_cia[identifier_upper]
        
        # ISO3 code
        if identifier_upper in self._iso3_to_cia:
            return self._iso3_to_cia[identifier_upper]
        
        # Country name
        if identifier_lower in self._name_to_cia:
            return self._name_to_cia[identifier_lower]
        
        # Search in loaded data
        for cia_code, data in self.countries.items():
            country_name = data.get("name", "").lower()
            if identifier_lower in country_name:
                return cia_code
        
        return None
    
    def list_countries(self) -> List[str]:
        """Return list of all loaded country CIA codes."""
        return list(self.countries.keys())
    
    def list_country_names(self) -> List[str]:
        """Return list of all loaded country names."""
        names = []
        for data in self.countries.values():
            name = data.get("name", "") or data.get("country_name", {}).get("conventional_long_form", "")
            if name and name not in names:
                names.append(name)
        return sorted(names)
    
    def get_country_info(self, country_identifier: str) -> Optional[Dict[str, Any]]:
        """
        Get metadata about a country (not the full data).
        
        Args:
            country_identifier: Country identifier
            
        Returns:
            Dictionary with country metadata
        """
        cia_code = self.resolve_country_code(country_identifier)
        if not cia_code:
            return None
        
        if cia_code in COUNTRY_CODES:
            info = COUNTRY_CODES[cia_code].copy()
            info["cia_code"] = cia_code
            return info
        
        # Try loaded data
        data = self.get_country_data(country_identifier)
        if data:
            return {
                "cia_code": cia_code,
                "name": data.get("name", ""),
                "iso2": data.get("iso2", ""),
                "iso3": data.get("iso3", ""),
            }
        
        return None
    
    def save_cache(self):
        """Save loaded data to cache file."""
        if not self.use_cache:
            return
        
        try:
            cache_data = {k: v for k, v in self._raw_data.items()}
            with open(self.cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            log.info(f"[FactbookDataLoader] Cache guardado en: {self.cache_path}")
        except Exception as e:
            log.error(f"[FactbookDataLoader] Error guardando cache: {e}")
    
    def clear(self):
        """Clear all loaded data."""
        self.countries.clear()
        self._raw_data.clear()
        self._initialized = False
    
    def __repr__(self) -> str:
        return f"FactbookDataLoader(countries={len(self.countries)}, initialized={self._initialized})"
