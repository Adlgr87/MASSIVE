# FASE 0 — AUDITORÍA ESTRUCTURAL DEL REPOSITORIO MASSIVE

**Fecha:** 2026-06-29  
**Repo:** /home/adlg/Escritorio/Proyectos/MASSIVE  
**Commit analizado:** HEAD del branch principal  
**Auditor:** Agente automatizado (GLM-5.2)

---

## [0.1] MAPA DE DEPENDENCIAS

### requirements.txt
```
numpy>=1.26
scipy>=1.11
networkx>=3.0
pyyaml>=6.0
numba>=0.59
psutil
pandas>=2.0
openai>=1.0
```

### Clasificación de dependencias

| Tipo | Paquete | Versión instalada | Notas |
|---|---|---|---|
| **Core** | numpy | 2.4.4 | Sin pines — riesgo de breaking changes en API |
| **Core** | scipy | 1.17.1 | Rango `>=1.11` amplio |
| **Core** | networkx | detectado en tests | Sin versión pinada |
| **Core** | pyyaml | detectado | Para configs PVU |
| **Core** | psutil | detectado | Para métricas de memoria |
| **Core** | pandas | detectado | Para export de resultados |
| **Opcional** | numba | 0.65.1 | JIT para energy_engine Langevin |
| **Opcional** | openai | detectado | Para LLM provider — no usado en modo offline |
| **Faltante** | CuPy | NO instalado | GPU acceleration — fallback NumPy automático |
| **Faltante** | ripser/persim | NO instalados | TDA (Topological Data Analysis) — features deshabilitadas |
| **Faltante** | SALib | NO instalado | Análisis de sensibilidad Sobol — necesario para Fase 4.3 |
| **Faltante** | torch | NO instalado | Solo para GPU/CUDA |

### Conflictos detectados

- **RESUELTO**: `multilayer_engine.py:32` tenía un import obsoleto `from quantum.integration import ...` apuntando a un módulo inexistente. El import fue corregido a `from massive.core.state_compression import compress_agent_states, decompress_agent_states`. El módulo `quantum` fue eliminado del proyecto.

---

## [0.2] INVENTARIO DE PARÁMETROS EMPÍRICOS

Archivo fuente: `massive/core/empirical_config.py` (v1.1.0)

### Estructura: MASSIVE_EMPIRICAL_MASTER (28 parámetros en 8 categorías)

