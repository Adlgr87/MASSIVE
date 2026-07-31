"""
Motor principal de simulación MASSIVE.

Este módulo contiene las funciones core simular() y simular_multiples(),
que ejecutan la dinámica de opiniones basada en reglas seleccionadas
por LLM o heurística.
"""

import numpy as np
from typing import Dict, Any, List, Optional, Tuple, Callable
import logging
from pathlib import Path
import json

# Imports internos del paquete simulator_core
from .config import (
    _get_rango as get_rango_config,
    clip_to_unit_interval as config_clip,
    TDA_AVAILABLE,
    EXTENDED_MODELS_AVAILABLE,
    CFC_AVAILABLE,
    EMPIRICAL_AVAILABLE,
)

# Definir constantes locales que antes estaban en simulator.py
RANGOS_DISPONIBLES = {
    "[0, 1] — Probabilístico": {
        "min": 0.0, "max": 1.0, "neutro": 0.5,
        "descripcion": "Opinión como probabilidad de apoyo. Neutro=0.5. Modelos SIR, adopción.",
        "ejemplo_apoyo": 0.8, "ejemplo_rechazo": 0.2, "ejemplo_neutro": 0.5,
        "defaults": {
            "opinion_inicial": 0.50, "propaganda": 0.70, "confianza": 0.40,
            "opinion_grupo_a": 0.72, "opinion_grupo_b": 0.28,
        },
    },
    "[-1, 1] — Bipolar": {
        "min": -1.0, "max": 1.0, "neutro": 0.0,
        "descripcion": "Rechazo activo en negativo. Neutro=0. Polarización, campañas, elecciones.",
        "ejemplo_apoyo": 0.7, "ejemplo_rechazo": -0.7, "ejemplo_neutro": 0.0,
        "defaults": {
            "opinion_inicial": 0.00, "propaganda": 0.40, "confianza": 0.40,
            "opinion_grupo_a": 0.65, "opinion_grupo_b": -0.55,
        },
    },
}

DEFAULT_CONFIG = {
    # Rango
    "rango": "[0, 1] — Probabilístico",
    # LLM
    "proveedor": "heurístico",
    "modelo": "",
    "api_key": "",
    "ollama_host": "http://localhost:11434",
    "llm_timeout": 20,
    "llm_temperature": 0.0,
    # Motor
    "alpha_blend": 0.8,
    "ruido_base": 0.03,
    "ruido_desconfianza": 0.08,
    "efecto_vecinos_peso": 0.05,
    "ventana_historial_llm": 6,
    # Simulación múltiple
    "ruido_estado_inicial": 0.01,
    # ── Nuevos mecanismos ──────────────────────────────────
    # Sesgo de confirmación: propaganda contraria pierde peso
    # 0.0 = sin sesgo | 1.0 = sesgo total (ignora información contraria)
    "sesgo_confirmacion": 0.3,
    # HK — Confianza Acotada
    # Solo se escucha a quienes están a ≤ epsilon de distancia
    "hk_epsilon": 0.3,
}

# Registry de reglas - se llena dinámicamente
REGLAS = {}

# Importar reglas y registrarlas
from .dynamics_rules.basic import (
    regla_lineal,
    regla_umbral,
    regla_memoria,
    regla_backlash,
    regla_polarizacion,
)
from .dynamics_rules.advanced import (
    regla_hk,
    regla_contagio_competitivo,
    regla_umbral_heterogeneo,
    regla_homofilia,
    regla_replicador,
    calculate_ews_metrics,
    check_ews_signals,
)
from .llm_integration import (
    llamar_llm,
    llamar_llm_heuristico,
)

# Registrar reglas básicas
REGLAS["lineal"] = regla_lineal
REGLAS["umbral"] = regla_umbral
REGLAS["memoria"] = regla_memoria
REGLAS["backlash"] = regla_backlash
REGLAS["polarizacion"] = regla_polarizacion

