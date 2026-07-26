# 📋 PLAN DE REFACTORIZACIÓN - simulator.py (Fase 2)

## 🎯 OBJETIVO
Dividir `simulator.py` (2,242 líneas) en módulos especializados manteniendo **compatibilidad hacia atrás total** para evitar romper código existente.

---

## 📊 DIAGNÓSTICO ACTUAL

### Estructura Actual de simulator.py:
- **Líneas:** 2,242
- **Clases:** 1 (`IntegratedSimulator`)
- **Funciones:** ~30 funciones principales
- **Dependencias críticas:** 
  - Doble import de `empirical_config` (líneas 55-62, 90) ⚠️
  - Imports condicionales (TDA, extended models, CfC)
  - Múltiples secciones bien definidas

### Secciones Identificadas:
1. **Configuración y Constantes** (líneas 1-277) - ~277 líneas
2. **Helpers de Rango** (líneas 284-300) - ~17 líneas
3. **Fuerza Estratégica** (líneas 310-430) - ~121 líneas
4. **Reglas de Dinámica** (líneas 431-750) - ~320 líneas
   - lineal, umbral, memoria, backlash, polarizacion
   - hk, contagio_competitivo, umbral_heterogeneo, homofilia
5. **Early Warning Signals** (líneas 751-817) - ~67 líneas
6. **Replicator Equation** (líneas 818-910) - ~93 líneas
7. **Topological Analysis** (líneas 911-1034) - ~124 líneas
8. **Validación y Prompt LLM** (líneas 1035-1149) - ~115 líneas
9. **LLM Helpers** (líneas 1150-1259) - ~110 líneas
10. **Selector Heurístico** (líneas 1260-1354) - ~95 líneas
11. **Efecto Grupos** (líneas 1355-1378) - ~24 líneas
12. **Simulador Principal** (líneas 1379-1569) - ~191 líneas
13. **Simulación Múltiple** (líneas 1570-1714) - ~145 líneas
14. **Utilidades** (líneas 1715-1877) - ~163 líneas
   - resumen, checkpoints, graph metrics
15. **IntegratedSimulator Class** (líneas 1878-2105) - ~228 líneas
16. **Run With Schedule** (líneas 2106-fin) - ~137 líneas

---

## 🏗️ ESTRATEGIA DE REFACTORIZACIÓN

### Principios Rectores:
1. ✅ **Compatibilidad hacia atrás total**: El archivo `simulator.py` original seguirá existiendo
2. ✅ **Re-exports automáticos**: Usar `__init__.py` para exponer todo desde el mismo namespace
3. ✅ **Migración gradual**: Los imports antiguos seguirán funcionando
4. ✅ **Testing continuo**: Verificar después de cada módulo extraído
5. ✅ **Documentación同步**: Actualizar docs con nueva estructura

### Estructura Propuesta:

```
massive/
├── simulator.py                    # Wrapper legacy (re-exports todo)
├── simulator_core/                 # NUEVO: Módulos refactorizados
│   ├── __init__.py                 # Exporta todo al namespace simulator
│   ├── config.py                   # Configuración y constantes
│   ├── range_helpers.py            # Helpers de rango (_get_rango, _clip, etc.)
│   ├── strategic_layer.py          # Fuerza estratégica y teoría de juegos
│   ├── dynamics_rules/             # NUEVO: Paquete de reglas
│   │   ├── __init__.py
│   │   ├── basic.py                # lineal, umbral, memoria
│   │   ├── advanced.py             # backlash, polarizacion
│   │   ├── social.py               # hk, contagio, umbral_heterogeneo, homofilia
│   │   └── egt.py                  # replicator, nash, bayesiano, sir
│   ├── ews_detection.py            # Early Warning Signals + TDA
│   ├── llm_integration/            # NUEVO: Paquete LLM
│   │   ├── __init__.py
│   │   ├── providers.py            # OpenAI, Ollama, Groq, etc.
│   │   ├── prompt_builder.py       # Construcción de prompts
│   │   └── heuristic_selector.py   # Selector heurístico
│   ├── simulation_engine.py        # simular(), simular_multiples()
│   ├── integrated_simulator.py     # Clase IntegratedSimulator
│   └── utils.py                    # Checkpoints, resumen, graph metrics
└── tests/
    └── test_simulator_refactor.py  # Tests de compatibilidad
```