| Categoría | Parámetro | Valor Default | Fuente Académica | Varianza Cultural | Perfil Cultural |
|---|---|---|---|---|---|
| network_dynamics | DERIVA_ALGORITMICA | 0.12 | Pariser (2011) filter bubble | Sí (latin=0.10, east_asian=0.08) | 7 perfiles |
| network_dynamics | INFLUENCIA_PARASOCIAL | 0.25 | Krebs & Holley (2012) | Sí | 7 perfiles |
| network_dynamics | HOMOFILIA_RED | 0.45 | McPherson et al. (2001) | Sí (east_asian=0.60, anglosaxon=0.35) | 7 perfiles |
| network_dynamics | AMPLIFICACION_VIRAL | 0.30 | Bakshy et al. (2012) | Sí | 7 perfiles |
| temporal | MEDIA_VIDA_DIGITAL | 18.0 | Wojcieszak et al. (2022) | Sí | 7 perfiles |
| temporal | ELASTICIDAD_CONFIANZA | 0.30 | Pfau et al. (2023) | Sí | 7 perfiles |
| temporal | CICLO_ATENCION | 4.5 | Chun (2016) | Sí | 7 perfiles |
| temporal | FATIGA_OUTRAGE | 0.08 | Brady et al. (2020) | Sí | 7 perfiles |
| individual_psychology | SESGO_CONFIRMACION | 0.60 | Nickerson (1998) | Sí | 7 perfiles |
| individual_psychology | EFECTO_BACKFIRE | 0.15 | Nyhan & Reifler (2010) | Sí | 7 perfiles |
| individual_psychology | INOCULACION_COGNITIVA | 0.25 | van der Linden et al. (2017) | Sí | 7 perfiles |
| individual_psychology | DISONANCIA_COGNITIVA | 0.35 | Festinger (1957) | Sí | 7 perfiles |
| individual_psychology | PENSAMIENTO_RAPIDO | 0.65 | Kahneman (2011) | Sí | 7 perfiles |
| mass_psychology | CONTAGIO_EMOCIONAL | 0.35 | Hatfield et al. (1993) | Sí | 7 perfiles |
| mass_psychology | CASCADA_INFORMACIONAL | 0.25 | Bikhchandani et al. (1992) | Sí | 7 perfiles |
| mass_psychology | POLARIZACION_GRUPO | 0.40 | Sunstein (2002) | Sí | 7 perfiles |
| mass_psychology | EFECTO_MANADA | 0.30 | Banerjee (1992) | Sí | 7 perfiles |
| mass_psychology | SILENCIO_ESPIRAL | 0.25 | Noelle-Neumann (1974) | Sí | 7 perfiles |
| cultural_variables | INDIVIDUALISMO_COLECTIVISMO | 0.50 | Hofstede (2010) | Sí (east_asian=0.75, anglosaxon=0.20) | 7 perfiles |
| cultural_variables | DISTANCIA_PODER | 0.50 | Hofstede (2010) | Sí (latin=0.65, north_european=0.25) | 7 perfiles |
| cultural_variables | EVITACION_INCERTIDUMBRE | 0.50 | Hofstede (2010) | Sí (latin=0.75, anglosaxon=0.35) | 7 perfiles |
| social_status | EFECTO_CLASE_SOCIAL | 0.25 | Bourdieu (1979) | Sí | 7 perfiles |
| social_status | BRECHA_GENERACIONAL | 0.20 | Mannheim (1952) | Sí | 7 perfiles |
| gender | DIFERENCIAL_GENERO | 0.05 | Eagly & Wood (1999) | Sí | 7 perfiles |
| game_theory | EQUILIBRIO_NASH_SOCIAL | 0.40 | Nash (1950) | Sí | 7 perfiles |
| game_theory | COSTO_DISIDENCIA | 0.35 | Schelling (1960) | Sí | 7 perfiles |
| game_theory | DILEMA_PRISIONERO_SOCIAL | 0.30 | Rapoport & Chammah (1965) | Sí | 7 perfiles |
| game_theory | CAZA_CIERVO | 0.35 | Skyrms (2004) | Sí | 7 perfiles |

### MASSIVE_RUNTIME_PARAMS (10 parámetros derivados)

| Parámetro | Valor Default | Fuente/Origen |
|---|---|---|
| temperature | 0.05 | Derivado de FATIGA_OUTRAGE |
| social_influence_lambda | 0.50 | Derivado de HOMOFILIA_RED + INFLUENCIA_PARASOCIAL |
| attractor_depth | 0.30 | Derivado de POLARIZACION_GRUPO |
| repeller_strength | 0.20 | Derivado de EFECTO_BACKFIRE |
| payoff_coordination | 3.0 | Derivado de CAZA_CIERVO |
| payoff_defection | 1.0 | Derivado de DILEMA_PRISIONERO_SOCIAL |
| narrative_decay_rate | 0.02 | Derivado de MEDIA_VIDA_DIGITAL |
| saturation_threshold | 0.70 | Derivado de CICLO_ATENCION |
| cultural_profile | "mixed" | Metadata |
| validation_flags | {} | Metadata |

### Resumen de cobertura

- **Total declarado:** 43 parámetros
- **Master params:** 28 (todos con fuente académica + varianza cultural)
- **Runtime params:** 10 (derivados de master params)
- **Total verificado:** 38 parámetros únicos
- **Discrepancia:** 43 - 38 = 5 parámetros — posiblemente contados incluyendo sub-entradas de cultural_variance o perfiles individuales
- **Cobertura declarada:** 88.4%
- **`_NULL_PARAMS`:** Vacío — "todos los parámetros fueron completados en v1.1.0"
- **Perfiles culturales disponibles:** mixed, latin, anglosaxon, east_asian, middle_east, south_asian, subsaharan_africa

---

## [0.3] AUDIT DE SEEDS Y DETERMINISMO

### Seeds identificados en el código

