"""
micro_engine.py — Motor de Simulación Inversa para Grupos Pequeños (MASSIVE Micro)

En lugar de predecir "qué va a pasar", ejecuta ensembles del MultilayerEngine
existente, clusteriza las trayectorias en "familias de futuros", e identifica
los parámetros de bifurcación que determinan en qué familia cae el grupo.

Flujo:
  1. Se describe un grupo (GroupProfile)
  2. Se ejecutan N simulaciones con variaciones paramétricas
  3. Se extraen features de cada trayectoria
  4. Se clusterizan en familias de futuros
  5. Se identifican los parámetros de bifurcación (Random Forest)
  6. El Micro Social Architect encuentra transiciones entre familias

Dependencias: numpy, scikit-learn, hdbscan (opcional)
"""

from __future__ import annotations

import logging
from typing import Any

import numpy as np

log = logging.getLogger("massive")

# ── Dependencies (all optional) ──────────────────────────────────────────────
try:
    from sklearn.preprocessing import StandardScaler
    from sklearn.decomposition import PCA
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

try:
    import hdbscan
    HDBSCAN_AVAILABLE = True
except ImportError:
    HDBSCAN_AVAILABLE = False

try:
    from dask import delayed, compute as dask_compute
    DASK_AVAILABLE = True
except ImportError:
    DASK_AVAILABLE = False

# Local imports (deferred to avoid circular imports at module level)
_ML_ENGINE = None
def _get_multilayer_engine():
    global _ML_ENGINE
    if _ML_ENGINE is None:
        from multilayer_engine import MultilayerEngine
        _ML_ENGINE = MultilayerEngine
    return _ML_ENGINE


# ============================================================
# FEATURE EXTRACTION
# ============================================================

