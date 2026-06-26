"""
multilayer_engine.py — Motor Multicapa Sociodemográfico para MASSIVE

Extiende la dinámica 1D de opiniones a un vector de estado multidimensional
con capas de red diferenciadas (social, digital, económica) y atributos
sociodemográficos fijos por agente.

Ecuación de Langevin multicapa para cada agente i:
    dx_i/dt = -∇U(x_i) + Σ_ℓ w_ℓ · (A_ℓ · G(x))_i + θ(a_i) · η_i

Donde:
  - x_i ∈ ℝ^K          : vector de estado (K comportamientos por agente)
  - A_ℓ ∈ ℝ^{N×N}      : matriz de adyacencia de la capa ℓ
  - w_ℓ                 : peso de la capa ℓ (personalizable)
  - ∇U(x)               : gradiente del potencial multidimensional
  - θ(a_i)              : modulación por atributos sociodemográficos

Columnas de x_i (K=5):
  0: opinion      — posición de opinión principal [-1, 1]
  1: cooperation  — c_i, tendencia a cooperar [0, 1]
  2: hierarchy    — h_i, reconocimiento de autoridad [0, 1]
  3: income       — y_i, nivel de ingreso normalizado [0, 1]
  4: info_access  — φ_i, acceso a información [0, 1]

Autor: MASSIVE Research
"""

import numpy as np
import pandas as pd
import networkx as nx
from llm_credentials import resolve_provider_api_key
from quantum.integration import compress_agent_states, decompress_agent_states

try:
    from numba import njit
    NUMBA_AVAILABLE = True
except ImportError:
    NUMBA_AVAILABLE = False
    def njit(*args, **kwargs):
        """No-op decorator when Numba is not installed."""
        def decorator(fn):
            return fn
        if args and callable(args[0]):
            return args[0]
        return decorator


# ── Coeficientes de modulación theta (calibrados empíricamente) ───────────
# Escalas de sensibilidad por atributo y dimensión de comportamiento.
# Valores derivados de literatura de psicología social y sociología:
#   - Religión/opinión (0.5): Altemeyer (1988), efectos de autoritarismo religioso
#   - Educación/cooperación (0.3): Putnam (2000), capital social y educación
#   - Edad/jerarquía (0.4): Alwin & Krosnick (1991), estabilidad actitudinal
#   - Juventud/ingreso (0.2): volatilidad laboral diferencial por cohorte
#   - Educación/info (0.4): van Dijk (2005), brecha digital y capital educativo
_THETA_RELIGION_OPINION:  float = 0.5
_THETA_EDUCATION_COOP:    float = 0.3
_THETA_AGE_HIERARCHY:     float = 0.4
_THETA_YOUTH_INCOME:      float = 0.2
_THETA_EDUCATION_INFO:    float = 0.4

# Número de hubs en la red jerárquica: ~10% del total.
# Una proporción de hubs del 10% equilibra conectividad y jerarquía realista;
# redes corporativas empíricas suelen tener 5-15% de nodos de alta centralidad
# (Watts & Strogatz, 1998; Barabási & Albert, 1999).
_HIERARCHY_HUB_FRACTION: float = 0.10

# Coeficiente de intensidad estocástica (ruido theta-modulado).
# Escala el término de difusión en la integración Euler-Maruyama.
# El valor 0.1 produce fluctuaciones comparables al gradiente del potencial
# a temperatura social moderada; análogo a kT/U en física estadística.
_STOCHASTIC_SCALE: float = 0.1

# ── Dimensiones del vector de estado ────────────────────────────────────────
K = 5  # [opinion, cooperation, hierarchy, income, info_access]
MPS_COMPRESSION_MIN_AGENTS = 1000

# ── Índices de columnas para claridad ────────────────────────────────────────
COL_OPINION = 0
COL_COOP    = 1
COL_HIER    = 2
COL_INCOME  = 3
COL_INFO    = 4


# ============================================================
# GENERADORES DE REDES
# ============================================================

def generate_watts_strogatz(N: int, k: int = 5, p: float = 0.1,
                             seed: int = 42) -> np.ndarray:
    """
    Genera la matriz de adyacencia de una red Watts-Strogatz (mundo pequeño).

    Args:
        N: Número de nodos.
        k: Cada nodo conectado a k vecinos más cercanos en el anillo.
        p: Probabilidad de reconexión.
        seed: Semilla aleatoria para reproducibilidad.

    Returns:
        Matriz de adyacencia (N, N) normalizada por grado.
    """
    G = nx.watts_strogatz_graph(N, k=min(k, N - 1), p=p, seed=seed)
    A = nx.to_numpy_array(G, dtype=np.float64)
    return _normalize_rows(A)