---

## 📝 PLAN DE EJECUCIÓN PASO A PASO

### **DÍA 1: Preparación y Módulo de Configuración**

#### Paso 1.1: Crear estructura de directorios
```bash
mkdir -p massive/simulator_core/dynamics_rules
mkdir -p massive/simulator_core/llm_integration
mkdir -p massive/tests
```

#### Paso 1.2: Extraer configuración (config.py)
- **Líneas fuente:** 1-277
- **Contenido:** 
  - Docstring inicial
  - Imports básicos (json, logging, numpy, etc.)
  - RANGOS_DISPONIBLES
  - PROVEEDORES
  - DEFAULT_CONFIG
  - DEFAULT_PAYOFF_MATRIX
  - _RANGOS_PARAMS
  - Constantes (_STRATEGIC_POLARIZATION_THRESHOLD, etc.)

#### Paso 1.3: Crear __init__.py principal
- Importar todo desde los módulos
- Exponer mismo namespace que simulator.py original
- Implementar shim de compatibilidad

#### Paso 1.4: Crear wrapper legacy en simulator.py
```python
# simulator.py (nuevo - solo re-exports)
from simulator_core import *
from simulator_core import __all__ as _all

# Mantener todo lo que el código externo espera
__all__ = _all

# Deprecated warning
import warnings
warnings.warn(
    "simulator.py es ahora un wrapper. Importa desde simulator_core directamente.",
    DeprecationWarning,
    stacklevel=2
)
```

---

### **DÍA 2: Helpers y Capa Estratégica**

#### Paso 2.1: Extraer range_helpers.py
- **Líneas fuente:** 284-300
- **Funciones:** _get_rango, _clip, _neutro, _es_bipolar, _amplitud
- **Dependencias:** config.py

#### Paso 2.2: Extraer strategic_layer.py
- **Líneas fuente:** 310-430
- **Funciones:** _calcular_fuerza_estrategica, _aplicar_sesgo_confirmacion, _actualizar_pesos_homofilia
- **Dependencias:** range_helpers.py, config.py

#### Paso 2.3: Tests del Día 2
```python
def test_range_helpers_compatibility():
    # Verificar que funciones importan igual
    from simulator import _clip as old_clip
    from simulator_core.range_helpers import _clip as new_clip
    assert old_clip == new_clip
```

---

### **DÍA 3: Reglas de Dinámica (Parte 1)**

#### Paso 3.1: Extraer dynamics_rules/basic.py
- **Líneas fuente:** 431-535
- **Funciones:** regla_lineal, regla_umbral, regla_memoria
- **Dependencias:** range_helpers.py, strategic_layer.py

#### Paso 3.2: Extraer dynamics_rules/advanced.py
- **Líneas fuente:** 503-622
- **Funciones:** regla_backlash, regla_polarizacion, regla_hk
- **Dependencias:** range_helpers.py, strategic_layer.py

#### Paso 3.3: Tests del Día 3
```python
def test_basic_rules_output():
    # Verificar que reglas producen mismo output
    estado_test = {...}
    old_result = simulator.regla_lineal(estado_test, params, cfg)
    new_result = simulator_core.dynamics_rules.basic.regla_lineal(estado_test, params, cfg)
    assert old_result == new_result
```

---

### **DÍA 4: Reglas de Dinámica (Parte 2) + EWS**

#### Paso 4.1: Extraer dynamics_rules/social.py
- **Líneas fuente:** 623-750
- **Funciones:** regla_contagio_competitivo, regla_umbral_heterogeneo, regla_homofilia

#### Paso 4.2: Extraer dynamics_rules/egt.py
- **Líneas fuente:** 818-910
- **Funciones:** calculate_ews_metrics, check_ews_signals, apply_replicator_equation, regla_replicador

