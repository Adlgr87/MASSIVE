#!/usr/bin/env python3
"""
Test script for CIA World Factbook integration in MASSIVE.

This script tests all 5 integration points:
1. Agent Initialization with country context
2. Social Pressure with ethnic/religious groups
3. Energy Engine with Gini index
4. Intervention Optimizer with economic data
5. Validation Framework

Usage:
    python test_factbook_integration.py
    python test_factbook_integration.py --country US
    python test_factbook_integration.py --test social_pressure
"""

import sys
import argparse
import logging
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("test_factbook")


def test_factbook_context():
    """Test FactbookContext module."""
    log.info("=" * 60)
    log.info("TEST 1: FactbookContext Module")
    log.info("=" * 60)
    
    try:
        from massive.core.factbook import FactbookContext
        
        # Create context
        context = FactbookContext()
        
        # Test loading countries
        countries_to_test = ["US", "CH", "GM"]
        
        for country_code in countries_to_test:
            log.info(f"\n--- Testing country: {country_code} ---")
            country = context.load_country(country_code)
            
            # Verify country data
            assert country.cia_code == country_code
            assert country.population > 0
            assert country.gini_index > 0
            
            # Get MASSIVE parameters
            params = country.massive_params
            
            log.info(f"  Name: {country.country_name}")
            log.info(f"  Population: {country.population:,}")
            log.info(f"  Gini Index: {country.gini_index}")
            log.info(f"  Ethnic Diversity: {country.ethnic_diversity:.3f}")
            log.info(f"  Religious Diversity: {country.religious_diversity:.3f}")
            log.info(f"  MASSIVE Agents: {params['n_agents']}")
            log.info(f"  Gini Coefficient: {params['gini_coefficient']:.3f}")
            log.info(f"  Inequality Factor: {params['inequality_factor']:.3f}")
            
            # Test helper methods
            social_weights = context.get_social_pressure_weights(country_code)
            log.info(f"  Social Pressure Weights: {social_weights}")
            
            demographic_matrix = context.get_demographic_matrix(country_code)
            log.info(f"  Demographic Matrix Shape: {demographic_matrix.shape}")
            
            economic_potential = context.get_economic_potential(country_code)
            log.info(f"  Economic Potential: {economic_potential}")
            
            intervention_constraints = context.get_intervention_constraints(country_code)
            log.info(f"  Intervention Constraints: {intervention_constraints}")
        
        log.info("\n✅ FactbookContext tests PASSED")
        return True
        
    except Exception as e:
        log.error(f"❌ FactbookContext tests FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_data_loader():
    """Test FactbookDataLoader module."""
    log.info("\n" + "=" * 60)
    log.info("TEST 2: FactbookDataLoader Module")
    log.info("=" * 60)
    
    try:
        from massive.core.factbook.loader import FactbookDataLoader
        
        # Test with sample data
        loader = FactbookDataLoader("data/factbook/factbook_sample.json")
        
        # Test country resolution
        cia_code = loader.resolve_country_code("United States")
        assert cia_code == "US"
        log.info(f"✓ Country code resolution: United States -> {cia_code}")
        
        cia_code = loader.resolve_country_code("CN")
        assert cia_code == "CH"
        log.info(f"✓ Country code resolution: CN -> {cia_code}")
        
        # Test data retrieval
        us_data = loader.get_country_data("US")
        assert us_data is not None
        assert "people" in us_data
        assert us_data["people"]["population"] > 0
        log.info(f"✓ Data retrieval: US population = {us_data['people']['population']:,}")
        
        # Test available countries
        countries = loader.list_countries()
        assert len(countries) >= 3
        log.info(f"✓ Loaded countries: {countries}")
        
        log.info("\n✅ FactbookDataLoader tests PASSED")
        return True
        
    except Exception as e:
        log.error(f"❌ FactbookDataLoader tests FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_social_pressure():
    """Test social pressure calculation with Factbook data."""
    log.info("\n" + "=" * 60)
    log.info("TEST 3: Social Pressure Integration (Point 2)")
    log.info("=" * 60)
    
    try:
        from massive.core.utility_logic import (
            calculate_social_pressure,
            calculate_group_cohesion,
            calculate_demographic_strategic_force,
        )
        from massive.core.schemas import GamePayoff
        from massive.core.factbook import FactbookContext
        
        # Load country data
        context = FactbookContext()
        country = context.load_country("US")
        
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
        
        log.info(f"✓ Social pressure calculation: {pressure:.4f}")
        log.info(f"  Agent opinion: {agent_opinion}")
        log.info(f"  Neighbors: {neighbors_opinions}")
        log.info(f"  Social weights: {social_weights}")
        
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
            
            log.info(f"✓ {country_code} consensus pressure: {pressure_consensus:.4f}")
            
            # Calculate pressure in polarized situation
            pressure_polarized = calculate_social_pressure(
                agent_opinion=0.0,
                neighbors_opinions=[-0.8, -0.8, -0.8],  # All neighbors disagree
                social_pressure_weights=weights,
            )
            
            log.info(f"✓ {country_code} polarized pressure: {pressure_polarized:.4f}")
        
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
        
        log.info(f"✓ Demographic strategic force: {demo_force:.4f}")
        
        log.info("\n✅ Social Pressure tests PASSED")
        return True
        
    except Exception as e:
        log.error(f"❌ Social Pressure tests FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_energy_engine():
    """Test energy engine with Gini index."""
    log.info("\n" + "=" * 60)
    log.info("TEST 4: Energy Engine Integration (Point 3)")
    log.info("=" * 60)
    
    try:
        from energy_engine import SocialEnergyEngine
        from massive.core.factbook import FactbookContext
        import numpy as np
        
        # Load country data
        context = FactbookContext()
        
        for country_code in ["US", "CH", "GM"]:
            context.load_country(country_code)
            country = context.get_country(country_code)
            
            # Get economic parameters
            gini_coeff = context.get_gini_coefficient(country_code)
            inequality_factor = context.get_inequality_factor(country_code)
            economic_potential = context.get_economic_potential(country_code)
            
            # Create energy engine with Factbook parameters
            engine = SocialEnergyEngine(
                range_type="bipolar",
                temperature=0.05,
                lambda_social=0.5,
                gini_coefficient=gini_coeff,
                inequality_factor=inequality_factor,
                economic_potential=economic_potential,
            )
            
            log.info(f"\n--- {country_code} Energy Engine ---")
            log.info(f"  Gini Coefficient: {engine.gini_coefficient:.3f}")
            log.info(f"  Inequality Factor: {engine.inequality_factor:.3f}")
            log.info(f"  Lambda Social: {engine.lambda_social:.3f}")
            
            # Create sample opinions
            n_agents = 100
            opinions = np.random.uniform(-1, 1, n_agents)
            
            # Create simple adjacency matrix
            adj = np.random.random((n_agents, n_agents))
            adj = (adj + adj.T) / 2  # Symmetrize
            np.fill_diagonal(adj, 0)
            
            # Create basic attractors and repellers
            attractors = [{"position": 0.5, "strength": 2.0}, {"position": -0.5, "strength": 1.5}]
            repellers = [{"position": 0.0, "strength": 1.0}]
            
            # Test Gini-adjusted landscape
            adj_attractors, adj_repellers = engine.create_gini_adjusted_landscape(
                attractors, repellers
            )
            
            log.info(f"  Original attractor strength: {attractors[0]['strength']}")
            log.info(f"  Adjusted attractor strength: {adj_attractors[0]['strength']:.3f}")
            
            # Run one step
            new_opinions = engine.step(opinions, adj, adj_attractors, adj_repellers, eta=0.01)
            
            log.info(f"  Opinion range: [{new_opinions.min():.3f}, {new_opinions.max():.3f}]")
            log.info(f"  Opinion mean: {new_opinions.mean():.3f}")
            
            # Test economic landscape creation
            econ_attractors, econ_repellers = engine.create_economic_landscape(
                mean_income=country.gdp_per_capita,
                n_attractors=2,
                n_repellers=1,
            )
            
            log.info(f"  Economic attractors: {len(econ_attractors)}")
            log.info(f"  Economic repellers: {len(econ_repellers)}")
        
        log.info("\n✅ Energy Engine tests PASSED")
        return True
        
    except Exception as e:
        log.error(f"❌ Energy Engine tests FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_intervention_optimizer():
    """Test intervention optimizer with economic data."""
    log.info("\n" + "=" * 60)
    log.info("TEST 5: Intervention Optimizer Integration (Point 4)")
    log.info("=" * 60)
    
    try:
        from massive.core.intervention_optimizer import (
            optimize_interventions,
            create_economic_aware_optimizer,
            estimate_intervention_cost,
            get_intervention_feasibility,
        )
        from massive.core.factbook import FactbookContext
        import numpy as np
        
        # Create simple evaluation function
        def evaluate_fn(interventions):
            """Simple evaluation: higher score for more consistent interventions."""
            # Favor interventions that are mostly positive or mostly negative
            avg = np.mean(interventions)
            consistency = 1.0 - np.std(interventions) * 2.0
            return float(consistency * (1.0 + abs(avg)))
        
        # Test with different countries
        context = FactbookContext()
        
        for country_code in ["US", "CH", "GM"]:
            context.load_country(country_code)
            constraints = context.get_intervention_constraints(country_code)
            
            log.info(f"\n--- {country_code} Intervention Optimization ---")
            log.info(f"  Constraints: {constraints}")
            
            # Optimize interventions
            result = optimize_interventions(
                evaluate_fn=evaluate_fn,
                n_agents=100,
                n_phases=5,
                max_iter=50,
                country_code=country_code,
                **constraints,
            )
            
            log.info(f"  Best score: {result['score']:.4f}")
            log.info(f"  Cost: {result['cost']:.2f}")
            log.info(f"  Feasibility: {result['feasibility']:.2f}")
            
            # Estimate cost
            cost = estimate_intervention_cost(
                result["interventions"],
                constraints.get("cost_scale_factor", 1.0),
                constraints.get("fiscal_constraint", 0.5),
            )
            log.info(f"  Estimated cost: {cost:.2f}")
            
            # Test economic-aware optimizer
            economic_optimizer = create_economic_aware_optimizer(country_code)
            result2 = economic_optimizer(evaluate_fn, n_agents=100, n_phases=5, max_iter=50)
            
            log.info(f"  Economic optimizer score: {result2['score']:.4f}")
        
        log.info("\n✅ Intervention Optimizer tests PASSED")
        return True
        
    except Exception as e:
        log.error(f"❌ Intervention Optimizer tests FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validation_framework():
    """Test validation framework."""
    log.info("\n" + "=" * 60)
    log.info("TEST 6: Validation Framework (Point 5)")
    log.info("=" * 60)
    
    try:
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
        
        log.info(f"\n--- Validation Report for US ---")
        log.info(f"  Overall Score: {report.overall_score:.2f}")
        log.info(f"  Number of Results: {len(report.results)}")
        
        # Show summary
        summary = report.get_summary()
        log.info(f"  Summary: {summary}")
        
        # Show best and worst
        best_worst = report.get_best_worst(3)
        log.info(f"\n  Best Metrics:")
        for result in best_worst["best"]:
            log.info(f"    - {result['metric_name']}: {result['score']:.1f}")
        
        log.info(f"\n  Worst Metrics:")
        for result in best_worst["worst"]:
            log.info(f"    - {result['metric_name']}: {result['score']:.1f}")
        
        # Test accuracy check
        passes, score, _ = validator.validate_accuracy(
            simulation_results, "US", threshold=50.0
        )
        log.info(f"\n  Accuracy Check (threshold=50): {'PASS' if passes else 'FAIL'}")
        log.info(f"  Score: {score:.2f}")
        
        # Save report
        report_path = report.save()
        log.info(f"  Report saved to: {report_path}")
        
        log.info("\n✅ Validation Framework tests PASSED")
        return True
        
    except Exception as e:
        log.error(f"❌ Validation Framework tests FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_initialization():
    """Test agent initialization with country context."""
    log.info("\n" + "=" * 60)
    log.info("TEST 7: Agent Initialization Integration (Point 1)")
    log.info("=" * 60)
    
    try:
        from massive.core.factbook import FactbookContext
        from massive_engine import MassiveEngine
        
        context = FactbookContext()
        
        for country_code in ["US", "CH", "GM"]:
            context.load_country(country_code)
            params = context.get_massive_params(country_code)
            
            n_agents = params["n_agents"]
            
            log.info(f"\n--- {country_code} Agent Initialization ---")
            log.info(f"  Agents: {n_agents}")
            
            # Create engine with country-specific parameters
            engine = MassiveEngine(config={"n_agents": n_agents})
            
            agents = engine.agents
            log.info(f"  Agent shape: {agents.shape}")
            log.info(f"  Agent mean opinion: {agents[:, 0].mean():.3f}")
            
            # Get demographic matrix for initialization
            demo_matrix = params["demographic_matrix"]
            log.info(f"  Demographic matrix shape: {demo_matrix.shape}")
            
            # Calculate age distribution
            age_percentages = [
                params["social_groups"].get("ethnic", {}).get("White", 0) if "US" == country_code else 0
            ]
        
        log.info("\n✅ Agent Initialization tests PASSED")
        return True
        
    except Exception as e:
        log.error(f"❌ Agent Initialization tests FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests or selected test."""
    parser = argparse.ArgumentParser(
        description="Test CIA World Factbook integration in MASSIVE",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_factbook_integration.py          # Run all tests
  python test_factbook_integration.py --test social_pressure  # Run specific test
  python test_factbook_integration.py --country US CH GM  # Test specific countries
        """,
    )
    
    parser.add_argument(
        "--test",
        choices=["all", "context", "loader", "social_pressure", "energy_engine", 
                 "intervention_optimizer", "validation", "agent_initialization"],
        default="all",
        help="Specific test to run (default: all)",
    )
    
    parser.add_argument(
        "--country",
        nargs="+",
        default=["US", "CH", "GM"],
        help="Specific countries to test (default: US, CH, GM)",
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show verbose output",
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Map test names to functions
    test_map = {
        "all": [test_factbook_context, test_data_loader, test_social_pressure, 
                test_energy_engine, test_intervention_optimizer, test_validation_framework,
                test_agent_initialization],
        "context": [test_factbook_context],
        "loader": [test_data_loader],
        "social_pressure": [test_social_pressure],
        "energy_engine": [test_energy_engine],
        "intervention_optimizer": [test_intervention_optimizer],
        "validation": [test_validation_framework],
        "agent_initialization": [test_agent_initialization],
    }
    
    # Get tests to run
    tests_to_run = test_map.get(args.test, [test_factbook_context])
    
    log.info("\n" + "=" * 60)
    log.info("CIA WORLD FACTBOOK INTEGRATION TESTS")
    log.info("=" * 60)
    log.info(f"Running {len(tests_to_run)} test(s)")
    log.info(f"Countries: {', '.join(args.country)}")
    
    # Run tests
    results = []
    for test_func in tests_to_run:
        try:
            result = test_func()
            results.append(result)
        except Exception as e:
            log.error(f"❌ Test {test_func.__name__} CRASHED: {e}")
            results.append(False)
    
    # Summary
    log.info("\n" + "=" * 60)
    log.info("TEST SUMMARY")
    log.info("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    log.info(f"Passed: {passed}/{total}")
    log.info(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        log.info("\n🎉 ALL TESTS PASSED! Factbook integration is working correctly.")
        return 0
    else:
        log.error("\n⚠️  Some tests failed. Check the logs above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
