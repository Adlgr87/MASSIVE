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
from typing import Any

from massive.core.factbook.mappings import COUNTRY_CODES

log = logging.getLogger("massive.factbook.loader")


@dataclass
class DataSource:
    """Information about a data source."""

    name: str
    path: str
    format: str = "json"
    priority: int = 0
    loaded: bool = False
    data: dict[str, Any] = field(default_factory=dict)


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
        data_path: str | Path | None = None,
        fallback_sources: list[str] | None = None,
        use_cache: bool = True,
        cache_path: str | None = None,
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
        self.countries: dict[str, dict[str, Any]] = {}
        self._raw_data: dict[str, Any] = {}
        self._sources: dict[str, DataSource] = {}

        # Country code mappings
        self._cia_to_iso2: dict[str, str] = {}
        self._cia_to_iso3: dict[str, str] = {}
        self._name_to_cia: dict[str, str] = {}
        self._iso2_to_cia: dict[str, str] = {}
        self._iso3_to_cia: dict[str, str] = {}

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
            log.warning(
                "[FactbookDataLoader] Usando datos de muestra. Carga el dataset completo para mejor precisión."
            )

        self._initialized = True
        return success

    def _load_json(self, path: Path):
        """Load data from a JSON file."""
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        self._process_loaded_data(data, str(path))

    def _load_cache(self):
        """Load data from cache file."""
        with open(self.cache_path, encoding="utf-8") as f:
            data = json.load(f)

        self._process_loaded_data(data, f"cache: {self.cache_path}")

    def _process_loaded_data(self, data: dict[str, Any], source_name: str):
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
                            if (
                                key.upper() == code
                                or key.upper() == COUNTRY_CODES[code].get("iso2", "")
                                or key.upper() == COUNTRY_CODES[code].get("iso3", "")
                            ):
                                self.countries[code] = value
                                self._raw_data[code] = value
                                break

            log.info(
                f"[FactbookDataLoader] Procesados {len(self.countries)} países desde {source_name}"
            )

    def _normalize_country_code(self, code: str) -> str | None:
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
        """Load sample data for all 15 contract-supported countries.

        Covers every country listed in ``COUNTRY_CODES`` so that the Factbook
        pipeline degrades gracefully (with realistic estimates) when the full
        CIA Factbook JSON is not available.  Full data for US/China/Germany
        is also available in ``data/factbook/factbook_sample.json``.
        """
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
            "BR": {
                "name": "Brazil",
                "cia_code": "BR",
                "iso2": "BR",
                "iso3": "BRA",
                "people": {
                    "population": 216422426,
                    "age_structure": {
                        "0-14_years": 20.9,
                        "15-24_years": 15.8,
                        "25-54_years": 38.0,
                        "55-64_years": 11.5,
                        "65_years_and_over": 13.8,
                    },
                    "ethnic_groups": {
                        "White": 47.7,
                        "Pardo": 43.1,
                        "Black": 7.6,
                        "Asian": 1.1,
                        "Other": 0.5,
                    },
                    "religions": {
                        "Roman Catholic": 50.0,
                        "Evangelical": 22.0,
                        "Spiritist": 2.0,
                        "None": 8.0,
                        "Other": 18.0,
                    },
                    "languages": {"Portuguese": 98.0},
                    "literacy": 93.2,
                    "urbanization": {"urban": 87.1, "rural": 12.9},
                    "life_expectancy_at_birth": 75.0,
                    "fertility_rate": 1.7,
                },
                "economy": {
                    "gdp_purchasing_power_parity": 4.116e12,
                    "gdp_per_capita": 15400.0,
                    "gini_index": 53.4,
                    "gdp_composition_by_sector": {
                        "agriculture": 4.8,
                        "industry": 13.3,
                        "services": 81.9,
                    },
                    "labor_force": 104000000,
                    "unemployment_rate": 9.3,
                    "budget": {
                        "revenues": 4.61e11,
                        "expenditures": 5.90e11,
                        "surplus_or_deficit": -1.29e11,
                    },
                },
                "government": {
                    "country_name": {"conventional_long_form": "Federative Republic of Brazil"},
                    "government_type": "federal presidential republic",
                },
            },
            "UK": {
                "name": "United Kingdom",
                "cia_code": "UK",
                "iso2": "GB",
                "iso3": "GBR",
                "people": {
                    "population": 69580000,
                    "age_structure": {
                        "0-14_years": 16.2,
                        "15-24_years": 13.0,
                        "25-54_years": 41.7,
                        "55-64_years": 13.5,
                        "65_years_and_over": 15.6,
                    },
                    "ethnic_groups": {
                        "White": 83.6,
                        "Black, Black British, Black Welsh": 4.4,
                        "Asian, Asian British": 9.9,
                        "Mixed": 2.1,
                    },
                    "religions": {
                        "Christian": 46.9,
                        "None": 37.2,
                        "Islam": 5.0,
                        "Other": 10.9,
                    },
                    "languages": {"English": 98.3},
                    "literacy": 99.0,
                    "urbanization": {"urban": 83.6, "rural": 16.4},
                    "life_expectancy_at_birth": 81.3,
                    "fertility_rate": 1.6,
                },
                "economy": {
                    "gdp_purchasing_power_parity": 3.527e12,
                    "gdp_per_capita": 50100.0,
                    "gini_index": 35.1,
                    "gdp_composition_by_sector": {
                        "agriculture": 0.6,
                        "industry": 19.9,
                        "services": 79.5,
                    },
                    "labor_force": 32900000,
                    "unemployment_rate": 3.8,
                    "budget": {
                        "revenues": 1.34e12,
                        "expenditures": 1.42e12,
                        "surplus_or_deficit": -8.0e10,
                    },
                },
                "government": {
                    "country_name": {
                        "conventional_long_form": "United Kingdom of Great Britain and Northern Ireland"
                    },
                    "government_type": "parliamentary constitutional monarchy",
                },
            },
            "FR": {
                "name": "France",
                "cia_code": "FR",
                "iso2": "FR",
                "iso3": "FRA",
                "people": {
                    "population": 68370000,
                    "age_structure": {
                        "0-14_years": 18.1,
                        "15-24_years": 12.2,
                        "25-54_years": 39.1,
                        "55-64_years": 13.7,
                        "65_years_and_over": 16.9,
                    },
                    "ethnic_groups": {
                        "White": 87.0,
                        "North African": 10.0,
                        "Other": 3.0,
                    },
                    "religions": {
                        "Christian": 55.0,
                        "None": 39.2,
                        "Islam": 5.7,
                        "Other": 0.1,
                    },
                    "languages": {"French": 98.0},
                    "literacy": 99.0,
                    "urbanization": {"urban": 82.3, "rural": 17.7},
                    "life_expectancy_at_birth": 82.5,
                    "fertility_rate": 1.8,
                },
                "economy": {
                    "gdp_purchasing_power_parity": 3.296e12,
                    "gdp_per_capita": 49300.0,
                    "gini_index": 32.7,
                    "gdp_composition_by_sector": {
                        "agriculture": 1.6,
                        "industry": 19.3,
                        "services": 79.1,
                    },
                    "labor_force": 30100000,
                    "unemployment_rate": 8.1,
                    "budget": {
                        "revenues": 1.37e12,
                        "expenditures": 1.55e12,
                        "surplus_or_deficit": -1.8e11,
                    },
                },
                "government": {
                    "country_name": {"conventional_long_form": "French Republic"},
                    "government_type": "semi-presidential republic",
                },
            },
            "JP": {
                "name": "Japan",
                "cia_code": "JP",
                "iso2": "JP",
                "iso3": "JPN",
                "people": {
                    "population": 123200000,
                    "age_structure": {
                        "0-14_years": 12.1,
                        "15-24_years": 9.6,
                        "25-54_years": 39.0,
                        "55-64_years": 15.6,
                        "65_years_and_over": 23.7,
                    },
                    "ethnic_groups": {"Japanese": 97.8},
                    "religions": {
                        "Shinto": 52.0,
                        "Buddhist": 35.0,
                        "Christian": 2.3,
                        "Other": 10.7,
                    },
                    "languages": {"Japanese": 98.5},
                    "literacy": 99.0,
                    "urbanization": {"urban": 91.7, "rural": 8.3},
                    "life_expectancy_at_birth": 84.6,
                    "fertility_rate": 1.3,
                },
                "economy": {
                    "gdp_purchasing_power_parity": 6.144e12,
                    "gdp_per_capita": 48100.0,
                    "gini_index": 33.0,
                    "gdp_composition_by_sector": {
                        "agriculture": 1.1,
                        "industry": 25.5,
                        "services": 73.4,
                    },
                    "labor_force": 68400000,
                    "unemployment_rate": 2.6,
                    "budget": {
                        "revenues": 1.89e12,
                        "expenditures": 2.14e12,
                        "surplus_or_deficit": -2.5e11,
                    },
                },
                "government": {
                    "country_name": {"conventional_long_form": "Japan"},
                    "government_type": "constitutional monarchy (Emperor)",
                },
            },
            "IN": {
                "name": "India",
                "cia_code": "IN",
                "iso2": "IN",
                "iso3": "IND",
                "people": {
                    "population": 1428627663,
                    "age_structure": {
                        "0-14_years": 25.4,
                        "15-24_years": 16.8,
                        "25-54_years": 35.3,
                        "55-64_years": 9.3,
                        "65_years_and_over": 13.2,
                    },
                    "ethnic_groups": {
                        "Hindu": 79.8,
                        "Muslim": 14.2,
                        "Other": 6.0,
                    },
                    "religions": {
                        "Hindu": 79.8,
                        "Muslim": 14.2,
                        "Other": 6.0,
                    },
                    "languages": {
                        "Hindi": 43.6,
                        "Bengali": 14.4,
                        "Telugu": 7.1,
                        "Marathi": 6.9,
                        "Other": 28.0,
                    },
                    "literacy": 77.8,
                    "urbanization": {"urban": 35.4, "rural": 64.6},
                    "life_expectancy_at_birth": 67.0,
                    "fertility_rate": 2.0,
                },
                "economy": {
                    "gdp_purchasing_power_parity": 1.376e13,
                    "gdp_per_capita": 11000.0,
                    "gini_index": 35.0,
                    "gdp_composition_by_sector": {
                        "agriculture": 15.0,
                        "industry": 23.0,
                        "services": 62.0,
                    },
                    "labor_force": 523000000,
                    "unemployment_rate": 7.8,
                    "budget": {
                        "revenues": 4.41e12,
                        "expenditures": 4.63e12,
                        "surplus_or_deficit": -2.2e11,
                    },
                },
                "government": {
                    "country_name": {"conventional_long_form": "Republic of India"},
                    "government_type": "federal parliamentary democratic republic",
                },
            },
            "RU": {
                "name": "Russia",
                "cia_code": "RU",
                "iso2": "RU",
                "iso3": "RUS",
                "people": {
                    "population": 144417000,
                    "age_structure": {
                        "0-14_years": 14.9,
                        "15-24_years": 10.4,
                        "25-54_years": 44.6,
                        "55-64_years": 14.7,
                        "65_years_and_over": 15.4,
                    },
                    "ethnic_groups": {
                        "Russian": 80.3,
                        "Tatar": 3.9,
                        "Ukrainian": 1.4,
                        "Bashkir": 1.2,
                        "Other": 23.2,
                    },
                    "religions": {
                        "Russian Orthodox": 68.0,
                        "Islam": 10.0,
                        "None": 16.0,
                        "Other": 6.0,
                    },
                    "languages": {"Russian": 85.0},
                    "literacy": 99.7,
                    "urbanization": {"urban": 74.4, "rural": 25.6},
                    "life_expectancy_at_birth": 72.1,
                    "fertility_rate": 1.5,
                },
                "economy": {
                    "gdp_purchasing_power_parity": 6.345e12,
                    "gdp_per_capita": 4500.0,
                    "gini_index": 40.7,
                    "gdp_composition_by_sector": {
                        "agriculture": 4.4,
                        "industry": 33.0,
                        "services": 62.6,
                    },
                    "labor_force": 69600000,
                    "unemployment_rate": 5.2,
                    "budget": {
                        "revenues": 3.09e12,
                        "expenditures": 2.91e12,
                        "surplus_or_deficit": 1.8e11,
                    },
                },
                "government": {
                    "country_name": {"conventional_long_form": "Russian Federation"},
                    "government_type": "semi-presidential republic",
                },
            },
            "IT": {
                "name": "Italy",
                "cia_code": "IT",
                "iso2": "IT",
                "iso3": "ITA",
                "people": {
                    "population": 58953567,
                    "age_structure": {
                        "0-14_years": 13.9,
                        "15-24_years": 10.5,
                        "25-54_years": 40.1,
                        "55-64_years": 13.9,
                        "65_years_and_over": 21.6,
                    },
                    "ethnic_groups": {"Italian": 92.0},
                    "religions": {
                        "Christian": 74.4,
                        "None": 20.1,
                        "Other": 5.5,
                    },
                    "languages": {"Italian": 93.0},
                    "literacy": 99.2,
                    "urbanization": {"urban": 68.8, "rural": 31.2},
                    "life_expectancy_at_birth": 82.3,
                    "fertility_rate": 1.3,
                },
                "economy": {
                    "gdp_purchasing_power_parity": 2.922e12,
                    "gdp_per_capita": 50500.0,
                    "gini_index": 35.0,
                    "gdp_composition_by_sector": {
                        "agriculture": 1.8,
                        "industry": 23.5,
                        "services": 74.7,
                    },
                    "labor_force": 23500000,
                    "unemployment_rate": 7.9,
                    "budget": {
                        "revenues": 1.29e12,
                        "expenditures": 1.42e12,
                        "surplus_or_deficit": -1.3e11,
                    },
                },
                "government": {
                    "country_name": {"conventional_long_form": "Italian Republic"},
                    "government_type": "parliamentary republic",
                },
            },
            "CA": {
                "name": "Canada",
                "cia_code": "CA",
                "iso2": "CA",
                "iso3": "CAN",
                "people": {
                    "population": 40264600,
                    "age_structure": {
                        "0-14_years": 15.2,
                        "15-24_years": 11.9,
                        "25-54_years": 40.3,
                        "55-64_years": 14.1,
                        "65_years_and_over": 18.5,
                    },
                    "ethnic_groups": {
                        "Canadian": 76.0,
                        "English": 15.0,
                        "French": 12.0,
                        "Other": 7.0,
                    },
                    "religions": {
                        "Christian": 67.2,
                        "None": 24.0,
                        "Islam": 4.0,
                        "Other": 4.8,
                    },
                    "languages": {
                        "English": 56.9,
                        "French": 21.3,
                        "Other": 21.8,
                    },
                    "literacy": 99.0,
                    "urbanization": {"urban": 81.4, "rural": 18.6},
                    "life_expectancy_at_birth": 82.6,
                    "fertility_rate": 1.4,
                },
                "economy": {
                    "gdp_purchasing_power_parity": 2.348e12,
                    "gdp_per_capita": 61800.0,
                    "gini_index": 32.6,
                    "gdp_composition_by_sector": {
                        "agriculture": 1.6,
                        "industry": 23.5,
                        "services": 74.9,
                    },
                    "labor_force": 21300000,
                    "unemployment_rate": 5.8,
                    "budget": {
                        "revenues": 1.09e12,
                        "expenditures": 1.20e12,
                        "surplus_or_deficit": -1.1e11,
                    },
                },
                "government": {
                    "country_name": {"conventional_long_form": "Canada"},
                    "government_type": "federal parliamentary democracy",
                },
            },
            "AU": {
                "name": "Australia",
                "cia_code": "AU",
                "iso2": "AU",
                "iso3": "AUS",
                "people": {
                    "population": 26296000,
                    "age_structure": {
                        "0-14_years": 14.6,
                        "15-24_years": 12.1,
                        "25-54_years": 41.3,
                        "55-64_years": 14.0,
                        "65_years_and_over": 18.0,
                    },
                    "ethnic_groups": {
                        "European": 76.6,
                        "Asian": 14.6,
                        "Indigenous": 3.2,
                        "Other": 5.6,
                    },
                    "religions": {
                        "Protestant": 45.0,
                        "Catholic": 26.0,
                        "None": 22.0,
                        "Other": 7.0,
                    },
                    "languages": {"English": 75.0},
                    "literacy": 99.0,
                    "urbanization": {"urban": 87.9, "rural": 12.1},
                    "life_expectancy_at_birth": 83.4,
                    "fertility_rate": 1.6,
                },
                "economy": {
                    "gdp_purchasing_power_parity": 1.893e12,
                    "gdp_per_capita": 71900.0,
                    "gini_index": 35.0,
                    "gdp_composition_by_sector": {
                        "agriculture": 3.6,
                        "industry": 26.1,
                        "services": 70.3,
                    },
                    "labor_force": 13600000,
                    "unemployment_rate": 3.5,
                    "budget": {
                        "revenues": 5.95e11,
                        "expenditures": 5.92e11,
                        "surplus_or_deficit": 3.0e9,
                    },
                },
                "government": {
                    "country_name": {"conventional_long_form": "Commonwealth of Australia"},
                    "government_type": "federal parliamentary democracy",
                },
            },
            "MX": {
                "name": "Mexico",
                "cia_code": "MX",
                "iso2": "MX",
                "iso3": "MEX",
                "people": {
                    "population": 128533000,
                    "age_structure": {
                        "0-14_years": 21.3,
                        "15-24_years": 16.4,
                        "25-54_years": 37.0,
                        "55-64_years": 11.0,
                        "65_years_and_over": 14.3,
                    },
                    "ethnic_groups": {
                        "Mestizo": 62.0,
                        "White": 17.0,
                        "Afro": 2.0,
                        "Indigenous": 6.0,
                        "Other": 13.0,
                    },
                    "religions": {
                        "Roman Catholic": 78.0,
                        "Other": 22.0,
                    },
                    "languages": {
                        "Spanish": 92.7,
                        "Indigenous": 5.4,
                        "Other": 1.9,
                    },
                    "literacy": 95.0,
                    "urbanization": {"urban": 80.2, "rural": 19.8},
                    "life_expectancy_at_birth": 75.1,
                    "fertility_rate": 2.1,
                },
                "economy": {
                    "gdp_purchasing_power_parity": 3.423e12,
                    "gdp_per_capita": 25400.0,
                    "gini_index": 46.2,
                    "gdp_composition_by_sector": {
                        "agriculture": 2.9,
                        "industry": 29.0,
                        "services": 68.1,
                    },
                    "labor_force": 57800000,
                    "unemployment_rate": 3.4,
                    "budget": {
                        "revenues": 4.65e11,
                        "expenditures": 4.88e11,
                        "surplus_or_deficit": -2.3e10,
                    },
                },
                "government": {
                    "country_name": {"conventional_long_form": "United Mexican States"},
                    "government_type": "federal democratic republic",
                },
            },
            "KR": {
                "name": "South Korea",
                "cia_code": "KR",
                "iso2": "KR",
                "iso3": "KOR",
                "people": {
                    "population": 52785400,
                    "age_structure": {
                        "0-14_years": 11.7,
                        "15-24_years": 10.1,
                        "25-54_years": 42.8,
                        "55-64_years": 15.1,
                        "65_years_and_over": 20.3,
                    },
                    "ethnic_groups": {"Korean": 99.9},
                    "religions": {
                        "Christian": 45.1,
                        "None": 46.5,
                        "Buddhist": 15.3,
                        "Other": 3.1,
                    },
                    "languages": {"Korean": 99.0},
                    "literacy": 99.9,
                    "urbanization": {"urban": 81.6, "rural": 18.4},
                    "life_expectancy_at_birth": 83.3,
                    "fertility_rate": 0.9,
                },
                "economy": {
                    "gdp_purchasing_power_parity": 1.864e12,
                    "gdp_per_capita": 37700.0,
                    "gini_index": 34.6,
                    "gdp_composition_by_sector": {
                        "agriculture": 1.8,
                        "industry": 40.5,
                        "services": 57.7,
                    },
                    "labor_force": 28300000,
                    "unemployment_rate": 2.7,
                    "budget": {
                        "revenues": 4.65e11,
                        "expenditures": 5.04e11,
                        "surplus_or_deficit": -3.9e10,
                    },
                },
                "government": {
                    "country_name": {"conventional_long_form": "Republic of Korea"},
                    "government_type": "democratic republic",
                },
            },
            "SP": {
                "name": "Spain",
                "cia_code": "SP",
                "iso2": "ES",
                "iso3": "ESP",
                "people": {
                    "population": 48744000,
                    "age_structure": {
                        "0-14_years": 14.4,
                        "15-24_years": 10.5,
                        "25-54_years": 40.2,
                        "55-64_years": 13.2,
                        "65_years_and_over": 21.7,
                    },
                    "ethnic_groups": {
                        "Spanish": 82.0,
                        "Other": 18.0,
                    },
                    "religions": {
                        "Christian": 66.0,
                        "None": 22.0,
                        "Other": 12.0,
                    },
                    "languages": {
                        "Spanish": 74.0,
                        "Catalan": 16.0,
                        "Other": 10.0,
                    },
                    "literacy": 98.6,
                    "urbanization": {"urban": 80.9, "rural": 19.1},
                    "life_expectancy_at_birth": 83.5,
                    "fertility_rate": 1.2,
                },
                "economy": {
                    "gdp_purchasing_power_parity": 2.399e12,
                    "gdp_per_capita": 49700.0,
                    "gini_index": 34.5,
                    "gdp_composition_by_sector": {
                        "agriculture": 2.5,
                        "industry": 23.6,
                        "services": 73.9,
                    },
                    "labor_force": 24200000,
                    "unemployment_rate": 12.5,
                    "budget": {
                        "revenues": 8.01e11,
                        "expenditures": 8.63e11,
                        "surplus_or_deficit": -6.2e10,
                    },
                },
                "government": {
                    "country_name": {"conventional_long_form": "Kingdom of Spain"},
                    "government_type": "parliamentary monarchy",
                },
            },
        }

        log.info(
            "[FactbookDataLoader] Datos de muestra cargados para %d países", len(self.countries)
        )

    def get_country_data(self, country_identifier: str) -> dict[str, Any] | None:
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
        for _cia_code, data in self.countries.items():
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

    def resolve_country_code(self, country_identifier: str) -> str | None:
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
        for cia_code, data in self.countries.items():  # noqa: B007
            country_name = data.get("name", "").lower()
            if identifier_lower in country_name:
                return cia_code

        return None

    def list_countries(self) -> list[str]:
        """Return list of all loaded country CIA codes."""
        return list(self.countries.keys())

    def list_country_names(self) -> list[str]:
        """Return list of all loaded country names."""
        names = []
        for data in self.countries.values():
            name = data.get("name", "") or data.get("country_name", {}).get(
                "conventional_long_form", ""
            )
            if name and name not in names:
                names.append(name)
        return sorted(names)

    def get_country_info(self, country_identifier: str) -> dict[str, Any] | None:
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
            with open(self.cache_path, "w", encoding="utf-8") as f:
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
        return (
            f"FactbookDataLoader(countries={len(self.countries)}, initialized={self._initialized})"
        )
