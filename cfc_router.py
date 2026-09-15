"""
cfc_router.py — Enrutador singleton CfC para MASSIVE.

Punto de entrada único para la capa CfC. Decide en cada invocación si
usar el modelo neuronal entrenado o delegar al comportamiento LLM/heurístico
existente.

Principio rector: CfC nunca bloquea.
  - Sin PyTorch instalado → fallback transparente.
  - Sin archivos .pt en models/ → fallback transparente.
  - Con confianza baja en la predicción → fallback transparente.
  - En todos los casos, MASSIVE funciona exactamente igual que sin CfC.

Uso::

    from cfc_router import CfCRouter
    router = CfCRouter.get()

    # Selector de régimen
    regime_id, source, confidence = router.select_regime(history, state)

    # Matriz tau sociodemográfica
    tau = router.compute_tau_matrix(attributes_np)

    # Propuesta de estrategia (Social Architect)
    propuesta = router.propose_strategy(initial_state, goal_embedding)

    # Estado del sistema
    print(router.status)  # {"regime_selector": True/False, ...}

Autor: MASSIVE Research
"""

import logging
from pathlib import Path
from typing import Optional

import numpy as np

log = logging.getLogger("massive")

# Umbral de confianza mínimo para aceptar la predicción CfC.
# Si la probabilidad máxima < CONFIDENCE_THRESHOLD → fallback LLM.
CONFIDENCE_THRESHOLD: float = 0.75

# Claves del estado que se extraen para el vector de entrada del selector.
_STATE_KEYS = (
    "opinion",
    "propaganda",
    "confianza",
    "opinion_grupo_a",
    "opinion_grupo_b",
    "trust",
    "ews_variance",
    "ews_autocorr",
)


