"""
micro_schemas.py — Modelos de datos para MASSIVE Micro
Simulación inversa de dinámica de grupos pequeños
"""

from pydantic import BaseModel, Field, field_validator
from typing import Literal


class MemberProfile(BaseModel):
    """Perfil de un miembro del grupo."""
    name: str = Field(default="", description="Nombre o identificador")
    role: str = Field(default="miembro", description="Rol en el grupo")
    initial_opinion: float | None = Field(default=None, ge=-1.0, le=1.0)
    cooperation_bias: float = Field(default=0.5, ge=0.0, le=1.0)
    hierarchy_bias: float = Field(default=0.5, ge=0.0, le=1.0)
    trust_bias: float = Field(default=0.5, ge=0.0, le=1.0)


class GroupProfile(BaseModel):
    """Descripción de un grupo pequeño para simulación micro."""
    n_members: int = Field(default=5, ge=3, le=15)
    context: Literal["friends", "family", "work", "couple", "neighbors", "custom"] = "work"
    context_label: str = Field(default="")

    initial_cohesion: float = Field(default=0.5, ge=0.0, le=1.0)
    communication_frequency: float = Field(default=0.3, ge=0.0, le=1.0)
    hierarchy_tolerance: float = Field(default=0.4, ge=0.0, le=1.0)
    external_pressure: float = Field(default=0.2, ge=0.0, le=1.0)
    diversity_of_opinion: float = Field(default=0.3, ge=0.0, le=1.0)

    members: list[MemberProfile] = Field(default_factory=list)

    @field_validator("members")
    @classmethod
    def _validate_members(cls, v, info):
        n = info.data.get("n_members", len(v))
        if v and len(v) != n:
            raise ValueError(f"members count ({len(v)}) must match n_members ({n})")
        return v


class SimVariation(BaseModel):
    """Variación de un parámetro para el ensemble."""
    param: str
    low: float
    high: float
    distribution: Literal["uniform", "normal"] = "uniform"


class EnsembleConfig(BaseModel):
    """Configuración de un ensemble de simulaciones."""
    n_simulations: int = Field(default=500, ge=50, le=100_000)
    steps_per_sim: int = Field(default=200, ge=20, le=2000)
    seed: int = Field(default=42)
    variations: list[SimVariation] = Field(default_factory=lambda: [
        SimVariation(param="coupling", low=0.05, high=0.8),
        SimVariation(param="external_pressure", low=0.0, high=0.5),
        SimVariation(param="initial_noise", low=0.01, high=0.3),
    ])
    n_clusters: int = Field(default=0, ge=0, description="0 = auto-detect")


class FamilyOfFutures(BaseModel):
    """Una familia de futuros: cluster de trayectorias similares."""
    id: int
    size: int
    proportion: float
    label: str = ""
    description: str = ""
    mean_features: dict[str, float] = Field(default_factory=dict)
    archetype_params: dict[str, float] = Field(default_factory=dict)
    risk_flags: list[str] = Field(default_factory=list)


class BifurcationMap(BaseModel):
    """Mapa de bifurcación: qué parámetros determinan la familia."""
    param_importances: dict[str, float] = Field(
        description="Importancia de cada parámetro (0-1)"
    )
    transition_costs: list[dict] = Field(
        default_factory=list,
        description="Costo de mover el grupo entre familias"
    )


class EnsembleResult(BaseModel):
    """Resultado completo de un ensemble de simulaciones."""
    group: GroupProfile
    config: EnsembleConfig
    n_families: int
    families: list[FamilyOfFutures]
    bifurcation: BifurcationMap
    stability: float = Field(default=0.0, ge=0.0, le=1.0,
                             description="Qué tan estable es la dinámica")
    summary: str = ""
