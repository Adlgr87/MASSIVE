"""Serializable scientific diagnostics for MASSIVE simulation histories.

This module is the opt-in integration layer between legacy MASSIVE histories
and the scientific extensions.  It does not mutate simulations; it converts a
history into numeric arrays and returns a JSON-friendly report.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any, Sequence

import numpy as np

from massive_core.numerics import StabilityAnalyzer
from massive_core.physics import StatisticalMechanicsEngine

Array = np.ndarray


@dataclass(frozen=True)
class ScientificReport:
    """Serializable scientific summary of a trajectory.

    Args:
        n_steps: Number of transitions in the trajectory.
        state_dim: Flattened state dimension per time step.
        final_state: Final flattened state as a list.
        stability_label: ``stable``, ``marginal`` or ``unstable`` from the
            fitted one-step linear map.
        spectral_radius: Spectral radius of the fitted one-step map.
        max_real_eigenvalue: Continuous-time proxy ``log(rho) / dt``.
        lyapunov_max: Largest lightweight Lyapunov estimate across dimensions.
        entropy: Shannon entropy of the final state distribution.
        free_energy: Canonical free energy of the final state histogram.
        susceptibility_peak: Maximum susceptibility over ``temperature_range``.
        tipping_indices: Time indices with unusually large trajectory jumps.
    """

    n_steps: int
    state_dim: int
    final_state: list[float]
    stability_label: str
    spectral_radius: float
    max_real_eigenvalue: float
    lyapunov_max: float
    entropy: float
    free_energy: float
    susceptibility_peak: float
    tipping_indices: list[int]

    def to_dict(self) -> dict[str, Any]:
        """Convert the report to a JSON-friendly dictionary.

        Returns:
            Dictionary containing only built-in scalar/list values.
        """

        return asdict(self)


def trajectory_from_history(history: Sequence[Any], fields: Sequence[str] | None = None) -> Array:
    """Convert MASSIVE history objects into a ``(time, dimensions)`` array.

    Args:
        history: Sequence of dictionaries from ``simular`` or NumPy-like states
            from multilayer engines.
        fields: Optional ordered dictionary keys to extract. Defaults to the
            opinion field when dictionaries are supplied.

    Returns:
        Two-dimensional float array with time along axis 0.
    """

    if isinstance(history, np.ndarray):
        data = np.asarray(history, dtype=float)
        if data.shape[0] == 0:
            raise ValueError("history cannot be empty")
        return data.reshape(data.shape[0], -1)
    if not history:
        raise ValueError("history cannot be empty")

    first = history[0]
    if isinstance(first, dict):
        selected = list(fields or ("opinion",))
        rows = []
        for item in history:
            rows.append([float(item[key]) for key in selected if key in item])
        if any(len(row) != len(rows[0]) for row in rows):
            raise ValueError("all history dictionaries must expose the same selected fields")
        return np.asarray(rows, dtype=float)

    array_rows: list[Array] = [
        np.asarray(item, dtype=float).reshape(-1) for item in history
    ]
    if any(row.shape != array_rows[0].shape for row in array_rows):
        raise ValueError("all array history entries must have the same shape")
    return np.vstack(array_rows)


def build_scientific_report(
    history: Sequence[Any],
    dt: float = 1.0,
    fields: Sequence[str] | None = None,
    bins: int = 10,
    temperature_range: Array | None = None,
) -> ScientificReport:
    """Build a scientific report from a MASSIVE trajectory.

    Args:
        history: Sequence of dict states or array snapshots.
        dt: Positive time step between snapshots.
        fields: Optional dict fields to extract when ``history`` contains
            dictionaries.
        bins: Histogram bins for entropy and free-energy diagnostics.
        temperature_range: Optional temperatures for susceptibility. Defaults
            to five values in ``[0.5, 2.0]``.

    Returns:
        ``ScientificReport`` with serializable stability and thermodynamic
        diagnostics.
    """

    if dt <= 0.0:
        raise ValueError("dt must be positive")
    if bins < 2:
        raise ValueError("bins must be at least 2")

    trajectory = trajectory_from_history(history, fields)
    if trajectory.shape[0] < 2:
        raise ValueError("history needs at least two time points")

    transition = _fit_transition_matrix(trajectory)
    eigenvalues = np.linalg.eigvals(transition)
    spectral_radius = float(np.max(np.abs(eigenvalues))) if eigenvalues.size else 0.0
    max_real = float(np.log(max(spectral_radius, 1e-12)) / dt)
    stability_label = _classify_stability(spectral_radius)

    stability = StabilityAnalyzer()
    if trajectory.shape[0] >= 3:
        lyapunov = stability.compute_lyapunov_exponents(trajectory, dt)
        lyapunov_max = float(np.max(lyapunov))
    else:
        lyapunov_max = 0.0

    stat = StatisticalMechanicsEngine()
    final_state = trajectory[-1]
    hist_counts, _ = np.histogram(final_state, bins=bins)
    entropy = stat.compute_entropy(hist_counts)
    free_energy = stat.compute_free_energy(hist_counts.astype(float) + 1e-12)
    temps = np.asarray(temperature_range if temperature_range is not None else np.linspace(0.5, 2.0, 5), dtype=float)
    susceptibility = stat.estimate_phase_transition(final_state, temps)["susceptibility"]

    return ScientificReport(
        n_steps=int(trajectory.shape[0] - 1),
        state_dim=int(trajectory.shape[1]),
        final_state=[float(value) for value in final_state],
        stability_label=stability_label,
        spectral_radius=spectral_radius,
        max_real_eigenvalue=max_real,
        lyapunov_max=lyapunov_max,
        entropy=entropy,
        free_energy=free_energy,
        susceptibility_peak=float(np.max(susceptibility)),
        tipping_indices=_detect_tipping_indices(trajectory),
    )


def _fit_transition_matrix(trajectory: Array) -> Array:
    previous = trajectory[:-1]
    next_values = trajectory[1:]
    coefficients = np.linalg.lstsq(previous, next_values, rcond=None)[0]
    return coefficients.T


def _classify_stability(spectral_radius: float, tolerance: float = 1e-3) -> str:
    if spectral_radius < 1.0 - tolerance:
        return "stable"
    if spectral_radius > 1.0 + tolerance:
        return "unstable"
    return "marginal"


def _detect_tipping_indices(trajectory: Array) -> list[int]:
    jumps = np.linalg.norm(np.diff(trajectory, axis=0), axis=1)
    if jumps.size == 0:
        return []
    median_jump = float(np.median(jumps))
    mad = float(np.median(np.abs(jumps - median_jump)))
    robust_sigma = 1.4826 * mad
    threshold = median_jump + max(3.0 * robust_sigma, 1e-12)
    return [int(index + 1) for index, jump in enumerate(jumps) if jump > threshold]
