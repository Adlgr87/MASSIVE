"""
Test script for CIA World Factbook integration in MASSIVE.
Tests all 5 integration points.
"""

import logging
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

log = logging.getLogger("test_factbook")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


class TestFactbookContext:
    def test_load_countries(self):
        from massive.core.factbook import FactbookContext

        context = FactbookContext()
        for country_code in ["US", "CH", "GM"]:
            country = context.load_country(country_code)
            assert country.cia_code == country_code
            assert country.population > 0
            assert country.gini_index > 0

    def test_helper_methods(self):
        from massive.core.factbook import FactbookContext

        context = FactbookContext()
        assert context.get_social_pressure_weights("US") is not None
        dm = context.get_demographic_matrix("US")
        assert dm is not None
        assert context.get_economic_potential("US") is not None
        assert context.get_intervention_constraints("US") is not None


class TestFactbookDataLoader:
    def test_country_code_resolution(self):
        from massive.core.factbook.loader import FactbookDataLoader

        loader = FactbookDataLoader("data/factbook/factbook_sample.json")
        assert loader.resolve_country_code("United States") == "US"
        assert loader.resolve_country_code("CN") == "CH"

    def test_data_retrieval(self):
        from massive.core.factbook.loader import FactbookDataLoader

        loader = FactbookDataLoader("data/factbook/factbook_sample.json")
        us_data = loader.get_country_data("US")
        assert us_data is not None
        assert "people" in us_data
        assert us_data["people"]["population"] > 0

    def test_list_countries(self):
        from massive.core.factbook.loader import FactbookDataLoader

        loader = FactbookDataLoader("data/factbook/factbook_sample.json")
        assert len(loader.list_countries()) >= 3


class TestSocialPressureIntegration:
    def test_social_pressure_calculation(self):
        from massive.core.factbook import FactbookContext
        from massive.core.utility_logic import calculate_social_pressure

        context = FactbookContext()
        weights = context.get_social_pressure_weights("US")
        pressure = calculate_social_pressure(
            agent_opinion=0.5,
            neighbors_opinions=[0.6, 0.4, 0.7, 0.55],
            social_pressure_weights=weights,
        )
        log.info(f"social pressure: {pressure:.4f}")

    def test_country_consensus_pressure(self):
        from massive.core.factbook import FactbookContext
        from massive.core.utility_logic import calculate_social_pressure

        context = FactbookContext()
        for cc in ["US", "CH", "GM"]:
            weights = context.get_social_pressure_weights(cc)
            p = calculate_social_pressure(0.0, [0.8, 0.8, 0.8], weights)
            log.info(f"{cc} consensus pressure: {p:.4f}")

    def test_country_polarized_pressure(self):
        from massive.core.factbook import FactbookContext
        from massive.core.utility_logic import calculate_social_pressure

        context = FactbookContext()
        for cc in ["US", "CH", "GM"]:
            weights = context.get_social_pressure_weights(cc)
            p = calculate_social_pressure(0.0, [-0.8, -0.8, -0.8], weights)
            log.info(f"{cc} polarized pressure: {p:.4f}")

    def test_demographic_strategic_force(self):
        from massive.core.factbook import FactbookContext
        from massive.core.schemas import GamePayoff
        from massive.core.utility_logic import calculate_demographic_strategic_force

        context = FactbookContext()
        dm = context.get_demographic_matrix("US")
        matrix = GamePayoff(cc=2.0, cd=1.0, dc=1.5, dd=0.5)
        f = calculate_demographic_strategic_force(
            agent_opinion=0.5,
            neighbors_opinions=[0.6, 0.4, 0.7],
            matrix=matrix,
            demographic_matrix=dm,
            age_group=2,
        )
        log.info(f"demographic strategic force: {f:.4f}")


