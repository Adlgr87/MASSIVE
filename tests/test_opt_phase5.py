"""FASE 5 backlog slice: Intervention validator, seed repro, config smoke."""

from __future__ import annotations

import warnings

import numpy as np
import pytest
from pydantic import ValidationError

from massive.core.schemas import Intervention
from massive_core.config import ScientificRuntimeConfig, get_app_settings, clear_settings_cache
from massive_core.numerics.steppers import EulerMaruyamaStepper


def test_intervention_validator_returns_self_no_warning():
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        iv = Intervention(
            time_start=1,
            time_end=10,
            model_name="lineal",
            parameters={"epsilon": 0.3},
            fase_rationale="test",
        )
    # Pydantic used to warn when model_validator returned None
    bad = [
        w
        for w in caught
        if issubclass(w.category, UserWarning)
        and "validator is returning a value other than `self`" in str(w.message)
    ]
    assert not bad, f"unexpected validator warnings: {bad}"
    assert iv.time_start == 1
    assert iv.time_end == 10


def test_intervention_rejects_inverted_time_window():
    with pytest.raises(ValidationError):
        Intervention(
            time_start=10,
            time_end=1,
            model_name="lineal",
            parameters={},
            fase_rationale="bad window",
        )


def test_app_settings_and_scientific_config_smoke():
    clear_settings_cache()
    s = get_app_settings()
    assert s.name == "MASSIVE"
    cfg = ScientificRuntimeConfig.from_dict({"solver": "euler_maruyama"})
    assert cfg.solver == "euler_maruyama"


def test_euler_stepper_and_energy_seed_reproducible():
    from energy_engine import SocialEnergyEngine

    def drift(x):
        return -0.05 * x

    a = EulerMaruyamaStepper(seed=5)
    b = EulerMaruyamaStepper(seed=5)
    x0 = np.ones(4)
    np.testing.assert_allclose(
        a.step(x0, 0.02, drift, diffusion=0.1).state,
        b.step(x0, 0.02, drift, diffusion=0.1).state,
    )

    eng_a = SocialEnergyEngine(range_type="bipolar", temperature=0.05, seed=7)
    eng_b = SocialEnergyEngine(range_type="bipolar", temperature=0.05, seed=7)
    n = 20
    rng = np.random.default_rng(7)
    op0 = rng.uniform(-1, 1, n)
    adj = np.ones((n, n)) / n
    attractors = [{"position": 0.0, "strength": 0.5}]
    repellers: list = []
    oa, ob = op0.copy(), op0.copy()
    for _ in range(5):
        oa = eng_a.step(oa, adj, attractors, repellers, eta=0.01)
        ob = eng_b.step(ob, adj, attractors, repellers, eta=0.01)
    np.testing.assert_allclose(oa, ob)