def generate_scale_free(N: int, m: int = 2, seed: int = 42) -> np.ndarray:
    """
    Genera la matriz de adyacencia de una red libre de escala (Barabási-Albert).

    Args:
        N: Número de nodos.
        m: Número de aristas a añadir por nodo nuevo.
        seed: Semilla aleatoria para reproducibilidad.

    Returns:
        Matriz de adyacencia (N, N) normalizada por grado.
    """
    G = nx.barabasi_albert_graph(N, m=m, seed=seed)
    A = nx.to_numpy_array(G, dtype=np.float64)
    return _normalize_rows(A)


def generate_hierarchical(N: int, seed: int = 42) -> np.ndarray:
    """
    Genera una red económica jerárquica: unos pocos nodos de alta autoridad
    (hubs) conectados en estrella a grupos de nodos subordinados.

    Args:
        N: Número de nodos totales.
        seed: Semilla aleatoria para reproducibilidad.

    Returns:
        Matriz de adyacencia (N, N) normalizada por grado, asimétrica
        (la influencia fluye de hubs hacia subordinados con mayor peso).
    """
    rng = np.random.default_rng(seed)
    n_hubs = max(1, int(N * _HIERARCHY_HUB_FRACTION))
    G = nx.star_graph(N - 1)  # base estrella
    # Añadir conexiones aleatorias entre hubs para conectividad
    hub_ids = list(range(n_hubs))
    for i in hub_ids:
        for j in hub_ids:
            if i != j and rng.random() < 0.7:
                G.add_edge(i, j)
    A = nx.to_numpy_array(G, dtype=np.float64)
    return _normalize_rows(A)


def _normalize_rows(A: np.ndarray) -> np.ndarray:
    """Normaliza cada fila por su suma para que las influencias estén en [0, 1]."""
    row_sums = A.sum(axis=1, keepdims=True)
    row_sums[row_sums == 0] = 1.0
    return A / row_sums


def build_layers(N: int, config: dict | None = None) -> dict:
    """
    Construye el diccionario de capas de red para N agentes.

    Args:
        N: Número de agentes.
        config: Configuración de capas (opcional). Si es None, usa valores por defecto.

    Returns:
        Dict con claves 'social', 'digital', 'economic', cada una mapea a
        una matriz numpy (N, N) normalizada.
    """
    cfg = config or {}
    social_cfg  = cfg.get("social",   {})
    digital_cfg = cfg.get("digital",  {})
    econ_cfg    = cfg.get("economic", {})

    return {
        "social":   generate_watts_strogatz(
            N,
            k=social_cfg.get("k", 5),
            p=social_cfg.get("p", 0.1),
        ),
        "digital":  generate_scale_free(
            N,
            m=digital_cfg.get("m", 2),
        ),
        "economic": generate_hierarchical(N),
    }


# ============================================================
# ATRIBUTOS SOCIODEMOGRÁFICOS
# ============================================================

def generate_attributes(
    N: int,
    age_dist:        tuple = (0.3, 0.4, 0.3),
    religion_prob:   float = 0.3,
    education_scale: float = 1.0,
    gender_ratio:    float = 0.5,
    seed:            int   = 42,
) -> pd.DataFrame:
    """
    Genera el DataFrame de atributos sociodemográficos para N agentes.

    Args:
        N: Número de agentes.
        age_dist: Proporción (young=0, middle=1, old=2). Debe sumar 1.
        religion_prob: Probabilidad de ser religioso [0, 1].
        education_scale: Escala multiplicativa del nivel educativo (≈1.0 normal).
        gender_ratio: Probabilidad de género femenino (1) [0, 1].
        seed: Semilla aleatoria.

    Returns:
        DataFrame con columnas: age_group, religion, education, gender.
    """
    rng = np.random.default_rng(seed)
    dist = np.array(age_dist, dtype=float)
    dist /= dist.sum()

    age_group = rng.choice([0, 1, 2], size=N, p=dist)
    religion  = (rng.random(N) < religion_prob).astype(int)
    education = np.clip(rng.beta(2, 2, N) * education_scale, 0.0, 1.0)
    gender    = (rng.random(N) < gender_ratio).astype(int)

    return pd.DataFrame({
        "age_group": age_group,   # 0=young, 1=middle, 2=old
        "religion":  religion,    # 0=no, 1=yes
        "education": education,   # continuous [0, 1]
        "gender":    gender,      # 0=male, 1=female
    })


