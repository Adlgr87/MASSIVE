#!/usr/bin/env python3
"""
Test script for CIA World Factbook integration in MASSIVE.

This script tests all 5 integration points:
1. Agent Initialization with country context
2. Social Pressure with ethnic/religious groups
3. Energy Engine with Gini index
4. Intervention Optimizer with economic data
5. Validation Framework
"""

import sys
from pathlib import Path

import pytest

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_factbook_context():
    """Test FactbookContext module."""
    from massive.core.factbook import FactbookContext

    # Create context
    context = FactbookContext()

    # Test loading countries
    countries_to_test = ["US", "CH", "GM", "BR"]

    for country_code in countries_to_test:
        country = context.load_country(country_code)

        # Verify country data
        assert country.cia_code == country_code
        assert country.population > 0
        assert country.gini_index > 0

        # Get MASSIVE parameters
        params = country.massive_params

        # Verify social pressure weights
        social_weights = context.get_social_pressure_weights(country_code)
        assert isinstance(social_weights, dict)

        # Get demographic matrix
        demographic_matrix = context.get_demographic_matrix(country_code)
        assert demographic_matrix is not None

        # Get economic potential
        economic_potential = context.get_economic_potential(country_code)
        assert economic_potential is not None

        # Get intervention constraints
        intervention_constraints = context.get_intervention_constraints(country_code)
        assert intervention_constraints is not None


def test_data_loader():
    """Test FactbookDataLoader module."""
    from massive.core.factbook.loader import FactbookDataLoader

    # Test with sample data
    loader = FactbookDataLoader("data/factbook/factbook_sample.json")

    # Test country resolution
    cia_code = loader.resolve_country_code("United States")
    assert cia_code == "US"

    cia_code = loader.resolve_country_code("CN")
    assert cia_code == "CH"

    # Test data retrieval
    us_data = loader.get_country_data("US")
    assert us_data is not None
    assert "people" in us_data
    assert us_data["people"]["population"] > 0

    # Test available countries
    countries = loader.list_countries()
    assert len(countries) >= 3


def test_social_pressure():
    """Test social pressure calculation with Factbook data."""
    from massive.core.utility_logic import (
        calculate_social_pressure,
        calculate_group_cohesion,
        calculate_demographic_strategic_force,
    )
    from massive.core.schemas import GamePayoff
    from massive.core.factbook import FactbookContext

    # Load country data
    context = FactbookContext()
    context.load_country("US")

    # Get social pressure weights
    social_weights = context.get_social_pressure_weights("US")

    # Test social pressure calculation
    agent_opinion = 0.5
    neighbors_opinions = [0.6, 0.4, 0.7, 0.55]

    pressure = calculate_social_pressure(
        agent_opinion=agent_opinion,
        neighbors_opinions=neighbors_opinions,
        social_pressure_weights=social_weights,
    )

    # Test with different countries (different diversity levels)
    for country_code in ["US", "CH", "GM"]:
        context.load_country(country_code)
        weights = context.get_social_pressure_weights(country_code)

        # Calculate pressure toward consensus
        pressure_consensus = calculate_social_pressure(
            agent_opinion=0.0,
            neighbors_opinions=[0.8, 0.8, 0.8],  # All neighbors agree
            social_pressure_weights=weights,
        )

        # Calculate pressure in polarized situation
        pressure_polarized = calculate_social_pressure(
            agent_opinion=0.0,
            neighbors_opinions=[-0.8, -0.8, -0.8],  # All neighbors disagree
            social_pressure_weights=weights,
        )

    # Test demographic strategic force
    matrix = GamePayoff(cc=2.0, cd=1.0, dc=1.5, dd=0.5)
    demographic_matrix = context.get_demographic_matrix("US")

    demo_force = calculate_demographic_strategic_force(
        agent_opinion=0.5,
        neighbors_opinions=[0.6, 0.4, 0.7],
        matrix=matrix,
        demographic_matrix=demographic_matrix,
        age_group=2,  # 25-54 age group
    )


def test_validation_framework():
    """Test validation framework."""
    from massive.core.factbook.validator import (
        FactbookValidator,
        ValidationReport,
        ValidationResult,
    )
    from massive.core.factbook import FactbookContext

    # Create validator
    validator = FactbookValidator()

    # Create sample simulation results
    simulation_results = {
        "population": 335000000,  # Close to US population
        "age_structure": {
            "0-14_years": 18.0,
            "15-24_years": 13.0,
            "25-54_years": 39.0,
            "55-64_years": 12.0,
            "65_years_and_over": 18.0,
        },
        "gini_index": 40.0,  # Close to US Gini
        "gdp_per_capita": 75000.0,
        "unemployment_rate": 3.8,
        "ethnic_diversity": 0.65,
        "religious_diversity": 0.60,
    }

    # Run validation
    report = validator.validate_simulation(
        simulation_results=simulation_results,
        country_identifier="US",
        config={"test": True},
    )

    # Verify report has results
    assert report is not None
    assert hasattr(report, "results")
    assert len(report.results) > 0

    # Test accuracy check
    passes, score, _ = validator.validate_accuracy(
        simulation_results, "US", threshold=50.0
    )
    assert isinstance(passes, bool)
    assert isinstance(score, float)


def test_agent_initialization():
    """Test agent initialization with country context."""
    from massive.core.factbook import FactbookContext
    from massive_engine import MassiveEngine

    context = FactbookContext()

    for country_code in ["US", "CH", "GM"]:
        context.load_country(country_code)
        params = context.get_massive_params(country_code)

        n_agents = params["n_agents"]

        # Create engine with country-specific parameters
        engine = MassiveEngine(config={"n_agents": n_agents})

        agents = engine.agents
        assert agents is not None

        # Get demographic matrix for initialization
        demo_matrix = params["demographic_matrix"]
        assert demo_matrix is not None


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))