# Registrar reglas avanzadas
REGLAS["hk"] = regla_hk
REGLAS["contagio_competitivo"] = regla_contagio_competitivo
REGLAS["umbral_heterogeneo"] = regla_umbral_heterogeneo
REGLAS["homofilia"] = regla_homofilia
REGLAS["replicador"] = regla_replicador

# Extended models (si disponibles)
try:
    from extended_models import regla_nash, regla_bayesiana, regla_sir
    REGLAS["nash"] = regla_nash
    REGLAS["bayesiana"] = regla_bayesiana
    REGLAS["sir"] = regla_sir
except ImportError:
    pass

log = logging.getLogger("massive")


def _get_rango(cfg: dict) -> dict:
    """Obtiene la configuración del rango de opinión."""
    return RANGOS_DISPONIBLES.get(cfg.get("rango", "[0, 1] — Probabilístico"), RANGOS_DISPONIBLES["[0, 1] — Probabilístico"])


def _clip(val: float, cfg: dict) -> float:
    """Clippea un valor al rango configurado."""
    rango = _get_rango(cfg)
    return max(rango["min"], min(rango["max"], val))


def _neutro(cfg: dict) -> float:
    """Obtiene el valor neutro del rango configurado."""
    return _get_rango(cfg)["neutro"]


def _es_bipolar(cfg: dict) -> bool:
    """Verifica si el rango es bipolar [-1, 1]."""
    return "Bipolar" in cfg.get("rango", "")


def _amplitud(cfg: dict) -> float:
    """Calcula la amplitud del rango."""
    rango = _get_rango(cfg)
    return rango["max"] - rango["min"]


def _calcular_fuerza_estrategica(estado: dict, cfg: dict) -> float:
    """
    Calcula fuerza estratégica basada en utilidad esperada.
    
    Esta función integra con utility_logic si está disponible.
    """
    try:
        from utility_logic import calculate_strategic_force
        return calculate_strategic_force(estado, cfg)
    except ImportError:
        # Fallback simple si utility_logic no está disponible
        opinion = estado.get("opinion", _neutro(cfg))
        propaganda = estado.get("propaganda", _neutro(cfg))
        return (opinion + propaganda) / 2.0


def _aplicar_sesgo_confirmacion(propaganda: float, opinion: float,
                                 sesgo: float, cfg: dict) -> float:
    """
    Aplica sesgo de confirmación: propaganda contraria pierde peso.
    
    Args:
        propaganda: Valor de propaganda
        opinion: Opinión actual del agente
        sesgo: Intensidad del sesgo (0.0 a 1.0)
        cfg: Configuración
        
    Returns:
        Propaganda ajustada por sesgo
    """
    neutro = _neutro(cfg)
    
    # Determinar si la propaganda es congruente o contraria
    if _es_bipolar(cfg):
        # En bipolar: mismo signo = congruente
        congruente = (propaganda * opinion) >= 0
    else:
        # En [0,1]: ambos > 0.5 o ambos < 0.5 = congruente
        congruente = (propaganda > neutro and opinion > neutro) or \
                     (propaganda < neutro and opinion < neutro)
    
    if congruente:
        # Sesgo refuerza propaganda congruente
        factor = 1.0 + sesgo * 0.5
    else:
        # Sesgo atenúa propaganda contraria
        factor = 1.0 - sesgo
    
    return propaganda * factor


def _actualizar_pesos_homofilia(estado: dict, cfg: dict) -> float:
    """
    Actualiza pesos de red basados en homofilia.
    
    Los agentes similares se conectan más fuertemente.
    """
    opinion = estado.get("opinion", _neutro(cfg))
    confianza = estado.get("confianza", 0.5)
    
    # Homofilia básica: similaridad aumenta conexión
    return confianza * (1.0 - abs(opinion - _neutro(cfg)) / (_amplitud(cfg) / 2))


