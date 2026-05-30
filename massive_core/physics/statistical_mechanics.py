"""Statistical-mechanics observables for complex social states."""

from __future__ import annotations

from typing import Callable

import numpy as np

Array = np.ndarray


class StatisticalMechanicsEngine:
    """Computes entropy, free energy and phase-transition diagnostics.

    Args:
        effective_temperature: Positive default temperature.
    """

    def __init__(self, effective_temperature: float = 1.0) -> None:
        if effective_temperature <= 0.0:
            raise ValueError("effective_temperature must be positive")
        self.effective_temperature = effective_temperature

    def compute_entropy(self, distribution: Array) -> float:
        """Compute Shannon entropy of a non-negative distribution.

        Args:
            distribution: Non-negative weights or probabilities.

        Returns:
            Shannon entropy ``-sum(p log p)``.
        """

        values = np.asarray(distribution, dtype=float)
        if np.any(values < 0.0):
            raise ValueError("distribution must be non-negative")
        total = float(np.sum(values))
        if total <= 0.0:
            return 0.0
        p = values / total
        p = p[p > 0.0]
        return float(-np.sum(p * np.log(p)))

    def compute_free_energy(self, energy: Array, temperature: float | None = None) -> float:
        """Compute canonical free energy from energy levels.

        Args:
            energy: Energy levels.
            temperature: Optional positive temperature.

        Returns:
            Free energy ``-T log Z`` with ``k_B = 1``.
        """

        temp = self._temperature(temperature)
        beta = 1.0 / temp
        levels = np.asarray(energy, dtype=float)
        shifted = levels - np.min(levels)
        z_shifted = np.sum(np.exp(-beta * shifted))
        return float(np.min(levels) - temp * np.log(z_shifted + 1e-12))

    def compute_partition_function(
        self,
        hamiltonian: Callable[[], Array] | Array,
        temperature: float | None = None,
    ) -> float:
        """Compute the partition function for energy levels.

        Args:
            hamiltonian: Callable returning energy levels or an array directly.
            temperature: Optional positive temperature.

        Returns:
            Partition function ``Z``.
        """

        temp = self._temperature(temperature)
        energy = hamiltonian() if callable(hamiltonian) else hamiltonian
        levels = np.asarray(energy, dtype=float)
        shifted = levels - np.min(levels)
        return float(np.exp(-np.min(levels) / temp) * np.sum(np.exp(-shifted / temp)))

    def compute_gibbs_free_energy_field(
        self,
        probability: Array,
        temperature: float | None = None,
    ) -> Array:
        """Compute ``G(x) = -T log P(x)`` from probabilities.

        Args:
            probability: Probability field or non-normalized non-negative mass.
            temperature: Optional positive temperature.

        Returns:
            Gibbs free-energy field.
        """

        temp = self._temperature(temperature)
        p = np.asarray(probability, dtype=float)
        if np.any(p < 0.0):
            raise ValueError("probability must be non-negative")
        total = np.sum(p)
        if total > 0.0:
            p = p / total
        return -temp * np.log(p + 1e-12)

    def estimate_phase_transition(self, order_parameter: Array, temperature_range: Array) -> dict[str, Array | int | float]:
        """Estimate transition temperature from susceptibility peaks.

        Args:
            order_parameter: Samples of the order parameter. Can be one vector
                reused for all temperatures or a ``(n_temperatures, samples)``
                matrix.
            temperature_range: Positive temperatures.

        Returns:
            Susceptibility curve and peak metadata.
        """

        temperatures = np.asarray(temperature_range, dtype=float).reshape(-1)
        if np.any(temperatures <= 0.0):
            raise ValueError("temperature_range must be positive")
        m = np.asarray(order_parameter, dtype=float)
        if m.ndim == 1:
            variance = np.var(m)
            susceptibility = variance / temperatures
        elif m.shape[0] == temperatures.size:
            susceptibility = np.var(m, axis=1) / temperatures
        else:
            raise ValueError("order_parameter shape must match temperature_range")
        peak_index = int(np.argmax(susceptibility))
        return {
            "susceptibility": susceptibility,
            "peak_index": peak_index,
            "critical_temperature": float(temperatures[peak_index]),
            "temperature_range": temperatures,
        }

    def _temperature(self, temperature: float | None) -> float:
        temp = self.effective_temperature if temperature is None else temperature
        if temp <= 0.0:
            raise ValueError("temperature must be positive")
        return float(temp)
