"""QAOA-inspired optimizer with a safe classical fallback."""

from __future__ import annotations

from typing import Callable

import numpy as np


try:
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator

    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False


def _evaluate_candidate(
    evaluate_fn: Callable[[np.ndarray], float],
    candidate: np.ndarray,
) -> float:
    score = float(evaluate_fn(candidate))
    if not np.isfinite(score):
        return -np.inf
    return score


def _sample_qiskit_candidates(num_qubits: int, shots: int) -> list[np.ndarray]:
    """Sample binary intervention candidates from a simple quantum circuit.

    Args:
        num_qubits: Number of qubits (equals n_agents * n_phases).
        shots: Number of measurements to collect.

    Returns:
        List of 1D numpy arrays encoded as {-1, +1} decisions.
    """
    circuit = QuantumCircuit(num_qubits, num_qubits)
    circuit.h(range(num_qubits))
    circuit.measure(range(num_qubits), range(num_qubits))

    simulator = AerSimulator()
    result = simulator.run(circuit, shots=shots).result()
    counts = result.get_counts()

    candidates = []
    for bitstring in counts:
        bits = np.array(list(bitstring[::-1]))
        bit_values = np.where(bits == "1", 1.0, -1.0).astype(np.float64)
        candidates.append(bit_values)
    return candidates


def _classical_random_search(
    evaluate_fn: Callable[[np.ndarray], float],
    n_agents: int,
    n_phases: int,
    max_iter: int,
    seed: int,
) -> dict:
    rng = np.random.default_rng(seed)
    best = rng.choice([-1.0, 1.0], size=(n_phases, n_agents)).astype(np.float64)
    best_score = _evaluate_candidate(evaluate_fn, best)

    for _ in range(max_iter):
        candidate = rng.choice([-1.0, 1.0], size=(n_phases, n_agents)).astype(np.float64)
        score = _evaluate_candidate(evaluate_fn, candidate)
        if score > best_score:
            best_score = score
            best = candidate

    return {
        "interventions": best,
        "score": float(best_score),
        "strategy": "classical",
        "qiskit_available": bool(QISKIT_AVAILABLE),
    }


def qaoa_optimize_interventions(
    evaluate_fn: Callable[[np.ndarray], float],
    n_agents: int,
    n_phases: int,
    max_iter: int = 100,
    force_classical: bool = False,
    seed: int = 42,
) -> dict:
    """Optimize intervention matrix using optional Qiskit sampling or classical fallback."""
    if n_agents <= 0 or n_phases <= 0:
        raise ValueError("n_agents and n_phases must be > 0")

    if force_classical or not QISKIT_AVAILABLE:
        return _classical_random_search(evaluate_fn, n_agents, n_phases, max_iter, seed)

    num_qubits = n_agents * n_phases
    candidates = _sample_qiskit_candidates(num_qubits, shots=max(32, max_iter))

    best = None
    best_score = -np.inf
    for vec in candidates:
        candidate = vec.reshape((n_phases, n_agents))
        score = _evaluate_candidate(evaluate_fn, candidate)
        if score > best_score:
            best_score = score
            best = candidate

    if best is None:
        return _classical_random_search(evaluate_fn, n_agents, n_phases, max_iter, seed)

    return {
        "interventions": best,
        "score": float(best_score),
        "strategy": "qaoa",
        "qiskit_available": True,
    }
