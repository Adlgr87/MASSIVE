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
        self._sel = None    # CfCRegimeSelector
        self._tau = None    # CfCTauMatrix
        self._arch = None   # CfCArchitectPolicy
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

        from cfc_engine import CfCRegimeSelector, CfCTauMatrix, CfCArchitectPolicy

        base = Path("models")

        def _try_load(filename, model_cls, *args, **kwargs):
            path = base / filename
            if not path.exists():
                return None
            try:
                m = model_cls(*args, **kwargs)
                m.load_state_dict(
                    torch.load(path, map_location="cpu", weights_only=True)
                )
                m.eval()
                log.info(f"[CfC] Modelo cargado: {filename}")
                return m
            except Exception as exc:
                log.warning(f"[CfC] No se pudo cargar {filename}: {exc}")
                return None

        self._sel = _try_load(
            "cfc_selector.pt", CfCRegimeSelector,
            window_size=6, state_dim=8, hidden=64,
        )
        self._tau = _try_load(
            "cfc_tau.pt", CfCTauMatrix,
            attr_dim=4, behavior_dim=5,
        )
        self._arch = _try_load(
            "cfc_architect.pt", CfCArchitectPolicy,
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

    def compute_tau_matrix(self, attributes: np.ndarray) -> Optional[np.ndarray]:
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
            result = self._tau(
                torch.tensor(attributes, dtype=torch.float32)
            )
        return result.numpy()

    def propose_strategy(
        self,
        initial_state: dict,
        goal_embedding: list,
    ) -> Optional[dict]:
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

    @property
    def status(self) -> dict:
        """
        Estado de disponibilidad de cada componente CfC.

        Returns:
            Diccionario con claves 'regime_selector', 'tau_matrix',
            'architect_policy', cada una True/False.
        """
        return {
            "regime_selector": self._sel is not None,
            "tau_matrix": self._tau is not None,
            "architect_policy": self._arch is not None,
        }