def compute_theta(attributes_df: pd.DataFrame, K: int = 5) -> np.ndarray:
    """
    Calcula la matriz theta de modulación (N, K) a partir de los atributos.

    Cada θ_{i,k} escala el ruido y la sensibilidad del agente i en la
    dimensión de comportamiento k, según sus características sociodemográficas.

    Args:
        attributes_df: DataFrame con columnas age_group, religion, education, gender.
        K: Número de dimensiones de comportamiento.

    Returns:
        Matriz theta de forma (N, K), flotante.
    """
    N = len(attributes_df)
    theta = np.ones((N, K), dtype=np.float64)

    rel = attributes_df["religion"].to_numpy(dtype=np.float64)
    edu = attributes_df["education"].to_numpy(dtype=np.float64)
    age = attributes_df["age_group"].to_numpy(dtype=np.float64)

    # Opinión: los más religiosos son más sensibles a señales morales
    theta[:, COL_OPINION] *= 1.0 + _THETA_RELIGION_OPINION * rel
    # Cooperación: educación aumenta la disposición a cooperar
    theta[:, COL_COOP]    *= 1.0 + _THETA_EDUCATION_COOP * edu
    # Jerarquía: los de mayor edad tienden a reconocer más la autoridad
    theta[:, COL_HIER]    *= 1.0 + _THETA_AGE_HIERARCHY * (age / 2.0)
    # Ingreso: jóvenes más volátiles en ingreso
    theta[:, COL_INCOME]  *= 1.0 + _THETA_YOUTH_INCOME * (1.0 - age / 2.0)
    # Acceso a información: educación amplifica el acceso digital
    theta[:, COL_INFO]    *= 1.0 + _THETA_EDUCATION_INFO * edu

    return theta


# ============================================================
# POTENCIAL MULTIDIMENSIONAL (JIT)
# ============================================================

@njit
def _bimodal_grad(opinion: float) -> float:
    """Gradiente del doble pozo U = (x²-0.49)² → attrae hacia ±0.7.

    El mínimo del pozo está en x = ±0.7 porque ∂U/∂x = 0 cuando x² = 0.49 = 0.7².
    """
    return 4.0 * opinion * (opinion * opinion - 0.49)


@njit
def multi_potential_gradient(x: np.ndarray) -> np.ndarray:
    """
    Gradiente del potencial social multidimensional U(x).

    U(x) = U_opinion(x[:,0]) + U_coop(x[:,1], x[:,0])
           + U_hierarchy(x[:,2]) + U_income(x[:,3]) + U_info(x[:,4])

    Args:
        x: Estado actual de forma (N, K).

    Returns:
        Gradiente ∇U de forma (N, K).
    """
    N = x.shape[0]
    grad = np.zeros_like(x)

    for i in range(N):
        op   = x[i, COL_OPINION]
        coop = x[i, COL_COOP]
        hier = x[i, COL_HIER]
        inc  = x[i, COL_INCOME]
        info = x[i, COL_INFO]

        # Opinión: doble pozo → polarización emergente en ±0.7
        grad[i, COL_OPINION] = _bimodal_grad(op)

        # Cooperación: depende de la opinión del agente (alineación social)
        # Alto acuerdo de opinión → cooperación se estabiliza en 0.8
        align = 0.5 * (op + 1.0)  # mapea [-1,1] → [0,1]
        grad[i, COL_COOP] = 2.0 * (coop - 0.8 * align)

        # Jerarquía: atracción hacia 0 (rebelde) o 1 (conformista)
        grad[i, COL_HIER] = -2.0 * hier * (1.0 - hier) * (2.0 * hier - 1.0)

        # Ingreso: gradiente suave hacia centro (0.5), con fricción por jerarquía
        grad[i, COL_INCOME] = 0.5 * (inc - 0.5) * (1.0 + hier)

        # Acceso info: decaimiento lento hacia 0.5 modulado por cooperación
        grad[i, COL_INFO] = 0.3 * (info - 0.5 - 0.2 * coop)

    return grad


