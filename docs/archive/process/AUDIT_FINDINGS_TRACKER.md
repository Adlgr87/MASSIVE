# Tracker de hallazgos de auditoría — MASSIVE

> **Documento maestro de trazabilidad.** Derive de `AUDIT_REPORT_2026-09-15.md` (148 hallazgos, commit `473b04a6`).
> Cada fila se asigna a una ola y tarea del `AUDIT_REMEDIATION_WORKFLOW.md`.
> Los hallazgos 🟢 son activos preservados (G-1) que no deben romperse.

| ID | Severidad | Título | Ola | Tarea | Estado | Issue |
|---|---|---|---|---|---|---|
| D1-001 | 🔴 CRITICAL | `import simulator` falla con `AttributeError` en cualquier entorno sin PyTorch — rompe 25 módulos y 21 archivos de test | W1 | W1-T01 | PENDIENTE | [#91](https://github.com/Adlgr87/MASSIVE/issues/91) |
| D1-002 | 🔴 CRITICAL | El "fallback NumPy" de `cfc_engine.py` no existe — el mensaje de warning miente y el módulo falla al definir las clases | W1 | W1-T02 | PENDIENTE | [#92](https://github.com/Adlgr87/MASSIVE/issues/92) |
| D1-003 | 🔴 CRITICAL | `simulator.py` importa `extended_models` desde root, pero el módulo vive en `massive/core/` — se desactiva en silencio y sin warning | W1 | W1-T01 | PENDIENTE | [#93](https://github.com/Adlgr87/MASSIVE/issues/93) |
| D1-004 | 🔴 CRITICAL | La recolección de pytest se interrumpe por completo en el entorno de dependencias que instala el job `core` de CI | W1 | W1-T03 | PENDIENTE | [#94](https://github.com/Adlgr87/MASSIVE/issues/94) |
| D1-005 | 🟠 HIGH | `mamba_engine.py` / `MambaBaseline` no existen — el brief los lista y el mapa del sistema los referencia | W5 | W5-T06 | PENDIENTE | [#95](https://github.com/Adlgr87/MASSIVE/issues/95) |
| D1-006 | 🟠 HIGH | `app.py` (Streamlit) no existe pero está referenciado 22 veces, el topic de GitHub sigue siendo `streamlit`, y `requirements.txt` sigue instalando Streamlit | W5 | W5-T06 | PENDIENTE | [#96](https://github.com/Adlgr87/MASSIVE/issues/96) |
| D1-007 | 🟢 PRESERVE | `simulator_core/` no existe — item del contexto previo resuelto | W0 | W0-T03 | GUARDRAIL → RESUELTO | - |
| D1-008 | 🟡 MEDIUM | Efectos colaterales en tiempo de import: `import simulator` crea archivos en el CWD | W2 | W2-T05 | PENDIENTE | - |
| D1-009 | 🟡 MEDIUM | Inventario de importabilidad: 121/146 OK sin torch, 146/146 con torch | W3 | W3-T05 | PENDIENTE | - |
| D1-010 | 🟢 PRESERVE | Cero errores de sintaxis y cero imports relativos rotos en 245 archivos | W0 | W0-T01 | GUARDRAIL | - |
| D1-011 | 🟡 MEDIUM | `docker-compose config` no verificable en el sandbox — validación YAML sustituta OK | W1 | W1-T04 | PENDIENTE | - |
| D2-001 | 🔴 CRITICAL | `ruff check .` falla (28 issues, exit 1) — bloquea `lint.yml` y la cadena completa de `publish.yml` | W1 | W1-T06 | PENDIENTE | [#97](https://github.com/Adlgr87/MASSIVE/issues/97) |
| D2-002 | 🔴 CRITICAL | `black --check .` reformatearía 30 de 245 archivos (exit 1) | W1 | W1-T06 | PENDIENTE | [#98](https://github.com/Adlgr87/MASSIVE/issues/98) |
| D2-003 | 🟠 HIGH | 198 errores de tipo repo-wide; 36 en el slice que ejecuta CI | W2 | W2-T06 | PENDIENTE | [#99](https://github.com/Adlgr87/MASSIVE/issues/99) |
| D2-004 | 🟠 HIGH | `mypy .` aborta sin analizar nada: "Duplicate module named backend" | W1 | W1-T07 | PENDIENTE | [#100](https://github.com/Adlgr87/MASSIVE/issues/100) |
| D2-005 | 🟠 HIGH | 127 `except Exception` y 26 handlers que silencian con `pass`/`continue` | W2 | W2-T05 | PENDIENTE | [#101](https://github.com/Adlgr87/MASSIVE/issues/101) |
| D2-006 | 🟠 HIGH | `energy_engine.py` calcula y descarta 6 valores en el hot path del paisaje de energía | W2 | W2-T07 | PENDIENTE | [#102](https://github.com/Adlgr87/MASSIVE/issues/102) |
| D2-007 | 🟢 PRESERVE | Cero `except:` desnudos en todo el repo | W0 | W0-T01 | GUARDRAIL | - |
| D2-008 | 🟡 MEDIUM | `print()` en código de librería — 156 ocurrencias vs 347 de logging | W2 | W2-T04 | PENDIENTE | - |
| D2-009 | 🟡 MEDIUM | `logging.basicConfig` invocado 13 veces, incluidas 2 en módulos de test y 2 a nivel de módulo de librería | W2 | W2-T05 | PENDIENTE | - |
| D2-010 | 🟡 MEDIUM | Tres convenciones de nombrado de logger coexisten; ninguna coincide con `__name__` de forma consistente | W2 | W2-T05 | PENDIENTE | - |
| D2-011 | 🟡 MEDIUM | 12 bloques con complejidad ciclomática ≥ D; dos en grado F | W5 | W5-T04 | PENDIENTE | - |
| D2-012 | 🟡 MEDIUM | `train_cfc_lambda.py`, `train_cfc_landscape.py` y `train_cfc_temp.py` son clones ~85 % idénticos | W5 | W5-T03 | PENDIENTE | - |
| D2-013 | 🟡 MEDIUM | Código muerto: 311 hallazgos de vulture al 60 %, con núcleos completos sin consumidores | W5 | W5-T03 | PENDIENTE | - |
| D2-014 | 🟡 MEDIUM | Nomenclatura mixta español/inglés para el mismo concepto, a veces dentro de la misma tupla | W5 | W5-T04 | PENDIENTE | - |
| D2-015 | 🟢 PRESERVE | Cero marcadores TODO/FIXME/HACK/XXX en el código Python | W0 | W0-T01 | GUARDRAIL | - |
| D2-016 | 🟡 MEDIUM | URLs y hosts hardcodeados; `interpreter_layer.py` ignora la variable de entorno que el resto sí respeta | W2 | W2-T08 | PENDIENTE | - |
| D2-017 | 🟡 MEDIUM | Deuda de estilo pytest: 230 asserts estilo unittest y 18 `__all__` sin ordenar | W1 | W1-T06 | PENDIENTE | - |
| D3-001 | 🔴 CRITICAL | `pyproject.toml` no empaqueta los 31 módulos root ni `metrics/` — cualquier wheel construido es import-roto | W3 | W3-T01 | PENDIENTE | [#103](https://github.com/Adlgr87/MASSIVE/issues/103) |
| D3-002 | 🔴 CRITICAL | Tres backends FastAPI paralelos con superficies divergentes | W5 | W5-T01 | PENDIENTE | [#104](https://github.com/Adlgr87/MASSIVE/issues/104) |
| D3-003 | 🔴 CRITICAL | Colisión de namespace `backend` entre root y `massive-ui-ng/` — rompe mypy y el generador de tipos forkado | W5 | W5-T01 | PENDIENTE | [#105](https://github.com/Adlgr87/MASSIVE/issues/105) |
| D3-004 | 🟠 HIGH | La capa de DTOs Pydantic es decorativa en el backend canónico: 5 de 6 routers aceptan `dict[str, Any]` crudo | W2 | W2-T01 | PENDIENTE | [#106](https://github.com/Adlgr87/MASSIVE/issues/106) |
| D3-005 | 🟠 HIGH | Dos frontends React/Vite paralelos con un archivo de 825 líneas byte-idéntico y tipos generados divergentes | W5 | W5-T01 | PENDIENTE | [#107](https://github.com/Adlgr87/MASSIVE/issues/107) |
| D3-006 | 🟠 HIGH | 31 módulos Python en la raíz del repositorio; `simulator.py` es un god-module de 2 457 líneas | W5 | W5-T02 | PENDIENTE | [#108](https://github.com/Adlgr87/MASSIVE/issues/108) |
| D3-007 | 🟠 HIGH | 22 archivos Python superan las 500 líneas; 49 174 LOC totales | W5 | W5-T02 | PENDIENTE | [#109](https://github.com/Adlgr87/MASSIVE/issues/109) |
| D3-008 | 🟠 HIGH | Tres paquetes `utils/` distintos bajo tres prefijos de paquete distintos | W5 | W5-T02 | PENDIENTE | [#110](https://github.com/Adlgr87/MASSIVE/issues/110) |
| D3-009 | 🟠 HIGH | La capa de shims deprecados de root es inconsistente: 4 silenciosos, 1 con warning incondicional y docstring malformado, 1 ausente | W5 | W5-T04 | PENDIENTE | [#111](https://github.com/Adlgr87/MASSIVE/issues/111) |
| D3-010 | 🟡 MEDIUM | `massive/` vs `massive_core/`: la separación de responsabilidades existe pero está invertida respecto a la intuición del nombre | W5 | W5-T02 | PENDIENTE | - |
| D3-011 | 🟡 MEDIUM | Cada endpoint `/v1/*` está duplicado en `/api/v1/*` — 22 paths en OpenAPI para 13 operaciones | W4 | W4-T05 | PENDIENTE | - |
| D3-012 | 🟡 MEDIUM | `micro_engine.py` (root, 1 034 líneas) y `micro_massive/` (9 módulos) son dos implementaciones micro paralelas | W5 | W5-T02 | PENDIENTE | - |
| D3-013 | 🟡 MEDIUM | El console script publicado (`massive-cli`) tiene 0 % de cobertura y 0 tests | W5 | W5-T06 | PENDIENTE | - |
| D3-014 | 🟡 MEDIUM | `monitoring/` está referenciado por el README pero no conectado a nada | W3 | W3-T03 | PENDIENTE | - |
| D3-015 | 🟢 PRESERVE | `adapters/mutalambda/` está bien diseñado: thin, sin dependencia dura, con manifiesto declarativo | W0 | W0-T01 | GUARDRAIL | - |
| D3-016 | 🟡 MEDIUM | La cadena de imports del adapter es frágil: `adapters → forecast → simulator → cfc_router` | W5 | W5-T02 | PENDIENTE | - |
| D3-017 | 🟡 MEDIUM | Dos `Cargo.toml` contradictorios para el mismo crate; el de `rust_core/` es huérfano y referencia un crate inexistente | W3 | W3-T02 | PENDIENTE | - |
| D3-018 | 🟠 HIGH | El núcleo Rust nunca se compila ni se testea en ningún entorno automatizado — es código muerto en la práctica | W3 | W3-T02 | PENDIENTE | [#112](https://github.com/Adlgr87/MASSIVE/issues/112) |
| D3-019 | 🟡 MEDIUM | `scripts/gen_ts_types.py` no tiene interfaz CLI: `--dry-run` y `--stdout` se ignoran en silencio y el script escribe el archivo | W2 | W2-T08 | PENDIENTE | - |
| D3-020 | 🟢 PRESERVE | Los tipos TypeScript de `frontend/` están efectivamente sincronizados con los DTOs Pydantic | W0 | W0-T01 | GUARDRAIL | - |
| D4-001 | 🔴 CRITICAL | 12 de 681 tests fallan en un clone limpio: requieren pesos `.pt` que no están en el repositorio | W1 | W1-T09 | PENDIENTE | [#113](https://github.com/Adlgr87/MASSIVE/issues/113) |
| D4-002 | 🟠 HIGH | Cobertura real 59.62 % branch; el README declara 68 %; el gate de CI está en 30 % | W5 | W5-T05 | PENDIENTE | [#114](https://github.com/Adlgr87/MASSIVE/issues/114) |
| D4-003 | 🟠 HIGH | 16 archivos con 0 % de cobertura (1 734 sentencias), incluido el CLI publicado y modelos científicos completos | W5 | W5-T03 | PENDIENTE | [#115](https://github.com/Adlgr87/MASSIVE/issues/115) |
| D4-004 | 🟠 HIGH | 16 archivos por debajo del 50 %; `social_architect.py` al 14.4 % es la superficie de producto menos cubierta | W2 | W2-T01 | PENDIENTE | [#116](https://github.com/Adlgr87/MASSIVE/issues/116) |
| D4-005 | 🟠 HIGH | 140 de 666 funciones de test (21 %) no contienen ninguna aserción | W5 | W5-T05 | PENDIENTE | [#117](https://github.com/Adlgr87/MASSIVE/issues/117) |
| D4-006 | 🟠 HIGH | 3 archivos de test no pueden recolectarse sin `httpx`, que no está declarado en `requirements.txt` | W1 | W1-T03 | PENDIENTE | [#118](https://github.com/Adlgr87/MASSIVE/issues/118) |
| D4-007 | 🟡 MEDIUM | Un segundo directorio de tests (`massive-ui-ng/tests/`) queda fuera de `testpaths` y nunca se ejecuta | W1 | W1-T10 | PENDIENTE | - |
| D4-008 | 🟡 MEDIUM | No existe `conftest.py` en la raíz ni en `tests/` | W1 | W1-T10 | PENDIENTE | - |
| D4-009 | 🟡 MEDIUM | El test diseñado para cubrir el camino sin torch no puede pasar en un entorno sin torch | W1 | W1-T10 | PENDIENTE | - |
| D4-010 | 🟡 MEDIUM | `tests/test_cfc_router.py` produce 4 fallos en entorno sin torch, incluido `test_simular_works_without_cfc_models` | W1 | W1-T01 | PENDIENTE | - |
| D4-011 | 🟡 MEDIUM | El benchmark PVU canónico termina en 0 pero emite `ConvergenceWarning` de statsmodels en los casos publicados | W6 | W6-T02 | PENDIENTE | - |
| D4-012 | 🟡 MEDIUM | En el caso de muestra publicado, MASSIVE pierde contra un baseline lineal (`ridge_lags`) en MAE y en accuracy direccional | W6 | W6-T02 | PENDIENTE | - |
| D4-013 | 🟢 PRESERVE | Suite predominantemente de integración real: ratio de mocks bajo y sólo 2 skips en 666 tests | W0 | W0-T01 | GUARDRAIL | - |
| D4-014 | 🟡 MEDIUM | Mezcla de `unittest.TestCase` y pytest en los mismos archivos; 230 asserts estilo unittest | W1 | W1-T10 | PENDIENTE | - |
| D5-001 | 🔴 CRITICAL | El backend canónico no impone ningún límite a `pasos`, `n_agents` ni `max_intentos` — las protecciones anti-DoS documentadas sólo existen en los caminos deprecados | W2 | W2-T01 | PENDIENTE | [#119](https://github.com/Adlgr87/MASSIVE/issues/119) |
| D5-002 | 🔴 CRITICAL | `pip install -e .` es imposible: el build-backend es `maturin` y ningún Dockerfile, workflow o documento instala un toolchain Rust | W3 | W3-T01 | PENDIENTE | [#120](https://github.com/Adlgr87/MASSIVE/issues/120) |
| D5-003 | 🟠 HIGH | 0 de 30 dependencias pinneadas y no existe lockfile de Python | W2 | W2-T10 | PENDIENTE | [#121](https://github.com/Adlgr87/MASSIVE/issues/121) |
| D5-004 | 🟠 HIGH | `requirements.txt` y `pyproject.toml` declaran conjuntos de dependencias distintos y con especificadores distintos | W2 | W2-T10 | PENDIENTE | [#122](https://github.com/Adlgr87/MASSIVE/issues/122) |
| D5-005 | 🟠 HIGH | 6 paquetes importados por el código no están declarados en ninguna parte (+ `httpx` para tests) | W1 | W1-T03 | PENDIENTE | [#123](https://github.com/Adlgr87/MASSIVE/issues/123) |
| D5-006 | 🟠 HIGH | Dependencias declaradas con cero imports: `torchdiffeq` y `streamlit` | W2 | W2-T10 | PENDIENTE | [#124](https://github.com/Adlgr87/MASSIVE/issues/124) |
| D5-007 | 🟠 HIGH | El `requirements.txt` de producción instala pytest y el stack completo de MkDocs en la imagen Docker | W2 | W2-T10 | PENDIENTE | [#125](https://github.com/Adlgr87/MASSIVE/issues/125) |
| D5-008 | 🟠 HIGH | `torch` es una dependencia dura de facto pero opcional de jure | W1 | W1-T02 | PENDIENTE | [#126](https://github.com/Adlgr87/MASSIVE/issues/126) |
| D5-009 | 🟡 MEDIUM | `GET /metrics` responde 200 sin autenticación y nginx lo expone públicamente | W2 | W2-T02 | PENDIENTE | - |
| D5-010 | 🟡 MEDIUM | `.env.example` propone `MASSIVE_ALLOWED_HOSTS=*` (wildcard) | W2 | W2-T02 | PENDIENTE | - |
| D5-011 | 🟡 MEDIUM | `.env.example` duplica claves y documenta explícitamente dos convenciones en competencia | W2 | W2-T10 | PENDIENTE | - |
| D5-012 | 🟡 MEDIUM | `.env.local.example` es un subconjunto divergente de `.env.example`, y `docker-compose.yml` monta ambos | W2 | W2-T10 | PENDIENTE | - |
| D5-013 | 🟡 MEDIUM | `MASSIVE_ENV` sin definir resuelve a "development", lo que activa la clave fallback publicada `dev-secret-key` | W2 | W2-T02 | PENDIENTE | - |
| D5-014 | 🟡 MEDIUM | CSP con `'unsafe-inline'` en script-src y style-src; header deprecado `X-XSS-Protection`; sin `server_tokens off` | W2 | W2-T03 | PENDIENTE | - |
| D5-015 | 🟡 MEDIUM | El `add_header` del location de assets estáticos cancela todos los headers de seguridad del nivel server (regla de herencia de nginx) | W2 | W2-T03 | PENDIENTE | - |
| D5-016 | 🟡 MEDIUM | El deploy a Hugging Face embebe el token en la URL del remoto git y hardcodea el usuario | W3 | W3-T04 | PENDIENTE | - |
| D5-017 | 🟢 PRESERVE | `pip-audit` no encuentra vulnerabilidades conocidas en `requirements.txt` | W0 | W0-T01 | GUARDRAIL | - |
| D5-018 | 🟢 PRESERVE | Sin credenciales en el árbol; `llm_credentials.py` está bien diseñado. Items `test-zapier.txt` y secretos commiteados: RESUELTOS | W0 | W0-T03 | GUARDRAIL → RESUELTO (test-zapier.txt) | - |
| D5-019 | 🟡 MEDIUM | Typo en `.gitignore`: `repomack-output*.xml` en lugar de `repomix-output*.xml` — el bundle generado NO está ignorado | W1 | W1-T05 | PENDIENTE | - |
| D5-020 | 🟡 MEDIUM | Las reglas de `.gitignore` para binarios y artefactos son ineficaces porque los archivos ya están trackeados | W1 | W1-T05 | PENDIENTE | - |
| D5-021 | 🟡 MEDIUM | Estado runtime commiteado: `data/ui_ng/runs.db` (SQLite, 40 KB) | W1 | W1-T05 | PENDIENTE | - |
| D5-022 | 🟡 MEDIUM | `.dockerignore` excluye `models/`, `datasets/` y `data/` — la imagen de producción arranca sin pesos CfC; además no excluye docs ni el segundo frontend, y tiene un glob malformado | W1 | W1-T05 | PENDIENTE | - |
| D5-023 | 🟡 MEDIUM | `gitleaks.toml` permite 14 stopwords, incluida la clave de desarrollo activa | W2 | W2-T02 | PENDIENTE | - |
| D5-024 | 🟡 MEDIUM | Faltan `SECURITY.md`, `dependabot.yml`, `CODEOWNERS` y `.github/ISSUE_TEMPLATE/` | W0 | W0-T02 | PENDIENTE | [#153](https://github.com/Adlgr87/MASSIVE/issues/153) |
| D6-001 | 🔴 CRITICAL | La tabla "Quality & production posture" del README contiene 4 afirmaciones falsas verificables | W4 | W4-T01 | PENDIENTE | [#127](https://github.com/Adlgr87/MASSIVE/issues/127) |
| D6-002 | 🟠 HIGH | `README.md` y `README_ES.md` discrepan en cifras y en enlaces pese a tener la misma estructura | W4 | W4-T01 | PENDIENTE | [#128](https://github.com/Adlgr87/MASSIVE/issues/128) |
| D6-003 | 🟠 HIGH | 21 archivos Markdown de planning/reportes/agentes en la raíz (≈250 KB) | W4 | W4-T02 | PENDIENTE | [#129](https://github.com/Adlgr87/MASSIVE/issues/129) |
| D6-004 | 🟠 HIGH | 356 referencias a rutas inexistentes repartidas en 114 archivos Markdown | W4 | W4-T03 | PENDIENTE | [#130](https://github.com/Adlgr87/MASSIVE/issues/130) |
| D6-005 | 🟠 HIGH | Rutas absolutas de la máquina personal del autor incrustadas en la documentación pública (16 ocurrencias) | W4 | W4-T03 | PENDIENTE | [#131](https://github.com/Adlgr87/MASSIVE/issues/131) |
| D6-006 | 🟠 HIGH | Tres reportes de root tienen fechas anteriores a la creación del repositorio | W1 | W1-T08 | PENDIENTE | [#132](https://github.com/Adlgr87/MASSIVE/issues/132) |
| D6-007 | 🟠 HIGH | `REPORT_OPTIMIZATION.md` describe una arquitectura Numba/JIT que fue eliminada del código | W4 | W4-T03 | PENDIENTE | [#133](https://github.com/Adlgr87/MASSIVE/issues/133) |
| D6-008 | 🟠 HIGH | `MASSIVE_SYSTEM_MAP.md` (36 KB, el mapa autoritativo) referencia 11 archivos inexistentes y componentes retirados | W4 | W4-T03 | PENDIENTE | [#134](https://github.com/Adlgr87/MASSIVE/issues/134) |
| D6-009 | 🟠 HIGH | 35 de 60 documentos de `docs/` son huérfanos del nav de MkDocs — invisibles en el sitio publicado | W4 | W4-T04 | PENDIENTE | [#135](https://github.com/Adlgr87/MASSIVE/issues/135) |
| D6-010 | 🟠 HIGH | La entrada "Spanish Version" del nav de MkDocs apunta a un stub de 5 líneas | W4 | W4-T03 | PENDIENTE | [#136](https://github.com/Adlgr87/MASSIVE/issues/136) |
| D6-011 | 🟡 MEDIUM | 24 de 245 archivos Python no tienen docstring de módulo | W4 | W4-T03 | PENDIENTE | - |
| D6-012 | 🟡 MEDIUM | `CHANGELOG.md` tiene dos secciones `[Unreleased]` y ninguna versión SemVer; no hay releases ni tags en GitHub | W3 | W3-T04 | PENDIENTE | - |
| D6-013 | 🟡 MEDIUM | El README indica servir MkDocs en el puerto 8000, que es el puerto de la API | W1 | W1-T08 | PENDIENTE | - |
| D6-014 | 🟡 MEDIUM | Recuentos de endpoints desactualizados en README y en el árbol de layout | W4 | W4-T01 | PENDIENTE | - |
| D6-015 | 🟡 MEDIUM | Seis archivos de instrucciones para agentes/IA con propósitos solapados | W4 | W4-T04 | PENDIENTE | - |
| D6-016 | 🟡 MEDIUM | `.github/Agent_Copilot2`: archivo sin extensión, en la ubicación equivocada y con frontmatter malformado | W1 | W1-T08 | PENDIENTE | - |
| D6-017 | 🟡 MEDIUM | `.github/agents/my-agent.agent.md` está envuelto en un code fence y tiene nombre de placeholder | W1 | W1-T08 | PENDIENTE | - |
| D6-018 | 🟢 PRESERVE | `mkdocs build --strict` compila sin errores ni warnings | W0 | W0-T01 | GUARDRAIL | - |
| D6-019 | 🟢 PRESERVE | Existen `CHANGELOG.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` y `PULL_REQUEST_TEMPLATE.md` | W0 | W0-T01 | GUARDRAIL | - |
| D7-001 | 🔴 CRITICAL | Los 13 workflows fallan en `main`; HEAD nunca fue validado por CI (bloqueo de facturación de GitHub Actions desde 2026-09-13) | W0 | W0-T01 | PENDIENTE | [#137](https://github.com/Adlgr87/MASSIVE/issues/137) |
| D7-002 | 🔴 CRITICAL | Aun con Actions restaurado, el pipeline está rojo por mérito propio en 7 puntos independientes | W3 | W3-T05 | PENDIENTE | [#138](https://github.com/Adlgr87/MASSIVE/issues/138) |
| D7-003 | 🔴 CRITICAL | El job `core` de `pytest.yml` instala dependencias sin torch y luego ejecuta los tests que requieren torch | W2 | W2-T09 | PENDIENTE | [#139](https://github.com/Adlgr87/MASSIVE/issues/139) |
| D7-004 | 🔴 CRITICAL | `Dockerfile.optimized` tiene una línea 1 que no es sintaxis Docker válida — el archivo no puede construirse | W1 | W1-T04 | PENDIENTE | [#140](https://github.com/Adlgr87/MASSIVE/issues/140) |
| D7-005 | 🟠 HIGH | Bucle de contradicción en la ruta de despliegue: cada archivo remite al siguiente, que remite al anterior | W1 | W1-T04 | PENDIENTE | [#141](https://github.com/Adlgr87/MASSIVE/issues/141) |
| D7-006 | 🟠 HIGH | El type checking no puede fallar CI: `|| true` en `lint.yml` y `continue-on-error` en `typecheck.yml` — y hoy hay un error real que se reporta como éxito | W2 | W2-T06 | PENDIENTE | [#142](https://github.com/Adlgr87/MASSIVE/issues/142) |
| D7-007 | 🟠 HIGH | `massive-ui-ng/infra/.github/workflows/ui-ng.yml` es un workflow muerto con rutas incorrectas para su propia ubicación | W5 | W5-T01 | PENDIENTE | [#143](https://github.com/Adlgr87/MASSIVE/issues/143) |
| D7-008 | 🟠 HIGH | `publish.yml` encadena 10 jobs detrás de un gate de lint que está rojo y de dos jobs que requieren un toolchain que nadie instala | W3 | W3-T04 | PENDIENTE | [#144](https://github.com/Adlgr87/MASSIVE/issues/144) |
| D7-009 | 🟡 MEDIUM | Ningún workflow, Dockerfile o target de Make construye o testa el crate Rust | W3 | W3-T02 | PENDIENTE | - |
| D7-010 | 🟡 MEDIUM | `pvu-validation.yml` no se dispara en push a `main` | W2 | W2-T09 | PENDIENTE | - |
| D7-011 | 🟡 MEDIUM | `main_massive.yml` despliega a Azure Web App: objetivo de despliegue huérfano, CRLF, y `python-version: '3.x'` | W3 | W3-T03 | PENDIENTE | - |
| D7-012 | 🟡 MEDIUM | Clave de API estática y débil en los smoke tests de CI | W2 | W2-T09 | PENDIENTE | - |
| D7-013 | 🟡 MEDIUM | `secret_scan.yml` hace `fetch-depth: 0` sobre 1 735 runs de historial sin `GITLEAKS_LICENSE` ni `paths-ignore` | W2 | W2-T09 | PENDIENTE | - |
| D7-014 | 🟡 MEDIUM | `mypy.ini` en modo permisivo, sin `exclude`, con opt-outs por módulo y duplicado de configuración con `pyproject.toml` | W1 | W1-T07 | PENDIENTE | - |
| D7-015 | 🟡 MEDIUM | Cuatro combinaciones de despliegue sin una ruta canónica documentada | W3 | W3-T03 | PENDIENTE | - |
| D7-016 | 🟡 MEDIUM | `supervisord.conf` gestiona 2 procesos en un contenedor (nginx como root + uvicorn como appuser) | W2 | W2-T03 | PENDIENTE | - |
| D7-017 | 🟢 PRESERVE | Los 13 workflows, los 2 compose, `mkdocs.yml` y los 2 `configs/*.yaml` parsean sin errores | W0 | W0-T01 | GUARDRAIL | - |
| D7-018 | 🟢 PRESERVE | `Makefile` e `install.sh` ofrecen una superficie de desarrollador coherente y auto-documentada | W0 | W0-T01 | GUARDRAIL | - |
| D7-019 | 🟡 MEDIUM | `pyproject.toml` declara `massive-cli` como único script pero el CLI no está probado, y `addopts` desactiva un plugin no declarado | W5 | W5-T06 | PENDIENTE | - |
| D7-020 | 🟡 MEDIUM | `.gitattributes` no declara binarios para `.pt`, `.npz`, `.png` ni `.db` pese a `* text=auto` | W1 | W1-T05 | PENDIENTE | - |
| D8-001 | 🟠 HIGH | 106 entradas en la raíz del repositorio (78 archivos + 28 directorios) — 7× el umbral razonable | W4 | W4-T02 | PENDIENTE | [#145](https://github.com/Adlgr87/MASSIVE/issues/145) |
| D8-002 | 🟠 HIGH | Cero releases, cero tags, cero versiones semánticas — con un pipeline de publicación a PyPI ya escrito | W3 | W3-T01 | PENDIENTE | [#146](https://github.com/Adlgr87/MASSIVE/issues/146) |
| D8-003 | 🟠 HIGH | GitHub no reconoce la licencia (reporta "Other") aunque `pyproject.toml` y el README declaran Apache-2.0 | W1 | W1-T08 | PENDIENTE | [#147](https://github.com/Adlgr87/MASSIVE/issues/147) |
| D8-004 | 🟡 MEDIUM | Topics de GitHub desactualizados y con una errata | W1 | W1-T08 | PENDIENTE | - |
| D8-005 | 🟡 MEDIUM | Badges del README: 5 presentes (2 de ellos rotos por estado de CI) y 7 relevantes ausentes | W4 | W4-T01 | PENDIENTE | - |
| D8-006 | 🟡 MEDIUM | Sin issue templates, sin labels de triaje visibles, 90 issues cerrados y 0 abiertos | W0 | W0-T02 | PENDIENTE | - |
| D8-007 | 🟡 MEDIUM | 0 estrellas, 0 forks, 0 watchers tras 5.5 meses — el repo no tiene tracción ni señales sociales | W6 | W6-T04 | PENDIENTE | - |
| D8-008 | 🟢 PRESERVE | El Quick start del README funciona de punta a punta — verificado en vivo | W0 | W0-T01 | GUARDRAIL | - |
| D8-009 | 🟢 PRESERVE | El ejemplo más simple de `simulator` del brief de auditoría ejecuta y produce salida correcta | W0 | W0-T01 | GUARDRAIL | - |
| D8-010 | 🟡 MEDIUM | El README es visualmente rico pero su tabla de arquitectura y su árbol de layout omiten la mitad del repositorio | W4 | W4-T01 | PENDIENTE | - |
| D8-011 | 🟡 MEDIUM | El renombrado UIL → UI-NG → MASSIVE está incompleto en nombres de archivo y de paquete | W4 | W4-T05 | PENDIENTE | - |
| D8-012 | 🟢 PRESERVE | `test-zapier.txt` y `repomix-output.xml`: ambos items sospechosos del brief están ausentes del árbol | W1 | W1-T05 | GUARDRAIL → RESUELTO | - |
| D9-001 | 🟠 HIGH | `LandscapeCache` no tiene TTL: la columna `created_at` se escribe y nunca se lee, y el dict en memoria crece sin límite | W2 | W2-T04 | PENDIENTE | [#148](https://github.com/Adlgr87/MASSIVE/issues/148) |
| D9-002 | 🟠 HIGH | Clave de cache = MD5 truncado a 48 bits del objetivo, sin componente de versión — riesgo de colisión y de envenenamiento entre versiones | W2 | W2-T04 | PENDIENTE | [#149](https://github.com/Adlgr87/MASSIVE/issues/149) |
| D9-003 | 🟠 HIGH | La afirmación de thread-safety del cache es falsa y los tres fallos de E/S se tragan en silencio | W2 | W2-T04 | PENDIENTE | [#150](https://github.com/Adlgr87/MASSIVE/issues/150) |
| D9-004 | 🟠 HIGH | `energy_engine.py` computa y descarta 6 valores en el cálculo del paisaje — incluido un coeficiente de Gini | W2 | W2-T07 | PENDIENTE | [#151](https://github.com/Adlgr87/MASSIVE/issues/151) |
| D9-005 | 🟠 HIGH | La tabla de escalabilidad del README no es reproducible desde nada que exista en el repositorio | W6 | W6-T01 | PENDIENTE | [#152](https://github.com/Adlgr87/MASSIVE/issues/152) |
| D9-006 | 🟡 MEDIUM | `profiling_results/` no existe; el material de profiling está disperso en 3 sitios sin conexión con CI | W6 | W6-T01 | PENDIENTE | - |
| D9-007 | 🟡 MEDIUM | El fallback Python de `rust_core.py` es correcto y está testeado, pero no existe test de paridad entre las dos implementaciones | W3 | W3-T02 | PENDIENTE | - |
| D9-008 | 🟡 MEDIUM | `multilayer_engine_sparse.py` (789 líneas) duplica `multilayer_engine.py` (1 025 líneas) y está exento de typing | W6 | W6-T03 | PENDIENTE | - |
| D9-009 | 🟡 MEDIUM | La narrativa de "uint8-quantized" no explica el footprint real: la extrapolación naive queda 88× por debajo de lo declarado | W6 | W6-T01 | PENDIENTE | - |
| D9-010 | 🟡 MEDIUM | El historial de simulación se acumula en memoria sin política de streaming ni checkpointing documentado | W6 | W6-T03 | PENDIENTE | - |
| D9-011 | 🟢 PRESERVE | Complejidad ciclomática media B (9.53) — razonable para un codebase científico de 49 K LOC | W6 | W6-T03 | GUARDRAIL | - |

---

## Resumen de cobertura

| Severidad | Hallazgos | Issues | Estado tracker |
|---|---|---|---|
| 🔴 CRITICAL | 17 | 17 | PENDIENTE |
| 🟠 HIGH | 45 | 45 | PENDIENTE |
| 🟡 MEDIUM | 69 | 0 | PENDIENTE |
| 🟢 PRESERVE | 17 | 0 | 17 preservados, 3 resueltos |
| **Total** | **148** | **62** | |

## Estados del tracker

| Estado | Significado |
|---|---|
| `PENDIENTE` | Hallazgo sin tratar; 🔴/🟠 tiene issue abierto |
| `RESUELTO` | Hallazgo 🟢 ya satisfecho en la línea base |
| Preservado | Hallazgo 🟢 que debe mantenerse (G-1) |
| `CERRADO` | Hallazgo tratado por una tarea del workflow |

## Referencias

- `AUDIT_REPORT_2026-09-15.md` — reporte de auditoría original (148 hallazgos)
- `AUDIT_REMEDIATION_WORKFLOW.md` — plan de remediación por olas
- [GitHub Issues](https://github.com/Adlgr87/MASSIVE/issues) — seguimiento por hallazgo
