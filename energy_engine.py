"""
energy_engine.py — Motor de Energía Social para MASSIVE
Implementa dinámica de Langevin sobre una red social con paisaje de energía configurable.

La ecuación de Langevin discreta para cada agente i es:
    x_i(t+η) = x_i(t) - η·∇U(x_i) + η·λ·(x̄_neighbors - x_i) + √(2η·T)·ε

Donde:
  - ∇U(x)   : gradiente del paisaje de energía (atractores/repulsores gaussianos)
  - λ        : lambda_social — balance entre paisaje (0) y red social (1)
  - T        : temperatura — nivel de ruido / libre albedrío
  - ε ~ N(0,1): ruido estocástico

Integración con CIA World Factbook:
  - Gini index para ajustar desigualdad en el paisaje energético
  - Wealth distribution para modificar fuerza de atractores/repulsores
  - Sector composition para paisajes económicos
"""
import logging
from typing import Any, Dict, Optional

import numpy as np

log = logging.getLogger("massive")

try:
    from numba import njit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    log.warning("[EnergyEngine] Numba no instalado — usando ruta Python (más lenta).")
    def njit(*args, **kwargs):
        """No-op decorator when Numba is not installed."""
        def decorator(fn):
            return fn
        return decorator if args and callable(args[0]) else decorator


# Ancho gaussiano por defecto para pozos/picos del paisaje
_SIGMA = 0.3


@njit
def _landscape_gradient_jit(
    x: float,
    att_positions: np.ndarray,
    att_strengths: np.ndarray,
    rep_positions: np.ndarray,
    rep_strengths: np.ndarray,
    sigma2: float,
) -> float:
    """
    JIT-compiled gradient of the energy landscape U(x).
    Works with plain arrays so Numba can compile it.
    """
    grad = 0.0
    for i in range(len(att_positions)):
        diff = x - att_positions[i]
        g = np.exp(-diff * diff / (2.0 * sigma2))
        grad += att_strengths[i] * diff / sigma2 * g
    for i in range(len(rep_positions)):
        diff = x - rep_positions[i]
        g = np.exp(-diff * diff / (2.0 * sigma2))
        grad -= rep_strengths[i] * diff / sigma2 * g
    return grad


@njit
def _step_jit(
    opinions: np.ndarray,
    neighbor_mean: np.ndarray,
    noise: np.ndarray,
    att_positions: np.ndarray,
    att_strengths: np.ndarray,
    rep_positions: np.ndarray,
    rep_strengths: np.ndarray,
    lambda_social: float,
    eta: float,
    sigma2: float,
    min_val: float,
    max_val: float,
) -> np.ndarray:
    """JIT-compiled Langevin update step for all agents."""
    n = len(opinions)
    new_opinions = np.empty(n)
    for i in range(n):
        grad = _landscape_gradient_jit(
            opinions[i], att_positions, att_strengths,
            rep_positions, rep_strengths, sigma2,
        )
        social_drift    = lambda_social * (neighbor_mean[i] - opinions[i])
        landscape_drift = (1.0 - lambda_social) * (-grad)
        val = opinions[i] + eta * landscape_drift + eta * social_drift + noise[i]
        if val < min_val:
            val = min_val
        elif val > max_val:
            val = max_val
        new_opinions[i] = val
    return new_opinions


def _gaussian(x: float, position: float, sigma: float = _SIGMA) -> float:
    """Evalúa una gaussiana normalizada centrada en position."""
    diff = x - position
    return float(np.exp(-diff ** 2 / (2 * sigma ** 2)))


def _landscape_gradient(x: float, attractors: list, repellers: list) -> float:
    """
    Calcula ∇U(x) para el paisaje de atractores y repulsores.

    Potencial:
      U(x) = -Σ strength_a · G(x, pos_a)   (atractores: pozos de energía)
             +Σ strength_r · G(x, pos_r)   (repulsores: colinas de energía)

    Gradiente (derivada analítica):
      ∇U(x) = Σ strength_a · (x - pos_a) / σ² · G(x, pos_a)
             -Σ strength_r · (x - pos_r) / σ² · G(x, pos_r)
    """
    grad = 0.0
    sigma2 = _SIGMA ** 2

    for att in attractors:
        diff = x - att["position"]
        grad += att["strength"] * diff / sigma2 * _gaussian(x, att["position"])

    for rep in repellers:
        diff = x - rep["position"]
        grad -= rep["strength"] * diff / sigma2 * _gaussian(x, rep["position"])

    return grad


