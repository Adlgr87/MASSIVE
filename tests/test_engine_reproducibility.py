"""Hard bit-equality reproducibility fixtures (B6)."""

from __future__ import annotations

import numpy as np
import pytest

from energy_engine import SocialEnergyEngine
from massive_engine import MassiveSimEngine
from multilayer_engine import MultilayerEngine
from simulator import simular, simular_multiples


@pytest.mark.parametrize("seed", [0, 42, 99])
def test_simular_seed_bit_equality(seed: int):
    estado = {"opinion": 0.4, "propaganda": 0.2}
    cfg = {"proveedor": "heurístico", "seed": seed, "ruido_base": 0.03}
    a = simular(estado, pasos=20, cada_n_pasos=5, config=cfg, verbose=False)
    b = simular(estado, pasos=20, cada_n_pasos=5, config=cfg, verbose=False)
    assert [h["opinion"] for h in a] == [h["opinion"] for h in b]


def test_simular_multiples_seed_reproducible():
    estado = {"opinion": 0.5, "propaganda": 0.1}
    cfg = {"proveedor": "heurístico", "seed": 7}
    a = simular_multiples(
        estado, pasos=8, cada_n_pasos=4, config=cfg, n_simulaciones=5
    )
    b = simular_multiples(
        estado, pasos=8, cada_n_pasos=4, config=cfg, n_simulaciones=5
    )
    assert a["media"] == b["media"]
    assert a["std"] == b["std"]
    assert a["percentiles"] == b["percentiles"]
    assert a["escenarios"] == b["escenarios"]
    assert a["n_simulaciones"] == b["n_simulaciones"]



def test_massive_engine_seed_bit_equality():
    r1 = MassiveSimEngine(N=500, quantize=False, event_driven=False, seed=13).run(
        steps=8
    )
    r2 = MassiveSimEngine(N=500, quantize=False, event_driven=False, seed=13).run(
        steps=8
    )
    assert r1["mean_opinion"] == r2["mean_opinion"]


def test_multilayer_engine_seed_allclose():
    h1 = MultilayerEngine(N=30, seed=5, layer_weights=(0.4, 0.3, 0.3)).run(steps=12)
    h2 = MultilayerEngine(N=30, seed=5, layer_weights=(0.4, 0.3, 0.3)).run(steps=12)
    np.testing.assert_allclose(np.asarray(h1), np.asarray(h2), atol=0.0, rtol=0.0)


def test_energy_engine_seed_bit_equality():
    n = 40
    adj = np.ones((n, n)) / n
    attractors = [{"position": 0.0, "strength": 0.8}]
    repellers: list = []

    def run(seed: int) -> np.ndarray:
        eng = SocialEnergyEngine(range_type="bipolar", temperature=0.04, seed=seed)
        rng = np.random.default_rng(seed)
        op = rng.uniform(-1, 1, n)
        for _ in range(15):
            op = eng.step(op, adj, attractors, repellers, eta=0.01)
        return op

    np.testing.assert_array_equal(run(21), run(21))
