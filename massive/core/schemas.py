from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

# ============================================================
# GAME THEORY — PAYOFF MATRIX & STRATEGIC CONFIG
# ============================================================


class GamePayoff(BaseModel):
    """2×2 payoff matrix for Cooperation vs. Defection.

    Entries follow the standard prisoner-dilemma convention:
      cc — both cooperate   (consensus reward)
      cd — I cooperate, opponent defects (sucker's payoff)
      dc — I defect, opponent cooperates (temptation)
      dd — both defect      (punishment / chaos)
    """

    cc: float = 1.0  # Both cooperate → consensus
    cd: float = -1.0  # I cooperate, other defects → sucker
    dc: float = 1.0  # I defect, other cooperates → temptation
    dd: float = -1.0  # Both defect → chaos


class StrategicConfig(BaseModel):
    """Configuration for the Game Theory strategic force layer."""

    enabled: bool = False
    payoff_matrix: GamePayoff = Field(default_factory=GamePayoff)
    # ω — how much the payoff matters vs. the physical landscape (0.0–1.0)
    strategic_weight: float = 0.3


class Intervention(BaseModel):
    time_start: int = Field(description="Iteración donde inicia esta fase")
    time_end: int = Field(description="Iteración donde termina esta fase")
    model_name: str = Field(
        description=(
            "Nombre del modelo: 'lineal', 'umbral', 'memoria', 'backlash', "
            "'polarizacion', 'hk', 'contagio_competitivo', 'umbral_heterogeneo', "
            "'homofilia', 'replicador', 'nash', 'bayesiano' o 'sir'"
        )
    )
    parameters: Dict[str, Any] = Field(
        description=(
            "Parámetros numéricos. Ej: {'epsilon': 0.3} o {'umbral': 0.5}. "
            "En modo corporativo puede incluir 'target_nodes': lista de IDs de nodos "
            "a intervenir directamente (ej. líderes de opinión en la empresa)."
        )
    )
    fase_rationale: str = Field(
        description="Breve justificación sociológica/organizacional de esta fase"
    )
    target_nodes: Optional[List[str]] = Field(
        default=None,
        description=(
            "Opcional. Lista de IDs de nodos específicos a intervenir "
            "(líderes informales, directivos clave). Solo relevante en modo corporativo."
        ),
    )


class StrategyMatrix(BaseModel):
    interventions: List[Intervention] = Field(
        description="Secuencia temporal de intervenciones"
    )