#### Paso 4.3: Extraer ews_detection.py
- **Líneas fuente:** 751-817, 911-1034
- **Funciones:** calculate_ews_metrics, check_ews_signals, detect_topological_change
- **Dependencias:** TDA (ripser, persim) condicional

---

### **DÍA 5: Integración LLM**

#### Paso 5.1: Extraer llm_integration/providers.py
- **Líneas fuente:** 1150-1206
- **Funciones:** _llamar_openai_compatible, _llamar_ollama
- **Dependencias:** resolve_provider_api_key

#### Paso 5.2: Extraer llm_integration/prompt_builder.py
- **Líneas fuente:** 1047-1149
- **Funciones:** _validar_params, _construir_prompt, _extraer_json

#### Paso 5.3: Extraer llm_integration/heuristic_selector.py
- **Líneas fuente:** 1260-1354
- **Funciones:** llamar_llm_heuristico
- **Dependencias:** Todas las reglas

#### Paso 5.4: Actualizar llamar_llm() en providers.py
- **Líneas fuente:** 1207-1259

---

### **DÍA 6: Motor de Simulación**

#### Paso 6.1: Extraer simulation_engine.py
- **Líneas fuente:** 1379-1714
- **Funciones:** simular(), simular_multiples(), simular_multiples_dask()
- **Dependencias:** Todas las reglas, LLM, strategic_layer

#### Paso 6.2: Extraer utils.py
- **Líneas fuente:** 1715-1877
- **Funciones:** resumen_historial, save_checkpoint, load_checkpoint, get_graph_metrics

#### Paso 6.3: Tests del Día 6
```python
def test_simular_backward_compatibility():
    # Ejecutar simulación completa y comparar resultados
    old_result = simulator.simular(config_old)
    new_result = simulator_core.simulation_engine.simular(config_new)
    assert np.allclose(old_result['historial'], new_result['historial'])
```

---

### **DÍA 7: Clase IntegratedSimulator + Finalización**

#### Paso 7.1: Extraer integrated_simulator.py
- **Líneas fuente:** 1878-2105
- **Clase:** IntegratedSimulator
- **Dependencias:** simulation_engine, ews_detection, utils

#### Paso 7.2: Extraer run_with_schedule()
- **Líneas fuente:** 2106-fin
- **Funciones:** run_with_schedule()

#### Paso 7.3: Consolidar __init__.py final
```python
# simulator_core/__init__.py
from .config import *
from .range_helpers import *
from .strategic_layer import *
from .dynamics_rules.basic import *
from .dynamics_rules.advanced import *
from .dynamics_rules.social import *
from .dynamics_rules.egt import *
from .ews_detection import *
from .llm_integration.providers import *
from .llm_integration.prompt_builder import *
from .llm_integration.heuristic_selector import *
from .simulation_engine import *
from .integrated_simulator import *
from .utils import *

__all__ = [
    # Config
    'DEFAULT_CONFIG', 'RANGOS_DISPONIBLES', 'PROVEEDORES',
    # Helpers
    '_clip', '_neutro', '_get_rango', '_amplitud', '_es_bipolar',
    # Strategic
    '_calcular_fuerza_estrategica', '_aplicar_sesgo_confirmacion',
    # Rules
    'regla_lineal', 'regla_umbral', 'regla_memoria', 'regla_backlash',
    'regla_polarizacion', 'regla_hk', 'regla_contagio_competitivo',
    'regla_umbral_heterogeneo', 'regla_homofilia', 'regla_replicador',
    # EWS
    'calculate_ews_metrics', 'check_ews_signals', 'detect_topological_change',
    # LLM
    'llamar_llm', 'llamar_llm_heuristico', '_construir_prompt',
    # Simulation
    'simular', 'simular_multiples', 'simular_multiples_dask',
    # Utils
    'resumen_historial', 'save_checkpoint', 'load_checkpoint', 'get_graph_metrics',
    # Classes
    'IntegratedSimulator',
    # Main
    'run_with_schedule',
]
```

