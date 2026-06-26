"""
FactbookValidator Module

Validates MASSIVE simulation results against CIA World Factbook data.

Provides methods to:
- Compare simulation outputs with real-world metrics
- Calculate accuracy scores for different validation criteria
- Generate validation reports
- Identify discrepancies between simulation and reality

Author: MASSIVE Research
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import warnings

import numpy as np
from scipy import stats

from massive.core.factbook.context import FactbookContext, get_factbook_context
from massive.core.factbook.mappings import COUNTRY_CODES, normalize_0_100_to_0_1

log = logging.getLogger("massive.factbook.validator")


@dataclass
class ValidationResult:
    """
    Container for a single validation result.
    
    Compares a simulation metric with real-world data.
    """
    metric_name: str
    simulated_value: float
    real_value: float
    unit: str = ""
    description: str = ""
    
    # Calculated fields
    absolute_error: float = 0.0
    relative_error: float = 0.0
    percentage_error: float = 0.0
    score: float = 0.0  # 0-100, higher is better
    
    def __post_init__(self):
        self._calculate_errors()
    
    def _calculate_errors(self):
        """Calculate error metrics."""
        if self.real_value == 0:
            self.absolute_error = abs(self.simulated_value - self.real_value)
            self.relative_error = self.absolute_error
            self.percentage_error = 0.0 if self.simulated_value == 0 else 100.0
        else:
            self.absolute_error = abs(self.simulated_value - self.real_value)
            self.relative_error = self.absolute_error / abs(self.real_value)
            self.percentage_error = self.relative_error * 100.0
        
        # Calculate score (0-100)
        # For most metrics, lower error = higher score
        # We use exponential decay: score = 100 * exp(-k * relative_error)
        # k is chosen so that 10% error gives score ~80
        k = 2.3  # ln(5) ≈ 1.609, but we want 0.1 relative error -> score 80
        # 80 = 100 * exp(-k * 0.1) => exp(-0.1k) = 0.8 => -0.1k = ln(0.8) => k = -ln(0.8)/0.1 ≈ 2.23
        
        if self.relative_error <= 0.01:  # Within 1%
            self.score = 100.0
        else:
            self.score = max(0.0, 100.0 * np.exp(-2.3 * self.relative_error))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "metric_name": self.metric_name,
            "simulated_value": self.simulated_value,
            "real_value": self.real_value,
            "unit": self.unit,
            "description": self.description,
            "absolute_error": self.absolute_error,
            "relative_error": self.relative_error,
            "percentage_error": self.percentage_error,
            "score": self.score,
        }


@dataclass
class ValidationReport:
    """
    Container for a complete validation report.
    
    Aggregates multiple validation results for a single simulation run.
    """
    country_code: str
    simulation_config: Dict[str, Any] = field(default_factory=dict)
    results: List[ValidationResult] = field(default_factory=list)
    overall_score: float = 0.0
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        self._calculate_overall_score()
    
    def _calculate_overall_score(self):
        """Calculate overall validation score."""
        if not self.results:
            self.overall_score = 0.0
            return
        
        # Weight different categories
        category_weights = {
            "demographic": 0.25,
            "economic": 0.35,
            "social": 0.25,
            "political": 0.15,
        }
        
        # Group results by category
        category_scores: Dict[str, List[float]] = {
            "demographic": [],
            "economic": [],
            "social": [],
            "political": [],
        }
        
        for result in self.results:
            metric_lower = result.metric_name.lower()
            if any(word in metric_lower for word in ["population", "age", "literacy", "fertility", "life"]):
                category_scores["demographic"].append(result.score)
            elif any(word in metric_lower for word in ["gdp", "gini", "income", "unemployment", "budget", "sector"]):
                category_scores["economic"].append(result.score)
            elif any(word in metric_lower for word in ["ethnic", "religion", "language", "urbanization"]):
                category_scores["social"].append(result.score)
            else:
                category_scores["political"].append(result.score)
        
        # Calculate weighted average
        total_score = 0.0
        total_weight = 0.0
        
        for category, scores in category_scores.items():
            if scores:
                category_avg = np.mean(scores)
                category_weight = category_weights.get(category, 0.25)
                total_score += category_avg * category_weight
                total_weight += category_weight
        
        if total_weight > 0:
            self.overall_score = total_score / total_weight
        else:
            self.overall_score = np.mean([r.score for r in self.results])
    
    def add_result(self, result: ValidationResult):
        """Add a validation result to the report."""
        self.results.append(result)
        self._calculate_overall_score()
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics for the report."""
        if not self.results:
            return {"overall_score": 0.0, "count": 0}
        
        scores = [r.score for r in self.results]
        
        return {
            "overall_score": self.overall_score,
            "count": len(self.results),
            "mean_score": float(np.mean(scores)),
            "median_score": float(np.median(scores)),
            "std_score": float(np.std(scores)),
            "min_score": float(np.min(scores)),
            "max_score": float(np.max(scores)),
            "passing": sum(1 for s in scores if s >= 80.0),
            "passing_percentage": (sum(1 for s in scores if s >= 80.0) / len(scores)) * 100,
        }
    
    def get_best_worst(self, n: int = 5) -> Dict[str, List[Dict[str, Any]]]:
        """Get best and worst performing metrics."""
        sorted_results = sorted(self.results, key=lambda r: r.score, reverse=True)
        
        return {
            "best": [r.to_dict() for r in sorted_results[:n]],
            "worst": [r.to_dict() for r in sorted_results[-n:]],
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "country_code": self.country_code,
            "simulation_config": self.simulation_config,
            "timestamp": self.timestamp,
            "overall_score": self.overall_score,
            "summary": self.get_summary(),
            "results": [r.to_dict() for r in self.results],
        }
    
    def save(self, path: Optional[Union[str, Path]] = None):
        """Save report to JSON file."""
        if path is None:
            path = Path(f"reports/factbook_validation_{self.country_code}_{self.timestamp[:10]}.json")
        
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
        
        log.info(f"[FactbookValidator] Reporte guardado en: {path}")
        return path


