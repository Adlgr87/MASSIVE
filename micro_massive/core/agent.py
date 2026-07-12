from enum import Enum

import numpy as np


class Strategy(str, Enum):
    COOPERATE = "cooperate"
    COMPETE = "compete"
    OBSERVE = "observe"


class SocialParticle:
    def __init__(self, id, charge=0.0, energy=0.5, strategy=Strategy.COOPERATE):
        self.id = id
        self.charge = charge
        self.energy = energy
        self.strategy = strategy
        self.mood = 0.0
        self.position = np.random.rand(2)
        self.neighbors = []
        self.payoff_history = []

    def update_mood(self, delta):
        self.mood = np.clip(self.mood + delta, -1.0, 1.0)

    def update_energy(self, delta):
        self.energy = np.clip(self.energy + delta, 0.0, 1.0)

    def distance_to(self, other):
        return np.linalg.norm(self.position - other.position)
