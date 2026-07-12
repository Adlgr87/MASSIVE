"""
MASSIVE — Utility Logic (Game Theory Layer)

Calculates the Strategic Force that biases agents toward
cooperation (consensus) or defection (fragmentation) based
on a 2×2 payoff matrix and the observed neighbourhood opinion.

Also integrates CIA World Factbook data for:
- Social pressure calculation using ethnic/religious/language group distributions
- Demographic-aware strategic force

Reference:
  Nash (1950) — Equilibrium Points in n-Person Games
  Axelrod (1984) — The Evolution of Cooperation
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
import logging

from massive.core.schemas import GamePayoff

log = logging.getLogger("massive.utility_logic")


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


def calculate_social_pressure(
    agent_opinion: float,
    neighbors_opinions: List[float],
    social_pressure_weights: Optional[Dict[str, float]] = None,
    ethnic_groups: Optional[Dict[str, float]] = None,
    religious_groups: Optional[Dict[str, float]] = None,
    language_groups: Optional[Dict[str, float]] = None,
    diversity_modulation: float = 1.0,
) -> float:
    """
    Calculates social pressure based on CIA World Factbook demographic data.
    
    Social pressure influences agents to conform to group norms. In more
    homogeneous societies (low diversity), social pressure is stronger.
    In diverse societies, pressure is weaker due to competing norms.
    
    This integrates CIA World Factbook data through the social_pressure_weights
    parameter, which contains diversity indices for ethnic, religious, and
    language groups.
    
    Args:
        agent_opinion: Current opinion of the focal agent
        neighbors_opinions: List of neighbour opinion values
        social_pressure_weights: Dictionary with keys 'ethnic', 'religious', 
            'language' and values [0, 1] where higher values indicate LESS
            diversity (more social pressure). Typically from FactbookContext.
        ethnic_groups: Optional raw ethnic group distribution for custom calculation
        religious_groups: Optional raw religious group distribution
        language_groups: Optional raw language group distribution
        diversity_modulation: Multiplicative factor to adjust pressure strength
    
    Returns:
        Social pressure force. Positive values push agent toward neighbor mean.
    
    Example:
        from massive.core.factbook import FactbookContext
        context = FactbookContext()
        context.load_country("US")
        weights = context.get_social_pressure_weights("US")
        
        pressure = calculate_social_pressure(
            agent_opinion=0.5,
            neighbors_opinions=[0.6, 0.4, 0.7],
            social_pressure_weights=weights
        )
    """
    if not neighbors_opinions:
        return 0.0
    
    # Calculate base social pressure (conformity to neighbors)
    neighbor_mean = sum(neighbors_opinions) / len(neighbors_opinions)
    opinion_diff = neighbor_mean - agent_opinion
    
    # Base pressure strength
    base_pressure = opinion_diff * 0.5  # Default modulation factor
    
    # If we have social pressure weights from Factbook, use them
    if social_pressure_weights:
        # Calculate composite diversity index
        ethnic_weight = social_pressure_weights.get("ethnic", 0.5)
        religious_weight = social_pressure_weights.get("religious", 0.5)
        language_weight = social_pressure_weights.get("language", 0.5)
        
        # Higher weights = less diversity = stronger social pressure
        # Invert and normalize: diversity_factor ranges from 0 to 1
        # where 0 = maximum diversity (no pressure), 1 = no diversity (maximum pressure)
        diversity_factor = (
            (1.0 - ethnic_weight) * 0.4 +
            (1.0 - religious_weight) * 0.4 +
            (1.0 - language_weight) * 0.2
        )
        
        # Invert: less diversity = more pressure
        pressure_multiplier = 1.0 + (1.0 - diversity_factor) * 2.0
    else:
        # Use custom group distributions if provided
        if ethnic_groups or religious_groups or language_groups:
            diversity_factor = 0.0
            count = 0
            
            if ethnic_groups:
                diversity_factor += _calculate_diversity_index(ethnic_groups) * 0.4
                count += 0.4
            if religious_groups:
                diversity_factor += _calculate_diversity_index(religious_groups) * 0.4
                count += 0.4
            if language_groups:
                diversity_factor += _calculate_diversity_index(language_groups) * 0.2
                count += 0.2
            
            if count > 0:
                diversity_factor /= count
            
            pressure_multiplier = 1.0 + (1.0 - diversity_factor) * 2.0
        else:
            # Default: assume moderate social pressure
            pressure_multiplier = 1.5
    
    # Apply modulation factors
    total_multiplier = pressure_multiplier * diversity_modulation
    
    return base_pressure * total_multiplier


def _calculate_diversity_index(distribution: Dict[str, float]) -> float:
    """
    Calculate diversity index from a group distribution.
    
    Uses the Simpson diversity index (1 - Herfindahl index).
    Higher values indicate more diversity.
    
    Args:
        distribution: Dictionary of group_name -> percentage
        
    Returns:
        Diversity index in range [0, 1]
    """
    if not distribution:
        return 0.0
    
    # Normalize percentages to sum to 1
    total = sum(distribution.values())
    if total <= 0:
        return 0.0
    
    normalized = {k: v / total for k, v in distribution.items()}
    
    # Calculate Herfindahl index (sum of squares)
    herfindahl = sum(p ** 2 for p in normalized.values())
    
    # Diversity = 1 - Herfindahl
    return 1.0 - herfindahl


def calculate_group_cohesion(
    agent_group: str,
    neighbor_groups: List[str],
    social_groups: Dict[str, Dict[str, float]],
    group_type: str = "ethnic",
) -> float:
    """
    Calculate cohesion force based on group membership.
    
    Agents feel stronger connections to others in their own ethnic,
    religious, or language group.
    
    Args:
        agent_group: The group identifier of the focal agent
        neighbor_groups: List of group identifiers for neighbors
        social_groups: Dictionary with group distributions (from Factbook)
        group_type: Type of group ('ethnic', 'religious', 'language')
        
    Returns:
        Cohesion multiplier > 1.0 if agent shares group with neighbors
    """
    if not neighbor_groups:
        return 1.0
    
    # Get the distribution for this group type
    group_dist = social_groups.get(group_type, {})
    if not group_dist:
        return 1.0
    
    # Count how many neighbors share the agent's group
    matching_neighbors = sum(1 for g in neighbor_groups if g == agent_group)
    total_neighbors = len(neighbor_groups)
    
    if total_neighbors == 0:
        return 1.0
    
    # Calculate proportion of matching neighbors
    match_proportion = matching_neighbors / total_neighbors
    
    # Get the size of the agent's group in the population
    agent_group_size = group_dist.get(agent_group, 0.0)
    if agent_group_size <= 0:
        return 1.0
    
    # Larger groups have stronger cohesion effects
    # Also, more matching neighbors = stronger cohesion
    cohesion = 1.0 + (match_proportion * agent_group_size * 0.5)
    
    return cohesion


def calculate_demographic_strategic_force(
    agent_opinion: float,
    neighbors_opinions: List[float],
    matrix: GamePayoff,
    demographic_matrix: Optional[Any] = None,
    age_group: int = 0,
    **kwargs,
) -> float:
    """
    Enhanced strategic force with demographic modulation.
    
    Uses the 5D demographic sensitivity matrix from Factbook data
    to modulate the strategic force based on the agent's demographic group.
    
    Args:
        agent_opinion: Current opinion of the focal agent
        neighbors_opinions: List of neighbour opinion values
        matrix: GamePayoff instance
        demographic_matrix: 5x5 demographic sensitivity matrix from Factbook
        age_group: Age group index (0-4 for 0-14, 15-24, 25-54, 55-64, 65+)
        **kwargs: Additional arguments passed to calculate_strategic_force
        
    Returns:
        Strategic force modulated by demographic factors
    """
    # Get base strategic force
    base_force = calculate_strategic_force(
        agent_opinion, neighbors_opinions, matrix, **kwargs
    )
    
    # If we have demographic matrix and age group, apply modulation
    if demographic_matrix is not None and 0 <= age_group < 5:
        # Get sensitivity for opinion dimension (index 0)
        opinion_sensitivity = demographic_matrix[age_group, 0]
        
        # Apply modulation: higher sensitivity = stronger force
        modulation_factor = 1.0 + opinion_sensitivity * 2.0
        return base_force * modulation_factor
    
    return base_force
