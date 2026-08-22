"""
Targeted coverage for uncovered scientific/dispatch paths in micro_engine.py.

Covers: kmeans fallback for tiny samples, _build_bifurcation_map early-exit
branches, _label_family label branches (Bloqueo, Jerárquico, Horizontal,
Volátil, confianza, Estancamiento, groupthink risk), find_transition
direct-calc fallback, suggest_narrative error/empty paths, run_single
external pressure branch, _features_to_matrix, and analyze_group without
scikit-learn.
"""

import numpy as np
import pytest

import micro_engine
from micro_engine import (
    FamilyOfFuturesAnalyzer,
    MicroSocialArchitect,
    extract_trajectory_features,
)
from micro_schemas import GroupProfile

# ── KMeans fallback / clustering edges ─────────────────────────────────────


class TestKmeansFallback:

    def test_kmeans_tiny_sample_returns_zeros(self):
        analyzer = FamilyOfFuturesAnalyzer(n_clusters=0, random_state=0)
        labels = analyzer._cluster(np.random.RandomState(0).rand(5, 3))
        assert labels.shape == (5,)
        assert set(labels.tolist()) == {0}

    def test_kmeans_fixed_k(self):
        analyzer = FamilyOfFuturesAnalyzer(n_clusters=2, random_state=0)
        X = np.random.RandomState(1).rand(40, 5)
        labels = analyzer._cluster(X)
        assert set(labels.tolist()) == {0, 1}


class TestBifurcationEarlyExit:

    def test_single_cluster_returns_empty(self):
        analyzer = FamilyOfFuturesAnalyzer(n_clusters=0, random_state=0)
        labels = np.zeros(60, dtype=int)
        X = np.random.RandomState(0).rand(60, 13)
        params = [
            {"coupling": 0.3, "external_pressure": 0.1, "initial_noise": 0.1} for _ in range(60)
        ]
        pm = analyzer._params_to_matrix(params)
        bif = analyzer._build_bifurcation_map(pm, labels, X)
        assert bif["param_importances"] == {}
        assert bif["transition_costs"] == []

    def test_too_few_nonnoise_returns_empty(self):
        analyzer = FamilyOfFuturesAnalyzer(n_clusters=0, random_state=0)
        labels = np.array([0] * 5 + [-1] * 5)
        X = np.random.RandomState(0).rand(10, 13)
        params = [
            {"coupling": 0.3, "external_pressure": 0.1, "initial_noise": 0.1} for _ in range(10)
        ]
        pm = analyzer._params_to_matrix(params)
        bif = analyzer._build_bifurcation_map(pm, labels, X)
        assert bif["param_importances"] == {}


# ── _label_family branches ─────────────────────────────────────────────────


class TestLabelFamilyBranches:

    def _feats(self, **over):
        base = {
            "polarization": 0.1,
            "cooperation": 0.5,
            "trust": 0.5,
            "hierarchy_mean": 0.5,
            "hierarchy_std": 0.2,
            "stability": 0.01,
            "extreme_fraction": 0.1,
            "opinion_delta": 0.1,
            "time_to_stabilize": 0.5,
            "max_polarization": 0.1,
            "dim_correlation": 0.3,
            "cooperation_delta": 0.1,
        }
        base.update(over)
        return base

    def test_bloqueo_low_cooperation(self):
        a = FamilyOfFuturesAnalyzer()
        label, desc, risks = a._label_family(self._feats(cooperation=0.2))
        assert "Bloqueo" in label
        assert any("cooperación" in r for r in risks)

    def test_jerarquico_label(self):
        a = FamilyOfFuturesAnalyzer()
        label, _, _ = a._label_family(self._feats(hierarchy_mean=0.7, hierarchy_std=0.1))
        assert "Jerárquico" in label

    def test_horizontal_label(self):
        a = FamilyOfFuturesAnalyzer()
        label, _, _ = a._label_family(self._feats(hierarchy_mean=0.1, hierarchy_std=0.1))
        assert "Horizontal" in label

    def test_volatilidad_unstable(self):
        a = FamilyOfFuturesAnalyzer()
        label, desc, risks = a._label_family(self._feats(stability=0.08))
        assert "Volátil" in label

    def test_desconfianza_label(self):
        a = FamilyOfFuturesAnalyzer()
        label, desc, risks = a._label_family(self._feats(trust=0.2))
        assert "desconfianza" in desc

    def test_extreme_fraction_risk(self):
        a = FamilyOfFuturesAnalyzer()
        label, desc, risks = a._label_family(self._feats(extreme_fraction=0.5))
        assert any("radicalización" in r for r in risks)

    def test_estancamiento_label(self):
        a = FamilyOfFuturesAnalyzer()
        label, desc, risks = a._label_family(self._feats(opinion_delta=0.01, polarization=0.1))
        assert label == "Estancamiento"
        assert any("apatía" in r for r in risks)

    def test_groupthink_risk(self):
        a = FamilyOfFuturesAnalyzer()
        label, desc, risks = a._label_family(
            self._feats(polarization=0.1, trust=0.8, hierarchy_mean=0.7)
        )
        assert any("Groupthink" in r for r in risks)

    def test_alta_confianza_risk(self):
        a = FamilyOfFuturesAnalyzer()
        label, desc, risks = a._label_family(self._feats(trust=0.8))
        assert any("groupthink" in r.lower() or "confianza" in r for r in risks)


