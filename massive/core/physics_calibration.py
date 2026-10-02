"""
physics_calibration.py — Layer 2: Physics/Math Equation Calibration for MASSIVE.

Loads and validates the traceable physics-parameter artefact
``configs/calibrated/physics_params_v1.0.0.yaml`` and exposes the calibrated
quantities for the simulation engines:

    • Langevin  :dx_i/dt = -∇U(x_i) + Σ_ℓ w_ℓ·(A_ℓ·G(x))_i + θ(a_i)·η_i
    • Energy SDE: x_i(t+η) = x_i(t) - η·∇U(x_i) + η·λ·(x̄ - x_i) + √(2η·T)·ε
    • HK        : bounded-confidence threshold ε per demographic profile
    • DeGroot   : asymmetric weight matrix W_ij from network authority

Conventions: Google-style docstrings, ``from __future__ import annotations``,
NumPy arrays, ``np.clip`` on every opinion-domain value, deterministic seeds
sourced from ``PhysicsParams.meta.deterministic_seed``.

Author: MASSIVE Research — A4 (Statistical Physicist, Parametric Calibration)
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Any

import numpy as np
import yaml

from massive.core.schemas import PhysicsParams as PhysicsParamsSchema

# Opinion-domain bounds used to clip every opinion-range quantity on output.
OPINION_MIN: float = -1.0
OPINION_MAX: float = 1.0

# Default location of the Layer 2 calibration artefact.
_DEFAULT_CONFIG_PATH: str = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "configs",
    "calibrated",
    "physics_params_v1.0.0.yaml",
)

# ── Canonical three-param shorthand (used by Layer 4: ABC-SMC & backtest) ────
# These mirror the empirical prior ranges defined in empirical_calibration.py
#   RUIDO_BASE_MIN=0.01, RUIDO_BASE_MAX=0.20  →  σ range
#   HK_EPSILON_MIN=0.20, HK_EPSILON_MAX=0.35  →  ε range
#   social_influence_lambda ∈ [0, 1]          →  λ range
PHYSICS_RANGES: dict[str, tuple[float, float]] = {
    "sigma": (0.01, 0.20),
    "epsilon": (0.20, 0.35),
    "lambda_social": (0.0, 1.0),
}

PARAM_NAMES: tuple[str, ...] = ("sigma", "epsilon", "lambda_social")


# ============================================================
# Loading & validation
# ============================================================


def _load_yaml(path: str) -> dict:
    """Load the YAML calibration artefact from ``path``.

    Args:
        path: Filesystem path to the physics_params YAML file.

    Returns:
        Parsed YAML as a dict.

    Raises:
        FileNotFoundError: If ``path`` does not exist.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"physics params config not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def load_physics_params(path: str | None = None) -> PhysicsParamsSchema:
    """Load and validate the physics-parameter artefact against the schema.

    Args:
        path: Optional explicit path. Defaults to the bundled
            ``configs/calibrated/physics_params_v1.0.0.yaml``.

    Returns:
        A validated ``PhysicsParams`` instance (``extra="forbid"``).
    """
    return PhysicsParamsSchema.model_validate(_load_yaml(path or _DEFAULT_CONFIG_PATH))


@lru_cache(maxsize=4)
def _load_cached(path: str) -> PhysicsParamsSchema:
    """Intern validated parameters so repeated lookups are allocation-free."""
    return load_physics_params(path)


def get_physics_params(segment: str = "mixed", path: str | None = None) -> PhysicsParamsSchema:
    """Return validated physics parameters, asserting ``segment`` is resolvable.

    The returned ``PhysicsParams`` contains *all* demographic segments;
    ``segment`` selects which sub-segment downstream consumers should resolve
    (e.g. ``langevin_drift``, ``hk_epsilon_distribution``). This function
    validates that ``segment`` actually exists in the artefact so callers fail
    fast on typos.

    Args:
        segment: Demographic segment label (``"mixed"`` or ``axis:label``).
        path: Optional explicit path to the YAML artefact.

    Returns:
        Validated ``PhysicsParams`` with all segments available.

    Raises:
        KeyError: If ``segment`` is not present in the artefact.
    """
    params = _load_cached(path or _DEFAULT_CONFIG_PATH)
    # Fail-fast validation that the requested segment exists.
    params.get_segment_value(segment)
    object.__setattr__(params, "_active_segment", segment)
    return params


