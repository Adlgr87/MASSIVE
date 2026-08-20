"""
Smoke tests for MASSIVE root engines: micro_engine & energy_engine.

Covers:
  - FamilyOfFuturesAnalyzer.describe_families smoke (4 clusters of 5)
  - MicroSimOrchestrator._kmeans_fallback with n_clusters=2 (regression)
  - SocialEnergyEngine smoke (non-torch)
"""

import numpy as np

from energy_engine import SocialEnergyEngine, random_network
from micro_engine import (
    FamilyOfFuturesAnalyzer,
)

# ============================================================
# fixtures / builders
# ============================================================


def _make_4_clusters_feature_matrix(n_per=5, n_feats=13, seed=42):
    """Builds 4 well-separated blobs => 4 clusters of `n_per` members."""
    rng = np.random.default_rng(seed)
    centers = [
        np.full(n_feats, 0.1),
        np.full(n_feats, 0.4),
        np.full(n_feats, 0.7),
        np.full(n_feats, 0.95),
    ]
    mats = []
    for c in centers:
        mats.append(c + rng.normal(0, 0.01, (n_per, n_feats)))
    return np.vstack(mats).astype(np.float64), [
        i + 1 for i, _ in enumerate(centers) for _ in range(n_per)
    ]


def _make_param_records(n=20):
    records = []
    rng = np.random.default_rng(7)
    for _ in range(n):
        records.append(
            {
                "coupling": float(rng.uniform(0.05, 0.8)),
                "external_pressure": float(rng.uniform(0.0, 0.5)),
                "initial_noise": float(rng.uniform(0.01, 0.3)),
            }
        )
    return records


# ============================================================
# FamilyOfFuturesAnalyzer.describe_families
# ============================================================


def test_describe_families_smoke_4clusters():
    """4 clusters of 15 (all >=2) => exactly 4 families.

    n_per=15 (60 sims) keeps the auto-k search meaningful: KMeans fallback
    caps k at min(8, n_sims // 10), so with fewer than 40 sims k=4 can never
    be evaluated (regression note 2026-08-20, see docs/production-readiness-audit.md TEST-03).
    """
    feature_matrix, labels = _make_4_clusters_feature_matrix(n_per=15, seed=11)
    param_records = _make_param_records(n=len(labels))

    analyzer = FamilyOfFuturesAnalyzer(n_clusters=0, random_state=42)
    fam_labels, _bifurcation = analyzer.fit(feature_matrix, param_records)

    families = analyzer.describe_families(fam_labels, feature_matrix, param_records)

    assert len(families) == 4, f"expected 4 families, got {len(families)}"
    for fam in families:
        assert fam["size"] >= 2
        assert 0.0 < fam["proportion"] <= 1.0
        assert len(fam["mean_features"]) == 13
        assert "coupling" in fam["archetype_params"]
    # ids should be 0..3
    ids = sorted(f["id"] for f in families)
    assert ids == [0, 1, 2, 3]


# ============================================================
# MicroSimOrchestrator._kmeans_fallback regression
# ============================================================


def test_kmeans_fallback_n_clusters_2():
    """Regression: n_clusters=2 previously raised UnboundLocalError on best_score."""
    analyzer = FamilyOfFuturesAnalyzer(n_clusters=2, random_state=42)

    # Enough samples for max_k computation: n_sims//10 >= 2 => n_sims >= 20
    rng = np.random.default_rng(3)
    X = rng.normal(0, 1, (100, 5))

    labels = analyzer._kmeans_fallback(X)

    assert labels.shape == (100,)
    assert len(set(labels)) == 2
    # no unbound best_score -> should have logged fine


# ============================================================
# SocialEnergyEngine smoke (non-torch)
# ============================================================


def test_social_energy_engine_smoke():
    engine = SocialEnergyEngine(range_type="bipolar", temperature=0.05, lambda_social=0.5, seed=123)
    n = 5
    adj = random_network(n, connectivity=0.4, seed=99)
    opinions = np.random.default_rng(1).uniform(-1, 1, n)
    attractors = [{"position": 0.0, "strength": 2.0}]
    repellers = [{"position": 0.7, "strength": 1.5}]

    new_opinions = engine.step(opinions, adj, attractors, repellers, eta=0.05)

    assert new_opinions.shape == (n,)
    assert np.all(new_opinions >= engine.min_val - 1e-9)
    assert np.all(new_opinions <= engine.max_val + 1e-9)

    metrics = engine.system_metrics(opinions, adj, attractors, repellers)
    for k in (
        "mean_opinion",
        "std_opinion",
        "polarizacion",
        "energia_total",
        "energia_media",
        "n_clusters_approx",
    ):
        assert k in metrics

    # economic landscape builder smoke
    att, rep = engine.create_economic_landscape(mean_income=35000, n_attractors=3, n_repellers=2)
    assert len(att) == 3 and len(rep) == 2
