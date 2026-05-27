# MASSIVE

## 1. Visión General

MASSIVE es una plataforma de simulación social para modelar evolución de opinión, polarización y propagación de influencia en redes complejas.  
El núcleo histórico (`simulator.py`) mantiene una API estable (`simular`, `simular_multiples`, `run_with_schedule`) y hoy convive con capas modernas: simulación integrada adaptativa (`IntegratedSimulator`), forecast temporal (`forecast/`) y selección de régimen con motor neuronal opcional CfC (`cfc_router.py`).

Su propósito actual es combinar ejecución operativa (simulación), diseño estratégico (Social Architect) y estimación de riesgo temporal en un flujo único, reproducible y ejecutable en hardware estándar.

## 2. Arquitectura y Áreas Clave

- **Motor de simulación base (`simulator.py`)**
  - Reglas principales: `regla_lineal`, `regla_umbral`, `regla_memoria`, `regla_backlash`, `regla_hk`, `regla_homofilia`, `regla_replicador`.
  - Métricas y utilidades: `calculate_ews_metrics`, `detect_topological_change`, `resumen_historial`.
  - API pública legacy preservada para compatibilidad.

- **Orquestación dinámica (`IntegratedSimulator` en `simulator.py`)**
  - Integra `MassiveEngine` y `MultilayerEngine`.
  - Añade drift contextual, saltos de Lévy, topología dinámica (`dynamic_rewiring`) y diagnóstico de divergencia (`run_butterfly_diagnostic`).

- **Escalamiento computacional (`massive_engine.py`)**
  - `MassiveSimEngine` implementa LOD por super-agentes (`build_super_agents`), cuantización (`quantize_state`) y ejecución event-driven (`ActiveSet`), con fallback de backend GPU/CPU.

- **Dinámica multicapa (`multilayer_engine.py`)**
  - `MultilayerEngine` modela capas social/digital/económica y atributos sociodemográficos.
  - Compresión de estado para poblaciones grandes mediante `state_compression.py` (`compress_agent_states`, `decompress_agent_states`).

- **Diseño de estrategias (`social_architect.py`)**
  - Bucle inverso con `buscar_estrategia_inversa`.
  - Optimización de fases con `find_optimal_interventions` + `optimize_interventions` (`intervention_optimizer.py`).

- **Forecast temporal (`forecast/`)**
  - API: `forecast(...)` con modos `analytical` y `monte_carlo`.
  - Configuración tipada con `TemporalConfig`.
  - Comparación de escenarios con `compare_scenarios`.

- **Capa contractual backend/frontend**
  - DTOs Pydantic v2 en `backend/app/models/`.
  - Generación tipada TypeScript con `python scripts/gen_ts_types.py` hacia `frontend/src/types/api.generated.ts`.
  - Adaptador estable `massive_core/` para importaciones nuevas sin romper módulos legacy.

## 3. Características Vanguardistas

- Selección híbrida de régimen (CfC/LLM/heurístico) con fallback no disruptivo (`CfCRouter`).
- Motor temporal dual (analítico + Monte Carlo) con intervalos de confianza y horizonte configurable.
- Simulación integrada con topología dinámica y monitoreo de transición caótica (Lyapunov).
- Escalamiento para grandes poblaciones con LOD, cuantización y conjuntos activos event-driven.
- Contratos API estrictos (`extra="forbid"`) y generación automática de tipos frontend para evitar deriva entre backend y UI.

## 4. Línea de Tiempo / Hitos

- **Base del proyecto:** consolidación del simulador social clásico con reglas múltiples y API estable (`simular`, `simular_multiples`).
- **Calibración empírica:** incorporación de `empirical_config.py` y `empirical_calibration.py`.
- **Motor CfC:** integración de `cfc_engine.py`, `cfc_router.py`, `cfc_trainer.py` como capa neuronal opcional.
- **Forecast temporal:** creación de `forecast/` e integración en UI y Social Architect.
- **Capa de contratos:** incorporación de DTOs Pydantic v2, `massive_core/` y pipeline de generación TS + validación CI.
- **Simulación integrada reciente:** commits recientes incorporan/refinan `IntegratedSimulator`, ajustes de constantes dinámicas y endurecimiento de hooks (historial reciente: PRs #41, #42, #43).

## 5. Guía de Inicio Rápido

```bash
pip install -r requirements.txt
streamlit run app.py
python -m pytest tests/
```


## Deployment note
CI deploy no longer uses force-push to Hugging Face Spaces. Ensure HF_TOKEN is configured in repository secrets.
