# Plan de Refactorización de simulator.py

**Estado Actual:** 2,242 líneas (monolito)  
**Objetivo:** Dividir en módulos cohesivos < 500 líneas cada uno  
**Principio Rector:** 100% backward-compatibility (CLAUDE.md: "Surgical Changes")

---

## ✅ Tests de Regresión (NO PUEDEN ROMPERSE)

Estos 5 tests en `tests/test_simulator.py` deben pasar ANTES y DESPUÉS de cada commit:

```bash
cd /workspace/MASSIVE && python -m pytest tests/test_simulator.py -v
```

### Tests Críticos (Bug Fixes Protegidos):
1. **`test_simular_multiples_confianza_stays_non_negative_bipolar`**  
   - Protege fix: `confianza` debe clippearse a [0,1], NO al rango de opinión [-1,1] en modo bipolar
   
2. **`test_simular_multiples_unit_interval_keys_clipped_correctly`**  
   - Protege fix: `pertenencia_grupo` debe clippearse a [0,1]

### Tests de Contrato Funcional:
3. **`test_simular_devuelve_historial_valido`** - Valida longitud (`pasos+1`), rango [0,1], presencia de `_regla_nombre`
4. **`test_resumen_historial_consistente`** - Valida consistencia interna de `resumen_historial()`
5. **`test_efecto_grupos_empuja_hacia_referencia_social`** - Valida signo del efecto de grupos

---

## ⚠️ Zonas de Acoplamiento Crítico (NO TOCAR SIN VERIFICAR)

### 1. Guards de Disponibilidad Opcional (try/except ImportError)
Estos 4 flags controlan ramas enteras de funcionalidad. Si se rompen, la funcionalidad cae silenciosamente al heurístico sin error visible:

```python
TDA_AVAILABLE          # ripser/persim → detección topológica
EXTENDED_MODELS_AVAILABLE  # extended_models → regla_nash, bayesiana, SIR
CFC_AVAILABLE          # cfc_router.CfCRouter → fast-path neuronal
EMPIRICAL_AVAILABLE    # empirical_config → configuración empírica
```

**Riesgo:** Refactorizar imports "para limpiar" puede desactivar estas features silenciosamente.

### 2. Bug de Shadowing Preexistente (Líneas 55-62)
```python
from empirical_calibration import (
    MASSIVE_EMPIRICAL_MASTER, MASSIVE_RUNTIME_PARAMS, ...
)
from empirical_config import MASSIVE_EMPIRICAL_MASTER, MASSIVE_RUNTIME_PARAMS
```
El segundo import **sobreescribe** los nombres del primero. Esto es un bug preexistente que debe documentarse pero NO es parte de este refactor.

### 3. IntegratedSimulator (Clase, No Funciones)
Acoplamiento fuerte con:
- `massive_engine.MassiveEngine`
- `multilayer_engine.MultilayerEngine`
- `massive_core.rust_core.langevin_opinion_update_inplace` (Rust/PyO3 — límite duro de tipos)
- `benchmarks.butterfly_diagnostic.run_butterfly_diagnostic_core`

**Scope:** Esta refactorización NO toca `IntegratedSimulator` a menos que sea estrictamente necesario.

### 4. run_with_schedule()
Usada por `social_architect.py` (Modo Inverso). No tiene cobertura directa en `test_simulator.py`.

**Verificación adicional requerida:** `python -m pytest tests/test_social_architect.py -v` si se toca esta función.

---

## 📦 Dependencias Externas de simulator.py

Archivos que importan desde `simulator`:

### Tests:
- `tests/test_simulator.py` → `calcular_efecto_grupos, resumen_historial, simular, simular_multiples`
- `tests/test_integration_llm.py` → `llamar_llm, simular, DEFAULT_CONFIG`
- `tests/test_integrated_dynamics.py` → `IntegratedSimulator`
- `tests/test_cfc_router.py` → `simular` (3 veces)
- `tests/test_game_theory.py` → `simular` (3 veces)

### Código de Producción:
- `social_architect.py` → `run_with_schedule, resumen_historial, DEFAULT_CONFIG, NOMBRES_REGLAS`

---

## 🏗️ Estructura Propuesta

