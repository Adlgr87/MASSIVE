"""Evolutionary game dynamics for micro-MASSIVE particles."""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np

from micro_massive.core.agent import SocialParticle, Strategy


class EvolutionaryGame:
    """Simple multiplayer game with strategy adaptation."""

    def __init__(
        self,
        particles: Sequence[SocialParticle],
        *,
        seed: Optional[int] = None,
        rng: Optional[np.random.Generator] = None,
    ) -> None:
        self.particles = list(particles)
        self.rng = rng if rng is not None else np.random.default_rng(seed)
        self.payoff_matrix = {
            (Strategy.COOPERATE, Strategy.COOPERATE): (3, 3),
            (Strategy.COOPERATE, Strategy.COMPETE): (0, 5),
            (Strategy.COMPETE, Strategy.COOPERATE): (5, 0),
            (Strategy.COMPETE, Strategy.COMPETE): (1, 1),
        }

    def play(self) -> None:
        for p in self.particles:
            for n in p.neighbors:
                key = (p.strategy, n.strategy)
                if key in self.payoff_matrix:
                    p_payoff, n_payoff = self.payoff_matrix[key]
                else:
                    p_payoff, n_payoff = 2, 2
                p.payoff_history.append(p_payoff)
                p.update_energy(0.05 * p_payoff)

    def update_strategies(self, memory: int = 5) -> None:
        for p in self.particles:
            recent = p.payoff_history[-memory:]
            if len(recent) < memory:
                continue
            mean_payoff = float(np.mean(recent))
            if mean_payoff < 1.5 and p.strategy == Strategy.COOPERATE:
                options = (Strategy.COOPERATE, Strategy.OBSERVE)
                p.strategy = options[int(self.rng.integers(0, len(options)))]
            elif mean_payoff < 1.0 and p.strategy == Strategy.COMPETE:
                p.strategy = Strategy.OBSERVE
            elif mean_payoff > 3.0 and p.strategy == Strategy.OBSERVE:
                p.strategy = Strategy.COOPERATE