#### Paso 7.4: Testing final exhaustivo
```bash
python -m pytest tests/test_simulator_refactor.py -v
python -m pytest tests/test_simulator.py -v  # Tests originales
```

---

## 🔧 DETALLES TÉCNICOS CRÍTICOS

### 1. Manejo de Imports Circulares
**Problema:** Algunos módulos pueden necesitar referencias cruzadas.

**Solución:**
```python
# En dynamics_rules/basic.py
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from simulator_core.strategic_layer import _calcular_fuerza_estrategica

def regla_lineal(estado, params, cfg):
    # Import local para evitar circular
    from simulator_core.strategic_layer import _calcular_fuerza_estrategica
    ...
```

### 2. Compatibilidad de Namespace
**Estrategia:** El `simulator.py` legacy hará:
```python
# simulator.py (wrapper legacy)
import sys
from simulator_core import *

# Inyectar todo en el namespace global
current_module = sys.modules[__name__]
for name, obj in globals().items():
    if not name.startswith('_'):
        setattr(current_module, name, obj)

# Warn una sola vez
import warnings
if not hasattr(current_module, '_refactor_warning_shown'):
    warnings.warn(
        "simulator.py está siendo migrado a simulator_core. "
        "El código funcionará pero actualiza tus imports gradualmente.",
        FutureWarning,
        stacklevel=2
    )
    current_module._refactor_warning_shown = True
```

### 3. Manejo de Dependencias Condicionales
**Problema:** TDA, extended models, CfC son opcionales.

**Solución:**
```python
# En ews_detection.py
try:
    from ripser import ripser as ripser_compute
    TDA_AVAILABLE = True
except ImportError:
    TDA_AVAILABLE = False
    TDA_AVAILABLE = False  # Mantener compatibilidad

def detect_topological_change(...):
    if not TDA_AVAILABLE:
        log.warning("TDA no disponible")
        return None
    # ... implementación normal
```

### 4. Fix de Doble Import (Issue #5)
**Problema actual:**
```python
# Línea 55-61
from empirical_calibration import (
    MASSIVE_EMPIRICAL_MASTER,
    MASSIVE_RUNTIME_PARAMS,
    ...
)
# Línea 62
from empirical_config import MASSIVE_EMPIRICAL_MASTER, MASSIVE_RUNTIME_PARAMS
```

**Solución en config.py:**
```python
# Unificar en un solo lugar
try:
    from empirical_config import (
        MASSIVE_EMPIRICAL_MASTER,
        MASSIVE_RUNTIME_PARAMS,
        EMPIRICAL_BASE_LOADED,
    )
    EMPIRICAL_AVAILABLE = True
except ImportError:
    MASSIVE_EMPIRICAL_MASTER = {}
    MASSIVE_RUNTIME_PARAMS = {}
    EMPIRICAL_AVAILABLE = False
    EMPIRICAL_BASE_LOADED = False

__all__ = ['MASSIVE_EMPIRICAL_MASTER', 'MASSIVE_RUNTIME_PARAMS', 'EMPIRICAL_AVAILABLE']
```

---

## ✅ CRITERIOS DE ACEPTACIÓN

### Funcionales:
- [ ] Todos los tests originales pasan sin modificación
- [ ] `from simulator import X` funciona igual que antes
- [ ] No hay regresión en performance (< 5% overhead)
- [ ] Doble import de empirical_config eliminado

### Técnicos:
- [ ] Cada módulo < 500 líneas
- [ ] Documentación actualizada en cada módulo
- [ ] Type hints completos en todas las funciones públicas
- [ ] Coverage de tests > 85%

### Migración:
- [ ] README actualizado con nueva estructura
- [ ] Guía de migración creada (SIMULATOR_MIGRATION_GUIDE.md)
- [ ] Deprecation warnings claros pero no intrusivos
- [ ] Scripts de ejemplo actualizados

---

