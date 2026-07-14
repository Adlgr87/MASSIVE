"""Intervention optimization utilities for MASSIVE."""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional
import logging

import numpy as np

log = logging.getLogger("massive.intervention_optimizer")


def _evaluate_candidate(
    evaluate_fn: Callable[[np.ndarray], float],
    candidate: np.ndarray,
) -> float:
    score = float(evaluate_fn(candidate))
    if not np.isfinite(score):
        return -np.inf
    return score


def _intervention_cost(
    interventions: np.ndarray,
    cost_scale_factor: float | None,
) -> float:
    """Cost model: density of non-zero actions scaled by national cost factor."""
    arr = np.asarray(interventions, dtype=float)
    density = float(np.mean(np.abs(arr) > 0))
    scale = float(cost_scale_factor) if cost_scale_factor is not None else 1.0
    return density * scale * arr.shape[0]  # phases * density * scale


def _fairness_penalty(interventions: np.ndarray) -> float:
    """Lower is better: high variance across agents means less fair targeting."""
    arr = np.asarray(interventions, dtype=float)
    per_agent = np.abs(arr).mean(axis=0)
    return float(np.std(per_agent))


def _complexity_penalty(interventions: np.ndarray) -> float:
    """Lower is better: more phase-to-phase flips => harder to implement."""
    arr = np.asarray(interventions, dtype=float)
    if arr.shape[0] < 2:
        return 0.0
    flips = np.mean(arr[1:] != arr[:-1])
    return float(flips)


def _composite_score(
    effectiveness: float,
    interventions: np.ndarray,
    cost_scale_factor: float | None,
    weights: dict[str, float],
) -> float:
    """Multi-objective scalarization (higher is better)."""
    cost = _intervention_cost(interventions, cost_scale_factor)
    fair = _fairness_penalty(interventions)
    complex_ = _complexity_penalty(interventions)
    return (
        weights.get("effectiveness", 1.0) * effectiveness
        - weights.get("cost", 0.25) * cost
        - weights.get("fairness", 0.1) * fair
        - weights.get("complexity", 0.1) * complex_
    )


def optimize_interventions(
    evaluate_fn: Callable[[np.ndarray], float],
    n_agents: int,
    n_phases: int,
    max_iter: int = 100,
    seed: int = 42,
    cost_scale_factor: Optional[float] = None,
    fiscal_constraint: Optional[float] = None,
    sector_multipliers: Optional[Dict[str, float]] = None,
    country_code: Optional[str] = None,
    objective_weights: Optional[Dict[str, float]] = None,
) -> dict:
    """
    Optimize interventions with stochastic search and explicit cost/feasibility.

    Fiscal and cost constraints affect **candidate sparsity / budget**, not only
    the iteration count. Optional multi-objective scalarization combines
    effectiveness, cost, fairness, and implementation complexity.

    Args:
        evaluate_fn: Function scoring intervention matrices (higher better).
        n_agents: Number of agents.
        n_phases: Number of intervention phases.
        max_iter: Search budget (iterations).
        seed: RNG seed.
        cost_scale_factor: National cost scale (Factbook).
        fiscal_constraint: Fiscal feasibility in [0, 1].
        sector_multipliers: Optional sector bias map.
        country_code: Optional Factbook country code.
        objective_weights: Optional weights for multi-objective terms.

    Returns:
        Dict with interventions, score, cost, feasibility report, and metadata.
    """
    if n_agents <= 0 or n_phases <= 0:
        raise ValueError("n_agents and n_phases must be > 0")
    if max_iter <= 0:
        raise ValueError("max_iter must be > 0")

    if country_code:
        try:
            from massive.core.factbook import get_factbook_context
            context = get_factbook_context()
            constraints = context.get_intervention_constraints(country_code)
            cost_scale_factor = constraints.get("cost_scale_factor", cost_scale_factor)
            fiscal_constraint = constraints.get("fiscal_constraint", fiscal_constraint)
            sector_multipliers = constraints.get("sector_multipliers", sector_multipliers)
            log.info("[InterventionOptimizer] Loaded constraints for %s", country_code)
        except Exception as e:
            log.warning("[InterventionOptimizer] Country load failed: %s", e)

    # Feasibility in [0, 1] — hard floor at 0.
    if fiscal_constraint is None:
        feasibility = 1.0
    else:
        feasibility = float(np.clip(fiscal_constraint, 0.0, 1.0))

    # Budget: max fraction of agent-phase slots that may be non-zero.
    # High cost_scale_factor and low feasibility → sparser interventions.
    scale = float(cost_scale_factor) if cost_scale_factor is not None else 1.0
    max_density = float(np.clip(feasibility / max(scale, 0.1), 0.05, 1.0))
    max_active = max(1, int(n_agents * n_phases * max_density))

    weights = {
        "effectiveness": 1.0,
        "cost": 0.25,
        "fairness": 0.1,
        "complexity": 0.1,
    }
    if objective_weights:
        weights.update({k: float(v) for k, v in objective_weights.items()})

    rng = np.random.default_rng(seed)

    def _sample_candidate(base: np.ndarray | None = None) -> np.ndarray:
        if base is None:
            candidate = rng.choice([-1.0, 0.0, 1.0], size=(n_phases, n_agents)).astype(np.float64)
        else:
            candidate = base.copy()
            flat = candidate.flatten()
            n_flip = max(1, int(0.1 * flat.size))
            idx = rng.choice(flat.size, size=n_flip, replace=False)
            flat[idx] = rng.choice([-1.0, 0.0, 1.0], size=n_flip)
            candidate = flat.reshape((n_phases, n_agents))

        # Enforce sparsity budget (hard constraint).
        flat = candidate.flatten()
        active = np.flatnonzero(np.abs(flat) > 0)
        if active.size > max_active:
            drop = rng.choice(active, size=active.size - max_active, replace=False)
            flat[drop] = 0.0
            candidate = flat.reshape((n_phases, n_agents))

        # Optional sector bias: push a phase toward a common sign.
        if sector_multipliers:
            sector_values = list(sector_multipliers.values())
            if sector_values and sum(sector_values) > 0 and rng.random() < 0.2:
                weights_s = np.asarray(sector_values, dtype=float)
                weights_s = weights_s / weights_s.sum()
                sign = 1.0 if weights_s[0] >= 0.5 else -1.0
                phase = int(rng.integers(0, n_phases))
                mask = candidate[phase] != 0
                candidate[phase, mask] = sign
        return candidate

    best = _sample_candidate()
    best_eff = _evaluate_candidate(evaluate_fn, best)
    best_score = _composite_score(best_eff, best, cost_scale_factor, weights)

    for _ in range(max_iter):
        candidate = _sample_candidate(best)
        eff = _evaluate_candidate(evaluate_fn, candidate)
        score = _composite_score(eff, candidate, cost_scale_factor, weights)
        if score > best_score:
            best_score = score
            best_eff = eff
            best = candidate

    cost = _intervention_cost(best, cost_scale_factor)
    feasible = feasibility >= 0.05 and cost <= (n_phases * max(scale, 0.1) + 1e-9)

    return {
        "interventions": best,
        "score": float(best_score),
        "effectiveness": float(best_eff),
        "strategy": "multiobjective_stochastic_search",
        "country_code": country_code,
        "cost": float(cost),
        "cost_scale_factor": cost_scale_factor,
        "fiscal_constraint": fiscal_constraint,
        "sector_multipliers": sector_multipliers,
        "feasibility": float(feasibility),
        "feasible": bool(feasible),
        "max_density": float(max_density),
        "objective_weights": weights,
        "fairness_penalty": _fairness_penalty(best),
        "complexity_penalty": _complexity_penalty(best),
    }


