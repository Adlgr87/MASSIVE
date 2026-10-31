"""Regression tests for the sparse-layer path and the bounded hub degree.

R2 fixed two scaling defects:

1. ``build_layers`` produced dense (N, N) adjacency matrices and
   ``MultilayerEngine`` kept them, so resident memory was O(N²) — 1.5 GB at
   N=8000. The sparse path now builds CSR natively (no dense intermediate).

2. ``generate_hierarchical`` connected every pair of hubs with probability 0.7,
   a near-dense clique of O(n_hubs²) edges — 2.36 M edges at N=16000. The hub
   core now has bounded degree, keeping the whole graph O(N).

These tests pin: exact numerical parity between dense and sparse, the O(N) edge
count of the hierarchical layer, and that rewiring still works on CSR.
"""

from __future__ import annotations

import numpy as np
from scipy import sparse as sp

from multilayer_engine import (
    MultilayerEngine,
    generate_hierarchical,
)


class TestSparseDenseParity:
    def test_sparse_and_dense_produce_identical_results(self):
        dense = MultilayerEngine(N=600, seed=42, dense_layers=True)
        sparse = MultilayerEngine(N=600, seed=42, dense_layers=False)
        dense.run(steps=150, store_history=False)
        sparse.run(steps=150, store_history=False)

        np.testing.assert_allclose(dense.x, sparse.x, atol=1e-12)

    def test_sparse_layers_are_csr(self):
        engine = MultilayerEngine(N=300, seed=42, dense_layers=False)
        assert all(sp.issparse(a) for a in engine.layers.values())
        assert all(a.format == "csr" for a in engine.layers.values())

    def test_dense_layers_are_ndarray(self):
        engine = MultilayerEngine(N=300, seed=42, dense_layers=True)
        assert all(isinstance(a, np.ndarray) for a in engine.layers.values())


class TestBoundedHierarchy:
    def test_hierarchical_edge_count_is_linear(self):
        """The economic layer must be O(N), not a dense hub clique O(N²)."""
        for N in (2000, 4000):
            adjacency = generate_hierarchical(N, sparse=True)
            # Bounded degree ~8 per hub + the star base (N-1) edges.
            # A dense clique would be ~(0.1·N)², e.g. 40_000 at N=2000.
            assert adjacency.nnz < N * 20, f"N={N} has {adjacency.nnz} edges"

    def test_hierarchical_is_deterministic(self):
        a = generate_hierarchical(2000, sparse=True)
        b = generate_hierarchical(2000, sparse=True)
        np.testing.assert_array_equal(a.toarray(), b.toarray())


class TestSparseRewiring:
    def test_rewiring_censorship_reduces_edges_on_csr(self):
        engine = MultilayerEngine(N=500, seed=42, dense_layers=False)
        before = engine.layers["social"].nnz
        engine.dynamic_rewiring("social", mode="censorship", intensity=0.9)
        after = engine.layers["social"].nnz
        assert after < before
        assert sp.issparse(engine.layers["social"])

    def test_rewiring_viral_hub_increases_edges_on_csr(self):
        engine = MultilayerEngine(N=500, seed=42, dense_layers=False)
        before = engine.layers["digital"].nnz
        engine.dynamic_rewiring("digital", mode="viral_hub", intensity=0.3)
        after = engine.layers["digital"].nnz
        assert after > before