def _landscape_energy(x: float, attractors: list, repellers: list) -> float:
    """Calcula U(x) — energía potencial en el punto x."""
    energy = 0.0
    for att in attractors:
        energy -= att["strength"] * _gaussian(x, att["position"])
    for rep in repellers:
        energy += rep["strength"] * _gaussian(x, rep["position"])
    return energy


class SocialEnergyEngine:
    """
    Motor de dinámica de Langevin para simulación de redes sociales.

    Cada agente evoluciona bajo tres fuerzas simultáneas:
      1. Paisaje de energía  — atractores (consenso, facciones) y repulsores (moderación)
      2. Fuerza social       — influencia de vecinos en la red (media ponderada)
      3. Ruido térmico       — libre albedrío / incertidumbre individual

    Args:
        range_type:     'bipolar' → opiniones en [-1, 1] | 'unipolar' → [0, 1]
        temperature:    Intensidad del ruido estocástico (0.01–0.20)
        lambda_social:  Balance red↔paisaje. 0.0 = solo paisaje, 1.0 = solo red social
    """

    def __init__(
        self,
        range_type: str = "bipolar",
        temperature: float = 0.05,
        lambda_social: float = 0.5,
        scientific_config: dict | None = None,
        gini_coefficient: Optional[float] = None,
        inequality_factor: Optional[float] = None,
        economic_potential: Optional[Dict[str, Any]] = None,
        seed: Optional[int] = None,
        rng: Optional[np.random.Generator] = None,
    ):
        self.range_type = range_type
        self.temperature = float(temperature)
        self.lambda_social = float(lambda_social)
        self.min_val = -1.0 if range_type == "bipolar" else 0.0
        self.max_val = 1.0
        
        # Factbook economic parameters
        self.gini_coefficient = gini_coefficient if gini_coefficient is not None else 0.35
        self.inequality_factor = inequality_factor if inequality_factor is not None else 1.35
        self.economic_potential = economic_potential or {}
        
        # Ensure gini is in [0, 1] range
        self.gini_coefficient = max(0.0, min(1.0, self.gini_coefficient))
        
        # Update lambda_social based on inequality
        # Higher inequality = more weight on social network (less on landscape)
        if inequality_factor:
            # Adjust lambda to account for inequality
            inequality_adjustment = (inequality_factor - 1.0) * 0.1
            self.lambda_social = max(0.0, min(1.0, self.lambda_social + inequality_adjustment))
        
        from massive_core.config import ScientificRuntimeConfig
        from massive_core.numerics import create_stepper

        self.scientific_config = ScientificRuntimeConfig.from_dict(scientific_config)
        self._stepper = create_stepper(self.scientific_config.solver)
        self.last_numerical_diagnostics = None
        
        # Initialize RNG
        if rng is not None:
            self.rng = rng
        elif seed is not None:
            self.rng = np.random.default_rng(seed)
        else:
            self.rng = None

    def step(
        self,
        opinions: np.ndarray,
        adj: np.ndarray,
        attractors: list,
        repellers: list,
        eta: float = 0.01,
    ) -> np.ndarray:
        """
        Avanza un paso de integración de Langevin (Euler-Maruyama).

        Args:
            opinions:   Array (n,) con las opiniones actuales en [min_val, max_val].
            adj:        Matriz de adyacencia (n, n) — pesos de influencia entre agentes.
            attractors: Lista de dicts con 'position' y 'strength'.
            repellers:  Lista de dicts con 'position' y 'strength'.
            eta:        Tamaño del paso de integración (dt).

        Returns:
            Array (n,) con opiniones actualizadas, clippeadas al rango válido.
        """
        n = len(opinions)

        # ── Fuerza social: media ponderada de vecinos ─────────────────────────
        row_sums = adj.sum(axis=1)
        row_sums = np.where(row_sums == 0, 1.0, row_sums)
        neighbor_mean = (adj @ opinions) / row_sums

        # ── Ruido estocástico (una muestra por agente) ─────────────────────────
        rng = self.rng if self.rng is not None else np.random
        noise = np.sqrt(2.0 * eta * self.temperature) * rng.randn(n)

        # ── Extract arrays for JIT-compiled hot path ───────────────────────────
        sigma2 = _SIGMA ** 2
        if attractors:
            att_positions = np.array([a["position"] for a in attractors], dtype=np.float64)
            att_strengths = np.array([a["strength"] for a in attractors], dtype=np.float64)
        else:
            att_positions = np.empty(0, dtype=np.float64)
            att_strengths = np.empty(0, dtype=np.float64)

        if repellers:
            rep_positions = np.array([r["position"] for r in repellers], dtype=np.float64)
            rep_strengths = np.array([r["strength"] for r in repellers], dtype=np.float64)
        else:
            rep_positions = np.empty(0, dtype=np.float64)
            rep_strengths = np.empty(0, dtype=np.float64)

        if self._stepper is not None:
            def drift(current: np.ndarray) -> np.ndarray:
                local_neighbor_mean = (adj @ current) / row_sums
                local_drift = np.empty(n)
                for i in range(n):
                    grad = _landscape_gradient(current[i], attractors, repellers)
                    social_drift = self.lambda_social * (local_neighbor_mean[i] - current[i])
                    landscape_drift = (1.0 - self.lambda_social) * (-grad)
                    local_drift[i] = landscape_drift + social_drift
                return local_drift

            diffusion = np.sqrt(2.0 * self.temperature) if self.temperature > 0.0 else None
            rng = self.rng if self.rng is not None else np.random
            step_noise = rng.randn(n) if diffusion is not None else None
            result = self._stepper.step(
                opinions.astype(np.float64),
                eta,
                drift,
                diffusion=diffusion,
                noise=step_noise,
                bounds=(self.min_val, self.max_val),
            )
            self.last_numerical_diagnostics = result.diagnostics
            return result.state

        # ── Actualización de cada agente (JIT path or Python fallback) ─────────
        if NUMBA_AVAILABLE:
            new_opinions = _step_jit(
                opinions.astype(np.float64),
                neighbor_mean.astype(np.float64),
                noise.astype(np.float64),
                att_positions, att_strengths,
                rep_positions, rep_strengths,
                self.lambda_social, eta, sigma2,
                self.min_val, self.max_val,
            )
        else:
            new_opinions = np.empty(n)
            for i in range(n):
                grad = _landscape_gradient(opinions[i], attractors, repellers)
                social_drift = self.lambda_social * (neighbor_mean[i] - opinions[i])
                landscape_drift = (1.0 - self.lambda_social) * (-grad)
                new_opinions[i] = (
                    opinions[i]
                    + eta * landscape_drift
                    + eta * social_drift
                    + noise[i]
                )
            new_opinions = np.clip(new_opinions, self.min_val, self.max_val)

        return new_opinions

    def set_gini_coefficient(self, gini: float):
        """
        Set Gini coefficient from CIA World Factbook.
        
        Args:
            gini: Gini index normalized to [0, 1] range
        """
        self.gini_coefficient = max(0.0, min(1.0, float(gini)))
        log.info(f"[EnergyEngine] Gini coefficient set to: {self.gini_coefficient}")
    
    def set_inequality_factor(self, factor: float):
        """
        Set inequality amplification factor.
        
        Args:
            factor: Inequality factor > 1.0 (higher for more unequal societies)
        """
        self.inequality_factor = max(1.0, float(factor))
        # Adjust lambda_social based on inequality
        inequality_adjustment = (self.inequality_factor - 1.0) * 0.1
        self.lambda_social = max(0.0, min(1.0, self.lambda_social + inequality_adjustment))
        log.info(f"[EnergyEngine] Inequality factor set to: {self.inequality_factor}")
    
    def set_economic_potential(self, potential: Dict[str, Any]):
        """
        Set economic potential parameters from Factbook data.
        
        Args:
            potential: Dictionary with polarization_factor, income_scale, etc.
        """
        self.economic_potential = potential or {}
        log.info(f"[EnergyEngine] Economic potential parameters updated")
    
    def create_gini_adjusted_landscape(
        self,
        base_attractors: list,
        base_repellers: list,
    ) -> tuple:
        """
        Create energy landscape adjusted for economic inequality (Gini index).
        
        Higher Gini index creates:
        - Deeper attractors (stronger consensus points)
        - Higher repulsors (stronger polarization barriers)
        - More pronounced energy wells
        
        Args:
            base_attractors: Base attractor positions and strengths
            base_repellers: Base repeller positions and strengths
            
        Returns:
            Tuple of (adjusted_attractors, adjusted_repellers)
        """
        gini = self.gini_coefficient
        inequality = self.inequality_factor
        
        # Get polarization factor from economic potential if available
        polarization = self.economic_potential.get("polarization_factor", gini)
        income_scale = self.economic_potential.get("income_scale", 1.0)
        attractor_multiplier = self.economic_potential.get("attractor_strength", 1.35)
        repeller_multiplier = self.economic_potential.get("repeller_strength", 0.75)
        
        # Adjust attractors: higher inequality = stronger attractors
        adjusted_attractors = []
        for att in base_attractors:
            adjusted_attractors.append({
                "position": att["position"],
                "strength": att["strength"] * inequality * attractor_multiplier
            })
        
        # Adjust repulsors: higher inequality = stronger repulsors (more polarization)
        adjusted_repellers = []
        for rep in base_repellers:
            adjusted_repellers.append({
                "position": rep["position"],
                "strength": rep["strength"] * inequality * repeller_multiplier
            })
        
        return adjusted_attractors, adjusted_repellers
    
    def create_economic_landscape(
        self,
        mean_income: float = 20000.0,
        n_attractors: int = 3,
        n_repellers: int = 2,
    ) -> tuple:
        """
        Create economic energy landscape based on Factbook economic data.
        
        Creates a landscape where:
        - Attractors represent economic opportunities (wealth, jobs)
        - Repellers represent economic barriers (poverty, inequality)
        - Gini index determines the distribution shape
        
        Args:
            mean_income: Mean income level (affects landscape scale)
            n_attractors: Number of economic opportunity centers
            n_repellers: Number of economic barriers
            
        Returns:
            Tuple of (attractors, repellers) configured for economic simulation
        """
        gini = self.gini_coefficient
        
        # Calculate income-based scaling
        income_scale = np.log1p(mean_income) / 15.0
        
        # Create attractors (economic opportunities)
        # In more unequal societies, opportunities are more concentrated
        attractors = []
        for i in range(n_attractors):
            position = -0.5 + (i / max(n_attractors - 1, 1)) if n_attractors > 1 else 0.0
            # Higher Gini = more concentrated opportunities (higher strength, fewer positions)
            strength = 2.0 * income_scale * (1.0 + gini)
            attractors.append({"position": position, "strength": strength})
        
        # Create repulsors (economic barriers)
        repellers = []
        for i in range(n_repellers):
            position = -0.7 + (i / max(n_repellers - 1, 1)) * 1.4
            # Higher Gini = stronger barriers
            strength = 1.5 * income_scale * (1.0 + gini * 2.0)
            repellers.append({"position": position, "strength": strength})
        
        return attractors, repellers
    
    def system_metrics(
        self,
        opinions: np.ndarray,
        adj: np.ndarray,
        attractors: list,
        repellers: list,
    ) -> dict:
        """
        Calcula métricas sistémicas del estado actual de la red.

        Returns:
            Dict con mean_opinion, std_opinion, polarizacion, energia_total,
            energia_media, n_clusters_approx.
        """
        mean = float(np.mean(opinions))
        std = float(np.std(opinions))

        # Polarización: desviación estándar normalizada al semi-rango
        half_range = (self.max_val - self.min_val) / 2.0
        polarizacion = float(std / half_range) if half_range > 0 else 0.0

        # Energía total del sistema
        energies = [
            _landscape_energy(x, attractors, repellers) for x in opinions
        ]
        energia_total = float(np.sum(energies))
        energia_media = float(np.mean(energies))

        # Estimación de clusters por umbral de distancia
        sorted_op = np.sort(opinions)
        gaps = np.diff(sorted_op)
        n_clusters = int(np.sum(gaps > 0.2)) + 1 if len(gaps) > 0 else 1

        return {
            "mean_opinion": mean,
            "std_opinion": std,
            "polarizacion": polarizacion,
            "energia_total": energia_total,
            "energia_media": energia_media,
            "n_clusters_approx": n_clusters,
        }


def random_network(
    n_agents: int,
    connectivity: float = 0.3,
    seed: int = 42,
) -> np.ndarray:
    """
    Genera una matriz de adyacencia aleatoria simétrica para la red social.

    Args:
        n_agents:     Número de agentes (nodos).
        connectivity: Probabilidad de que exista un enlace entre cualquier par (0–1).
        seed:         Semilla para reproducibilidad.

    Returns:
        Matriz numpy (n_agents, n_agents) binaria simétrica, diagonal=0.
    """
    if n_agents < 2:
        raise ValueError("n_agents must be >= 2")

    rng = np.random.default_rng(seed)
    upper = rng.random((n_agents, n_agents))
    mask = (upper < connectivity).astype(float)

    # Simetrizar y eliminar auto-lazos
    adj = np.triu(mask, k=1)
    adj = adj + adj.T
    np.fill_diagonal(adj, 0.0)
    return adj
