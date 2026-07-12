import numpy as np


class InfluenceMatrix:
    def __init__(self, particles, base_weight=0.3):
        self.particles = particles
        self.n = len(particles)
        self.base_weight = base_weight
        self.weights = np.full((self.n, self.n), base_weight)
        np.fill_diagonal(self.weights, 0.0)

    def decay(self, decay_rate=0.001):
        self.weights *= 1.0 - decay_rate

    def reinforce(self, i, j, amount=0.05):
        self.weights[i, j] = np.clip(self.weights[i, j] + amount, 0.0, 1.0)
        self.weights[j, i] = np.clip(self.weights[j, i] + amount, 0.0, 1.0)

    def step(self, noise=0.02):
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
                delta = (target - p.mood) * 0.1 + np.random.normal(0, noise)
                p.update_mood(delta)
