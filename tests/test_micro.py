"""
Tests para el módulo MASSIVE Micro (micro_engine, micro_schemas)
"""

import numpy as np
from micro_schemas import GroupProfile, MemberProfile, EnsembleConfig, SimVariation
from micro_engine import (
    extract_trajectory_features,
    MicroSimOrchestrator,
    FamilyOfFuturesAnalyzer,
    MicroSocialArchitect,
    analyze_group,
)


class TestMicroSchemas:
    def test_group_profile_defaults(self):
        p = GroupProfile()
        assert p.n_members == 5
        assert p.context == "work"
        assert p.communication_frequency == 0.3

    def test_group_profile_custom(self):
        p = GroupProfile(
            n_members=7, context="friends",
            communication_frequency=0.6, hierarchy_tolerance=0.8,
        )
        assert p.n_members == 7
        assert p.communication_frequency == 0.6

    def test_group_profile_with_members(self):
        members = [
            MemberProfile(name="A", role="leader", cooperation_bias=0.8),
            MemberProfile(name="B", role="introvert", cooperation_bias=0.3),
            MemberProfile(name="C", role="mediator", cooperation_bias=0.6),
        ]
        p = GroupProfile(n_members=3, members=members)
        assert len(p.members) == 3
        assert p.members[0].name == "A"

    def test_member_profile_defaults(self):
        m = MemberProfile()
        assert m.cooperation_bias == 0.5
        assert m.hierarchy_bias == 0.5


class TestMicroEngine:
    def test_extract_features_from_single_sim(self):
        T, N, K = 100, 5, 5
        history = [np.random.randn(N, K).astype(np.float64) for _ in range(T)]
        history[-1][:, 0] = np.linspace(-0.8, 0.8, N)

        feats = extract_trajectory_features(history)
        assert "polarization" in feats
        assert "cooperation" in feats
        assert "trust" in feats
        assert "stability" in feats
        assert feats["polarization"] > 0.01

    def test_orchestrator_single_run(self):
        orch = MicroSimOrchestrator(quiet=True)
        profile = GroupProfile(n_members=4, communication_frequency=0.5)
        hist, feats = orch.run_single(profile, steps=50)
        assert hist.shape[0] >= 50
        assert hist.shape[1] == 4
        assert hist.shape[2] == 5
        assert "polarization" in feats

    def test_orchestrator_ensemble(self):
        orch = MicroSimOrchestrator(quiet=True)
        profile = GroupProfile(n_members=3, communication_frequency=0.3)
        trajs, feat_mat, params = orch.run_ensemble(
            profile, n_simulations=20, steps_per_sim=30, use_dask=False,
        )
        assert feat_mat.shape[0] == 20
        assert feat_mat.shape[1] > 5
        assert len(params) == 20
        assert "coupling" in params[0]

    def test_full_pipeline_small(self):
        profile = GroupProfile(
            n_members=4, context="work",
            communication_frequency=0.4, hierarchy_tolerance=0.3,
        )
        result = analyze_group(
            profile=profile,
            n_simulations=30,
            steps_per_sim=40,
            use_dask=False,
        )
        assert "families" in result
        assert "bifurcation" in result
        assert "architect" in result
        assert len(result["families"]) >= 1
        assert "param_importances" in result["bifurcation"]

    def test_bifurcation_detects_importance(self):
        """Verifica que el análisis de bifurcación encuentra estructura."""
        profile = GroupProfile(
            n_members=5,
            communication_frequency=0.3,
            hierarchy_tolerance=0.3,
        )
        result = analyze_group(
            profile=profile,
            n_simulations=50,
            steps_per_sim=60,
            use_dask=False,
        )
        bif = result["bifurcation"]
        if bif.get("param_importances"):
            total = sum(bif["param_importances"].values())
            assert abs(total - 1.0) < 0.01  # importances normalizadas

    def test_micro_architect_transition(self):
        profile = GroupProfile(n_members=4, communication_frequency=0.3)
        result = analyze_group(
            profile=profile,
            n_simulations=30,
            steps_per_sim=40,
            use_dask=False,
        )
        families = result["families"]
        bif = result["bifurcation"]
        architect = result["architect"]

        if len(families) >= 2:
            transition = architect.find_transition(families, bif,
                                                   families[0]["id"],
                                                   families[1]["id"])
            assert "from_label" in transition
            assert "to_label" in transition
            assert "recommendation" in transition

            narrative = architect.suggest_narrative(transition)
            assert len(narrative) > 10


class TestFamilyOfFuturesAnalyzer:
    def test_label_variety(self):
        analyzer = FamilyOfFuturesAnalyzer()
        scenarios = [
            {"polarization": 0.7, "cooperation": 0.3, "trust": 0.3,
             "stability": 0.01, "hierarchy_mean": 0.5, "hierarchy_std": 0.1,
             "extreme_fraction": 0.6, "opinion_delta": 0.3, "time_to_stabilize": 0.5,
             "max_polarization": 0.7, "dim_correlation": 0.3, "cooperation_delta": 0.1},
            {"polarization": 0.1, "cooperation": 0.8, "trust": 0.8,
             "stability": 0.01, "hierarchy_mean": 0.5, "hierarchy_std": 0.1,
             "extreme_fraction": 0.1, "opinion_delta": 0.05, "time_to_stabilize": 0.5,
             "max_polarization": 0.1, "dim_correlation": 0.3, "cooperation_delta": 0.1},
        ]
        labels = []
        for s in scenarios:
            label, desc, risks = analyzer._label_family(s)
            labels.append((label, risks))
        # Las dos deben ser diferentes
        assert labels[0][0] != labels[1][0]

    def test_clustering(self):
        analyzer = FamilyOfFuturesAnalyzer()
        X = np.random.rand(100, 10)
        params = [
            {"coupling": np.random.uniform(0, 1),
             "external_pressure": np.random.uniform(0, 1),
             "initial_noise": np.random.uniform(0, 1)}
            for _ in range(100)
        ]
        labels, bif = analyzer.fit(X, params)
        assert len(labels) == 100
        assert "param_importances" in bif
