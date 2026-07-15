"""Orchestrator for micro-MASSIVE multi-particle simulations."""

from __future__ import annotations

from typing import Any, Optional, Sequence

import numpy as np

from micro_massive.core.agent import SocialParticle
from micro_massive.core.game import EvolutionaryGame
from micro_massive.core.influence import InfluenceMatrix
from micro_massive.utils.metrics import GroupMetrics


class MicroOrchestrator:
    """Coordinates influence, games, and metrics for a particle group."""

    def __init__(
        self,
        particles: Optional[Sequence[SocialParticle]] = None,
        n_particles: int = 8,
        initial_cohesion: float = 0.3,
        *,
        seed: Optional[int] = None,
        rng: Optional[np.random.Generator] = None,
    ) -> None:
        self.rng = rng if rng is not None else np.random.default_rng(seed)
        if particles is not None:
            self.particles = list(particles)
        else:
            self.particles = [
                SocialParticle(i, seed=None, rng=self.rng) for i in range(n_particles)
            ]
        self._initialize_neighbors(initial_cohesion)
        self.influence = InfluenceMatrix(self.particles, rng=self.rng)
        self.game = EvolutionaryGame(self.particles)
        self.metrics = GroupMetrics(self.particles)
        self._step = 0

    def _initialize_neighbors(self, cohesion: float) -> None:
        for p in self.particles:
            p.neighbors = []
            for q in self.particles:
                if p is not q and self.rng.random() < cohesion:
                    p.neighbors.append(q)

    def step(self) -> None:
        self._step += 1
        self.influence.step()
        if self._step % 3 == 0:
            self.game.play()
            self.game.update_strategies()
        for p in self.particles:
            p.update_mood(-0.01 * p.mood)

        p = self.metrics.pressure()
        if p > 0.6:
            for a in self.particles:
                if a.charge > 0:
                    a.update_mood(-0.02)
        elif p < 0.2:
            for a in self.particles:
                if a.charge > 0:
                    a.update_mood(0.01)

    def run(self, steps: int = 100) -> list[dict[str, Any]]:
        history: list[dict[str, Any]] = []
        for _ in range(steps):
            self.step()
            history.append(self.get_state())
        return history

    def get_state(self) -> dict[str, Any]:
        return {
            "step": self._step,
            "particles": [
                {
                    "id": p.id,
                    "mood": round(p.mood, 3),
                    "energy": round(p.energy, 3),
                    "strategy": p.strategy.value,
                    "charge": round(p.charge, 3),
                    "position": [round(float(x), 3) for x in p.position],
                }
                for p in self.particles
            ],
            "metrics": {
                "cohesion": round(self.metrics.cohesion(), 3),
                "conflict": round(self.metrics.pressure(), 3),
                "diversity": round(self.metrics.diversity(), 3),
                "mean_mood": round(self.metrics.mean_mood(), 3),
            },
        }