```
simulator.py                          # Wrapper legacy (re-exporta todo)
simulator_core/
├── __init__.py                       # Exporta todo para backward-compat
├── config.py                         # ~150 líneas: DEFAULT_CONFIG, NOMBRES_REGLAS, helpers de rango
├── range_helpers.py                  # ~80 líneas: _get_rango, _clip, _neutro, _es_bipolar, _amplitud
├── strategic_layer.py                # ~200 líneas: _calcular_fuerza_estrategica, utility_logic integration
├── bias_mechanisms.py                # ~150 líneas: _aplicar_sesgo_confirmacion, _actualizar_pesos_homofilia
├── dynamics_rules/
│   ├── __init__.py
│   ├── basic.py                      # ~400 líneas: regla_lineal, umbral, memoria, backlash, polarizacion
│   ├── advanced.py                   # ~350 líneas: hk, contagio_competitivo, umbral_heterogeneo, homofilia
│   ├── extended.py                   # ~100 líneas: wrapper para regla_nash, bayesiana, SIR (si disponibles)
│   └── replicator.py                 # ~150 líneas: calculate_ews_metrics, check_ews_signals, apply_replicator_equation, regla_replicador
├── ews_detection.py                  # ~200 líneas: detect_topological_change (TDA)
├── llm_integration/
│   ├── __init__.py
│   ├── providers.py                  # ~150 líneas: _llamar_openai_compatible, _llamar_ollama, llamar_llm
│   ├── prompt_builder.py             # ~200 líneas: _construir_prompt, _extraer_json
│   └── heuristic_selector.py         # ~250 líneas: llamar_llm_heuristico, _seleccionar
├── simulation_engine.py              # ~400 líneas: simular, simular_multiples, simular_multiples_dask
├── integrated_simulator.py           # ~300 líneas: class IntegratedSimulator (sin cambios mayores)
├── checkpointing.py                  # ~100 líneas: save_checkpoint, load_checkpoint
├── graph_metrics.py                  # ~100 líneas: get_graph_metrics
└── utils.py                          # ~80 líneas: resumen_historial, calcular_efecto_grupos
```

**Total estimado:** ~3,000 líneas distribuidas en 18 archivos (vs 2,242 en 1 archivo)

---

## 📅 Cronograma Quirúrgico (7 días / commits pequeños)

### Día 1: Fundación + Config
- [ ] Crear `simulator_core/` con `__init__.py` vacío
- [ ] Extraer `config.py`: DEFAULT_CONFIG, NOMBRES_REGLAS, constantes
- [ ] Extraer `range_helpers.py`: _get_rango, _clip, _neutro, _es_bipolar, _amplitud
- [ ] Actualizar `simulator.py` para importar desde `simulator_core`
- [ ] **Verify:** `pytest tests/test_simulator.py -v` ✅

**Commit:** `refactor(simulator): extraer config y range helpers a simulator_core`

### Día 2: Strategic Layer + Bias Mechanisms
- [ ] Extraer `strategic_layer.py`: _calcular_fuerza_estrategica
- [ ] Extraer `bias_mechanisms.py`: _aplicar_sesgo_confirmacion, _actualizar_pesos_homofilia
- [ ] **Verify:** `pytest tests/test_simulator.py -v` ✅

**Commit:** `refactor(simulator): extraer strategic layer y bias mechanisms`

### Día 3: Reglas Básicas (Core del Monolito)
- [ ] Crear `dynamics_rules/__init__.py`
- [ ] Extraer `dynamics_rules/basic.py`: regla_lineal, umbral, memoria, backlash, polarizacion
- [ ] **Verify:** `pytest tests/test_simulator.py::test_simular_devuelve_historial_valido` ✅

**Commit:** `refactor(simulator): mover reglas básicas a dynamics_rules/basic.py`

### Día 4: Reglas Avanzadas + Extended
- [ ] Extraer `dynamics_rules/advanced.py`: hk, contagio_competitivo, umbral_heterogeneo, homofilia
- [ ] Extraer `dynamics_rules/extended.py`: wrappers para nash, bayesiana, SIR (guardando try/except)
- [ ] Extraer `dynamics_rules/replicator.py`: replicador + EWS
- [ ] **Verify:** `pytest tests/test_simulator.py -v` ✅

**Commit:** `refactor(simulator): mover reglas avanzadas y extended a dynamics_rules/`

### Día 5: LLM Integration
- [ ] Crear `llm_integration/__init__.py`
- [ ] Extraer `llm_integration/providers.py`: _llamar_openai_compatible, _llamar_ollama
- [ ] Extraer `llm_integration/prompt_builder.py`: _construir_prompt, _extraer_json
- [ ] Extraer `llm_integration/heuristic_selector.py`: llamar_llm_heuristico, _seleccionar
- [ ] **Verify:** `pytest tests/test_integration_llm.py -v` ✅

**Commit:** `refactor(simulator): extraer integración LLM a llm_integration/`

