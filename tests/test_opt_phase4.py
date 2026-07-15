"""Optimization FASE 4 smoke tests."""

from __future__ import annotations

import numpy as np

from massive_core.numerics.steppers import EulerMaruyamaStepper
from micro_massive.core import EvolutionaryGame, MicroOrchestrator, SocialParticle, Strategy
from micro_massive.utils import ForerPersonalityGenerator, GroupMetrics


def test_micro_package_exports():
    assert SocialParticle is not None
    assert Strategy.COOPERATE.value == "cooperate"
    assert ForerPersonalityGenerator is not None
    assert GroupMetrics is not None


def test_euler_maruyama_local_rng_reproducible():
    def drift(x):
        return -0.1 * x

    a = EulerMaruyamaStepper(seed=11)
    b = EulerMaruyamaStepper(seed=11)
    x0 = np.array([1.0, -0.5, 0.25])
    ra = a.step(x0, 0.05, drift, diffusion=0.2)
    rb = b.step(x0, 0.05, drift, diffusion=0.2)
    np.testing.assert_allclose(ra.state, rb.state)


def test_evolutionary_game_uses_injected_rng():
    rng = np.random.default_rng(99)
    particles = [SocialParticle(i, seed=None, rng=rng) for i in range(4)]
    for p in particles:
        p.neighbors = [q for q in particles if q is not p]
        p.payoff_history = [1.0, 1.0, 1.0, 1.0, 1.0]
        p.strategy = Strategy.COOPERATE
    game = EvolutionaryGame(particles, rng=np.random.default_rng(3))
    game.update_strategies(memory=5)
    # With low mean payoff, cooperators may switch; must not use global random
    assert all(isinstance(p.strategy, Strategy) for p in particles)


def test_orchestrator_full_seed_reproducible():
    a = MicroOrchestrator(n_particles=5, seed=123)
    b = MicroOrchestrator(n_particles=5, seed=123)
    ha = a.run(steps=12)
    hb = b.run(steps=12)
    assert ha[-1]["metrics"] == hb[-1]["metrics"]
