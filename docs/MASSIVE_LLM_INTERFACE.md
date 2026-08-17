# MASSIVE-LLM Interface

> **Fase 6 — Diseñador de Prompts LLM + Integrador LLM–Backend**  
> **Versión:** 1.1.0 · **Contrato origen:** `configs/llm_contract/massive_llm_contract.json`

Este documento describe la interfaz canónica mediante la cual un agente LLM
interactúa con el backend MASSIVE: el endpoint **`POST /v1/llm/run_simulation`**,
las reglas de selección de motor, los campos de entrada/salida, los prompts de
referencia, la autenticación y los ejemplos de uso.

---

## 1. Resumen ejecutable

| Concepto | Valor |
|----------|-------|
| **Endpoint** | `POST /v1/llm/run_simulation` |
| **Auth** | `X-API-Key` (server-side) + LLM provider key configurada (verificado en `/ready`) |
| **Rate-limit** | 30 req/min por IP (`MASSIVE_ENV=development` → `dev-secret-key`) |
| **Entry point código** | `backend/app/routers/llm.py` → `services/llm_orchestrator.run_llm_simulation` |
| **DTOs** | `backend/app/models/dto_llm.py` (`LLMRunRequest`, `LLMRunResponse`, `LLMAmbiguityResponse`) |
| **Prompts de referencia** | `docs/LLM_PROMPTS.md` (RT, WC, NR, AC) |

---

## 2. Flujos soportados

Véase también `massive_llm_contract.json` → sección `supported_flows`.

### 2.1 Flujo canónico (NL → config → run → summary)

```
LLM client
   │ POST /v1/llm/run_simulation {intent, motor?, country?, partial_config?}
   ▼
Backend (services.llm_orchestrator)
   ├─ 1. classify_motor(intent, motor_hint?)   ← reglas del contrato
   ├─ 2. (opcional) wizard_config(intent)      ← NL → config (InterpreterLayer)
   ├─ 3. Factbook augmentation si country       ← services.factbook_service
   ├─ 4. Dispatch engine por `motor`
   ├─ 5. Narrate (ResultNarratorChain)
   └─ Devolver LLMRunResponse {sim_id, motor, config, summary, narrative, results, assumptions, factbook_params}
```

### 2.2 Endpoints directos (bypass NL→config)

Cuando el LLM ya posee parámetros estructurados, puede invocar directamente:

| Endpoint | Uso |
|----------|-----|
| `POST /v1/simulate` | Dinámica de opiniones legacy (scalar `simular`) |
| `POST /v1/engine/energy` | Motor Langevin + paisaje de energía |
| `POST /v1/engine/architect` | Búsqueda inversa de intervenciones |
| `POST /v1/forecast` | Pronóstico temporal (analytical / monte_carlo) |
| `POST /v1/benchmarks` | PVU-BS benchmark (offline/real/llm) |
| `GET /ready` | Verificar disponibilidad del provider LLM + adapter UIL |

---

## 3. Especificación del endpoint `POST /v1/llm/run_simulation`

### 3.1 Request

```jsonc
{
  "intent": "Quiero entender cómo evoluciona la opinión en un país con alta desigualdad económica", // string, REQUIRED
  "motor": "energy_engine",            // opcional; si se omite, el backend clasifica
  "country": "Brazil",                 // opcional; para augmentación Factbook
  "partial_config": { "seed": 7 },     // opcional; overrides estructurados
  "llm": { "provider": "groq", "model": "llama-3.3-70b-versatile" }, // opcional
  "simulation_steps": 100,             // opcional (default 50)
  "seed": 42,                          // opcional (default 42)
  "config_overrides": { "temperature": 0.12 } // opcional; engine-specific
}
```

**Validación de DTO** (`LLMRunRequest`, `extra="forbid"`):
- `intent` requerido (mín 1 carácter).
- `motor` ∈ `{energy_engine, social_architect, forecast, multilayer_engine, massive_engine, micro_massive, benchmark_offline, factbook_validation}`.
- Campos desconocidos → `422`.