def _seleccionar_regla(estado: dict, escenario: str, historial_reciente: list, cfg: dict) -> str:
    """
    Selecciona la regla de dinámica a aplicar.
    
    Usa LLM si está configurado,否则 usa heurística.
    """
    proveedor = cfg.get("proveedor", "heurístico")
    
    if proveedor == "heurístico":
        resultado = llamar_llm_heuristico(estado, escenario, historial_reciente, cfg)
        return resultado.get("regla", "lineal")
    else:
        # Intentar con LLM
        resultado = llamar_llm(estado, escenario, historial_reciente, cfg)
        if resultado and "regla" in resultado:
            return resultado["regla"]
        # Fallback a heurística si LLM falla
        log.warning("LLM falló, usando heurística como fallback")
        resultado = llamar_llm_heuristico(estado, escenario, historial_reciente, cfg)
        return resultado.get("regla", "lineal")


def simular(
    opinion_inicial: float = 0.5,
    pasos: int = 100,
    params: dict | None = None,
    config: dict | None = None,
    guardar_historial: bool = True,
    semilla: int | None = None,
    escenario: str = "genérico",
    intervalo_historial: int = 1,
) -> list[dict] | dict[str, Any]:
    """
    Ejecuta una simulación de dinámica de opiniones.
    
    Args:
        opinion_inicial: Opinión inicial del agente o población
        pasos: Número de pasos de simulación
        params: Parámetros específicos de la regla
        config: Configuración general (rango, proveedor LLM, etc.)
        guardar_historial: Si True, devuelve historial completo
        semilla: Semilla para reproducibilidad
        escenario: Descripción del escenario para el selector LLM
        intervalo_historial: Guardar cada N pasos (1 = todos)
        
    Returns:
        Si guardar_historial=True: lista de dicts con estado en cada paso
        Si guardar_historial=False: dict con estado final y metadata
    """
    # Configurar
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    params = params or {}
    
    if semilla is not None:
        np.random.seed(semilla)
    
    # Inicializar estado
    rango = _get_rango(cfg)
    estado = {
        "opinion": float(opinion_inicial),
        "propaganda": cfg.get("propaganda", rango["neutro"]),
        "confianza": cfg.get("confianza", 0.5),
        "pertenencia_grupo": cfg.get("pertenencia_grupo", 0.5),
        "historial_opiniones": [float(opinion_inicial)],
        "paso": 0,
    }
    
    # Verificar TDA si está disponible
    if TDA_AVAILABLE and cfg.get("usar_tda", False):
        log.info("TDA habilitado para detección topológica")
    
    historial = []
    if guardar_historial:
        estado_copy = {k: v for k, v in estado.items() if k != "historial_opiniones"}
        estado_copy["_regla_nombre"] = "inicial"
        historial.append(estado_copy)
    
    # Bucle principal
    for paso in range(pasos):
        estado["paso"] = paso
        
        # Seleccionar regla
        historial_reciente = estado.get("historial_opiniones", [estado["opinion"]])[-cfg.get("ventana_historial_llm", 6):]
        regla_nombre = _seleccionar_regla(estado, escenario, historial_reciente, cfg)
        
        # Obtener función de regla
        if regla_nombre not in REGLAS:
            log.warning(f"Regla '{regla_nombre}' no encontrada, usando 'lineal'")
            regla_nombre = "lineal"
        
        regla_func = REGLAS[regla_nombre]
        
        # Aplicar regla
        try:
            estado = regla_func(estado, params, cfg)
        except Exception as e:
            log.error(f"Error aplicando regla {regla_nombre}: {e}")
            # Fallback a regla lineal
            estado = regla_lineal(estado, params, cfg)
        
        # Clippear valores críticos
        estado["opinion"] = _clip(estado["opinion"], cfg)
        estado["confianza"] = clip_to_unit_interval(estado.get("confianza", 0.5))
        estado["pertenencia_grupo"] = clip_to_unit_interval(estado.get("pertenencia_grupo", 0.5))
        
        # Actualizar historial
        estado["historial_opiniones"].append(estado["opinion"])
        
        # Guardar en historial si corresponde
        if guardar_historial and (paso + 1) % intervalo_historial == 0:
            estado_copy = {k: v for k, v in estado.items() if k != "historial_opiniones"}
            estado_copy["_regla_nombre"] = regla_nombre
            historial.append(estado_copy)
        
        # Verificar EWS si está habilitado
        if cfg.get("usar_ews", False) and len(estado["historial_opiniones"]) >= 10:
            metrics = calculate_ews_metrics(estado["historial_opiniones"][-50:])
            signals = check_ews_signals(metrics, cfg.get("ews_thresholds", {}))
            if any(signals.values()):
                log.warning(f"EWS signals detectados: {signals}")
    
    # Retorno
    if guardar_historial:
        return historial
    else:
        return {
            "estado_final": estado,
            "pasos_completados": pasos,
            "regla_final": regla_nombre,
        }


