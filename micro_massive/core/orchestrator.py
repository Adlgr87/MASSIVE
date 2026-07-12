import numpy as np

from micro_massive.core.agent import SocialParticle, Strategy
from micro_massive.core.influence import InfluenceMatrix
from micro_massive.core.game import EvolutionaryGame
from micro_massive.utils.metrics import GroupMetrics


class MicroOrchestrator:
    def __init__(self, particles=None, n_particles=8, initial_cohesion=0.3):
        if particles is not None:
            self.particles = particles
        else:
            self.particles = [SocialParticle(i) for i in range(n_particles)]
        self._initialize_neighbors(initial_cohesion)
        self.influence = InfluenceMatrix(self.particles)
        self.game = EvolutionaryGame(self.particles)
        self.metrics = GroupMetrics(self.particles)
        self._step = 0

    def _initialize_neighbors(self, cohesion):
        for p in self.particles:
            p.neighbors = []
            for q in self.particles:
                if p != q and np.random.random() < cohesion:
                    p.neighbors.append(q)

    def step(self):
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

    def run(self, steps=100):
        history = []
        for _ in range(steps):
            self.step()
            history.append(self.get_state())
        return history

    def get_state(self):
        return {
            "step": self._step,
            "particles": [
                {
                    "id": p.id,
                    "mood": round(p.mood, 3),
                    "energy": round(p.energy, 3),
                    "strategy": p.strategy.value,
                    "charge": round(p.charge, 3),
                    "position": [round(x, 3) for x in p.position],
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