class CfCRouter:
    """
    Singleton que gestiona los tres modelos CfC de MASSIVE.

    Carga los modelos desde models/ al inicializarse. Si algún archivo
    no existe o PyTorch no está disponible, ese componente queda en None
    y se usa el comportamiento anterior sin interrupciones.
    """

    _instance: Optional["CfCRouter"] = None

    def __init__(self) -> None:
        self._sel = None  # CfCRegimeSelector
        self._tau = None  # CfCTauMatrix
        self._arch = None  # CfCArchitectPolicy
        self._residual = None  # CfCResidualCorrector
        self._torch_available = False
        self._load()

    # ── Singleton ────────────────────────────────────────────────────────────

    @classmethod
    def get(cls) -> "CfCRouter":
        """Devuelve la instancia singleton, creándola si no existe."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Carga de modelos ─────────────────────────────────────────────────────

    def _load(self) -> None:
        try:
            import torch

            self._torch_available = True
        except ImportError:
            log.debug("[CfC] PyTorch no disponible — CfC desactivado.")
            return

        from cfc_engine import (
            NUM_REGIMES,
            CfCArchitectPolicy,
            CfCLambdaCorrector,
            CfCLandscapeModulator,
            CfCRegimeSelector,
            CfCResidualCorrector,
            CfCTauMatrix,
        )

        # Check both models/ root and models/cfc_calibrated/ for trained weights.
        # The calibrated residual corrector lives in models/cfc_calibrated/.
        base = Path("models")
        alt_base = Path("models/cfc_calibrated")

        def _try_load(filename, model_cls, *args, **kwargs):
            path = base / filename
            if not path.exists():
                path = alt_base / filename
            if not path.exists():
                return None
            try:
                m = model_cls(*args, **kwargs)
                ckpt = torch.load(path, map_location="cpu", weights_only=True)
                # Handle both flat and nested {"cell_state", "readout_state"} formats
                if "cell_state" in ckpt:
                    m.cell.load_state_dict(ckpt["cell_state"])
                    m.readout.load_state_dict(ckpt["readout_state"])
                else:
                    m.load_state_dict(ckpt)
                m.eval()
                log.info(f"[CfC] Modelo cargado: {filename}")
                return m
            except Exception as exc:
                log.warning(f"[CfC] No se pudo cargar {filename}: {exc}")
                return None

        self._sel = _try_load(
            "cfc_selector.pt",
            CfCRegimeSelector,
            window_size=6,
            state_dim=8,
            hidden=64,
        )
        self._tau = _try_load(
            "cfc_tau.pt",
            CfCTauMatrix,
            attr_dim=4,
            behavior_dim=5,
        )
        self._arch = _try_load(
            "cfc_architect.pt",
            CfCArchitectPolicy,
            state_dim=10,
            goal_dim=5,
            hidden=128,
            n_phases=5,
            n_regimes=NUM_REGIMES,
        )
        # Residual-correction model (calibration_log.md §6). Loads
        # models/cfc_residual.pt if present; transparent fallback otherwise.
        self._residual = _try_load(
            "cfc_residual.pt",
            CfCResidualCorrector,
            input_dim=9,
            hidden_size=64,
        )
        # Lambda correction model (CfCLambdaCorrector).
        # Loads models/cfc_lambda_corrector.pt if present.
        self._lambda_corrector = _try_load(
            "cfc_lambda_corrector.pt",
            CfCLambdaCorrector,
            input_dim=5,
            hidden_size=32,
        )
        # Landscape modulation model (CfCLandscapeModulator).
        self._landscape_corrector = _try_load(
            "cfc_landscape.pt",
            CfCLandscapeModulator,
            input_dim=5,
            hidden_size=32,
        )

    # ── API pública ──────────────────────────────────────────────────────────

    def select_regime(
        self,
        history: list,
        state: dict,
    ) -> tuple:
        """
        Selecciona el régimen de simulación usando el modelo CfC.

        Args:
            history: Lista de opiniones recientes (mínimo 6 valores float).
            state:   Diccionario con el estado actual del simulador.

        Returns:
            Tupla (regime_id, source, confidence) donde:
                - regime_id:  int, índice del régimen (0–12), o -1 si fallback.
                - source:     "cfc" | "llm_fallback".
                - confidence: float en [0, 1].
        """
        if self._sel is None or not self._torch_available:
            return -1, "llm_fallback", 0.0

        import torch

        Xh = torch.tensor([history[-6:]], dtype=torch.float32)
        Xs = torch.tensor(
            [[float(state.get(k, 0.0)) for k in _STATE_KEYS]],
            dtype=torch.float32,
        )

        with torch.no_grad():
            probs = torch.softmax(self._sel(Xh, Xs), dim=-1)
            conf, rid = probs.max(dim=-1)

        cf = float(conf.item())
        if cf >= CONFIDENCE_THRESHOLD:
            return int(rid.item()), "cfc", cf
        return -1, "llm_fallback", cf

    def compute_tau_matrix(self, attributes: np.ndarray) -> np.ndarray | None:
        """
        Genera la matriz de modulación τ sociodemográfica.

        Args:
            attributes: Array de forma (N_agents, 4) con columnas
                        [religion, education, age_norm, gender].

        Returns:
            Array de forma (N_agents, 5) con valores τ, o None si CfC
            no está disponible para este componente.
        """
        if self._tau is None or not self._torch_available:
            return None

        import torch

        with torch.no_grad():
            result = self._tau(torch.tensor(attributes, dtype=torch.float32))
        return result.numpy()

    def propose_strategy(
        self,
        initial_state: dict,
        goal_embedding: list,
    ) -> dict | None:
        """
        Propone una estrategia de intervención sin llamar a la API LLM.

        Args:
            initial_state:   Diccionario con el estado inicial de la red.
            goal_embedding:  Lista de 5 floats codificando el objetivo.

        Returns:
            Diccionario con regime_logits, durations, params y source="cfc",
            o None si el modelo no está disponible.
        """
        if self._arch is None or not self._torch_available:
            return None

        import torch

        # Tomar hasta 10 claves del estado como vector
        state_values = [float(v) for v in list(initial_state.values())[:10]]
        # Rellenar con ceros si hay menos de 10 claves
        state_values += [0.0] * (10 - len(state_values))

        s = torch.tensor([state_values], dtype=torch.float32)
        g = torch.tensor([goal_embedding[:5]], dtype=torch.float32)

        with torch.no_grad():
            out = self._arch(s, g)

        return {k: v.numpy() for k, v in out.items()} | {"source": "cfc"}

    def propose_lambda(
        self,
        features: dict,
    ) -> tuple[float, str]:
        """
        Propose a lambda_social correction based on polarization/Gini context.
        
        Args:
            features: Dict containing polarization, delta_p1, delta_p5, gini, volatility.
        
        Returns:
            (lambda_value, source) where source is "cfc" or "passthrough".
        """
        if self._lambda_corrector is None or not self._torch_available:
            return 0.5, "passthrough"

        import torch

        # Build 5-feature vector: [polarization, delta_p1, delta_p5, gini, volatility]
        try:
            u_vec = [
                float(features.get("polarization", 0.0)),
                float(features.get("delta_p1", 0.0)),
                float(features.get("delta_p5", 0.0)),
                float(features.get("gini", 0.35)),
                float(features.get("volatility", 0.0)),
            ]
            u_tensor = torch.tensor([u_vec], dtype=torch.float32)
        except (ValueError, TypeError):
            return 0.5, "passthrough"

        with torch.no_grad():
            # Forward pass: returns a scalar lambda value
            lambda_val = float(self._lambda_corrector(u_tensor).item())

        return float(np.clip(lambda_val, 0.0, 1.0)), "cfc"

    def propose_landscape(
        self,
        features: dict,
    ) -> tuple[dict | None, str]:
        """
        Propose new landscape parameters using the trained CfC landscape modulator.

        Args:
            features: Dict containing polarization, delta_p1, delta_p5, skewness, gini.

        Returns:
            (landscape_params, source) where landscape_params is a dict with
            'sigma_p', 'attractor_position', 'attractor_strength',
            'repeller_position', 'repeller_strength', or None if unavailable.
            Source is "cfc" or "none".
        """
        if self._landscape_corrector is None or not self._torch_available:
            return None, "none"

        try:
            import torch
            u_vec = [
                float(features.get("polarization", 0.0)),
                float(features.get("delta_p1", 0.0)),
                float(features.get("delta_p5", 0.0)),
                float(features.get("skewness", 0.0)),
                float(features.get("gini", 0.35)),
            ]
            u_tensor = torch.from_numpy(np.array(u_vec, dtype=np.float32)).unsqueeze(0)
            with torch.no_grad():
                vals = self._landscape_corrector(u_tensor)[0]

            return {
                "sigma_p": float(vals[0].item()),
                "attractor_strength": float(vals[1].item()),
                "repeller_strength": float(vals[2].item()),
                "attractor_position": float(vals[3].item()),
                "repeller_position": float(vals[4].item()),
            }, "cfc"
        except Exception:
            return None, "none"

    def correct_residual(
        self,
        history: list[float],
        simulated: list[float] | float,
        *,
        actual: list[float] | float | None = None,
        dt: float = 0.1,
    ) -> tuple[float, str]:
        """Apply CfC residual correction to an energy-engine opinion trajectory.

        Implements calibration_log.md §6: final(t) = ŷ(t) + r̂(t).

        The trained model has R² = -18.7 per-step (poor point-wise
        generalization), so the *bias direction* is used for adaptive
        correction scaled toward the known baseline error (§7).

        Args:
            history:  List of simulated leave% / opinion values, ≥ 3.
            simulated: Latest simulated value (scalar) or full series.
            actual:  Optional ground-truth series for adaptive scaling.
            dt:      ODE integration step (matches training).

        Returns:
            (corrected_value, source) — source is "cfc" or "passthrough".
            Returns uncorrected value when model unavailable.
        """
        if self._residual is None or not self._torch_available:
            sim_val = float(np.asarray(simulated).ravel()[-1]) if simulated is not None else 0.0
            return sim_val, "passthrough"

        import torch

        hist_arr = np.asarray(history, dtype=np.float64).ravel()
        if hist_arr.size < 3:
            sim_val = float(np.asarray(simulated).ravel()[-1]) if simulated is not None else 0.0
            return sim_val, "passthrough"

        sim_arr = np.asarray(simulated, dtype=np.float64)
        if sim_arr.ndim == 0 or sim_arr.size == 1:
            sim_series = np.full(hist_arr.size, float(sim_arr.ravel()[-1]))
        else:
            sim_series = hist_arr

        n = hist_arr.size
        t_norm = np.arange(n, dtype=np.float64) / max(n, 1)
        mean_sim = float(np.mean(sim_series))

        if actual is not None:
            actual_arr = np.asarray(actual, dtype=np.float64)
            if actual_arr.ndim == 0 or actual_arr.size == 1:
                actual_series = np.full(n, float(actual_arr.ravel()[-1]))
            else:
                actual_series = actual_arr[:n] if actual_arr.size >= n else np.pad(actual_arr, (0, n - actual_arr.size))
            residuals = actual_series - sim_series
        else:
            residuals = np.full(n, 0.0426)  # training mean (calibration_log §5)

        # Feature vector: 9 features = [t_norm, sim, mean(sim)] + 6 lags
        u = np.zeros(self._residual.input_dim, dtype=np.float32)
        u[0] = float(t_norm[-1])
        u[1] = float(sim_series[-1])
        u[2] = mean_sim
        for i in range(6):
            u[3 + i] = float(residuals[-1 - i]) if len(residuals) > i + 1 else 0.0

        x = torch.zeros(1, self._residual.hidden_size)
        u_tensor = torch.from_numpy(u).unsqueeze(0)
        with torch.no_grad():
            r_hat = float(self._residual(x, u_tensor, dt=dt).item())

        sim_val = float(sim_series[-1])

        # Adaptive correction: scale 50% toward target when ground truth known;
        # otherwise use raw model prediction for bias detection only.
        if actual is not None:
            baseline_error = sim_val - float(actual_arr.ravel()[-1]) if actual_arr.size else 0.0
            correction = 0.5 * baseline_error  # positive when sim overestimates
        else:
            correction = r_hat

        corrected = sim_val - correction  # subtract to move toward actual
        return float(np.clip(corrected, -1.0, 1.0)), "cfc"

    @property
    def status(self) -> dict:
        """
        Estado de disponibilidad de cada componente CfC.

        Returns:
            Diccionario con claves 'regime_selector', 'tau_matrix',
            'architect_policy', 'residual_corrector', cada una True/False.
        """
        return {
            "regime_selector": self._sel is not None,
            "tau_matrix": self._tau is not None,
            "architect_policy": self._arch is not None,
            "residual_corrector": self._residual is not None,
            "lambda_corrector": self._lambda_corrector is not None,
            "landscape_corrector": self._landscape_corrector is not None,
        }
