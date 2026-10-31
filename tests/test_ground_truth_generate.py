"""Tests for the pure, deterministic parts of ``ground_truth/_generate.py``.

This module generates the SEALED ground-truth data (splits, provenance) and had
**zero** test coverage, which is the worst possible place for an untested module:
the seals depend on it. The file-writing entry points are exercised only via the
conftest-guarded paths, so these tests cover the pure computational core:

* the IPF synthetic-microdata fitter (SAFE methodology),
* the Gini coefficient,
* synthetic microdata generation (shape, bounds, reproducibility),
* network topology metrics (keys, reproducibility).
"""

from __future__ import annotations

import numpy as np
import pytest

import ground_truth._generate as gen


class TestGini:
    def test_uniform_distribution_is_zero(self):
        assert gen._gini(np.array([1.0, 1.0, 1.0, 1.0])) == pytest.approx(0.0)

    def test_extreme_concentration_approaches_one(self):
        g = gen._gini(np.array([0.0, 0.0, 0.0, 100.0]))
        assert g > 0.7

    def test_gini_is_order_invariant(self):
        assert gen._gini(np.array([1.0, 2.0, 3.0])) == pytest.approx(
            gen._gini(np.array([3.0, 1.0, 2.0]))
        )

    def test_gini_is_scale_invariant(self):
        assert gen._gini(np.array([1.0, 2.0, 3.0])) == pytest.approx(
            gen._gini(np.array([10.0, 20.0, 30.0]))
        )


class TestIterativeProportionalFitting:
    def test_result_matches_target_marginals(self):
        shape = (2, 3)
        marginals = {
            0: np.array([0.5, 0.5]),
            1: np.array([0.2, 0.3, 0.5]),
        }
        table = gen._iterative_proportional_fitting(marginals, shape)
        np.testing.assert_allclose(table.sum(axis=1), [0.5, 0.5], atol=1e-6)
        np.testing.assert_allclose(table.sum(axis=0), [0.2, 0.3, 0.5], atol=1e-6)
        assert table.min() >= 0.0

    def test_result_is_normalised_to_one(self):
        marginals = {0: np.array([0.4, 0.6]), 1: np.array([0.3, 0.7])}
        table = gen._iterative_proportional_fitting(marginals, (2, 2))
        assert table.sum() == pytest.approx(1.0)

    def test_zero_marginal_does_not_diverge(self):
        marginals = {0: np.array([0.0, 1.0]), 1: np.array([0.5, 0.5])}
        table = gen._iterative_proportional_fitting(marginals, (2, 2))
        assert np.isfinite(table).all()


class TestGenerateMicrodata:
    def test_shape_and_columns(self):
        df = gen.generate_microdata(n_agents=500, seed=42)
        assert len(df) == 500
        assert {"age_group", "education_level", "income_quintile", "opinion_baseline"} <= set(
            df.columns
        )

    def test_opinion_baseline_is_bipolar(self):
        df = gen.generate_microdata(n_agents=500, seed=42)
        assert df["opinion_baseline"].between(-1.0, 1.0).all()

    def test_reproducible_for_a_fixed_seed(self):
        a = gen.generate_microdata(n_agents=200, seed=7)
        b = gen.generate_microdata(n_agents=200, seed=7)
        pd = pytest.importorskip("pandas")
        pd.testing.assert_frame_equal(a, b)

    def test_different_seeds_produce_different_data(self):
        a = gen.generate_microdata(n_agents=200, seed=1)
        b = gen.generate_microdata(n_agents=200, seed=2)
        assert not a.equals(b)


class TestComputeNetworkMetrics:
    def test_returns_expected_metric_keys(self):
        metrics = gen.compute_network_metrics(n_nodes=100, seed=42)
        assert {"clustering_coefficient", "modularity", "echo_chamber_density"} <= set(metrics)

    def test_reproducible_for_a_fixed_seed(self):
        a = gen.compute_network_metrics(n_nodes=80, seed=42)
        b = gen.compute_network_metrics(n_nodes=80, seed=42)
        assert a.keys() == b.keys()
        # metadata.generated_at is a provenance timestamp, intentionally
        # non-deterministic; the SCIENTIFIC metrics must be reproducible.
        for key in a:
            if key == "metadata":
                continue
            av, bv = a[key], b[key]
            if isinstance(av, (int, float, str, bool)) or av is None:
                assert av == bv, key
            else:
                np.testing.assert_equal(av, bv)

    def test_metadata_describes_the_run(self):
        metrics = gen.compute_network_metrics(n_nodes=80, seed=42)
        meta = metrics["metadata"]
        assert meta["n_nodes"] == 80
        assert meta["seed"] == 42
        assert meta["version"] == "1.0.0"
        assert meta["generated_at"]  # provenance timestamp present
