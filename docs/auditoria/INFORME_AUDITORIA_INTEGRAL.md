# INFORME DE AUDITORÍA INTEGRAL — MASSIVE
## Fases 1–5 · Análisis estático forense

> **Repo:** `Adlgr87/MASSIVE` · **Rama:** `arena/01a0fb01-massive` · **Commit:** `963ff7f` · **Fecha:** 2026-10-01
> **Fase 0 (inventario y mapeo):** entregada en [`FASE0_INVENTARIO_Y_MAPEO.md`](FASE0_INVENTARIO_Y_MAPEO.md)
> **Método:** lectura semántica + grafo AST. **No se modificó código.** Toda corrección es *sugerida*.
> **Notación:** **[HECHO]** evidencia directa en código · **[INFERENCIA]** deducción lógica · **[DIN]** requiere ejecución.

---

# 1. RESUMEN EJECUTIVO

## 1.1 Conteo de hallazgos

| Severidad | N.º | Categorías dominantes |
|---|---:|---|
| 🔴 **Crítico** | **6** | infra, correlación-variables, desconectado, seguridad |
| 🟠 **Alto** | **14** | correlación-variables, error, seguridad, optimización |
| 🟡 **Medio** | **13** | duplicación, contrato, CI, docs |
| 🔵 **Bajo** | **9** | higiene, nomenclatura |
| ⚪ Informativo | 5 | buenas prácticas confirmadas |
| | **47** | |

| Categoría | N.º |
|---|---:|
| Correlación de variables | 13 |
| Error / bug | 9 |
| Desconectado / código muerto | 7 |
| Seguridad | 6 |
| Optimización | 5 |
| Conexión front↔back / GUI | 4 |
| Contrato / docs / CI | 3 |

## 1.2 Top 5 riesgos críticos

| # | Riesgo | Impacto en una frase |
|---|---|---|
| **1** | **`load_dotenv()` no se invoca en ningún punto del repo** pese a que `python-dotenv` es dependencia *core*, el README manda `cp .env.example .env` y compose monta `./.env:/app/.env:ro` | En Docker **todos los endpoints `/v1/*` responden 503**: `MASSIVE_API_KEY` nunca llega a `os.environ`. El producto no arranca como está documentado. |
| **2** | **La imagen Docker no puede construirse**: `Dockerfile` copia `nginx.conf` y `supervisord.conf`, que fueron movidos a `docs/archive/legacy_docker/`, directorio que además `.dockerignore` excluye | `docker compose build` falla → el workflow `docker-e2e.yml` está en rojo → no hay despliegue posible. |
| **3** | **El corrector CfC no corrige: interpola hacia la verdad conocida** (`cfc_router.py:379-386`). Con `actual` presente, `corrected = 0.5·sim + 0.5·actual` y la salida del modelo `r_hat` se **descarta** | Cualquier métrica de "mejora por CfC" validada contra ground truth es **fuga de etiqueta**, no habilidad del modelo. Invalida las conclusiones de calibración (p. ej. Brexit). |
| **4** | **La fuerza social del motor multicapa es una suma de grado, no una media de consenso** (`multilayer_engine.py:356`): `Σ_j A_ij·x_j` sin normalizar por grado y **sin término `− x_i`** | La fuerza escala con N·p (×300 en la config por defecto). El sistema satura en los bordes en pocos pasos y el *clipping* disfraza la explosión numérica de "polarización". |
| **5** | **La capa de datos del frontend está completamente desconectada**: `App.tsx` son 32 líneas y no llama a `api`; `services/api.ts` (200 LOC) y `hooks/useApi.ts` (72 LOC) no los importa nadie | No existe GUI funcional. Lo que se audita como "frontend" es un esqueleto con un botón. |

## 1.3 Cobertura analizada

473/473 archivos versionados inventariados · 218 módulos Python parseados con AST (0 fallos) · lectura semántica completa de: las 2 apps FastAPI, los 5 routers, la capa `services`, `security`/`config`, `energy_engine`, `multilayer_engine`, `massive_engine` (LOD/cuantización), `cfc_router`, `kalman`, `rust_core` + crate Rust, `factbook/{mappings,context}`, `metrics/unified_metrics`, los 9 archivos del frontend y los 11 workflows.

**Exclusiones declaradas:** `docs/archive/**` (77 `.md`, usados sólo como contexto histórico), `uv.lock` y `package-lock.json` (auditoría de dependencias pendiente por herramienta), contenido numérico de los 9 `.pt` **[DIN]**, y el interior de `simulator.py` (2.467 LOC) más allá de sus fronteras de llamada — declarado como deuda de auditoría.

---

# 2. MAPA DE ARQUITECTURA VERIFICADO Y DESVIACIONES

Ver diagrama completo en Fase 0 §2. Resumen de desviaciones frente al mapa declarado en README y en el prompt:

| ID | Declarado | Real | Sev. |
|---|---|---|---|
| M1 | «El frontend React usa la capa legacy `/api`» | El frontend usa `/v1` (`api.ts:27`). `api.py` **no tiene ningún consumidor**. | Medio |
| M2 | Una API canónica `/v1` | `backend/app/main.py:262-273` monta los 5 routers **dos veces**: `/v1/*` **y** `/api/v1/*` | Alto |
| M3 | — | Coexisten **dos apps FastAPI** (`api:app`, `backend.app.main:app`) con `/health`,`/ready`,`/version` duplicados y **lógica divergente** | Alto |
| M4 | `massive-ui-ng/`, `docker-compose.single.yml` | No existen (el primero eliminado el 2026-09-22; el segundo referenciado por README en una ruta vacía) | Medio |
| M5 | 530 tests, 68 % cobertura, 16 checks con semgrep | 689 funciones de test, `fail_under = 30`, 52 jobs, **sin semgrep** | Bajo |
| M6 | `utility_logic.py`, `state_compression.py`, `schemas.py` en raíz | Viven en `massive/core/` | Informativo |

