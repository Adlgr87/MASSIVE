# Auditoría integral del proyecto MASSIVE — 2026-09-22

> Informe puntual generado por el agente de Arena.ai (rama `arena/01a0c972-massive`).
> Estado del repo analizado: commit `9428a89` (main). 568 archivos, 251 Python, 117 Markdown.
> Tests al momento del análisis: 679 pasan / 0 fallan (pero hay código roto no cubierto, ver A-1).

---

## ⚡ ESTADO DE IMPLEMENTACIÓN (actualizado al cierre)

**Todas las olas ejecutadas.** Resultado final:

- **Tests: 694 pasan / 0 fallan** (679 originales + 15 nuevos de invariantes de correlación).
- **Respaldo:** tag `pre-cleanup-2026-09-22` (push a origin) con el estado previo a la limpieza.
- **Ola 1 (bugs):** A-1…A-13 ✅ — CLI reparado, polarización bipolar corregida (0.8→0.4),
  Gini→ingreso monótono con media 0.5, factibilidad fiscal en dirección correcta
  (déficit→0.30, equilibrado→0.50, superávit→0.70), Gini→σ implementado y anclado,
  `social_pressure_weights` conectado al acoplamiento (0.8×–1.2×), docstrings de θ
  veraces, escala `income_scale` unificada, `propose_landscape` con contrato válido,
  doble muestreo de ruido eliminado, `.env.example` y README limpios, torch-guard en
  `cfc_engine`. Nueva suite `tests/test_correlation_invariants.py` bloquea direcciones
  y magnitudes.
- **Ola 2 (duplicados/basura):** ✅ — `massive-ui-ng/` eliminado (tag de respaldo),
  workflows Azure + HF borrados (11 workflows), 5 stubs raíz eliminados con 12 imports
  migrados a `massive.core.*`, `py_modules` del pyproject corregido (listaba 3 módulos
  inexistentes), demo JSX huérfana (825 líneas) eliminada, `reports/` reducido a
  `audit_baseline.json` + dir de runtime, 27 archivos de artefactos borrados y 46
  archivados en `docs/archive/`.
- **Ola 3 (agentes):** ✅ — de ~1.095 coincidencias a 79 funcionales (cliente LLM del
  producto, seguridad, ubicación canónica). `CLAUDE.md` eliminado, `Autor: MASSIVE
  Research` eliminado de 16 archivos, CODEOWNERS y PULL_REQUEST_TEMPLATE sin
  referencias a agentes, narrativa de audit neutralizada, `.github/agents/` con README
  como única ubicación canónica (decisión del owner).
- **Ola 4 (docs):** ✅ — 44 .md activos (antes 117), `docs/factbook.md` consolidado,
  `mkdocs.yml` solo con docs de usuario, `current-state.md` reverificado 2026-09-22
  (afirmaciones caducas corregidas), `check_docs_refs.py` verde.
- **Ola 5 (verificación):** ✅ — pytest 694/0, ruff + black limpios, CLI smoke OK,
  API en vivo OK (`/health`, `/ready`, `/v1/simulate`, `/v1/llm/run_simulation` con
  detección de país → Brasil: gini 0.534, presión social derivada, motor energy_engine).

Este archivo es el registro del trabajo; puede borrarse o moverse a `docs/archive/`
una vez revisado.

---

## A. DEFECTOS FUNCIONALES (críticos)