# ============================================================
# (a) Langevin ∇V — cognitive rigidity / attraction drift
# ============================================================


def _resolve_segment_values(params: PhysicsParamsSchema, segment: str) -> dict:
    """Resolve cognitive rigidity, sigma multiplier and HK epsilon for a segment."""
    return params.get_segment_value(segment)


def _opinion_well_width(params: PhysicsParamsSchema) -> float:
    """Return a² of the double-well U = (x² - a²)² from the attractor positions."""
    a = float(np.max(np.abs(params.langevin.drift.opinion_attractors.value)))
    return float(a * a)


def langevin_drift(x: float, segment: str, params: PhysicsParamsSchema) -> float:
    """Compute ∇V(x) for the opinion double-well, scaled by segment rigidity.

    The opinion potential is a symmetric double well

        U(x) = (x² - a²)²        with a = 0.7  (minima at x = ±0.7)

    whose gradient (force) is

        ∇U(x) = 4·x·(x² - a²)

    This is the cognitive-drift term of the Langevin equation
    ``dx/dt = -∇U(x) + ...``. Cognitive rigidity (Wilson & Maher, 2007),
    calibrated per demographic segment from A1 microdata, scales the magnitude
    of this gradient: a more rigid agent is more strongly anchored to its
    basin (resists noise / social disruption) but commits faster to a pole.

    The returned value is ∇V (the *gradient*); the Langevin integrator moves
    in the gradient-descent direction ``x_{t+1} = x_t - η·∇V`` which pushes
    opinions toward the nearest attractor (±0.7).

    Args:
        x: Current opinion in the bipolar domain [-1, 1].
        segment: Demographic segment (``"mixed"`` or ``axis:label``).
        params: Validated ``PhysicsParams``.

    Returns:
        ∇V(x) — the potential gradient (float).  Sign is such that
        ``x - η·∇V`` descends toward the nearest attractor.
    """
    x_clipped = float(np.clip(x, OPINION_MIN, OPINION_MAX))
    rigid = float(_resolve_segment_values(params, segment)["cognitive_rigidity"])
    a2 = _opinion_well_width(params)
    grad = 4.0 * x_clipped * (x_clipped * x_clipped - a2)
    return float(rigid * grad)


# ============================================================
# (b) σ — diffusion / noise
# ============================================================


def context_dependent_sigma(
    volatility: float,
    segment: str,
    params: PhysicsParamsSchema,
) -> float:
    """Compute the context-dependent diffusion coefficient σ(t).

    σ(t) = σ_base · σ_segment · (1 + k · volatility)

    where ``volatility`` is the A3 timeseries volatility and ``k`` is the
    ``context_volatility_sensitivity``. Higher A3 volatility ⇒ more
    decision-space noise (Risken, 1996), modulated per demographic segment.

    Args:
        volatility: Normalised A3 timeseries volatility ∈ [0, 1].
        segment: Demographic segment (``"mixed"`` or ``axis:label``).
        params: Validated ``PhysicsParams``.

    Returns:
        Effective diffusion coefficient σ(t) (float).
    """
    base = float(params.langevin.sigma.base.value)
    k = float(params.langevin.sigma.context_volatility_sensitivity.value)
    mult = float(_resolve_segment_values(params, segment)["sigma_multiplier"])
    k = max(0.0, k)
    return float(base * mult * (1.0 + k * float(volatility)))


# ============================================================
# (c) Hegselmann-Krause HK ε — bounded-confidence threshold
# ============================================================


