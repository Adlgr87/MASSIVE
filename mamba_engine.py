"""
mamba_engine.py — Selective State Space Model (Mamba/SSM) para MASSIVE.

Implementación pura PyTorch de un SSM discreto selectivo, complementario
al motor CfC (cfc_engine.py). No requiere la extensión C++ ``mamba-ssm``.

Diferencia clave respecto a CfC:
  - CfC modela la dinámica como una ODE continua con τ aprendido.
  - Mamba usa matrices de espacio de estados (A, B, C, D) con selectividad
    dependiente de la entrada (Δ es función de u), permitiendo capturar
    dependencias de largo plazo con complejidad lineal en la secuencia.

Ecuación SSM discreta (discretización ZOH):
    ̄A = exp(Δ · A)
    ̄B = (̄A − I) A⁻¹ B   ≈ Δ · B  (para A diagonal)
    h_t = ̄A · h_{t-1} + ̄B · u_t
    y_t = C · h_t + D · u_t

Modelos:
    MambaCell       — celda SSM selectiva (un paso)
    MambaSSM        — red SSM sobre secuencia completa (L pasos)
    MambaBaseline   — wrapper ``predict(train, horizon)`` para benchmarks PVU-BS

Uso en benchmarks::

    from mamba_engine import MambaBaseline
    baseline = MambaBaseline(d_model=8, d_state=16)
    forecast = baseline.predict(train_series, horizon=10)

Autor: MASSIVE Research
"""

import torch
import torch.nn as nn
import numpy as np

# Dimensión del estado oculto por defecto
_DEFAULT_D_STATE: int = 16
_DEFAULT_D_MODEL: int = 8


