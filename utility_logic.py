"""
MASSIVE — Utility Logic (Game Theory Layer)

Calculates the Strategic Force that biases agents toward
cooperation (consensus) or defection (fragmentation) based
on a 2×2 payoff matrix and the observed neighbourhood opinion.

Reference:
  Nash (1950) — Equilibrium Points in n-Person Games
  Axelrod (1984) — The Evolution of Cooperation
"""

from __future__ import annotations

from schemas import GamePayoff


def calculate_strategic_force(
    agent_opinion: float,
    neighbors_opinions: list[float],
    matrix: GamePayoff,
    neutral: float = 0.0,
    proximity_threshold: float = 0.2,
) -> float:
    """
    Computes the strategic reward gradient for a single agent.

    The function evaluates the *best response* given the average
    neighbour opinion and returns the payoff incentive that should
    be added (scaled externally) to the Langevin update.

    Logic:
      • Neighbours near the neutral point → cooperate with them is
        beneficial  → incentive = cc − dc  (pull toward centre)
      • Neighbours far from the neutral point → defection pays more
        → incentive = dd − cd  (may push toward fragmentation)

    Args:
        agent_opinion: Current opinion of the focal agent (unused in the
            payoff calculation but available for future extensions).
        neighbors_opinions: List of neighbour opinion values.  Returns 0
            immediately if the list is empty.
        matrix: GamePayoff instance with the 2×2 payoff values.
        neutral: Neutral point of the opinion range.  Defaults to 0.0
            for the primary [-1, 1] bipolar range.  Pass 0.5 explicitly
            when using the [0, 1] probabilistic range.
        proximity_threshold: Absolute distance from *neutral* below which
            neighbours are considered "near consensus" (default 0.2).
            For the [-1, 1] range this means |avg| < 0.2, matching the
            original proposal specification.

    Returns:
        Signed float representing the strategic incentive. Positive values
        pull the agent toward the dominant coalition; negative values push
        it away.
    """
    if not neighbors_opinions:
        return 0.0

    avg_neighbor = sum(neighbors_opinions) / len(neighbors_opinions)

    if abs(avg_neighbor - neutral) < proximity_threshold:
        # Neighbours are near consensus → cooperation is the best response
        return matrix.cc - matrix.dc
    else:
        # Neighbours are polarised → defection/fragmentation pays more
        return matrix.dd - matrix.cd
