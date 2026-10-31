"""Structural tests for the explicit coupling matrix (Fase 1).

These tests pin the properties that were missing before the coupling rebuild:

* the interaction graph is *declared* (not buried in the potential algebra);
* it is dense enough to be a coupled system and contains a feedback cycle;
* every declared term changes the trajectory when ablated;
* the model exposes a real response surface (it is not a constant function);
* cross-variable directions are correct: same-direction terms move together,
  opposite-direction terms move apart.

They are behavioural, not numeric: they must survive a legitimate recalibration,
but fail if the model silently regresses to the old feed-forward chain where
4 of 5 state variables influenced nothing.
"""

from __future__ import annotations

import numpy as np
import pytest

from metrics.unified_metrics import calculate_polarization
from multilayer_engine import (
    COUPLING_RATIONALE,
    DEFAULT_COUPLING_GAINS,
    STATE_VARIABLES,
    K,
    MultilayerEngine,
    multi_potential_gradient,
)

# ── helpers ──────────────────────────────────────────────────────────────────


def _run(gains=None, n_agents=300, steps=300, **kwargs) -> np.ndarray:
    engine = MultilayerEngine(N=n_agents, seed=42, dt=0.02, coupling_gains=gains, **kwargs)
    engine.run(steps=steps, store_history=False)
    return engine.x


def _summary(state: np.ndarray) -> dict[str, float]:
    return {
        "polarization": float(calculate_polarization(state[:, 0], "bipolar")),
        "mean_opinion": float(state[:, 0].mean()),
        "cooperation": float(state[:, 1].mean()),
        "hierarchy": float(state[:, 2].mean()),
        "income": float(state[:, 3].mean()),
        "info_access": float(state[:, 4].mean()),
    }


def _jacobian(gains, at_value: float = 0.4) -> np.ndarray:
    """Numerical Jacobian of the drift, d(x_dot_i)/d(x_j)."""
    eps = 1e-6
    point = np.full((1, K), at_value)
    jac = np.zeros((K, K))
    for j in range(K):
        plus, minus = point.copy(), point.copy()
        plus[0, j] += eps
        minus[0, j] -= eps
        jac[:, j] = -(
            multi_potential_gradient(plus, gains)[0] - multi_potential_gradient(minus, gains)[0]
        ) / (2 * eps)
    return jac


# ── the graph is declared and auditable ─────────────────────────────────────


class TestCouplingIsDeclared:
    def test_every_gain_has_a_rationale(self):
        """A coupling without a stated mechanism is unjustified."""
        missing = [term for term in DEFAULT_COUPLING_GAINS if term not in COUPLING_RATIONALE]
        assert not missing, f"coupling terms without rationale: {missing}"

    def test_terms_reference_real_state_variables(self):
        """No coupling may name a variable that does not exist."""
        for source, target in DEFAULT_COUPLING_GAINS:
            assert source in STATE_VARIABLES
            assert target in STATE_VARIABLES

    def test_no_self_coupling(self):
        """Self-dynamics belong to the potential, not to the coupling table."""
        assert all(source != target for source, target in DEFAULT_COUPLING_GAINS)

    def test_coupling_density_is_not_a_feed_forward_chain(self):
        """The graph must be a coupled system, not a 2-link chain.

        Before the rebuild the potential had 2 of 20 possible cross-couplings.
        """
        jac = _jacobian(DEFAULT_COUPLING_GAINS)
        cross = [(i, j) for i in range(K) for j in range(K) if i != j and abs(jac[i, j]) > 1e-6]
        assert len(cross) >= 6, f"only {len(cross)} cross-couplings: model is too sparse"

    def test_feedback_cycle_exists(self):
        """At least one cycle must close, or the model stays feed-forward."""
        graph: dict[str, set[str]] = {name: set() for name in STATE_VARIABLES}
        for source, target in DEFAULT_COUPLING_GAINS:
            graph[source].add(target)

        def reachable(start: str) -> set[str]:
            seen, frontier = set(), [start]
            while frontier:
                node = frontier.pop()
                for nxt in graph[node]:
                    if nxt not in seen:
                        seen.add(nxt)
                        frontier.append(nxt)
            return seen

        cycles = [name for name in STATE_VARIABLES if name in reachable(name)]
        assert cycles, "the coupling graph is acyclic: no feedback loop exists"


# ── every declared link is functional ───────────────────────────────────────