# ============================================================
# PASO DE LANGEVIN MULTICAPA (JIT)
# ============================================================

@njit
def multilayer_langevin_step(
    x_vec:        np.ndarray,
    layers_flat:  np.ndarray,
    layer_weights: np.ndarray,
    theta_matrix: np.ndarray,
    coupling:     float,
    dt:           float,
    x_min:        float,
    x_max:        float,
) -> np.ndarray:
    """
    Paso de Euler-Maruyama de la dinámica de Langevin multicapa.

    Ecuación: dx_i = (-∇U + Σ_ℓ w_ℓ F_ℓ(x)) dt + θ_i · η_i · √dt

    Args:
        x_vec:         Estado actual (N, K).
        layers_flat:   Matrices de adyacencia apiladas (L, N, N).
        layer_weights: Pesos de cada capa (L,).
        theta_matrix:  Modulación sociodemográfica (N, K).
        coupling:      Intensidad del acoplamiento social.
        dt:            Paso de tiempo.
        x_min:         Mínimo del rango (opinión).
        x_max:         Máximo del rango (opinión).

    Returns:
        Estado actualizado (N, K) con opinión recortada a [x_min, x_max]
        y las demás dimensiones recortadas a [0, 1].
    """
    N, Kdim = x_vec.shape
    L = layers_flat.shape[0]

    # Fuerza social multicapa: Σ_ℓ w_ℓ · A_ℓ · x[:,0]
    social_force = np.zeros((N, Kdim))
    for ell in range(L):
        w = layer_weights[ell]
        for i in range(N):
            s = 0.0
            for j in range(N):
                s += layers_flat[ell, i, j] * x_vec[j, COL_OPINION]
            social_force[i, COL_OPINION] += coupling * w * s

    # Gradiente del potencial multidimensional
    grad_U = multi_potential_gradient(x_vec)

    # Ruido gaussiano modulado por theta
    noise = np.random.randn(N, Kdim)

    # Actualización: Euler-Maruyama
    x_new = x_vec + dt * (-grad_U + social_force) + theta_matrix * _STOCHASTIC_SCALE * noise * np.sqrt(dt)

    # Recortar al rango válido
    for i in range(N):
        v = x_new[i, COL_OPINION]
        if v < x_min:
            x_new[i, COL_OPINION] = x_min
        elif v > x_max:
            x_new[i, COL_OPINION] = x_max
        for k in range(1, Kdim):
            if x_new[i, k] < 0.0:
                x_new[i, k] = 0.0
            elif x_new[i, k] > 1.0:
                x_new[i, k] = 1.0

    return x_new


# ============================================================
# SESGO LLM DIRIGIDO (extensión de llm_oracle)
# ============================================================

def targeted_llm_bias(
    layer_target: str = "digital",
    demographic:  str = "religion=1",
    proveedor:    str = "heurístico",
    api_key:      str = "",
    modelo:       str = "",
) -> str:
    """
    Genera un argumento narrativo dirigido a un grupo demográfico en una capa específica.

    Integra con el LLM configurado en el sistema (mismo proveedor que el selector).

    Args:
        layer_target: Capa objetivo ('social', 'digital', 'economic').
        demographic:  Descriptor del grupo objetivo (ej. 'religion=1', 'age_group=0').
        proveedor:    Proveedor LLM a usar.
        api_key:      API key del proveedor.
        modelo:       Modelo a usar.

    Returns:
        Argumento narrativo generado, o cadena heurística si no hay LLM.
    """
    etiquetas = {
        "religion=1": "comunidades religiosas conservadoras",
        "religion=0": "comunidades seculares",
        "age_group=0": "jóvenes (18-35)",
        "age_group=2": "adultos mayores (55+)",
        "gender=1":   "mujeres",
        "gender=0":   "hombres",
    }
    grupo_label = etiquetas.get(demographic, demographic)
    layer_label = {"social": "red de contactos sociales", "digital": "redes digitales/social media",
                   "economic": "red económica/laboral"}.get(layer_target, layer_target)

    prompt = (
        f"En el contexto de una simulación de dinámica social, genera un argumento persuasivo "
        f"de máximo 2 oraciones dirigido a {grupo_label} en {layer_label}. "
        f"El objetivo es aumentar la cooperación y reducir la polarización. "
        f"Responde solo con el argumento, sin explicaciones adicionales."
    )

    key = resolve_provider_api_key(proveedor, fallback=api_key)

    if proveedor == "heurístico" or not key:
        return (
            f"[Heurístico] Narrativa para {grupo_label} vía {layer_label}: "
            f"La cooperación compartida fortalece a tu comunidad. "
            f"Juntos construimos mejores resultados."
        )

    try:
        import requests
        try:
            from simulator import PROVEEDORES as _PROVEEDORES
            base_url = _PROVEEDORES[proveedor]["base_url"]
        except (ImportError, KeyError):
            return (
                f"[Fallback] Narrativa para {grupo_label}: "
                f"El diálogo y la cooperación construyen comunidades más resilientes."
            )
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        payload = {
            "model": modelo,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.7,
            "max_tokens": 100,
        }
        resp = requests.post(f"{base_url}/chat/completions", json=payload,
                             headers=headers, timeout=15)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()
    except Exception:
        return (
            f"[Fallback] Narrativa para {grupo_label}: "
            f"El diálogo y la cooperación construyen comunidades más resilientes."
        )


