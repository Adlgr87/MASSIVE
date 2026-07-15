"""Neighbor influence updates for micro-MASSIVE particles."""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np

from micro_massive.core.agent import SocialParticle


class InfluenceMatrix:
    """Weighted influence matrix over social particles."""

    def __init__(
        self,
        particles: Sequence[SocialParticle],
        base_weight: float = 0.3,
        *,
        seed: Optional[int] = None,
        rng: Optional[np.random.Generator] = None,
    ) -> None:
        self.particles = list(particles)
        self.n = len(self.particles)
        self.base_weight = base_weight
        self.weights = np.full((self.n, self.n), base_weight, dtype=float)
        np.fill_diagonal(self.weights, 0.0)
        self.rng = rng if rng is not None else np.random.default_rng(seed)

    def decay(self, decay_rate: float = 0.001) -> None:
        self.weights *= 1.0 - decay_rate

    def reinforce(self, i: int, j: int, amount: float = 0.05) -> None:
        self.weights[i, j] = float(np.clip(self.weights[i, j] + amount, 0.0, 1.0))
        self.weights[j, i] = float(np.clip(self.weights[j, i] + amount, 0.0, 1.0))

    def step(self, noise: float = 0.02) -> None:
        """Propagate neighbor mood with local RNG noise."""
        for i, p in enumerate(self.particles):
            if not p.neighbors:
                continue
            weighted_mood = 0.0
            total_weight = 0.0
            for n in p.neighbors:
                j = n.id
                w = self.weights[i, j]
                weighted_mood += w * n.mood
                total_weight += w
            if total_weight > 0:
                target = weighted_mood / total_weight
                delta = (target - p.mood) * 0.1 + float(self.rng.normal(0, noise))
                p.update_mood(delta)