class TestEveryCouplingIsFunctional:
    @pytest.mark.parametrize("term", sorted(DEFAULT_COUPLING_GAINS))
    def test_ablating_a_term_changes_the_trajectory(self, term):
        """Removing a declared coupling must visibly change the outcome.

        A term that can be ablated without any measurable consequence is
        decorative, and decorative terms are worse than absent ones: they
        inflate the state, the cost and the illusion of richness.
        """
        baseline = _summary(_run())
        ablated_gains = dict(DEFAULT_COUPLING_GAINS)
        ablated_gains.pop(term)
        ablated = _summary(_run(gains=ablated_gains))

        deltas = {key: abs(ablated[key] - baseline[key]) for key in baseline}
        assert (
            max(deltas.values()) > 1e-3
        ), f"coupling {term} has no measurable effect; deltas={deltas}"

    def test_income_is_not_a_dead_variable(self):
        """Income must not collapse to a constant 0.5.

        Previously `income` relaxed to a fixed 0.5 and had no in-edges at all:
        its per-agent spread halved and it influenced nothing.
        """
        state = _run()
        assert state[:, 3].std() > 0.12, "income collapsed towards a constant"
        assert abs(state[:, 3].mean() - 0.5) > 0.02 or state[:, 3].std() > 0.12

    def test_hierarchy_is_bistable_and_consequential(self):
        """Hierarchy must stay bimodal *and* move something downstream."""
        state = _run()
        hierarchy = state[:, 2]
        extremes = np.mean((hierarchy < 0.15) | (hierarchy > 0.85))
        assert extremes > 0.8, "hierarchy is no longer bimodal"

        without = dict(DEFAULT_COUPLING_GAINS)
        without.pop(("hierarchy", "income"))
        income_with = state[:, 3].mean()
        income_without = _run(gains=without)[:, 3].mean()
        assert abs(income_with - income_without) > 1e-3

    def test_network_force_reaches_every_dimension(self):
        """The social layers must influence all behaviours, not only opinion.

        With the force applied to opinion alone, 'multilayer' described the
        topology of one term rather than a coupled multi-variable system.
        """
        baseline = _summary(_run(coupling=0.3))
        uncoupled = _summary(_run(coupling=0.0))
        moved = [
            key
            for key in ("cooperation", "hierarchy", "income", "info_access")
            if abs(baseline[key] - uncoupled[key]) > 1e-3
        ]
        assert len(moved) >= 3, f"network force only affects {moved}"


# ── direction semantics ─────────────────────────────────────────────────────


class TestCouplingDirections:
    def test_declared_positive_terms_move_together(self):
        """A positive gain must mean 'both go up'."""
        state = _run()
        base_coop = state[:, 1].mean()

        boosted = dict(DEFAULT_COUPLING_GAINS)
        boosted[("opinion", "cooperation")] = 1.6  # strong alignment
        strong = _run(gains=boosted)

        # Agents that end up further from neutral must cooperate more.
        far = np.abs(strong[:, 0]) > np.median(np.abs(strong[:, 0]))
        near = ~far
        assert strong[far, 1].mean() > strong[near, 1].mean()
        assert base_coop > 0

    def test_negative_gain_flips_the_relationship(self):
        """Declaring a negative gain must invert the target's response.

        This is the capability the model did not have: before the rebuild every
        cross-coupling was non-negative, so no variable could ever move opposite
        to another.
        """
        positive = dict(DEFAULT_COUPLING_GAINS)
        positive[("hierarchy", "income")] = 0.4
        negative = dict(DEFAULT_COUPLING_GAINS)
        negative[("hierarchy", "income")] = -0.4

        pos = _run(gains=positive)
        neg = _run(gains=negative)

        # With a negative gain, conformists (high hierarchy) must end up with
        # *less* income than rebels — the opposite of the positive case.
        conformists = pos[:, 2] > 0.85
        rebels = pos[:, 2] < 0.15
        assert pos[conformists, 3].mean() > pos[rebels, 3].mean()
        assert neg[conformists, 3].mean() < neg[rebels, 3].mean()


# ── the model is not a constant function ────────────────────────────────────


class TestResponseSurface:
    def test_polarization_responds_to_declared_knobs(self):
        """Polarization must move by >0.05 across reasonable configurations.

        Before the rebuild it was 0.697 ± 0.005 for every seed, population size,
        dt and layer weighting — i.e. the model returned a near-constant and had
        nothing to optimise.
        """
        outputs = []
        for gain in (0.0, 0.25, 0.5, 0.75):
            gains = dict(DEFAULT_COUPLING_GAINS)
            gains[("info_access", "opinion")] = gain
            outputs.append(_summary(_run(gains=gains))["polarization"])

        spread = max(outputs) - min(outputs)
        assert spread > 0.05, f"polarization spread {spread:.4f} is too small"

    def test_coupling_intensity_moves_the_output(self):
        values = [_summary(_run(coupling=c))["polarization"] for c in (0.0, 0.3, 0.6)]
        spread = max(values) - min(values)
        assert spread > 0.02, f"coupling has no effect: spread {spread:.4f}"

    def test_layer_weighting_changes_secondary_variables(self):
        """Layer weights must matter for more than just numerical noise."""
        social = _summary(_run(layer_weights=(0.9, 0.05, 0.05)))
        economic = _summary(_run(layer_weights=(0.05, 0.05, 0.9)))
        deltas = [abs(social[key] - economic[key]) for key in ("cooperation", "info_access")]
        assert max(deltas) > 0.01, f"layer weights do not matter: deltas={deltas}"


# ── numerical health ────────────────────────────────────────────────────────


class TestNumericalHealth:
    @pytest.mark.parametrize("coupling", [0.0, 0.3, 1.0])
    def test_ranges_respected_and_finite(self, coupling):
        state = _run(coupling=coupling)
        assert np.isfinite(state).all()
        assert state[:, 0].min() >= -1.0 and state[:, 0].max() <= 1.0
        assert state[:, 1:].min() >= 0.0 and state[:, 1:].max() <= 1.0

    def test_high_info_access_does_not_saturate_the_clip(self):
        """The echo-chamber term must not push every agent onto ±1.

        Saturation would mean the reported polarization is an artefact of
        clipping rather than a property of the dynamics.
        """
        gains = dict(DEFAULT_COUPLING_GAINS)
        gains[("info_access", "opinion")] = 0.5
        state = _run(gains=gains)
        saturated = float(np.mean(np.abs(state[:, 0]) > 0.98))
        assert saturated < 0.10, f"{saturated:.1%} of agents pinned to the boundary"