## 🚨 RIESGOS Y MITIGACIÓN

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Romper imports existentes | Media | Alto | Wrapper legacy mantiene compatibilidad total |
| Imports circulares | Alta | Medio | Usar TYPE_CHECKING + imports locales |
| Pérdida de performance | Baja | Medio | Profiling antes/después, optimizar si > 5% |
| Confusión de developers | Media | Bajo | Documentación clara + warnings amigables |
| Tests fallan por paths | Media | Alto | Tests verifican ambos namespaces |

---

## 📅 CRONOGRAMA ESTIMADO

| Día | Entregable | Horas estimadas |
|-----|-----------|-----------------|
| 1 | Estructura + config.py | 6h |
| 2 | range_helpers + strategic_layer | 6h |
| 3 | dynamics_rules (basic + advanced) | 8h |
| 4 | dynamics_rules (social + egt) + ews | 8h |
| 5 | llm_integration (3 módulos) | 8h |
| 6 | simulation_engine + utils | 6h |
| 7 | integrated_simulator + testing final | 8h |
| **Total** | | **50 horas** |

---

## 🧪 TESTING STRATEGY

### Tests de Compatibilidad:
```python
# tests/test_refactor_compatibility.py

def test_all_exports_available():
    """Verificar que todo lo exportado antes sigue disponible"""
    import simulator
    import simulator_core
    
    old_exports = [name for name in dir(simulator) if not name.startswith('_')]
    new_exports = [name for name in dir(simulator_core) if not name.startswith('_')]
    
    missing = set(old_exports) - set(new_exports)
    assert not missing, f"Faltan exports: {missing}"

def test_function_identity():
    """Verificar que funciones son idénticas"""
    from simulator import simular as old_simular
    from simulator_core.simulation_engine import simular as new_simular
    
    # Misma firma
    import inspect
    old_sig = inspect.signature(old_simular)
    new_sig = inspect.signature(new_simular)
    assert str(old_sig) == str(new_sig)

def test_simulation_results_match():
    """Verificar que resultados son idénticos"""
    config = {...}  # Config de test
    
    result_old = simulator.simular(config)
    result_new = simulator_core.simulation_engine.simular(config)
    
    assert np.allclose(
        result_old['historial'], 
        result_new['historial'],
        rtol=1e-10
    )
```

### Tests de Regresión:
```bash
# Ejecutar tests originales
pytest tests/test_simulator.py -v

# Ejecutar tests nuevos de compatibilidad
pytest tests/test_refactor_compatibility.py -v

# Ejecutar tests de integración
pytest tests/test_integrated_simulator.py -v
```

---

## 📚 DOCUMENTACIÓN A GENERAR

1. **SIMULATOR_REFACTOR_OVERVIEW.md** - Visión general
2. **SIMULATOR_MIGRATION_GUIDE.md** - Guía de migración paso a paso
3. **simulator_core/README.md** - Documentación de cada módulo
4. **API_REFERENCE.md** - Referencia completa de API
5. **CHANGELOG.md** - Registro de cambios breaking/non-breaking

---

## ✨ BENEFICIOS ESPERADOS

1. **Mantenibilidad:** Archivos de 300-500 líneas vs 2,242
2. **Testabilidad:** Tests unitarios por módulo específico
3. **Colaboración:** Múltiples devs pueden trabajar en módulos separados
4. **Performance:** Posible optimización al aislar hot paths
5. **Claridad:** Nombres de módulos auto-explicativos
6. **Flexibilidad:** Reemplazar módulos individuales sin afectar todo

---

## 🔄 POST-REFACTOR OPTIMIZACIONES (Fase 3+)

Una vez completada la refactorización:
1. Profile de cada módulo para identificar bottlenecks
2. Vectorización de operaciones numpy en reglas
3. Cacheo de resultados intermedios
4. Parallelización de simular_multiples
5. Lazy loading de módulos pesados (TDA, LLM)

---

**¿Listo para comenzar?** Comenzaré con el **DÍA 1: Preparación y Módulo de Configuración** una vez des luz verde.
