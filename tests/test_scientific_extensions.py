import unittest

import numpy as np

from massive_core.data_assimilation import EnsembleKalmanFilter
from massive_core.dynamical_systems import BifurcationAnalyzer
from massive_core.metalearning import MetaRegimeSelector
from massive_core.multiscale import MultiTimescaleEngine
from massive_core.network_inference import NetworkReconstructor
from massive_core.numerics import AdaptiveODESolver, StabilityAnalyzer
from massive_core.physics import AgentHydrodynamics, PerturbationTheorySolver, StatisticalMechanicsEngine


class ScientificExtensionTests(unittest.TestCase):
    def test_adaptive_solver_clips_and_reports_method(self):
        solver = AdaptiveODESolver(
            drift=lambda x: -0.5 * x,
            diffusion=0.0,
            bounds=(-1.0, 1.0),
            rng=np.random.default_rng(0),
        )

        x_next, dt_next = solver.step(np.array([0.8]), 0.1)

        self.assertTrue(-1.0 <= x_next[0] <= 1.0)
        self.assertGreater(dt_next, 0.0)
        self.assertIsNotNone(solver.last_diagnostics)
        self.assertIn(solver.last_diagnostics.method, {"milstein", "rk4_maruyama", "implicit_euler_maruyama"})

    def test_stability_analyzer_identifies_stable_linear_field(self):
        analyzer = StabilityAnalyzer(lambda x: -2.0 * x)

        report = analyzer.analyze_linear_stability(np.array([1.0]))

        self.assertTrue(report.stable)
        self.assertAlmostEqual(report.max_real_eigenvalue, -2.0, places=4)
        self.assertAlmostEqual(analyzer.compute_spectral_radius(np.array([[0.5, 0.0], [0.0, 0.25]])), 0.5, places=4)

    def test_ensemble_kalman_filter_update_moves_mean_toward_observation(self):
        initial = np.array([[-1.0], [0.0], [1.0], [2.0]])
        enkf = EnsembleKalmanFilter(
            n_ensemble=4,
            n_state_dim=1,
            observation_covariance=np.array([[1e-6]]),
            initial_ensemble=initial,
            rng=np.random.default_rng(1),
        )
        before, _ = enkf.get_state_estimate()

        enkf.update(np.array([4.0]))
        after, _ = enkf.get_state_estimate()

        self.assertGreater(abs(before[0] - 4.0), abs(after[0] - 4.0))

    def test_bifurcation_analyzer_reports_stability_change(self):
        analyzer = BifurcationAnalyzer(lambda param: (lambda x: param * x - x**3), bounds=(-2.0, 2.0))

        diagram = analyzer.detect_bifurcation_diagram(np.array([-0.5, 0.5]), np.array([0.01]), n_steps=50, dt=0.05)

        self.assertEqual(diagram["fixed_points"].shape, (2, 1))
        self.assertGreaterEqual(len(diagram["bifurcation_points"]), 1)

    def test_multiscale_engine_keeps_state_in_bounds(self):
        engine = MultiTimescaleEngine(
            timescales={"slow": {"tau": 1.0, "amplitude": 0.0}},
            bounds=(0.0, 1.0),
            rng=np.random.default_rng(2),
        )

        x_next = engine.step(np.array([0.95]), 0.1, drift=lambda x: np.ones_like(x))

        self.assertTrue(0.0 <= x_next[0] <= 1.0)

    def test_physics_helpers_return_valid_observables(self):
        stat = StatisticalMechanicsEngine(effective_temperature=1.0)
        self.assertAlmostEqual(stat.compute_entropy(np.array([0.5, 0.5])), np.log(2.0))
        self.assertLess(stat.compute_free_energy(np.array([0.0, 1.0])), 0.0)

        perturb = PerturbationTheorySolver(dt=0.1, n_steps=3, bounds=(-1.0, 1.0))
        trajectory = perturb.compute_perturbation_expansion(
            np.array([0.0]),
            base_system=lambda x: np.ones_like(x) * 0.1,
            perturbation=lambda x: np.ones_like(x) * 0.2,
            epsilon=0.5,
            order=1,
        )
        self.assertEqual(trajectory.shape, (4, 1))

        hydro = AgentHydrodynamics(grid=np.linspace(-1.0, 1.0, 21))
        density = hydro.compute_density_field(np.array([-0.2, 0.2]), kernel_bandwidth=0.2)
        self.assertTrue(np.all(density >= 0.0))
        self.assertAlmostEqual(np.trapezoid(density, hydro.grid), 1.0, places=3)

    def test_network_reconstruction_and_meta_selector(self):
        t = np.linspace(0.0, 1.0, 20)
        trajectories = np.column_stack([t, t + 0.01, 1.0 - t])
        adjacency = NetworkReconstructor().reconstruct_correlation_based(trajectories, threshold=0.9)
        self.assertEqual(adjacency.shape, (3, 3))
        self.assertEqual(adjacency[0, 0], 0.0)
        self.assertEqual(adjacency[0, 1], 1.0)

        selector = MetaRegimeSelector(n_rules=3)
        selector.update_performance(1, 2.0)
        probabilities = selector.predict_proba(trajectories, trajectories[-1], {"pressure": 0.5})
        self.assertEqual(probabilities.shape, (3,))
        self.assertAlmostEqual(float(np.sum(probabilities)), 1.0)
        self.assertEqual(int(np.argmax(probabilities)), 1)


if __name__ == "__main__":
    unittest.main()