| ID | Severidad | Hallazgo | Evidencia |
|----|-----------|----------|-----------|
| A-1 | 🔴 CRÍTICO | **CLI roto**: `massive/cli/main.py` tiene un marcador de conflicto de merge huérfano (`<<<<<<< HEAD` en línea 20) + línea `log = logging.getLogger(__name__)` duplicada. `python -m massive.cli` ni siquiera compila. Ningún test lo cubre. | `python -m compileall` falla; SyntaxError línea 20 |
| A-2 | 🔴 CRÍTICO | **Polarización duplicada en rango bipolar** (motor escalar, path por defecto de `/v1/simulate`): `resumen_historial()` pasa la etiqueta humana `"[-1, 1] — Bipolar"` como `range_type` a `calculate_partisanship()`, que solo reconoce la cadena literal `"bipolar"` → cae en la rama unipolar (half_range 0.5 en vez de 1.0). **Reproducido: opiniones [0.2,0.4,0.6] bipolares reportan 0.80 en vez de 0.40 (2× el valor real).** Afecta `summary.polarizacion_media` de la API, CLI y services. | Repro ejecutado: bipolar → 0.8 (esperado 0.4) |
| A-3 | 🔴 CRÍTICO | **Correlación Gini→ingreso invertida/no monótona** en `massive_engine.initialize_agents()`: `income ~ Beta(2(1-g), 2g)` ⇒ media del ingreso = `1-gini` (¡más Gini = país entero más pobre, el Gini no dice nada del nivel de ingreso!) y la **dispersión** (lo que el comentario dice querer) es no-monótona: máxima en g=0.5 y con g=0 (igualdad perfecta) sigue habiendo σ≈0.22 de dispersión de ingreso. Con g→1 la dispersión además *baja*. | `massive_engine.py:180-182`; Beta(a,b) con a+b=2 |
| A-4 | 🔴 CRÍTICO | **Correlación fiscal invertida**: `fiscal_constraint` se deriva como `1 − (signo_superávit)·0.1` ⇒ **déficit → 1.0 (máxima "feasibility"), superávit → 0.9, presupuesto equilibrado → 0.5**. Se usa como presupuesto de intervención (`max_density = feasibility/scale`): un país en déficit recibe el MAYOR presupuesto de intervención y se reporta como el más sano (`fiscal_health`). Dirección exactamente opuesta a la real. | `massive/core/factbook/context.py::_derive_massive_params`; `intervention_optimizer.py:122-130` |
| A-5 | 🟠 ALTO | **Gini declarado pero sin efecto real en EnergyEngine**: comentarios contradictorios — `create_gini_adjusted_landscape()` dice "Gini's effect is wired in step() (σ↓)"; `step()` dice "handled via propose_lambda() y EWS". **Ninguno de los dos es cierto**: `step()` no usa gini, y `propose_lambda()` es camino muerto porque los modelos `cfc_temperature.pt` / `cfc_lambda_corrector.pt` / `cfc_landscape.pt` **no existen** en `models/cfc_calibrated/` (solo existe `cfc_residual.pt`). El único efecto real de gini en energía es vía `inequality_factor → lambda_social`. | `energy_engine.py:139-144, 385-390, 455-460`; ls models/ |
| A-6 | 🟠 ALTO | **`social_pressure_weights` = correlación muerta**: se deriva (diversidad → presión social: `1 − diversidad`), se guarda, se pasa a `MassiveEngine.from_factbook`… y **ninguna dinámica la consume**. Cable sin conectar. | grep: solo asignación en context.py:118 y config en massive_engine.py:168 |
| A-7 | 🟠 ALTO | **`theta` sociodemográfico solo modula ruido**: docstrings de `compute_theta()` afirman que religion/educación/edad escalan "el ruido **y la sensibilidad**" (educación→cooperación, edad→autoridad, etc.), pero en la dinámica (`multilayer_langevin_step`) theta **solo multiplica el término estocástico**. Efectos de nivel anunciados (educación↑ → cooperación↑) no existen en las ecuaciones; lo único implementado es volatilidad. Documentación de física ≠ física. | `multilayer_engine.py:230-262 vs 411-470` |
| A-8 | 🟡 MEDIO | **Inconsistencia de escala del mismo concepto**: `income_scale = log1p(ingreso)/10` en `create_wealth_potential()` pero `/15` en `create_economic_landscape()`. Además defaults contradictorios: atractor `1.35` en el motor vs `1+2·polarización` (=1.7 para gini 35) en el mapeo. | `mappings.py:511` vs `energy_engine.py:527` |
| A-9 | 🟡 MEDIO | **`propose_landscape()` viola su contrato**: docstring dice "Falls back to original values" pero retorna `None` cuando no hay modelo (siempre). Callers deben manejar `None` no documentado. | `energy_engine.py:262-266` |
| A-10 | 🟡 MEDIO | **Doble muestreo de ruido en `energy_engine.step()`**: en el path del stepper se muestrea `noise` (línea ~375) y se descarta; luego se muestrea `step_noise`. RNG consumido innecesariamente y streams divergentes entre paths. | `energy_engine.py:374-432` |
| A-11 | 🟡 MEDIO | **`.env.example` contiene artefacto de parche**: sección "Missing Environment Variables (Added 2026-09-14)" — comentario de agente que documenta su propio parche, no al usuario. | `.env.example` líneas 40+ |
| A-12 | 🟡 MEDIO | **README con tautología imposible**: "MASSIVE was previously developed as **MASSIVE** (archived in git history). Renamed 2026-06-29." El historial fue squashed a 1 commit; además MASSIVE→MASSIVE no es un renombramiento. Resto del proyecto dice que se renombró desde otro nombre (huellas: `.aionrs/` en .gitignore, "AionRS session data"). | README.md pie; .gitignore |
| A-13 | 🟡 MEDIO | `cfc_engine.py` importa `torch` de forma dura (sin el fallback que la auditoría anterior D1-002 ya señalaba); funciona aquí solo porque torch está instalado. El README afirma "torch optional / every optional layer has a deterministic fallback" — **falso para cfc_engine** (los guards de simulator/cfc_router contienen el fallo, pero `import cfc_engine` directo falla sin torch). | `cfc_engine.py:17` |