def extract_trajectory_features(
    history: list[np.ndarray],
) -> dict[str, float]:
    """
    Extrae un vector de características de la trayectoria de un grupo.

    Args:
        history: Lista de estados (N, K) del MultilayerEngine.

    Returns:
        Dict con ~13 features numéricas que describen la dinámica del grupo.
    """
    arr = np.stack(history, axis=0)  # (T, N, K)
    T, N, K = arr.shape
    if T < 2:
        return {"_error": 1.0}

    # Dimensiones
    op = arr[:, :, 0]   # opinion  (T, N)
    co = arr[:, :, 1]   # cooperation
    hi = arr[:, :, 2]   # hierarchy
    ic = arr[:, :, 3]   # income/status
    ia = arr[:, :, 4]   # info_access/trust

    # Estado final
    op_end = op[-1, :]
    co_end = co[-1, :]
    hi_end = hi[-1, :]
    ia_end = ia[-1, :]

    # Polarización: desviación estándar de opiniones al final
    # (alta = grupo dividido, baja = consenso)
    pol = float(np.std(op_end))

    # Qué tan jerárquico es el grupo (mean + spread)
    hier_mean = float(np.mean(hi_end))
    hier_std = float(np.std(hi_end))

    # Cooperación promedio al final
    coop_mean = float(np.mean(co_end))

    # Confianza/flujo de información
    trust_mean = float(np.mean(ia_end))

    # Asimetría de la distribución de opiniones
    op_skew = float(np.mean((op_end - np.mean(op_end))**3) / max(np.std(op_end)**3, 1e-10))

    # Estabilidad: varianza de la opinión media en el último 20% de pasos
    tail = max(T // 5, 2)
    mean_op_tail = np.mean(op[-tail:, :], axis=1)
    stability = float(np.var(mean_op_tail))

    # Máxima polarización alcanzada durante toda la simulación
    op_std_t = np.std(op, axis=1)
    max_pol = float(np.max(op_std_t))

    # Tiempo de estabilización: primer paso donde la desviación estándar
    # de opinión queda dentro del 10% del valor final
    final_std = op_std_t[-1]
    tol = 0.1 * max(abs(final_std), 0.01)
    stable_idx = T - 1
    for t in range(T - 1, T // 2, -1):
        if abs(op_std_t[t] - final_std) > tol:
            stable_idx = t
            break
    time_to_stabilize = float(stable_idx) / float(T)

    # Correlación entre dimensiones al final
    final_state = arr[-1, :, :]
    corr = np.corrcoef(final_state.T)
    corr_off_diag = corr[np.triu_indices(K, k=1)]
    dim_corr_mean = float(np.mean(np.abs(corr_off_diag)))

    # Cambio total en opinión media (consenso o disenso)
    op_mean_start = float(np.mean(op[0, :]))
    op_mean_end = float(np.mean(op[-1, :]))
    op_delta = abs(op_mean_end - op_mean_start)

    # Cambio en cooperación
    co_delta = abs(float(np.mean(co[-1, :]) - np.mean(co[0, :])))

    # Extreme concentration: qué fracción de agentes está en los extremos
    threshold = 0.7
    extreme_frac = float(np.mean(np.abs(op_end) > threshold))

    return {
        "polarization": pol,
        "hierarchy_mean": hier_mean,
        "hierarchy_std": hier_std,
        "cooperation": coop_mean,
        "trust": trust_mean,
        "opinion_skew": op_skew,
        "stability": stability,
        "max_polarization": max_pol,
        "time_to_stabilize": time_to_stabilize,
        "dim_correlation": dim_corr_mean,
        "opinion_delta": op_delta,
        "cooperation_delta": co_delta,
        "extreme_fraction": extreme_frac,
    }


# ============================================================
# GROUP PROFILE → MULTILAYERENGINE MAPPER
# ============================================================

def _profile_to_engine_params(
    profile: Any,
    variation: dict[str, float] | None = None,
    seed: int = 42,
) -> dict:
    """
    Convierte un GroupProfile + variación en kwargs para MultilayerEngine.

    Args:
        profile: GroupProfile instance.
        variation: Sobrescritura de parámetros para esta simulación.
        seed: Semilla RNG.

    Returns:
        Dict con kwargs para MultilayerEngine.__init__ + initial state config.
    """
    var = variation or {}

    # coupling = communication_frequency ± variación
    coupling = var.get("coupling", profile.communication_frequency)

    # external_pressure modula el ruido
    external_pressure = var.get("external_pressure", profile.external_pressure)

    # hierarchy_tolerance → layer_weights (más económico = más jerárquico)
    # A mayor hierarchy_tolerance, más peso en la capa económica
    social_w = 0.5 * (1.0 - profile.hierarchy_tolerance)
    digital_w = 0.3 * (1.0 - profile.hierarchy_tolerance)
    economic_w = 0.2 + 0.8 * profile.hierarchy_tolerance
    layer_weights = (social_w, digital_w, economic_w)

    # diversity_of_opinion → dispersión inicial de opiniones
    div = profile.diversity_of_opinion

    # initial cohesion → media de la opinión inicial
    # (alta cohesión = opiniones cerca del neutro, baja = dispersas)
    initial_noise = var.get("initial_noise", 0.1)
    base_spread = div * 0.5 + initial_noise * 0.3

    return {
        "N": profile.n_members,
        "layer_weights": layer_weights,
        "coupling": coupling,
        "dt": 0.01,
        "range_type": "bipolar",
        "seed": seed,
        "_external_pressure": external_pressure,
        "_base_spread": base_spread,
        "_initial_noise": initial_noise,
    }


# ============================================================
# ENSEMBLE RUNNER
# ============================================================

class MicroSimOrchestrator:
    """
    Orquestador de ensembles de simulación para grupos pequeños.

    Construye un MultilayerEngine con los parámetros del GroupProfile,
    varía parámetros clave en cada corrida, extrae features y las
    prepara para clusterización.

    Ejemplo::

        orch = MicroSimOrchestrator()
        result = orch.run_ensemble(profile, config)
        print(result.n_families, "familias de futuros encontradas")
    """

    def __init__(self, quiet: bool = False):
        self._quiet = quiet

    def run_single(
        self,
        profile: Any,
        variation: dict[str, float] | None = None,
        steps: int = 200,
        seed: int = 42,
    ) -> tuple[np.ndarray, dict[str, float]]:
        """
        Ejecuta una simulación individual.

        Args:
            profile: GroupProfile.
            variation: Parámetros de variación para esta corrida.
            steps: Número de pasos.
            seed: Semilla.

        Returns:
            Tupla (history_array, features_dict).
        """
        params = _profile_to_engine_params(profile, variation, seed=seed)
        ext_pressure = params.pop("_external_pressure", 0.0)
        base_spread = params.pop("_base_spread", 0.3)
        initial_noise = params.pop("_initial_noise", 0.1)

        EngineCls = _get_multilayer_engine()
        engine = EngineCls(**params)

        # Sobrescribir estado inicial según el perfil
        rng = np.random.default_rng(seed)
        N = profile.n_members
        opinions = rng.uniform(
            -base_spread - initial_noise * 0.5,
            base_spread + initial_noise * 0.5,
            N,
        )
        opinions = np.clip(opinions, -1.0, 1.0)

        # Si hay miembros con opinión inicial específica, usarla
        for i, member in enumerate(profile.members):
            if member.initial_opinion is not None and i < N:
                opinions[i] = np.clip(member.initial_opinion, -1.0, 1.0)

        # Cooperation biases de miembros (default si no hay miembros definidos)
        if profile.members:
            coop = np.array([
                profile.members[i].cooperation_bias if i < len(profile.members) else 0.5
                for i in range(N)
            ])
            hier = np.array([
                profile.members[i].hierarchy_bias if i < len(profile.members) else 0.5
                for i in range(N)
            ])
            trust = np.array([
                profile.members[i].trust_bias if i < len(profile.members) else 0.5
                for i in range(N)
            ])
        else:
            coop = np.full(N, 0.5)
            hier = np.full(N, 0.5)
            trust = np.full(N, 0.5)

        state = np.column_stack([
            opinions,
            coop + rng.normal(0, initial_noise * 0.1, N),
            hier + rng.normal(0, initial_noise * 0.1, N),
            base_spread * rng.random(N),
            trust + rng.normal(0, initial_noise * 0.1, N),
        ]).astype(np.float64)
        state = np.clip(state, [-1, 0, 0, 0, 0], [1, 1, 1, 1, 1])
        engine.update_opinions(state)

        # Ejecutar
        history = engine.run(steps=steps)

        # Aplicar external_pressure como ruido adicional en cada paso
        # (simula presión externa continua sobre el grupo)
        if ext_pressure > 0.01:
            rng_step = np.random.default_rng(seed + 42)
            x = history[-1].copy()
            for t in range(steps):
                noise = rng_step.normal(0, ext_pressure * 0.05, (N, 5))
                x = x + noise
                x[:, 0] = np.clip(x[:, 0], -1.0, 1.0)
                x[:, 1:] = np.clip(x[:, 1:], 0.0, 1.0)
                engine.update_opinions(x)
            history = engine._history

        history_arr = np.stack(history, axis=0)
        features = extract_trajectory_features(history)

        return history_arr, features

    def run_ensemble(
        self,
        profile: Any,
        n_simulations: int = 500,
        steps_per_sim: int = 200,
        variations: list[dict[str, float]] | None = None,
        seed: int = 42,
        use_dask: bool = True,
    ) -> tuple[list[np.ndarray], np.ndarray, list[dict[str, float]]]:
        """
        Ejecuta N simulaciones variando parámetros clave.

        Args:
            profile: GroupProfile.
            n_simulations: Número de simulaciones.
            steps_per_sim: Pasos por simulación.
            variations: Lista de dicts con variaciones de parámetros.
                Si es None, se genera automáticamente.
            seed: Semilla base.
            use_dask: Usar Dask si está disponible.

        Returns:
            Tupla (trajectories, feature_matrix, param_records).
        """
        if variations is None:
            variations = self._generate_variations(n_simulations, seed)
        else:
            n_simulations = len(variations)

        all_histories: list[np.ndarray] = []
        all_features: list[dict] = []
        all_params: list[dict] = []

        if use_dask and DASK_AVAILABLE and n_simulations > 20:
            log.info(f"[Micro] Ensemble Dask: {n_simulations} simulaciones")

            @delayed
            def _run_one(var: dict, s: int) -> tuple[np.ndarray, dict, dict]:
                hist, feats = self.run_single(profile, var, steps_per_sim, seed=s)
                return hist, feats, var

            tasks = [_run_one(v, seed + i) for i, v in enumerate(variations)]
            results = dask_compute(*tasks)

            for hist, feats, var in results:
                all_histories.append(hist)
                all_features.append(feats)
                all_params.append(var)
        else:
            log.info(f"[Micro] Ensemble secuencial: {n_simulations} simulaciones")
            for i in range(n_simulations):
                var = variations[i]
                hist, feats = self.run_single(profile, var, steps_per_sim, seed + i)
                all_histories.append(hist)
                all_features.append(feats)
                all_params.append(var)

        feature_matrix = self._features_to_matrix(all_features)

        log.info(f"[Micro] Ensemble completo: {n_simulations} sims, "
                 f"{feature_matrix.shape[1]} features")

        return all_histories, feature_matrix, all_params

    def _generate_variations(
        self,
        n: int,
        seed: int = 42,
    ) -> list[dict[str, float]]:
        """Genera variaciones paramétricas aleatorias."""
        rng = np.random.default_rng(seed)
        variations = []
        for _ in range(n):
            variations.append({
                "coupling": rng.uniform(0.05, 0.8),
                "external_pressure": rng.uniform(0.0, 0.5),
                "initial_noise": rng.uniform(0.01, 0.3),
            })
        return variations

    def _features_to_matrix(self, features: list[dict]) -> np.ndarray:
        """Convierte lista de dicts de features en matriz numpy."""
        keys = [k for k in features[0].keys() if not k.startswith("_")]
        matrix = np.zeros((len(features), len(keys)), dtype=np.float64)
        for i, f in enumerate(features):
            for j, k in enumerate(keys):
                matrix[i, j] = f.get(k, 0.0)
        return matrix

    def get_feature_names(self) -> list[str]:
        """Returns feature names from the last extraction."""
        return [
            "polarization", "hierarchy_mean", "hierarchy_std", "cooperation",
            "trust", "opinion_skew", "stability", "max_polarization",
            "time_to_stabilize", "dim_correlation", "opinion_delta",
            "cooperation_delta", "extreme_fraction",
        ]


# ============================================================
# CLUSTERIZACIÓN Y ANÁLISIS DE BIFURCACIÓN
# ============================================================

class FamilyOfFuturesAnalyzer:
    """
    Analiza las trayectorias del ensemble para encontrar familias de futuros
    y sus parámetros de bifurcación.

    Las "familias de futuros" son clusters de trayectorias que comparten
    características dinámicas similares (misma polarización, cooperación,
    estabilidad, etc). Los "parámetros de bifurcación" son las variables
    de entrada que más determinan en qué familia cae cada simulación.
    """

    def __init__(self, n_clusters: int = 0, random_state: int = 42):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self._scaler: Any = None
        self._pca: Any = None
        self._clusterer: Any = None
        self._rf: Any = None

    def fit(
        self,
        feature_matrix: np.ndarray,
        param_records: list[dict[str, float]],
    ) -> tuple[np.ndarray, dict]:
        """
        Clusteriza las trayectorias y mapea bifurcaciones.

        Args:
            feature_matrix: (n_sims, n_features).
            param_records: Lista de dicts con parámetros de cada sim.

        Returns:
            Tupla (labels, bifurcation_info).
        """
        if not SKLEARN_AVAILABLE:
            raise ImportError("Se requiere scikit-learn para el análisis de familias")

        n_sims = feature_matrix.shape[0]
        n_feats = feature_matrix.shape[1]

        # 1. Estandarizar features
        self._scaler = StandardScaler()
        X_scaled = self._scaler.fit_transform(feature_matrix)

        # 2. PCA si hay muchas features
        n_components = min(n_feats, 10, n_sims - 1)
        if n_components < n_feats:
            self._pca = PCA(n_components=n_components, random_state=self.random_state)
            X_pca = self._pca.fit_transform(X_scaled)
        else:
            X_pca = X_scaled

        # 3. Clusterizar
        labels = self._cluster(X_pca)

        # 4. Mapa de bifurcación
        param_matrix = self._params_to_matrix(param_records)
        bifurcation = self._build_bifurcation_map(param_matrix, labels, feature_matrix)

        return labels, bifurcation

    def _cluster(self, X: np.ndarray) -> np.ndarray:
        """Aplica HDBSCAN o KMeans con silhouette."""
        n_sims = X.shape[0]

        if HDBSCAN_AVAILABLE and self.n_clusters == 0:
            self._clusterer = hdbscan.HDBSCAN(
                min_cluster_size=max(5, n_sims // 50),
                min_samples=1,
                cluster_selection_epsilon=0.5,
                prediction_data=True,
            )
            labels = self._clusterer.fit_predict(X)
            n_noise = int((labels == -1).sum())
            n_found = len(set(labels)) - (1 if -1 in labels else 0)
            log.info(f"[Micro] HDBSCAN: {n_found} clusters, {n_noise} ruido")
            if n_found < 2 and n_sims >= 20:
                log.info("[Micro] HDBSCAN no encontró estructura, usando KMeans")
                return self._kmeans_fallback(X)
            return labels

        return self._kmeans_fallback(X)

    def _kmeans_fallback(self, X: np.ndarray) -> np.ndarray:
        """KMeans con selección automática de k vía silhouette."""
        n_sims = X.shape[0]
        max_k = min(8, n_sims // 10)

        if max_k < 2:
            return np.zeros(n_sims, dtype=int)

        if self.n_clusters > 1:
            k = min(self.n_clusters, max_k)
        else:
            best_k, best_score = 2, -1.0
            for k in range(2, max_k + 1):
                km = KMeans(n_clusters=k, n_init=5, random_state=self.random_state)
                labels = km.fit_predict(X)
                if len(set(labels)) > 1:
                    score = silhouette_score(X, labels)
                    if score > best_score:
                        best_k, best_score = k, score
            k = best_k

        km = KMeans(n_clusters=k, n_init=10, random_state=self.random_state)
        labels = km.fit_predict(X)
        self._clusterer = km
        log.info(f"[Micro] KMeans: k={k}, silhouette={best_score:.3f}")
        return labels

    def _params_to_matrix(self, param_records: list[dict]) -> np.ndarray:
        """Convierte registros de params en matriz."""
        keys = list(param_records[0].keys()) if param_records else []
        matrix = np.zeros((len(param_records), len(keys)), dtype=np.float64)
        for i, rec in enumerate(param_records):
            for j, k in enumerate(keys):
                matrix[i, j] = rec.get(k, 0.0)
        return matrix

    def _build_bifurcation_map(
        self,
        param_matrix: np.ndarray,
        labels: np.ndarray,
        feature_matrix: np.ndarray,
    ) -> dict:
        """
        Entrena un Random Forest para predecir cluster desde parámetros
        y extrae importancias.
        """
        n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
        if n_clusters < 2:
            return {"param_importances": {}, "transition_costs": []}

        mask = labels != -1
        if mask.sum() < 10:
            return {"param_importances": {}, "transition_costs": []}

        X_params = param_matrix[mask]
        y = labels[mask]

        self._rf = RandomForestClassifier(
            n_estimators=min(200, 100 * (n_clusters - 1)),
            max_depth=5,
            random_state=self.random_state,
            class_weight="balanced",
        )
        self._rf.fit(X_params, y)

        # Normalizar importancias
        importances = self._rf.feature_importances_
        imp_sum = importances.sum() or 1.0
        importances = importances / imp_sum

        param_keys = ["coupling", "external_pressure", "initial_noise"]

        # Matriz de transición entre clusters
        n = n_clusters
        transition_costs = []
        for i in range(n):
            for j in range(i + 1, n):
                mask_i = y == i
                mask_j = y == j
                if mask_i.sum() < 2 or mask_j.sum() < 2:
                    continue
                center_i = X_params[mask_i].mean(axis=0)
                center_j = X_params[mask_j].mean(axis=0)
                # Distancia ponderada por importancia
                diff = (center_i - center_j) ** 2
                weighted_dist = np.sqrt(np.sum(diff * importances))
                transition_costs.append({
                    "from": int(i),
                    "to": int(j),
                    "cost": float(weighted_dist),
                    "params_change": {
                        k: float(center_j[idx] - center_i[idx])
                        for idx, k in enumerate(param_keys[:len(center_i)])
                    },
                })

        return {
            "param_importances": {
                k: float(importances[idx])
                for idx, k in enumerate(param_keys[:len(importances)])
            },
            "transition_costs": sorted(transition_costs, key=lambda x: x["cost"]),
        }

    def describe_families(
        self,
        labels: np.ndarray,
        feature_matrix: np.ndarray,
        param_records: list[dict[str, float]],
    ) -> list[dict]:
        """
        Genera descripciones humanas de cada familia de futuros.

        Args:
            labels: Cluster labels.
            feature_matrix: (n_sims, n_features).
            param_records: Parámetros usados en cada sim.

        Returns:
            Lista de dicts con descripción de cada familia.
        """
        n_sims = feature_matrix.shape[0]
        unique_labels = sorted(set(labels))

        families = []
        for lbl in unique_labels:
            mask = labels == lbl
            n_members = int(mask.sum())
            if n_members < 2:
                continue

            mean_feats = np.mean(feature_matrix[mask], axis=0)
            std_feats = np.std(feature_matrix[mask], axis=0)

            # Parámetros típicos de esta familia
            params_array = np.array([
                [p.get("coupling", 0), p.get("external_pressure", 0),
                 p.get("initial_noise", 0)]
                for p in param_records
            ])
            mean_params = np.mean(params_array[mask], axis=0)

            feat_names = self._get_feature_names(feature_matrix.shape[1])
            mean_dict = {n: float(mean_feats[i]) for i, n in enumerate(feat_names)}

            # Etiqueta humana basada en patrones
            label, desc, risks = self._label_family(mean_dict)

            families.append({
                "id": int(lbl) if lbl >= 0 else -1,
                "size": n_members,
                "proportion": float(n_members / n_sims),
                "label": label,
                "description": desc,
                "mean_features": mean_dict,
                "archetype_params": {
                    "coupling": float(mean_params[0]),
                    "external_pressure": float(mean_params[1]),
                    "initial_noise": float(mean_params[2]),
                },
                "risk_flags": risks,
            })

        # Ordenar por tamaño descendente
        families.sort(key=lambda x: x["size"], reverse=True)
        # Re-asignar IDs
        for i, fam in enumerate(families):
            fam["id"] = i

        return families

    def _get_feature_names(self, n_feats: int) -> list[str]:
        base = [
            "polarization", "hierarchy_mean", "hierarchy_std", "cooperation",
            "trust", "opinion_skew", "stability", "max_polarization",
            "time_to_stabilize", "dim_correlation", "opinion_delta",
            "cooperation_delta", "extreme_fraction",
        ]
        return base[:n_feats]

    def _label_family(
        self, feats: dict[str, float]
    ) -> tuple[str, str, list[str]]:
        """Asigna etiqueta humana a una familia basada en sus features."""
        pol = feats.get("polarization", 0)
        coop = feats.get("cooperation", 0.5)
        trust = feats.get("trust", 0.5)
        hier = feats.get("hierarchy_mean", 0.5)
        hier_std = feats.get("hierarchy_std", 0.2)
        stable = feats.get("stability", 0.5)
        extreme = feats.get("extreme_fraction", 0)
        op_delta = feats.get("opinion_delta", 0)
        time_stab = feats.get("time_to_stabilize", 0.5)
        max_pol = feats.get("max_polarization", pol)

        risks = []
        parts = []

        # 1. Eje principal: polarización
        if pol > 0.55:
            label = "Fragmentación"
            parts.append("division en facciones")
            risks.append(f"Alta polarización (σ={pol:.2f}) → riesgo de ruptura")
        elif pol > 0.35:
            label = "Tensión Moderada"
            parts.append("opiniones diversas sin ruptura")
        elif pol > 0.15:
            label = "Cohesión"
            parts.append("tendencia al acuerdo")
        else:
            label = "Consenso Fuerte"
            parts.append("alineación total")

        # 2. Cooperación
        if coop < 0.3:
            label += " + Bloqueo"
            parts.append("baja cooperación")
            risks.append("Baja cooperación → conflicto latente")
        elif coop > 0.7:
            parts.append("alta colaboración")

        # 3. Jerarquía
        if hier > 0.6 and hier_std < 0.2:
            label += " [Jerárquico]"
            parts.append("estructura jerárquica definida")
        elif hier < 0.3 and hier_std < 0.2:
            label += " [Horizontal]"
            parts.append("estructura plana")

        # 4. Estabilidad
        if stable > 0.05:
            label = "Volátil" if "Fragmentación" not in label else label
            parts.append("dinámica inestable")
            risks.append("Inestabilidad → cambios impredecibles")
        else:
            parts.append("dinámica estable")

        # 5. Confianza
        if trust < 0.3:
            parts.append("desconfianza generalizada")
            risks.append("Desconfianza → comunicación deficiente")
        elif trust > 0.7:
            parts.append("alta confianza")
            risks.append("Exceso de confianza → posible groupthink (Janis, 1972)")

        # 6. Extremos
        if extreme > 0.4:
            risks.append(f"{extreme:.0%} en posiciones extremas → radicalización")

        # 7. Delta de opinión
        if op_delta < 0.05 and pol < 0.2:
            label = "Estancamiento"
            parts = ["el grupo no evoluciona"]
            risks.append("Sin cambio → apatía o anomia (Durkheim, 1893)")

        # 8. Riesgo groupthink
        if pol < 0.15 and trust > 0.7 and hier > 0.6:
            risks.append("Cohesión + jerarquía + confianza → alto riesgo de Groupthink")

        desc = "Grupo con " + ", ".join(parts) + "."
        return label, desc, risks


# ============================================================
# MICRO SOCIAL ARCHITECT
# ============================================================

class MicroSocialArchitect:
    """
    Versión micro del Social Architect.

    En lugar de "encuentra la intervención que lleva al objetivo",
    responde: "qué parámetros cambiar para que el grupo pase de
    la familia de futuros A a la familia B".
    """

    def __init__(self):
        self._last_result: dict | None = None

    def find_transition(
        self,
        families: list[dict],
        bifurcation: dict,
        from_id: int,
        to_id: int,
    ) -> dict:
        """
        Encuentra la transición de parámetros entre dos familias.

        Args:
            families: Lista de familias (de describe_families).
            bifurcation: Mapa de bifurcación (de fit).
            from_id: ID de la familia actual.
            to_id: ID de la familia objetivo.

        Returns:
            Dict con la ruta de transición.
        """
        from_fam = next((f for f in families if f["id"] == from_id), None)
        to_fam = next((f for f in families if f["id"] == to_id), None)

        if not from_fam or not to_fam:
            return {"error": "Familia no encontrada"}

        # Buscar en transition_costs
        costs = bifurcation.get("transition_costs", [])
        transition = next(
            (c for c in costs
             if c["from"] == from_id and c["to"] == to_id),
            None
        )

        if not transition:
            # Calcular directamente
            p_from = from_fam["archetype_params"]
            p_to = to_fam["archetype_params"]
            importances = bifurcation.get("param_importances", {})

            changes = {}
            weighted_dist = 0.0
            for k in p_from:
                diff = p_to[k] - p_from[k]
                changes[k] = round(diff, 4)
                w = importances.get(k, 1.0 / max(len(p_from), 1))
                weighted_dist += w * diff ** 2
            weighted_dist = np.sqrt(weighted_dist)

            transition = {
                "from": from_id,
                "to": to_id,
                "cost": float(weighted_dist),
                "params_change": changes,
            }

        # Generar recomendación
        imp = bifurcation.get("param_importances", {})
        sorted_params = sorted(imp.items(), key=lambda x: -x[1])

        recommendation = (
            f"Para pasar de '{from_fam['label']}' a '{to_fam['label']}':\n"
        )
        for param, importance in sorted_params:
            change = transition.get("params_change", {}).get(param, 0)
            direction = "aumentar" if change > 0 else "reducir"
            recommendation += (
                f"  - {direction} '{param}' en {abs(change):.3f} "
                f"(importancia: {importance:.2f})\n"
            )

        transition["recommendation"] = recommendation
        transition["from_label"] = from_fam["label"]
        transition["to_label"] = to_fam["label"]

        self._last_result = transition
        return transition

    def suggest_narrative(self, transition: dict) -> str:
        """
        Genera una narrativa humana de la transición.

        Args:
            transition: Dict de find_transition.

        Returns:
            Texto explicativo.
        """
        if "error" in transition:
            return f"No se pudo calcular: {transition['error']}"

        changes = transition.get("params_change", {})
        parts = []
        for k, v in changes.items():
            label_map = {
                "coupling": "la frecuencia de comunicación",
                "external_pressure": "la presión externa sobre el grupo",
                "initial_noise": "la incertidumbre inicial en las relaciones",
            }
            param_label = label_map.get(k, k)
            action = "aumentar" if v > 0 else "reducir"
            parts.append(f"{action} {param_label} ({abs(v):.1%})")

        if not parts:
            return "No hay cambios paramétricos significativos entre estas familias."

        return (
            f"Para que el grupo transicione de '{transition['from_label']}' "
            f"a '{transition['to_label']}', la intervención clave es:\n"
            + "\n".join(f"  • {p}" for p in parts)
            + f"\n\nCosto estimado de transición: {transition['cost']:.3f} "
            "(a menor costo, más factible el cambio)."
        )


# ============================================================
# ORQUESTADOR COMPLETO
# ============================================================

def analyze_group(
    profile: Any,
    n_simulations: int = 500,
    steps_per_sim: int = 200,
    n_clusters: int = 0,
    variations: list[dict] | None = None,
    seed: int = 42,
    use_dask: bool = True,
    quiet: bool = False,
) -> dict:
    """
    Función de alto nivel: orquesta el flujo completo.

    1. Ejecuta ensemble de simulaciones
    2. Extrae features y clusteriza en familias de futuros
    3. Identifica parámetros de bifurcación
    4. Prepara el Micro Social Architect

    Args:
        profile: GroupProfile configurado.
        n_simulations: Número de simulaciones en el ensemble.
        steps_per_sim: Pasos por simulación.
        n_clusters: Número de clusters (0 = auto).
        variations: Variaciones paramétricas personalizadas.
        seed: Semilla RNG.
        use_dask: Usar paralelización Dask.
        quiet: Suprimir logs.

    Returns:
        Dict con: families, bifurcation, architect, feature_matrix, labels.
    """
    if not SKLEARN_AVAILABLE:
        raise ImportError(
            "scikit-learn es necesario para Micro. "
            "Instálalo con: pip install scikit-learn"
        )

    # 1. Ensemble
    orch = MicroSimOrchestrator(quiet=quiet)
    trajectories, feature_matrix, param_records = orch.run_ensemble(
        profile=profile,
        n_simulations=n_simulations,
        steps_per_sim=steps_per_sim,
        variations=variations,
        seed=seed,
        use_dask=use_dask,
    )

    # 2. Clusterización y bifurcación
    analyzer = FamilyOfFuturesAnalyzer(n_clusters=n_clusters, random_state=seed)
    labels, bifurcation = analyzer.fit(feature_matrix, param_records)

    # 3. Descripción de familias
    families = analyzer.describe_families(labels, feature_matrix, param_records)

    # 4. Social Architect micro
    architect = MicroSocialArchitect()

    return {
        "families": families,
        "bifurcation": bifurcation,
        "architect": architect,
        "feature_matrix": feature_matrix,
        "labels": labels,
        "param_records": param_records,
        "n_simulations": n_simulations,
        "trajectories": trajectories,
    }