class MambaCell(nn.Module):
    """
    Celda SSM selectiva: un paso de la recurrencia discreta.

    La selectividad viene de que Δ (paso de discretización) depende
    de la entrada u, lo que permite al modelo "enfocarse" en tokens relevantes.

    Args:
        d_model: Dimensión de la entrada u.
        d_state: Dimensión del estado oculto h.
    """

    def __init__(self, d_model: int = _DEFAULT_D_MODEL, d_state: int = _DEFAULT_D_STATE) -> None:
        super().__init__()
        self.d_model = d_model
        self.d_state = d_state

        # Matriz A: inicialización HiPPO-like (diagonal negativa → estabilidad)
        # A es diagonal → representada como vector para eficiencia
        A_init = -torch.arange(1, d_state + 1, dtype=torch.float32)
        self.A_log = nn.Parameter(torch.log(-A_init))  # log(-A), A < 0

        # B y C: proyecciones lineales dependientes de la entrada
        self.B_proj = nn.Linear(d_model, d_state, bias=False)
        self.C_proj = nn.Linear(d_model, d_state, bias=False)

        # Δ: paso de discretización selectivo (función de la entrada)
        self.delta_proj = nn.Sequential(
            nn.Linear(d_model, d_state),
            nn.Softplus(),  # Δ siempre positivo
        )

        # D: skip connection (salida directa de la entrada)
        self.D = nn.Parameter(torch.ones(d_model))

        # Proyección de salida: estado → espacio del modelo
        self.out_proj = nn.Linear(d_state, d_model, bias=False)

    def forward(
        self,
        h: torch.Tensor,
        u: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Avanza un paso SSM.

        Args:
            h: Estado oculto actual, forma (batch, d_state).
            u: Vector de entrada, forma (batch, d_model).

        Returns:
            Tupla (y, h_new) donde:
                - y:     Salida del modelo, forma (batch, d_model).
                - h_new: Nuevo estado oculto, forma (batch, d_state).
        """
        # A diagonal (negativa por construcción)
        A = -torch.exp(self.A_log)                  # (d_state,)

        # B y C selectivos (dependen de la entrada)
        B = self.B_proj(u)                           # (batch, d_state)
        C = self.C_proj(u)                           # (batch, d_state)

        # Δ selectivo: tamaño de paso depende de la entrada
        delta = self.delta_proj(u)                   # (batch, d_state)

        # Discretización ZOH (aproximación para A diagonal):
        # Ā = exp(Δ ⊙ A), B̄ ≈ Δ ⊙ B
        A_bar = torch.exp(delta * A.unsqueeze(0))    # (batch, d_state)
        B_bar = delta * B                            # (batch, d_state)

        # Recurrencia: h_new = Ā ⊙ h + B̄ ⊙ u_projected
        h_new = A_bar * h + B_bar                   # (batch, d_state)

        # Salida: y = C · h_new + D ⊙ u
        y = self.out_proj(C * h_new) + self.D * u   # (batch, d_model)

        return y, h_new


class MambaSSM(nn.Module):
    """
    Red SSM selectiva sobre una secuencia completa de L pasos.

    Aplica MambaCell recurrentemente sobre cada elemento de la secuencia
    y devuelve la salida del último paso (útil para predicción).

    Args:
        d_model: Dimensión de la entrada por paso.
        d_state: Dimensión del estado oculto.
        n_layers: Número de capas SSM apiladas.
    """

    def __init__(
        self,
        d_model: int = _DEFAULT_D_MODEL,
        d_state: int = _DEFAULT_D_STATE,
        n_layers: int = 2,
    ) -> None:
        super().__init__()
        self.d_model = d_model
        self.d_state = d_state
        self.cells = nn.ModuleList(
            [MambaCell(d_model, d_state) for _ in range(n_layers)]
        )
        self.norm = nn.LayerNorm(d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Procesa una secuencia y devuelve la representación del último paso.

        Args:
            x: Secuencia de entrada, forma (batch, seq_len, d_model).

        Returns:
            Representación del último paso, forma (batch, d_model).
        """
        batch = x.shape[0]
        out = x
        for cell in self.cells:
            h = torch.zeros(batch, self.d_state, device=x.device, dtype=x.dtype)
            step_outs = []
            for t in range(out.shape[1]):
                y, h = cell(h, out[:, t, :])
                step_outs.append(y.unsqueeze(1))
            out = self.norm(torch.cat(step_outs, dim=1))
        return out[:, -1, :]  # último paso


class MambaBaseline:
    """
    Baseline de predicción SSM para el protocolo PVU-BS de MASSIVE.

    Sigue la misma interfaz ``predict(train, horizon)`` que los baselines
    existentes (``AR1Baseline``, ``ETSBaseline``, etc.) para ser evaluado
    automáticamente bajo el protocolo Diebold-Mariano + Holm-Bonferroni.

    Arquitectura: MambaSSM de 1 capa entrenado online por serie (fit-per-series).
    Limitación conocida: en series cortas (< 20 puntos) la ventaja de SSM sobre
    AR1/ETS es marginal — el test Holm-Bonferroni lo reflejará. Para mayor
    impacto, considerar pretraining cruzado sobre los 20 casos PVU.

    Args:
        d_model:  Dimensión del embedding interno (default: 8).
        d_state:  Dimensión del estado oculto SSM (default: 16).
        n_layers: Número de capas SSM apiladas (default: 1).
        lags:     Ventana de pasos de entrada por muestra (default: 4).
        epochs:   Épocas de entrenamiento online por serie (default: 30).
        lr:       Tasa de aprendizaje Adam (default: 1e-3).
    """

    name = "mamba_ssm"

    def __init__(
        self,
        d_model: int = _DEFAULT_D_MODEL,
        d_state: int = _DEFAULT_D_STATE,
        n_layers: int = 1,
        lags: int = 4,
        epochs: int = 30,
        lr: float = 1e-3,
    ) -> None:
        import torch  # verificación de disponibilidad en construcción
        self.d_model = d_model
        self.d_state = d_state
        self.n_layers = n_layers
        self.lags = lags
        self.epochs = epochs
        self.lr = lr
        self._model: MambaSSM | None = None
        self._head: nn.Linear | None = None

    def _build_model(self) -> tuple[MambaSSM, nn.Linear]:
        model = MambaSSM(self.d_model, self.d_state, self.n_layers)
        head = nn.Linear(self.d_model, 1)
        return model, head

    def _make_windows(self, series: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Construye ventanas deslizantes (X, y) para entrenamiento."""
        X, y = [], []
        for i in range(self.lags, len(series)):
            X.append(series[i - self.lags: i])
            y.append(series[i])
        return np.asarray(X, dtype=np.float32), np.asarray(y, dtype=np.float32)

    def fit(self, train: np.ndarray) -> "MambaBaseline":
        """
        Ajusta el modelo SSM sobre la serie de entrenamiento.

        Args:
            train: Serie temporal 1-D de entrenamiento.

        Returns:
            self (para encadenamiento).
        """
        import torch
        from torch import nn

        if len(train) <= self.lags + 1:
            self._model = None
            return self

        series = np.asarray(train, dtype=np.float32)

        # Normalización min-max para estabilidad numérica
        lo, hi = series.min(), series.max()
        scale = max(hi - lo, 1e-6)
        series_norm = (series - lo) / scale

        X_np, y_np = self._make_windows(series_norm)
        if len(X_np) == 0:
            self._model = None
            return self

        # (N, lags) → (N, lags, 1) → (N, lags, d_model) via repeat
        X_t = torch.tensor(X_np).unsqueeze(-1).expand(-1, -1, self.d_model)
        y_t = torch.tensor(y_np).unsqueeze(-1)

        model, head = self._build_model()
        optimizer = torch.optim.Adam(
            list(model.parameters()) + list(head.parameters()), lr=self.lr
        )
        loss_fn = nn.MSELoss()

        model.train()
        head.train()
        for _ in range(self.epochs):
            pred = head(model(X_t))
            loss = loss_fn(pred, y_t)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

        model.eval()
        head.eval()
        self._model = model
        self._head = head
        self._lo = float(lo)
        self._scale = float(scale)
        return self

    def predict(self, train: np.ndarray, horizon: int) -> np.ndarray:
        """
        Genera un pronóstico de ``horizon`` pasos.

        Si PyTorch no está disponible o la serie es demasiado corta para
        ajustar el modelo, hace fallback a AR(1).

        Args:
            train:   Serie temporal 1-D de entrenamiento.
            horizon: Número de pasos a pronosticar.

        Returns:
            Array 1-D de ``horizon`` valores pronosticados.
        """
        try:
            import torch
        except ImportError:
            # Fallback a AR(1) si PyTorch no está disponible
            from benchmarks.baselines import AR1Baseline
            return AR1Baseline().predict(train, horizon)

        self.fit(train)
        if self._model is None:
            # Serie demasiado corta — persiste último valor
            return np.full(horizon, float(train[-1]))

        series = np.asarray(train, dtype=np.float32)
        series_norm = (series - self._lo) / self._scale

        hist = list(series_norm[-self.lags:])
        preds_norm = []

        self._model.eval()
        self._head.eval()
        with torch.no_grad():
            for _ in range(horizon):
                window = np.asarray(hist[-self.lags:], dtype=np.float32)
                x_t = torch.tensor(window).unsqueeze(0).unsqueeze(-1)
                x_t = x_t.expand(-1, -1, self.d_model)
                y_hat = float(self._head(self._model(x_t)).squeeze())
                preds_norm.append(y_hat)
                hist.append(y_hat)

        # Desnormalizar
        preds = np.asarray(preds_norm) * self._scale + self._lo
        return np.clip(preds, 0.0, 1.0)
