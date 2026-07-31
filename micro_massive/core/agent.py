"""Social particle agent for micro-MASSIVE simulations."""

from __future__ import annotations

from enum import Enum
from typing import Optional

import numpy as np


class Strategy(str, Enum):
    COOPERATE = "cooperate"
    COMPETE = "compete"
    OBSERVE = "observe"


class SocialParticle:
    """Lightweight agent with mood, energy, and 2-D position."""

    def __init__(
        self,
        id: int,
        charge: float = 0.0,
        energy: float = 0.5,
        strategy: Strategy = Strategy.COOPERATE,
        *,
        seed: Optional[int] = None,
        rng: Optional[np.random.Generator] = None,
    ) -> None:
        self.id = id
        self.charge = charge
        self.energy = energy
        self.strategy = strategy
        self.mood = 0.0
        _rng = rng if rng is not None else np.random.default_rng(seed)
        self.position = _rng.random(2)
        self.neighbors: list[SocialParticle] = []
        self.payoff_history: list[float] = []

    def update_mood(self, delta: float) -> None:
        self.mood = float(np.clip(self.mood + delta, -1.0, 1.0))

    def update_energy(self, delta: float) -> None:
        self.energy = float(np.clip(self.energy + delta, 0.0, 1.0))

    def distance_to(self, other: "SocialParticle") -> float:
        return float(np.linalg.norm(self.position - other.position))