---

# 3. MATRIZ DE ENDPOINTS FRONT ↔ BACK

## 3.1 Llamadas del frontend (`frontend/src/services/api.ts`, `baseURL="/v1"`)

| Llamada (línea) | Endpoint | ¿Existe? | Canónico/legacy | Payload vs DTO | Envelope vs GUI | Códigos manejados | Headers | Desviación | Sev. |
|---|---|---|---|---|---|---|---|---|---|
| `forecast()` ~108 | `POST /v1/forecast` | ✅ | /v1 | tipado laxo (`Record<string,unknown>`) | `{forecast, raw}` ✓ | sólo 401/429 logueados | `X-API-Key` ✓ | 422/503/413 no manejados | Medio |
| `architect()` ~127 | `POST /v1/engine/architect` | ✅ | /v1 | ✓ coincide con `ArchitectRequest` | `{strategy,narrative,attempts,history_summary,history_length}` ✓ | ídem | ✓ | **endpoint LLM-dependiente; GUI no trata el 503** | Alto |
| `energy()` ~160 | `POST /v1/engine/energy` | ✅ | /v1 | ✓ `EngineEnergyRequest` | ✓ | ídem | ✓ | — | — |
| `simulateUil()` ~175 | `POST /v1/simulate` | ✅ | /v1 | ⚠ envía `{description}`; `SimRequest` espera `estado_inicial/escenario/pasos/config/verbose` con **`extra=forbid`** | — | ídem | ✓ | **422 garantizado: `description` es campo desconocido** | **Alto** |
| `extractDocument()` ~183 | `POST /v1/llm/extract` | ✅ | /v1 | multipart ✓ | `{config}` ✓ | ídem | ✓ | allowlist divergente (ver H-11) | Medio |
| `wizard()` ~195 | `POST /v1/llm/wizard` | ✅ | /v1 | ✓ `LLMWizardRequest` | `{config}` ✓ | ídem | ✓ | — | — |

> **H-01 (Alto) [HECHO]** — `simulateUil()` hace `POST /v1/simulate` con body `{description}`. El router `sim.py:31` valida contra `SimRequest`, cuyo módulo declara `extra="forbid"` (`dto_simulate.py:26`: «Extra fields are rejected so clients cannot inject…»). `description` no es campo de `SimRequest`. **Toda llamada devolverá 422.** El comentario del cliente («was /api/simulate-uil») revela que la migración cambió el endpoint pero **no el contrato**: el legacy `/api/simulate-uil` sí aceptaba `{description}` (`api.py:222-293`). *Corrección sugerida:* enrutar a `POST /v1/llm/wizard`+`/v1/simulate`, o añadir un DTO `SimulateFromDescriptionRequest`.

## 3.2 Endpoints sin consumidor

`POST /v1/benchmarks` · `POST /v1/llm/run_simulation` (¡el entry point canónico del contrato LLM v1.1.0!) · `GET /metrics` · `GET /openapi/v1.json` · **los 10 endpoints de `api.py`**.

## 3.3 Deriva de contrato LLM v1.1.0

| Punto del contrato | Implementación | Estado |
|---|---|---|
| `entry_point: POST /v1/llm/run_simulation` | existe (`llm.py:63`) | ✅ pero sin consumidor |
| 422 + `requested_fields` ante ambigüedad | `llm.py:104-114` **sólo** dispara si la ambigüedad es exactamente `temporal_horizon_days` **y** no hay `motor` | ⚠ El resto de campos de `llm_requested_fields.when_ambiguous` se resuelven con defaults silenciosos → **el orquestador sí "adivina"**, contra lo que pide el contrato |
| `assumption_defaults` deben anunciarse | `result["assumptions"]` existe en el DTO | ✅ **[DIN]** verificar que se pueble siempre |
| `rate_limit_tiers.default = 60/min per IP` | `security.py:76` lee `MASSIVE_RATE_LIMIT_PER_MIN` (default 60) | ✅ |

---

# 4. MATRIZ DE CORRELACIÓN PROPORCIONAL ENTRE VARIABLES

> Sección de énfasis máximo. Cada fila es una relación esperada contrastada contra la implementada.

## 4.1 Factbook → motor

| Variable | Definición (archivo:línea, rango) | Consumo | Transformación real | Relación esperada | Relación real | Desviación | Sev. |
|---|---|---|---|---|---|---|---|
| `gini_index` | `context.py:73` default **35.0**, rango [0,100] | `_calculate_indices` | `normalize_0_100_to_0_1` → clip [0,1] (`mappings.py:410`) | lineal, ↑desigualdad → ↑polarización | ✓ lineal, signo correcto | — | ⚪ |
| `inequality_factor` | `context.py:136` | energy_engine | `1 + 2·(gini/100)` ∈ [1,3] | monótona ↑ | ✓ | **se aplica DOS veces** → ver C-04 | 🔴 |
| `ethnic/religious/language_diversity` | `context.py:104-106` | `social_pressure_weights` | `diversity_index = 1 − HHI` | ↑diversidad → ? | `peso = 1 − diversidad = HHI` ⇒ **↑homogeneidad → ↑presión social** | Signo **opuesto** al declarado en el prompt («diversidad → presión social»). El código es defendible (conformidad), la narrativa no. **Y con datos ausentes `diversity=0 ⇒ peso=1.0 (máximo)`** | 🟠 |
| `social_pressure_weights` ante datos faltantes | `context.py:104` `if self.ethnic_groups else 0.0` | ídem | diversidad=0 → peso=**1.0** | dato ausente → valor **neutro** | dato ausente → **efecto máximo** | **C-05**: un país sin datos étnicos recibe la presión social más alta posible | 🟠 |
| `population → n_agents` | `context.py:112` | engines | `scale_to_max(pop, 100_000)` | escalable a 100 M (README) | **techo duro 100 k** | `EngineEnergyRequest` admite 200 k; `random_network` corta en 50 k; README promete 100 M → **4 topes contradictorios** | 🟡 |
| `gdp_per_capita → cost_scale_factor` | `context.py:143` | optimizador | `log1p(gdp)/10` | ↑riqueza → ↑presupuesto | ✓ monótona creciente | sin cota superior documentada | 🔵 |
| `budget_surplus_deficit → fiscal_constraint` | `context.py:149-152` | optimizador | `clip(0.5 + 2·(surplus/revenues), 0, 1)` | déficit→<0.5, superávit→>0.5 | ✓ **correcto** | — | ⚪ |
| ídem, **tabla declarativa** | `mappings.py:393` | **ninguno** | `lambda x: max(0,min(1,1-(x/abs(x))·0.1))` ⇒ superávit→0.9, déficit→**1.0** | monótona | **invertida** | Vive sólo en `FACTBOOK_TO_MASSIVE`, que **nadie ejecuta** (C-06) | 🟡 |
| `age_structure → demographic_matrix` | `mappings.py:450-494` | `context.py:117` | matriz 5×5: filas=grupos etarios, columnas=dims | — | docstring dice «las 5 dimensiones: 0 opinion…» describiendo **las columnas**, pero indexa **filas** por edad | Ambigüedad 5×5 que invita a transponer por error; además **muta la lista de entrada** (`append`) | 🟡 |