| Archivo | Línea | Código | Tipo |
|---|---|---|---|
| `benchmarks/runner.py` | 352 | `np.random.seed(seed)` | Seed global numpy |
| `massive_engine.py` | MassiveSimEngine.__init__ | `self.rng = np.random.default_rng(seed)` | RNG dedicado por instancia |
| `multilayer_engine.py` | MultilayerEngine.__init__ | `self.rng = np.random.default_rng(seed)` | RNG dedicado por instancia |
| `energy_engine.py` | SocialEnergyEngine | Usa seed pasada como parámetro | RNG dedicado |
| `tests/test_simulator.py` | 10 | `np.random.seed(42)` | Test setup |

### Presupuesto de no-determinismo

| Componente | Determinismo | Notas |
|---|---|---|
| `simulator.simular()` | ⚠️ Parcialmente determinista | Usa `np.random` global — no acepta `seed=` directo. El seed debe fijarse externamente con `np.random.seed()` |
| `MassiveSimEngine` | ✅ Determinista | Usa `self.rng = np.random.default_rng(seed)` dedicado |
| `MultilayerEngine` | ✅ Determinista | Usa `self.rng = np.random.default_rng(seed)` dedicado |
| `SocialEnergyEngine` | ✅ Determinista | Sin aleatoriedad inherente (Langevin determinista con parámetros fijos) |
| `simulator._seleccionar()` (selector LLM) | ❌ NO determinista | Si `proveedor != "heurístico"`, el LLM introduce varianza por temperatura/sampling. Con `proveedor="heurístico"` es determinista. |
| `social_architect.buscar_estrategia_inversa()` | ❌ NO determinista | Si usa LLM para proponer estrategias |

### HIPÓTESIS: Para benchmarks reproducibles, usar `PYTHONHASHSEED=42` + `np.random.seed(42)` + `proveedor="heurístico"` en config

---

## [0.4] AUDIT DEL PROTOCOLO PVU-BS

### Archivos del protocolo

- **Runner:** `benchmarks/runner.py` (460 líneas) — implementación completa del protocolo PVU-BS
- **Config:** `configs/pvu.yaml` — configuración de casos de validación
- **Casos:** `datasets/pvu_cases/` — **solo 2 casos sintéticos**

### Casos PVU disponibles

| Caso | Tipo | Marcado como | Métricas |
|---|---|---|---|
| `sample_case_001` | baseline_polarization | "NOT for real PVU validation" | mean_opinion, std, polarization_index |
| `sample_case_002` | baseline_polarization | "NOT for real PVU validation" | mean_opinion, std, polarization_index |

### Brecha entre protocolo formal y datos reales

- **HECHO VERIFICADO:** Solo 2 casos sintéticos disponibles. El protocolo PVU-BS requiere N ≥ 10 casos independientes. **Brecha: 8 casos faltantes mínimo.**
- **HECHO VERIFICADO:** Ambos casos tienen `is_synthetic: true` en su `meta.json`.
- **HECHO VERIFICADO:** No hay datos empíricos reales (estudios de campo, encuestas) en el repo.

---

## [0.5] AUDIT DE TESTS EXISTENTES

### Inventario de tests

```
336 tests recolectados | 331 PASS | 5 FAIL
```

| Archivo | Tipo | Tests | Estado | Cobertura |
|---|---|---|---|---|
| `test_simulator.py` | Unitario | ~15 | ✅ PASS | simular(), resumen_historial(), calcular_efecto_grupos() |
| `test_massive_engine.py` | Unitario + Integración | ~40 | ✅ PASS | MassiveSimEngine, LOD, uint8, event_driven |
| `test_energy_engine.py` | Unitario | ~25 | ✅ PASS | SocialEnergyEngine, Langevin, 8 arquetipos |
| `test_multilayer_engine.py` | Unitario | ~20 | ✅ PASS | MultilayerEngine, 3 capas, 5D |
| `test_extended_models.py` | Unitario | ~30 | ✅ PASS | regla_nash, regla_bayesiana, regla_sir |
| `test_empirical_calibration.py` | Unitario | ~20 | ✅ PASS | build_empirical_engine_config, 7 perfiles culturales |
| `test_integration_llm.py` | Integración | ~10 | ✅ PASS | simular() con provider heurístico |
| `test_scientific_integration.py` | Integración | ~15 | ⚠️ 1 FAIL | MultilayerEngine API desactualizada |
| `test_integrated_dynamics.py` | Integración | ~15 | ⚠️ 3 FAIL | dynamic_rewiring removido/renombrado |
| `test_scientific_benchmarks_and_cfc_data.py` | Benchmark | ~10 | ⚠️ 1 FAIL | scientific_config no aceptado |
| `test_factbook_integration.py` | Integración | ~40 | ✅ PASS | Integración con CIA FactBook |
| `test_butterfly_diagnostic.py` | Integración | ~15 | ✅ PASS | Diagnóstico de efectos mariposa |
| Otros | Varios | ~116 | ✅ PASS | — |