# ============================================================
# CLASE ORQUESTADORA
# ============================================================

class MultilayerEngine:
    """
    Motor de simulación social multicapa con atributos sociodemográficos.

    Integra redes diferenciadas (social, digital, económica), vector de estado
    multidimensional por agente, potencial social multidimensional y modulación
    de ruido por atributos (theta_matrix).

    Ejemplo de uso::

        engine = MultilayerEngine(N=200)
        history = engine.run(steps=100)
        df = engine.trajectories_by_attribute('age_group')
    """

    def __init__(
        self,
        N:              int   = 100,
        layer_weights:  tuple = (0.4, 0.3, 0.3),
        coupling:       float = 0.3,
        dt:             float = 0.01,
        range_type:     str   = "bipolar",
        attr_config:    dict  | None = None,
        layer_config:   dict  | None = None,
        seed:           int   = 42,
    ):
        """
        Inicializa el motor multicapa.

        Args:
            N: Número de agentes.
            layer_weights: Pesos de capas (social, digital, económica). Se normalizan.
            coupling: Intensidad del acoplamiento social λ.
            dt: Paso de tiempo de integración.
            range_type: 'bipolar' [-1,1] o 'unipolar' [0,1] para la opinión.
            attr_config: Parámetros de generación de atributos (ver generate_attributes).
            layer_config: Parámetros de generación de capas (ver build_layers).
            seed: Semilla para reproducibilidad.
        """
        if N < 2:
            raise ValueError("N debe ser ≥ 2")

        self.N = N
        self.coupling = float(coupling)
        self.dt = float(dt)
        self.seed = seed
        self.range_type = range_type
        self.x_min = -1.0 if range_type == "bipolar" else 0.0
        self.x_max = 1.0

        # Pesos de capas normalizados
        w = np.array(layer_weights, dtype=np.float64)
        self.layer_weights = w / w.sum()

        # Atributos sociodemográficos
        attr_cfg = attr_config or {}
        self.attributes_df = generate_attributes(N, seed=seed, **attr_cfg)
        self.theta = compute_theta(self.attributes_df)

        # CfC INTEGRATION — τ aprendido sustituye la theta manual si está disponible
        try:
            from cfc_router import CfCRouter
            _cfc_tau = CfCRouter.get().compute_tau_matrix(
                np.stack([
                    self.attributes_df["religion"].to_numpy(dtype=np.float32),
                    self.attributes_df["education"].to_numpy(dtype=np.float32),
                    (self.attributes_df["age_group"].to_numpy(dtype=np.float32) / 3.0),
                    self.attributes_df["gender"].to_numpy(dtype=np.float32),
                ], axis=1)
            )
            if _cfc_tau is not None:
                # Escalar al rango de la theta manual para compatibilidad
                self.theta = (_cfc_tau * self.theta.max()).astype(np.float64)
        except ImportError:
            pass

        # Capas de red
        self.layers = build_layers(N, layer_config)
        self._layers_flat = np.stack([
            self.layers["social"],
            self.layers["digital"],
            self.layers["economic"],
        ], axis=0).astype(np.float64)

        # Estado inicial
        rng = np.random.default_rng(seed)
        x0_opinion = rng.uniform(self.x_min * 0.5, self.x_max * 0.5, N)
        x0_rest    = rng.uniform(0.2, 0.8, (N, K - 1))
        self.x = np.column_stack([x0_opinion, x0_rest]).astype(np.float64)

        self._history: list[np.ndarray] = [self.x.copy()]
        self.mps_state = None

    # ── API pública ─────────────────────────────────────────────────────────

    def _refresh_mps_state(self) -> None:
        """Synchronize compressed state according to population size."""
        self.mps_state = (
            compress_agent_states(self.x)
            if self.N > MPS_COMPRESSION_MIN_AGENTS
            else None
        )

    def step(self) -> np.ndarray:
        """Advance one integration step and return the updated state."""
        self.x = multilayer_langevin_step(
            self.x,
            self._layers_flat,
            self.layer_weights,
            self.theta,
            self.coupling,
            self.dt,
            self.x_min,
            self.x_max,
        )
        self._history.append(self.x.copy())
        self._refresh_mps_state()
        return self.x

    def run(self, steps: int = 100) -> list[np.ndarray]:
        """
        Ejecuta la simulación por `steps` pasos.

        Args:
            steps: Número de pasos de integración.

        Returns:
            Lista de matrices de estado (N, K), de longitud steps + 1
            (incluye el estado inicial).
        """
        if steps < 1:
            raise ValueError("steps debe ser ≥ 1")
        for _ in range(steps):
            self.step()
        return self._history

    def get_landscape(self) -> dict:
        """
        Calcula métricas del paisaje social actual.

        Returns:
            Dict con mean_opinion, std_opinion, polarization, mean_cooperation,
            mean_hierarchy.
        """
        x = self.x
        opinions = x[:, COL_OPINION]
        return {
            "mean_opinion":    float(np.mean(opinions)),
            "std_opinion":     float(np.std(opinions)),
            "polarization":    float(np.mean(np.abs(opinions))),
            "mean_cooperation": float(np.mean(x[:, COL_COOP])),
            "mean_hierarchy":   float(np.mean(x[:, COL_HIER])),
        }

    def trajectories_by_attribute(self, attribute: str = "age_group") -> pd.DataFrame:
        """
        Calcula la trayectoria de opinión media agrupada por un atributo.

        Args:
            attribute: Columna del attributes_df por la que agrupar.

        Returns:
            DataFrame con columnas: step, <attribute_value>, mean_opinion.
        """
        records = []
        for step_idx, x_snap in enumerate(self._history):
            for group_val in self.attributes_df[attribute].unique():
                mask = self.attributes_df[attribute].to_numpy() == group_val
                mean_op = float(x_snap[mask, COL_OPINION].mean())
                records.append({"step": step_idx, attribute: group_val,
                                 "mean_opinion": mean_op})
        return pd.DataFrame(records)

    def update_opinions(self, new_opinions: np.ndarray) -> None:
        """Update the engine state and optionally compress it for large populations.

        Args:
            new_opinions: New state matrix with shape (N, K).

        Raises:
            ValueError: If the provided matrix shape does not match (N, K).
        """
        arr = np.asarray(new_opinions, dtype=np.float64)
        if arr.shape != (self.N, K):
            raise ValueError(f"new_opinions must have shape ({self.N}, {K})")
        arr[:, COL_OPINION] = np.clip(arr[:, COL_OPINION], self.x_min, self.x_max)
        arr[:, 1:] = np.clip(arr[:, 1:], 0.0, 1.0)
        self.x = arr
        self._history.append(self.x.copy())
        self._refresh_mps_state()

    def get_opinions(self) -> np.ndarray:
        """Return the current state, decompressing MPS payload when present.

        Returns:
            Numpy array with shape (N, K).
        """
        if self.mps_state is not None:
            return decompress_agent_states(self.mps_state)
        return self.x

    def behavior_correlation_matrix(self) -> np.ndarray:
        """
        Calcula la matriz de correlación (K × K) entre los K comportamientos
        usando el estado final.

        Returns:
            Matriz de correlación numpy (K, K).
        """
        return np.corrcoef(self.x.T)

    def plot(self) -> "dict":
        """
        Genera diccionarios de datos para las visualizaciones multicapa.

        Returns:
            Dict con claves 'trajectories_df', 'corr_matrix', 'landscape'.
        """
        return {
            "trajectories_df": self.trajectories_by_attribute("age_group"),
            "corr_matrix":     self.behavior_correlation_matrix(),
            "landscape":       self.get_landscape(),
        }
