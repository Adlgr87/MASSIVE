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
) -> dict:
    """
    Optimize interventions with stochastic search, considering economic constraints.
    
    Integrates CIA World Factbook economic data:
    - cost_scale_factor: Scales intervention costs based on national wealth (GDP per capita)
    - fiscal_constraint: Limits intervention feasibility based on budget balance
    - sector_multipliers: Adjusts intervention effectiveness by economic sector
    
    Args:
        evaluate_fn: Function to evaluate intervention quality
        n_agents: Number of agents to optimize for
        n_phases: Number of intervention phases
        max_iter: Maximum optimization iterations
        seed: Random seed for reproducibility
        cost_scale_factor: Economic cost scaling from Factbook (higher = more expensive interventions)
        fiscal_constraint: Fiscal feasibility [0, 1] from Factbook (0 = impossible, 1 = no constraint)
        sector_multipliers: Sector effectiveness multipliers from Factbook
        country_code: Country code for automatic Factbook parameter loading
        
    Returns:
        Dictionary with optimized interventions, score, and metadata
        
    Example:
        from massive.core.factbook import FactbookContext
        context = FactbookContext()
        context.load_country("US")
        constraints = context.get_intervention_constraints("US")
        
        result = optimize_interventions(
            evaluate_fn=evaluate_function,
            n_agents=1000,
            n_phases=10,
            **constraints
        )
    """
    if n_agents <= 0 or n_phases <= 0:
        raise ValueError("n_agents and n_phases must be > 0")

    # Load country-specific constraints if country_code provided
    if country_code:
        try:
            from massive.core.factbook import get_factbook_context
            context = get_factbook_context()
            constraints = context.get_intervention_constraints(country_code)
            cost_scale_factor = constraints.get("cost_scale_factor", cost_scale_factor)
            fiscal_constraint = constraints.get("fiscal_constraint", fiscal_constraint)
            sector_multipliers = constraints.get("sector_multipliers", sector_multipliers)
            log.info(f"[InterventionOptimizer] Cargando restricciones para {country_code}")
        except Exception as e:
            log.warning(f"[InterventionOptimizer] Error cargando datos del país: {e}")

    # Apply fiscal constraint
    if fiscal_constraint is not None:
        max_iter = int(max_iter * fiscal_constraint)
        if max_iter < 10:
            max_iter = 10
        log.info(f"[InterventionOptimizer] Ajustando iteraciones por restricción fiscal: {max_iter}")

    # Apply cost scaling
    if cost_scale_factor is not None:
        # Higher cost = fewer iterations, more selective interventions
        cost_adjustment = min(1.0, 1.0 / max(0.1, cost_scale_factor))
        max_iter = int(max_iter * cost_adjustment)
        log.info(f"[InterventionOptimizer] Ajustando iteraciones por costo: {max_iter}")

    rng = np.random.default_rng(seed)
    
    # Create initial candidate
    # Use sector multipliers if available to bias initial interventions
    if sector_multipliers:
        # Bias interventions toward more effective sectors
        sector_values = list(sector_multipliers.values())
        weights = np.array(sector_values) / sum(sector_values)
        # Map sectors to intervention directions
        # Higher sector multiplier = more likely to have interventions in that direction
        initial_direction = 2.0 * (weights[0] - 0.5)  # Simplified: positive or negative bias
    else:
        initial_direction = 0.0
    
    # Initial interventions with possible bias
    best = rng.choice([-1.0, 1.0], size=(n_phases, n_agents)).astype(np.float64)
    
    # Apply initial bias if we have sector data
    if sector_multipliers:
        for phase in range(n_phases):
            if rng.random() < 0.3:  # 30% chance to apply bias
                sign = 1.0 if initial_direction > 0 else -1.0
                best[phase] = sign * np.ones(n_agents)
    
    best_score = _evaluate_candidate(evaluate_fn, best)

    for iteration in range(max_iter):
        # Create new candidate
        candidate = rng.choice([-1.0, 1.0], size=(n_phases, n_agents)).astype(np.float64)
        
        # Apply cost constraints: fewer changes in high-cost environments
        if cost_scale_factor and cost_scale_factor > 1.0:
            # In high-cost countries, prefer smaller, more targeted interventions
            n_changes = max(1, int(n_agents * n_phases * 0.5 / cost_scale_factor))
            candidate_flat = candidate.flatten()
            change_indices = rng.choice(len(candidate_flat), n_changes, replace=False)
            candidate_flat[:] = best.flatten()
            candidate_flat[change_indices] = rng.choice([-1.0, 1.0], n_changes)
            candidate = candidate_flat.reshape((n_phases, n_agents))
        
        score = _evaluate_candidate(evaluate_fn, candidate)
        if score > best_score:
            best_score = score
            best = candidate

    # Calculate intervention cost if scale factor available
    intervention_cost = 0.0
    if cost_scale_factor:
        # Cost is proportional to number of intervention phases and agents
        intervention_cost = n_phases * n_agents * cost_scale_factor * 0.01
    
    return {
        "interventions": best,
        "score": float(best_score),
        "strategy": "stochastic_search",
        "country_code": country_code,
        "cost": intervention_cost,
        "cost_scale_factor": cost_scale_factor,
        "fiscal_constraint": fiscal_constraint,
        "sector_multipliers": sector_multipliers,
        "feasibility": fiscal_constraint if fiscal_constraint else 0.5,
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
        
    Example:
        from massive.core.intervention_optimizer import create_economic_aware_optimizer
        
        us_optimizer = create_economic_aware_optimizer("US")
        result = us_optimizer(evaluate_fn, n_agents=1000, n_phases=10)
    """
    try:
        from massive.core.factbook import get_factbook_context
        context = get_factbook_context()
        constraints = context.get_intervention_constraints(country_code)
        
        def economic_optimizer(
            evaluate_fn: Callable[[np.ndarray], float],
            n_agents: int,
            n_phases: int,
            **kwargs,
        ) -> dict:
            # Merge constraints with kwargs
            all_kwargs = {**constraints, **kwargs}
            return optimize_interventions(
                evaluate_fn,
                n_agents,
                n_phases,
                country_code=country_code,
                **all_kwargs,
            )
        
        return economic_optimizer
        
    except Exception as e:
        log.error(f"[InterventionOptimizer] Error creating economic optimizer: {e}")
        return base_optimizer or optimize_interventions


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
    
    # Base cost: proportional to number of intervention points
    base_cost = n_phases * n_agents
    
    # Scale by economic factors
    cost = base_cost * cost_scale_factor
    
    # Adjust for fiscal constraint (higher constraint = lower effective cost)
    cost *= (1.0 + fiscal_constraint) * 0.5
    
    return cost


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
        
        return {
            "feasible": constraints.get("fiscal_constraint", 0.5) > 0.3,
            "cost": cost,
            "country": country_code,
            "gdp_per_capita": context.get_country(country_code).gdp_per_capita if context.get_country(country_code) else None,
            "fiscal_health": constraints.get("fiscal_constraint", 0.5),
            "sector_effectiveness": constraints.get("sector_multipliers", {}),
        }
    except Exception as e:
        log.error(f"[InterventionOptimizer] Error evaluating feasibility: {e}")
        return {
            "feasible": True,
            "cost": 0.0,
            "error": str(e),
        }
