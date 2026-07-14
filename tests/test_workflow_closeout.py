"""Tests covering remaining MASSIVE_REMEDIATION_WORKFLOW closeout items."""

from __future__ import annotations

import numpy as np
import pytest

from adapters.mutalambda.massive_target import (
    MassiveTargetManifest,
    evaluate_massive_vector,
    make_objective,
)
from benchmarks.baselines import SeasonalNaiveBaseline, get_all_baselines
from benchmarks.walk_forward import walk_forward_scores, rolling_origin_splits
from forecast.targets import TargetDefinition, resolve_target, all_targets
from massive_core.numerics.steppers import AdaptiveStepper, create_stepper
from massive_engine import MassiveEngine
from services.simulation_service import run_scalar_simulation, run_multilayer_simulation


def test_target_definitions_cover_pvu_clusters():
    names = {t.name for t in all_targets()}
    assert "opinion_mean" in names
    assert "polarization_index" in names
    assert resolve_target("contagion_sir").name == "protest_participation"
    assert resolve_target("polarization_spike").name == "polarization_index"


def test_seasonal_naive_and_baseline_registry():
    y = np.array([0.1, 0.2, 0.3, 0.4, 0.5, 0.6])
    sn = SeasonalNaiveBaseline(season=2)
    pred = sn.predict(y, horizon=3)
    assert pred.shape == (3,)
    names = {b.name for b in get_all_baselines()}
    assert "seasonal_naive" in names
    assert "naive" in names


def test_walk_forward_scores_finite():
    y = np.linspace(0.1, 0.9, 12)
    scores = walk_forward_scores(
        y,
        predict_fn=lambda train, h: np.full(h, float(train[-1])),
        min_train=4,
        horizon=2,
    )
    assert scores["n_folds"] >= 1
    assert np.isfinite(scores["mae"])


def test_rolling_origin_splits_shapes():
    y = np.arange(10, dtype=float)
    folds = list(rolling_origin_splits(y, min_train=4, horizon=2))
    assert len(folds) >= 1
    train, test = folds[0]
    assert len(train) == 4
    assert len(test) == 2


def test_adaptive_stepper_reuses_solver_instance():
    stepper = AdaptiveStepper()
    assert create_stepper("adaptive") is not None

    def drift(x):
        return -x

    s = np.array([0.5, -0.2])
    r1 = stepper.step(s, 0.01, drift)
    solver1 = stepper._solver
    r2 = stepper.step(r1.state, 0.01, drift)
    assert stepper._solver is solver1
    assert r2.diagnostics.method


def test_massive_engine_from_factbook_fallback_defaults():
    class _DummyCtx:
        def get_massive_params(self, country):
            return {
                "n_agents": 120,
                "gini_coefficient": 0.41,
                "social_groups": {"ethnic": {"a": 0.6, "b": 0.4}},
                "economic_potential": {"scale": 1.0},
            }

    eng = MassiveEngine.from_factbook("US", context=_DummyCtx(), seed=1)
    assert eng.agents.shape[0] == 120
    assert eng.config["gini_coefficient"] == 0.41
    assert eng.param_provenance["n_agents"] == "derived_parameter"
    assert eng.param_provenance["gini_coefficient"] == "derived_parameter"


def test_mutalambda_adapter_evaluates():
    manifest = MassiveTargetManifest()
    assert manifest.to_dict()["decision_dim"] == 8
    m = evaluate_massive_vector(
        np.array([0.1, 0.3, 0.4, 0.3, 0.3]),
        n_agents=30,
        steps=3,
        seed=0,
        cluster_id="polarization_escalation",
    )
    assert "polarization_index" in m
    obj = make_objective(n_agents=20, steps=2, seed=1)
    assert np.isfinite(obj(np.zeros(5)))


def test_simulation_service_scalar_and_multilayer():
    out = run_scalar_simulation(
        {"opinion": 0.0, "propaganda": 0.1},
        pasos=5,
        verbose=False,
    )
    assert len(out["history"]) == 6
    assert "summary" in out
    ml = run_multilayer_simulation(n_agents=25, steps=3, seed=0)
    assert ml["n_agents"] == 25
    assert "landscape" in ml


def test_sparse_remove_layer_ix():
    from massive_core.numerics.multilayer_engine_sparse import (
        SparseMultilayerEngine,
        LayerState,
    )
    from scipy.sparse import csr_matrix

    def _layer(lid: str, n: int) -> LayerState:
        return LayerState(
            node_features=np.zeros((n, 2)),
            graph_adjacency=csr_matrix(np.eye(n)),
            layer_id=lid,
        )

    layers = [_layer("a", 4), _layer("b", 3), _layer("c", 2)]
    eng = SparseMultilayerEngine(layers=layers)
    eng.interaction_matrix = np.arange(9, dtype=float).reshape(3, 3)
    eng.add_inter_layer_edge(0, 0, 1, 0)
    eng.add_inter_layer_edge(2, 0, 0, 1)
    eng.remove_layer(1)
    assert eng.n_layers == 2
    assert eng.interaction_matrix.shape == (2, 2)
    if eng.inter_layer_edges.size:
        assert np.all(eng.inter_layer_edges[:, 0] < 2)
        assert np.all(eng.inter_layer_edges[:, 2] < 2)