### 3.2 Respuesta (200 OK)

```jsonc
{
  "sim_id": "sim_3f7c1a2b9e8d",
  "motor": "energy_engine",
  "config": {
    "estado_inicial": {"opinion": 0.0, "propaganda": 0.0},
    "escenario": "campana",
    "pasos": 100,
    "config": { /* DEFAULT_CONFIG mergeado + overrides + Factbook */ },
    "country": "Brazil"
  },
  "summary": {
    "motor": "energy_engine",
    "indicators": {
      "mean_opinion": 0.31,
      "std_opinion": 0.12,
      "polarizacion": 0.28,
      "consenso": 0.62,
      "delta_total": 0.25
    },
    "regla_dominante": "confirmation_bias",
    "factbook_country": "Brazil"
  },
  "narrative": "Simulación completada. Opinión media evolucionó de 0.0 a 0.31...",
  "results": {
    "sim_id": "sim_3f7c1a2b9e8d",
    "motor": "energy_engine",
    "payload": { /* output crudo del motor */ },
    "timeline": [ { "tick": 0, "mean_opinion": 0.0, "polarization": null }, ... ],
    "final_state": { "mean_opinion": 0.31, "std_opinion": 0.12, "polarizacion": 0.28 }
  },
  "assumptions": [
    "country detectado desde la intención: Brazil",
    "params de Factbook inyectados para Brazil: n_agents=1000, gini=0.35",
    "seed=42 (reproducible)",
    "horizonte por defecto según motor (contract.llm_guidelines)"
  ],
  "factbook_params": { "country": "Brazil", "n_agents": 1000, "gini_coefficient": 0.35, ... }
}
```

### 3.3 Códigos de error

| Código | Condición |
|--------|-----------|
| `400` | `intent` vacío o payload inválido. |
| `401` | `X-API-Key` ausente o inválida. |
| `422` | *Intent ambiguo* y no resoluble con defaults. Devuelve `{detail, requested_fields, motor}`. El LLM cliente debe recoger los campos faltantes y re-enviar. |
| `429` | Rate limit excedido (30/min). |
| `503` | Motor requiere LLM key no configurada (p. ej. `social_architect`). Verificar `/ready`. |

---

## 4. Reglas de selección de motor (motor classification)

Implementadas en `services/llm_orchestrator.classify_motor`, derivadas de
`massive_llm_contract.json` → `llm_guidelines`. Si el LLM envía `motor`
explícito y es válido, se respeta.

| Señal en `intent` | Motor asignado |
|-------------------|----------------|
| *"energía", "desigualdad", "polarización", "conflicto social"* + country | `energy_engine` |
| *"estrategia inversa", "cómo llegar a", "qué intervención", "reducir polarización"* | `social_architect` |
| *"pronosticar", "predecir", "probabilidad de", "viral", "semanas"* | `forecast` |
| *"múltiples escalas", "millones de agentes", "gran escala", "masivo"* | `massive_engine` |
| *"familias de futuros", "grupo pequeño", "amigos", "organizacional"* | `micro_massive` |
| *"benchmark", "validación CI", "puntos de inflexión"* | `benchmark_offline` |
| *"validar", "validación", "datos reales"* + country | `factbook_validation` |
| (default) dinámica de opiniones general | `multilayer_engine` |

---

## 5. Campos de entrada que el LLM debe solicitar

Fuente: `massive_llm_contract.json` → `llm_requested_fields.when_ambiguous`.

