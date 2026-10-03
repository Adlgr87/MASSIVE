from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# Estimation method taxonomy used across all calibrated physics entries.
ESTIMATION_METHODS = Literal[
    "least_squares_fit",
    "maximum_likelihood",
    "method_of_moments",
    "fixed",
]

# ============================================================
# GAME THEORY — PAYOFF MATRIX & STRATEGIC CONFIG
# ============================================================


class GamePayoff(BaseModel):
    """2x2 payoff matrix for Cooperation vs. Defection.

    Entries follow the standard prisoner-dilemma convention:
      cc -- both cooperate   (consensus reward)
      cd -- I cooperate, opponent defects (sucker's payoff)
      dc -- I defect, opponent cooperates (temptation)
      dd -- both defect      (punishment / chaos)
    """

    cc: float = 1.0  # Both cooperate -> consensus
    cd: float = -1.0  # I cooperate, other defects -> sucker
    dc: float = 1.0  # I defect, other cooperates -> temptation
    dd: float = -1.0  # Both defect -> chaos


class StrategicConfig(BaseModel):
    """Configuration for the Game Theory strategic force layer."""

    enabled: bool = False
    payoff_matrix: GamePayoff = Field(default_factory=GamePayoff)
    # w -- how much the payoff matters vs. the physical landscape (0.0-1.0)
    strategic_weight: float = Field(0.3, ge=0.0, le=1.0)


VALID_MODEL_NAMES = Literal[
    "lineal",
    "umbral",
    "memoria",
    "backlash",
    "polarizacion",
    "hk",
    "contagio_competitivo",
    "umbral_heterogeneo",
    "homofilia",
    "replicador",
    "nash",
    "bayesiano",
    "sir",
]


class Intervention(BaseModel):
    time_start: int = Field(description="Iteracion donde inicia esta fase")
    time_end: int = Field(description="Iteracion donde termina esta fase")
    model_name: VALID_MODEL_NAMES = Field(
        description=(
            "Nombre del modelo: 'lineal', 'umbral', 'memoria', 'backlash', "
            "'polarizacion', 'hk', 'contagio_competitivo', 'umbral_heterogeneo', "
            "'homofilia', 'replicador', 'nash', 'bayesiano' o 'sir'"
        )
    )

    @model_validator(mode="after")
    def _validate_time_order(self) -> Intervention:
        if self.time_start > self.time_end:
            raise ValueError(
                f"time_start ({self.time_start}) must be <= time_end ({self.time_end})"
            )
        return self

    parameters: dict[str, Any] = Field(
        description=(
            "Parametros numericos. Ej: {'epsilon': 0.3} o {'umbral': 0.5}. "
            "En modo corporativo puede incluir 'target_nodes': lista de IDs de nodos "
            "a intervenir directamente (ej. líderes de opinión en la empresa)."
        )
    )
    fase_rationale: str = Field(
        description="Breve justificacion sociologica/organizacional de esta fase"
    )
    target_nodes: list[str] | None = Field(
        default=None,
        description=(
            "Opcional. Lista de IDs de nodos específicos a intervenir "
            "(leaders informales, directivos clave). Solo relevante en modo corporativo."
        ),
    )


class StrategyMatrix(BaseModel):
    interventions: list[Intervention] = Field(description="Secuencia temporal de intervenciones")


# ============================================================
# Layer 2 — Physics-equation parameter calibration schemas
# ============================================================
#
# These models validate ``configs/calibrated/physics_params_v1.0.0.yaml``.
# Every calibrated leaf is a ``ParamEntry`` carrying its traceability metadata
# (value / sem / source_dataset / estimation_method / empirical_reference).
#
# Physical invariant: MASSIVE normalises the opinion spectrum to [-1, 1].
# Opinion-domain quantities (attractor/repeller positions, the HK band) are
# constrained to that range at the schema level via Field(ge=, le=) /
# field_validators. Other calibrated parameters (noise multipliers, rigidity
# fractions, couplings) carry their own physically meaningful ranges.