class TestEnergyEngineIntegration:
    def test_energy_engine_gini_adjusted_landscape(self):
        from energy_engine import SocialEnergyEngine
        from massive.core.factbook import FactbookContext

        context = FactbookContext()
        for cc in ["US", "CH", "GM"]:
            context.load_country(cc)
            context.get_country(cc)
            engine = SocialEnergyEngine(
                range_type="bipolar",
                temperature=0.05,
                lambda_social=0.5,
                gini_coefficient=context.get_gini_coefficient(cc),
                inequality_factor=context.get_inequality_factor(cc),
                economic_potential=context.get_economic_potential(cc),
            )
            attractors = [{"position": 0.5, "strength": 2.0}, {"position": -0.5, "strength": 1.5}]
            repellers = [{"position": 0.0, "strength": 1.0}]
            adj_a, adj_r = engine.create_gini_adjusted_landscape(attractors, repellers)
            log.info(f"{cc} adjusted attractor strength: {adj_a[0]['strength']:.3f}")

    def test_energy_engine_step(self):
        import numpy as np

        from energy_engine import SocialEnergyEngine
        from massive.core.factbook import FactbookContext

        context = FactbookContext()
        for cc in ["US", "CH", "GM"]:
            context.load_country(cc)
            context.get_country(cc)
            engine = SocialEnergyEngine(
                range_type="bipolar",
                temperature=0.05,
                lambda_social=0.5,
                gini_coefficient=context.get_gini_coefficient(cc),
                inequality_factor=context.get_inequality_factor(cc),
                economic_potential=context.get_economic_potential(cc),
            )
            n = 100
            opinions = np.random.uniform(-1, 1, n)
            adj = np.random.random((n, n))
            adj = (adj + adj.T) / 2
            np.fill_diagonal(adj, 0)
            attractors = [{"position": 0.5, "strength": 2.0}, {"position": -0.5, "strength": 1.5}]
            repellers = [{"position": 0.0, "strength": 1.0}]
            adj_a, adj_r = engine.create_gini_adjusted_landscape(attractors, repellers)
            new_ops = engine.step(opinions, adj, adj_a, adj_r, eta=0.01)
            assert new_ops.shape == opinions.shape
            assert new_ops.min() >= -1.0
            assert new_ops.max() <= 1.0

    def test_energy_engine_economic_landscape(self):
        from energy_engine import SocialEnergyEngine
        from massive.core.factbook import FactbookContext

        context = FactbookContext()
        for cc in ["US", "CH", "GM"]:
            context.load_country(cc)
            country = context.get_country(cc)
            engine = SocialEnergyEngine(
                range_type="bipolar",
                temperature=0.05,
                lambda_social=0.5,
                gini_coefficient=context.get_gini_coefficient(cc),
                inequality_factor=context.get_inequality_factor(cc),
                economic_potential=context.get_economic_potential(cc),
            )
            ea, er = engine.create_economic_landscape(
                mean_income=country.gdp_per_capita,
                n_attractors=2,
                n_repellers=1,
            )
            assert len(ea) == 2
            assert len(er) == 1


class TestInterventionOptimizerIntegration:
    def test_optimize_interventions(self):
        import numpy as np

        from massive.core.factbook import FactbookContext
        from massive.core.intervention_optimizer import optimize_interventions

        def evaluate_fn(interventions):
            avg = np.mean(interventions)
            consistency = 1.0 - np.std(interventions) * 2.0
            return float(consistency * (1.0 + abs(avg)))

        context = FactbookContext()
        for cc in ["US", "CH", "GM"]:
            context.load_country(cc)
            constraints = context.get_intervention_constraints(cc)
            result = optimize_interventions(
                evaluate_fn=evaluate_fn,
                n_agents=100,
                n_phases=5,
                max_iter=50,
                country_code=cc,
                **constraints,
            )
            assert result is not None
            assert "score" in result
            assert "cost" in result
            assert "feasibility" in result
            assert "interventions" in result

    def test_estimate_intervention_cost(self):
        from massive.core.factbook import FactbookContext
        from massive.core.intervention_optimizer import estimate_intervention_cost

        rng = np.random.default_rng(42)
        context = FactbookContext()
        for cc in ["US", "CH", "GM"]:
            constraints = context.get_intervention_constraints(cc)
            # Contract: interventions is a (n_phases, n_agents) matrix
            # (see massive/core/intervention_optimizer.py::estimate_intervention_cost).
            interventions = rng.uniform(-1, 1, (5, 20))
            cost = estimate_intervention_cost(
                interventions,
                constraints.get("cost_scale_factor", 1.0),
                constraints.get("fiscal_constraint", 0.5),
            )
            assert cost >= 0

    def test_economic_aware_optimizer(self):
        import numpy as np

        from massive.core.intervention_optimizer import create_economic_aware_optimizer

        def evaluate_fn(interventions):
            avg = np.mean(interventions)
            consistency = 1.0 - np.std(interventions) * 2.0
            return float(consistency * (1.0 + abs(avg)))

        opt = create_economic_aware_optimizer("US")
        result = opt(evaluate_fn, n_agents=100, n_phases=5, max_iter=50)
        assert result is not None
        assert "score" in result