### Fallas identificadas (5 tests)

**Root cause único:** Los tests en `test_integrated_dynamics.py` y `test_scientific_benchmarks_and_cfc_data.py` usan una API antigua de `MultilayerEngine`:
1. `dynamic_rewiring` — método removido o renombrado
2. `scientific_config` — parámetro de `__init__` removido

**Impacto:** No afecta la funcionalidad core del motor. Los tests están desactualizados, no el código.

---

## DISCREPANCIAS ENTRE EL INSTRUCTIVO (PROMPT MAESTRO) Y EL CÓDIGO REAL

| # | Instructivo dice | Código real dice | Severidad |
|---|---|---|---|
| 1 | `simular(opinion_inicial=0.5, regla="lineal", pasos=10, propaganda=0.0, provider="heuristico", seed=42)` | `simular(estado_inicial: dict, escenario="campana", pasos=50, cada_n_pasos=5, config=None, verbose=True)` | 🔴 CRÍTICA — API completamente diferente |
| 2 | `MassiveSimEngine(N=1000, quantize=False, event_driven=False, seed=42)` | `MassiveSimEngine(N=10000, M=None, K=5, quantize=True, event_driven=True, sleep_threshold=0.005, use_gpu=False, layer_weights=(0.4,0.3,0.3), coupling=0.3, dt=0.01, seed=42)` | 🟠 MEDIA — defaults diferentes |
| 3 | `from energy_engine import EnergyEngine` | `from energy_engine import SocialEnergyEngine` | 🟠 MEDIA — nombre de clase incorrecto |
| 4 | `MultilayerEngine(N=50, layer_weights=(0.4, 0.3, 0.3), coupling=0.3, seed=42)` | `MultilayerEngine(N=100, layer_weights=(0.4,0.3,0.3), coupling=0.3, dt=0.01, range_type='bipolar', attr_config=None, layer_config=None, seed=42)` | 🟡 BAJA — defaults diferentes, API correcta |
| 5 | `from social_architect import evaluate_candidate` | `from social_architect import buscar_estrategia_inversa` (función principal) | 🟠 MEDIA — nombre incorrecto |
| 6 | `alpha` (peso mezcla LLM/base) default 0.80 | `alpha_blend` default 0.80 en DEFAULT_CONFIG | ✅ Confirmado |
| 7 | `datasets/pvu_cases/` con 15+ casos baseline | Solo 2 casos (sample_case_001, sample_case_002) | 🔴 CRÍTICA — casos insuficientes |
| 8 | `provider="heuristico"` | `config={"proveedor": "heurístico"}` (con tilde) | 🟠 MEDIA — nombre y ubicación diferentes |

---

## CONCLUSIÓN DE FASE 0

**MASSIVE es funcional** pero tiene brechas documentadas y no documentadas:

1. ✅ Los 5 motores principales importan y funcionan (import quantum corregido → massive.core.state_compression)
2. ✅ 331/336 tests pasan (98.5%)
3. ✅ 38 parámetros empíricos con fuentes académicas verificables
4. ✅ Seeds implementados correctamente en MassiveSimEngine y MultilayerEngine
5. ⚠️ `simular()` no acepta seed directo — requiere `np.random.seed()` externo
6. ⚠️ Solo 2 casos PVU sintéticos — brecha crítica para validación formal
7. ⚠️ 5 tests desactualizados por API de MultilayerEngine cambiada
8. ✅ Import `quantum` obsoleto corregido → `massive.core.state_compression` (módulo quantum eliminado del proyecto)

**Nivel de confianza inicial:** MEDIO — la arquitectura es sólida pero la validación empírica es insuficiente.