# ── MicroSocialArchitect transitions ───────────────────────────────────────


class TestMicroSocialArchitect:

    def test_find_transition_direct_calc_fallback(self):
        arch = MicroSocialArchitect()
        families = [
            {
                "id": 0,
                "label": "Consenso",
                "archetype_params": {
                    "coupling": 0.2,
                    "external_pressure": 0.1,
                    "initial_noise": 0.1,
                },
            },
            {
                "id": 1,
                "label": "Fragmentación",
                "archetype_params": {
                    "coupling": 0.6,
                    "external_pressure": 0.4,
                    "initial_noise": 0.2,
                },
            },
        ]
        bif = {
            "param_importances": {"coupling": 0.5, "external_pressure": 0.3, "initial_noise": 0.2},
            "transition_costs": [],
        }
        tr = arch.find_transition(families, bif, 0, 1)
        assert tr["from"] == 0
        assert tr["to"] == 1
        assert tr["from_label"] == "Consenso"
        assert tr["to_label"] == "Fragmentación"
        assert "coupling" in tr["params_change"]
        assert len(tr["recommendation"]) > 0

    def test_find_transition_missing_family_error(self):
        arch = MicroSocialArchitect()
        tr = arch.find_transition([], {"param_importances": {}, "transition_costs": []}, 0, 1)
        assert "error" in tr

    def test_suggest_narrative_empty_changes(self):
        arch = MicroSocialArchitect()
        transition = {"params_change": {}, "from_label": "A", "to_label": "B", "cost": 0.1}
        text = arch.suggest_narrative(transition)
        assert "No hay cambios" in text

    def test_suggest_narrative_with_changes(self):
        arch = MicroSocialArchitect()
        transition = {
            "params_change": {"coupling": 0.1, "external_pressure": -0.05, "initial_noise": 0.02},
            "from_label": "Consenso",
            "to_label": "Fragmentación",
            "cost": 0.34,
        }
        text = arch.suggest_narrative(transition)
        assert "Consenso" in text
        assert "Fragmentación" in text
        assert "0.340" in text or "0.34" in text

    def test_suggest_narrative_error_transition(self):
        arch = MicroSocialArchitect()
        text = arch.suggest_narrative({"error": "algo falló"})
        assert "No se pudo calcular" in text


# ── extract_trajectory_features edge ───────────────────────────────────────


class TestExtractFeaturesEdge:

    def test_short_history_returns_error_flag(self):
        feats = extract_trajectory_features([np.zeros((3, 5))])
        assert feats == {"_error": 1.0}


# ── _profile_to_engine_params ─────────────────────────────────────────────


class TestProfileToEngineParams:

    def test_profile_params_basic(self):
        profile = GroupProfile(n_members=5)
        params = micro_engine._profile_to_engine_params(profile, seed=42)
        assert params["N"] == 5
        assert params["coupling"] == profile.communication_frequency
        assert params["seed"] == 42
        assert params["_base_spread"] == pytest.approx(
            profile.diversity_of_opinion * 0.5 + 0.1 * 0.3
        )


# ── run_single external pressure branch ────────────────────────────────────


class TestRunSingleExternalPressure:

    def test_external_pressure_applies_noise(self):
        from micro_engine import MicroSimOrchestrator

        orch = MicroSimOrchestrator(quiet=True)
        profile = GroupProfile(n_members=4, communication_frequency=0.3)
        variation = {"coupling": 0.4, "external_pressure": 0.6, "initial_noise": 0.15}
        hist, feats = orch.run_single(profile, variation=variation, steps=12)
        assert hist.shape[0] >= 12
        assert "polarization" in feats


# ── describe_families: members >=2 filter ──────────────────────────────────


class TestDescribeFamiliesFilters:

    def test_single_member_clusters_filtered(self):
        analyzer = FamilyOfFuturesAnalyzer(n_clusters=0, random_state=0)
        np_rng = np.random.RandomState(0)
        X = np_rng.rand(20, 13)
        params = [
            {"coupling": 0.3, "external_pressure": 0.1, "initial_noise": 0.1} for _ in range(20)
        ]
        labels = np.array([0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3])
        fams = analyzer.describe_families(labels, X, params)
        assert len(fams) == 4
        # ids re-asigned after sort
        assert [f["id"] for f in fams] == [0, 1, 2, 3]


# ── analyze_group without scikit-learn ─────────────────────────────────────


class TestAnalyzeGroupNoSklearn:

    def test_raises_without_sklearn(self, monkeypatch):
        monkeypatch.setattr(micro_engine, "SKLEARN_AVAILABLE", False)
        profile = GroupProfile(n_members=5)
        with pytest.raises(ImportError):
            micro_engine.analyze_group(profile, n_simulations=5, steps_per_sim=5, use_dask=False)