def hk_epsilon_distribution(
    segment: str,
    params: PhysicsParamsSchema,
    n: int = 1000,
    seed: int | None = None,
) -> np.ndarray:
    """Sample the bounded-confidence threshold distribution for a segment.

    Draws ``n`` samples from a Normal centred on the segment's calibrated
    ε value with its standard error, then clips every sample into the
    admissible HK band [0.20, 0.35] (Hegselmann & Krause, 2002). The result is
    a *distribution* of personal thresholds — not a single scalar — reflecting
    empirical interaction-tolerance heterogeneity from A2 network data.

    Args:
        segment: Demographic segment (``"mixed"`` or ``axis:label``).
        params: Validated ``PhysicsParams``.
        n: Number of samples (population size proxy).
        seed: RNG seed (defaults to ``params.meta.deterministic_seed``).

    Returns:
        NumPy array of shape ``(n,)`` with every ε ∈ [0.20, 0.35].
    """
    entry = params.hk.epsilon.per_segment.resolve(segment)
    center = float(entry.value)
    sem = float(entry.sem)
    band = params.hk.epsilon.band
    lo, hi = float(band[0]), float(band[1])
    rng_seed = seed if seed is not None else int(params.meta.deterministic_seed)
    rng = np.random.default_rng(rng_seed)
    samples = rng.normal(loc=center, scale=sem, size=n)
    return np.clip(samples, lo, hi)


# ============================================================
# (d) DeGroot W_ij — asymmetric weight matrix from authority
# ============================================================


def degroot_weight_matrix(
    A: np.ndarray,
    authority_scores: np.ndarray,
    params: PhysicsParamsSchema | None = None,
    self_weight: float | None = None,
    authority_exponent: float | None = None,
) -> np.ndarray:
    """Build a row-stochastic DeGroot influence matrix from authority metrics.

    W_ij = (1 - s) · Â_ij + s · δ_ij

    where the directed influence from j on i is proportional to the edge
    weight ``A_ij`` times ``authority_j ** alpha`` (higher-authority nodes
    receive more incoming weight — i.e. column sums correlate with authority,
    DeGroot 1974; Cha et al. 2010). Rows are normalised to sum to 1.

    Args:
        A: Adjacency matrix (N, N), non-negative. ``A[i,j]`` = influence
            potential i→j / j→i depending on convention; here column j is the
            source weighted by ``authority_j``.
        authority_scores: Authority per node (N,), non-negative.
        params: Optional validated PhysicsParams providing
            ``degroot.authority_exponent`` and ``degroot.self_weight``.
        self_weight: Override teleport/self-loop weight ``s`` ∈ [0, 1].
        authority_exponent: Override authority exponent ``alpha``.

    Returns:
        Row-stochastic weight matrix W (N, N) with rows summing to 1.0.
    """
    A_arr = np.asarray(A, dtype=np.float64)
    auth = np.asarray(authority_scores, dtype=np.float64)
    n = A_arr.shape[0]

    if params is not None:
        if authority_exponent is None:
            authority_exponent = float(params.degroot.authority_exponent.value)
        if self_weight is None:
            self_weight = float(params.degroot.self_weight.value)

    alpha = float(authority_exponent if authority_exponent is not None else 0.7)
    s = float(self_weight if self_weight is not None else 0.1)
    s = float(np.clip(s, 0.0, 1.0))
    alpha = max(0.0, alpha)

    # Avoid 0^alpha for zero-authority nodes.
    auth_safe = np.where(auth <= 0.0, 1e-6, auth)
    W = A_arr * (auth_safe[None, :] ** alpha)
    np.fill_diagonal(W, 0.0)

    row_sums = W.sum(axis=1, keepdims=True)
    row_sums = np.where(row_sums == 0.0, 1.0, row_sums)
    W = W / row_sums

    # Teleport / self-loop for aperiodic, well-posed DeGroot dynamics.
    W = (1.0 - s) * W + s * np.eye(n)
    return W


