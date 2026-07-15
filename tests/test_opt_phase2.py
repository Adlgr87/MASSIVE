"""Optimization FASE 2 smoke checks."""

from __future__ import annotations

import numpy as np

from massive_core.utils.rng import create_seed_sequence, ensure_rng, get_default_rng
from services import forecast_service, simulation_service


def test_seed_sequence_unique_children():
    seeds = create_seed_sequence(42, 5)
    assert len(seeds) == 5
    assert len(set(seeds)) == 5
    assert all(isinstance(s, (int, np.integer)) for s in seeds)


def test_ensure_rng_identity():
    g = get_default_rng(1)
    assert ensure_rng(g) is g


def test_simulation_service_typed_surface():
    out = simulation_service.run_scalar_simulation(
        {"opinion": 0.0, "propaganda": 0.0},
        pasos=3,
        config={"seed": 3},
        verbose=False,
    )
    assert len(out["history"]) == 4


def test_forecast_service_doc_surface():
    assert any(t["name"] == "opinion_mean" for t in forecast_service.list_targets())
