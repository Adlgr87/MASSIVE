"""Layer 4 — Approximate Bayesian Computation + Neural Density Estimation.

Provides Bayesian hyperparameter calibration for the MASSIVE opinion-dynamics
engine using ABC-SMC (Sequential Monte Carlo) and an optional lightweight
neural density estimator (Mixture Density Network via ``torch``).

The three calibration parameters are the Layer 2 physics params:

    σ (sigma)       — noise temperature            ∈ [0.01, 0.20]
    ε (epsilon)     — HK bounded-confidence        ∈ [0.20, 0.35]
    λ (lambda_social) — social-network coupling    ∈ [0.00, 1.00]

Distance metric
===============
``compute_distance`` combines:

1. **Wasserstein-1** on the final opinion *distribution* (individual agent
   opinions), normalised by the opinion range [−1, 1].
2. **Normalised RMSE** on the *aggregate trajectory* (polarization P over
   time), normalised by the observed P range.

Distance = 0.5 · w_norm + 0.5 · rmse_norm  ∈ [0, 1]

References
----------
- Sisson et al. (2007), *Approximate Bayesian computation via Metropolis
  within sequential Monte Carlo* (ABC-SMC).
- Papamakarios et al. (2017), *Mixture Density Networks* for neural density
  estimation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
from scipy.stats import wasserstein_distance

from massive.core.physics_calibration import (
    PARAM_NAMES,
    PHYSICS_RANGES,
    PhysicsParams,
    p_to_opinions,
    simulate_opinion_dynamics,
)

# ── Constants ───────────────────────────────────────────────────────────────

# Default simulation settings for ABC calibration
_DEFAULT_N_AGENTS = 80
_DEFAULT_N_STEPS = 30
_DEFAULT_ETA = 0.1

# Weight of Wasserstein vs RMSE in combined distance
_WASSERSTEIN_WEIGHT = 0.5
_RMSE_WEIGHT = 0.5

# Opinion range half-width (bipolar [-1, 1])
_OPINION_RANGE = 2.0

# Perturbation kernel bandwidth (relative to each param's range) for SMC
_PERTURB_FRACTION = 0.10


# ── Trajectory container ────────────────────────────────────────────────────


@dataclass
class TrajectoryObservation:
    """Container for a trajectory that may have both aggregate and distribution data.

    Args:
        trajectory: 1-D array of aggregate values over time (e.g. mean opinion
            or polarization P).
        distribution: Optional 1-D array of individual agent opinions at the
            final time step.
    """

    trajectory: np.ndarray
    distribution: np.ndarray | None = None

    def __post_init__(self) -> None:
        self.trajectory = np.asarray(self.trajectory, dtype=np.float64)
        if self.distribution is not None:
            self.distribution = np.asarray(self.distribution, dtype=np.float64)


# ── ABCCalibrator ───────────────────────────────────────────────────────────


class ABCCalibrator:
    """ABC-SMC calibrator for MASSIVE physics hyperparameters.

    Uses Sequential Monte Carlo with decreasing distance thresholds to
    progressively refine the posterior over (σ, ε, λ).

    Args:
        n_agents: Number of agents per simulation.
        n_steps: Number of integration steps per simulation.
        eta: Integration step size for the Langevin dynamics.
        seed: Master random seed (deterministic sub-seeds are derived
            for each SMC round).

    Examples:
        >>> cal = ABCCalibrator(n_agents=50, n_steps=20, seed=42)
        >>> prior = cal.simulate_prior(100)
        >>> prior.shape
        (100, 3)
        >>> _ = cal.calibrate({"trajectory": obs_p, "distribution": obs_dist},
        ...                  n_rounds=2, n_samples=50, threshold=0.3)
        >>> summary = cal.posterior_summary()
    """

    def __init__(
        self,
        n_agents: int = _DEFAULT_N_AGENTS,
        n_steps: int = _DEFAULT_N_STEPS,
        eta: float = _DEFAULT_ETA,
        seed: int = 42,
    ) -> None:
        self.n_agents = n_agents
        self.n_steps = n_steps
        self.eta = eta
        self.seed = seed

        self.posterior: np.ndarray | None = None
        self.posterior_distances: np.ndarray | None = None
        self._prior_samples: np.ndarray | None = None
        self._prior_distances: np.ndarray | None = None
        self._observations: TrajectoryObservation | None = None
        self._initial_opinions: np.ndarray | None = None
        self._n_steps_obs: int = 0

    # ── Prior ───────────────────────────────────────────────────────────────

    def simulate_prior(self, n_samples: int) -> np.ndarray:
        """Sample hyperparameters from uniform empirical priors.

        σ ∈ [0.01, 0.20], ε ∈ [0.20, 0.35], λ ∈ [0.0, 1.0].

        Args:
            n_samples: Number of parameter vectors to draw.

        Returns:
            Array of shape ``(n_samples, 3)`` with columns
            ``[sigma, epsilon, lambda_social]``.
        """
        rng = np.random.default_rng(self.seed)
        lows = np.array([PHYSICS_RANGES[p][0] for p in PARAM_NAMES])
        highs = np.array([PHYSICS_RANGES[p][1] for p in PARAM_NAMES])
        return rng.uniform(low=lows, high=highs, size=(n_samples, 3))

    # ── Forward simulation ──────────────────────────────────────────────────

    def simulate(
        self,
        params: PhysicsParams | np.ndarray | dict[str, float],
        seed: int,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Run a single simulation with the given physics parameters.

        Args:
            params: Either a :class:`PhysicsParams` instance, a 3-element
                array ``[sigma, epsilon, lambda_social]``, or a dict with
                those keys.
            seed: Random seed for the simulation noise generator.

        Returns:
            Tuple ``(trajectory, final_opinions)`` where *trajectory* is a
            1-D array of polarization P values (length ``n_steps + 1``) and
            *final_opinions* is a 1-D array of agent opinions.
        """
        if isinstance(params, PhysicsParams):
            sigma = params.sigma
            epsilon = params.epsilon
            lambda_social = params.lambda_social
        elif isinstance(params, dict):
            sigma = params["sigma"]
            epsilon = params["epsilon"]
            lambda_social = params["lambda_social"]
        else:
            arr = np.asarray(params, dtype=np.float64).ravel()
            sigma, epsilon, lambda_social = arr[0], arr[1], arr[2]

        if self._initial_opinions is None:
            # Default: small spread, mean 0
            rng = np.random.default_rng(seed)
            self._initial_opinions = np.clip(rng.standard_normal(self.n_agents) * 0.05, -1.0, 1.0)

        return simulate_opinion_dynamics(
            sigma=sigma,
            epsilon=epsilon,
            lambda_social=lambda_social,
            n_agents=self.n_agents,
            n_steps=self._n_steps_obs,
            initial_opinions=self._initial_opinions,
            seed=seed,
            eta=self.eta,
        )

    # ── Distance ────────────────────────────────────────────────────────────

    def compute_distance(
        self,
        simulated_trajectory: TrajectoryObservation | np.ndarray | dict,
        observed_trajectory: TrajectoryObservation | np.ndarray | dict,
    ) -> float:
        """Compute the combined ABC distance between simulated and observed data.

        Distance = 0.5 · W₁_norm + 0.5 · RMSE_norm

        where *W₁* is the Wasserstein-1 distance on opinion distributions
        (or on aggregate trajectories when distributions are unavailable)
        and *RMSE* is the root-mean-squared error on the aggregate trajectory,
        normalised by the observed trajectory's range.

        Args:
            simulated_trajectory: Simulated data as a
                :class:`TrajectoryObservation`, dict, or plain array.
            observed_trajectory: Observed data in the same format.

        Returns:
            Combined distance in [0, 1] (0 = perfect match).
        """
        sim = _as_trajectory(simulated_trajectory)
        obs = _as_trajectory(observed_trajectory)

        # ── Wasserstein-1 on opinion distributions ───────────────────────────
        if sim.distribution is not None and obs.distribution is not None:
            w_dist = wasserstein_distance(sim.distribution, obs.distribution)
        else:
            # Fall back to Wasserstein on aggregate trajectories
            w_dist = _wasserstein_trajectories(sim.trajectory, obs.trajectory)

        w_norm = w_dist / _OPINION_RANGE

        # ── Normalised RMSE on aggregate trajectory ──────────────────────────
        sim_t = _resample(sim.trajectory, len(obs.trajectory))
        rmse = float(np.sqrt(np.mean((sim_t - obs.trajectory) ** 2)))
        obs_range = float(np.max(obs.trajectory) - np.min(obs.trajectory))
        obs_range = max(obs_range, 1e-6)
        rmse_norm = rmse / obs_range

        return _WASSERSTEIN_WEIGHT * w_norm + _RMSE_WEIGHT * rmse_norm

    # ── ABC-SMC calibration ─────────────────────────────────────────────────

    def calibrate(
        self,
        observations: TrajectoryObservation | np.ndarray | dict,
        n_rounds: int = 3,
        n_samples: int = 1000,
        threshold: float = 0.1,
        seed: int = 42,
    ) -> np.ndarray:
        """Run ABC-SMC to estimate the posterior over physics parameters.

        Sequential Monte Carlo proceeds in *n_rounds* rounds.  In round 0
        particles are drawn from the prior; in subsequent rounds particles
        are resampled from the previous accepted set, perturbed by a Gaussian
        kernel, and re-simulated.  The acceptance threshold decreases
        geometrically across rounds.

        Args:
            observations: Observed trajectory as a
                :class:`TrajectoryObservation`, dict with ``trajectory`` and
                optional ``distribution`` keys, or a 1-D array.
            n_rounds: Number of SMC rounds.
            n_samples: Number of particle simulations per round.
            threshold: Initial (round-0) acceptance threshold.  Decreases
                by a factor of ``n_rounds / (r + 1)`` in round *r*.
            seed: Master random seed.

        Returns:
            Posterior samples array of shape ``(n_accepted, 3)``.
        """

        # ── Normalise observations ──────────────────────────────────────────
        obs = _as_trajectory(observations)
        self._observations = obs

        # Determine simulation length from observations
        self._n_steps_obs = max(len(obs.trajectory) - 1, 1)

        # Build initial opinions from first observed P value
        rng_init = np.random.default_rng(seed)
        p0 = float(obs.trajectory[0]) if len(obs.trajectory) > 0 else 0.0
        self._initial_opinions = p_to_opinions(p0, self.n_agents, rng_init)

        # Construct observed distribution if not provided
        if obs.distribution is None:
            obs.distribution = p_to_opinions(
                float(obs.trajectory[-1]) if len(obs.trajectory) > 0 else 0.0,
                self.n_agents,
                rng_init,
            )

        # ── Deterministic seed sequence ─────────────────────────────────────
        seeds = self._get_seeds(seed, n_rounds)

        # ── Round 0: sample from prior ──────────────────────────────────────
        prior_samples = self.simulate_prior(n_samples)
        self._prior_samples = prior_samples
        distances = np.empty(n_samples, dtype=np.float64)

        for i in range(n_samples):
            traj, dist = self.simulate(prior_samples[i], seeds[0] + i)
            distances[i] = self.compute_distance(TrajectoryObservation(traj, dist), obs)

        self._prior_distances = distances.copy()

        accepted = distances <= threshold
        posterior = prior_samples[accepted]
        posterior_dist = distances[accepted]

        if len(posterior) == 0:
            # Fall back: accept the best 10 % of particles
            n_fallback = max(n_samples // 10, 5)
            idx = np.argsort(distances)[:n_fallback]
            posterior = prior_samples[idx]
            posterior_dist = distances[idx]

        # ── Rounds 1 … n_rounds-1: perturb + resample + re-simulate ─────────
        for r in range(1, n_rounds):
            # Decreasing threshold (geometric schedule)
            r_threshold = threshold * (1.0 - r / n_rounds)
            r_threshold = max(r_threshold, float(np.median(posterior_dist)))

            rng_r = np.random.default_rng(seeds[r])
            new_particles = []
            new_distances = []

            for _ in range(n_samples):
                # Resample from current posterior
                if len(posterior) > 0:
                    w = np.ones(len(posterior))
                    if posterior_dist is not None and len(posterior_dist) > 0:
                        # Weight by inverse distance (closer = higher weight)
                        w = 1.0 / (posterior_dist + 1e-8)
                    w = w / w.sum()
                    idx = rng_r.choice(len(posterior), p=w)
                    base = posterior[idx].copy()
                else:
                    base = self.simulate_prior(1)[0]

                # Perturb with Gaussian kernel
                perturb_widths = np.array(
                    [
                        (PHYSICS_RANGES[p][1] - PHYSICS_RANGES[p][0]) * _PERTURB_FRACTION
                        for p in PARAM_NAMES
                    ]
                )
                params = base + rng_r.normal(0, perturb_widths)
                params = _clip_to_ranges(params)

                traj, dist = self.simulate(params, seeds[r] + _)
                dist_val = self.compute_distance(TrajectoryObservation(traj, dist), obs)

                if dist_val <= r_threshold:
                    new_particles.append(params)
                    new_distances.append(dist_val)

            if new_particles:
                posterior = np.array(new_particles)
                posterior_dist = np.array(new_distances)
            else:
                # No improvement this round — keep previous posterior
                pass

        self.posterior = posterior
        self.posterior_distances = posterior_dist
        return posterior

    # ── Posterior diagnostics ───────────────────────────────────────────────

    def posterior_summary(self) -> dict[str, dict[str, float]]:
        """Compute posterior mean, std, and 90 % credible interval per parameter.

        Returns:
            Dict keyed by parameter name, each with ``mean``, ``std``,
            ``ci_lower``, ``ci_upper``, and ``n_samples``:
            ``{"sigma": {"mean": ..., "std": ..., "ci_lower": ..., "ci_upper": ..., "n": ...}, ...}``
        """

        if self.posterior is None or len(self.posterior) == 0:
            if self._prior_samples is not None:
                samples = self._prior_samples
            else:
                samples = self.simulate_prior(1)
        else:
            samples = self.posterior

        summary: dict[str, dict[str, float]] = {}
        for i, name in enumerate(PARAM_NAMES):
            col = samples[:, i]
            ci_lower = float(np.percentile(col, 5.0))
            ci_upper = float(np.percentile(col, 95.0))
            summary[name] = {
                "mean": float(np.mean(col)),
                "std": float(np.std(col)),
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "n": len(col),
            }
        return summary

    def posterior_mean_params(self) -> PhysicsParams:
        """Return posterior mean as a :class:`PhysicsParams` instance."""
        summary = self.posterior_summary()
        return PhysicsParams(
            sigma=summary["sigma"]["mean"],
            epsilon=summary["epsilon"]["mean"],
            lambda_social=summary["lambda_social"]["mean"],
        )

    def prior_mean_distance(self) -> float:
        """Mean distance of prior particles (baseline for comparison)."""
        if self._prior_distances is None:
            return float("nan")
        return float(np.mean(self._prior_distances))

    def posterior_mean_distance(self) -> float:
        """Mean distance of posterior particles."""
        if self.posterior_distances is None:
            return float("nan")
        return float(np.mean(self.posterior_distances))

    # ── Internal ────────────────────────────────────────────────────────────

    def _get_seeds(self, seed: int, n_rounds: int) -> np.ndarray:
        """Derive deterministic sub-seeds for each SMC round."""
        from massive.core.data_provenance import get_seed_sequence

        seeds_list = get_seed_sequence(seed, n_rounds)
        return np.array(seeds_list, dtype=np.int64)


def _as_trajectory(obj: Any) -> TrajectoryObservation:
    """Coerce various input formats into a :class:`TrajectoryObservation`."""
    if isinstance(obj, TrajectoryObservation):
        return obj
    if isinstance(obj, dict):
        return TrajectoryObservation(
            trajectory=np.asarray(obj["trajectory"], dtype=np.float64),
            distribution=(
                np.asarray(obj["distribution"], dtype=np.float64)
                if obj.get("distribution") is not None
                else None
            ),
        )
    arr = np.asarray(obj, dtype=np.float64)
    return TrajectoryObservation(trajectory=arr, distribution=None)


def _resample(a: np.ndarray, n: int) -> np.ndarray:
    """Linearly resample a 1-D array to length *n*."""
    if len(a) == n:
        return a
    from scipy.interpolate import interp1d

    x_old = np.arange(len(a))
    x_new = np.linspace(0, len(a) - 1, n)
    f = interp1d(x_old, a, kind="linear", bounds_error=False, fill_value="extrapolate")
    return np.clip(f(x_new), 0.0, 1.0)


def _wasserstein_trajectories(a: np.ndarray, b: np.ndarray) -> float:
    """Wasserstein distance between two 1-D arrays of possibly different length."""
    a = _resample(a, len(b))
    return float(wasserstein_distance(a, b))


def _clip_to_ranges(arr: np.ndarray) -> np.ndarray:
    """Clip each parameter to its empirical range."""
    result = arr.copy()
    for i, name in enumerate(PARAM_NAMES):
        lo, hi = PHYSICS_RANGES[name]
        result[i] = np.clip(result[i], lo, hi)
    return result


# ── NeuralPosteriorEstimator (optional) ────────────────────────────────────


class NeuralPosteriorEstimator:
    """Simple neural density estimator via a Mixture Density Network.

    Trains a learnable Gaussian-mixture model using ``torch`` autograd
    (maximum-likelihood on the posterior samples produced by the ABC-SMC
    run).  Unlike a parametric GMM fitted with EM, this approach can be
    extended to conditional MNWs that take the observed trajectory as
    context.

    Args:
        n_components: Number of Gaussian mixture components.
        hidden_size: Hidden-layer width for the latent mapping network.
        seed: Random seed for torch initialisation.

    Examples:
        >>> est = NeuralPosteriorEstimator(n_components=5, seed=42)
        >>> samples = np.random.randn(500, 3)
        >>> est.fit(samples)
        >>> new = est.sample(10)
        >>> new.shape
        (10, 3)
    """

    def __init__(
        self,
        n_components: int = 5,
        hidden_size: int = 32,
        seed: int = 42,
    ) -> None:
        self.n_components = n_components
        self.hidden_size = hidden_size
        self.seed = seed
        self._fitted = False
        self._weights: np.ndarray | None = None
        self._means: np.ndarray | None = None
        self._stds: np.ndarray | None = None

    def fit(
        self,
        samples: np.ndarray,
        lr: float = 0.05,
        n_iter: int = 300,
    ) -> NeuralPosteriorEstimator:
        """Fit the mixture density network to posterior samples.

        Args:
            samples: Array of shape ``(n_samples, n_dim)``.
            lr: Learning rate for Adam optimiser.
            n_iter: Number of gradient steps.

        Returns:
            ``self`` (for chaining).
        """

        try:
            import torch
        except ImportError as exc:  # pragma: no cover
            raise ImportError("torch is required for NeuralPosteriorEstimator") from exc

        samples = np.asarray(samples, dtype=np.float32)
        if samples.ndim != 2:
            raise ValueError(f"samples must be 2-D, got {samples.ndim}-D")
        n_dim = samples.shape[1]
        x = torch.from_numpy(samples)

        torch.manual_seed(self.seed)

        # ── Mixture parameters (unconstrained, transformed during forward) ──
        # Weights: softmax over logits
        log_w = torch.randn(self.n_components, requires_grad=True)
        # Means
        means = torch.randn(self.n_components, n_dim, requires_grad=True)
        # Log-stds
        log_stds = torch.randn(self.n_components, n_dim, requires_grad=True)

        optimiser = torch.optim.Adam([log_w, means, log_stds], lr=lr)

        for _ in range(n_iter):
            optimiser.zero_grad()

            weights = torch.softmax(log_w, dim=0)  # (K,)
            stds = torch.exp(log_stds)  # (K, D)

            # Compute log-likelihood of each sample under each component
            # shape: (N, K)
            log_probs = torch.zeros(x.shape[0], self.n_components)
            for k in range(self.n_components):
                dist = torch.distributions.Normal(means[k], stds[k])
                log_probs[:, k] = torch.log(weights[k] + 1e-10) + dist.log_prob(x).sum(dim=1)

            # log-sum-exp → log-likelihood
            log_likelihood = torch.logsumexp(log_probs, dim=1).mean()
            loss = -log_likelihood
            loss.backward()
            optimiser.step()

        self._weights = torch.softmax(log_w, dim=0).detach().numpy()
        self._means = means.detach().numpy()
        self._stds = torch.exp(log_stds).detach().numpy()
        self._fitted = True
        return self

    def sample(self, n: int) -> np.ndarray:
        """Draw *n* samples from the fitted mixture.

        Args:
            n: Number of samples to draw.

        Returns:
            Array of shape ``(n, n_dim)``.

        Raises:
            RuntimeError: If ``fit`` has not been called.
        """
        if not self._fitted:
            raise RuntimeError("Call fit() before sampling")

        rng = np.random.default_rng(self.seed)
        components = rng.choice(self.n_components, size=n, p=self._weights)
        n_dim = self._means.shape[1]
        out = np.empty((n, n_dim), dtype=np.float64)
        for k in range(self.n_components):
            mask = components == k
            nk = int(mask.sum())
            if nk > 0:
                out[mask] = rng.normal(self._means[k], self._stds[k], size=(nk, n_dim))
        return out

    def density(self, points: np.ndarray) -> np.ndarray:
        """Evaluate the probability density at each row of *points*.

        Args:
            points: Array of shape ``(n_points, n_dim)``.

        Returns:
            Array of shape ``(n_points,)`` with density values.
        """
        if not self._fitted:
            raise RuntimeError("Call fit() before evaluating density")

        points = np.asarray(points, dtype=np.float64)
        if points.ndim == 1:
            points = points.reshape(1, -1)

        n_dim = self._means.shape[1]
        total = np.zeros(points.shape[0])
        for k in range(self.n_components):
            comp_log_std = np.sum(np.log(self._stds[k] + 1e-300))
            diff = points - self._means[k]
            mahal = -0.5 * np.sum((diff / self._stds[k]) ** 2, axis=1)
            log_gaussian = mahal - comp_log_std - 0.5 * n_dim * np.log(2 * np.pi)
            total += self._weights[k] * np.exp(log_gaussian)
        return total


__all__ = [
    "TrajectoryObservation",
    "ABCCalibrator",
    "NeuralPosteriorEstimator",
]