### Día 6: Simulation Engine + Utils
- [ ] Extraer `simulation_engine.py`: simular, simular_multiples, simular_multiples_dask
- [ ] Extraer `utils.py`: resumen_historial, calcular_efecto_grupos
- [ ] Extraer `checkpointing.py`: save_checkpoint, load_checkpoint
- [ ] Extraer `graph_metrics.py`: get_graph_metrics
- [ ] **Verify:** `pytest tests/test_simulator.py -v` ✅
- [ ] **Verify:** `pytest tests/test_social_architect.py -v` ✅

**Commit:** `refactor(simulator): extraer simulation engine y utilidades`

### Día 7: EWS/TDA + IntegratedSimulator + Testing Final
- [ ] Extraer `ews_detection.py`: detect_topological_change (manteniendo TDA_AVAILABLE guard)
- [ ] Mover `integrated_simulator.py`: class IntegratedSimulator (mínimos cambios)
- [ ] Actualizar `simulator.py` como wrapper que re-exporta todo
- [ ] **Verify:** TODOS los tests relacionados:
  ```bash
  pytest tests/test_simulator.py tests/test_integration_llm.py \
         tests/test_integrated_dynamics.py tests/test_social_architect.py \
         tests/test_cfc_router.py tests/test_game_theory.py -v
  ```
- [ ] Actualizar documentación (README, docs/)

**Commit:** `refactor(simulator): completar refactorización con EWS e IntegratedSimulator`

---

## 🔒 Criterios de Aceptación (Definition of Done)

Para cada commit:

1. ✅ `pytest tests/test_simulator.py -v` pasa (5/5 tests)
2. ✅ No hay cambios en el comportamiento observable (mismos outputs para mismos inputs)
3. ✅ Imports existentes siguen funcionando: `from simulator import X`
4. ✅ Guards de disponibilidad opcional se mantienen intactos
5. ✅ Cada nuevo archivo < 500 líneas
6. ✅ Docstrings Google-style preservados
7. ✅ Tipo de retorno y parámetros sin cambios breaking

Al final del refactor (Día 7):

1. ✅ Todos los tests relacionados pasan (ver lista arriba)
2. ✅ `simulator.py` es un wrapper delgado (< 100 líneas)
3. ✅ Documentación actualizada
4. ✅ No hay regresión de performance (opcional: correr benchmarks)

---

## 🛡️ Estrategia de Backward-Compatibility

### Wrapper Legacy (`simulator.py`):
```python
# simulator.py (después del refactor)
"""Wrapper legacy para backward-compatibility. Todo el código está en simulator_core/."""

from simulator_core import *  # Re-exporta todo
from simulator_core.config import *
from simulator_core.range_helpers import *
from simulator_core.strategic_layer import *
from simulator_core.bias_mechanisms import *
from simulator_core.dynamics_rules import *
from simulator_core.ews_detection import *
from simulator_core.llm_integration import *
from simulator_core.simulation_engine import *
from simulator_core.integrated_simulator import *
from simulator_core.checkpointing import *
from simulator_core.graph_metrics import *
from simulator_core.utils import *

# Mantener exactamente los mismos nombres públicos
__all__ = [...]  # Lista explícita de exports
```

### Por qué funciona:
- Cualquier código que hace `from simulator import X` sigue funcionando
- Los tests no necesitan modificación
- El wrapper puede eliminarse en una próxima versión mayor (v2.0)

---

## 📊 Métricas de Éxito

| Métrica | Antes | Después | Objetivo |
|---------|-------|---------|----------|
| Líneas en simulator.py | 2,242 | < 100 | ✅ |
| Archivo más grande | 2,242 | < 500 | ✅ |
| Tests passing | 5/5 | 5/5 | ✅ |
| Imports rotos | 0 | 0 | ✅ |
| Performance | 1.0x | ≥ 0.95x | ✅ |

---

## 🚨 Rollback Plan

Si algo sale mal en cualquier commit:

```bash
# Revertir último commit manteniendo cambios en working directory
git reset --soft HEAD~1

# O revertir completamente
git reset --hard HEAD~1

# Restaurar simulator.py original desde backup
git checkout HEAD -- simulator.py
```

Cada commit es pequeño y autocontenido, facilitando `git bisect` si hay regresión.

---

## 📝 Notas Adicionales

### Sobre Mamba:
No hay rastro de `mamba_engine.py` en el repositorio actual. Si existió previamente, ya fue removido. No es parte de este refactor.

### Sobre Claims de RAM (99.8% ahorro):
Fuera del scope de este refactor. Se abordará en Fase 4 del REPAIR_OPTIMIZATION_PLAN.md.

### Sobre LangChain:
Es opcional en `app.py`. No es dependencia principal. Fuera del scope de este refactor.

---

**Aprobado por:** [Tu nombre]  
**Fecha de inicio:** [Fecha]  
**Fecha estimada de completion:** [Fecha + 7 días]
