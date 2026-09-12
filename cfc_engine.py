"""
cfc_engine.py — Closed-form Continuous-time (CfC) neural network architectures.

Arquitectura CfC pura. Sin dependencias de MASSIVE.
Usada por cfc_router.py y entrenada por cfc_trainer.py.

Ecuación ODE subyacente:
    dx/dt = Ax + Bu + C·tanh(Wx·x + Wu·u),  A = -I/τ
donde τ es aprendido dinámicamente a partir del estado y la entrada.

Modelos:
    CfCCell            — celda ODE base (un paso Euler)
    CfCRegimeSelector  — selecciona uno de los 13 regímenes del simulador
    CfCTauMatrix       — genera la matriz θ sociodemográfica del motor multicapa
    CfCArchitectPolicy — propone una estrategia de intervención sin llamada LLM

Autor: MASSIVE Research
"""

import numpy as np
import torch
import torch.nn as nn

# Número de regímenes (reglas 0–12 definidas en simulator.py → NOMBRES_REGLAS)
NUM_REGIMES: int = 13


class CfCCell(nn.Module):
    """
    Celda CfC: un paso de Euler sobre la ODE continua.

    ODE: dx/dt = -x/τ + B(u) + C · tanh(Wx(x) + Wu(u))

    Args:
        input_size: Dimensión del vector de entrada u.
        hidden_size: Dimensión del estado oculto x.
    """

    def __init__(self, input_size: int, hidden_size: int) -> None:
        super().__init__()
        self.hidden_size = hidden_size
        self.W_x = nn.Linear(hidden_size, hidden_size, bias=False)
        self.W_u = nn.Linear(input_size, hidden_size, bias=False)
        self.B = nn.Linear(input_size, hidden_size, bias=False)
        self.C = nn.Parameter(torch.ones(hidden_size))
        self.tau_net = nn.Sequential(
            nn.Linear(input_size + hidden_size, hidden_size),
            nn.Softplus(),  # τ siempre positivo
        )

    def forward(
        self,
        x: torch.Tensor,
        u: torch.Tensor,
        dt: float = 0.1,
    ) -> torch.Tensor:
        """
        Avanza un paso Euler de la ODE CfC.

        Args:
            x: Estado oculto actual, forma (batch, hidden_size).
            u: Vector de entrada, forma (batch, input_size).
            dt: Tamaño del paso de integración.

        Returns:
            Nuevo estado oculto, forma (batch, hidden_size).
        """
        tau = self.tau_net(torch.cat([x, u], dim=-1)) + 1e-3
        dx = (-1.0 / tau) * x + self.B(u) + self.C * torch.tanh(self.W_x(x) + self.W_u(u))
        return x + dt * dx


class CfCRegimeSelector(nn.Module):
    """
    Selector de régimen CfC: reemplaza la llamada LLM en el hot path del simulador.

    Toma una ventana de historial de opinión y un vector de estado actual,
    y devuelve logits sobre los 13 regímenes disponibles.

    Args:
        window_size: Pasos de historial de opinión a considerar.
        state_dim: Dimensión del vector de estado adicional.
        hidden: Tamaño del estado oculto de la celda CfC.
    """

    def __init__(
        self,
        window_size: int = 6,
        state_dim: int = 8,
        hidden: int = 64,
    ) -> None:
        super().__init__()
        self.cell = CfCCell(window_size + state_dim, hidden)
        self.head = nn.Linear(hidden, NUM_REGIMES)

    def forward(
        self,
        history: torch.Tensor,
        state: torch.Tensor,
    ) -> torch.Tensor:
        """
        Args:
            history: Ventana de opiniones recientes, forma (batch, window_size).
            state:   Vector de estado, forma (batch, state_dim).

        Returns:
            Logits por régimen, forma (batch, NUM_REGIMES).
        """
        u = torch.cat([history, state], dim=-1)
        h = torch.zeros(u.shape[0], self.cell.hidden_size, device=u.device)
        h = self.cell(h, u)
        return self.head(h)


class CfCTauMatrix(nn.Module):
    """
    Generador de matriz τ sociodemográfica para el motor multicapa.

    Reemplaza la matriz theta fija (_THETA_*) en multilayer_engine.py.
    Aprende cómo los atributos demográficos modulan la escala de ruido
    por dimensión de comportamiento.

    Args:
        attr_dim: Dimensión del vector de atributos por agente
                  (religion, education, age_norm, gender → 4).
        behavior_dim: Número de dimensiones de comportamiento
                      (K=5 en multilayer_engine).
    """

    def __init__(self, attr_dim: int = 4, behavior_dim: int = 5) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(attr_dim, 32),
            nn.Tanh(),
            nn.Linear(32, behavior_dim),
            nn.Softplus(),
        )

    def forward(self, attributes: torch.Tensor) -> torch.Tensor:
        """
        Args:
            attributes: Matriz de atributos, forma (N_agents, attr_dim).

        Returns:
            Matriz τ de modulación, forma (N_agents, behavior_dim).
            Mínimo garantizado de 0.1 por construcción.
        """
        return self.net(attributes) + 0.1


