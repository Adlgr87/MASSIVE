"""Optimization FASE 3–4 smoke tests."""

from __future__ import annotations

import logging

import numpy as np

from massive_core.config import (
    ScientificRuntimeConfig,
    clear_settings_cache,
    configure_logging,
    get_app_settings,
    get_logger,
)
from micro_massive.core.orchestrator import MicroOrchestrator
from micro_massive.utils.forer import ForerPersonalityGenerator


def test_scientific_runtime_still_importable_from_package():
    cfg = ScientificRuntimeConfig(solver="euler_maruyama")
    assert cfg.solver == "euler_maruyama"


def test_app_settings_from_yaml_defaults():
    clear_settings_cache()
    s = get_app_settings()
    assert s.name == "MASSIVE"
    assert s.simulation.default_steps == 50
    assert s.rate_limit_per_min >= 1
    assert "localhost" in s.cors_origins[0]


def test_configure_logging_idempotent():
    configure_logging("INFO", force=True)
    log = get_logger("massive.test")
    assert isinstance(log, logging.Logger)
    configure_logging("INFO")  # no raise


def test_micro_massive_seed_reproducible():
    a = MicroOrchestrator(n_particles=6, seed=42)
    b = MicroOrchestrator(n_particles=6, seed=42)
    ha = a.run(steps=5)
    hb = b.run(steps=5)
    assert ha[-1]["metrics"]["mean_mood"] == hb[-1]["metrics"]["mean_mood"]
    moods_a = [p["mood"] for p in ha[-1]["particles"]]
    moods_b = [p["mood"] for p in hb[-1]["particles"]]
    assert moods_a == moods_b


def test_forer_generator_seed_reproducible():
    g1 = ForerPersonalityGenerator(seed=7)
    g2 = ForerPersonalityGenerator(seed=7)
    p1 = g1.generate_group(4)
    p2 = g2.generate_group(4)
    assert [p.archetype for p in p1] == [p.archetype for p in p2]
    np.testing.assert_allclose(p1[0].position, p2[0].position)