## 4.2 Motor de energía (SDE Langevin / Euler–Maruyama)

| Variable | Definición | Relación esperada | Real | Desviación | Sev. |
|---|---|---|---|---|---|
| **σ del paisaje** | `_SIGMA=0.3` (`energy_engine.py:38`); `effective_sigma(gini)` (`:49-63`) | la dinámica y la energía reportada deben usar **el mismo potencial** | `step()` usa `effective_sigma(gini)` (`:410`); `system_metrics` → `_landscape_energy` usa **`_SIGMA` fijo** (`:98,630`) | **C-01**: para `gini ≠ 0.35` la energía reportada **no es el potencial que gobierna la dinámica**. Todo diagnóstico energético (profundidad de pozo, barrera) es incorrecto | 🔴 |
| **fuerza de atractores** | 3 fórmulas distintas | una sola ley | (a) `mappings.create_wealth_potential`: `1+2g`; (b) `create_gini_adjusted_landscape:548`: `strength · inequality · attractor_multiplier` = `strength·(1+2g)²`; (c) `create_economic_landscape:597`: `2·income_scale·(1+g)` | **C-04**: doble aplicación del mismo factor Gini → dependencia **cuadrática** donde la documentación declara lineal. Con g=0.5: ×4 en vez de ×2 | 🔴 |
| **ruido / temperatura** | `temperature` ∈ [0.01,0.20] | EM: ruido `~ √(2·D·dt)` | rama legacy `:466` `√(2·η·T)·N(0,1)` ✓ ; rama stepper `:446` `diffusion=√(2T)` y el *stepper* aplica `dt` | ✓ equivalente **[DIN]** verificar que el stepper multiplique por `√dt` y no por `dt` | 🟡 |
| **multiplicador EWS** | `_ews_fallback_multiplier:66`, CfC `:392` | acotado | fallback `min(mult, 2.0)`; CfC `clip(0.5, 2.0)` | ✓ acotado, sin NaN | — | ⚪ |
| **clipping de opiniones** | `:471` `np.clip(new, min, max)` | frontera reflectante o absorbente declarada | clip duro cada paso | Acumula masa en ±1 → **sesga la varianza a la baja y fabrica "consenso"**; rompe el balance detallado del SDE | 🟠 |
| **polarización** | `unified_metrics.py:47-73` `std/half_range`, clip [0,1] | 0=consenso, 1=máxima división | ✓ correcto, invariante a traslación | — | ⚪ |

## 4.3 Motor multicapa 5D (Langevin sociodemográfico)

| Variable | Definición | Relación esperada | Real | Desviación | Sev. |
|---|---|---|---|---|---|
| **fuerza social** | `:352-357` (denso) y `:402` (esparso) | término de consenso `λ·(x̄_vecinos − x_i)`, como en `energy_engine:461` | `social_force = coupling·w·Σ_j A_ij·x_j` — **sin normalizar por grado y sin `− x_i`** | **C-02**: (i) escala con el grado medio (N·p = 300 en la config por defecto) ⇒ `dt·social ≈ 0.9·x̄` por paso ⇒ saturación inmediata; (ii) no es una fuerza de consenso sino un **sesgo aditivo** proporcional a la opinión agregada; (iii) **incoherente con el otro motor** pese a `test_cross_engine_polarization.py` | 🔴 |
| **matriz de acoplamiento 5×5** | — | el prompt pide verificar simetría y autovalores | **No existe.** El acoplamiento social sólo toca `COL_OPINION` (`:356`, `:402`); las otras 4 dimensiones evolucionan sólo por `−∇U + ruido` | No hay acoplamiento inter-dimensional en la red; el "multicapa 5D" es 1D en lo social | 🟠 |
| `θ` (theta) × `_STOCHASTIC_SCALE` | `_STOCHASTIC_SCALE=0.1` (`:66`); θ de literatura (`:50-54`) | ruido ≥ 0 | `θ·0.1·η·√dt` — EM correcto | **[DIN]** verificar `θ ≥ 0` en `build_theta_matrix` | 🟡 |
| `grad[COL_INCOME]` | `:318` `0.5·(inc−0.5)·(1+hier)` | ingreso debe poder dispersarse (Gini) | `−grad` empuja **todo ingreso a 0.5** | El modelo **no puede generar desigualdad de ingreso**: la distribución colapsa a una delta en 0.5, contradiciendo el acoplamiento Gini | 🟠 |
| ídem, docstring | `:317` «con fricción por jerarquía» | fricción = frena | `(1+hier)` **amplifica** la fuerza restauradora ⇒ más jerarquía = vuelta **más rápida** al centro | Nomenclatura invertida respecto al efecto | 🔵 |
| `grad[COL_HIER]` | `:315` | atractores en 0 y 1, repulsor en 0.5 | ✓ verificado analíticamente | — | ⚪ |
| `grad[COL_COOP]`, `grad[COL_INFO]` | `:311`, `:321` | relajación a `0.8·align` y a `0.5+0.2·coop` | ✓ signos correctos | — | ⚪ |