def simular_multiples(
    n_simulaciones: int = 10,
    opinion_inicial: float | List[float] = 0.5,
    pasos: int = 100,
    params: dict | None = None,
    config: dict | None = None,
    semilla: int | None = None,
    escenario: str = "genérico",
    paralelo: bool = False,
    batch_size: int = 10,
) -> List[list[dict]]:
    """
    Ejecuta múltiples simulaciones en paralelo o secuencia.
    
    Args:
        n_simulaciones: Número de simulaciones a ejecutar
        opinion_inicial: Opinión inicial (float o lista de floats)
        pasos: Pasos por simulación
        params: Parámetros de reglas
        config: Configuración general
        semilla: Semilla base (se incrementa para cada simulación)
        escenario: Escenario para todas las simulaciones
        paralelo: Si True, intenta ejecutar en paralelo
        batch_size: Tamaño de batch para procesamiento paralelo
        
    Returns:
        Lista de historiales, uno por simulación
    """
    cfg = {**DEFAULT_CONFIG, **(config or {})}
    params = params or {}
    
    # Determinar opiniones iniciales
    if isinstance(opinion_inicial, (int, float)):
        opiniones = [float(opinion_inicial)] * n_simulaciones
    elif isinstance(opinion_inicial, list):
        if len(opinion_inicial) != n_simulaciones:
            raise ValueError(
                f"opinion_inicial debe tener {n_simulaciones} elementos, "
                f"pero tiene {len(opinion_inicial)}"
            )
        opiniones = [float(o) for o in opinion_inicial]
    else:
        raise TypeError("opinion_inicial debe ser float o lista de floats")
    
    # Función para ejecutar una simulación
    def run_single(idx: int, opinion: float) -> list[dict]:
        sim_seed = None if semilla is None else semilla + idx
        return simular(
            opinion_inicial=opinion,
            pasos=pasos,
            params=params,
            config=cfg,
            guardar_historial=True,
            semilla=sim_seed,
            escenario=escenario,
        )
    
    # Ejecutar
    if paralelo and n_simulaciones > batch_size:
        # Ejecución paralela (requiere joblib o similar)
        try:
            from joblib import Parallel, delayed
            resultados = Parallel(n_jobs=-1)(
                delayed(run_single)(idx, op) 
                for idx, op in enumerate(opiniones)
            )
        except ImportError:
            log.warning("joblib no disponible, ejecutando en secuencia")
            resultados = [run_single(idx, op) for idx, op in enumerate(opiniones)]
    else:
        # Ejecución secuencia
        resultados = [run_single(idx, op) for idx, op in enumerate(opiniones)]
    
    return resultados