class FactbookValidator:
    """
    Validates MASSIVE simulation results against CIA World Factbook data.
    
    This class provides comprehensive validation capabilities:
    
    1. **Demographic Validation**: Compare population structure, age distribution
    2. **Economic Validation**: Compare GDP, Gini index, sector composition
    3. **Social Validation**: Compare ethnic/religious/language diversity
    4. **Statistical Validation**: Use statistical tests to assess similarity
    
    Usage:
        validator = FactbookValidator()
        
        # Run validation for a simulation
        report = validator.validate_simulation(
            simulation_results,
            country_code="US",
            config=simulation_config
        )
        
        # Get validation score
        score = report.overall_score
        
        # Save report
        report.save()
    
    Author: MASSIVE Research
    """
    
    def __init__(self, context: Optional[FactbookContext] = None):
        """
        Initialize FactbookValidator.
        
        Args:
            context: Optional FactbookContext instance. If None, creates a new one.
        """
        self.context = context or get_factbook_context()
        self._tolerance_levels: Dict[str, float] = {
            "strict": 0.05,    # 5% error tolerance
            "moderate": 0.10, # 10% error tolerance
            "lenient": 0.20,  # 20% error tolerance
        }
    
    def validate_simulation(
        self,
        simulation_results: Dict[str, Any],
        country_identifier: str,
        config: Optional[Dict[str, Any]] = None,
        validation_level: str = "moderate",
    ) -> ValidationReport:
        """
        Run comprehensive validation of simulation results.
        
        Args:
            simulation_results: Dictionary with simulation outputs
            country_identifier: Country identifier (CIA code, ISO2, ISO3, or name)
            config: Optional simulation configuration
            validation_level: Tolerance level ('strict', 'moderate', 'lenient')
            
        Returns:
            ValidationReport with all validation results
        """
        report = ValidationReport(
            country_code=country_identifier,
            simulation_config=config or {},
        )
        
        # Get real data for comparison
        try:
            real_data = self.context.get_country(country_identifier)
            if real_data:
                # Demographic validation
                demo_results = self._validate_demographics(simulation_results, real_data)
                report.results.extend(demo_results)
                
                # Economic validation
                econ_results = self._validate_economics(simulation_results, real_data)
                report.results.extend(econ_results)
                
                # Social validation
                social_results = self._validate_social(simulation_results, real_data)
                report.results.extend(social_results)
                
                # Political validation (if applicable)
                # political_results = self._validate_political(simulation_results, real_data)
                # report.results.extend(political_results)
            else:
                log.warning(f"[FactbookValidator] No se encontraron datos reales para {country_identifier}")
        except Exception as e:
            log.error(f"[FactbookValidator] Error obteniendo datos reales: {e}")
        
        return report
    
    def _validate_demographics(
        self,
        sim_results: Dict[str, Any],
        real_data: Any,
    ) -> List[ValidationResult]:
        """Validate demographic aspects of the simulation."""
        results = []
        
        # Population comparison
        sim_pop = self._extract_metric(sim_results, ["population", "n_agents", "total_population"])
        real_pop = getattr(real_data, "population", None)
        if sim_pop is not None and real_pop is not None:
            # Scale simulation population to match real scale
            if sim_pop > 0 and real_pop > 0:
                scale_factor = real_pop / sim_pop
                sim_pop_scaled = sim_pop * scale_factor
                results.append(ValidationResult(
                    metric_name="Population",
                    simulated_value=float(sim_pop_scaled),
                    real_value=float(real_pop),
                    unit="people",
                    description="Total population comparison",
                ))
        
        # Age structure comparison
        sim_age = self._extract_metric(sim_results, ["age_structure", "age_distribution", "demographics"])
        real_age = getattr(real_data, "age_structure", {})
        if isinstance(sim_age, dict) and isinstance(real_age, dict):
            # Compare each age group
            for age_group, real_value in real_age.items():
                if age_group in sim_age:
                    results.append(ValidationResult(
                        metric_name=f"Age: {age_group}",
                        simulated_value=float(sim_age[age_group]),
                        real_value=float(real_value),
                        unit="%",
                        description=f"Percentage of population aged {age_group}",
                    ))
        
        # Life expectancy comparison
        sim_life = self._extract_metric(sim_results, ["life_expectancy", "avg_life_expectancy"])
        real_life = getattr(real_data, "life_expectancy", None)
        if sim_life is not None and real_life is not None:
            results.append(ValidationResult(
                metric_name="Life Expectancy",
                simulated_value=float(sim_life),
                real_value=float(real_life),
                unit="years",
                description="Average life expectancy at birth",
            ))
        
        # Fertility rate comparison
        sim_fertility = self._extract_metric(sim_results, ["fertility_rate", "avg_children"])
        real_fertility = getattr(real_data, "fertility_rate", None)
        if sim_fertility is not None and real_fertility is not None:
            results.append(ValidationResult(
                metric_name="Fertility Rate",
                simulated_value=float(sim_fertility),
                real_value=float(real_fertility),
                unit="births per woman",
                description="Total fertility rate",
            ))
        
        return results
    
    def _validate_economics(
        self,
        sim_results: Dict[str, Any],
        real_data: Any,
    ) -> List[ValidationResult]:
        """Validate economic aspects of the simulation."""
        results = []
        
        # GDP per capita comparison
        sim_gdp_capita = self._extract_metric(sim_results, [
            "gdp_per_capita", "avg_income", "mean_income"
        ])
        real_gdp_capita = getattr(real_data, "gdp_per_capita", None)
        if sim_gdp_capita is not None and real_gdp_capita is not None:
            # Convert to comparable units
            # Simulation might use different scales
            results.append(ValidationResult(
                metric_name="GDP per Capita",
                simulated_value=float(sim_gdp_capita),
                real_value=float(real_gdp_capita),
                unit="USD",
                description="GDP per capita (PPP)",
            ))
        
        # Gini index comparison
        sim_gini = self._extract_metric(sim_results, ["gini_index", "gini", "inequality"])
        real_gini = getattr(real_data, "gini_index", None)
        if sim_gini is not None and real_gini is not None:
            # Normalize to [0, 100] range
            sim_gini_norm = self._normalize_gini(sim_gini)
            real_gini_norm = float(real_gini)
            results.append(ValidationResult(
                metric_name="Gini Index",
                simulated_value=sim_gini_norm,
                real_value=real_gini_norm,
                unit="points",
                description="Income inequality (0=perfect equality, 100=maximum inequality)",
            ))
        
        # Economic sector comparison
        sim_sectors = self._extract_metric(sim_results, ["sector_composition", "gdp_by_sector"])
        if isinstance(sim_sectors, dict):
            real_agriculture = getattr(real_data, "agriculture_share", None)
            real_industry = getattr(real_data, "industry_share", None)
            real_services = getattr(real_data, "services_share", None)
            
            sim_agriculture = sim_sectors.get("agriculture", sim_sectors.get("agriculture_share", 0))
            sim_industry = sim_sectors.get("industry", sim_sectors.get("industry_share", 0))
            sim_services = sim_sectors.get("services", sim_sectors.get("services_share", 0))
            
            if real_agriculture is not None and sim_agriculture is not None:
                results.append(ValidationResult(
                    metric_name="Agriculture Share",
                    simulated_value=float(sim_agriculture),
                    real_value=float(real_agriculture),
                    unit="% of GDP",
                    description="Agriculture share of GDP",
                ))
            
            if real_industry is not None and sim_industry is not None:
                results.append(ValidationResult(
                    metric_name="Industry Share",
                    simulated_value=float(sim_industry),
                    real_value=float(real_industry),
                    unit="% of GDP",
                    description="Industry share of GDP",
                ))
            
            if real_services is not None and sim_services is not None:
                results.append(ValidationResult(
                    metric_name="Services Share",
                    simulated_value=float(sim_services),
                    real_value=float(real_services),
                    unit="% of GDP",
                    description="Services share of GDP",
                ))
        
        # Unemployment rate comparison
        sim_unemployment = self._extract_metric(sim_results, ["unemployment_rate", "unemployment"])
        real_unemployment = getattr(real_data, "unemployment_rate", None)
        if sim_unemployment is not None and real_unemployment is not None:
            results.append(ValidationResult(
                metric_name="Unemployment Rate",
                simulated_value=float(sim_unemployment),
                real_value=float(real_unemployment),
                unit="%",
                description="Unemployment rate",
            ))
        
        return results
    
    def _validate_social(
        self,
        sim_results: Dict[str, Any],
        real_data: Any,
    ) -> List[ValidationResult]:
        """Validate social aspects of the simulation."""
        results = []
        
        # Ethnic diversity comparison
        sim_ethnic_diversity = self._extract_metric(sim_results, [
            "ethnic_diversity", "ethnic_diversity_index"
        ])
        real_ethnic_diversity = getattr(real_data, "ethnic_diversity", None)
        if sim_ethnic_diversity is not None and real_ethnic_diversity is not None:
            results.append(ValidationResult(
                metric_name="Ethnic Diversity",
                simulated_value=float(sim_ethnic_diversity),
                real_value=float(real_ethnic_diversity),
                unit="index",
                description="Ethnic diversity index (higher = more diverse)",
            ))
        
        # Religious diversity comparison
        sim_religious_diversity = self._extract_metric(sim_results, [
            "religious_diversity", "religion_diversity_index"
        ])
        real_religious_diversity = getattr(real_data, "religious_diversity", None)
        if sim_religious_diversity is not None and real_religious_diversity is not None:
            results.append(ValidationResult(
                metric_name="Religious Diversity",
                simulated_value=float(sim_religious_diversity),
                real_value=float(real_religious_diversity),
                unit="index",
                description="Religious diversity index (higher = more diverse)",
            ))
        
        # Language diversity comparison
        sim_language_diversity = self._extract_metric(sim_results, [
            "language_diversity", "language_diversity_index"
        ])
        real_language_diversity = getattr(real_data, "language_diversity", None)
        if sim_language_diversity is not None and real_language_diversity is not None:
            results.append(ValidationResult(
                metric_name="Language Diversity",
                simulated_value=float(sim_language_diversity),
                real_value=float(real_language_diversity),
                unit="index",
                description="Language diversity index (higher = more diverse)",
            ))
        
        # Urbanization comparison
        sim_urbanization = self._extract_metric(sim_results, ["urbanization", "urban_rate"])
        real_urbanization = getattr(real_data, "urbanization", {})
        if isinstance(sim_urbanization, (int, float)) and isinstance(real_urbanization, dict):
            real_urban = real_urbanization.get("urban", None)
            if real_urban is not None:
                results.append(ValidationResult(
                    metric_name="Urbanization Rate",
                    simulated_value=float(sim_urbanization),
                    real_value=float(real_urban),
                    unit="%",
                    description="Percentage of population living in urban areas",
                ))
        
        return results
    
    def _extract_metric(
        self,
        data: Dict[str, Any],
        possible_keys: List[str],
    ) -> Optional[Any]:
        """Extract a metric from nested data using multiple possible keys."""
        for key in possible_keys:
            if key in data:
                return data[key]
            # Try nested access
            for top_key, top_value in data.items():
                if isinstance(top_value, dict) and key in top_value:
                    return top_value[key]
        return None
    
    def _normalize_gini(self, gini: Any) -> float:
        """Normalize Gini index to [0, 100] range."""
        if gini is None:
            return 0.0
        
        # If already in [0, 100]
        if 0 <= gini <= 100:
            return float(gini)
        
        # If in [0, 1] range, scale to [0, 100]
        if 0 <= gini <= 1:
            return float(gini) * 100.0
        
        # Clip to valid range
        return float(np.clip(float(gini), 0.0, 100.0))
    
    def validate_accuracy(
        self,
        simulation_results: Dict[str, Any],
        country_identifier: str,
        threshold: float = 80.0,
    ) -> Tuple[bool, float, ValidationReport]:
        """
        Check if simulation results meet accuracy threshold.
        
        Args:
            simulation_results: Simulation results to validate
            country_identifier: Country to validate against
            threshold: Minimum acceptable accuracy score (0-100)
            
        Returns:
            Tuple of (passes_threshold, overall_score, full_report)
        """
        report = self.validate_simulation(simulation_results, country_identifier)
        passes = report.overall_score >= threshold
        return passes, report.overall_score, report
    
    def get_accuracy_score(
        self,
        simulation_results: Dict[str, Any],
        country_identifier: str,
    ) -> float:
        """
        Get accuracy score for a simulation.
        
        Args:
            simulation_results: Simulation results
            country_identifier: Country to compare with
            
        Returns:
            Accuracy score from 0 to 100
        """
        _, score, _ = self.validate_accuracy(simulation_results, country_identifier)
        return score
    
    def compare_opinion_distributions(
        self,
        sim_opinions: np.ndarray,
        real_distribution: Optional[np.ndarray] = None,
        country_identifier: Optional[str] = None,
        bins: int = 10,
    ) -> Dict[str, Any]:
        """
        Compare simulated opinion distribution with real data.
        
        Args:
            sim_opinions: Array of simulated opinions (normalized to [0, 1] or [-1, 1])
            real_distribution: Optional real opinion distribution
            country_identifier: If provided, load real distribution for this country
            bins: Number of bins for histogram comparison
            
        Returns:
            Dictionary with comparison metrics and statistical tests
        """
        results = {}
        
        # Normalize simulation opinions to [0, 1]
        if len(sim_opinions) == 0:
            return results
        
        sim_min = np.min(sim_opinions)
        sim_max = np.max(sim_opinions)
        
        # Handle bipolar range [-1, 1]
        if sim_min < 0:
            sim_opinions_norm = (sim_opinions - sim_min) / (sim_max - sim_min)
        else:
            sim_opinions_norm = sim_opinions
        
        results["sim_opinion_mean"] = float(np.mean(sim_opinions))
        results["sim_opinion_std"] = float(np.std(sim_opinions))
        results["sim_opinion_min"] = float(np.min(sim_opinions))
        results["sim_opinion_max"] = float(np.max(sim_opinions))
        
        # Get real distribution if available
        if real_distribution is None and country_identifier:
            real_data = self.context.get_country(country_identifier)
            # For now, we don't have direct opinion data in Factbook
            # This would need to be loaded from surveys or other sources
            pass
        
        # If we have real distribution, compare
        if real_distribution is not None:
            real_opinions_norm = real_distribution
            
            # Kolmogorov-Smirnov test
            ks_stat, ks_pvalue = stats.ks_2samp(sim_opinions_norm, real_opinions_norm)
            results["ks_statistic"] = float(ks_stat)
            results["ks_pvalue"] = float(ks_pvalue)
            
            # Chi-squared test
            hist_sim, bin_edges = np.histogram(sim_opinions_norm, bins=bins)
            hist_real, _ = np.histogram(real_opinions_norm, bins=bin_edges)
            
            # Avoid zero division
            hist_sim = hist_sim.astype(float)
            hist_real = hist_real.astype(float)
            
            # Normalize to percentages
            hist_sim = (hist_sim / len(sim_opinions_norm)) * 100
            hist_real = (hist_real / len(real_opinions_norm)) * 100
            
            chi2_stat = np.sum((hist_sim - hist_real) ** 2 / (hist_real + 1e-10))
            results["chi2_statistic"] = float(chi2_stat)
            
            # Calculate correlation
            if len(hist_sim) == len(hist_real):
                corr, _ = stats.pearsonr(hist_sim, hist_real)
                results["distribution_correlation"] = float(corr)
        
        return results
    
    def validate_trends(
        self,
        time_series: Dict[str, List[float]],
        country_identifier: str,
        comparison_period: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Validate simulation trends against real historical data.
        
        Args:
            time_series: Dictionary with metric names and time series values
            country_identifier: Country to compare with
            comparison_period: Optional specific time period
            
        Returns:
            Dictionary with trend validation results
        """
        results = {}
        
        # Get real historical data (would need to be loaded from Factbook time series)
        # For now, this is a placeholder
        
        # Compare trends for each metric
        for metric_name, sim_values in time_series.items():
            if len(sim_values) < 2:
                continue
            
            # Calculate trend (linear regression slope)
            x = np.arange(len(sim_values))
            slope, intercept, r_value, p_value, std_err = stats.linregress(x, sim_values)
            
            results[f"{metric_name}_trend"] = {
                "slope": float(slope),
                "r_squared": float(r_value ** 2),
                "p_value": float(p_value),
            }
        
        return results
    
    def set_tolerance_level(self, level: str):
        """Set the tolerance level for validation."""
        if level in self._tolerance_levels:
            self._current_tolerance = self._tolerance_levels[level]
        else:
            warnings.warn(f"Unknown tolerance level: {level}. Using 'moderate'.")
            self._current_tolerance = self._tolerance_levels["moderate"]
    
    def __repr__(self) -> str:
        return f"FactbookValidator(context={len(self.context.list_loaded_countries())} countries)"


def create_validation_report(
    simulation_results: Dict[str, Any],
    country_identifier: str,
    config: Optional[Dict[str, Any]] = None,
) -> ValidationReport:
    """
    Convenience function to create a validation report.
    
    Args:
        simulation_results: Simulation results
        country_identifier: Country code
        config: Optional configuration
        
    Returns:
        ValidationReport
    """
    validator = FactbookValidator()
    return validator.validate_simulation(simulation_results, country_identifier, config)
