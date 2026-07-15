"""Reproducibility: same seed ⇒ same trajectories (no global RNG)."""

from __future__ import annotations

import numpy as np

from energy_engine import SocialEnergyEngine
from massive_engine import MassiveSimEngine
from multilayer_engine import MultilayerEngine
from simulator import simular


def test_massive_sim_engine_seed_reproducible():
    a = MassiveSimEngine(N=200, M=20, quantize=False, event_driven=False, seed=42)
    b = MassiveSimEngine(N=200, M=20, quantize=False, event_driven=False, seed=42)
    ra = a.run(steps=10)
    rb = b.run(steps=10)
    np.testing.assert_allclose(ra["opinion_history"], rb["opinion_history"], atol=1e-12)
    np.testing.assert_allclose(ra["cluster_opinions"], rb["cluster_opinions"], atol=1e-12)


def test_massive_sim_engine_different_seeds_diverge():
    a = MassiveSimEngine(N=200, M=20, quantize=False, event_driven=False, seed=1)
    b = MassiveSimEngine(N=200, M=20, quantize=False, event_driven=False, seed=2)
    ra = a.run(steps=10)
    rb = b.run(steps=10)
    assert not np.allclose(ra["opinion_history"], rb["opinion_history"])


def test_multilayer_engine_seed_reproducible():
    a = MultilayerEngine(N=40, seed=7)
    b = MultilayerEngine(N=40, seed=7)
    ha = a.run(steps=8)
    hb = b.run(steps=8)
    np.testing.assert_allclose(ha[-1], hb[-1], atol=1e-12)


def test_social_energy_engine_seed_reproducible():
    eng_a = SocialEnergyEngine(seed=11)
    eng_b = SocialEnergyEngine(seed=11)
    n = 30
    rng = np.random.default_rng(0)
    opinions = rng.uniform(-1, 1, n)
    adj = np.eye(n)
    # same starting opinions
    o1 = opinions.copy()
    o2 = opinions.copy()
    for _ in range(5):
        o1 = eng_a.step(o1, adj, [], [], eta=0.01)
        o2 = eng_b.step(o2, adj, [], [], eta=0.01)
    np.testing.assert_allclose(o1, o2, atol=1e-12)


def test_simular_config_seed_reproducible():
    estado = {"opinion": 0.1, "propaganda": 0.0, "confianza": 0.5}
    cfg = {"seed": 99, "proveedor": "heurístico"}
    h1 = simular(estado, pasos=12, cada_n_pasos=50, config=cfg, verbose=False)
    h2 = simular(estado, pasos=12, cada_n_pasos=50, config=cfg, verbose=False)
    ops1 = [h["opinion"] for h in h1]
    ops2 = [h["opinion"] for h in h2]
    np.testing.assert_allclose(ops1, ops2, atol=1e-12)