## 4.4 LOD / super-agentes / cuantización (massive_engine)

| Variable | Definición | Relación esperada | Real | Desviación | Sev. |
|---|---|---|---|---|---|
| cuantización uint8 | `:265-308` | sin sesgo direccional | `np.round` (banker's) + `clip` ⇒ **insesgado**; precisión 2/255 ≈ 0,0078 coincide con el docstring | — | ⚪ |
| cuantización **por paso** | `quantize=True` almacena uint8 **entre pasos** (`:12`, `:866`) | el paso de integración debe superar el cuanto | con `dt=0.01` y deriva O(1), `Δx ≈ 0.01` vs cuanto `0.0078` ⇒ margen ×1,3 | **Zona muerta**: con derivas más suaves o `dt` menor, la dinámica **se congela** y el sistema aparenta equilibrio. Sin guardia ni aviso | 🟠 |
| conservación al agregar | `build_aggregated_super_agents:654` `raise RuntimeError` si los conteos no suman N | población conservada | ✓ comprobación explícita de N | **[DIN]** falta verificar conservación de **media y varianza** | 🟡 |

## 4.5 Corrector residual CfC

| Aspecto | Evidencia | Problema | Sev. |
|---|---|---|---|
| Fórmula documentada vs implementada | docstring `:367` «`final(t) = ŷ(t) + r̂(t)`» vs código `:441` `corrected = sim_val − correction` | **signo opuesto** al documentado | 🟠 |
| Uso del modelo | `:429` calcula `r_hat`; `:436-439` si `actual is not None` ⇒ `correction = 0.5·(sim−actual)` y **`r_hat` se descarta** | **C-03 — fuga de etiqueta**: `corrected = 0.5·sim + 0.5·actual`. No hay predicción, hay interpolación a la respuesta | 🔴 |
| Etiqueta de procedencia | `:442` devuelve `"cfc"` en ambas ramas | el consumidor **no puede distinguir** modo-fuga de modo-modelo | 🟠 |
| Calidad declarada | docstring `:369` «R² = −18.7 per-step (poor point-wise generalization)» | se embarca como «corrector calibrado» un modelo **peor que predecir la media** | 🟠 |
| Parámetro ignorado | `:414` `sim_series = hist_arr` en la rama multi-valor | el argumento **`simulated` se descarta** silenciosamente | 🟠 |
| Off-by-one en lags | `:424` `residuals[-1-i] if len(residuals) > i+1 else 0.0` | con `len==1` el lag 0 se rellena con 0 en vez de usar `residuals[-1]`; debería ser `> i` | 🟡 |
| Constante mágica | `:416` `np.full(n, 0.0426)` «training mean» | valor hardcodeado sin trazabilidad a `models/cfc_calibrated/` | 🔵 |
| Paridad engine/router/trainer | `cfc_router` carga `cfc_residual.pt`; `energy_engine:206` busca `cfc_temperature.pt` con fallback a `models/cfc_temperature.pt` | **`models/cfc_calibrated/cfc_temperature.pt` no existe** en el repo (sólo `cfc_residual.pt`) ⇒ el modulador de temperatura **siempre cae al fallback por reglas** | 🟠 |

## 4.6 Asimilación de datos (EnKF)

| Aspecto | Evidencia | Problema | Sev. |
|---|---|---|---|
| Inflación de covarianza | `kalman.py:95` `P = AᵀA/(n−1)` | **no existe inflación**. Con ensambles pequeños el EnKF subestima la dispersión y **diverge** (colapso del filtro) | 🟠 |
| Localización | — | **no implementada**. Sin localización aparecen correlaciones espurias a larga distancia | 🟠 |
| Tamaño de ensamble | `n_ensemble=100` por defecto, mínimo 2 | `n_ensemble=2` pasa la validación y produce una covarianza de rango 1 | 🟡 |
| Ganancia de Kalman | `:97` `pinv(innovation_covariance)` | ✓ robusto a singularidad | ⚪ |
| Determinismo | `:39` `self.rng = rng or np.random.default_rng()` | **sin semilla por defecto** ⇒ viola el invariante de determinismo | 🟠 |
| Rendimiento | `:66`, `:99` bucles Python sobre miembros; `multivariate_normal` **dentro** del bucle | O(n_ens) llamadas a descomposición de Cholesky por actualización | 🟡 |

## 4.7 Paridad Rust ↔ Python

| Función | Python (`massive_core/rust_core.py`) | Rust (`rust_core/src/lib.rs`) | Veredicto |
|---|---|---|---|
| `multi_potential_gradient` | `:37-51` | `:18-48` | **Idéntica término a término** ✅ (verificado línea a línea: bimodal `4x(x²−0.49)`, coop, hier, income, info) |
| — | — | — | ⚠ **Triplicada**: existe una **tercera** implementación en `multilayer_engine.py:283-323` (bucle por agente). Las tres coinciden hoy; nada impide que diverjan |
| `langevin_opinion_update_inplace` | `:76-95` | `:64-96` | Fórmula idéntica. **Pero** `:76` hace `np.asarray(agents, dtype=np.float64)`: si el llamante pasa float32 / no contiguo, **se crea una copia y la actualización "in-place" se pierde silenciosamente** 🟠 |
| `active_mask_step` | `:115-128` | `:100-142` | Fórmula consistente **[DIN]** |
| Comportamiento ante `ncols==0` | fallback: `IndexError` | Rust: `ValueError` explícito | Divergencia de errores 🔵 |
| Paridad numérica real | — | — | **[DIN]** — no compilable aquí; no hay test de paridad que compare ambas rutas con tolerancia |

## 4.8 Configuración, semillas y determinismo

| Variable | Dónde se define | ¿Se consume? | Desviación | Sev. |
|---|---|---|---|---|
| **todo `.env`** | `.env.example` (42 vars) | **NO** — `load_dotenv()` no aparece en ningún `.py` | **C-07**: configuración documentada y montada en Docker pero **nunca cargada** | 🔴 |
| `MASSIVE_MAX_UPLOAD_MB` | `.env.example:15` | `api.py:115` ✅ · `backend/app/routers/llm.py:38,193` **hardcodea 10 MB dos veces** | el canónico ignora la variable | 🟡 |
| `MASSIVE_API_KEY` vs `MASSIVE_API_KEYS` | `.env.example:8` y `:60` | sólo se lee el **singular** | la variable plural está documentada y **no existe en código** | 🟡 |
| `MASSIVE_ALLOWED_HOSTS` | `.env.example:59` | `main.py:104-108` | **C-08**: ambas ramas del condicional hacen `return await call_next(request)` ⇒ **si la variable no está definida, la validación de Host es un no-op también en producción**, contra el docstring. Rama duplicada muerta | 🟠 |
| `MASSIVE_RATE_LIMIT_PER_MIN`, `_BACKEND`, `_PATH`, `MASSIVE_MAX_BODY_MB`, `MASSIVE_CORS_ORIGINS`, `MASSIVE_ENV` | varios | leídos **a nivel de módulo** (`security.py:76,78`; `main.py:59,85,108,88`) | se congelan en el import; cambiar el entorno después no tiene efecto (afecta tests y recargas) | 🟡 |
| `PYTHONHASHSEED` | `.env.example:19` | `benchmarks/massive_real.py:43` hace `os.environ["PYTHONHASHSEED"]=str(seed)` **en tiempo de ejecución** | **No tiene ningún efecto**: debe fijarse antes de arrancar el intérprete. Determinismo aparente | 🟠 |
| semillas | `default_rng(seed)` en motores ✅ | `benchmarks/runner.py:503` mezcla `np.random.seed` (global legacy) con `default_rng` | dos fuentes de aleatoriedad conviviendo | 🔵 |
| `torch.manual_seed` | — | **nunca se llama** | inferencia CfC es determinista (estado inicial `zeros`), pero el entrenamiento no es reproducible | 🟡 |

---

# 5. HALLAZGOS POR CATEGORÍA (orden de severidad)

## 🔴 CRÍTICOS

### C-07 · `.env` nunca se carga — la API queda inoperativa en Docker
**Categoría:** error / seguridad / infra · **Evidencia [HECHO]:**
```
$ grep -rn "load_dotenv" --include=*.py .     → (vacío)
pyproject.toml:20        "python-dotenv>=1.0.1",     (dependencia CORE)
README.md:48,82          cp .env.example .env
docker-compose.yml:19    - ./.env:/app/.env:ro
docker-compose.yml:22    environment: - MASSIVE_ENV=${MASSIVE_ENV:-development}
```
**Cadena de consumo:** `docker compose up` → sólo `MASSIVE_ENV` entra por `environment:` → `MASSIVE_API_KEY` sigue sin definir → `backend/app/security.py:56-68` → `is_dev_fallback_allowed()` falso (`MASSIVE_DEV_FALLBACK` tampoco cargado) → **HTTP 503 en todos los `/v1/*`**.
**Por qué CI no lo detecta:** `docker-e2e.yml:48-52` sólo hace smoke de `/health` y `/version`, ambos **sin autenticación**.
**Corrección sugerida:** llamar `load_dotenv()` una vez en `backend/app/main.py` y en `api.py` antes de las lecturas de entorno a nivel de módulo; o declarar `env_file: .env` en `docker-compose.yml`; y añadir al smoke de CI una llamada autenticada a `/v1/simulate`.

### C-09 · El `Dockerfile` referencia archivos inexistentes y excluidos
**Categoría:** error / infra · **Evidencia [HECHO]:** `Dockerfile` ejecuta `COPY nginx.conf …` y `COPY supervisord.conf …`; ambos están en `docs/archive/legacy_docker/`, y `.dockerignore` contiene `docs/`. `CMD` arranca `supervisord -c /etc/supervisor/conf.d/supervisord.conf`.
**Impacto:** build imposible → `docker-compose.yml` inservible → `docker-e2e.yml` en rojo → README incumplido.
**Corrección sugerida:** restaurar ambos `.conf` a la raíz (fueron movidos en la «limpieza integral» sin actualizar el Dockerfile) o eliminar la dependencia de nginx/supervisord.

### C-03 · El corrector CfC interpola hacia la verdad conocida (fuga de etiqueta)
**Categoría:** correlación-variables / validez científica · **Evidencia [HECHO]** `cfc_router.py:429-441`:
```python
r_hat = float(self._residual(x, u_tensor, dt=dt).item())   # 429  ← se calcula…
if actual is not None:
    baseline_error = sim_val - float(actual_arr.ravel()[-1])  # 437
    correction = 0.5 * baseline_error                          # 438  ← …y se IGNORA
else:
    correction = r_hat
corrected = sim_val - correction        # 441 ⇒ 0.5·sim + 0.5·actual
```
**Impacto:** toda evaluación con ground truth mide la interpolación, no el modelo. El docstring reconoce `R² = −18.7`. Las conclusiones de `brexit_calibration.py` y de `docs/research/calibration_log.md` quedan **no sostenidas**.
**Corrección sugerida:** eliminar la rama con `actual`; evaluar exclusivamente con `r_hat` en *walk-forward* fuera de muestra; devolver `source="leakage"` si se mantiene por compatibilidad.

### C-02 · Fuerza social sin normalizar por grado y sin término de consenso
**Categoría:** correlación-variables · **Evidencia [HECHO]** `multilayer_engine.py:352-357`:
```python
for j in range(N):
    s += layers_flat[ell, i, j] * x_vec[j, COL_OPINION]
social_force[i, COL_OPINION] += coupling * w * s
```
contra `energy_engine.py:461`: `social_drift = self.lambda_social * (neighbor_mean - opinions)`.
**Impacto cuantitativo:** con N=1000, p=0.3, `coupling=0.3`, `dt=0.01` → `dt·coupling·Σ ≈ 0.9·x̄` por paso: saturación en ≤2 pasos. El `clip` posterior (`:368-376`) convierte la divergencia en una falsa «polarización total».
**Corrección sugerida:** `social_force = coupling·w·(A@x/deg − x_i)`, equiparándola a la del motor de energía; añadir un test de invariancia al grado medio.

### C-01 · σ inconsistente entre dinámica y energía reportada
**Categoría:** correlación-variables · **Evidencia [HECHO]:** `energy_engine.py:410` `sigma2 = effective_sigma(self.gini_coefficient)**2` (dinámica) vs `:98` `sigma2 = _SIGMA**2` dentro de `_landscape_gradient`, y `:630` `_landscape_energy(...)` con `_SIGMA` fijo, usado por `system_metrics`.
**Impacto:** para cualquier `gini ≠ 0.35` la energía total/media devuelta al cliente corresponde a **otro potencial**. `energia_total` es el campo que la GUI y los benchmarks usan como diagnóstico de estabilidad.
**Corrección sugerida:** parametrizar `_gaussian/_landscape_gradient/_landscape_energy` con `sigma` y pasar siempre `effective_sigma(gini)`.

### C-10 · Capa de datos del frontend desconectada
**Categoría:** desconectado / GUI · **Evidencia [HECHO]:** `App.tsx` tiene 32 líneas e importa sólo `Routes/Route` y `Button`; ningún archivo importa `services/api.ts`, `hooks/useApi.ts` ni `lib/utils.ts`.
**Impacto:** no existe GUI operativa; los checks `frontend-build` y `validate_ts_types` pasan sobre código que nadie ejecuta.

## 🟠 ALTOS

| ID | Hallazgo | Evidencia | Corrección sugerida |
|---|---|---|---|
| **A-01** | `useApi.execute` pasa `AxiosRequestConfig` en la posición de **`data`** | `useApi.ts:36` castea `api[method]` a `(url, config)`; pero `ApiService.post(url, data, config)` (`api.ts:62`) | Firmar `execute(data?, config?)` y despachar por método |
| **A-02** | Clave `dev-secret-key` **cableada en el bundle** del frontend | `api.ts:35-38` | Eliminar; exigir `VITE_MASSIVE_API_KEY` |
| **A-03** | `validate_host_header` es no-op también en producción | `main.py:104-108` (dos ramas idénticas) | Fail-closed cuando `_is_dev` es falso y no hay allowlist |
| **A-04** | **`api.py` carece de todo el middleware de seguridad**: sin límite de body, sin `X-Request-ID`, sin validación de Host, sin métricas, sin deprecación | `api.py` no registra ningún `@app.middleware` | Retirar la app legacy o montarla tras el mismo stack |
| **A-05** | `api.py` expone `/docs`, `/redoc`, `/openapi.json` **siempre** (FastAPI por defecto); el canónico los desactiva fuera de dev (`main.py:79-81`) | `api.py:27` | `docs_url=None` fuera de dev |
| **A-06** | `api.py:/ready` devuelve **503 sin clave LLM**; el canónico devuelve 200 «degraded» | `api.py:206-207` vs `main.py:220-222` | Unificar: LLM es opcional ⇒ nunca 503 |
| **A-07** | Intervalo de confianza **fabricado**: `±0.05` constante | `api.py:326-333` `confidence_lower = p_event − 0.05`, `polarization = 0.0` hardcodeado | Derivar el IC del modelo o no exponerlo |
| **A-08** | `random_network` asigna `rng.random((N,N))` **completa** antes de quedarse con la triangular | `energy_engine.py:671-678`; el tope `_DENSE_CAP=50_000` implica **20 GB** en float64, no los «12 GB» del comentario | Generar sólo la triangular superior; recalcular el tope |
| **A-09** | Núcleo denso multicapa con **triple bucle Python** O(L·N²) | `multilayer_engine.py:351-357` (3 M iteraciones/paso con N=1000, L=3) | Sustituir por `layers_flat[ell] @ x[:,0]` |
| **A-10** | EnKF sin inflación ni localización, y **sin semilla por defecto** | `kalman.py:39,95` | Añadir `inflation` y `localization_radius`; exigir `rng` |
| **A-11** | `PYTHONHASHSEED` fijado en runtime (sin efecto) | `benchmarks/massive_real.py:43` | Fijarlo en el wrapper/Makefile/CI |
| **A-12** | `langevin_opinion_update_inplace` puede escribir sobre una **copia** | `massive_core/rust_core.py:76` | Validar `agents.dtype == float64 and agents.flags.writeable`, si no `raise` |
| **A-13** | El clip duro del SDE sesga varianza y fabrica consenso | `energy_engine.py:471`; `multilayer_engine.py:368-376` | Documentar como frontera reflectante y medir el sesgo |
| **A-14** | Modulador de temperatura CfC: el checkpoint que busca **no existe** | `energy_engine.py:206-208` busca `cfc_temperature.pt`; en `models/cfc_calibrated/` sólo hay `cfc_residual.pt` | Publicar el peso o eliminar la rama |

## 🟡 MEDIOS (extracto)

| ID | Hallazgo | Evidencia |
|---|---|---|
| M-01 | Allowlist de subida **divergente** entre apps y respecto a la documentación: `api.py:116` `{pdf,json,csv,xlsx,txt,md}` vs `llm.py:37` `{pdf,json,csv,xlsx,docx}` vs docstrings «pdf/json/csv/xlsx» | 3 contratos distintos |
| M-02 | `_safe_suffix` se valida **después** de leer los 10 MB en el canónico | `llm.py:201-210` |
| M-03 | `content += chunk` en bucle → O(n²) de copias | `llm.py:206`, `api.py:180` |
| M-04 | `_MAX_UPLOAD_BYTES` definido **dos veces** en el mismo archivo | `llm.py:38` y `:193` |
| M-05 | Middleware `deprecation_warning` **nunca dispara**: marca `/api/*` no-`/api/v1`, y `backend/app` no expone ninguna ruta así | `main.py:155-159` |
| M-06 | `/ready` instancia el adaptador UIL **en cada sondeo** | `main.py:209-215` (k8s sondea cada 10 s) |
| M-07 | `/metrics` exige `X-API-Key`; Prometheus no lo envía por defecto | `main.py:299` vs `monitoring/prometheus/alerts.yml` |
| M-08 | `FACTBOOK_TO_MASSIVE` (90 líneas) **no lo ejecuta nadie** y **contradice** la implementación viva (herfindahl vs 1−herfindahl; lambda de fiscalidad invertida) | `mappings.py:311-403` |
| M-09 | Cuatro topes contradictorios de `n_agents` (100 k / 200 k / 50 k / 100 M) | §4.1 |
| M-10 | Lecturas de entorno a nivel de módulo congelan la configuración | §4.8 |
| M-11 | Gradiente multipotencial **triplicado** (Rust, wrapper NumPy, multilayer) | §4.7 |
| M-12 | `torch.load` **sin `weights_only`** en los ejemplos de entrenamiento | `docs/examples/train_cfc_landscape.py:324`, `train_cfc_temp.py:321` |
| M-13 | Contrato LLM: sólo `temporal_horizon_days` dispara 422; el resto se adivina | `llm.py:104` |

## 🔵 BAJOS
Nomenclatura «fricción» invertida (`multilayer_engine.py:317`) · constante mágica `0.0426` · `create_5d_demographic_matrix` muta su entrada · divergencia de errores Rust/NumPy ante `ncols==0` · README con cifras obsoletas (530 tests) y enlace roto a `docker-compose.single.yml` · doble fuente de RNG en `benchmarks/runner.py` · `api.py` cachea el adaptador en un global sin invalidación · `EnKF` admite `n_ensemble=2` · `_ALLOWED_EXT` no cubre `.docx` en la ruta legacy.

## ⚪ INFORMATIVO — buenas prácticas confirmadas
1. **Cero `except:` desnudos**, cero `eval`/`exec`/`pickle.load`/`yaml.load` inseguros en todo el árbol.
2. `torch.load(..., weights_only=True)` en **todo el código de producción**.
3. Comparación de claves en **tiempo constante** real (`hmac.compare_digest`, `api_auth.py:66-78`) y gate de fallback **de dos factores** (`is_dev_fallback_allowed`) — correctamente fail-closed cuando `MASSIVE_ENV` está sin definir.
4. CORS filtra el comodín `*` explícitamente antes de habilitar credenciales (`main.py:88`).
5. `calculate_polarization` es dimensionalmente correcta e invariante a traslación.

---

# 6. INVENTARIO DE CÓDIGO MUERTO / DESCONECTADO

| Ruta | Tipo | LOC | Evidencia |
|---|---|---:|---|
| `social_connectors.py` | módulo | 332 | **cero menciones** en todo el repo; arrastra `tweepy`/`praw` |
| `benchmark_scalability.py` | módulo | 908 | sin imports; sólo citado en docs archivadas |
| `benchmarks/bench_perf_f.py` | módulo | — | única mención en `docs/archive/reports/REPORT_STRUCTURE.md:124` |
| `frontend/src/hooks/useApi.ts` | 6 hooks | 72 | sin importadores |
| `frontend/src/services/api.ts` | 9 métodos | 200 | sin importadores |
| `frontend/src/lib/utils.ts` | helper | 6 | sin importadores |
| `api.py` completo | 10 endpoints | 506 | ningún cliente tras la migración del frontend a `/v1` |
| `massive_core/.../mappings.FACTBOOK_TO_MASSIVE` | tabla | ~90 | exportada en `__all__`, nunca ejecutada |
| `mappings.herfindahl_index` | función | 7 | sólo la usa `diversity_index` |
| `main.py:deprecation_warning` | middleware | 15 | condición inalcanzable |
| `main.py:104-108` | rama `if` | 5 | las dos ramas son idénticas |
| `cfc_router.py:429` `r_hat` | variable | 1 | calculada y descartada en la rama con `actual` |
| `POST /v1/benchmarks`, `/v1/llm/run_simulation`, `/openapi/v1.json` | endpoints | — | sin consumidor |
| Módulos sólo con consumo en tests | — | ~900 | `brexit_calibration`, `visualizations`, `micro_schemas`, `metalearning.cfc_training_data`, `multiscale.hierarchical_time` |

**Total estimado: ≈ 3.100 LOC desconectadas** (6,7 % del Python del repo).

---

# 7. OPTIMIZACIONES PRIORIZADAS

| # | Optimización | Impacto | Esfuerzo | Evidencia |
|---|---|---|---|---|
| 1 | Vectorizar el núcleo denso multicapa (`Σ_j` → `A @ x`) | **~100–1000×** en el paso denso | S | `multilayer_engine.py:351-357` |
| 2 | Generar sólo la triangular superior en `random_network` | **−50 % memoria y tiempo**; elimina el riesgo de OOM de 20 GB | S | `energy_engine.py:671-678` |
| 3 | Vectorizar el bucle de miembros del EnKF y sacar `multivariate_normal` del bucle | O(n_ens) Cholesky → 1 | S | `kalman.py:66,99-102` |
| 4 | `bytearray`/`BytesIO` en lugar de `content += chunk` | O(n²) → O(n) en subidas de 10 MB | S | `llm.py:206`, `api.py:180` |
| 5 | Cachear el adaptador UIL en `/ready` | evita instanciar un cliente LLM en cada sondeo | S | `main.py:209-215` |
| 6 | Unificar las 3 implementaciones del gradiente multipotencial | mantenibilidad; elimina riesgo de deriva silenciosa | M | §4.7 |
| 7 | Retirar `api.py` y las 3 huérfanas duras | **−1.750 LOC**, −2 dependencias (`tweepy`,`praw`) | M | §6 |

---

# 8. PLAN DE REMEDIACIÓN POR FASES

### Fase A — Bloqueantes (el producto no funciona)
1. **C-07** invocar `load_dotenv()` / `env_file:` en compose · 2. **C-09** restaurar `nginx.conf` y `supervisord.conf` · 3. **H-01** alinear `simulateUil()` con `SimRequest` · 4. **C-10** conectar la GUI o declararla explícitamente como demo · 5. Endurecer el smoke de `docker-e2e` con una llamada **autenticada**.

### Fase B — Validez científica (los resultados no son defendibles)
6. **C-03** eliminar la fuga de etiqueta del CfC y re-evaluar *walk-forward* · 7. **C-02** normalizar la fuerza social por grado y añadir el término `−x_i` · 8. **C-01** unificar σ entre dinámica y energía · 9. **C-04** aplicar el factor Gini una sola vez y elegir una única ley · 10. **A-10** inflación + localización + semilla en el EnKF · 11. **C-05** valor neutro (no máximo) ante datos de diversidad ausentes · 12. **A-07** eliminar el IC fabricado de ±0.05.

### Fase C — Seguridad y contratos
13. **A-03** host-header fail-closed · 14. **A-02** quitar `dev-secret-key` del bundle · 15. **A-04/A-05/A-06** retirar `api.py` o igualar su stack de seguridad · 16. **M-01** una sola allowlist de extensiones · 17. **M-05/M-07** middleware muerto y acceso de Prometheus a `/metrics` · 18. **A-11** `PYTHONHASHSEED` desde el entorno.

### Fase D — Deuda
19. Eliminar las ~3.100 LOC desconectadas · 20. Desmontar el alias `/api/v1` · 21. Unificar el gradiente triplicado · 22. Borrar o ejecutar `FACTBOOK_TO_MASSIVE` · 23. Subir `fail_under` por encima de 30 y cubrir motores numéricos · 24. Corregir README (530 tests, enlace roto) · 25. Añadir semgrep si se quiere sostener lo documentado.

---

# 9. PENDIENTES DE VERIFICACIÓN DINÁMICA [DIN]

1. `docker compose build` — confirmar el fallo en el `COPY nginx.conf` y revisar el último run de `docker-e2e.yml`.
2. `pytest tests/ -q --cov` — cobertura real frente al `fail_under = 30`; cuántos de los 689 tests se **saltan** sin torch ni pesos CfC (hay 33 marcas `skipif`, la mayoría ligadas a `models/cfc_*`).
3. Paridad numérica Rust↔Python: compilar con maturin y comparar las tres rutas con tolerancia; **no existe test de paridad**.
4. Verificar que `massive_core.numerics.steppers` aplique `√dt` (y no `dt`) a la difusión, para confirmar la equivalencia de las dos ramas de `energy_engine.step`.
5. Confirmar que `build_theta_matrix` produce θ ≥ 0.
6. Medir la zona muerta de la cuantización uint8: ejecutar `MassiveSimEngine(quantize=True)` con `dt` decreciente y comprobar en qué punto la dinámica se congela.
7. Comprobar conservación de media y varianza en `build_aggregated_super_agents`.
8. `ruff check . && black --check . && mypy` — el informe no ejecutó linters.
9. Auditoría de secretos históricos: **imposible aquí** (el clon tiene 1 commit). Ejecutar gitleaks sobre el historial completo en origen.
10. `pip-audit` / `npm audit` sobre `uv.lock` y `package-lock.json`.
11. Confirmar en caliente que `/v1/*` responde 503 en un contenedor levantado con sólo `.env` (demostración de C-07).

---

# 10. CHECKLIST FINAL

- [x] ¿Recorrí todos los motores de la raíz y `massive_core/`? — sí, salvo el interior de `simulator.py` (declarado en §1.3).
- [x] ¿Comparé `api.py` legacy vs `backend/app/` canónico? — 6 divergencias (A-04…A-07, M-01, M-05).
- [x] ¿Tracé cada parámetro de config/Factbook hasta su consumo? — §4.1 y §4.8; hallazgo central: `.env` no se carga.
- [x] ¿Verifiqué paridad Rust↔Python y CfC engine/router/trainer? — §4.5 y §4.7; paridad del gradiente confirmada por lectura, la numérica queda en [DIN].
- [x] ¿Inventarié endpoints y llamadas y los crucé? — §3.
- [x] ¿Revisé `useApi.ts`, validación de forms y 422/503/429? — §3.1, A-01, A-02; **no hay formularios**: la GUI es un esqueleto.
- [x] ¿Confirmé que `massive-ui-ng/` no esté huérfano ni duplicado? — **no existe** (eliminado el 2026-09-22).
- [x] ¿Verifiqué fail-closed, auth en tiempo constante y ausencia de fallback dev en producción? — auth correcta (⚪3); fallos en host-header (A-03) y en el bundle del frontend (A-02).
- [x] ¿Cada hallazgo tiene archivo:línea, severidad, impacto y corrección? — sí.
- [x] ¿Separé hechos, inferencias y pendientes dinámicos? — sí; §9 lista 11 pendientes.
