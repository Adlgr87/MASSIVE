"""
MASSIVE Simulator Core

Módulos refactorizados del núcleo de simulación.
Ver simulator.py para interfaz pública legacy (backward-compatible).
"""

# Importar funciones principales del motor de simulación
from simulator_core.simulation_engine import (
    simular,
    simular_multiples,
    resumen_historial,
    save_checkpoint,
    load_checkpoint,
    get_graph_metrics,
)

# Importar configuración
from simulator_core.config import (
    # Empirical configuration (unified - fixes duplicate import bug)
    MASSIVE_EMPIRICAL_MASTER,
    MASSIVE_RUNTIME_PARAMS,
    ENGINE_METADATA_KEYS,
    apply_empirical_profile,
    build_empirical_engine_config,
    EMPIRICAL_AVAILABLE,
    
    # Optional dependencies availability flags
    TDA_AVAILABLE,
    EXTENDED_MODELS_AVAILABLE,
    CFC_AVAILABLE,
    
    # Range helpers
    clip_to_unit_interval,
    normalize_opinion,
    opinion_range_clip,
)

# Importar reglas de dinámica
from simulator_core.dynamics_rules.basic import (
    regla_lineal,
    regla_umbral,
    regla_memoria,
    regla_backlash,
    regla_polarizacion,
)

from simulator_core.dynamics_rules.advanced import (
    regla_hk,
    regla_contagio_competitivo,
    regla_umbral_heterogeneo,
    regla_homofilia,
    regla_replicador,
    calculate_ews_metrics,
    check_ews_signals,
)

from simulator_core.dynamics_rules.social import (
    calcular_efecto_grupos,
    validar_coalicion,
    influencia_grupos,
    calcular_presion_social,
)

# Importar integración LLM
from simulator_core.llm_integration import (
    llamar_llm,
    llamar_llm_heuristico,
    construir_prompt,
    extraer_json,
)

# Importar utils
from simulator_core.utils import (
    generate_simulation_id,
    validate_opinion_range,
    is_converged,
    consensus_metric,
    polarization_index,
)

# GamePayoff se importa directamente de schemas para evitar circular imports
from schemas import GamePayoff

# Strategic force wrapper
from simulator_core.config import calculate_strategic_force_wrapper

# IntegratedSimulator y scheduler - temporalmente comentado hasta crear el módulo
# from simulator_core.integrated_simulator import (
#     IntegratedSimulator,
#     run_with_schedule,
# )

__all__ = [
    # Funciones principales de simulación
    'simular',
    'simular_multiples',
    'resumen_historial',
    'save_checkpoint',
    'load_checkpoint',
    'get_graph_metrics',
    
    # Empirical config
    'MASSIVE_EMPIRICAL_MASTER',
    'MASSIVE_RUNTIME_PARAMS',
    'ENGINE_METADATA_KEYS',
    'apply_empirical_profile',
    'build_empirical_engine_config',
    'EMPIRICAL_AVAILABLE',
    
    # Availability flags
    'TDA_AVAILABLE',
    'EXTENDED_MODELS_AVAILABLE',
    'CFC_AVAILABLE',
    
    # Reglas básicas
    'regla_lineal',
    'regla_umbral',
    'regla_memoria',
    'regla_backlash',
    'regla_polarizacion',
    
    # Reglas avanzadas
    'regla_hk',
    'regla_contagio_competitivo',
    'regla_umbral_heterogeneo',
    'regla_homofilia',
    'regla_replicador',
    'calculate_ews_metrics',
    'check_ews_signals',
    
    # Funciones sociales
    'calcular_efecto_grupos',
    'validar_coalicion',
    'influencia_grupos',
    'calcular_presion_social',
    
    # LLM integration
    'llamar_llm',
    'llamar_llm_heuristico',
    'construir_prompt',
    'extraer_json',
    
    # Utils
    'generate_simulation_id',
    'validate_opinion_range',
    'is_converged',
    'consensus_metric',
    'polarization_index',
    
    # Strategic
    'calculate_strategic_force_wrapper',
    'GamePayoff',
    
    # Integrated simulator - temporalmente comentado
    # 'IntegratedSimulator',
    # 'run_with_schedule',
]