| Campo | Tipo | ¿Por qué se pide? |
|-------|------|------------------|
| `country` | string | Factbook augmentation (gini, n_agents, social_pressure_weights). Detectar de nombres como *United States*, *México*, *Brasil*, *US*, *MX*. |
| `horizon_steps` | int | Duración. Preguntar si el intent menciona *"durante X meses/semanas"*. |
| `n_agents` | int | Escala poblacional (multilayer/massive). |
| `seed` | int | Reproducibilidad (default 42). |
| `confidence_interval` | bool | Si el usuario quiere rangos → `forecast` modo `monte_carlo` con `n_runs`. |
| `temporal_horizon_days` | int | Para flows `forecast`: *"2 semanas"* → `n_steps=14, step_duration_days=1`. |

### Supuestos por defecto anunciables

| Campo | Default anunciado |
|-------|-------------------|
| horizonte | 50 pasos (legacy), 100 (energy_engine), 14 días (forecast viral_online) |
| `range_type` | `"bipolar"` |
| `connectivity` | `0.3` |
| `n_agents` | 50 (energy), 100 (multilayer); escalable via Factbook |
| `seed` | `42` (reproducible; anunciar siempre) |
| `mode` (forecast) | `"analytical"` |
| `mode` (benchmark) | `"offline"` |

---

## 6. Campos de salida

Fuente: `massive_llm_contract.json` → `llm_output_fields`.

### 6.1 Indicadores numéricos

| Nombre | Rango | Descripción |
|--------|-------|-------------|
| `mean_opinion` | [-1, 1] ∥ [0, 1] | Opinión media poblacional |
| `std_opinion` | [0, 1] | Desviación típica |
| `polarizacion` | [0, 1] | Índice de polarización (↑ = más dividida) |
| `consenso` | [0, 1] | Tasa de consenso |
| `p_event` | [0, 1] | Probabilidad de evento umbral (forecast) |
| `delta_total` | [-2, 2] | Cambio neto de opinión |
| `feasibility_score` | [0, 1] | Viabilidad objetivo (forecast) |
| `horizon_ticks` | int | Horizonte temporal (forecast) |
| `attempts` | int | Intentos del Social Architect |

### 6.2 Resúmenes textuales

`diagnostico`, `dinamica_clave`, `implicaciones`, `recomendaciones` (lista),
`narrative`, `regla_dominante`, `confidence_label`.

### 6.3 Artefactos estructurados

`config`, `history` (o slice), `final_state`, `metrics_timeline`, `strategy`
(architect), `feasibility` {score, label, rationale}, `factbook_params`.

---

## 7. Plantillas de prompts base

Véase `docs/LLM_PROMPTS.md` para las plantillas completas (Jinja2):

| Prompt | Rol | Uso |
|--------|-----|-----|
| **RT** (Router Intento/Motor) | Clasificar intención → motor | Antes del dispatch, o validación local del LLM cliente |
| **WC** (Wizard NL→Config) | Traducir intención a config estructurado | `services.llm_service.wizard_config` (InterpreterLayer.wizard) |
| **NR** (Narrador) | Resultados → síntesis narrativa | Post-simulación, produce `narrative` |
| **AC** (Validador Ambigüedad) | Decidir si pedir campos faltantes | Determina 422 vs proceed-with-defaults |

### Ejemplo de prompt del Wizard (WC)

```text
Eres el Asistente de Configuración MASSIVE, versión 1.1.0.
Convierte la descripción del usuario en parámetros de simulación MASSIVE,
anunciando cada supuesto de forma explícita.

PARÁMETROS Y RANGOS:
  opinion [-1,1], confianza [0,1], propaganda [-1,1],
  identidad_grupo [0,1], sesgo_confirmacion [0,1], homofilia_tasa [0,1],
  pasos [10,500], regla ∈ {degroot, hegselmann_krause, ...}

EJEMPLOS:
  "hay mucha polarización" → opinion≈0.0, identidad_grupo≈0.8, regla=hegselmann_krause
  "todos están de acuerdo" → opinion≈0.7, identidad_grupo≈0.2, regla=degroot

Salida JSON:
{
  "config": {...},
  "motor_sugerido": "<motor>",
  "supuestos": ["seed=42", "horizonte=100 pasos (energy_engine)"],
  "advertencias": [...],
  "confianza": 0.0-1.0
}

Texto del usuario:
{{INTENT_TEXT}}
```