def resumen_historial(historial: list[dict], config: dict | None = None) -> dict:
    """
    Genera un resumen estadístico del historial de simulación.
    
    Args:
        historial: Historial de estados desde simular()
        config: Configuración para interpretación
        
    Returns:
        Diccionario con métricas resumidas
    """
    if not historial:
        return {"error": "Historial vacío"}
    
    cfg = config or DEFAULT_CONFIG
    opiniones = [h.get("opinion", 0.5) for h in historial]
    
    # Métricas básicas
    resumen = {
        "pasos_totales": len(historial),
        "opinion_inicial": opiniones[0],
        "opinion_final": opiniones[-1],
        "opinion_promedio": float(np.mean(opiniones)),
        "opinion_std": float(np.std(opiniones)),
        "opinion_min": float(np.min(opiniones)),
        "opinion_max": float(np.max(opiniones)),
        "cambio_total": opiniones[-1] - opiniones[0],
    }
    
    # Reglas utilizadas
    reglas_usadas = [h.get("_regla_nombre", "desconocida") for h in historial if "_regla_nombre" in h]
    if reglas_usadas:
        from collections import Counter
        conteo_reglas = Counter(reglas_usadas)
        resumen["reglas_utilizadas"] = dict(conteo_reglas)
        resumen["regla_mas_usada"] = conteo_reglas.most_common(1)[0][0]
    
    # Convergencia
    if len(opiniones) >= 10:
        ventana_final = opiniones[-10:]
        resumen["convergencia"] = max(ventana_final) - min(ventana_final)
        resumen["convergio"] = resumen["convergencia"] < 0.01
    
    # Polarización
    resumen["polarizacion"] = 1.0 - (resumen["opinion_std"] * 4)  # Normalizado
    resumen["polarizacion"] = max(0.0, min(1.0, resumen["polarizacion"]))
    
    return resumen


def save_checkpoint(historial: list[dict], filepath: str | Path) -> None:
    """
    Guarda un checkpoint del historial de simulación.
    
    Args:
        historial: Historial a guardar
        filepath: Ruta del archivo
    """
    filepath = Path(filepath)
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(historial, f, indent=2, ensure_ascii=False)
    
    log.info(f"Checkpoint guardado en {filepath}")


def load_checkpoint(filepath: str | Path) -> list[dict]:
    """
    Carga un checkpoint previamente guardado.
    
    Args:
        filepath: Ruta del archivo
        
    Returns:
        Historial cargado
    """
    filepath = Path(filepath)
    
    if not filepath.exists():
        raise FileNotFoundError(f"Checkpoint no encontrado: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        historial = json.load(f)
    
    log.info(f"Checkpoint cargado desde {filepath}")
    return historial


def get_graph_metrics(G, modo: str = "macro", top_n: int = 5) -> str:
    """
    Obtiene métricas de una red NetworkX.
    
    Args:
        G: Grafo NetworkX
        modo: "macro" para resumen, "micro" para detalles
        top_n: Número de nodos top a mostrar
        
    Returns:
        String formateado con métricas
    """
    import networkx as nx
    
    try:
        n_nodos = G.number_of_nodes()
        n_aristas = G.number_of_edges()
        densidad = nx.density(G)
        
        if modo == "macro":
            return (
                f"Red: {n_nodos} nodos, {n_aristas} aristas, "
                f"densidad={densidad:.3f}"
            )
        else:
            # Métricas detalladas
            centralidades = nx.degree_centrality(G)
            top_centrales = sorted(centralidades.items(), key=lambda x: x[1], reverse=True)[:top_n]
            
            metrics_str = f"Red: {n_nodos} nodos, {n_aristas} aristas\n"
            metrics_str += f"Densidad: {densidad:.3f}\n"
            metrics_str += f"Top {top_n} nodos centrales:\n"
            for nodo, cent in top_centrales:
                metrics_str += f"  - {nodo}: {cent:.3f}\n"
            
            return metrics_str
            
    except Exception as e:
        log.error(f"Error calculando métricas de grafo: {e}")
        return f"Error: {e}"