# ============================================================
# Layer 4 convenience: shorthand PhysicsParams + simulation
# ============================================================
# The full pydantic model above carries rich provenance metadata for every
# parameter and per-segment variants.  Layer 4 (ABC-SMC and backtesting)
# operates on three scalar physics parameters for tractability: σ, ε, λ.
# The helpers below bridge that gap.


class PhysicsParams:
    """Lightweight, frozen dataclass wrapper around the three scalar physics params.

    This is the *shorthand* form used by the ABC-SMC calibrator and the
    historical backtester.  It mirrors the pydantic ``PhysicsParamsSchema``
    but collapses the nested, segment-aware structure into three scalars.

    Attributes:
        sigma: Temperature / noise intensity (σ).
        epsilon: Hegselmann-Krause bounded-confidence threshold (ε).
        lambda_social: Social-network coupling weight (λ).

    Example::

        from massive.core.physics_calibration import PhysicsParams

        p = PhysicsParams(sigma=0.05, epsilon=0.25, lambda_social=0.5)
        p.validate()  # checks ranges against PHYSICS_RANGES
    """

    __slots__ = ("sigma", "epsilon", "lambda_social")

    def __init__(self, sigma: float = 0.05, epsilon: float = 0.25, lambda_social: float = 0.5) -> None:
        self.sigma = float(sigma)
        self.epsilon = float(epsilon)
        self.lambda_social = float(lambda_social)

    def validate(self) -> None:
        """Validate that every parameter falls within its empirical range.

        Raises:
            ValueError: If any parameter is outside its allowed bounds.
        """
        for name in PARAM_NAMES:
            lo, hi = PHYSICS_RANGES[name]
            val = getattr(self, name)
            if not (lo <= val <= hi):
                raise ValueError(
                    f"{name} = {val} outside allowed range [{lo}, {hi}]"
                )

    def to_dict(self) -> dict[str, float]:
        """Serialise to a plain dictionary."""
        return {
            "sigma": self.sigma,
            "epsilon": self.epsilon,
            "lambda_social": self.lambda_social,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PhysicsParams":
        """Build a :class:`PhysicsParams` from a dictionary.

        Args:
            data: Dict with keys ``sigma``, ``epsilon``, ``lambda_social``.

        Returns:
            A :class:`PhysicsParams` instance.
        """
        return cls(
            sigma=float(data["sigma"]),
            epsilon=float(data["epsilon"]),
            lambda_social=float(data["lambda_social"]),
        )

    @classmethod
    def from_schema(cls, schema: PhysicsParamsSchema) -> "PhysicsParams":
        """Extract the three scalar physics params from a validated schema object.

        Args:
            schema: A validated ``PhysicsParamsSchema`` (from ``get_physics_params``).

        Returns:
            A :class:`PhysicsParams` with the scalar values extracted.
        """
        return cls(
            sigma=float(schema.langevin.sigma.base.value),
            epsilon=float(schema.hk.epsilon.base.value),
            lambda_social=float(schema.lambda_social.value),
        )

    def __repr__(self) -> str:
        return (
            f"PhysicsParams(sigma={self.sigma:.4f}, "
            f"epsilon={self.epsilon:.4f}, "
            f"lambda_social={self.lambda_social:.4f})"
        )


def load_calibrated_params(path: str | None = None) -> PhysicsParams:
    """Load calibrated physics parameters (shorthand 3-param form).

    Reads the full Layer 2 artefact and extracts the three scalar parameters
    (σ, ε, λ) used by the compact simulation.

    Args:
        path: Optional explicit path to the YAML.  Defaults to
            ``configs/calibrated/physics_params_v1.0.0.yaml``.

    Returns:
        A :class:`PhysicsParams` instance.
    """
    schema = load_physics_params(path)
    return PhysicsParams.from_schema(schema)


def save_calibrated_params(params: PhysicsParams, path: str | Path) -> None:
    """Persist shorthand physics parameters to a simple YAML file.

    Args:
        params: The 3-parameter :class:`PhysicsParams` to save.
        path: Destination YAML file path.
    """

    import yaml
    from pathlib import Path

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(params.to_dict(), fh, default_flow_style=False, sort_keys=True)


def p_to_opinions(
    p_value: float,
    n_agents: int,
    rng: np.random.Generator,
) -> np.ndarray:
    """Convert a polarization index P ∈ [0, 1] to initial opinions in [-1, 1].

    The polarization metric used throughout MASSIVE is *std / half_range*.
    For bipolar [-1, 1] the half-range is 1.0, so P = std(opinions).

    A bimodal distribution is constructed so that the resulting std approximates
    the supplied polarization value:

        opinions = N(+μ, σ_c) ⊕ N(−μ, σ_c)

    where *μ* and *σ_c* are chosen so that ``std ≈ p_value``.

    Args:
        p_value: Target polarization in [0, 1].
        n_agents: Number of agents to generate.
        rng: NumPy random generator (for determinism).

    Returns:
        Array of shape ``(n_agents,)`` with opinions clipped to [-1, 1].
    """

    p_value = float(np.clip(p_value, 0.0, 1.0))
    half = n_agents // 2
    remainder = n_agents - half

    # Bimodal concentration: means at ±μ where μ increases with p.
    # When p=0 → μ ≈ 0.05 (tiny spread); when p=1 → μ ≈ 0.8 (near poles).
    mu = 0.05 + p_value * 0.75
    sigma_component = 0.10 + p_value * 0.15

    opinions = np.empty(n_agents, dtype=np.float64)
    opinions[:half] = rng.normal(mu, sigma_component, half)
    opinions[half:] = rng.normal(-mu, sigma_component, remainder)
    return np.clip(opinions, -1.0, 1.0)


def simulate_opinion_dynamics(
    sigma: float,
    epsilon: float,
    lambda_social: float,
    n_agents: int,
    n_steps: int,
    initial_opinions: np.ndarray,
    seed: int,
    eta: float = 0.1,
    *,
    interventions: list[tuple[int, dict]] | None = None,
    attractor_strength: float = 1.0,
    attractor_position: float = 0.7,
) -> tuple[np.ndarray, np.ndarray]:
    """Compact vectorised Langevin-dynamics opinion simulation.

    Implements the discrete Energy SDE (the same equation used by
    ``SocialEnergyEngine.step``) but fully vectorised over agents for speed
    — critical for ABC-SMC which may run thousands of simulations:

        x_i(t+η) = x_i(t) - η·∇U(x_i) + η·λ·(x̄_ε − x_i) + √(2ησ)·ε_i

    where:

    * **∇U** is the gradient of the opinion double-well potential
      ``U(x) = 0.25·(x² - a²)²`` (with ``a = 0.7``, attractors at ±0.7).
    * **x̄_ε** is the mean opinion of agents within HK *epsilon* of agent *i*.
    * **ε_i ~ N(0, 1)**.

    Args:
        sigma: Temperature / noise intensity (σ).
        epsilon: Hegselmann-Krause bounded-confidence threshold (ε).
        lambda_social: Social-network coupling weight (λ).
        n_agents: Number of agents.
        n_steps: Number of integration steps.
        initial_opinions: Array ``(n_agents,)`` of initial opinions in [-1, 1].
        seed: Random seed for the noise generator.
        eta: Integration step size (default 0.1, matching ``energy_engine``).
        interventions: Optional list of ``(step_index, forcing_dict)`` where
            ``forcing_dict`` has keys ``direction`` ∈ {−1, +1} and
            ``strength`` — a temporary opinion boost simulating external events.
        attractor_strength: Multiplier on the landscape force.
        attractor_position: Half-width of the double-well potential (a). Attractors at ±a.

    Returns:
        Tuple ``(trajectory, final_opinions)`` where:
        * ``trajectory`` — array of length ``n_steps + 1`` containing the
          polarization index P = std at each time step.
        * ``final_opinions`` — array of length ``n_agents`` with the final
          opinion distribution.

    Example::

        from massive.core.physics_calibration import p_to_opinions, simulate_opinion_dynamics
        import numpy as np

        rng = np.random.default_rng(42)
        init = p_to_opinions(0.28, n_agents=50, rng=rng)
        traj, dist = simulate_opinion_dynamics(
            sigma=0.05, epsilon=0.25, lambda_social=0.5,
            n_agents=50, n_steps=30,
            initial_opinions=init, seed=42,
        )
        print(f"P trajectory: {traj}")
    """

    rng = np.random.default_rng(seed)
    opinions = np.clip(initial_opinions.copy(), OPINION_MIN, OPINION_MAX)

    # Double-well: U(x) = 0.25*(x² - a²)²  with a = 0.7
    # ∇U = dU/dx = x*(x² - a²) = x³ - a²*x
    # Landscape force = -∇U = -x³ + a²*x = a²*x - x³
    a_well = attractor_position
    a2 = a_well * a_well

    interventions = interventions or []
    # Track active intervention steps and their remaining duration
    active_forcings: list[tuple[int, float, int]] = []  # (step, strength, remaining)

    trajectory = np.empty(n_steps + 1, dtype=np.float64)
    trajectory[0] = float(np.std(opinions))

    sqrt_2eta_sigma = np.sqrt(2.0 * eta * sigma)

    for t in range(n_steps):
        # ── Start new interventions at this step ──────────────────────────────
        for step_idx, forcing in interventions:
            if step_idx == t:
                direction = float(forcing.get("direction", 0.0))
                strength = float(forcing.get("strength", 0.1))
                duration = int(forcing.get("duration", 3))
                if direction != 0.0:
                    active_forcings.append((t, direction * strength, duration))

        # ── Active intervention forcing ──────────────────────────────────────
        # direction > 0: push opinions away from centre (increase polarization)
        # direction < 0: push opinions toward centre (decrease polarization)
        for f_step, f_dir_str, f_rem in active_forcings:
            if f_rem > 0:
                # Radial push: direction * sign(x) moves agents toward poles
                radial_push = f_dir_str * eta * np.sign(opinions + 1e-8)
                opinions += radial_push
                opinions = np.clip(opinions, OPINION_MIN, OPINION_MAX)
            f_rem -= 1

        # Remove expired forcings
        active_forcings = [(s, d, r - 1) for s, d, r in active_forcings if r > 0]

        # ── Bounded-confidence neighbour means (HK model) ───────────────────
        diffs = np.abs(opinions[:, None] - opinions[None, :])
        mask = diffs <= epsilon
        np.fill_diagonal(mask, True)
        counts = mask.sum(axis=1).astype(np.float64)
        counts = np.where(counts == 0.0, 1.0, counts)
        neighbor_means = (mask.astype(np.float64) @ opinions) / counts

        # ── Landscape gradient (double-well) ───────────────────────────────
        du_dx = opinions**3 - a2 * opinions  # ∇U = x³ - a²x
        landscape_force = -(1.0 - lambda_social) * du_dx * attractor_strength

        # ── Social coupling ────────────────────────────────────────────────
        social_force = lambda_social * (neighbor_means - opinions)

        # ── Stochastic noise ───────────────────────────────────────────────
        noise = sqrt_2eta_sigma * rng.standard_normal(n_agents)

        # ── Langevin update ────────────────────────────────────────────────
        opinions = opinions + eta * (landscape_force + social_force) + noise
        opinions = np.clip(opinions, OPINION_MIN, OPINION_MAX)

        trajectory[t + 1] = float(np.std(opinions))

    return trajectory, opinions.copy()


__all__ = [
    "PhysicsParams",
    "PhysicsParamsSchema",
    "PHYSICS_RANGES",
    "PARAM_NAMES",
    "load_physics_params",
    "get_physics_params",
    "load_calibrated_params",
    "save_calibrated_params",
    "langevin_drift",
    "context_dependent_sigma",
    "hk_epsilon_distribution",
    "degroot_weight_matrix",
    "p_to_opinions",
    "simulate_opinion_dynamics",
]