---

## 8. Ejemplos de uso (curl)

### 8.1 Simulación sin país (multilayer)

```bash
curl -X POST http://localhost:8000/v1/llm/run_simulation \
  -H "X-API-Key: dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "Simula la dinámica de opinión para 1000 agentes con red tipo mundo pequeño",
    "seed": 42,
    "simulation_steps": 150
  }'
```

### 8.2 Pronóstico con country + motor explícito

```bash
curl -X POST http://localhost:8000/v1/llm/run_simulation \
  -H "X-API-Key: dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{
    "intent": "Pronostica si una protesta será viral en las próximas 2 semanas en México",
    "motor": "forecast",
    "country": "Mexico",
    "partial_config": {
      "temporal_config": {"n_steps": 14, "step_duration_days": 1, "event_type": "viral_online"},
      "simulation_state": {"historial": [{"opinion": 0.45}, {"opinion": 0.52}, {"opinion": 0.58}],
                           "ews": {"metrics": {"variance": 0.08, "autocorr": 0.65}}}
    }
  }'
```

### 8.3 Intent ambiguo → 422

```bash
curl -X POST http://localhost:8000/v1/llm/run_simulation \
  -H "X-API-Key: dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"intent": "Quiero pronosticar algo"}'
# → 422 { "detail": "...", "requested_fields": ["country","temporal_horizon_days"], "motor": "forecast" }
```

### 8.4 Motor que requiere LLM key no configurada → 503

```bash
curl -X POST http://localhost:8000/v1/llm/run_simulation \
  -H "X-API-Key: dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"intent":"Reduce la polarización en España","motor":"social_architect","country":"Spain"}'
# → 503 "social_architect motor requires an LLM API key..."
```

---

## 9. Wireup de código

| Archivo | Rol |
|---------|-----|
| `configs/llm_contract/massive_llm_contract.json` | Contrato canónico (flujos, campos, prompts, reglas). V 1.1.0. |
| `backend/app/models/dto_llm.py` | DTOs `LLMRunRequest` / `LLMRunResponse` / `LLMAmbiguityResponse`. |
| `backend/app/routers/llm.py` | Router FastAPI `POST /v1/llm/run_simulation`. Auth + rate-limit. |
| `backend/app/main.py` | Registro del router: `app.include_router(llm.router, prefix="/v1")`. |
| `services/llm_orchestrator.py` | Orquestación: `classify_motor`, `run_llm_simulation`, `_dispatch`, `_narrate`. |
| `services/llm_service.py` | `wizard_config` (NL→config) vía `InterpreterLayer.wizard`. |
| `services/factbook_service.py` | `country_params` (Factbook augmentation). |
| `services/__init__.py` | Re-exporta `run_llm_simulation`. |
| `interpreter_layer.py` | `InterpreterLayer` con cadenas Wizard/Explainer/Narrator/Translator. |
| `docs/LLM_PROMPTS.md` | Plantillas de prompts de referencia (RT, WC, NR, AC). |

---

## 10. Integración con observabilidad (futuro)

- **Trace IDs**: inyectar `X-Request-ID` en el response header para trazabilidad.
- **Métrica de latencia**: instrumentar `run_llm_simulation` con OpenTelemetry
  (`@instrument` decorator sobre el dispatcher).
- **Contador de dispatch por motor**: `massive.llm.motor_dispatch_total{motor="energy_engine"}`.
- **SLO**: P95 `< 30 s` para endpoints LLM (contract `rate_limit_tiers.llm`).

---

*Documento generado por Diseñador de Prompts LLM + Integrador LLM–Backend — MASSIVE Master Orchestrator, Fase 6.*
*Última actualización: 2026-08-16.*