def create_economic_aware_optimizer(
    country_code: str,
    base_optimizer: Optional[Callable] = None,
) -> Callable:
    """
    Factory function to create an optimizer pre-configured with country economic data.

    Args:
        country_code: CIA country code (e.g., "US", "CH", "GM")
        base_optimizer: Optional base optimizer function to wrap

    Returns:
        Optimizer function pre-configured with Factbook economic data
    """
    try:
        from massive.core.factbook import get_factbook_context
        context = get_factbook_context()
        constraints = context.get_intervention_constraints(country_code)

        def economic_optimizer(
            evaluate_fn: Callable[[np.ndarray], float],
            n_agents: int,
            n_phases: int,
            **kwargs: Any,
        ) -> dict:
            all_kwargs = {**constraints, **kwargs}
            opt = base_optimizer or optimize_interventions
            return opt(
                evaluate_fn,
                n_agents,
                n_phases,
                country_code=country_code,
                **all_kwargs,
            )

        return economic_optimizer
    except Exception as e:
        log.warning("[InterventionOptimizer] economic factory fallback: %s", e)

        def fallback_optimizer(
            evaluate_fn: Callable[[np.ndarray], float],
            n_agents: int,
            n_phases: int,
            **kwargs: Any,
        ) -> dict:
            opt = base_optimizer or optimize_interventions
            return opt(evaluate_fn, n_agents, n_phases, country_code=country_code, **kwargs)

        return fallback_optimizer


def estimate_intervention_cost(
    interventions: np.ndarray,
    cost_scale_factor: float = 1.0,
    fiscal_constraint: float = 0.5,
) -> float:
    """
    Estimate the cost of interventions based on Factbook economic data.

    Args:
        interventions: Matrix of interventions (n_phases, n_agents)
        cost_scale_factor: Economic scale factor from Factbook GDP data
        fiscal_constraint: Fiscal feasibility from Factbook budget data

    Returns:
        Estimated cost of interventions
    """
    n_phases, n_agents = interventions.shape
    base_cost = n_phases * n_agents
    cost = base_cost * cost_scale_factor
    cost *= (1.0 + fiscal_constraint) * 0.5
    return float(cost)


def get_intervention_feasibility(
    interventions: np.ndarray,
    country_code: str,
) -> Dict[str, Any]:
    """
    Evaluate the feasibility of interventions given a country's economic situation.

    Args:
        interventions: Matrix of interventions
        country_code: Country to evaluate against

    Returns:
        Dictionary with feasibility metrics
    """
    try:
        from massive.core.factbook import get_factbook_context
        context = get_factbook_context()
        constraints = context.get_intervention_constraints(country_code)

        cost = estimate_intervention_cost(
            interventions,
            constraints.get("cost_scale_factor", 1.0),
            constraints.get("fiscal_constraint", 0.5),
        )

        country = context.get_country(country_code)
        return {
            "feasible": constraints.get("fiscal_constraint", 0.5) > 0.3,
            "cost": cost,
            "country": country_code,
            "gdp_per_capita": country.gdp_per_capita if country else None,
            "fiscal_health": constraints.get("fiscal_constraint", 0.5),
            "sector_effectiveness": constraints.get("sector_multipliers", {}),
        }
    except Exception as e:
        log.error("[InterventionOptimizer] Error evaluating feasibility: %s", e)
        return {
            "feasible": True,
            "cost": 0.0,
            "error": str(e),
        }
