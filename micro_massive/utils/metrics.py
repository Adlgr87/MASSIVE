import numpy as np

from micro_massive.core.agent import Strategy


class GroupMetrics:
    def __init__(self, particles):
        self.particles = particles

    def cohesion(self):
        if len(self.particles) < 2:
            return 1.0
        distances = []
        for i, a in enumerate(self.particles):
            for b in self.particles[i + 1:]:
                distances.append(a.distance_to(b))
        return 1.0 - np.mean(distances) if distances else 1.0

    def pressure(self):
        charges = [abs(p.charge) for p in self.particles if p.charge < 0]
        return np.mean(charges) if charges else 0.0

    def mean_mood(self):
        return np.mean([p.mood for p in self.particles])

    def diversity(self):
        strategies = [p.strategy.value for p in self.particles]
        _, counts = np.unique(strategies, return_counts=True)
        probs = counts / len(strategies)
        return -np.sum(probs * np.log(probs)) if len(probs) > 1 else 0.0