# Type alias: a calibrated value may be a scalar or an explicit [min, max]
# interval (used for opinion-domain quantities such as attractor/repeller
# positions and the HK bounded-confidence band).
CalibratedValue = float | list[float]


def _check_opinion_positions(positions: list[float]) -> None:
    """Ensure every reported position lives inside the MASSIVE [-1, 1] spectrum."""
    for pos in positions:
        if pos < -1.0 or pos > 1.0:
            raise ValueError(f"opinion position {pos} outside [-1, 1] spectrum")


class ParamEntry(BaseModel):
    """A single calibrated physics parameter with full provenance.

    Attributes:
        value: Calibrated value -- a scalar float or a ``[min, max]`` interval.
        sem: Standard error / sensitivity of estimation (>= 0).
        source_dataset: Layer 1 dataset identifier (``A1``/``A2``/``A3``/...).
        estimation_method: How the value was estimated.
        empirical_reference: Academic citation grounding the parameter.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    value: CalibratedValue
    sem: float = Field(ge=0.0)
    source_dataset: str
    estimation_method: ESTIMATION_METHODS
    empirical_reference: str

    @model_validator(mode="after")
    def _validate_interval_order(self) -> ParamEntry:
        """Validate interval ordering (min <= max). Opinion-range bounds live on
        the domain fields (positions, HK band), not on generic multipliers."""
        v = self.value
        if isinstance(v, list):
            if len(v) != 2:
                raise ValueError(f"interval value must have exactly 2 elements [min, max], got {v}")
            if float(v[0]) > float(v[1]):
                raise ValueError(f"interval min ({v[0]}) must be <= max ({v[1]})")
        return self


class _SegmentSet(BaseModel):
    """Common shape: a ``mixed`` composite plus per-axis segment dicts."""

    model_config = ConfigDict(extra="forbid")

    mixed: ParamEntry
    age: dict[str, ParamEntry] = Field(default_factory=dict)
    education: dict[str, ParamEntry] = Field(default_factory=dict)
    income: dict[str, ParamEntry] = Field(default_factory=dict)

    def resolve(self, segment: str) -> ParamEntry:
        """Resolve a segment label to its ParamEntry.

        Args:
            segment: ``"mixed"`` or an ``axis:label`` form such as
                ``"age:old"``, ``"education:high_edu"`` or ``"income:low_inc"``.

        Returns:
            The matching ParamEntry for the requested segment.

        Raises:
            KeyError: If ``segment`` is unknown.
        """
        if segment == "mixed":
            return self.mixed
        known_axes = ("age", "education", "income")
        axis, sep, label = segment.partition(":")
        if sep:
            if axis not in known_axes:
                raise KeyError(
                    f"Unknown axis '{axis}' in segment '{segment}'. "
                    f"Known axes: {known_axes}; or 'mixed'."
                )
            try:
                return getattr(self, axis)[label]
            except KeyError as exc:
                raise KeyError(
                    f"Unknown segment '{segment}'. Known axes: "
                    f"age, education, income; or 'mixed'."
                ) from exc
        # Bare label fallback: search age -> education -> income.
        for ax in ("age", "education", "income"):
            ax_map = getattr(self, ax)
            if label in ax_map:
                return ax_map[label]
        raise KeyError(f"Unknown segment '{segment}'")


class AttractorBlock(BaseModel):
    """Energy-landscape attractor positions and strength."""

    model_config = ConfigDict(extra="forbid")

    positions: list[float] = Field(description="Attractor x-positions, each clipped to [-1, 1]")
    strength: ParamEntry

    @field_validator("positions")
    @classmethod
    def _clip_positions(cls, v: list[float]) -> list[float]:
        _check_opinion_positions(v)
        return v


class RepellerBlock(BaseModel):
    """Energy-landscape repeller (barrier) positions and strength."""

    model_config = ConfigDict(extra="forbid")

    positions: list[float] = Field(description="Repeller x-positions, each clipped to [-1, 1]")
    strength: ParamEntry

    @field_validator("positions")
    @classmethod
    def _clip_positions(cls, v: list[float]) -> list[float]:
        _check_opinion_positions(v)
        return v


class LangevinDriftParams(BaseModel):
    """Gradient-drift (cognitive rigidity / attraction) parameters."""

    model_config = ConfigDict(extra="forbid")

    opinion_attractors: ParamEntry
    opinion_repeller: ParamEntry
    cognitive_rigidity: _SegmentSet
    dimension_coupling: dict[str, float] = Field(
        default_factory=dict,
        description="Per-dimension drift coupling scales (mirror theta coefficients).",
    )


class LangevinSigmaParams(BaseModel):
    """Diffusion / noise (sigma) parameters."""

    model_config = ConfigDict(extra="forbid")

    base: ParamEntry
    context_volatility_sensitivity: ParamEntry
    segment_multiplier: _SegmentSet


class LangevinParams(BaseModel):
    """Full Langevin-layer calibration."""

    model_config = ConfigDict(extra="forbid")

    drift: LangevinDriftParams
    sigma: LangevinSigmaParams
    attractors: AttractorBlock
    repellers: RepellerBlock
    sigma_gaussian: ParamEntry
    eta: ParamEntry


class EpsBlock(BaseModel):
    """HK epsilon: base value, admissible band and per-segment distribution."""

    model_config = ConfigDict(extra="forbid")

    base: ParamEntry
    band: list[float] = Field(description="Admissible HK epsilon range [min, max], both in [-1, 1]")
    per_segment: _SegmentSet

    @field_validator("band")
    @classmethod
    def _validate_band(cls, v: list[float]) -> list[float]:
        _check_opinion_positions(v)
        if len(v) != 2 or v[0] > v[1]:
            raise ValueError("hk epsilon band must be [min, max] with min <= max")
        return v


class HKParams(BaseModel):
    """Hegselmann-Krause bounded-confidence parameters."""

    model_config = ConfigDict(extra="forbid")

    epsilon: EpsBlock


class DeGrootParams(BaseModel):
    """DeGroot weight-matrix calibration parameters."""

    model_config = ConfigDict(extra="forbid")

    authority_exponent: ParamEntry
    self_weight: ParamEntry
    authority_source: str


class PhysicsMeta(BaseModel):
    """Metadata describing the calibration artifact itself."""

    model_config = ConfigDict(extra="forbid")

    version: str
    layer: int = Field(ge=1)
    framework: str
    deterministic_seed: int = Field(ge=0)
    description: str


class PhysicsParams(BaseModel):
    """Top-level physics-parameter calibration container.

    Validates the full ``physics_params_v1.0.0.yaml`` artifact with
    ``extra="forbid"`` so schema drift is caught at load time.
    """

    model_config = ConfigDict(extra="forbid")

    meta: PhysicsMeta
    langevin: LangevinParams
    lambda_social: ParamEntry
    temperature: ParamEntry
    hk: HKParams
    degroot: DeGrootParams

    def get_segment_value(self, segment: str) -> dict:
        """Return the resolved scalar values for a given demographic segment.

        Args:
            segment: ``"mixed"`` or an ``axis:label`` segment identifier.

        Returns:
            Dict with ``cognitive_rigidity``, ``sigma_multiplier`` and
            ``hk_epsilon`` scalar floats for the requested segment.
        """
        rigidity = float(self.langevin.drift.cognitive_rigidity.resolve(segment).value)
        multiplier = float(self.langevin.sigma.segment_multiplier.resolve(segment).value)
        epsilon = float(self.hk.epsilon.per_segment.resolve(segment).value)
        return {
            "cognitive_rigidity": rigidity,
            "sigma_multiplier": multiplier,
            "hk_epsilon": epsilon,
        }


__all__ = [
    "ParamEntry",
    "LangevinParams",
    "LangevinDriftParams",
    "LangevinSigmaParams",
    "HKParams",
    "DeGrootParams",
    "PhysicsParams",
    "PhysicsMeta",
    "AttractorBlock",
    "RepellerBlock",
    "EpsBlock",
    "ESTIMATION_METHODS",
]