class TestValidationFramework:
    def test_validate_simulation(self):
        from massive.core.factbook.validator import FactbookValidator

        validator = FactbookValidator()
        sim = {
            "population": 335000000,
            "age_structure": {
                "0-14_years": 18.0,
                "15-24_years": 13.0,
                "25-54_years": 39.0,
                "55-64_years": 12.0,
                "65_years_and_over": 18.0,
            },
            "gini_index": 40.0,
            "gdp_per_capita": 75000.0,
            "unemployment_rate": 3.8,
            "ethnic_diversity": 0.65,
            "religious_diversity": 0.60,
        }
        report = validator.validate_simulation(
            simulation_results=sim, country_identifier="US", config={"test": True}
        )
        log.info(f"overall score: {report.overall_score:.2f}")

    def test_report_summary(self):
        from massive.core.factbook.validator import FactbookValidator

        validator = FactbookValidator()
        sim = {
            "population": 335000000,
            "age_structure": {
                "0-14_years": 18.0,
                "15-24_years": 13.0,
                "25-54_years": 39.0,
                "55-64_years": 12.0,
                "65_years_and_over": 18.0,
            },
            "gini_index": 40.0,
            "gdp_per_capita": 75000.0,
            "unemployment_rate": 3.8,
            "ethnic_diversity": 0.65,
            "religious_diversity": 0.60,
        }
        report = validator.validate_simulation(
            simulation_results=sim, country_identifier="US", config={"test": True}
        )
        summary = report.get_summary()
        log.info(f"summary: {summary}")
        bw = report.get_best_worst(3)
        for r in bw["best"]:
            log.info(f"best: {r['metric_name']}: {r['score']:.1f}")
        for r in bw["worst"]:
            log.info(f"worst: {r['metric_name']}: {r['score']:.1f}")

    def test_accuracy_check(self):
        from massive.core.factbook.validator import FactbookValidator

        validator = FactbookValidator()
        sim = {
            "population": 335000000,
            "age_structure": {
                "0-14_years": 18.0,
                "15-24_years": 13.0,
                "25-54_years": 39.0,
                "55-64_years": 12.0,
                "65_years_and_over": 18.0,
            },
            "gini_index": 40.0,
            "gdp_per_capita": 75000.0,
            "unemployment_rate": 3.8,
            "ethnic_diversity": 0.65,
            "religious_diversity": 0.60,
        }
        passes, score, _ = validator.validate_accuracy(sim, "US", threshold=50.0)
        log.info(f"accuracy check: {'PASS' if passes else 'FAIL'}, score={score:.2f}")

    def test_report_saving(self, tmp_path):
        from massive.core.factbook.validator import FactbookValidator

        validator = FactbookValidator()
        sim = {
            "population": 335000000,
            "age_structure": {
                "0-14_years": 18.0,
                "15-24_years": 13.0,
                "25-54_years": 39.0,
                "55-64_years": 12.0,
                "65_years_and_over": 18.0,
            },
            "gini_index": 40.0,
            "gdp_per_capita": 75000.0,
            "unemployment_rate": 3.8,
            "ethnic_diversity": 0.65,
            "religious_diversity": 0.60,
        }
        report = validator.validate_simulation(
            simulation_results=sim, country_identifier="US", config={"test": True}
        )
        # Save to pytest tmp dir — the default path writes into the repo tree
        # (reports/factbook_validation_*.json) and dirties the working copy.
        report_path = report.save(tmp_path / "factbook_validation_test.json")
        assert Path(report_path).exists()


class TestAgentInitialization:
    def test_engine_creation(self):
        from massive.core.factbook import FactbookContext
        from massive_engine import MassiveEngine

        context = FactbookContext()
        for cc in ["US", "CH", "GM"]:
            context.load_country(cc)
            params = context.get_massive_params(cc)
            n_agents = params["n_agents"]
            engine = MassiveEngine(config={"n_agents": n_agents})
            agents = engine.agents
            assert agents.shape[0] == n_agents
            dm = params["demographic_matrix"]
            log.info(f"{cc} demographics: {dm.shape}")