class CfCResidualCorrector(nn.Module):
    """
    Closed-form Continuous-time residual-correction cell.

    Trained to predict the residual ``r(t) = actual_leave - simulated_leave``
    so that the corrected energy-engine output is ``final(t) = ŷ(t) + r̂(t)``.
    (calibration_log.md §4 — CfCResidualCorrector-N9H64)

    Input layout (9 features):
      [time_normalized, actual_leave_pct, simulated_leave_pct,
       residual_t-6, residual_t-5, residual_t-4, residual_t-3,
       residual_t-2, residual_t-1]

    The hidden state is a CfC cell with dynamic τ; a readout head projects
    the final hidden state to a scalar residual estimate.

    Note:
        The trained model has R² = -18.7 per-step (poor point-wise
        generalization) but its *bias direction* is reliable — calibration
        uses the mean prediction for adaptive bias correction
        (see ``calibration_log.md §7``).
    """

    def __init__(
        self,
        input_dim: int = 9,
        hidden_size: int = 64,
        eps: float = 1e-3,
    ) -> None:
        super().__init__()
        self.input_dim = input_dim
        self.hidden_size = hidden_size
        self.u_encoder = nn.Sequential(
            nn.Linear(input_dim, hidden_size),
            nn.Tanh(),
        )
        # tau_net / f_net share the concatenated (hidden + input) context (73 = 64 + 9)
        self.tau_net = nn.Sequential(
            nn.Linear(hidden_size + input_dim, hidden_size),
            nn.Softplus(),
        )
        self.f_net = nn.Sequential(
            nn.Linear(hidden_size + input_dim, hidden_size),
            nn.Tanh(),
        )
        self.readout = nn.Linear(hidden_size, 1)
        self._eps = eps

    def forward(
        self,
        x: torch.Tensor,
        u: torch.Tensor,
        dt: float = 0.1,
    ) -> torch.Tensor:
        """One Euler step of the residual ODE, returning new hidden state.

        Args:
            x: Hidden state (batch, hidden_size).
            u: Input features (batch, input_dim).
            dt: Integration step (matches training config).

        Returns:
            Predicted residual r̂(t) (batch, 1).
        """
        _ = self.u_encoder(u)                                 # (batch, hidden) — encoder path
        tau = self.tau_net(torch.cat([x, u], dim=-1)) + self._eps
        f = self.f_net(torch.cat([x, u], dim=-1))
        dx = (-1.0 / tau) * x + f
        x_new = x + dt * dx
        return self.readout(x_new)


class CfCArchitectPolicy(nn.Module):
    """
    Política de arquitecto social: propone una estrategia de intervención
    sin llamar a la API LLM.

    Primer intento (Intento 0) del Social Architect, antes de entrar al
    bucle LLM. Si la puntuación ≥ 90, el LLM no se invoca en absoluto.

    Args:
        state_dim:  Dimensión del vector de estado inicial (máx. 10 claves).
        goal_dim:   Dimensión del embedding de objetivo (5 floats codificados).
        hidden:     Tamaño del estado oculto de la celda CfC.
        n_phases:   Número de fases de intervención a proponer.
        n_regimes:  Número de regímenes disponibles (13 por defecto).
    """

    def __init__(
        self,
        state_dim: int = 10,
        goal_dim: int = 5,
        hidden: int = 128,
        n_phases: int = 5,
        n_regimes: int = NUM_REGIMES,
    ) -> None:
        super().__init__()
        self.n_phases = n_phases
        self.cell = CfCCell(state_dim + goal_dim, hidden)
        self.regime_h = nn.Linear(hidden, n_regimes)
        self.duration_h = nn.Linear(hidden, n_phases)
        self.param_h = nn.Linear(hidden, n_phases * 4)

    def forward(
        self,
        initial_state: torch.Tensor,
        goal: torch.Tensor,
    ) -> dict:
        """
        Args:
            initial_state: Estado inicial, forma (batch, state_dim).
            goal:          Embedding del objetivo, forma (batch, goal_dim).

        Returns:
            Diccionario con:
                - regime_logits: (batch, n_regimes)
                - durations:     (batch, n_phases) — softmax, suman 1
                - params:        (batch, n_phases, 4) — parámetros continuos
        """
        u = torch.cat([initial_state, goal], dim=-1)
        h = torch.zeros(u.shape[0], self.cell.hidden_size, device=u.device)
        h = self.cell(h, u)
        return {
            "regime_logits": self.regime_h(h),
            "durations": torch.softmax(self.duration_h(h), dim=-1),
            "params": self.param_h(h).view(-1, self.n_phases, 4),
        }


def select_regime(features, history):
    """Pick regime from {stable, oscillatory, critical, collapse}."""
    energy = np.dot(features.ravel(), features.ravel()) / features.size
    if energy < 0.1:
        return "stable"
    elif energy < 0.5:
        return "oscillatory"
    elif energy < 1.0:
        return "critical"
    else:
        return "collapse"
