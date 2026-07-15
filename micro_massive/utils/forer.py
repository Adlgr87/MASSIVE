"""Archetype-based particle generation for micro-MASSIVE."""

from __future__ import annotations

from typing import Any, Optional

import numpy as np

from micro_massive.core.agent import SocialParticle, Strategy


class ForerPersonalityGenerator:
    """Sample social particles from named archetypes with local RNG."""

    def __init__(self, *, seed: Optional[int] = None, rng: Optional[np.random.Generator] = None) -> None:
        self.rng = rng if rng is not None else np.random.default_rng(seed)
        self.archetypes: dict[str, dict[str, Any]] = {
            "el_pegamento": {"charge": 0.8, "energy": 0.7, "strategy": Strategy.COOPERATE},
            "el_lider": {"charge": 0.6, "energy": 0.9, "strategy": Strategy.COOPERATE},
            "el_observador": {"charge": 0.0, "energy": 0.5, "strategy": Strategy.OBSERVE},
            "el_disruptor": {"charge": -0.7, "energy": 0.8, "strategy": Strategy.COMPETE},
            "el_cansado": {"charge": -0.3, "energy": 0.2, "strategy": Strategy.OBSERVE},
            "el_conciliador": {"charge": 0.9, "energy": 0.6, "strategy": Strategy.COOPERATE},
            "el_competitivo": {"charge": 0.4, "energy": 0.8, "strategy": Strategy.COMPETE},
            "el_inseguro": {"charge": -0.5, "energy": 0.4, "strategy": Strategy.OBSERVE},
            "el_creativo": {"charge": 0.5, "energy": 0.9, "strategy": Strategy.COOPERATE},
            "el_pasivo_agresivo": {"charge": -0.6, "energy": 0.5, "strategy": Strategy.COMPETE},
        }

    def generate_particle(
        self,
        id: int,
        archetype: Optional[str] = None,
    ) -> SocialParticle:
        if archetype and archetype in self.archetypes:
            params = self.archetypes[archetype]
        else:
            keys = list(self.archetypes.keys())
            archetype = str(self.rng.choice(keys))
            params = self.archetypes[archetype]
        charge = float(np.clip(params["charge"] + self.rng.normal(0, 0.1), -1.0, 1.0))
        energy = float(np.clip(params["energy"] + self.rng.normal(0, 0.1), 0.0, 1.0))
        p = SocialParticle(
            id=id,
            charge=charge,
            energy=energy,
            strategy=params["strategy"],
            rng=self.rng,
        )
        p.archetype = archetype  # type: ignore[attr-defined]
        return p

    def generate_group(
        self,
        n_particles: int,
        archetype_distribution: Optional[dict[str, float]] = None,
    ) -> list[SocialParticle]:
        if archetype_distribution is None:
            archetype_distribution = {
                "el_pegamento": 0.1,
                "el_lider": 0.1,
                "el_observador": 0.2,
                "el_disruptor": 0.1,
                "el_cansado": 0.1,
                "el_conciliador": 0.1,
                "el_competitivo": 0.1,
                "el_inseguro": 0.1,
                "el_creativo": 0.05,
                "el_pasivo_agresivo": 0.05,
            }
        archetypes = list(archetype_distribution.keys())
        probabilities = np.asarray(list(archetype_distribution.values()), dtype=float)
        probabilities = probabilities / probabilities.sum()
        return [
            self.generate_particle(i, str(self.rng.choice(archetypes, p=probabilities)))
            for i in range(n_particles)
        ]