## B. ESTRUCTURA: duplicación, áreas no funcionales, basura

### B-1. Duplicación mayor (tres backends, dos frontends, dos kits UI)
| Ítem | Detalle |
|------|---------|
| `massive-ui-ng/` | Kit completo duplicado: **backend FastAPI propio** (security.py, settings.py, metrics.py, rate_limit.py, narrative.py, 15 archivos), **frontend React propio**, `infra/` con su **propio `.github/workflows`** anidado (raro y confuso), Dockerfile propio, tests propios, y 4 docs de proceso (AGENTS.md, WORKFLOW.md, EXAMPLES.md, MANIFEST.txt). No está en el CI raíz (README lo admite: "ARCH-02"). El CHANGELOG ya borró sus módulos huérfanos del backend raíz (PR #84) — el kit entero es el residuo. |
| `frontend/src/MASSIVE_UIL_demo.jsx` | **Copia byte-idéntica de 825 líneas** duplicada también en `massive-ui-ng/frontend/src/`. Demo legacy "UIL" en ambos. |
| `backend/app/` vs `massive-ui-ng/backend/app/` | security.py / settings.py / metrics.py divergen (fork sin sincronizar). Namespace `backend` colisiona (auditoría previa D3-003, sin resolver). |
| `api.py` (legacy /api) vs `backend/app/` (canónico /v1) | Superficies solapadas — esto sí está documentado como compatibilidad intencional, pero conviene congelarlo con fecha de expiración. |
| Stubs raíz deprecados | `empirical_calibration.py`, `empirical_config.py`, `llm_credentials.py`, `schemas.py`, `state_compression.py` en raíz = re-exports de `massive/core/*` (5 archivos que solo existen por 12 imports legacy que se pueden actualizar). |

### B-2. Documentación-artefacto (trabajo de agentes, no documentación)
`docs/` tiene 117 .md (≈28.800 líneas). Gran parte NO es documentación de usuario sino bitácoras de agentes:

| Archivo/carpeta | Qué es |
|-----------------|--------|
| `docs/AUDIT_FINDINGS_TRACKER.md` (27 KB) | Tracker de 148 hallazgos de una auditoría anterior, mayormente "PENDIENTE" |
| `docs/architecture/AUDIT_REPORT_2026-09-15.md` | Reporte de auditoría puntual con 29 menciones de agentes |
| `docs/architecture/` (22 archivos) | Incluye process-artifacts: `checkpoint_status.md`, `compatibility_map.md`, `consolidation_plan/vision/workflow.md` (3 sobre lo mismo), `domain_ownership.md`, `first_execution_slices.md`, `module_inventory.md`, `MASSIVE_PRODUCTION_SIGNOFF.md`, `MASSIVE_SYSTEM_MAP.md` (obsoleto vs current-state.md), `backward_compatibility_aliases.md`… |
| `docs/FACTBOOK_{SUMMARY,QUICKSTART,INTEGRATION_PLAN,INTEGRATION_COMPLETE}.md` | 4 documentos del mismo feature (plan + "complete" + resumen + quickstart) |
| `docs/OPTIMIZATION_STATUS.md`, `docs/REMEDIATION_STATUS.md`, `docs/BACKLOG_POST_WORKFLOW.md` | Status de olas de trabajo internas (FASE 1-5, PRs #68-73+) |
| `docs/archive/` | Ya archived: `Audit_MASSIVE.patch` (¡un .patch!), REPORT_*.md (5), repomix-instruction.md |
| `docs/experiments/` | Carpetas numeradas 00-11 (falta 07, 09, 10 — numeración con huecos), con JSONs de resultados, `audit_report.md`, `TEST_SUMMARY.md` |
| `docs/research/progress.md` | "operator map" con PRs internos |
| `docs/development_history/micro_massive_workflow_2026-05-17.md` | Historial de trabajo |
| `docs/MASSIVE_mockup.png` (698 KB) + `docs/massive_ui_mockup.png` (141 KB) | Mockups sueltos en docs/ |
| `docs/repomix.config.json` + `.repomixignore` | Config de herramienta de empaque para LLMs |
| `mkdocs.yml` nav | Publica en el sitio la basura: AUDIT_FINDINGS_TRACKER, FACTBOOK_INTEGRATION_PLAN, etc. |

### B-3. `reports/` con artefactos de runtime y de agentes
- `investigador_de_tendencias.md` — output de un agente "investigador de tendencias" (fuentes con enlaces `file:///tmp/MASSIVE/...` rotos)
- `phase2_synthesis.md` — "Equipo de Agentes (4 paralelos)" con modelos `gemma4:31b-cloud` nombrados
- `phase4_qa_validation.md`, `production_readiness_check.md` — checks puntuales
- `factbook_validation_US_2026-{06-26,08-13,08-16,08-17}.json` — 4 versiones del mismo dump
- `enkf_pilot*/`, `cluster_run/`, `sota_baselines/`, `validation/ci-test/` — outputs de runs
- `.gitignore` ya dice `reports/**/*.json` pero estos están force-trackeados o son .md

### B-4. CI/infra irrelevante o rota
| Ítem | Problema |
|------|----------|
| `.github/workflows/main_massive.yml` | Workflow **de plantilla Azure** con finales de línea CRLF (`\r`), deploy a Azure Web App en cada push a main. No hay configuración Azure en el repo (sin startup file, sin .azure). Deploy que no puede funcionar + nombre default. |
| `.github/workflows/deploy_hf_spaces.yml` | Push espejo a HuggingFace Spaces — requiere secret `HF_TOKEN`; ¿se usa? |
| 13 workflows | El README presume "13 CI workflows per PR"; hay superposición (pytest vs main vs pvu vs benchmark) |
| `massive-ui-ng/infra/.github/workflows/` | **workflows anidados dentro de un subdirectorio** — GitHub no los ejecuta pero confunde (además de duplicar CI). |
| `docs/examples/Dockerfile.optimized` + `docker-compose.single.yml` + nginx/supervisord | Variante legacy archivada "bajo docs/examples" — configs de Docker dentro de docs/ es antipatrón. |

### B-5. Menciones excesivas de agentes de IA (~1.095 coincidencias en .md)
- `CLAUDE.md` en raíz (guías de comportamiento LLM genéricas, mezcladas con instrucciones de proyecto)
- `.github/agents/massive-data-architect.agent.md` + `repo-surgeon.agent.md` (definiciones de agentes autónomos, una de ellas un "agente cirujano" que audita todo el repo)
- `massive-ui-ng/AGENTS.md` + WORKFLOW.md + EXAMPLES.md (más menciones de agentes)
- CODEOWNERS referencia "AGENTS.md — agente Foundation" (archivo que no existe en raíz)
- Docs tachados de nombres de agentes: "agente Foundation", "Investigador", "Arquitecto", "Devil's Advocate", equipos de 4 agentes paralelos, "repo-surgeon", etc.
- Cabeceras tipo `Autor: MASSIVE Research` en cada engine + menciones en comentarios de código

### B-6. Varios menores
- `metrics/`, `adapters/mutalambda/`, `micro_massive/` — paquetes con un solo consumidor cada uno (correctos pero dispersos; pyproject ya los empaqueta, OK).
- `docs/NAMING_CONVENTIONS.md` (1.2 KB) existe pero el código mezcla español/inglés (auditoría previa D2-014).
- Numeración de carpetas de experiments con huecos (00-06, 08, 11).
- `uv.lock` (1.2 MB) trackeado junto a `requirements.txt` y `pyproject.toml` — 3 mecanismos de lock.
- `benchmark_scalability.py` (35 KB) y `brexit_calibration.py` (9 KB) en raíz — scripts, no módulos de librería.

## C. Lo que SÍ está bien (no tocar)
- 679 tests verdes en ~42 s; suite de reproducibilidad y caracterización.
- `metrics/unified_metrics.py` — unificación URCC de polarización bien documentada y testeada.
- Arquitectura de engines + services + backend canónico; separación legacy documentada.
- EnKF, PVU benchmark, contract LLM v1.1.0, security fail-closed, Docker multi-stage no-root.
- Correlación Gini→regla_polarizacion del motor escalar: implementada, lineal y testeada (test_gini_rule_bridge).

---

## PLAN DE IMPLEMENTACIÓN

### Ola 1 — Bugs funcionales y de lógica (sin romper API)
1. **A-1**: Reparar `massive/cli/main.py` (quitar marcador de conflicto y línea duplicada) + smoke test del CLI.
2. **A-2**: `resumen_historial()` → derivar `range_type` con `_es_bipolar(cfg)`; test de caracterización bipolar/unipolar (0.4 y 0.333).
3. **A-3**: `initialize_agents()` — ingreso ~ Beta simétrica con dispersión monótona en Gini y media desacoplada (media fija 0.5 o anclada a GDP si viene del factbook); test: Gini 0.6 → dispersión > Gini 0.3 → dispersión > Gini 0.1; media estable.
4. **A-4**: `fiscal_constraint` → factibilidad fiscal monótona: `clip(0.5 + 2.0·(superávit/revenues), 0, 1)` (déficit<0 → <0.5; superávit → >0.5); tests de dirección con déficit/superávit.
5. **A-5**: conciliar comentarios/código: implementar el efecto Gini→σ del paisaje en `step()` (σ = σ₀·(1−0.5·gini)) o eliminar la promesa; conectar `propose_lambda`/modelos CfC faltantes → eliminar caminos muertos y dejar docstrings honestos.
6. **A-6**: conectar `social_pressure_weights` en `MassiveEngine` (modular la fuerza social por presión de grupo) O eliminar la derivación; decidido: conectar con efecto documentado y testeado (homogeneidad → más conformidad).
7. **A-7**: corregir docstrings de `compute_theta` (declara solo volatilidad) — y opcionalmente añadir el efecto de nivel educación→cooperación en el target del potencial (ya existe el término coop; se puede modular el target 0.8·align con educación). Implementación mínima honesta: docstrings veraces + efecto nivel para educación (el resto queda como ruido documentado).
8. **A-8/A-9/A-10**: unificar escala income_scale (constante compartida), defaults consistentes, contrato de `propose_landscape` (`return base` en vez de None), eliminar doble muestreo de ruido.

### Ola 2 — Limpieza de duplicación y basura (según respuestas del usuario)
- Eliminar/archivar `massive-ui-ng/`; eliminar `MASSIVE_UIL_demo.jsx` duplicado; consolidar stubs raíz actualizando los 12 imports legacy; limpiar `reports/` de artefactos; quitar workflows Azure/HF si no se usan; mover configs Docker legacy fuera de docs.

### Ola 3 — Reducción de menciones de agentes
- Consolidar todo lo de agentes en UN lugar canónico (`.github/agents/` para prompts funcionales + una sección breve en CONTRIBUTING). Quitar nombres de agentes, "Autor: MASSIVE Research" redundante, referencias a equipos de agentes de docs, "agente Foundation" en CODEOWNERS, sección-parche en .env.example, tautología del README.

### Ola 4 — Docs profesionales
- Reestructurar `docs/` para usuarios: keep runbooks/security/testing/validation/architecture(current/target); mover todo lo demás a `docs/archive/` o borrar; regenerar `mkdocs.yml` nav; arreglar numeración de experiments; README/README_ES consistentes y sin historia interna.

### Ola 5 — Optimización y verificación final
- Suite completa + lint + smoke CLI + API `/v1/simulate` sanity; revisar cobertura de los fixes; `check_docs_refs.py` verde.

**Criterios de éxito**: tests verdes (679 + nuevos), CLI funcional, correlaciones con tests de dirección (Gini↑→dispersión↑, déficit→factibilidad↓, bipolar→magnitud correcta), repo sin duplicados, docs nav limpio, ≤1 ubicación de menciones de agentes.
