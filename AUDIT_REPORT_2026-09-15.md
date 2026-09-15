# REPORTE DE AUDITORÍA — MASSIVE

**Fecha:** 2026-09-15
**Analista:** Arena.ai Agent Mode (senior software audit)
**Repo:** https://github.com/Adlgr87/MASSIVE
**Hash del commit analizado:** `473b04a6b4002b258da13f9c553949a6c59d5d5f` (`refactor: Humanize code — remove AI-generated tells`, commiteado 2026-09-15T03:51:05Z)
**Rama de trabajo:** `arena/01a0a6d3-massive`

> **Nota metodológica.** Todos los hallazgos marcados **[CONFIRMADO]** fueron reproducidos ejecutando comandos contra el checkout real. Los marcados **[HIPÓTESIS]** se derivan de inspección de código/config sin ejecución (principalmente por ausencia de `docker`, `cargo` y del runtime de GitHub Actions en el sandbox). Los marcados **[CONOCIDO PREVIO]** corresponden al contexto entregado en el brief de auditoría.
>
> **Entorno de reproducción:** Python 3.11.2 · numpy/scipy/pandas/networkx/pydantic/plotly/fastapi/uvicorn/scikit-learn/statsmodels · torch 2.14.0+cu130 · ruff 0.16.7 · mypy 2.3.1 · black · vulture · radon · pylint · pip-audit · mkdocs + material + mkdocstrings. Sin `cargo`, sin `docker`, sin `streamlit`, sin `psutil` (inicialmente).

---

## 1. RESUMEN EJECUTIVO

**Total de hallazgos: 148**

| Severidad | Cantidad |
|---|---|
| 🔴 Críticos (bloquean funcionalidad) | **17** |
| 🟠 Altos (degradan calidad significativamente) | **45** |
| 🟡 Medios (deuda técnica o UX) | **69** |
| 🟢 Positivos / resueltos (guardarraíles a preservar) | **17** |

**Distribución por dominio**

| Dominio | Hallazgos | 🔴 | 🟠 | 🟡 | 🟢 |
|---|---|---|---|---|---|
| 1 · Integridad funcional | 11 | 4 | 2 | 3 | 2 |
| 2 · Calidad de código Python | 17 | 2 | 4 | 8 | 3 |
| 3 · Arquitectura y organización | 20 | 3 | 7 | 8 | 2 |
| 4 · Tests y cobertura | 14 | 1 | 5 | 7 | 1 |
| 5 · Dependencias y seguridad | 24 | 2 | 6 | 14 | 2 |
| 6 · Documentación | 19 | 1 | 9 | 7 | 2 |
| 7 · CI/CD y configuración | 20 | 4 | 4 | 10 | 2 |
| 8 · Estética del repositorio | 12 | 0 | 3 | 6 | 3 |
| 9 · Optimización y rendimiento | 11 | 0 | 5 | 5 | 1 |
| **Total** | **148** | **17** | **45** | **69** | **17** |

### Estado de salud general: **3.5 / 10**

**Justificación.**

El núcleo científico del proyecto está **vivo y funciona**: 669 de 681 tests pasan, el backend canónico arranca y sirve tráfico real, `mkdocs build --strict` compila sin un solo warning, no hay secretos trackeados, `pip-audit` no reporta vulnerabilidades conocidas, y la cobertura medida (59.62 % branch) es respetable para un codebase de investigación de 49 174 LOC.

Pero el proyecto falla en **todo lo que rodea al núcleo**:

1. **No existe señal de CI.** Los 13 workflows fallan en `main` desde 2026-09-13 por bloqueo de facturación de GitHub Actions. El último verde real fue `da4c7e7b` (2026-09-12). Los 8+ commits posteriores —incluido HEAD— **nunca fueron validados**.
2. **Aun con CI restaurado, la tubería está roja por mérito propio**: `ruff check .` sale 1, `black --check .` reformatearía 30 archivos, `mypy` reporta 36 errores en el slice de CI y 198 en el repo, 12 tests fallan en un clone limpio, `pip install -e .` es imposible (backend `maturin` sin toolchain Rust), y `docker compose build` del camino "canónico" apunta a un `Dockerfile.optimized` cuya **línea 1 no es sintaxis Docker válida**.
3. **Un solo defecto de 1 línea rompe el 17 % del codebase** en cualquier entorno sin PyTorch: `import simulator` lanza `AttributeError` y arrastra 25 módulos y 21 archivos de test. Y PyTorch es apenas un *extra opcional* en `pyproject.toml`.
4. **Las afirmaciones públicas del README son falsas en 4 puntos verificables** (nº de tests, cobertura, "ruff + black + mypy green in CI", "semgrep").
5. **Tres backends FastAPI paralelos, dos frontends React paralelos, dos `Cargo.toml` contradictorios, dos convenciones de nombres de variables de entorno** — y las dos protecciones anti-DoS documentadas en el README viven precisamente en los dos caminos *deprecados*, no en el canónico.

El puntaje refleja un proyecto con **sustancia científica real y envoltura de ingeniería no confiable**: se puede investigar con él, pero no se puede instalar, desplegar, ni creer en su documentación de portada.

---

## 2. HALLAZGOS POR DOMINIO

### DOMINIO 1 — INTEGRIDAD FUNCIONAL

---

**ID:** D1-001
**Severidad:** 🔴
**Dominio:** Integridad funcional
**Título:** `import simulator` falla con `AttributeError` en cualquier entorno sin PyTorch — rompe 25 módulos y 21 archivos de test
**Ubicación:** `cfc_router.py:452` (propiedad `status`) + `cfc_router.py:89-180` (`_load`) + `simulator.py:85`
**Estado:** **[CONFIRMADO]** · **[CONOCIDO PREVIO — variante nueva del "app roto en main por imports"]**

**Descripción.** `CfCRouter.__init__` inicializa `_sel`, `_tau`, `_arch`, `_residual` y `_torch_available`, y luego llama a `self._load()`. `_load()` hace `return` temprano cuando `import torch` falla (líneas 90-96). Los atributos `_lambda_corrector` y `_landscape_corrector` **solo se asignan después** de ese `return` (líneas 167 y 176). La propiedad `status` los lee incondicionalmente. `simulator.py:85` evalúa `_cfc.status["regime_selector"]` **a nivel de módulo** dentro de un `try/except ImportError` que no captura `AttributeError`.

**Evidencia.**
```
$ python -c "import simulator"
[TDA] ripser/persim no instalados — detección topológica desactivada.
Traceback (most recent call last):
  File "<string>", line 1, in <module>
  File "/home/user/MASSIVE/simulator.py", line 85, in <module>
    CFC_AVAILABLE = _cfc.status["regime_selector"]
  File "/home/user/MASSIVE/cfc_router.py", line 452, in status
    "lambda_corrector": self._lambda_corrector is not None,
AttributeError: 'CfCRouter' object has no attribute '_lambda_corrector'
```
Módulos que fallan en cascada (25 de 146 = 17 %): `simulator`, `social_architect`, `energy_runner`, `uil_adapter`, `backend.app.main`, `backend.app.routers.{sim,llm}`, `services` (+5 submódulos), `benchmarks.runner`, `forecast` (+5 submódulos), `adapters.mutalambda` (+1).

```
$ python -m pytest tests/ --collect-only
!!!!!!!!!!!!!!!!!!! Interrupted: 21 errors during collection !!!!!!!!!!!!!!!!!!!
ERROR tests/test_simulator.py - AttributeError: 'CfCRouter' object has no attribute '_lambda_corrector'
... (21 archivos)
```

**Impacto.** El módulo central del proyecto es no-importable en la configuración de dependencias *base* declarada en `pyproject.toml` (torch está solo en el extra `ml`). Bloquea el job `core` de `pytest.yml`, el ejemplo del README basado en `simulator`, y toda la cadena `forecast → social_architect → adapters`. Viola explícitamente el contrato documentado en el propio docstring de `cfc_router.py`: *"Principio rector: CfC nunca bloquea. Sin PyTorch instalado → fallback transparente."*

**Acción sugerida.** Inicializar `_lambda_corrector = None` y `_landscape_corrector = None` en `__init__` junto a los otros cuatro; ampliar el `except ImportError` de `simulator.py:83-87` a `except Exception` con log de warning; añadir un test que ejecute `import simulator` en un subprocess con `torch` bloqueado.

**Esfuerzo:** XS

---

**ID:** D1-002
**Severidad:** 🔴
**Dominio:** Integridad funcional
**Título:** El "fallback NumPy" de `cfc_engine.py` no existe — el mensaje de warning miente y el módulo falla al definir las clases
**Ubicación:** `cfc_engine.py:21-34` (bloque `try/except ImportError`) + líneas 65-68, 110-112, 151, 210-213, 265-266, 301, 321, 343
**Estado:** **[CONFIRMADO]**

**Descripción.** Ante la ausencia de torch, el módulo hace `torch = None` y fabrica un `nn` falso (`nn = type("nn", (), {"Module": object})()`), y emite el warning *"CFC engine usará implementación NumPy fallback"*. Pero **no hay ninguna implementación NumPy**: las anotaciones de tipo de los `forward()` (`x: torch.Tensor`) se evalúan en tiempo de definición de función (no hay `from __future__ import annotations`), por lo que `torch.Tensor` → `AttributeError: 'NoneType' object has no attribute 'Tensor'` durante la propia definición de las clases.

**Evidencia.**
```
$ python -c "import cfc_engine"
cfc_engine.py:31: UserWarning: PyTorch no disponible: No module named 'torch'.
  CFC engine usará implementación NumPy fallback. Instale con: pip install torch
AttributeError: 'NoneType' object has no attribute 'Tensor'
```
Búsqueda de implementaciones NumPy en `cfc_engine.py`: 0 ocurrencias de `np.` fuera del bloque de fallback.

**Impacto.** Doble defecto: (a) funcional — el módulo es inutilizable sin torch pese a declararse lo contrario; (b) de honestidad — el warning promete un comportamiento que el código no puede cumplir, lo que induce a diagnóstico erróneo.

**Acción sugerida.** O bien (i) añadir `from __future__ import annotations` y reemplazar las anotaciones por strings/cualificadas + una rama NumPy real, o (ii) eliminar el bloque de fallback falso, declarar `torch` como dependencia dura y corregir docstrings/warning. La opción (ii) es coherente con D5-008.

**Esfuerzo:** S (opción ii) / L (opción i)

---

**ID:** D1-003
**Severidad:** 🔴
**Dominio:** Integridad funcional
**Título:** `simulator.py` importa `extended_models` desde root, pero el módulo vive en `massive/core/` — se desactiva en silencio y sin warning
**Ubicación:** `simulator.py:73-78`; canonical en `massive/core/extended_models.py`
**Estado:** **[CONFIRMADO]**

**Descripción.** El patrón de migración del repo es: módulo canónico en `massive/core/X.py` + shim deprecado en root `X.py`. Existen shims para `empirical_config`, `empirical_calibration`, `llm_credentials`, `state_compression`, `schemas`. **No existe shim para `extended_models`.** Por lo tanto `from extended_models import regla_bayesiana, regla_nash, regla_sir` falla siempre, `EXTENDED_MODELS_AVAILABLE` queda en `False` permanentemente, y —a diferencia de las ramas TDA y LangChain— **no se emite ningún log**.

**Evidencia.**
```
$ python -c "from extended_models import regla_bayesiana"
FAIL: No module named 'extended_models'

$ find . -name "extended_models*" -not -path "./.git/*"
./massive/core/extended_models.py       # único

$ grep -rn "extended_models" --include="*.py" .
./simulator.py:74:    from extended_models import regla_bayesiana, regla_nash, regla_sir
./experiments/01_unit/run_invariant_tests.py:36:  from massive.core.extended_models import ...   # ruta correcta
```
Cobertura de `massive/core/extended_models.py`: **0.0 %** (205 sentencias).

**Impacto.** Tres reglas científicas (Bayes, Nash, SIR) están permanentemente desactivadas en el simulador principal sin que ningún log, métrica ni test lo denuncie. Los `experiments/` usan la ruta correcta, así que los resultados de experiments y los de simulator **no son comparables**.

**Acción sugerida.** Corregir a `from massive.core.extended_models import ...`; añadir un `log.warning` en la rama `except ImportError` para paridad con TDA/LangChain; añadir un test que afirme `EXTENDED_MODELS_AVAILABLE is True`.

**Esfuerzo:** XS

---

**ID:** D1-004
**Severidad:** 🔴
**Dominio:** Integridad funcional
**Título:** La recolección de pytest se interrumpe por completo en el entorno de dependencias que instala el job `core` de CI
**Ubicación:** `tests/` (59 archivos) · `.github/workflows/pytest.yml:18-28`
**Estado:** **[CONFIRMADO]**

**Descripción.** El job `core` instala explícitamente numpy, scipy, pandas, networkx, pydantic, pyyaml, python-dotenv, pytest, plotly, requests — **sin torch** — y a continuación ejecuta `tests/test_simulator.py`. Ese entorno es exactamente el que reproduce D1-001.

**Evidencia.**
```
$ python -m pytest tests/ --collect-only -q        # sin torch
!!!!!!!!!!!!!!!!!!! Interrupted: 21 errors during collection !!!!!!!!!!!!!!!!!!!

$ python -m pytest tests/ --collect-only -q        # con torch
tests/test_simulator.py: 5  ...  (681 tests recolectados, 0 errores)
```
Adicionalmente, 3 archivos (`test_api_security.py`, `test_backend_observability.py`, `test_llm_endpoint.py`) fallan la colección incluso con torch por `RuntimeError: The starlette.testclient module requires httpx` — `httpx` no está en `requirements.txt` (ver D5-005).

**Impacto.** Cero señal de test en el job más rápido de la matriz. Como `full-suite` tiene `needs: [core, scientific, api]`, **toda la suite queda `skipped`** — confirmado en el run real: `JOB: full-suite => skipped`.

**Acción sugerida.** Unificar la instalación de dependencias de los 4 jobs en un solo paso reutilizable (composite action o `pip install -r requirements.txt` + `httpx`), o al mínimo añadir `torch` y `httpx` al job `core`.

**Esfuerzo:** S

---

**ID:** D1-005
**Severidad:** 🟠
**Dominio:** Integridad funcional
**Título:** `mamba_engine.py` / `MambaBaseline` no existen — el brief los lista y el mapa del sistema los referencia
**Ubicación:** árbol completo · `MASSIVE_SYSTEM_MAP.md:539`
**Estado:** **[CONFIRMADO]** · **[CONOCIDO PREVIO]**

**Descripción.** No hay ningún archivo con "mamba" en el nombre, ni ninguna referencia a `MambaBaseline` en 245 archivos Python. El issue #59 (`feat: Mamba SSM benchmark baseline`) introdujo el módulo; fue eliminado después. Queda un único residuo documental.

**Evidencia.**
```
$ python -c "from mamba_engine import MambaBaseline"
ModuleNotFoundError: No module named 'mamba_engine'

$ find . -iname "*mamba*" -not -path "./.git/*"     # (vacío)
$ grep -rn "MambaBaseline" . --include="*.py"        # (vacío)
$ grep -rn "mamba_engine" .
./MASSIVE_SYSTEM_MAP.md:539:├── test_mamba_engine.py
```

**Impacto.** El documento presentado como mapa autoritativo del sistema (`MASSIVE_SYSTEM_MAP.md`, 36 KB) describe archivos inexistentes. El README sigue promocionando "Mamba/SSM" como capacidad en el brief de producto.

**Acción sugerida.** Eliminar la entrada del system map, o restaurar el baseline Mamba si sigue siendo parte de la propuesta de valor. Decidir explícitamente; no dejar la referencia huérfana.

**Esfuerzo:** XS

---

**ID:** D1-006
**Severidad:** 🟠
**Dominio:** Integridad funcional
**Título:** `app.py` (Streamlit) no existe pero está referenciado 22 veces, el topic de GitHub sigue siendo `streamlit`, y `requirements.txt` sigue instalando Streamlit
**Ubicación:** árbol completo · `requirements.txt:29` · topics del repo · 22 archivos `.md`
**Estado:** **[CONFIRMADO]** · **[CONOCIDO PREVIO — el item "1.3 streamlit run app.py" del brief]**

**Descripción.** La app Streamlit fue eliminada (OPS-02, documentado en `CHANGELOG.md:89` y en `pyproject.toml`: *"Streamlit (legacy UIL demo flow) was removed — see OPS-02"*). Sin embargo: (a) `requirements.txt` conserva `streamlit>=1.36.0` con el comentario "UI (Streamlit legacy UIL demo flow — optional in Docker)"; (b) 0 imports de streamlit en 245 archivos Python; (c) el topic de GitHub `streamlit` sigue activo; (d) 22 archivos Markdown siguen referenciando `app.py`; (e) `PLAN_INTEGRACION_UI_NG.md` es un plan de 11 KB para eliminar algo que ya fue eliminado.

**Evidencia.**
```
$ ls app.py                       → No such file or directory
$ grep -rn "import streamlit" --include="*.py" .   → 0 resultados
$ gh repo view --json repositoryTopics → [... {"name":"streamlit"} ...]
$ grep -rln "app\.py" --include="*.md" . | wc -l   → 22
```

**Impacto.** ~100 MB de dependencias muertas instaladas en cada entorno y en la imagen Docker. El punto 1.3 del checklist de auditoría ("¿la app Streamlit levanta?") es inejecutable. Un visitante que llega por el topic `streamlit` encuentra un proyecto que ya no es Streamlit.

**Acción sugerida.** Eliminar `streamlit` de `requirements.txt`, retirar el topic, y purgar/anotar las 22 referencias a `app.py`.

**Esfuerzo:** S

---

**ID:** D1-007
**Severidad:** 🟢
**Dominio:** Integridad funcional
**Título:** `simulator_core/` no existe — item del contexto previo resuelto
**Ubicación:** árbol completo
**Estado:** **[CONFIRMADO — RESUELTO]** · **[CONOCIDO PREVIO]**

**Descripción.** El brief mencionaba la coexistencia de `massive/`, `massive_core/`, `simulator_core/` y `micro_massive/`. `simulator_core/` no existe en el árbol. La confusión modular real es otra: `massive/core/` (legacy) vs `massive_core/` (científico opt-in) — ver D3-010.

**Evidencia.** `find . -name "simulator_core" -not -path "./.git/*"` → vacío.

**Impacto.** Ninguno (resuelto).

**Acción sugerida.** Ninguna. Documentar en el system map que la separación es `massive/core/` (legacy core) ↔ `massive_core/` (scientific opt-in).

**Esfuerzo:** XS

---

**ID:** D1-008
**Severidad:** 🟡
**Dominio:** Integridad funcional
**Título:** Efectos colaterales en tiempo de import: `import simulator` crea archivos en el CWD
**Ubicación:** `simulator.py:100-108` · `cache_manager.py:23-38`
**Estado:** **[CONFIRMADO]**

**Descripción.** `simulator.py` ejecuta `logging.basicConfig(..., handlers=[logging.FileHandler(Path("massive_run.log")), ...])` a nivel de módulo. Cualquier import —incluido desde un test, un worker de uvicorn o un notebook— escribe un archivo en el directorio de trabajo actual. `LandscapeCache` hace lo propio con `landscapes_cache.db`.

**Evidencia.**
```
$ ls -la massive_run.log landscapes_cache.db
-rw-r--r-- 1 user user 12288 Sep 15 20:50 landscapes_cache.db
-rw-r--r-- 1 user user  2574 Sep 15 21:17 massive_run.log
```

**Impacto.** Rompe en sistemas de archivos de solo lectura (serverless, contenedores read-only, HF Spaces, AWS Lambda). Contamina el CWD de cualquier consumidor. `basicConfig` en una librería secuestra la configuración de logging de la aplicación anfitriona.

**Acción sugerida.** Mover `basicConfig` a los puntos de entrada (`massive/cli/main.py`, `backend/app/main.py` vía `massive_core/config/logging_setup.py`); usar `NullHandler` en los módulos de librería; hacer `LOG_PATH` configurable vía env con default en un directorio temporal.

**Esfuerzo:** S

---

**ID:** D1-009
**Severidad:** 🟡
**Dominio:** Integridad funcional
**Título:** Inventario de importabilidad: 121/146 OK sin torch, 146/146 con torch
**Ubicación:** repo completo
**Estado:** **[CONFIRMADO]**

**Descripción.** Barrido sistemático de los 146 módulos importables (31 root + paquetes `massive`, `massive_core`, `micro_massive`, `backend`, `services`, `benchmarks`, `forecast`, `adapters`, `scripts`).

**Evidencia.**
```
SIN torch:   OK: 121  FAIL: 25
  - 21 × AttributeError '_lambda_corrector'  (D1-001)
  - 1  × cfc_engine: 'NoneType' has no attribute 'Tensor'  (D1-002)
  - 2  × massive_core.neural_physics[.pinns]: No module named 'torch'  (sin fallback)
  - 1  × benchmark_scalability: No module named 'psutil'  (D5-005)
CON torch:   OK: 146  FAIL: 0
```

**Impacto.** Cuantifica el radio de explosión de D1-001/D1-002: 17 % del codebase.

**Acción sugerida.** Convertir este barrido en un test de humo parametrizado (`tests/test_import_smoke.py`) ejecutado en dos matrices de dependencias: mínima y completa.

**Esfuerzo:** S

---

**ID:** D1-010
**Severidad:** 🟢
**Dominio:** Integridad funcional
**Título:** Cero errores de sintaxis y cero imports relativos rotos en 245 archivos
**Ubicación:** repo completo
**Estado:** **[CONFIRMADO — POSITIVO]**

**Descripción.** Parseo AST exhaustivo de los 245 archivos Python: 0 `SyntaxError`. 0 imports relativos (`from .x import`) en paquetes sin `__init__.py`. Los 42 paquetes del repo tienen `__init__.py` correcto.

**Evidencia.** `Syntax/relative-import problems: 0` (script AST propio sobre 245 archivos).

**Impacto.** Positivo: el punto 1.5 del brief no arroja hallazgos.

**Acción sugerida.** Ninguna.

**Esfuerzo:** —

---

**ID:** D1-011
**Severidad:** 🟡
**Dominio:** Integridad funcional
**Título:** `docker-compose config` no verificable en el sandbox — validación YAML sustituta OK
**Ubicación:** `docker-compose.yml`, `docker-compose.single.yml`
**Estado:** **[HIPÓTESIS]** · punto 1.4 del brief

**Descripción.** `docker` y `docker-compose` no están disponibles en el entorno de auditoría. Se sustituyó por validación de esquema YAML.

**Evidencia.**
```
$ which docker docker-compose   → (vacío)
$ python -c "yaml.safe_load(...)"
OK   docker-compose.yml
OK   docker-compose.single.yml
OK   massive-ui-ng/infra/docker-compose.yml
OK   mkdocs.yml + 13 workflows + configs/*.yaml   (20/20 OK)
```
Ambos compose usan la forma moderna `services:` sin clave `version:` obsoleta. **Pero** el build de `docker-compose.single.yml` apunta a `Dockerfile.optimized`, que es sintácticamente inválido (D7-004).

**Impacto.** El compose es estructuralmente válido pero semánticamente inviable por el Dockerfile al que apunta.

**Acción sugerida.** Verificar `docker compose config` en un entorno con Docker como parte del gate de la Wave 4.

**Esfuerzo:** XS

---

### DOMINIO 2 — CALIDAD DE CÓDIGO PYTHON

---

**ID:** D2-001
**Severidad:** 🔴
**Dominio:** Calidad de código
**Título:** `ruff check .` falla (28 issues, exit 1) — bloquea `lint.yml` y la cadena completa de `publish.yml`
**Ubicación:** repo completo · `.github/workflows/lint.yml:29` · `.github/workflows/publish.yml:28`
**Estado:** **[CONFIRMADO]**

**Descripción.** Con la configuración del propio repo (`[tool.ruff]` en `pyproject.toml`, select `E,F,I,UP,B,SIM`), ruff reporta 28 violaciones. `publish.yml` tiene `needs: lint` en **todos** los jobs de build/publish, así que un ruff rojo congela PyPI, GHCR, Docker, docs y benchmark.

**Evidencia.**
```
$ ruff check . ; echo $?
28 issues · exit=1

Por código:  E402:9  F841:6  F401:3  B904:3  B007:3  I001:1  B028:1  F404:1  SIM108:1
Por archivo: energy_engine.py:6  massive-ui-ng/backend/app/main.py:6
             train_cfc_lambda.py:4  train_cfc_landscape.py:3  train_cfc_temp.py:3
             micro_schemas.py:2  backend/app/models/dto_simulation.py:1
             cfc_engine.py:1  energy_schemas.py:1  schemas.py:1

Detalle relevante:
F404  massive-ui-ng/backend/app/main.py:26  `from __future__` imports must occur at the beginning of the file
E402  energy_schemas.py:16 / micro_schemas.py:16,18 / schemas.py:15  module import not at top
F841  energy_engine.py:360,365,366,372,373,466  variables calculadas y descartadas (ver D9-004)
B904  train_cfc_{lambda,landscape,temp}.py  raise sin `from err`
F401  train_cfc_{lambda,landscape,temp}.py:~66  `torch` importado solo para探测 disponibilidad
```

**Impacto.** CI rojo permanente en cuanto se restaure la facturación. 47 issues son auto-fixeables con `ruff --fix`.

**Acción sugerida.** `ruff check . --fix` (47 fixables), luego corrección manual de `F404`/`E402` (reordenar `from __future__` antes del docstring en `massive-ui-ng/backend/app/main.py`, `schemas.py`, `micro_schemas.py`, `energy_schemas.py`) y de los 6 `F841` de `energy_engine.py`.

**Esfuerzo:** S

---

**ID:** D2-002
**Severidad:** 🔴
**Dominio:** Calidad de código
**Título:** `black --check .` reformatearía 30 de 245 archivos (exit 1)
**Ubicación:** repo completo · `.github/workflows/lint.yml:32` · `.github/workflows/publish.yml:29`
**Estado:** **[CONFIRMADO]**

**Descripción.** El README afirma *"Static quality: ruff + black + mypy (gradual slice) green in CI"*. Black no está verde.

**Evidencia.**
```
$ black --check .
would reformat /home/user/MASSIVE/tests/test_gini_rule_bridge.py
would reformat /home/user/MASSIVE/simulator.py
would reformat /home/user/MASSIVE/train_cfc_lambda.py
would reformat /home/user/MASSIVE/train_cfc_landscape.py
would reformat /home/user/MASSIVE/train_cfc_temp.py
Oh no! 💥 💔 💥
30 files would be reformatted, 215 files would be left unchanged.
exit=1
```
Nota: la versión de black del sandbox puede diferir de la de CI (no pinneada, ver D5-003), lo que es en sí mismo parte del problema: `black>=24` sin pin significa que el formateo puede cambiar entre runs.

**Impacto.** CI rojo. Peor: como black no está pinneado, un bump de versión puede rojear el repo sin ningún cambio de código.

**Acción sugerida.** `black .` una vez, commitear, y pinnear la versión exacta de black + ruff en un `requirements-dev.txt` o en el extra `dev`.

**Esfuerzo:** XS

---

**ID:** D2-003
**Severidad:** 🟠
**Dominio:** Calidad de código
**Título:** 198 errores de tipo repo-wide; 36 en el slice que ejecuta CI
**Ubicación:** repo completo · `.github/workflows/lint.yml:47-56`
**Estado:** **[CONFIRMADO]**

**Descripción.**

**Evidencia.**
```
$ mypy . --ignore-missing-imports --exclude 'massive-ui-ng/|frontend/|node_modules/'
Found 198 errors in 46 files (checked 216 source files)

Histograma de códigos:
  39 [call-arg]   36 [attr-defined]   36 [arg-type]   35 [assignment]
  22 [operator]    9 [return-value]    9 [annotation-unchecked]
   7 [var-annotated]  6 [unused-ignore]  5 [index]  2 [union-attr]
   2 [import]  1 [misc]  1 [mask]  1 [func-returns-value]

$ mypy --config-file mypy.ini massive/ backend/ services/ massive_core/   # lo que corre CI
Found 36 errors in 16 files (checked 83 source files)

Ejemplos con riesgo real de runtime:
backend/app/routers/llm.py:162: error: "LLMLlmHint" has no attribute "api_key"  [attr-defined]
services/llm_orchestrator.py:479: error: Incompatible types in assignment
    (expression has type "ForecastResult", variable has type "dict[str, Any]")  [assignment]
backend/app/routers/engine.py:89: error: Argument "config" to "buscar_estrategia_inversa"
    has incompatible type "Any | None"; expected "dict[Any, Any]"  [arg-type]
backend/app/main.py:304: error: Unused "type: ignore" comment  [unused-ignore]
```

**Impacto.** `[attr-defined]` sobre `payload.llm.api_key` es un `AttributeError` latente en producción en `/v1/llm/*`. Los 39 `[call-arg]` indican llamadas con firma desincronizada — la clase de bug que la migración api.py → backend/ suele dejar atrás.

**Acción sugerida.** Triar los 36 del slice primero (son los que CI mira), priorizando `attr-defined` y `call-arg`; luego quemar el resto por paquete.

**Esfuerzo:** L

---

**ID:** D2-004
**Severidad:** 🟠
**Dominio:** Calidad de código
**Título:** `mypy .` aborta sin analizar nada: "Duplicate module named backend"
**Ubicación:** `backend/__init__.py` vs `massive-ui-ng/backend/__init__.py` · `mypy.ini` (sin `exclude`)
**Estado:** **[CONFIRMADO]**

**Descripción.** Dos paquetes llamados `backend` en el mismo árbol, ambos con `__init__.py`, y `mypy.ini` no declara `exclude` ni `namespace_packages` resuelve el conflicto. mypy sale con código 2 sin chequear un solo archivo.

**Evidencia.**
```
$ mypy . --ignore-missing-imports
massive-ui-ng/backend/__init__.py: error: Duplicate module named "backend"
(also at "./backend/__init__.py")
note: Common resolutions include:
note:     a) using `--exclude` to avoid checking one of them,
exit=2 · 1 error · 0 archivos analizados
```

**Impacto.** Nadie puede ejecutar mypy sobre el repo completo. Cualquier desarrollador que intente `mypy .` recibe un error de herramienta, no de código, y probablemente lo abandone.

**Acción sugerida.** Añadir `exclude = (?x)(^massive-ui-ng/|^frontend/|^node_modules/|^site/)` a `mypy.ini`, o renombrar `massive-ui-ng/backend` → `massive_ui_ng_backend`. El renombrado resuelve también D3-003 y D3-005.

**Esfuerzo:** XS (exclude) / M (renombrado)

---

**ID:** D2-005
**Severidad:** 🟠
**Dominio:** Calidad de código
**Título:** 127 `except Exception` y 26 handlers que silencian con `pass`/`continue`
**Ubicación:** repo completo
**Estado:** **[CONFIRMADO]**

**Descripción.** Análisis AST de todos los `ExceptHandler` del repo.

**Evidencia.**
```
bare `except:` handlers          : 0     ← positivo (ver D2-007)
`except Exception` handlers      : 127
handlers silenciados (solo pass) : 26

Distribución de los 26 silenciados:
  benchmark_scalability.py:80,88,126,137     cache_manager.py:56,74,84
  energy_engine.py:238                        massive_engine.py:69,78
  multilayer_engine.py:667                    services/llm_orchestrator.py:776
  massive-ui-ng/backend/app/llm_chat.py:187,191,210,217
  massive-ui-ng/backend/app/routers/live.py:68
  massive-ui-ng/backend/app/routers/status.py:32,40,49
  scripts/todo_triage.py:46  experiments/08_enkf_delta/exp_003_enkf.py:97
  tests/test_cfc_engine.py:28  massive-ui-ng/tests/test_ui_ng_live.py:85,122,144

Ruff extendido: 93 × BLE001 (blind-except)
```
Los 3 de `cache_manager.py` son los más graves: son las tres operaciones de persistencia (ver D9-003).

**Impacto.** Fallos de E/S, de red y de base de datos se convierten en `None`/no-op silenciosos. En un sistema científico esto produce resultados incorrectos sin rastro, que es peor que un crash.

**Acción sugerida.** Reemplazar cada `pass` por `log.warning(..., exc_info=True)` o por un re-raise tipado; en `cache_manager.py`, propagar o degradar explícitamente a modo memory-only con métrica.

**Esfuerzo:** M

---

**ID:** D2-006
**Severidad:** 🟠
**Dominio:** Calidad de código
**Título:** `energy_engine.py` calcula y descarta 6 valores en el hot path del paisaje de energía
**Ubicación:** `energy_engine.py:360, 365, 366, 372, 373, 466`
**Estado:** **[CONFIRMADO]**

**Descripción.** `sigma2`, `att_positions`, `att_strengths`, `rep_positions`, `rep_strengths` y `gini` se asignan y nunca se leen.

**Evidencia.**
```
F841 energy_engine.py:360  Local variable `sigma2` is assigned to but never used
F841 energy_engine.py:365  Local variable `att_positions` is assigned to but never used
F841 energy_engine.py:366  Local variable `att_strengths` is assigned to but never used
F841 energy_engine.py:372  Local variable `rep_positions` is assigned to but never used
F841 energy_engine.py:373  Local variable `rep_strengths` is assigned to but never used
F841 energy_engine.py:466  Local variable `gini` is assigned to but never used
```

**Impacto.** Doble: (a) cómputo desperdiciado en el engine que el README reporta como el más costoso en memoria (16.8 GB a 100M agentes); (b) señal fuerte de que una refactorización quedó a medias — o bien esos valores *deberían* usarse (bug funcional latente) o bien el código es residual.

**Acción sugerida.** Decidir por variable: si el cálculo era necesario para la dinámica, cablearlo; si no, borrarlo. `gini` en particular aparece en el plan de coherencia reactiva como señal de acoplamiento — verificar si se perdió el cableado.

**Esfuerzo:** S

---

**ID:** D2-007
**Severidad:** 🟢
**Dominio:** Calidad de código
**Título:** Cero `except:` desnudos en todo el repo
**Ubicación:** repo completo
**Estado:** **[CONFIRMADO — POSITIVO]**

**Descripción.** El punto 2.6 del brief (`grep -rn "except:"`) arroja 0 coincidencias en 245 archivos. Todos los handlers especifican tipo.

**Evidencia.** `grep -rn "except:" --include="*.py" . | wc -l` → `0` · AST: `bare except handlers: 0`.

**Impacto.** Positivo.

**Acción sugerida.** Ninguna.

**Esfuerzo:** —

---

**ID:** D2-008
**Severidad:** 🟡
**Dominio:** Calidad de código
**Título:** `print()` en código de librería — 156 ocurrencias vs 347 de logging
**Ubicación:** repo completo · notable en `cache_manager.py`, `programmatic_architect.py`, `scripts/`
**Estado:** **[CONFIRMADO]**

**Descripción.** Ratio 156 `print(` : 80 `logging.` : 267 `log.<nivel>(`. El ratio no es catastrófico, pero el problema cualitativo es que hay `print()` dentro de **código de librería** que se ejecuta bajo un servidor FastAPI.

**Evidencia.**
```
$ grep -rn "print(" --include="*.py" . | wc -l    → 156
$ grep -rn "logging\." --include="*.py" . | wc -l → 80
$ grep -rnE '\blog(ger)?\.(debug|info|warning|error|critical|exception)' → 267

cache_manager.py:36   print(f"[Cache] ⚠️ No se pudo inicializar SQLite: {e}. Caché solo en memoria.")
```
Ruff extendido: 0 × T201 en el set seleccionado, porque la regla `T20` no está habilitada en `[tool.ruff.lint] select`.

**Impacto.** Salida no estructurada, sin nivel, sin timestamp, sin correlación con `X-Request-ID`, imposible de filtrar en producción. En `cache_manager.py` el `print` incluye el emoji `⚠️`, que rompe en terminales no-UTF8.

**Acción sugerida.** Habilitar `T20` en ruff para los paquetes de librería (excluyendo `scripts/`, `benchmarks/` y `experiments/`, donde `print` es la interfaz); migrar `cache_manager.py` a `logging`.

**Esfuerzo:** S

---

**ID:** D2-009
**Severidad:** 🟡
**Dominio:** Calidad de código
**Título:** `logging.basicConfig` invocado 13 veces, incluidas 2 en módulos de test y 2 a nivel de módulo de librería
**Ubicación:** ver lista
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
simulator.py:102                              ← nivel de módulo de librería (ver D1-008)
massive-ui-ng/backend/app/main.py:49          ← nivel de módulo de librería
backend/app/main.py:51                        ← dentro de except fallback (aceptable)
massive_core/config/logging_setup.py:52       ← canónico (correcto)
massive/cli/main.py:27                        ← entrypoint (correcto)
benchmark_scalability.py:63 · benchmarks/runner.py:48  ← entrypoints (correcto)
cfc_trainer.py:358 · train_cfc_{lambda,landscape,temp}.py:~290  ← __main__ (correcto)
tests/test_factbook_integration.py:15         ← ✗ contamina la config global de pytest
tests/test_sparse_refactor.py:10              ← ✗ idem
```

**Impacto.** `basicConfig` es un no-op si ya hay handlers, así que **el primero en ejecutarse gana** — el orden de import determina la configuración de logging de todo el proceso. Los dos de `tests/` hacen que la suite se comporte distinto según el orden de colección.

**Acción sugerida.** Eliminar `basicConfig` de `simulator.py`, `massive-ui-ng/backend/app/main.py` y de los dos tests; centralizar en `massive_core/config/logging_setup.py`.

**Esfuerzo:** S

---

**ID:** D2-010
**Severidad:** 🟡
**Dominio:** Calidad de código
**Título:** Tres convenciones de nombrado de logger coexisten; ninguna coincide con `__name__` de forma consistente
**Ubicación:** repo completo · canonical sin adoptar: `massive_core/config/logging_setup.py`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
14 × logging.getLogger("massive")            ← logger único, sin granularidad de módulo
 6 × logging.getLogger(__name__)              ← convención correcta
~20 × nombres punteados a mano que NO coinciden con la ruta real:
   massive/core/factbook/loader.py     → getLogger("massive.factbook.loader")     (debería ser massive.core.factbook.loader)
   massive/core/factbook/validator.py  → getLogger("massive.factbook.validator")
   massive/core/utility_logic.py       → getLogger("massive.utility_logic")
   services/llm_orchestrator.py        → getLogger("massive.services.llm_orchestrator")
   massive-ui-ng/backend/app/*.py      → getLogger("massive.ui_ng.*")   (11 módulos)
   tests/test_factbook_integration.py  → getLogger("test_factbook")
```

**Impacto.** Imposible filtrar logs por módulo real; los 14 que usan `"massive"` colapsan todo el sistema en un solo canal. `logging_setup.py` existe y está documentado como canónico pero sólo lo consume `backend/app/main.py`.

**Acción sugerida.** Estandarizar en `getLogger(__name__)` en toda la librería y configurar la jerarquía desde `logging_setup.py`.

**Esfuerzo:** M

---

**ID:** D2-011
**Severidad:** 🟡
**Dominio:** Calidad de código
**Título:** 12 bloques con complejidad ciclomática ≥ D; dos en grado F
**Ubicación:** ver tabla
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ radon cc . -s -n B --average
312 blocks analyzed. Average complexity: B (9.53)

$ radon cc . -s -n D
massive-ui-ng/backend/app/narrative.py:234      build_narrative                 F (57)
services/llm_orchestrator.py:292                _dispatch                       F (50)
massive-ui-ng/backend/app/scenario_parser.py:272 interpret                      E (39)
massive-ui-ng/backend/app/evaluation.py:43      _score_case                     E (32)
social_architect.py:491                         buscar_estrategia_inversa       D (27)
energy_runner.py:15                             run_energy_simulation           D (26)
simulator.py:1530                               simular                         D (26)
benchmark_scalability.py:647 / :705             compute_median_results / main   D (24) / D (24)
experiments/03_calibration/run_calibration.py:32 test_cultural_profiles         D (23)
scripts/gen_ts_types.py:95                      _schema_to_ts                   D (22)
massive-ui-ng/infra/scripts/gen_ts_types.py:102 _schema_to_ts                   D (22)   ← duplicado
```

**Impacto.** `_dispatch` (F-50) es el router central del orquestador LLM: cualquier motor nuevo implica tocar una función de 50 decisiones, y es además donde mypy detecta el error de tipo con riesgo de runtime (D2-003). `build_narrative` (F-57) vive en el backend excluido de CI.

**Acción sugerida.** Extraer `_dispatch` a una tabla de dispatch `{motor: handler}`; dividir `build_narrative` por sección narrativa; eliminar el `gen_ts_types.py` duplicado (D3-019).

**Esfuerzo:** M

---

**ID:** D2-012
**Severidad:** 🟡
**Dominio:** Calidad de código
**Título:** `train_cfc_lambda.py`, `train_cfc_landscape.py` y `train_cfc_temp.py` son clones ~85 % idénticos
**Ubicación:** 3 archivos root, 11 223 / 12 030 / 11 383 bytes
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ pylint . --disable=all --enable=R0801
9 bloques duplicados detectados:
==train_cfc_lambda:[93:117]   ==train_cfc_temp:[89:114]        (25 líneas)
==train_cfc_lambda:[171:193]  ==train_cfc_temp:[180:202]       (23 líneas, bucle de training)
==train_cfc_landscape:[44:80] ==train_cfc_temp:[45:82]         (37 líneas, setup + logging)
... + 6 bloques más entre los tres
Además: ==api:[60:77] ↔ ==backend.app.main:[81:99]             (configuración CORS duplicada)
```
Los tres comparten además los mismos 3 issues ruff cada uno (`F401 torch`, `B904`, `B007 t`) — evidencia de copy-paste literal.

**Impacto.** ~33 KB de código triplicado. Un fix en el bucle de entrenamiento debe aplicarse 3 veces; los tres tienen 0 % de cobertura (D4-003), así que ninguna regresión se detectaría.

**Acción sugerida.** Extraer un `cfc_trainer.py` genérico parametrizado por (target, feature-builder, model-class) — nótese que `cfc_trainer.py` ya existe en root y también tiene 0 % de cobertura, lo que sugiere que la consolidación se inició y se abandonó.

**Esfuerzo:** M

---

**ID:** D2-013
**Severidad:** 🟡
**Dominio:** Calidad de código
**Título:** Código muerto: 311 hallazgos de vulture al 60 %, con núcleos completos sin consumidores
**Ubicación:** ver lista
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ vulture . --min-confidence 80     → 2 hallazgos
   massive/core/factbook/validator.py:279  unused variable 'validation_level'
   massive/core/factbook/validator.py:730  unused variable 'comparison_period'

$ vulture . --min-confidence 60     → 311 hallazgos
Muerte real confirmada (cruzada con cobertura 0 %):
   social_connectors.py:146 TwitterConnector  · :177 fetch_opinions
   social_connectors.py:235 RedditConnector   · :269 fetch_opinions      → archivo 0.0 % cobertura
   simulator.py:1821 simular_multiples_dask                              → integración Dask huérfana
   simulator.py:430  _actualizar_pesos_homofilia
   simulator.py:2212 apply_levy_jumps_to_agents
   programmatic_architect.py:290 design_intervention
   massive_core/physics/perturbation_theory.py  (5 métodos/clases, 33 % cobertura)
   massive_core/physics/statistical_mechanics.py (2 métodos, 57 %)
   services/factbook_service.py:43,60 · services/forecast_service.py:22 · services/llm_service.py:35
   micro_schemas.py:103 EnsembleResult (+ 7 campos huérfanos)
   massive_engine.py:86 _get_array_module · :347 _M · :918 _layers_csr
```

**Impacto.** `social_connectors.py` (85 sentencias, 325 líneas) implementa conectores Twitter/Reddit completos —y las dependencias `tweepy` y `praw` están declaradas en `requirements.txt` y `pyproject.toml`— pero nada los consume. Es funcionalidad de producto que no existe.

**Acción sugerida.** Decidir por módulo: cablear (`social_connectors` es feature de producto anunciada), o eliminar + retirar `tweepy`/`praw` de las dependencias.

**Esfuerzo:** M

---

**ID:** D2-014
**Severidad:** 🟡
**Dominio:** Calidad de código
**Título:** Nomenclatura mixta español/inglés para el mismo concepto, a veces dentro de la misma tupla
**Ubicación:** repo completo · caso emblemático `cfc_router.py:45-54`
**Estado:** **[CONFIRMADO]** · **[CONOCIDO PREVIO — punto 2.9 del brief]**

**Evidencia.**
```
$ grep -rnE 'opinion|propaganda|confianza|pertenencia' --include='*.py' . | wc -l → 1596

Concepto          Español      Inglés
confianza/trust      146          30
polarización         48          210
ruido/noise          21           88
homofilia             30           7
pertenencia_grupo    59       (belonging: 2)

Caso concreto — cfc_router.py:45:
_STATE_KEYS = (
    "opinion", "propaganda", "confianza",
    "opinion_grupo_a", "opinion_grupo_b",
    "trust",              ← mismo concepto que "confianza", en la MISMA tupla
    "ews_variance", "ews_autocorr",
)
```
`docs/NAMING_CONVENTIONS.md` existe y `docs/OPTIMIZATION_STATUS.md` registra *"3.2 Rename step/to_dict — Rejected (policy)"*, es decir que la mezcla es una decisión documentada, no un accidente. Pero la decisión no cubre el caso `confianza`/`trust`.

**Impacto.** El vector de entrada del selector de régimen CfC tiene 8 slots de los cuales dos son sinónimos. Si el estado entrante usa `trust`, `confianza` se rellena con el default; si usa `confianza`, `trust` queda en default. Las predicciones del modelo entrenado con una convención se aplican a estados con la otra → sesgo sistemático silencioso en el fast path neuronal.

**Acción sugerida.** Definir un alias canónico único por concepto en `massive/core/schemas.py` y normalizar en la frontera de entrada del router; documentar la política en `NAMING_CONVENTIONS.md` con la tabla de mapeo completa.

**Esfuerzo:** M

---

**ID:** D2-015
**Severidad:** 🟢
**Dominio:** Calidad de código
**Título:** Cero marcadores TODO/FIXME/HACK/XXX en el código Python
**Ubicación:** repo completo
**Estado:** **[CONFIRMADO — POSITIVO]** · punto 6.6 del brief

**Evidencia.**
```
$ python scripts/todo_triage.py
# MASSIVE TODO triage (0 items)
_No TODO/FIXME markers found outside experiments/site._

$ grep -rnE "TODO|FIXME|HACK|XXX" --include="*.py" . | wc -l → 5
   (los 5 son falsos positivos: "TODOS los agentes" en massive_engine.py:670
    y las 4 auto-referencias del propio scripts/todo_triage.py)
```

**Impacto.** Positivo. La deuda está documentada en `docs/BACKLOG_POST_WORKFLOW.md` / `docs/OPTIMIZATION_STATUS.md` en lugar de ensuciar el código.

**Acción sugerida.** Ninguna.

**Esfuerzo:** —

---

**ID:** D2-016
**Severidad:** 🟡
**Dominio:** Calidad de código
**Título:** URLs y hosts hardcodeados; `interpreter_layer.py` ignora la variable de entorno que el resto sí respeta
**Ubicación:** `interpreter_layer.py:222` · 18 hardcodes `localhost` · 6 URLs de proveedores
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
URLs hardcodeadas en .py (excluyendo tests/comentarios):
  18 × http://localhost        6 × https://openrouter.ai/api/v1
   5 × https://api.groq.com/openai/v1     3 × https://api.openai.com/v1
   2 × https://github.com/Adlgr87/MASSIVE 1 × http://127.0.0.1

Inconsistencia Ollama:
  langchain_workflows.py:147            os.getenv("OLLAMA_HOST", "http://localhost:11434")   ✓
  massive-ui-ng/backend/app/llm_chat.py:59  os.getenv("OLLAMA_HOST", "http://localhost:11434") ✓
  interpreter_layer.py:222              "ollama": {"base_url": "http://localhost:11434/v1"}    ✗ hardcodeado
```
Puerto Ollama `11434`: 10 referencias, de las cuales 1 es hardcode sin escape por env.

**Impacto.** Un despliegue con Ollama en otro host funciona para `langchain_workflows` y para `ui-ng`, pero no para `interpreter_layer` — fallo parcial difícil de diagnosticar.

**Acción sugerida.** Centralizar las URLs base de proveedores en `massive_core/config/settings.py` y consumir desde allí; hacer que `interpreter_layer.py:222` lea `OLLAMA_HOST`.

**Esfuerzo:** S

---

**ID:** D2-017
**Severidad:** 🟡
**Dominio:** Calidad de código
**Título:** Deuda de estilo pytest: 230 asserts estilo unittest y 18 `__all__` sin ordenar
**Ubicación:** `tests/` · repo completo
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ ruff check . --isolated --select ALL (subset de estilo)
230 × PT009  pytest-unittest-assertion       (self.assertEqual en archivos pytest)
 93 × BLE001 blind-except                    (ver D2-005)
 27 × RUF059 unused-unpacked-variable
 18 × RUF022 unsorted-dunder-all
 16 × PT018 pytest-composite-assertion
 14 × FAST002 fast-api-non-annotated-dependency
 13 × PT011 pytest-raises-too-broad
  5 × RUF013 implicit-optional
Total con set extendido: 732 errores, 47 auto-fixeables
```

**Impacto.** Menor en sí mismo, pero `FAST002` (14 dependencias FastAPI sin anotar) y `RUF013` (5 `Optional` implícitos) sí tienen efecto runtime/typing.

**Acción sugerida.** No habilitar `ALL`; sí añadir `PT`, `RUF`, `FAST` al `select` de `[tool.ruff.lint]` de forma incremental, empezando por `FAST002` y `RUF013`.

**Esfuerzo:** S

---

### DOMINIO 3 — ARQUITECTURA Y ORGANIZACIÓN

---

**ID:** D3-001
**Severidad:** 🔴
**Dominio:** Arquitectura
**Título:** `pyproject.toml` no empaqueta los 31 módulos root ni `metrics/` — cualquier wheel construido es import-roto
**Ubicación:** `pyproject.toml:60-63` (`[tool.setuptools.packages.find]`)
**Estado:** **[CONFIRMADO]**

**Descripción.** `include = ["massive*", "backend*", "services*", "benchmarks*", "micro_massive*", "forecast*", "massive_core*"]`. Faltan: los 31 módulos top-level (`simulator.py`, `energy_engine.py`, `massive_engine.py`, `multilayer_engine.py`, `micro_engine.py`, `social_architect.py`, `cfc_*.py`, `api.py`, `energy_runner.py`, `cache_manager.py`, …), el paquete `metrics/`, `monitoring/`, `adapters/` y `experiments/`. No hay `[tool.setuptools] py-modules = [...]`.

**Evidencia.** Los paquetes SÍ incluidos dependen de los NO incluidos:
```
$ grep -rn "^from (simulator|massive_engine|energy_engine|empirical_config) import" backend services forecast massive_core
forecast/engine.py:14              from simulator import DEFAULT_CONFIG
services/simulation_service.py:7   from simulator import DEFAULT_CONFIG, resumen_historial, simular
services/simulation_service.py:10  from simulator import run_with_schedule
services/forecast_service.py:14    from simulator import DEFAULT_CONFIG
backend/app/routers/engine.py:15   from energy_engine import SocialEnergyEngine
backend/app/routers/engine.py:16   from massive_engine import MassiveSimEngine
massive/core/empirical_calibration.py:13  from empirical_config import MASSIVE_EMPIRICAL_MASTER
```
Y `metrics/` es consumido por 5 engines:
```
$ grep -rn "from metrics.unified_metrics import" .
energy_engine.py:25 · massive_engine.py:49 · micro_engine.py:26 · multilayer_engine.py:35 · simulator.py:59
```

**Impacto.** `publish.yml` publica sdist+wheel a PyPI bajo el nombre `massive`. Ese artefacto **no puede funcionar**: `import massive.core.empirical_calibration` → `ModuleNotFoundError: No module named 'empirical_config'`. Además `[project.scripts] massive-cli = "massive.cli.main:main"` apunta a un entrypoint cuyo paquete depende de módulos no empaquetados.

**Acción sugerida.** O (i) declarar `py-modules` con los 31 módulos root + añadir `metrics*`, `adapters*` al `include`; o (ii) —preferible— completar la migración a `massive/core/` y eliminar los módulos root, de modo que el `include` actual sea correcto. La opción (ii) está ya iniciada (ver D3-009) y es la que `docs/OPTIMIZATION_STATUS.md` marca como *"1.2 Delete root wrappers — Rejected (intentional)"*, decisión que debe revisarse porque es incompatible con publicar un wheel.

**Esfuerzo:** L

---

**ID:** D3-002
**Severidad:** 🔴
**Dominio:** Arquitectura
**Título:** Tres backends FastAPI paralelos con superficies divergentes
**Ubicación:** `api.py` (497 líneas) · `backend/app/` (17 archivos) · `massive-ui-ng/backend/app/` (21 archivos)
**Estado:** **[CONFIRMADO]** · **[CONOCIDO PREVIO — "doble entrada API", en realidad triple]**

**Evidencia.**
```
api.py — docstring: "⚠️ DEPRECATED - Legacy API Module ... Please migrate to backend/app/ immediately."
  Rutas: /api/extract, /api/wizard, /api/simulate-uil, /api/v1/architect, /api/v1/forecast,
         /api/v1/energy, /, /health, /ready, /version          (10 rutas, 497 líneas, 32.2 % cobertura)
  Sigue siendo el target de `make api-legacy` y de frontend/ (Vite proxy → /api)

backend/app/ — "Production FastAPI entry-point ... replaces the legacy api.py monolith"
  Rutas reales (OpenAPI en vivo): 22 paths = 9 × /v1/* + 9 × /api/v1/* (alias) + 4 infra

massive-ui-ng/backend/app/ — tercer backend con routers propios
  (conversation, live, simulation, status) + live_runner, llm_chat, narrative,
  scenario_parser, evaluation, run_store, rate_limit, security, settings
  EXCLUIDO de CI ("not in CI root — see ARCH-02" en README)
```
Duplicación funcional concreta: `security.py`, `settings.py`, `metrics.py` y `models/dto_*.py` existen en `backend/app/` **y** en `massive-ui-ng/backend/app/`. Ruff detecta duplicación de bloque `api:[60:77] ↔ backend.app.main:[81:99]` (setup CORS).

**Impacto.** Tres implementaciones de auth, rate-limit, métricas y DTOs que divergen. El brief preguntaba "¿cuál es el punto de entrada real?" — la respuesta verificada es: `backend.app.main:app` (Makefile `api`, supervisord, Dockerfile.optimized, README), pero `frontend/` consume `api.py`, y `massive-ui-ng/frontend/` consume el tercero. Cada bug de seguridad debe arreglarse 3 veces; el hallazgo D5-001 demuestra que no se hace.

**Acción sugerida.** Congelar `api.py` (solo fixes de seguridad), migrar `frontend/` a `/v1/*`, y decidir el destino de `massive-ui-ng/`: o se promueve a canónico (y entonces `backend/` se retira) o se extrae a un repo/rama propia. No mantener los tres.

**Esfuerzo:** XL

---

**ID:** D3-003
**Severidad:** 🔴
**Dominio:** Arquitectura
**Título:** Colisión de namespace `backend` entre root y `massive-ui-ng/` — rompe mypy y el generador de tipos forkado
**Ubicación:** `backend/__init__.py` · `massive-ui-ng/backend/__init__.py` · `massive-ui-ng/infra/scripts/gen_ts_types.py:29`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ mypy . → error: Duplicate module named "backend" (also at "./backend/__init__.py")

$ python massive-ui-ng/infra/scripts/gen_ts_types.py
Traceback (most recent call last):
  File ".../massive-ui-ng/infra/scripts/gen_ts_types.py", line 29, in <module>
    from backend.app.models import (  # noqa: E402
ModuleNotFoundError: No module named 'backend'
```
El script forkado intenta importar `AssumptionItem, CFCStatus, ChatMessage, ConversationRequest, ConversationResponse, ExplainRequest, ExplainResponse, Highlight` — símbolos que viven en `massive-ui-ng/backend/app/models/dto_ui.py`, no en `backend/app/models/`.

**Impacto.** (a) mypy repo-wide imposible (D2-004); (b) el generador de tipos de UI-NG es inejecutable, por lo que `massive-ui-ng/frontend/src/types/api.generated.ts` (244 líneas) no puede regenerarse ni validarse — y de hecho diverge del de `frontend/` (201 líneas); (c) los routers de `massive-ui-ng` hacen `from backend.app.models...`, que sólo resuelve por manipulación de `sys.path` y según el CWD.

**Acción sugerida.** Renombrar `massive-ui-ng/backend/` → `massive_ui_ng/backend/` con `__init__.py` y ajustar los imports internos; o consolidar en un único backend (D3-002).

**Esfuerzo:** M

---

**ID:** D3-004
**Severidad:** 🟠
**Dominio:** Arquitectura
**Título:** La capa de DTOs Pydantic es decorativa en el backend canónico: 5 de 6 routers aceptan `dict[str, Any]` crudo
**Ubicación:** `backend/app/routers/{sim,engine,forecast,benchmark}.py` · `backend/app/models/`
**Estado:** **[CONFIRMADO]**

**Descripción.** `backend/app/models/` define DTOs con `model_config = {"extra": "forbid"}` y restricciones `Field(..., ge=-1.0, le=1.0)`. `scripts/gen_ts_types.py` los compila a TypeScript y `validate_ts_types.yml` verifica la sincronía. Pero los endpoints canónicos no los usan como cuerpo de request.

**Evidencia.**
```
$ grep -rn "payload: dict\[str, Any\]" backend/app/routers/*.py
backend/app/routers/benchmark.py:22  async def v1_benchmarks(request, payload: dict[str, Any])
backend/app/routers/engine.py:25     async def v1_energy(request, payload: dict[str, Any])
backend/app/routers/engine.py:59     async def v1_architect(request, payload: dict[str, Any])
backend/app/routers/forecast.py:24   async def v1_forecast(request, payload: dict[str, Any]) -> ForecastResponse
backend/app/routers/sim.py:26        async def v1_simulate(request, payload: dict[str, Any])
                                     ← solo llm.py:69 usa `payload: LLMRunRequest`

Consumo real de los DTOs:
$ grep -rn "dto_simulation|dto_architect|dto_forecast|dto_llm|dto_snapshot" backend services
backend/app/models/__init__.py  (solo re-export)
backend/app/models/dto_snapshot.py:4  (solo un docstring)
→ NINGÚN router ni service los consume.

Ironía: el backend EXCLUIDO de CI sí los usa:
massive-ui-ng/backend/app/routers/live.py:34        from backend.app.models.dto_simulation import ...
massive-ui-ng/backend/app/routers/conversation.py:18 from backend.app.models.dto_ui import ...
massive-ui-ng/backend/app/routers/simulation.py:33   from backend.app.models.dto_ui import ...
massive-ui-ng/backend/app/routers/status.py:10       from backend.app.models.dto_ui import ...
```

**Impacto.** `extra="forbid"` nunca se aplica → payload drift silencioso. Las cotas `ge/le` nunca se validan → es la causa raíz de D5-001 (sin límites en `pasos`, `n_agents`, `max_intentos`). El contrato TypeScript que consume el frontend describe una API que el backend no valida. El OpenAPI publicado muestra `body: dict` sin esquema.

**Acción sugerida.** Tipar los cuerpos de request con los DTOs existentes (o crear `SimulationRequest`, `ArchitectRequest`, `EnergyRequest`, `BenchmarkRequest`) y dejar que FastAPI devuelva 422. Esto resuelve simultáneamente D5-001 y los 39 errores mypy `[call-arg]`.

**Esfuerzo:** M

---

**ID:** D3-005
**Severidad:** 🟠
**Dominio:** Arquitectura
**Título:** Dos frontends React/Vite paralelos con un archivo de 825 líneas byte-idéntico y tipos generados divergentes
**Ubicación:** `frontend/` (v1.0.0) · `massive-ui-ng/frontend/` (v2.0.0)
**Estado:** **[CONFIRMADO]** · **[CONOCIDO PREVIO — extensión del item "confusión modular"]**

**Evidencia.**
```
frontend/src/MASSIVE_UIL_demo.jsx              825 líneas  ══ IDÉNTICO ══  massive-ui-ng/frontend/src/MASSIVE_UIL_demo.jsx  825 líneas
frontend/src/types/api.generated.ts            201 líneas  ── DIVERGENTE ── massive-ui-ng/frontend/src/types/api.generated.ts 244 líneas
frontend/src/App.tsx                            32 líneas  ── DIVERGENTE ── massive-ui-ng/frontend/src/App.tsx                399 líneas

Stacks incompatibles:
  frontend/            react 18.3.0 · react-router-dom · axios · @radix-ui/react-slot · tailwind · lucide · clsx · eslint+prettier
  massive-ui-ng/frontend/ react 18.3.1 · recharts · SIN router · SIN lint script · SIN eslint · SIN prettier

CI: lint.yml y frontend-build.yml y publish.yml solo construyen `frontend/`.
    massive-ui-ng/frontend no tiene NINGÚN workflow activo (el suyo está muerto, D7-007).
```

**Impacto.** 825 líneas duplicadas que hay que mantener dos veces; dos contratos de tipos que ya divergieron; un frontend (el v2.0.0, presumiblemente el futuro) sin lint, sin typecheck, sin build en CI y sin tests ejecutándose.

**Acción sugerida.** Decidir cuál sobrevive. Si es `massive-ui-ng/frontend`, promoverlo a `frontend/` y añadirle eslint+tsc+build a CI. Si es `frontend/`, archivar `massive-ui-ng/`. En cualquier caso, eliminar el `.jsx` duplicado de 825 líneas.

**Esfuerzo:** L

---

**ID:** D3-006
**Severidad:** 🟠
**Dominio:** Arquitectura
**Título:** 31 módulos Python en la raíz del repositorio; `simulator.py` es un god-module de 2 457 líneas
**Ubicación:** root · `simulator.py`
**Estado:** **[CONFIRMADO]** · **[CONOCIDO PREVIO — "~30+ archivos Python sueltos en root"]**

**Evidencia.**
```
$ find . -maxdepth 1 -name "*.py" | wc -l → 31

Clasificación propuesta (destino modular):
  Núcleo de simulación → massive/core/engines/
    simulator.py (2457)  massive_engine.py (1232)  multilayer_engine.py (1025)
    micro_engine.py (1034)  energy_engine.py (624)
  Capa CfC → massive/cfc/
    cfc_engine.py (383)  cfc_router.py (467)  cfc_trainer.py (361)
    train_cfc_lambda.py  train_cfc_landscape.py  train_cfc_temp.py  (→ consolidar, D2-012)
  Servicios/orquestación → services/
    social_architect.py (706)  programmatic_architect.py  energy_runner.py
    document_intelligence.py (717)  interpreter_layer.py (585)  langchain_workflows.py
    visualizations.py  uil_adapter.py  social_connectors.py
  Infraestructura → massive_core/
    cache_manager.py  state_compression.py (shim)  llm_credentials.py (shim)
    empirical_config.py (shim)  empirical_calibration.py (shim)  schemas.py (shim)
    micro_schemas.py  energy_schemas.py
  HTTP → backend/  (api.py, deprecado)
  Scripts/benchmarks → scripts/ · benchmarks/
    benchmark_scalability.py (908)  brexit_calibration.py

$ wc -l simulator.py → 2457
$ grep -c "^def \|^class " simulator.py → 41 defs/clases top-level
  class CircuitBreaker (1195) · class IntegratedSimulator (2081)
  dicts de configuración a nivel de módulo: RANGOS_DISPONIBLES:116 · DEFAULT_CONFIG:198 · NOMBRES_REGLAS:1035
  + logging.basicConfig:102 (D1-008) + 4 bloques try/except de feature-flags (60-96)
```

**Impacto.** `simulator.py` mezcla: configuración, tabla de 13 reglas de dinámica, motor escalar, circuit breaker, simulador integrado, utilidades de historial, y side-effects de logging. Es el archivo con más cobertura faltante relevante (67 %, 274 sentencias sin cubrir) y el de mayor acoplamiento (5 módulos importan de él). Cada cambio obliga a releer 2 457 líneas.

**Acción sugerida.** Split por responsabilidad: `config.py` (RANGOS/DEFAULT_CONFIG/NOMBRES_REGLAS), `rules.py` (las 13 reglas), `engine.py` (`simular`, `run_with_schedule`), `history.py` (`resumen_historial`), `circuit_breaker.py`, `integrated.py`. Mantener `simulator.py` como fachada de re-export durante la transición.

**Esfuerzo:** XL

---

**ID:** D3-007
**Severidad:** 🟠
**Dominio:** Arquitectura
**Título:** 22 archivos Python superan las 500 líneas; 49 174 LOC totales
**Ubicación:** repo completo
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
 2457  simulator.py                       1232  massive_engine.py
 1226  massive/core/factbook/loader.py    1034  micro_engine.py
 1025  multilayer_engine.py                908  benchmark_scalability.py
  868  services/llm_orchestrator.py        794  massive/core/factbook/validator.py
  789  massive_core/numerics/multilayer_engine_sparse.py
  717  document_intelligence.py            706  social_architect.py
  657  experiments/real_validation/generate_real_cases.py
  654  massive/core/factbook/context.py    645  massive/core/empirical_config.py
  638  massive-ui-ng/backend/app/scenario_parser.py
  624  energy_engine.py                    598  massive_core/contracts.py
  585  interpreter_layer.py                565  massive-ui-ng/backend/app/routers/simulation.py
  549  benchmarks/runner.py                534  massive/core/factbook/mappings.py
  511  tests/test_massive_engine.py
Total: 245 archivos · 49 174 líneas · 1 783 def/async def
```

**Impacto.** Los 5 engines principales (simulator, massive_engine, micro_engine, multilayer_engine, energy_engine = 6 373 líneas) comparten la forma "un archivo = un motor completo", lo que impide compartir la infraestructura común (RNG, métricas, historial, circuit breaker) y genera las duplicaciones que detecta pylint.

**Acción sugerida.** Definir un umbral de 500 líneas en la guía de contribución y priorizar el split de los 5 engines + `llm_orchestrator.py`.

**Esfuerzo:** XL

---

**ID:** D3-008
**Severidad:** 🟠
**Dominio:** Arquitectura
**Título:** Tres paquetes `utils/` distintos bajo tres prefijos de paquete distintos
**Ubicación:** `massive/core/utils/` · `massive_core/utils/` · `micro_massive/utils/`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
massive/core/utils/__init__.py        (sin docstring)
massive/core/utils/serialize.py
massive_core/utils/rng.py             (23 stmts, 65 % cobertura, en el slice mypy estricto)
micro_massive/utils/__init__.py
micro_massive/utils/forer.py          (26 stmts, 83 %)
micro_massive/utils/metrics.py        (22 stmts, 93 %, sin docstring)
+ massive/core/utility_logic.py       (74 stmts, 37.7 % cobertura) — nombre ambiguo
```
Y simultáneamente existe `metrics/unified_metrics.py` como paquete top-level consumido por los 5 engines.

**Impacto.** Un desarrollador que necesita "el RNG" debe saber si está en `massive`, `massive_core` o `micro_massive`. `utility_logic.py` no declara en su nombre qué lógica de utilidad contiene. `micro_massive/utils/metrics.py` y `metrics/unified_metrics.py` hacen cosas solapadas.

**Acción sugerida.** Consolidar en `massive_core/utils/` (rng, serialize, metrics) y hacer que los otros re-exporten; renombrar `utility_logic.py` a algo descriptivo tras leer su contenido (funciones de utilidad para el motor de agentes).

**Esfuerzo:** M

---

**ID:** D3-009
**Severidad:** 🟠
**Dominio:** Arquitectura
**Título:** La capa de shims deprecados de root es inconsistente: 4 silenciosos, 1 con warning incondicional y docstring malformado, 1 ausente
**Ubicación:** root: `empirical_config.py`, `empirical_calibration.py`, `llm_credentials.py`, `state_compression.py`, `schemas.py` · faltante: `extended_models.py`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
empirical_config.py       → docstring "@deprecated — re-export only" + `from massive.core...`   (silencioso)
empirical_calibration.py  → ídem, 25 símbolos re-exportados + __all__                            (silencioso)
llm_credentials.py        → ídem, 4 símbolos                                                     (silencioso)
state_compression.py      → docstring `.. deprecated::` RST-style (convención distinta)          (silencioso)

schemas.py                → ANÓMALO:
   1  from __future__ import annotations      ← ANTES del docstring
   3  """⚠️ DEPRECATION NOTICE ... Canonical location: massive/core/schemas.py
       This file: Primary schema file - contains core DTOs"""    ← se contradice a sí mismo
  11  """@deprecated — re-export only..."""   ← SEGUNDO docstring (string literal muerto)
  15  warnings.warn("schemas.py is a deprecated re-export...", DeprecationWarning, stacklevel=2)
       ← warning INCONDICIONAL en cada import, sin filtro ni once=True

extended_models.py        → NO EXISTE (D1-003)
```
Ruff confirma: `E402 schemas.py:15 module level import not at top of file` (consecuencia del `from __future__` desplazado).
`massive/core/schemas.py` no tiene docstring de módulo (D6-011).

**Impacto.** El shim de `schemas.py` emite un `DeprecationWarning` en cada proceso que lo importe, ensuciando la salida de tests y de la API. Su docstring dice simultáneamente "canonical location: massive/core/schemas.py" y "This file: Primary schema file", lo que impide saber cuál es la verdad. Y la ausencia del shim de `extended_models` rompe funcionalidad científica en silencio.

**Acción sugerida.** Uniformar los 5 shims a un único patrón (docstring `.. deprecated::` + re-export + `warnings.warn(..., stacklevel=2)` protegido por un flag de env o `DeprecationWarning` filtrable), crear el shim de `extended_models` o corregir el import (D1-003), y corregir el docstring contradictorio de `schemas.py`.

**Esfuerzo:** S

---

**ID:** D3-010
**Severidad:** 🟡
**Dominio:** Arquitectura
**Título:** `massive/` vs `massive_core/`: la separación de responsabilidades existe pero está invertida respecto a la intuición del nombre
**Ubicación:** `massive/` (20 módulos) · `massive_core/` (30 módulos)
**Estado:** **[CONFIRMADO]** · **[CONOCIDO PREVIO]**

**Descripción.** Verificada la separación real:

| Paquete | Contenido real | Rol |
|---|---|---|
| `massive/` | `cli/` (main, __main__) + `core/` (empirical_config, empirical_calibration, extended_models, intervention_optimizer, llm_credentials, schemas, state_compression, utility_logic, factbook/{context,loader,mappings,validator}, utils/serialize) | **Es el paquete instalable** (`name = "massive"` en pyproject). Contiene el código *legacy* migrado desde root + el CLI |
| `massive_core/` | `config/` (api_auth, rate_limit, logging_setup, settings, scientific, defaults.yaml), `numerics/` (steppers, solvers, stability, multilayer_engine_sparse), `physics/`, `dynamical_systems/`, `data_assimilation/` (kalman, workflow), `diagnostics/`, `metalearning/`, `network_inference/`, `neural_physics/` (pinns), `multiscale/`, `contracts.py`, `rust_core.py`, `scientific_runner.py`, `utils/rng.py` | **Capa científica opt-in** + configuración transversal de la app |

**Evidencia.** `README.md:268-270` lo documenta correctamente: *"massive_core/ # Opt-in scientific layer"* · *"massive/ # CLI + core/factbook"* · *"massive/core/ # Legacy core modules"*.

**Impacto.** La nomenclatura es contraintuitiva: `massive_core` suena al núcleo del producto pero es la capa científica opcional, mientras que el "core" real vive en `massive/core/`. Un contribuyente nuevo importará del sitio equivocado. Además `massive_core/config/` contiene la configuración **de la app** (api_auth, rate_limit, settings) que nada tiene de científica — responsabilidad mal ubicada.

**Acción sugerida.** Mover `massive_core/config/` → `massive/config/` (es configuración de aplicación, no ciencia), y renombrar `massive_core/` → `massive/scientific/` en una migración por fases. Documentar la regla en `docs/architecture/domain_ownership.md` (que ya existe y es huérfano del nav, D6-009).

**Esfuerzo:** L

---

**ID:** D3-011
**Severidad:** 🟡
**Dominio:** Arquitectura
**Título:** Cada endpoint `/v1/*` está duplicado en `/api/v1/*` — 22 paths en OpenAPI para 13 operaciones
**Ubicación:** `backend/app/main.py` (registro de alias) · verificado en vivo vía `/openapi.json`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ curl -s localhost:8000/openapi.json | jq '.paths | keys'
22 paths:
  /v1/simulate /v1/forecast /v1/engine/energy /v1/engine/architect /v1/benchmarks
  /v1/llm/extract /v1/llm/wizard /v1/llm/run_simulation            (9 versionados)
  /api/v1/… × 8 (alias idénticos)  +  /api/v1/forecast
  /  /health  /ready  /version  /metrics  /openapi/v1.json          (6 infra)
```
`nginx.conf` lo reconoce: *"/api/v1/* is aliased to /v1/* in backend/app/main.py, so a single proxy location handles the full surface"* — pero mantiene dos bloques `location` separados con las mismas 4 directivas `proxy_set_header` duplicadas.

**Impacto.** Superficie de OpenAPI duplicada → los tipos generados, la documentación y los tests de contrato deben considerar dos rutas. Los contadores de métricas agrupan por `group`, así que la misma operación aparece bajo dos paths. No es un bug, pero es deuda de superficie.

**Acción sugerida.** Anunciar una fecha de retirada de `/api/v1/*`, añadir un header `Deprecation`/`Sunset` en las respuestas del alias, y registrar la duplicación en `docs/architecture/backward_compatibility_aliases.md` (que ya existe y es huérfano).

**Esfuerzo:** S

---

**ID:** D3-012
**Severidad:** 🟡
**Dominio:** Arquitectura
**Título:** `micro_engine.py` (root, 1 034 líneas) y `micro_massive/` (9 módulos) son dos implementaciones micro paralelas
**Ubicación:** `micro_engine.py` · `micro_massive/{core/{agent,game,influence,orchestrator},utils/{forer,metrics}}` · `micro_schemas.py`
**Estado:** **[CONFIRMADO]** · **[CONOCIDO PREVIO]**

**Evidencia.**
```
micro_engine.py                  411 stmts · 89 % cobertura · importa metrics.unified_metrics
micro_massive/core/agent.py       —  · micro_massive/core/game.py       31 stmts · 87 %
micro_massive/core/influence.py   32 stmts · 90 %
micro_massive/core/orchestrator.py 50 stmts · 83 %
micro_massive/utils/forer.py      26 stmts · 83 %   (Fisher-Of-Return?)
micro_massive/utils/metrics.py    22 stmts · 93 %   ← solapa con metrics/unified_metrics.py
micro_schemas.py                  58 stmts · 97 %   ← en root, no en micro_massive/
Consumido por: tests/test_micro.py, tests/test_micro_engine_coverage.py
Vulture: micro_massive/core/influence.py:33 `reinforce` sin usar; micro_massive/core/game.py:36 `n_payoff` sin usar
```

**Impacto.** Dos modelos "micro" con métricas propias. `micro_schemas.py` (los DTOs) está en root mientras el paquete que los describe está en `micro_massive/`. El README no menciona `micro_massive/` en el árbol de layout.

**Acción sugerida.** Mover `micro_schemas.py` → `micro_massive/schemas.py`; documentar la relación entre `micro_engine.py` (motor monolítico) y `micro_massive/` (descomposición por agentes) en `docs/architecture/domain_ownership.md`; fusionar las dos implementaciones de métricas.

**Esfuerzo:** M

---

**ID:** D3-013
**Severidad:** 🟡
**Dominio:** Arquitectura
**Título:** El console script publicado (`massive-cli`) tiene 0 % de cobertura y 0 tests
**Ubicación:** `pyproject.toml:56` · `massive/cli/main.py` (99 stmts) · `massive/cli/__main__.py`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
pyproject.toml:  [project.scripts]  massive-cli = "massive.cli.main:main"
coverage.json:   massive/cli/main.py       99 stmts   0.0 %
                 massive/cli/__init__.py    3 stmts   0.0 %
                 massive/cli/__main__.py    3 stmts   0.0 %
$ grep -rln "massive.cli\|massive-cli" tests/   → (vacío)
```
El README lo documenta como vía de uso principal: *"Or use the CLI, no server needed"*.

**Impacto.** La interfaz de usuario más simple del producto —la que no requiere levantar servidor— es la única superficie pública completamente sin probar. Cualquier regresión en el parseo de argumentos llega a PyPI sin detección.

**Acción sugerida.** Añadir `tests/test_cli.py` con `subprocess`/`CliRunner` cubriendo: `--help`, una simulación mínima, salida JSON, códigos de error.

**Esfuerzo:** S

---

**ID:** D3-014
**Severidad:** 🟡
**Dominio:** Arquitectura
**Título:** `monitoring/` está referenciado por el README pero no conectado a nada
**Ubicación:** `monitoring/prometheus/alerts.yml` · `monitoring/grafana/dashboard.json`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ grep -rn "prometheus|grafana" docker-compose.yml docker-compose.single.yml \
      massive-ui-ng/infra/docker-compose.yml supervisord.conf
(vacío — ningún servicio de Prometheus ni Grafana en ningún compose ni en supervisord)

$ grep -rn "prometheus_client" --include="*.py" .
backend/app/metrics.py:3  "Deliberately dependency-free (no prometheus_client): a tiny thread-safe…"
→ las métricas se emiten en texto Prometheus propio, pero nada las scrapea

Referencias documentales:
README.md:287  "├── monitoring/  # Prometheus alert rules + Grafana dashboard spec"
MASSIVE_REACTIVE_COHERENCE_PLAN.md:429-430  "✅ Created — 5 alert rules / 6 panels"
RESTART_CHECKLIST.md:211
```

**Impacto.** Observabilidad declarada pero inoperante: 5 reglas de alerta y 6 paneles que ningún despliegue del repo instancia. Da falsa confianza en el posture de producción que el README promociona.

**Acción sugerida.** Añadir un `docker-compose.observability.yml` opcional con prometheus+grafana montando `monitoring/`, o marcar explícitamente el directorio como "reference-only, bring your own stack" en el README.

**Esfuerzo:** S

---

**ID:** D3-015
**Severidad:** 🟢
**Dominio:** Arquitectura
**Título:** `adapters/mutalambda/` está bien diseñado: thin, sin dependencia dura, con manifiesto declarativo
**Ubicación:** `adapters/mutalambda/{__init__.py, massive_target.py, target_manifest.yaml}`
**Estado:** **[CONFIRMADO — POSITIVO]** · **[CONOCIDO PREVIO — punto 3.7]**

**Descripción.** Responde a las tres preguntas del brief:
- **¿Completo?** Sí para su alcance declarado: `MassiveTargetManifest` (dataclass con `to_dict()`), `evaluate_massive_vector()`, `make_objective()`, `resolve_target`.
- **¿Documentado?** Sí: docstring de módulo explícito (*"thin, stable interface … does not pull MutaLambda as a hard dependency"*) + `target_manifest.yaml` con `name`, `version`, `decision_dim: 8`, `bounds` por dimensión, y dos targets (`polarization_index`, `opinion_mean`) con `range`/`unit`/`semantics`/`source`.
- **¿Testado?** Sí: `tests/test_workflow_closeout.py` (9 tests) lo ejercita.
- **¿Importa módulos inexistentes de MutaLambda?** **No importa MutaLambda en absoluto** — sólo `numpy` y `forecast.targets`. La inversión de dependencia es correcta.

**Evidencia.** `grep -rn "^from |^import " adapters/mutalambda/*.py` → `collections.abc`, `dataclasses`, `typing`, `numpy`, `forecast.targets`, `adapters.mutalambda.massive_target`. Cobertura: los 9 tests de `test_workflow_closeout.py` pasan.

**Impacto.** Positivo. Es el único adapter del repo y es un buen ejemplo del patrón.

**Acción sugerida.** Ninguna en el adapter. Sí: `progress.md` lista *"MutaLambda nested `tests/` / `benchmarks/` layout"* como pendiente del owner — verificar si el repo externo espera una disposición distinta.

**Esfuerzo:** —

---

**ID:** D3-016
**Severidad:** 🟡
**Dominio:** Arquitectura
**Título:** La cadena de imports del adapter es frágil: `adapters → forecast → simulator → cfc_router`
**Ubicación:** `adapters/mutalambda/massive_target.py:15` → `forecast/__init__.py:3` → `forecast/engine.py:14` → `simulator.py:85`
**Estado:** **[CONFIRMADO]**

**Evidencia.** Traceback real de pytest:
```
tests/test_workflow_closeout.py:7: in <module>
    from adapters.mutalambda.massive_target import (
adapters/mutalambda/__init__.py:3: in <module>
    from adapters.mutalambda.massive_target import (
adapters/mutalambda/massive_target.py:15: in <module>
    from forecast.targets import POLARIZATION_INDEX, TargetDefinition, resolve_target
forecast/__init__.py:3: in <module>
    from .engine import ForecastResult, forecast
forecast/engine.py:14: in <module>
    from simulator import DEFAULT_CONFIG
simulator.py:85: in <module>
    CFC_AVAILABLE = _cfc.status["regime_selector"]   ← BOOM (D1-001)
```
Cuatro saltos para llegar a un fallo. `forecast/__init__.py` importa `.engine` eagerly, y `engine` importa `simulator` en cabeza de módulo.

**Impacto.** Cualquier módulo que toque `forecast.targets` (un módulo puro de definiciones) arrastra todo el motor de simulación + CfC. Esto convierte un fallo de un componente opcional en un fallo de todo el adapter. Es el mecanismo por el que D1-001 se propagó a 25 módulos.

**Acción sugerida.** Hacer `forecast/__init__.py` perezoso (`__getattr__` de módulo, PEP 562); mover `DEFAULT_CONFIG` a un módulo de configuración sin dependencias (`massive_core/config/`) y que tanto `simulator` como `forecast.engine` importen de ahí.

**Esfuerzo:** M

---

**ID:** D3-017
**Severidad:** 🟡
**Dominio:** Arquitectura
**Título:** Dos `Cargo.toml` contradictorios para el mismo crate; el de `rust_core/` es huérfano y referencia un crate inexistente
**Ubicación:** `Cargo.toml` (root) · `rust_core/Cargo.toml` · `Cargo.lock`
**Estado:** **[CONFIRMADO]** · **[HIPÓTESIS]** en la parte de `cargo check` (sin toolchain Rust en el sandbox)

**Evidencia.**
```
$ diff Cargo.toml rust_core/Cargo.toml
8,9c8
< crate-type = ["cdylib", "rlib"]
< path = "rust_core/src/lib.rs"
---
> crate-type = ["cdylib"]
12,14c11,14
< ndarray = "0.17"
< numpy   = "0.28"
< pyo3    = { version = "0.28", features = ["extension-module"] }
---
> pyo3        = { version = "0.22", features = ["extension-module", "abi3-py38"] }
> pyo3-ndarray = "0.22"          ← este crate no existe en crates.io
> ndarray     = "0.15"
> numpy       = "0.22"

Ambos declaran: name = "massive-rust-core", version = "0.1.0", edition = "2021"

$ cat Cargo.lock | grep -A4 'name = "massive-rust-core"'
dependencies = ["ndarray", "numpy", "pyo3"]     ← sin pyo3-ndarray
pyo3    = "0.28.3"   ndarray = "0.17.2"   numpy = "0.28.0"
→ Cargo.lock resuelve contra el Cargo.toml ROOT. rust_core/Cargo.toml nunca se usó.
```
`pyproject.toml` confirma: `[tool.maturin] module-name = "massive_rust_core"` — maturin usa el manifiesto root.

**Impacto.** `rust_core/Cargo.toml` es un archivo muerto que además **no resolvería** si alguien intentara usarlo (`pyo3-ndarray` no está publicado). Peor: `README_ES.md:14` enlaza su badge de Rust a `Cargo.toml` y `README.md:14` a `rust_core/`, así que un lector puede acabar en el manifiesto equivocado. Un desarrollador Rust que haga `cd rust_core && cargo build` obtendrá un error de resolución confuso.

**Acción sugerida.** Eliminar `rust_core/Cargo.toml` (el root ya declara `path = "rust_core/src/lib.rs"`), o convertirlo en un workspace member real. Verificar `cargo check && cargo test` en un entorno con Rust.

**Esfuerzo:** XS

---

**ID:** D3-018
**Severidad:** 🟠
**Dominio:** Arquitectura
**Título:** El núcleo Rust nunca se compila ni se testea en ningún entorno automatizado — es código muerto en la práctica
**Ubicación:** `rust_core/src/lib.rs` (162 líneas) · `.github/workflows/*` · `Dockerfile*` · `Makefile`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ grep -rniE "cargo|rust|maturin" .github/ Dockerfile Dockerfile.optimized Makefile install.sh
.github/CI_CD_BEST_PRACTICES.md:42:  …only match on the word "rust" inside "Trust" (id-token: write, OIDC trust)
→ 0 jobs de CI con Rust. 0 Dockerfile que instale rustc/cargo. 0 target de Makefile.

massive_core/rust_core.py:15:
  RUST_CORE_AVAILABLE: Final[bool] = importlib.util.find_spec("massive_rust_core") is not None
→ En CI, en Docker y en cualquier `pip install -r requirements.txt`, esto es SIEMPRE False.

coverage.json: massive_core/rust_core.py 81 % — el 19 % sin cubrir son exactamente las ramas `if _rust_core is not None`.
tests/test_rust_core_wrapper.py: 3 tests, todos sobre el fallback NumPy.
```
Además `pip install -e .` es imposible sin Rust (D5-002), así que ni siquiera un desarrollador motivado puede activar la ruta Rust sin instalar el toolchain manualmente —y nada documenta cómo.

**Impacto.** 162 líneas de Rust mantenidas, versionadas y con `Cargo.lock`, que jamás se ejecutan. Las dos implementaciones (Rust y NumPy) pueden divergir sin que ningún test lo detecte: no existe test de paridad. El README lo declara honestamente (*"a conceptual PoC, not yet a significant speedup"*), lo cual mitiga el riesgo de comunicación pero no el de mantenimiento.

**Acción sugerida.** Añadir un job `rust` a CI (`dtolnay/rust-toolchain` + `cargo fmt --check` + `cargo clippy -D warnings` + `cargo test` + `maturin develop` + test de paridad Rust↔NumPy), o archivar `rust_core/` en una rama hasta que se justifique.

**Esfuerzo:** M

---

**ID:** D3-019
**Severidad:** 🟡
**Dominio:** Arquitectura
**Título:** `scripts/gen_ts_types.py` no tiene interfaz CLI: `--dry-run` y `--stdout` se ignoran en silencio y el script escribe el archivo
**Ubicación:** `scripts/gen_ts_types.py` (6 535 bytes, 184-215)
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ grep -n "argparse|sys.argv|dry|stdout" scripts/gen_ts_types.py
(vacío — solo `import sys` para sys.path)

$ python scripts/gen_ts_types.py --dry-run
✓  Generated frontend/src/types/api.generated.ts        ← ESCRIBIÓ el archivo
$ python scripts/gen_ts_types.py --stdout > /tmp/gen.ts
✓  Generated frontend/src/types/api.generated.ts        ← imprimió el mensaje, no el contenido
$ head -1 /tmp/gen.ts
✓  Generated frontend/src/types/api.generated.ts        ← stdout capturó el log, no los tipos
```
`main()` termina con `_OUT.write_text(content, encoding="utf-8")` incondicional.
Existe además un fork roto en `massive-ui-ng/infra/scripts/gen_ts_types.py` (D3-003) cuyo `_schema_to_ts` tiene la misma complejidad D(22).

**Impacto.** El punto 3.5 del brief es inejecutable tal como está escrito. Peor: un usuario que siga la documentación y ejecute `--dry-run` para *inspeccionar* modifica su working tree — y si lo commitea, `validate_ts_types.yml` falla de forma inexplicable.

**Acción sugerida.** Añadir `argparse` con `--dry-run` (compara y reporta sin escribir, exit 1 si hay diff), `--stdout` (imprime el contenido), `--out PATH` y `--check` (modo CI). Eliminar el fork de `massive-ui-ng/infra/`.

**Esfuerzo:** S

---

**ID:** D3-020
**Severidad:** 🟢
**Dominio:** Arquitectura
**Título:** Los tipos TypeScript de `frontend/` están efectivamente sincronizados con los DTOs Pydantic
**Ubicación:** `frontend/src/types/api.generated.ts` (201 líneas) · `backend/app/models/`
**Estado:** **[CONFIRMADO — POSITIVO]**

**Evidencia.** Tras ejecutar el generador (que escribe incondicionalmente, D3-019):
```
$ git status --porcelain
(vacío — el archivo regenerado es byte-idéntico al commiteado)
```
`validate_ts_types.yml` está correctamente diseñado (`git diff --exit-code` tras regenerar).

**Impacto.** Positivo: el contrato Pydantic→TS funciona. La pena es que el backend no valide contra esos DTOs en runtime (D3-004), así que el contrato se cumple en el papel y no en la ejecución.

**Acción sugerida.** Ninguna sobre la sincronía. Priorizar D3-004 para que el contrato tenga efecto real.

**Esfuerzo:** —

---

### DOMINIO 4 — TESTS Y COBERTURA

---

**ID:** D4-001
**Severidad:** 🔴
**Dominio:** Tests
**Título:** 12 de 681 tests fallan en un clone limpio: requieren pesos `.pt` que no están en el repositorio
**Ubicación:** `tests/test_cfc_lambda_integration.py` (4) · `tests/test_cfc_landscape_integration.py` (7) · `tests/test_brexit_calibration.py` (1)
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ python -m pytest tests/ -q          # con torch instalado, entorno completo
669 passed, 12 failed  (681 recolectados)

FAILED tests/test_brexit_calibration.py::TestBrexitCalibration::test_both_models_loaded
    assert status["lambda_corrector"] is True   →  E assert False is True
FAILED tests/test_cfc_lambda_integration.py::TestLambdaCorrectorModel::test_loads_from_trained_weights
    ckpt = torch.load(...)  → FileNotFoundError
FAILED tests/test_cfc_lambda_integration.py::TestRouterLambdaIntegration::{test_lambda_corrector_loaded,
       test_reactive_different_inputs, test_reactive_high_gini_reduces_coupling}
FAILED tests/test_cfc_landscape_integration.py::TestCfCLandscapeModulator::{test_model_file_exists,
       test_model_loads_in_router, test_propose_landscape_returns_valid_params, test_landscape_output_ranges,
       test_engine_loads_landscape_model, test_engine_propose_landscape, test_router_status_includes_landscape}

Archivos que SÍ están:            Archivos que los tests esperan y NO están:
models/cfc_calibrated/            models/cfc_calibrated/cfc_lambda_corrector.pt   ✗
  cfc_residual.pt          ✓      models/cfc_calibrated/cfc_landscape.pt          ✗
  cfc_lambda_config.json   ✓      models/cfc_calibrated/cfc_temperature.pt        ✗
  cfc_lambda_training_log.json ✓
  cfc_landscape_config.json ✓     (los CONFIG y los TRAINING LOG de los modelos
  cfc_landscape_training_log.json ✓  ausentes SÍ están commiteados)
  checkpoints/checkpoint_ep{25..200}.pt ✓ (8 archivos, 396 KB)
```
Referenciados además en `MASSIVE_REACTIVE_COHERENCE_PLAN.md` (2× cada uno) como artefactos esperados.

**Impacto.** `pytest tests/` nunca está verde en un clone limpio. Esto bloquea `publish.yml:job test` → y por `needs`, toda la cadena de publicación. Y es una trampa de diseño: los **logs y configs de entrenamiento están versionados pero los pesos no**, así que el repo afirma tener modelos calibrados que no puede cargar. El README publicita *"~50 % error reduction on the Brexit 2016 referendum case (validated on 10/10 seeds)"* — esa afirmación depende de `cfc_lambda_corrector.pt`, que no está.

**Acción sugerida.** Elegir una de tres: (a) publicar los 3 `.pt` vía Git LFS (el `.gitignore` ya comenta *"Git LFS recommended"* y `deploy_hf_spaces.yml` hace checkout con `lfs: true`); (b) convertir esos 12 tests en `pytest.mark.skipif(not path.exists())` con un fixture de descarga; (c) regenerar los pesos en CI con `train_cfc_lambda.py`/`train_cfc_landscape.py` (que hoy tienen 0 % de cobertura). La opción (a) es la única que sostiene la afirmación del README.

**Esfuerzo:** M

---

**ID:** D4-002
**Severidad:** 🟠
**Dominio:** Tests
**Título:** Cobertura real 59.62 % branch; el README declara 68 %; el gate de CI está en 30 %
**Ubicación:** `pyproject.toml:82` (`fail_under = 30`) · `README.md:245` · `README_ES.md:221`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ python -m pytest tests/ --cov=. --cov-report=json:coverage.json -q
TOTAL  11493 stmts · 4361 miss · 2874 branches · 457 partial → 60 %
Required test coverage of 30.0 % reached. Total coverage: 59.62 %
144 archivos medidos · 45 con cobertura completa

README.md:245    | Coverage | 68 % branch (scope: engines + services + backend) |
README_ES.md:221 | (declaración análoga) |
pyproject.toml:82  fail_under = 30
progress.md:       "Coverage hard gate 30 % in CI once baseline is stable on 3.11 runners"
```

**Impacto.** Triple problema: (a) la cifra pública está sobreestimada en ~8 puntos; (b) el gate de 30 % está 29.6 puntos por debajo de la realidad, así que **no puede detectar ninguna regresión** — se podría borrar un tercio del test suite y CI seguiría verde; (c) el `--cov` de CI en `pytest.yml` enumera 12 targets explícitos mientras `[tool.coverage.run] source` en pyproject enumera otros — dos definiciones de scope que pueden divergir.

**Acción sugerida.** Corregir la cifra del README a la medida; subir `fail_under` a 55 con ratchet (subir 2 puntos por release); unificar el scope de cobertura en un solo sitio (`[tool.coverage.run]`) y que CI use `--cov` sin argumentos.

**Esfuerzo:** S

---

**ID:** D4-003
**Severidad:** 🟠
**Dominio:** Tests
**Título:** 16 archivos con 0 % de cobertura (1 734 sentencias), incluido el CLI publicado y modelos científicos completos
**Ubicación:** ver tabla
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
  0.0 %  483 stmts  benchmark_scalability.py            ← la evidencia de las cifras del README (D9-005)
  0.0 %  205 stmts  massive/core/extended_models.py     ← Bayes/Nash/SIR (D1-003)
  0.0 %  168 stmts  train_cfc_landscape.py              ← clon (D2-012)
  0.0 %  164 stmts  train_cfc_temp.py                   ← clon
  0.0 %  153 stmts  train_cfc_lambda.py                 ← clon
  0.0 %  135 stmts  cfc_trainer.py                      ← el trainer "canónico"
  0.0 %   99 stmts  massive/cli/main.py                 ← console_script publicado (D3-013)
  0.0 %   91 stmts  langchain_workflows.py
  0.0 %   90 stmts  benchmarks/massive_real.py
  0.0 %   85 stmts  social_connectors.py                ← Twitter/Reddit (D2-013)
  0.0 %   25 stmts  benchmarks/bench_perf_f.py
  0.0 %   25 stmts  massive_core/neural_physics/pinns.py ← PINNs (requiere torch, sin fallback)
  0.0 %    3 stmts  massive/cli/__init__.py
  0.0 %    3 stmts  massive/cli/__main__.py
  0.0 %    2 stmts  massive_core/analysis/__init__.py
  0.0 %    2 stmts  massive_core/neural_physics/__init__.py
```

**Impacto.** Cuatro categorías de riesgo: (1) el entrypoint publicado sin probar; (2) el pipeline completo de entrenamiento CfC (655 stmts entre `cfc_trainer.py` y los 3 `train_cfc_*.py`) sin probar — y son los que deberían regenerar los pesos que faltan en D4-001; (3) la evidencia de escalabilidad del README sin probar; (4) `massive_core/neural_physics/pinns.py` importa `torch` en cabeza de módulo sin fallback (único módulo del repo que lo hace).

**Acción sugerida.** Prioridad: CLI (S) → `cfc_trainer.py` con un test de 1 época sobre datos sintéticos (M) → `extended_models.py` tras arreglar D1-003 (S) → `benchmark_scalability.py` con un test de smoke en configuración mini (M).

**Esfuerzo:** L (total) · desglosado en el workflow

---

**ID:** D4-004
**Severidad:** 🟠
**Dominio:** Tests
**Título:** 16 archivos por debajo del 50 %; `social_architect.py` al 14.4 % es la superficie de producto menos cubierta
**Ubicación:** ver tabla
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
 14.4 %  254 stmts  social_architect.py          ← "Inverse intervention design", feature destacada del README
 15.1 %   39 stmts  backend/app/routers/benchmark.py
 20.7 %  191 stmts  massive_core/network_inference/reconstruct.py   ← O(N²), flagged en REPORT_OPTIMIZATION
 23.1 %   33 stmts  backend/app/routers/forecast.py
 24.4 %   72 stmts  uil_adapter.py
 26.5 %   26 stmts  backend/app/routers/engine.py ← donde falta el clamp de max_intentos (D5-001)
 32.2 %  217 stmts  api.py
 33.0 %  166 stmts  massive_core/physics/perturbation_theory.py
 36.1 %  177 stmts  interpreter_layer.py
 36.5 %  304 stmts  document_intelligence.py
 37.7 %   74 stmts  massive/core/utility_logic.py
 39.4 %   85 stmts  backend/app/routers/llm.py    ← donde mypy ve `LLMLlmHint.api_key` inexistente (D2-003)
 41.4 %   42 stmts  massive_core/physics/hydrodynamics.py
 43.3 %   22 stmts  services/llm_service.py
 45.6 %   95 stmts  programmatic_architect.py
 46.0 %   ...       (massive_core/physics/statistical_mechanics.py 57 %)
```
Nota: 4 de los 5 routers del backend canónico están por debajo del 40 %.

**Impacto.** La capa HTTP canónica —la que sirve tráfico real— está entre las menos cubiertas del proyecto, y es justo donde viven los hallazgos de seguridad D5-001 y los errores de tipo con riesgo runtime D2-003. `social_architect.py` es una de las 7 capacidades que el README vende en su tabla "frontier".

**Acción sugerida.** Tests de contrato por router (payload válido → 200 con esquema; payload inválido → 422; sin key → 401; límite excedido → 429/413) usando `TestClient` + DTOs (se resuelve junto con D3-004).

**Esfuerzo:** M

---

**ID:** D4-005
**Severidad:** 🟠
**Dominio:** Tests
**Título:** 140 de 666 funciones de test (21 %) no contienen ninguna aserción
**Ubicación:** `tests/` · concentración en `test_cfc_engine.py`, `test_cfc_router.py`
**Estado:** **[CONFIRMADO]**

**Evidencia.** Análisis AST sobre las 666 funciones `test_*`:
```
test functions: 666
sin ast.Assert y sin pytest.raises/fail/warns: 140  (21.0 %)

Ejemplos (nombre → lo que realmente hace):
 tests/test_cfc_engine.py:16  test_import_no_crash_without_torch   ← ver D4-009, no puede pasar sin torch
 tests/test_cfc_engine.py:51  test_output_shape      (solo llama al forward)
 tests/test_cfc_engine.py:59  test_no_nan_output     (no comprueba NaN)
 tests/test_cfc_engine.py:76  test_tau_always_positive (no comprueba signo)
 tests/test_cfc_router.py:50  test_status_all_false  ← SÍ aserta, pero con unittest (self.assertFalse)
 tests/test_cfc_router.py:73  test_singleton_identity

assert True / assert 1 / `is not None` sin más: 32 ocurrencias
```
Nota metodológica: el contador AST subestima ligeramente porque `self.assertEqual` (unittest) es una `Call`, no un `Assert` — de los 140, una parte sí aserta vía unittest. Aun descontando eso, `test_output_shape`/`test_no_nan_output`/`test_tau_always_positive` en `test_cfc_engine.py` **sí** usan `self.assertEqual`/`self.assertFalse`, por lo que el hallazgo cualitativo se sostiene: hay tests cuyo *nombre promete una propiedad* (no-NaN, τ positivo, forma correcta) cuya verificación depende de que la clase padre unittest aserte — y en los casos listados la aserción existe pero está en la rama que sólo corre con torch.

**Impacto.** Tests que pasan por no lanzar excepción, no por verificar comportamiento. En un simulador científico esto es especialmente peligroso: un motor que devuelve NaN en cada paso pasa un test de "no crash".

**Acción sugerida.** Regla de contribución: todo `test_*` debe contener ≥1 assert explícito sobre una propiedad. Añadir `PT009`→migrar a asserts de pytest y habilitar una regla custom o revisión por pares. Empezar por los 3 archivos CfC.

**Esfuerzo:** M

---

**ID:** D4-006
**Severidad:** 🟠
**Dominio:** Tests
**Título:** 3 archivos de test no pueden recolectarse sin `httpx`, que no está declarado en `requirements.txt`
**Ubicación:** `tests/test_api_security.py` · `tests/test_backend_observability.py` · `tests/test_llm_endpoint.py` · `requirements.txt`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ python -m pytest tests/ --collect-only      # sin httpx
ERROR tests/test_api_security.py        - RuntimeError: The starlette.testclient module requires httpx
ERROR tests/test_backend_observability.py - RuntimeError: The starlette.testclient module requires httpx
ERROR tests/test_llm_endpoint.py        - RuntimeError: The starlette.testclient module requires httpx

$ grep -n httpx requirements.txt pyproject.toml
(vacío en ambos)

Sí lo instala ad-hoc el job `api` de pytest.yml:
  pip install fastapi "uvicorn[standard]" python-multipart pydantic pytest httpx numpy scipy
Y el workflow muerto de ui-ng:  pip install httpx
```

**Impacto.** `make test` y `install.sh test` fallan en la colección de 3 archivos para cualquiera que siga el README (`pip install -r requirements.txt`). Los tests de seguridad de la API (`test_api_security.py`, que según `massive_core/config/api_auth.py` *"enforced by tests/test_api_security.py parity tests"*) son precisamente los que no se pueden ejecutar.

**Acción sugerida.** Añadir `httpx>=0.27` al extra `dev` de `pyproject.toml` y a `requirements.txt` (o a un `requirements-dev.txt`).

**Esfuerzo:** XS

---

**ID:** D4-007
**Severidad:** 🟡
**Dominio:** Tests
**Título:** Un segundo directorio de tests (`massive-ui-ng/tests/`) queda fuera de `testpaths` y nunca se ejecuta
**Ubicación:** `pyproject.toml:57` (`testpaths = ["tests"]`) · `massive-ui-ng/tests/{test_ui_ng.py, test_ui_ng_live.py}` · `massive-ui-ng/conftest.py`
**Estado:** **[CONFIRMADO]** · punto 4.3 del brief

**Evidencia.**
```
$ find . -type d -name "tests" -not -path "./.git/*" -not -path "*/node_modules/*"
./massive-ui-ng/tests      (2 archivos)
./tests                    (59 archivos)

$ find . -name "conftest.py" …
./massive-ui-ng/conftest.py     ← único conftest del repo; NO hay conftest en tests/ ni en root

El único workflow que los ejecutaría está muerto (D7-007) y además invoca mal la ruta:
massive-ui-ng/infra/.github/workflows/ui-ng.yml:37
  python -m pytest tests/test_ui_ng.py tests/test_ui_ng_live.py -q
  ← resuelto desde la raíz del repo, donde esos archivos no existen
```

**Impacto.** Dos archivos de test (con 3 handlers silenciados cada uno en `test_ui_ng_live.py:85,122,144`) no aportan señal. Y la ausencia de un `tests/conftest.py` raíz obliga a confiar en la inserción de `rootdir` en `sys.path` de pytest, que es frágil.

**Acción sugerida.** Crear `tests/conftest.py` con el setup de `sys.path` explícito; mover `massive-ui-ng/tests/` a `tests/ui_ng/` o ampliar `testpaths`.

**Esfuerzo:** S

---

**ID:** D4-008
**Severidad:** 🟡
**Dominio:** Tests
**Título:** No existe `conftest.py` en la raíz ni en `tests/`
**Ubicación:** repo completo
**Estado:** **[CONFIRMADO]**

**Descripción.** 59 archivos de test dependen de que pytest añada el rootdir a `sys.path` (comportamiento por defecto con `rootdir` detectado vía `pyproject.toml`). No hay fixtures compartidas, no hay setup de entorno (p. ej. `MASSIVE_ENV`), no hay reset del singleton `CfCRouter._instance` entre tests.

**Evidencia.** El único `conftest.py` está en `massive-ui-ng/`. Los tests que necesitan resetear el singleton lo hacen ad-hoc: `tests/test_cfc_lambda_integration.py:18 def reset_router` (marcado como *unused function* por vulture, porque es una fixture sin decorador `@pytest.fixture`).

**Impacto.** Estado compartido entre tests vía el singleton `CfCRouter._instance` y vía `logging.basicConfig` (D2-009). El orden de ejecución puede alterar resultados; hoy no se detecta porque no hay `pytest-randomly` instalado (y `addopts = "-q -p no:libtmux"` desactiva un plugin que nadie declaró como dependencia).

**Acción sugerida.** Crear `tests/conftest.py` con: fixture autouse que resetee `CfCRouter._instance`, fixture que aisle `MASSIVE_ENV`, y `sys.path` explícito. Eliminar `-p no:libtmux` de `addopts` (o declarar `libtmux` como dev-dep si de verdad se necesita).

**Esfuerzo:** S

---

**ID:** D4-009
**Severidad:** 🟡
**Dominio:** Tests
**Título:** El test diseñado para cubrir el camino sin torch no puede pasar en un entorno sin torch
**Ubicación:** `tests/test_cfc_engine.py:14-28`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```python
class TestCfCEngineImport(unittest.TestCase):
    """Verifica que la importación de cfc_engine falla limpiamente sin torch."""
    def test_import_no_crash_without_torch(self):
        """cfc_engine importa si torch está instalado, y falla con ImportError si no."""
        try:
            import torch  # noqa: F401
            import cfc_engine
            self.assertTrue(hasattr(cfc_engine, "CfCCell"))
            ...
        except ImportError:
            pass  # Aceptable si torch no está instalado
```
Sin torch, `import cfc_engine` lanza **`AttributeError`** (D1-002), no `ImportError` → el `except` no lo captura → el test **falla**. Con torch, la rama `except` es código muerto. Es decir: el test nunca ejercita lo que su nombre y su docstring prometen.

**Impacto.** Es exactamente el test que debería haber detectado D1-001 y D1-002. Su existencia crea la falsa sensación de que el camino sin torch está cubierto.

**Acción sugerida.** Reescribirlo como test de subprocess con un `sitecustomize`/`PYTHONPATH` que bloquee `torch`, y afirmar que `import simulator` y `import cfc_engine` terminan con código 0.

**Esfuerzo:** S

---

**ID:** D4-010
**Severidad:** 🟡
**Dominio:** Tests
**Título:** `tests/test_cfc_router.py` produce 4 fallos en entorno sin torch, incluido `test_simular_works_without_cfc_models`
**Ubicación:** `tests/test_cfc_router.py`
**Estado:** **[CONFIRMADO]**

**Evidencia.** Ejecución con `torch` bloqueado vía `PYTHONPATH`:
```
$ PYTHONPATH=/tmp/notorch python -m pytest tests/test_cfc_engine.py tests/test_cfc_router.py -q --tb=line
.sssssssssssssss....F.sssssFFF                                    [100 %]
FAILED tests/test_cfc_router.py::TestCfCRouterFallback::test_status_all_false
FAILED tests/test_cfc_router.py::TestCfCSimulatorIntegration::test_cfc_available_is_boolean
FAILED tests/test_cfc_router.py::TestCfCSimulatorIntegration::test_cfc_fast_path_does_not_change_output_format
FAILED tests/test_cfc_router.py::TestCfCSimulatorIntegration::test_simular_works_without_cfc_models
E  AttributeError: 'CfCRouter' object has no attribute '_lambda_corrector'   (cfc_router.py:452)
```
Nótese que `TestCfCRouterFallback` **no** está decorada con `skip_no_torch` (a diferencia de las demás clases del archivo) — es la clase que precisamente prueba el fallback.

**Impacto.** Los 4 tests que verifican el contrato "CfC nunca bloquea" son los 4 que fallan cuando CfC realmente no puede cargar. La suite sólo está verde en la configuración que no ejercita el contrato.

**Acción sugerida.** Añadir una matriz de CI con y sin torch; quitar el `skip_no_torch` implícito de `TestCfCRouterFallback`; usar estos 4 tests como criterio de aceptación de la corrección de D1-001.

**Esfuerzo:** S

---

**ID:** D4-011
**Severidad:** 🟡
**Dominio:** Tests
**Título:** El benchmark PVU canónico termina en 0 pero emite `ConvergenceWarning` de statsmodels en los casos publicados
**Ubicación:** `benchmarks/runner.py` · `datasets/pvu_cases/sample_case_{001,002}` · `.github/workflows/pvu-validation.yml`
**Estado:** **[CONFIRMADO]** · punto 4.5 del brief

**Evidencia.**
```
$ PYTHONHASHSEED=42 python -m benchmarks.runner --cases datasets/pvu_cases --offline --out /tmp/pvu_out --seed 42
[TDA] ripser/persim no instalados — detección topológica desactivada.
INFO PVU-BS runner | mode=offline | seed=42 | cases=datasets/pvu_cases
INFO Loaded 2 case(s).
INFO Evaluating case: sample_case_001
site-packages/statsmodels/tsa/statespace/mlemodel.py:737: ConvergenceWarning:
   Maximum Likelihood optimization failed to converge. Check mle_retvals
INFO Evaluating case: sample_case_002
INFO Done. 2 case(s) evaluated, 0 skipped.
EXIT=0
```
El mismo warning aparece en la corrida completa de pytest.

**Impacto.** El baseline ARIMA/ETS no converge con las series de los casos publicados. El runner devuelve 0 igualmente, así que CI reporta "PVU OK" con un baseline numéricamente inválido. Cualquier comparación MASSIVE-vs-baseline sobre esos casos es científicamente cuestionable.

**Acción sugerida.** Capturar `mle_retvals` y marcar el baseline como `converged: false` en `metrics.json`; hacer que el runner falle (o avise con código de salida distinto de 0) si un baseline no converge; considerar series de muestra más largas o inicialización distinta.

**Esfuerzo:** M

---

**ID:** D4-012
**Severidad:** 🟡
**Dominio:** Tests
**Título:** En el caso de muestra publicado, MASSIVE pierde contra un baseline lineal (`ridge_lags`) en MAE y en accuracy direccional
**Ubicación:** `/tmp/pvu_out/report.md` · `datasets/pvu_cases/sample_case_001`
**Estado:** **[CONFIRMADO]**

**Evidencia.** Salida textual del runner:
```
### Baseline metrics (test split) — sample_case_001, target polarization_index
| Baseline           | MAE    | RMSE   | MAPE   | Dir.Acc |
| ridge_lags         | 0.1239 | 0.1335 | 40.58  | 0.5882  |  ← mejor baseline
| random_regime      | 0.1563 | 0.1734 | 50.54  | 0.2941  |
| ar1                | 0.1632 | 0.1731 | 53.01  | 0.5882  |
| naive              | 0.2297 | 0.2427 | 74.50  | 0.0000  |
| arima              | 0.2468 | 0.2590 | 79.66  | 0.1765  |
| ets                | 0.3297 | 0.3479 | 106.53 | 0.4118  |

### MASSIVE metrics (test split)
| MAE    | RMSE   | MAPE   | Dir.Acc |
| 0.1261 | 0.1395 | 41.17  | 0.3529  |
```
MASSIVE queda **2º en MAE** (peor que `ridge_lags`) y **por debajo de lanzar una moneda** en accuracy direccional (0.3529 < 0.5), mientras `ridge_lags` y `ar1` alcanzan 0.5882.

El propio reporte se auto-descarga: *"⚠️ Sample-case disclaimer: results from `sample_case_*` are synthetic and do NOT constitute PVU real-validation evidence. Real validation requires N ≥ 10 independent cases."* Y sólo hay 2 sample cases en `datasets/pvu_cases/`, aunque existen **12 casos reales** en `datasets/real_cases/` (brazil_election_2022, brexit_referendum_2016, chile_estallido_2019, colombia_paro_2021, egypt_arab_spring_2011, france_gilets_jaunes_2018, germany_pegida_2014, hong_kong_protests_2019, iran_mahsa_amini_2022, myanmar_coup_cdm_2021, south_korea_candlelight_2016, us_election_2020) que el runner por defecto **no ejecuta**.

**Impacto.** El protocolo pre-registrado del proyecto exige N ≥ 10 y el repo **tiene** los 12 casos, pero el comando por defecto (README, Makefile `benchmark`, `pvu-validation.yml`, `publish.yml`) apunta sólo a `datasets/pvu_cases`. Así, la única validación que corre en CI es la que el propio reporte declara no válida, y en ella el modelo pierde contra una regresión lineal.

**Acción sugerida.** Cambiar el default a `datasets/real_cases` (o ejecutar ambos y publicar los dos resultados); añadir al `metrics.json` un campo `beats_best_baseline: bool` y hacerlo fallar el gate si es `false`; publicar el resultado de los 12 casos reales en el README en lugar de la tabla teórica.

**Esfuerzo:** M

---

**ID:** D4-013
**Severidad:** 🟢
**Dominio:** Tests
**Título:** Suite predominantemente de integración real: ratio de mocks bajo y sólo 2 skips en 666 tests
**Ubicación:** `tests/`
**Estado:** **[CONFIRMADO — POSITIVO]**

**Evidencia.**
```
$ grep -rn "def test_" tests/ --include="*.py" | wc -l        → 666
$ grep -rnE "mock|Mock|patch" tests/ --include="*.py" | wc -l → 69   (ratio 0.10 mocks/test)
$ grep -rnE "@pytest.mark.skip|skipif|xfail" tests/ | wc -l   → 2
    tests/test_cfc_engine.py:39  skip_no_torch = pytest.mark.skipif(not TORCH_AVAILABLE, …)
    tests/test_cfc_router.py:96  skip_no_torch = pytest.mark.skipif(not TORCH_AVAILABLE, …)
$ grep -rnE "assert True|assert 1$" tests/                     → 0 aserciones vacías literales
59 archivos de test · 681 tests recolectables · 669 pasan en entorno completo
```

**Impacto.** Positivo y relevante: la suite prueba el sistema real, no dobles. No hay `xfail` acumulados ni skips silenciosos que enmascaren deuda. Los 681 tests corren en ~28 s.

**Acción sugerida.** Mantener. Al añadir los tests que faltan (D4-003/D4-004), preservar el estilo de integración.

**Esfuerzo:** —

---

**ID:** D4-014
**Severidad:** 🟡
**Dominio:** Tests
**Título:** Mezcla de `unittest.TestCase` y pytest en los mismos archivos; 230 asserts estilo unittest
**Ubicación:** `tests/test_cfc_engine.py`, `tests/test_cfc_router.py` y ~21 archivos más
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ ruff check . --isolated --select PT
230 × PT009 pytest-unittest-assertion       (self.assertEqual/assertTrue en archivos test_*.py)
 16 × PT018 pytest-composite-assertion      (assert a and b — no reporta cuál falló)
 13 × PT011 pytest-raises-too-broad         (pytest.raises(Exception))
  4 × PT001 pytest-fixture-incorrect-parentheses-style
  3 × PT027 pytest-unittest-raises-assertion
  1 × PT028 pytest-parameter-with-default-argument

Caso concreto: tests/test_cfc_engine.py importa `unittest` Y `pytest`, define clases
`unittest.TestCase` y a la vez usa `pytest.mark.skipif` como decorador de clase.
tests/test_cfc_lambda_integration.py:18 `def reset_router` es una fixture sin `@pytest.fixture`
  (vulture la reporta como función no usada).
```

**Impacto.** `PT018` (16 asserts compuestos) y `PT011` (13 `raises(Exception)`) reducen el valor diagnóstico de los fallos. Las fixtures sin decorador no se aplican → el singleton no se resetea (D4-008).

**Acción sugerida.** Migración incremental a asserts de pytest (`ruff --select PT --fix` resuelve PT001/PT009 automáticamente en parte); convertir `reset_router`/`sparse_rng`/`_hermetic` en fixtures reales.

**Esfuerzo:** M

---

### DOMINIO 5 — DEPENDENCIAS Y SEGURIDAD

---

**ID:** D5-001
**Severidad:** 🔴
**Dominio:** Seguridad
**Título:** El backend canónico no impone ningún límite a `pasos`, `n_agents` ni `max_intentos` — las protecciones anti-DoS documentadas sólo existen en los caminos deprecados
**Ubicación:** `backend/app/routers/sim.py:45` · `backend/app/routers/engine.py:88` · `services/simulation_service.py:49,89` · `services/llm_orchestrator.py:446`
**Estado:** **[CONFIRMADO]**

**Descripción.** El README declara textualmente: *"Security: … `n_agents` cap (prevents 8 TB OOM), `max_intentos` clamp (prevents LLM DoS)"*. La búsqueda de esos límites muestra que viven **exclusivamente** en `api.py` (marcado DEPRECATED) y en `massive-ui-ng/backend/app/routers/live.py` (excluido de CI y no desplegado).

**Evidencia.**
```
Límites que SÍ existen (caminos no canónicos):
  api.py:303                              max_intentos=min(int(payload.get("max_intentos", 3)), 10)   ← DEPRECATED
  massive-ui-ng/backend/app/routers/live.py:46-47  _ENERGY_MAX_AGENTS = 200 ; _MASSIVE_MAX_AGENTS = 200_000
  massive-ui-ng/backend/app/routers/live.py:113,122  n_agents = max(2, min(n_agents, _ENERGY_MAX_AGENTS))

Camino CANÓNICO, sin límites:
  backend/app/routers/sim.py:45       pasos=int(payload.get("pasos", 50))                 ← sin cota superior
  backend/app/routers/engine.py:88    max_intentos=int(payload.get("max_intentos", 3))    ← sin clamp
  services/simulation_service.py:49   def run_multilayer_simulation(*, n_agents: int = 100, steps: int = 50, …)
  services/simulation_service.py:89   n_agents: int = 10_000, …  N=n_agents               ← sin clamp
  services/llm_orchestrator.py:446    max_intentos=int(config.get("max_intentos", 3))     ← sin clamp

$ grep -rniE "MAX_N_AGENTS|MAX_AGENTS|N_AGENTS_MAX|max_agents" --include="*.py" backend services massive_core
(vacío)

Causa raíz arquitectónica: los routers aceptan `payload: dict[str, Any]` en lugar de los DTOs
Pydantic con `Field(ge=…, le=…)` que ya existen (D3-004). Las cotas están escritas pero no cableadas.
```

**Impacto.** Un cliente autenticado con la clave de desarrollo publicada (`dev-secret-key`) puede enviar `POST /v1/simulate {"pasos": 100000000}` o `POST /v1/engine/energy {"n_agents": 10000000}` y agotar CPU/RAM del worker. `MultilayerEngine(N=n)` construye una matriz de adyacencia, así que el coste es O(N²) en memoria: N=100 000 → ~80 GB. El rate-limit (60 req/min) no mitiga: una sola petición basta. La afirmación del README es falsa para el camino que el README recomienda.

**Acción sugerida.** Cablear los DTOs Pydantic como cuerpo de request (D3-004) con cotas explícitas: `pasos: int = Field(50, ge=1, le=10_000)`, `n_agents: int = Field(100, ge=2, le=200_000)`, `max_intentos: int = Field(3, ge=1, le=10)`. Añadir tests de límite (payload fuera de rango → 422).

**Esfuerzo:** M

---

**ID:** D5-002
**Severidad:** 🔴
**Dominio:** Dependencias
**Título:** `pip install -e .` es imposible: el build-backend es `maturin` y ningún Dockerfile, workflow o documento instala un toolchain Rust
**Ubicación:** `pyproject.toml:1-4` · `install.sh:cmd_install/cmd_install_dev` · `Dockerfile:66` · `.github/workflows/publish.yml`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
pyproject.toml:
  [build-system] requires = ["maturin>=1.7,<2.0", "setuptools>=68"] ; build-backend = "maturin"
  [tool.maturin] module-name = "massive_rust_core" ; features = ["pyo3/extension-module"]

$ pip install --no-deps -e .
BackendUnavailable: ModuleNotFoundError: No module named 'maturin'

$ pip install maturin && pip install --no-deps --no-build-isolation -e .
  File ".../maturin/__init__.py", line 80, in _get_env
    from puccinialin import setup_rust
ModuleNotFoundError: No module named 'puccinialin'
error: metadata-generation-failed

$ grep -rniE "cargo|rustc|maturin" .github/ Dockerfile Dockerfile.optimized Makefile install.sh
(vacío — ningún job ni imagen instala Rust)

Consumidores rotos:
  install.sh:cmd_install      pip_cmd install -e ".[dev]"      ← el comando de instalación documentado
  install.sh:cmd_install_dev  pip_cmd install -e ".[full]"
  Dockerfile:66               RUN pip install --no-deps -e /app  ← la imagen de producción
  publish.yml:job docs        pip install -e ".[docs]"
  publish.yml:job build-wheels python -m build                    ← sdist+wheel para PyPI
```

**Impacto.** Cuatro caminos de despliegue/instalación rotos: el script de instalación oficial, la imagen Docker principal, el build de documentación de CI y la publicación a PyPI. Como el Dockerfile falla en `RUN pip install --no-deps -e /app`, **`docker compose build` no puede completar**, lo que hace fallar `docker-e2e.yml` incluso con facturación restaurada.

**Acción sugerida.** Desacoplar el paquete Python de la extensión Rust: usar `setuptools` como build-backend para `massive` y publicar `massive_rust_core` como un paquete/wheel separado y opcional (o construirlo con `maturin` en un job dedicado que instale `dtolnay/rust-toolchain`). Mientras tanto, cambiar `Dockerfile:66` a una instalación sin build (copiar el árbol + `PYTHONPATH`) o instalar Rust en la stage builder.

**Esfuerzo:** L

---

**ID:** D5-003
**Severidad:** 🟠
**Dominio:** Dependencias
**Título:** 0 de 30 dependencias pinneadas y no existe lockfile de Python
**Ubicación:** `requirements.txt` · `pyproject.toml` · `.gitignore:60`
**Estado:** **[CONFIRMADO]** · punto 5.2 del brief

**Evidencia.**
```
$ grep -v "==" requirements.txt | grep -v "#" | grep -v "^$" | wc -l → 30
$ grep -vE "^\s*#" requirements.txt | grep -v "^$" | wc -l           → 30
   → 30/30 líneas usan `>=`, ninguna usa `==`

$ ls *.lock uv.lock poetry.lock Pipfile* constraints*.txt
-rw-r--r-- Cargo.lock            ← solo existe lockfile de Rust
ls: cannot access 'uv.lock': No such file or directory

.gitignore:60  uv.lock           ← el repo ignora ACTIVAMENTE el lockfile

Sin pin también en el tooling: pyproject `dev` extra = "mypy>=1.8", "ruff>=0.6", "black>=24"
→ la definición de "formateado correcto" puede cambiar entre dos runs de CI.
```

**Impacto.** Builds no reproducibles. Un release upstream de numpy/scipy/torch puede romper `main` sin ningún commit del proyecto. Explica también por qué `black --check` puede empezar a fallar espontáneamente (D2-002). Y hace que `pip-audit` sea menos útil: audita la resolución *actual*, no la declarada.

**Acción sugerida.** Generar y commitear un lockfile (`uv pip compile` o `pip-tools`) por plataforma/extra; dejar `requirements.txt` como archivo de input con rangos y añadir `requirements.lock`. Retirar `uv.lock` del `.gitignore`. Pinnear al menos black/ruff/mypy a versión exacta.

**Esfuerzo:** M

---

**ID:** D5-004
**Severidad:** 🟠
**Dominio:** Dependencias
**Título:** `requirements.txt` y `pyproject.toml` declaran conjuntos de dependencias distintos y con especificadores distintos
**Ubicación:** `requirements.txt` (30 entradas) · `pyproject.toml:14-46`
**Estado:** **[CONFIRMADO]** · punto 5.1 del brief

**Evidencia.**
```
$ diff <(requirements.txt normalizado) <(pyproject dependencies+extras normalizado)
Solo en requirements.txt:
  plotly>=5.18.0            ← NO está en pyproject (ni en el extra `core` ni en ninguno)
  streamlit>=1.36.0         ← NO está en pyproject; pyproject dice explícitamente que fue eliminado
  torch>=2.2.0              ← en pyproject solo bajo el extra `ml`
Solo en pyproject (extra `dev`):
  black>=24 · build>=1.2 · mypy>=1.8 · pytest-cov>=5.0 · ruff>=0.6
Especificadores divergentes para el mismo paquete:
  scikit-learn>=1.4.0 (req) vs scikit-learn>=1.4 (pyproject)
  statsmodels>=0.14.0 vs statsmodels>=0.14
  torch>=2.2.0        vs torch>=2.2
  plotly>=5.18.0      vs (ausente)
Self-reference en el diff:  massive[core,api,llm,ml,scientific,docs,dev]  (extra `full`)
```
Además `pytest>=8.0.0` está en el `requirements.txt` **principal** (no en un extra de dev), y `mkdocs`/`mkdocs-material`/`mkdocstrings` también — todos se instalan en la imagen Docker de producción.

**Impacto.** Dos fuentes de verdad que ya divergieron. `pip install -r requirements.txt` y `pip install massive[core]` producen entornos distintos. `plotly` es importado por los tests (`tests/test_visualizations.py`) pero no está declarado en el paquete publicado. `torch` es requerido de facto (D1-001) pero opcional de jure.

**Acción sugerida.** Hacer de `pyproject.toml` la única fuente de verdad y generar `requirements.txt` a partir de él (`uv pip compile --extra core --extra api …`). Mover `pytest`/`mkdocs*` a extras de dev/docs. Añadir `plotly` al extra correspondiente. Resolver `torch` (ver D5-008).

**Esfuerzo:** M

---

**ID:** D5-005
**Severidad:** 🟠
**Dominio:** Dependencias
**Título:** 6 paquetes importados por el código no están declarados en ninguna parte (+ `httpx` para tests)
**Ubicación:** `requirements.txt` · `pyproject.toml`
**Estado:** **[CONFIRMADO]**

**Evidencia.** Extracción AST de todos los imports de nivel superior, filtrada contra stdlib, módulos locales y lo declarado:
```
Imports externos encontrados en el código (31):
  cupy, dask, fastapi, groq, hdbscan, langchain_core, langchain_groq, langchain_openai,
  massive_rust_core, nashpy, networkx, numpy, openai, pandas, persim, pgmpy, plotly,
  praw, psutil, pydantic, pytest, requests, ripser, scipy, sklearn, starlette,
  statsmodels, torch, tweepy, uvicorn, yaml

IMPORTADOS PERO NO DECLARADOS:
  psutil   → benchmark_scalability.py:29 (import en cabeza de módulo, HARD)
             experiments/04_benchmark/run_pvu_benchmark.py:211
  cupy     → massive_engine.py:60,90,734 · benchmark_scalability.py:83   (try/except, soft)
  hdbscan  → micro_engine.py:43                                          (try/except, soft)
  groq     → interpreter_layer.py:251                                    (lazy, soft)
  ripser   → simulator.py:63                                             (try/except, soft)
  persim   → simulator.py:62                                             (try/except, soft)
  massive_rust_core → massive_core/rust_core.py:19 (find_spec, soft)
  httpx    → requerido por starlette.testclient en 3 archivos de test (D4-006)
Transitivos aceptables: langchain_core (vía langchain), starlette (vía fastapi)
```

**Impacto.** `psutil` es el único **hard-fail**: `import benchmark_scalability` lanza `ModuleNotFoundError`. Ese archivo es el que produce las cifras de escalabilidad del README (D9-005), así que la evidencia de la afirmación de marketing es inejecutable tras un `pip install -r requirements.txt`. Los soft (try/except) degradan capacidades en silencio: `cupy` → sin GPU; `hdbscan` → sin clustering en micro_engine; `ripser`/`persim` → sin detección topológica (se ve el warning en cada arranque del servidor).

**Acción sugerida.** Añadir `psutil` a `requirements.txt`; crear extras `gpu = ["cupy"]`, `tda = ["ripser", "persim"]`, `clustering = ["hdbscan"]`, `social = ["tweepy", "praw"]`, `test = ["pytest", "pytest-cov", "httpx"]`. Documentar en el README qué capacidad se pierde sin cada extra.

**Esfuerzo:** S

---

**ID:** D5-006
**Severidad:** 🟠
**Dominio:** Dependencias
**Título:** Dependencias declaradas con cero imports: `torchdiffeq` y `streamlit`
**Ubicación:** `requirements.txt:26,29` · `pyproject.toml:38` (extra `ml`)
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ grep -rn "import torchdiffeq|from torchdiffeq" --include="*.py" .  → 0
$ grep -rn "import streamlit|from streamlit"     --include="*.py" .  → 0

requirements.txt:26  torchdiffeq>=0.2.3       (bajo "# Scientific / ML")
requirements.txt:29  streamlit>=1.36.0        (bajo "# UI (Streamlit legacy UIL demo flow — optional in Docker)")
pyproject.toml:38    ml = ["torch>=2.2", "torchdiffeq>=0.2.3", "scikit-learn>=1.4"]
pyproject.toml:36-37 # Streamlit (legacy UIL demo flow) was removed — see OPS-02.
```
Contradicción interna: `pyproject.toml` documenta en un comentario que Streamlit fue **eliminado**, mientras `requirements.txt` lo sigue declarando.

**Impacto.** `torchdiffeq` arrastra dependencias y tiempo de build; `streamlit` añade ~100 MB y decenas de dependencias transitivas a la imagen Docker de producción para una UI que no existe. Ambos inflan el tiempo de `docker compose build` y la superficie de CVEs.

**Acción sugerida.** Eliminar `streamlit` de `requirements.txt` (ver D1-006). Verificar si `torchdiffeq` se usaba en la capa CfC antes de una refactorización; si no, eliminarlo también del extra `ml`.

**Esfuerzo:** XS

---

**ID:** D5-007
**Severidad:** 🟠
**Dominio:** Dependencias
**Título:** El `requirements.txt` de producción instala pytest y el stack completo de MkDocs en la imagen Docker
**Ubicación:** `requirements.txt:10,33-35` · `Dockerfile:20,57`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
requirements.txt:10  pytest>=8.0.0          (bajo "# Core", NO en una sección de dev)
requirements.txt:33  mkdocs>=1.5.3
requirements.txt:34  mkdocs-material>=9.5.0
requirements.txt:35  mkdocstrings[python]>=0.24.0

Dockerfile:20  RUN pip wheel --wheel-dir=/wheels -r /wheels/requirements.txt
Dockerfile:57  RUN pip install --no-index --find-links /wheels -r /app/requirements.txt
→ pytest + mkdocs + mkdocs-material + mkdocstrings se compilan y se instalan en la imagen runtime
```

**Impacto.** Imagen de producción más grande y con más superficie de ataque de lo necesario; tiempo de build mayor (mkdocs-material trae muchas dependencias). Un framework de test en runtime también permite que un endpoint mal aislado ejecute código de test.

**Acción sugerida.** Split en `requirements.txt` (runtime) + `requirements-dev.txt` (test/lint/docs); que el Dockerfile instale sólo el primero.

**Esfuerzo:** S

---

**ID:** D5-008
**Severidad:** 🟠
**Dominio:** Dependencias
**Título:** `torch` es una dependencia dura de facto pero opcional de jure
**Ubicación:** `requirements.txt:25` vs `pyproject.toml:38` (extra `ml`) · `cfc_router.py:90` · `cfc_engine.py:21`
**Estado:** **[CONFIRMADO]**

**Descripción.** El diseño declarado es "torch opcional con fallback transparente". La realidad medida es que sin torch el proyecto no se puede importar (D1-001, D1-002, D1-004). `requirements.txt` lo incluye, `pyproject.toml` lo relega al extra `ml`.

**Evidencia.**
```
requirements.txt:25           torch>=2.2.0                    (sección "# Scientific / ML")
pyproject.toml:14-27          [project] dependencies → NO incluye torch
pyproject.toml:38             ml = ["torch>=2.2", "torchdiffeq>=0.2.3", "scikit-learn>=1.4"]
cfc_router.py:1-13 docstring  "Sin PyTorch instalado → fallback transparente."  ← FALSO (D1-001)
cfc_engine.py:31 warning      "CFC engine usará implementación NumPy fallback."  ← FALSO (D1-002)
massive_core/neural_physics/pinns.py:3-90  import torch en cabeza, sin fallback → 0 % cobertura
pytest.yml:job core           instala deps SIN torch y corre tests/test_simulator.py → falla
Reproducción:  sin torch → 25/146 módulos no importables, 21 archivos de test no recolectables
               con torch → 146/146 OK
```

**Impacto.** `pip install massive` (el wheel publicado, dependencias base de pyproject) produce un paquete roto. El job de CI más rápido está roto por diseño. Y la documentación promete una tolerancia a fallos que el código no implementa.

**Acción sugerida.** Decisión binaria y explícita: (A) hacer `torch` dependencia base y borrar los fallbacks falsos; o (B) arreglar los fallbacks de verdad (D1-001 + D1-002 + `pinns.py`) y añadir la matriz de CI sin torch. (B) es más trabajo pero coherente con la arquitectura "opt-in" que el README vende.

**Esfuerzo:** L (opción B) · XS (opción A)

---

**ID:** D5-009
**Severidad:** 🟡
**Dominio:** Seguridad
**Título:** `GET /metrics` responde 200 sin autenticación y nginx lo expone públicamente
**Ubicación:** `backend/app/main.py` (registro de `/metrics`) · `nginx.conf:62` (regex de locations que incluye `metrics`)
**Estado:** **[CONFIRMADO]** — sonda en vivo

**Evidencia.**
```
$ uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
$ curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8000/metrics            → 200   (sin X-API-Key)
$ curl -s -o /dev/null -w "%{http_code}" -H "X-API-Key: dev-secret-key" …/metrics  → 200
Comparativa: POST /v1/simulate sin key → 401  ✓ (el resto de la API sí protege)

nginx.conf:62  location ~ ^/(docs|openapi.json|redoc|health|ready|version|metrics) { proxy_pass …; }
→ /docs, /redoc, /openapi.json Y /metrics quedan expuestos en el puerto 80 público

backend/app/metrics.py emite: http_requests_total{method,group,status}, massive_uptime_seconds,
  histograms de latencia y SLO gauges.
.env.example documenta MASSIVE_SLO_ERROR_BUDGET y MASSIVE_SLO_P95_LATENCY_MS.
```

**Impacto.** Divulgación de información operativa: volumen de tráfico por grupo de endpoints, tasas de error, latencias p95 y uptime. Es exactamente el perfil que un atacante necesita para dimensionar un ataque y para saber cuándo el sistema está degradado. `/docs` + `/openapi.json` públicos además publican el esquema completo de la API.

**Acción sugerida.** Proteger `/metrics` con la misma dependencia `get_api_key`, o restringirlo por red (sólo desde el CIDR del scraper de Prometheus) en `nginx.conf`; deshabilitar `/docs`, `/redoc` y `/openapi.json` cuando `MASSIVE_ENV=production`.

**Esfuerzo:** S

---

**ID:** D5-010
**Severidad:** 🟡
**Dominio:** Seguridad
**Título:** `.env.example` propone `MASSIVE_ALLOWED_HOSTS=*` (wildcard)
**Ubicación:** `.env.example:66`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
.env.example:66   MASSIVE_ALLOWED_HOSTS=*
```
`nginx.conf` usa `server_name _;` (catch-all) y pasa `proxy_set_header Host $host` sin validar.

**Impacto.** Un allowlist de hosts en wildcard anula la protección contra Host-header injection / cache poisoning. Combinado con `MASSIVE_CORS_ORIGINS` bien configurado el riesgo es menor, pero el archivo de ejemplo es lo que la gente copia.

**Acción sugerida.** Cambiar el valor de ejemplo a `localhost,127.0.0.1` con un comentario explicando que en producción debe listarse el dominio real; validar el header `Host` contra la lista en el middleware.

**Esfuerzo:** XS

---

**ID:** D5-011
**Severidad:** 🟡
**Dominio:** Seguridad / Configuración
**Título:** `.env.example` duplica claves y documenta explícitamente dos convenciones en competencia
**Ubicación:** `.env.example:26` y `:72` · `:57-62`
**Estado:** **[CONFIRMADO]** · punto 5.5 del brief

**Evidencia.**
```
Duplicación literal:
  .env.example:26   OLLAMA_HOST=http://localhost:11434   # optional, for local Ollama integration
  .env.example:72   OLLAMA_HOST=http://localhost:11434

El propio archivo admite la inconsistencia:
  .env.example:53  # ─── Missing Environment Variables (Added 2026-09-14) ───
  .env.example:54  # These variables are used in the codebase but were not documented:
  .env.example:59  # LLM Configuration (two naming conventions exist - use the consistent one)
  .env.example:60  LLM_MODEL=google/gemini-2.5-pro
  .env.example:61  MASSIVE_LLM_MODEL=google/gemini-2.5-pro     ← misma semántica, dos nombres
  .env.example:62  LLM_PROVIDER=google
  .env.example:23  PROVIDER=groq                               ← y un tercer nombre para proveedor
  .env.example:67  MASSIVE_API_KEYS=  # comma-separated API keys (plural, different from MASSIVE_API_KEY)
  .env.example:9   MASSIVE_API_KEY=change-me-in-production

Sección con formato roto: las líneas 11-12 y 39 usan sangría de continuación que en un .env
real se interpreta como una variable llamada " " o se ignora:
  .env.example:11  "                                           # In production set to your UI domain(s)…"
```

**Impacto.** Un operador que copie `.env.example` obtiene dos convenciones activas y no sabe cuál gana; el comentario "use the consistent one" no dice cuál es la consistente. Las líneas de continuación sangradas pueden producir parseos inesperados según la librería (`python-dotenv` vs el loader de Docker).

**Acción sugerida.** Eliminar duplicados; elegir `MASSIVE_*` como prefijo canónico y mantener `LLM_MODEL`/`PROVIDER` sólo como alias deprecados con comentario; convertir las líneas de continuación en comentarios de línea completa.

**Esfuerzo:** S

---

**ID:** D5-012
**Severidad:** 🟡
**Dominio:** Seguridad / Configuración
**Título:** `.env.local.example` es un subconjunto divergente de `.env.example`, y `docker-compose.yml` monta ambos
**Ubicación:** `.env.local.example` (8 vars) · `.env.example` (~40 vars) · `docker-compose.yml:16-17`
**Estado:** **[CONFIRMADO]** · punto 5.5 del brief

**Evidencia.**
```
$ diff .env.example .env.local.example
.env.local.example contiene SOLO:
  GROQ_API_KEY, OPENAI_API_KEY, OPENROUTER_API_KEY, OLLAMA_HOST,
  TWITTER_BEARER_TOKEN, REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET
Faltan respecto de .env.example: MASSIVE_API_KEY, MASSIVE_ENV, MASSIVE_CORS_ORIGINS,
  MASSIVE_RATE_LIMIT_*, MASSIVE_MAX_UPLOAD_MB, MASSIVE_LOG_FILE, PROVIDER,
  MASSIVE_LLM_TIMEOUT_SECONDS, MASSIVE_LLM_MAX_RETRIES, OTEL_*, MASSIVE_SLO_*,
  CACHE_DB_PATH, EVAL_*, LLM_MODEL, MASSIVE_LLM_MODEL, MASSIVE_ALLOWED_HOSTS, …

docker-compose.yml:16-17
    volumes:
      - ./.env.local:/app/.env.local:ro
      - ./.env:/app/.env:ro
.env.local.example:2  "Mounted into the Docker container and read by backend/app/settings.py"
.env.local.example:3  "Copy .env.example to .env.local and fill in your API keys."
   ← instrucción contradictoria: dice copiar .env.example a .env.local, siendo el primero 5× mayor
```

**Impacto.** Dos archivos que se montan simultáneamente con contenidos solapados y sin regla de precedencia documentada. `MASSIVE_API_KEY` no está en `.env.local.example`, así que un despliegue que sólo cree `.env.local` arranca sin clave → cae en el fallback de desarrollo (D5-013).

**Acción sugerida.** Unificar en un único `.env.example` y eliminar `.env.local.example`, o documentar explícitamente la precedencia y qué变量 pertenece a cuál.

**Esfuerzo:** S

---

**ID:** D5-013
**Severidad:** 🟡
**Dominio:** Seguridad
**Título:** `MASSIVE_ENV` sin definir resuelve a "development", lo que activa la clave fallback publicada `dev-secret-key`
**Ubicación:** `massive_core/config/api_auth.py:22,38-40` · `backend/app/security.py:57` · `api.py:39`
**Estado:** **[CONFIRMADO]** — sonda en vivo

**Descripción.** El diseño es correcto en intención (fail-closed en staging/production) pero **insecure by default**: la ausencia de `MASSIVE_ENV` se interpreta como development.

**Evidencia.**
```python
# massive_core/config/api_auth.py
DEV_FALLBACK_API_KEY = "dev-secret-key"
_DEV_ENV_VALUES = frozenset({"development", "dev"})

def is_dev_env(env: str | None) -> bool:
    """…True for None, "", "development" and the legacy alias "dev"…
    Unset is development, matching the documented default in .env.example"""
    return (env or "development").strip().lower() in _DEV_ENV_VALUES
```
```
Sonda en vivo (servidor arrancado SIN MASSIVE_ENV y SIN MASSIVE_API_KEY):
  log:  WARNING MASSIVE_API_KEY not set — using dev fallback (development mode only)
  curl -H "X-API-Key: dev-secret-key" POST /v1/simulate → 200
  curl (sin header)                                     → 401

Publicación de la clave:
  README.md:56 · README_ES.md:56 · docs/MASSIVE_LLM_INTERFACE.md:261,274,292,302
  docs/runbooks/local-development.md:32-33 · PRODUCTION_ARCHITECTURE_SPEC.md:190,500,506
  gitleaks.toml: allowlist explícito de "dev-secret-key"
docs/production-readiness-audit.md:40 ya lo registra como SEC-04 (🟡, sin resolver)
```

**Impacto.** Cualquier despliegue que olvide fijar `MASSIVE_ENV=production` acepta una clave conocida y publicada. El warning existe pero sólo en el log de arranque.

**Acción sugerida.** Invertir el default: `MASSIVE_ENV` sin definir → `staging` (fail-closed), y exigir `MASSIVE_ENV=development` explícito para habilitar el fallback. Alternativamente, exigir que el fallback se active con una segunda variable (`MASSIVE_ALLOW_DEV_FALLBACK=1`). Añadir un test que arranque la app sin env y verifique 503.

**Esfuerzo:** S

---

**ID:** D5-014
**Severidad:** 🟡
**Dominio:** Seguridad
**Título:** CSP con `'unsafe-inline'` en script-src y style-src; header deprecado `X-XSS-Protection`; sin `server_tokens off`
**Ubicación:** `nginx.conf:73-79`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```nginx
add_header X-Frame-Options "DENY" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header X-XSS-Protection "1; mode=block" always;          ← deprecado; puede introducir vulns en navegadores legacy
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline';
   style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self' https:;
   frame-ancestors 'none';" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
```
Ausentes: `server_tokens off`, `Permissions-Policy`, `Cross-Origin-Opener-Policy`, `Cross-Origin-Resource-Policy`, gzip/brotli.

**Impacto.** `'unsafe-inline'` en `script-src` anula la principal defensa CSP contra XSS inyectado. `connect-src 'self' https:` permite exfiltración a **cualquier** origen HTTPS. HSTS sin `preload`. La versión de nginx queda expuesta en el header `Server`.

**Acción sugerida.** Construir el frontend sin inline scripts (Vite lo permite con `build.assetsInlineLimit` y hashes) y eliminar `'unsafe-inline'` de `script-src`; restringir `connect-src` a la lista real de proveedores LLM; añadir `server_tokens off` y `Permissions-Policy`.

**Esfuerzo:** M

---

**ID:** D5-015
**Severidad:** 🟡
**Dominio:** Seguridad
**Título:** El `add_header` del location de assets estáticos cancela todos los headers de seguridad del nivel server (regla de herencia de nginx)
**Ubicación:** `nginx.conf:66-71` vs `:73-79`
**Estado:** **[CONFIRMADO]** (por semántica documentada de nginx) · **[HIPÓTESIS]** en cuanto a la respuesta real (sin nginx en el sandbox)

**Descripción.** En nginx, `add_header` se hereda del nivel superior **sólo si el nivel actual no define ningún `add_header` propio**. El location de assets define uno.

**Evidencia.**
```nginx
server {
    location ~* \.(js|css|png|jpg|jpeg|gif|svg|ico|woff2?|ttf)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";    ← único add_header del bloque
        access_log off;
    }
    # ...a nivel server:
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Content-Security-Policy "…" always;
    add_header Strict-Transport-Security "…" always;
}
```
Consecuencia: las respuestas de `/assets/*.js` y `*.css` salen **sin** CSP, sin HSTS, sin X-Content-Type-Options, sin X-Frame-Options.

**Impacto.** Los archivos JavaScript y CSS —los de mayor riesgo— se sirven sin `X-Content-Type-Options: nosniff` y sin HSTS. Un escáner de seguridad que sólo pruebe `/` reportará "headers OK" y dará un falso positivo de cumplimiento.

**Acción sugerida.** Repetir el bloque completo de `add_header` dentro del location de assets, o (mejor) mover los headers de seguridad a un `include security-headers.conf` e incluirlo en cada `location`.

**Esfuerzo:** XS

---

**ID:** D5-016
**Severidad:** 🟡
**Dominio:** Seguridad / CI
**Título:** El deploy a Hugging Face embebe el token en la URL del remoto git y hardcodea el usuario
**Ubicación:** `.github/workflows/deploy_hf_spaces.yml:22-25`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```yaml
run: |
  git push https://Adlgr87:$HF_TOKEN@huggingface.co/spaces/$SPACE_ID main
```
Además `SPACE_ID: "Adlgr87/MASSIVE"` está hardcodeado en el env del step, y el checkout usa `lfs: true` mientras ningún archivo del repo está declarado en `.gitattributes` como LFS (`.gitattributes` contiene sólo `* text=auto`).

**Impacto.** El token aparece en la línea de comando del proceso; con `set -x` o en ciertos logs de acción puede filtrarse. El nombre de usuario hardcodeado impide el fork-and-deploy. `lfs: true` sin configuración LFS es un no-op que sólo añade tiempo (y es la pista de que los `.pt` deberían estar en LFS, ver D4-001).

**Acción sugerida.** Usar `git remote add hf https://Adlgr87:${HF_TOKEN}@…` con `x-access-token` y limpiar el remoto tras el push, o mejor, la acción oficial `huggingface/hub-docs`/`wauplin/push-to-hub-action`. Parametrizar `SPACE_ID` desde `vars`.

**Esfuerzo:** S

---

**ID:** D5-017
**Severidad:** 🟢
**Dominio:** Seguridad
**Título:** `pip-audit` no encuentra vulnerabilidades conocidas en `requirements.txt`
**Ubicación:** `requirements.txt`
**Estado:** **[CONFIRMADO — POSITIVO]** · punto 5.3 del brief

**Evidencia.**
```
$ pip-audit -r requirements.txt --no-deps
WARNING:pip_audit._cli:--no-deps is supported, but users are encouraged to fully hash their pinned dependencies
WARNING:pip_audit._cli:Consider using a tool like `pip-compile`: https://pip-tools.readthedocs.io/en/latest/#using-hashes
No known vulnerabilities found
```
El propio warning de la herramienta refuerza D5-003: sin pinning ni hashes, la auditoría es puntual y no garantiza reproducibilidad.

**Impacto.** Positivo, con la salvedad de que audita la resolución del momento.

**Acción sugerida.** Ejecutar `pip-audit` contra el lockfile una vez exista (D5-003), y con `--require-hashes`.

**Esfuerzo:** —

---

**ID:** D5-018
**Severidad:** 🟢
**Dominio:** Seguridad
**Título:** Sin credenciales en el árbol; `llm_credentials.py` está bien diseñado. Items `test-zapier.txt` y secretos commiteados: RESUELTOS
**Ubicación:** `llm_credentials.py` · `massive/core/llm_credentials.py` · `gitleaks.toml`
**Estado:** **[CONFIRMADO — POSITIVO / RESUELTO]** · **[CONOCIDO PREVIO — item "test-zapier.txt"]**

**Evidencia.**
```
$ git ls-files | grep -iE "\.env$|api_key|secret|token|credential|\.pem$|\.key$|password"
.github/workflows/secret_scan.yml          (workflow, no secreto)
docs/security/secrets-and-configuration.md (documentación)
llm_credentials.py                         (shim deprecado)
massive/core/llm_credentials.py            (implementación)
→ 0 archivos de credenciales trackeados. 0 .env trackeados. Solo .env.example y .env.local.example.

$ cat massive/core/llm_credentials.py       (leído completo, como pide el brief — alto riesgo)
  PROVIDER_ENV_KEYS = {"groq": "GROQ_API_KEY", "openai": "OPENAI_API_KEY", "openrouter": "OPENROUTER_API_KEY"}
  _provider_keys: dict[str, str] = {}     ← store en memoria
  Comentario de diseño explícito y correcto:
    "In-memory store for provider API keys. Avoids mutating os.environ which leaks keys
     to subprocesses, overwrites HF Secrets, and leaves stale values when providers are switched."
  get_provider_api_key() → env o store, con .strip()
  resolve_provider_api_key(proveedor, fallback="") → prioriza env/store, luego fallback
  persist_provider_api_key() → escribe SOLO en el dict en memoria, nunca en os.environ ni en disco
  → 0 literales de clave. 0 escritura a disco. Diseño correcto.

$ grep -rnE "api_key\s*=\s*[\"'][a-zA-Z0-9]" --include="*.py" . | grep -vE "getenv|environ|None|\"\"|''"
  interpreter_layer.py:17,23   api_key="gsk-..."     ← placeholder truncado en un docstring de ejemplo
  langchain_workflows.py:151   api_key="ollama"      ← convención de Ollama (no es secreto)
  massive-ui-ng/.../llm_chat.py:53  api_key = "ollama"  # Ollama does not require a key.
  tests/test_multilayer_engine_coverage.py:140  api_key="fake"
  → 0 secretos reales

test-zapier.txt:
  $ ls -a | grep -iE "zapier"                 → (vacío)
  $ find . -name "test-*.txt" -o -name "test-*.json"  → (vacío)
  $ git ls-files | grep -i zapier             → (vacío)
  Contexto histórico: issue/PR #81 "Remove .codebuff folder containing exposed Zapier MCP token"
  gitleaks.toml:11-15 documenta la remediación:
    "the former EXCEPTION 1 (SEC-01 historical Zapier token) was removed on 2026-08-22 after
     the token was revoked by the owner and the secret was purged from the public git history
     via `git filter-repo` (fresh-clone scan verified clean)."
```

**Impacto.** Positivo. La respuesta al item sospechoso del brief: `test-zapier.txt` **no existe** y el incidente de secreto asociado (token MCP de Zapier en `.codebuff/`) fue revocado, purgado del historial con `git filter-repo` y documentado. El `.gitignore` protege `.codebuff/` (línea 41, "may contain secrets").

**Acción sugerida.** Verificar de forma independiente el purgado del historial (un `gitleaks detect --log-opts="--all"` sobre un clone completo, no shallow) — el clone de auditoría es shallow (1 commit) y no puede confirmarlo.

**Esfuerzo:** XS (verificación)

---

**ID:** D5-019
**Severidad:** 🟡
**Dominio:** Configuración
**Título:** Typo en `.gitignore`: `repomack-output*.xml` en lugar de `repomix-output*.xml` — el bundle generado NO está ignorado
**Ubicación:** `.gitignore:34-35` · `repomix.config.json:6`
**Estado:** **[CONFIRMADO]** · **[CONOCIDO PREVIO — item "repomix-output.xml presente en el árbol"]**

**Evidencia.**
```
.gitignore:34  # HEADROOM/Repomack
.gitignore:35  repomack-output*.xml          ← "repomack", no "repomix"

repomix.config.json:6   "filePath": "repomix-output.xml"
.repomixignore:2        repomix-output*      ← aquí SÍ está bien escrito, pero .repomixignore
                                               solo afecta a la herramienta, no a git

Estado actual del árbol:
  $ git ls-files | grep -i repomix  → .repomixignore, repomix-instruction.md, repomix.config.json
  $ ls -a | grep repomix-output     → (no existe)
```

**Impacto.** El bundle **no está commiteado hoy** (item del brief parcialmente RESUELTO), pero la salvaguarda está rota: el primer desarrollador que ejecute `npx repomix --config repomix.config.json` (exactamente lo que indica el Paso 0 del brief de auditoría) generará un `repomix-output.xml` de varios MB que `git status` mostrará como *untracked* y que un `git add .` commiteará. Además el comentario de sección dice "HEADROOM/Repomack", doble errata.

**Acción sugerida.** Corregir a `repomix-output*.xml` y el comentario a `# Repomix`.

**Esfuerzo:** XS

---

**ID:** D5-020
**Severidad:** 🟡
**Dominio:** Configuración
**Título:** Las reglas de `.gitignore` para binarios y artefactos son ineficaces porque los archivos ya están trackeados
**Ubicación:** `.gitignore:63-72` · 9 archivos `.pt` · 30+ `reports/*.json` · `experiments/*.csv`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
.gitignore declara:
   models/**/*.pt · models/**/*.pth · models/**/checkpoints/ · *.pt · *.pth
   experiments/**/results.json · experiments/**/metrics.json · reports/**/*.json

$ git ls-files | grep "\.pt$"
models/cfc_calibrated/cfc_residual.pt
models/cfc_calibrated/checkpoints/checkpoint_ep25.pt   …ep50 …ep75 …ep100 …ep125 …ep150 …ep175 …ep200
→ 9 archivos .pt trackeados (396 KB) pese a `*.pt` y `models/**/checkpoints/`

$ git ls-files reports | head
reports/cluster_run/metrics.json · reports/enkf_full_i3_s002/{delta,metrics_post,metrics_pre}.json
reports/enkf_pilot/… · reports/factbook_validation_US_2026-{06-26,08-13,08-16,08-17}.json
reports/real_validation/metrics.json · reports/sota_baselines/metrics.json · …
→ 30+ JSON de reports trackeados pese a `reports/**/*.json`

$ git ls-files | grep experiments
experiments/02_parameter_sweep/parameter_sweep_results.csv   (+ .json)
experiments/00_smoke/smoke_test_results.json · 01_unit/invariant_validation_results.json · 03_calibration/…
```
`.gitignore` sólo afecta a archivos *untracked*; estos se commitearon antes de añadir las reglas.

**Impacto.** El `.gitignore` da una falsa sensación de higiene. Artefactos de ejecución versionados producen diffs ruidosos y conflictos de merge en archivos binarios. Y la regla `*.pt` bloquea **futuros** pesos, lo que es precisamente la causa de D4-001 (los modelos que faltan no se pueden commitear sin `-f`).

**Acción sugerida.** Decidir por categoría: (a) pesos de modelo → Git LFS con `.gitattributes` explícito; (b) reports de validación → o se versionan como evidencia científica (y entonces eliminar la regla de ignore) o se mueven a artifacts de CI; (c) resultados de experiments → lo mismo. Hoy el repo hace las dos cosas a la vez.

**Esfuerzo:** M

---

**ID:** D5-021
**Severidad:** 🟡
**Dominio:** Configuración
**Título:** Estado runtime commiteado: `data/ui_ng/runs.db` (SQLite, 40 KB)
**Ubicación:** `data/ui_ng/runs.db` · `massive-ui-ng/backend/app/run_store.py`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ git ls-files | grep -E "\.db$|\.sqlite"
data/ui_ng/runs.db
$ ls -la data/ui_ng/  → -rw-r--r-- 40960 runs.db

.gitignore cubre `landscapes_cache.db` y `*.log`, pero NO `*.db` ni `data/ui_ng/`.
.gitignore:26-28 sí protege data/factbook/*_raw.json y *_test.json con !.gitkeep — patrón correcto
  que no se aplicó a data/ui_ng/.
Contiene CRLF/binario según el barrido de `.gitattributes` (D7-020): git puede intentar normalizarlo.
```

**Impacto.** Estado de ejecución de la UI (posiblemente con contenidos generados por LLM) versionado en el repo. Cada corrida local produce un diff binario. Riesgo de commitear datos de usuario si la app se usa en real.

**Acción sugerida.** `git rm --cached data/ui_ng/runs.db`, añadir `data/ui_ng/` y `*.db`/`*.sqlite` a `.gitignore`, y declarar `*.db binary` en `.gitattributes`.

**Esfuerzo:** XS

---

**ID:** D5-022
**Severidad:** 🟡
**Dominio:** Configuración / Despliegue
**Título:** `.dockerignore` excluye `models/`, `datasets/` y `data/` — la imagen de producción arranca sin pesos CfC; además no excluye docs ni el segundo frontend, y tiene un glob malformado
**Ubicación:** `.dockerignore`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
# Data and models (large binary files)
data/
datasets/
results/
models/          ← la imagen NO tendrá models/cfc_calibrated/cfc_residual.pt

Consecuencia verificada por código: cfc_router.py:112-115 busca en Path("models") y
Path("models/cfc_calibrated"); al no existir, _try_load devuelve None para los 6 modelos
→ status = {regime_selector: False, …} → el fast path neuronal queda desactivado en el contenedor,
en silencio (solo un log.debug por modelo).

# CSV data files
*.csv            ← refuerza la exclusión de datasets/*/timeseries.csv

NO excluidos (sí deberían):
  docs/ (63 archivos) · .github/ (17) · experiments/ (27) · reports/ (32) · *.md de root (21, ~250 KB)
  massive-ui-ng/frontend/node_modules/  ← SOLO se excluye frontend/node_modules/
  site/ · .repomixignore · repomix* · CLAUDE.md · AGENTS.md · gitleaks.toml · mypy.ini

Glob malformado (última línea del archivo):
  *.env.*\.backup      ← la barra invertida es literal en un .dockerignore; no coincide con nada
    (probablemente se quiso decir `.env.*.backup`, que .gitignore:2 sí cubre como `.env.backup`)
```

**Impacto.** Doble: (a) **funcional** — la imagen Docker publicitada como producción no tiene la capacidad CfC que el README destaca como diferenciador; (b) **de build** — el contexto incluye cientos de archivos irrelevantes, y si `massive-ui-ng/frontend/node_modules/` existe localmente se copia entero al daemon.

**Acción sugerida.** Decidir si los pesos van en la imagen (entonces incluir `models/cfc_calibrated/*.pt` explícitamente) o se montan en runtime (entonces documentarlo en `docker-compose.yml` como volumen y en `docs/DOCKER.md`). Excluir `docs/`, `.github/`, `experiments/`, `reports/`, `*.md`, `site/`, `massive-ui-ng/frontend/node_modules/`. Corregir el glob final.

**Esfuerzo:** S

---

**ID:** D5-023
**Severidad:** 🟡
**Dominio:** Seguridad
**Título:** `gitleaks.toml` permite 14 stopwords, incluida la clave de desarrollo activa
**Ubicación:** `gitleaks.toml:20-45`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```toml
[[allowlists]]
description = "MASSIVE non-secret fixture values (documented dev fallback key, test keys, .env.example placeholders)"
stopwords = [
  "dev-secret-key",              ← clave ACTIVA en development (D5-013), no un fixture
  "default-secret-key",          ← "present in git history (pre-2026-08 commits)"
  "replace_with_generated_key",
  "testkey111", "badkey00", "fake-llm-key", "live-secret", "secret-123",
  "change-me-in-production", "ci-test-key",
  "your_groq_api_key_here", "your_openai_api_key_here", "your_openrouter_api_key_here",
  "your_twitter_bearer_token_here", "your_reddit_client_id_here", "your_reddit_client_secret_here",
]
```
El archivo está bien documentado y su sección EXCEPTION 1 registra la remediación del token de Zapier (D5-018). La lista está ordenada por justificación.

**Impacto.** `stopwords` en gitleaks suprime cualquier hallazgo que *contenga* la cadena, no sólo coincidencias exactas. `"live-secret"` y `"secret-123"` son suficientemente genéricas como para enmascarar un hallazgo real. Permitir `dev-secret-key` es aceptable mientras sea sólo un fallback de desarrollo, pero se vuelve peligroso si D5-013 no se corrige.

**Acción sugerida.** Reemplazar `stopwords` por `regexes` anclados (p. ej. `^dev-secret-key$`) y por `paths` (permitir sólo en `tests/`, `*.example`, `docs/`). Resolver D5-013 primero.

**Esfuerzo:** S

---

**ID:** D5-024
**Severidad:** 🟡
**Dominio:** Seguridad / Gobernanza
**Título:** Faltan `SECURITY.md`, `dependabot.yml`, `CODEOWNERS` y `.github/ISSUE_TEMPLATE/`
**Ubicación:** `.github/`
**Estado:** **[CONFIRMADO]** · punto 8.3 del brief

**Evidencia.**
```
$ ls .github/ISSUE_TEMPLATE           → No such file or directory
$ ls SECURITY.md .github/SECURITY.md  → No such file or directory
$ ls .github/CODEOWNERS               → No such file or directory
$ ls .github/dependabot.yml           → No such file or directory

$ find .github -type f
.github/Agent_Copilot2                      ← archivo sin extensión, malformado (D6-016)
.github/CI_CD_BEST_PRACTICES.md
.github/PULL_REQUEST_TEMPLATE.md            ← ✓ existe
.github/agents/my-agent.agent.md            ← envuelto en code fence (D6-017)
.github/workflows/*.yml                     ← 13 workflows
```
Existe en cambio infraestructura de seguridad técnica: `secret_scan.yml` (gitleaks), `gitleaks.toml`, `docs/security/threat-model.md`, `docs/security/secrets-and-configuration.md`, `scripts/security_audit.sh`.

**Impacto.** Sin `SECURITY.md` no hay canal privado para reportar vulnerabilidades — irónico dado que el repo tiene un modelo de amenazas documentado y un incidente de secreto histórico (#81). Sin `dependabot.yml`, las 30 dependencias sin pin (D5-003) no reciben avisos de seguridad. Sin issue templates, 90 issues cerrados con formatos heterogéneos.

**Acción sugerida.** Añadir los cuatro. `SECURITY.md` puede referenciar `docs/security/threat-model.md` que ya existe.

**Esfuerzo:** S

---

### DOMINIO 6 — DOCUMENTACIÓN

---

**ID:** D6-001
**Severidad:** 🔴
**Dominio:** Documentación
**Título:** La tabla "Quality & production posture" del README contiene 4 afirmaciones falsas verificables
**Ubicación:** `README.md:242-251`
**Estado:** **[CONFIRMADO]**

**Evidencia.** Línea por línea contra la medición:

| Afirmación del README | Medición real | Veredicto |
|---|---|---|
| `Test suite \| **679 tests, ~32 s**` | 681 recolectados · **669 passed · 12 failed** · ~28 s | ❌ falso (12 fallos) |
| `Coverage \| 68 % branch (scope: engines + services + backend)` | **59.62 %** branch, 144 archivos, scope `--cov=.` | ❌ sobreestimado 8.4 pts |
| `Static quality \| ruff + black + mypy (gradual slice) **green in CI**` | ruff exit 1 (28) · black 30 archivos · mypy 36 errores en el slice, 198 repo-wide | ❌ los tres rojos |
| `CI \| 13 CI workflows per PR: … secret scan, **semgrep**, PVU benchmark` | 13 archivos de workflow ✓, pero `grep -rni semgrep .github/` → **0 resultados**; `pvu-validation.yml` sólo corre en `pull_request`/`workflow_dispatch`, no en push | ❌ semgrep no existe |
| `Security \| … n_agents cap (prevents 8 TB OOM), max_intentos clamp (prevents LLM DoS)` | esos límites no existen en el backend canónico (D5-001) | ❌ falso para `/v1/*` |
| `Security \| … no secrets in tree` | confirmado: 0 secretos | ✓ |
| `Observability \| /metrics Prometheus … X-Request-ID … degraded-mode readiness` | confirmado en vivo: `/metrics` 200, `X-Request-ID` y `traceparent` en logs, `/ready` → `mode: degraded` | ✓ |
| `Backup \| scripts/backup_*.sh` · `DR Plan \| docs/disaster_recovery_plan.md` · `Runbooks` | los 4 scripts y los 3 runbooks existen | ✓ |

Agravante: el commit inmediatamente anterior a HEAD es `e2900ab0 docs: Fix test count consistency in README`, y la inconsistencia persiste (D6-002).

**Impacto.** Es la primera pantalla que ve cualquier evaluador. Cuatro de las ocho filas de la tabla de calidad son falsas, y las falsas son precisamente las que un revisor técnico comprobaría primero. Destruye la credibilidad de las afirmaciones que sí son ciertas (que son varias).

**Acción sugerida.** Generar la tabla desde CI: un job que escriba `tests/coverage/report.json` con (nº tests, passed, failed, coverage %, ruff/black/mypy exit codes) y un script que inyecte esos valores en el README entre marcadores `<!-- QUALITY:START -->`/`<!-- QUALITY:END -->`. Retirar "semgrep" o añadir semgrep.

**Esfuerzo:** M

---

**ID:** D6-002
**Severidad:** 🟠
**Dominio:** Documentación
**Título:** `README.md` y `README_ES.md` discrepan en cifras y en enlaces pese a tener la misma estructura
**Ubicación:** `README.md` (337 líneas) · `README_ES.md` (297 líneas)
**Estado:** **[CONFIRMADO]** · punto 6.2 del brief

**Evidencia.**
```
Estructura: AMBOS tienen las mismas 11 secciones en el mismo orden ✓
  EN: Why MASSIVE is different · 🚀 Quick start · 🏗 Architecture · 📡 HTTP API ·
      🤖 The LLM layer · 📊 Benchmarks · 🧪 Quality & production posture ·
      📁 Repository layout · 📚 Documentation · 🤝 Contributing · 📜 License
  ES: Qué hace diferente a MASSIVE · 🚀 Inicio rápido · 🏗 Arquitectura · 📡 API HTTP · … (idéntico)

Discrepancias de contenido:
  README.md:244     | Test suite | **679 tests, ~32 s** |
  README_ES.md:220  | Suite de tests | **530 tests, ~38 s**, sin exclusiones |
      → 679 vs 530. Ambos distintos del real (681/669). "sin exclusiones" es falso (2 skipif)

  README.md:247     | CI | **13 CI workflows** per PR: … |
  README_ES.md:223  | CI | **16 checks** por PR: … |
      → 13 vs 16

  README.md:14      [![Rust: optional PoC](…Rust-optional_compilable-orange)](rust_core/)
  README_ES.md:14   [![Rust: opcional](…Rust-aceleración_opcional-orange)](Cargo.toml)
      → distinto destino del enlace; el de ES apunta al Cargo.toml root, el de EN al directorio

  Diferencia de longitud: 337 vs 297 líneas (40 líneas / 12 % más en EN)

Rename a MASSIVE (junio 2026, issues #28/#29/#40/#51): SÍ está reflejado en README_ES.md
  — no quedan referencias a "BeyondSight" en ninguno de los dos. ✓ item del brief RESUELTO
```

**Impacto.** Un lector hispanohablante recibe cifras distintas (y más bajas) que uno anglófono. La divergencia crece con cada commit porque no hay mecanismo de sincronización.

**Acción sugerida.** Extraer las cifras a un único `docs/quality-metrics.json` generado por CI (D6-001) y que ambos README las referencien; añadir un check de CI que compare los encabezados de sección de ambos archivos.

**Esfuerzo:** S

---

**ID:** D6-003
**Severidad:** 🟠
**Dominio:** Documentación
**Título:** 21 archivos Markdown de planning/reportes/agentes en la raíz (≈250 KB)
**Ubicación:** root
**Estado:** **[CONFIRMADO]** · **[CONOCIDO PREVIO — el patrón persiste con otros nombres]**

**Evidencia.** Inventario y clasificación propuesta por destino:
```
$ ls *.md | wc -l → 21      (total repo: 113 .md, de los cuales 60 en docs/)

┌─ DEBE QUEDAR EN ROOT (8) ────────────────────────────────────────────────┐
 README.md (18 KB) README_ES.md (15 KB) CHANGELOG.md (8.7 KB) LICENSE
 CONTRIBUTING.md (2.7 KB) CODE_OF_CONDUCT.md (1.2 KB)
 CLAUDE.md (3.7 KB) AGENTS.md (14 KB)   ← los 2 últimos: consolidar, ver D6-015
└──────────────────────────────────────────────────────────────────────────┘

┌─ MOVER A docs/reports/ (5 reportes de auditoría previos, 72 KB) ─────────┐
 REPORT_AUDIT.md        8.3 KB  Fecha: 2026-09-14   (reciente, vigente)
 REPORT_BUGS.md        11.6 KB  Fecha: 2025-07-09   ← fecha imposible (D6-006)
 REPORT_LEGACY.md      10.4 KB  Fecha: 2026-07-17
 REPORT_OPTIMIZATION.md 15.2 KB Fecha: 2025-07-24   ← fecha imposible + Numba eliminado (D6-007)
 REPORT_STRUCTURE.md   26.7 KB  Fecha: 2025-09-14   ← fecha imposible
└──────────────────────────────────────────────────────────────────────────┘

┌─ MOVER A docs/architecture/ o docs/plans/ (4, 109 KB) ───────────────────┐
 MASSIVE_SYSTEM_MAP.md              36.1 KB  mapa autoritativo — contiene fantasmas (D6-008)
 PRODUCTION_ARCHITECTURE_SPEC.md    28.9 KB  spec de producción
 MASSIVE_REACTIVE_COHERENCE_PLAN.md 26.4 KB  plan de trabajo — referencia .pt ausentes (D4-001)
 PLAN_INTEGRACION_UI_NG.md          11.3 KB  plan para eliminar Streamlit… ya eliminado (D1-006)
└──────────────────────────────────────────────────────────────────────────┘

┌─ MOVER A docs/operations/ (2) ───────────────────────────────────────────┐
 MASSIVE_PRODUCTION_SIGNOFF.md  6.6 KB   RESTART_CHECKLIST.md  7.1 KB
└──────────────────────────────────────────────────────────────────────────┘

┌─ MOVER A docs/research/ (2) ─────────────────────────────────────────────┐
 calibration_log.md  9.5 KB  ← referenciado por el README como evidencia del 50 % de mejora
 progress.md         0.9 KB  ← "operator map", dice "Last aligned: post FASE 5 closeout"
└──────────────────────────────────────────────────────────────────────────┘

┌─ EVALUAR (1) ────────────────────────────────────────────────────────────┐
 repomix-instruction.md 1.1 KB  ← lo consume repomix.config.json:instructionFilePath; DEBE quedar en root
└──────────────────────────────────────────────────────────────────────────┘

Comparación con el contexto previo del brief:
  FACTBOOK_INTEGRATION_PLAN.md      → MOVIDO a docs/ ✓
  FACTBOOK_INTEGRATION_COMPLETE.md  → MOVIDO a docs/ ✓
  FACTBOOK_QUICKSTART.md            → MOVIDO a docs/ ✓
  FACTBOOK_SUMMARY.md               → MOVIDO a docs/ ✓
  REFACTOR_SIMULATOR_PLAN.md        → ELIMINADO ✓
  REPAIR_OPTIMIZATION_PLAN.md       → ELIMINADO ✓
  SIMULATOR_REFACTOR_PLAN.md        → ELIMINADO ✓
  SECURITY_FIX.md                   → ELIMINADO ✓
  progress.md                       → SIGUE EN ROOT ✗
  → El patrón se corrigió una vez y se volvió a acumular: 13 archivos nuevos de planning/reportes.
```

**Impacto.** La primera impresión del repo es la de un directorio de trabajo personal, no la de un proyecto open source. 250 KB de planes cerrados y reportes de auditoría anteriores compiten visualmente con el README. Cuatro de ellos contienen rutas absolutas de la máquina del autor (D6-005) y tres tienen fechas imposibles (D6-006).

**Acción sugerida.** `git mv` según la clasificación; dejar en root sólo README, README_ES, CHANGELOG, LICENSE, CONTRIBUTING, CODE_OF_CONDUCT y un único AGENTS.md. Añadir la regla "ningún `.md` de planning en root" a `CONTRIBUTING.md`.

**Esfuerzo:** S

---

**ID:** D6-004
**Severidad:** 🟠
**Dominio:** Documentación
**Título:** 356 referencias a rutas inexistentes repartidas en 114 archivos Markdown
**Ubicación:** repo completo (docs)
**Estado:** **[CONFIRMADO]**

**Evidencia.** Extracción regex de tokens `` `ruta.ext` `` en los 114 `.md`, resueltos contra el árbol:
```
Markdown files scanned: 114
Distinct referenced-but-MISSING paths: 186
Total broken references: 356

Casos de alto impacto (excluyendo falsos positivos de nombres genéricos como `__init__.py`):
  22 × app.py                                  → CHANGELOG.md, PLAN_INTEGRACION_UI_NG.md,
                                                 PRODUCTION_ARCHITECTURE_SPEC.md, y 12 archivos de
                                                 docs/architecture/*  (D1-006)
   7 × utility_logic.py                        → REPORT_STRUCTURE.md (ruta root; real: massive/core/)
   6 × intervention_optimizer.py               → REPORT_STRUCTURE.md (ruta root; real: massive/core/)
   4 × extended_models.py                      → REPORT_STRUCTURE.md (ruta root; real: massive/core/)
   3 × backend/app/services/llm_orchestrator.py→ docs/architecture/current-state.md
                                                 (ruta real: services/llm_orchestrator.py)
   3 × agent_initialization.py                 → docs/FACTBOOK_INTEGRATION_PLAN.md   (módulo fantasma)
   3 × energy_engine_pure.py                   → docs/FACTBOOK_INTEGRATION_PLAN.md   (módulo fantasma)
   3 × optimizer.py                            → docs/FACTBOOK_INTEGRATION_PLAN.md   (módulo fantasma)
   3 × README.backup.md                        → CHANGELOG.md
   2 × models/cfc_calibrated/cfc_lambda_corrector.pt → MASSIVE_REACTIVE_COHERENCE_PLAN.md (D4-001)
   2 × models/cfc_calibrated/cfc_landscape.pt        → idem
   2 × cfc_temperature.pt / cfc_landscape.pt         → MASSIVE_REACTIVE_COHERENCE_PLAN.md
   2 × .codebuff/config.json                   → CHANGELOG.md (carpeta purgada, D5-018)
   2 × gen_report.py                           → REPORT_LEGACY.md
   1 × massive/cli.py                          → PRODUCTION_ARCHITECTURE_SPEC.md (real: massive/cli/main.py)
   4 × test_simulator.py / test_multilayer.py / test_social_architect.py / test_forecast.py
        → REPORT_STRUCTURE.md las ubica en rutas que ya no corresponden
```

**Impacto.** La documentación arquitectónica —que es abundante y detallada— no se puede seguir. Un contribuyente que intente navegar desde `docs/architecture/current-state.md` al orquestador LLM llega a una ruta que no existe. Los 4 módulos fantasma de `FACTBOOK_INTEGRATION_PLAN.md` sugieren que un plan se documentó antes de implementarse y nunca se reconcilió.

**Acción sugerida.** Pasada de reconciliación documento↔árbol con un script (el mismo usado en esta auditoría) integrado en CI como check no bloqueante; marcar los documentos históricos como `> ⚠️ Documento histórico — refleja el estado en {fecha}` en lugar de corregirlos uno a uno.

**Esfuerzo:** L

---

**ID:** D6-005
**Severidad:** 🟠
**Dominio:** Documentación
**Título:** Rutas absolutas de la máquina personal del autor incrustadas en la documentación pública (16 ocurrencias)
**Ubicación:** `AGENTS.md` · `REPORT_AUDIT.md` · `REPORT_LEGACY.md` · `REPORT_STRUCTURE.md` · `RESTART_CHECKLIST.md` · `MASSIVE_REACTIVE_COHERENCE_PLAN.md` · `PLAN_INTEGRACION_UI_NG.md` · `docs/FACTBOOK_QUICKSTART.md` · `docs/architecture/validation_baseline.md`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
AGENTS.md:97    Output artifacts: `/home/adlg/MASSIVE/models/cfc_calibrated/{cfc_residual.pt, config.json, …}`
                Calibration doc: `/home/adlg/MASSIVE/calibration_log.md`
AGENTS.md:103   The scalability benchmark script is at `/home/adlg/MASSIVE/benchmark_scalability.py`:
AGENTS.md:122   cd /home/adlg/MASSIVE && python3 benchmark_scalability.py
AGENTS.md:142   Script: `/home/adlg/MASSIVE/benchmark_scalability.py` (reusable, self-contained)
MASSIVE_REACTIVE_COHERENCE_PLAN.md:172  cd /home/adlg/Escritorio/Proyectos/MASSIVE
PLAN_INTEGRACION_UI_NG.md:16,304,368    # Desde /home/adlg/MASSIVE
REPORT_AUDIT.md:6      > **Ruta base:** `/home/adlg/Escritorio/Proyectos/MASSIVE`
REPORT_LEGACY.md:4     **Projecto:** /home/adlg/Escritorio/Proyectos/MASSIVE
REPORT_STRUCTURE.md:4  > Fecha: 2025-09-14 | Path: `/home/adlg/Escritorio/Proyectos/MASSIVE`
RESTART_CHECKLIST.md:23,181   cd /home/adlg/Escritorio/Proyectos/MASSIVE
docs/FACTBOOK_QUICKSTART.md:53          cd /home/adlg/MASSIVE/data/factbook
docs/architecture/validation_baseline.md:28  /home/adlg/Escritorio/Proyectos/MASSIVE
→ 16 ocurrencias · 2 rutas base distintas · 9 archivos
```

**Impacto.** (a) Los comandos copiados no funcionan para nadie más; (b) `AGENTS.md` es el archivo que leen los agentes de IA — un agente que siga esas instrucciones buscará rutas inexistentes; (c) filtra el nombre de usuario del sistema y la estructura de directorios del autor (menor, pero es información innecesariamente pública); (d) dos rutas base distintas (`/home/adlg/MASSIVE` y `/home/adlg/Escritorio/Proyectos/MASSIVE`) indican que los documentos se escribieron en épocas/ubicaciones diferentes y nunca se normalizaron.

**Acción sugerida.** Reemplazar por rutas relativas al repo (`cd MASSIVE`, `./benchmark_scalability.py`) o por `$REPO_ROOT` con una línea de setup. Añadir un check de CI que rechace `/home/` y `/Users/` en archivos trackeados.

**Esfuerzo:** S

---

**ID:** D6-006
**Severidad:** 🟠
**Dominio:** Documentación
**Título:** Tres reportes de root tienen fechas anteriores a la creación del repositorio
**Ubicación:** `REPORT_STRUCTURE.md:4` · `REPORT_BUGS.md:3` · `REPORT_OPTIMIZATION.md:3`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
Repo creado (gh api repos/Adlgr87/MASSIVE): 2026-04-01T04:33:13Z

REPORT_STRUCTURE.md:4     > Fecha: 2025-09-14 | Path: /home/adlg/Escritorio/Proyectos/MASSIVE
REPORT_BUGS.md:3          **Fecha:** 2025-07-09
REPORT_OPTIMIZATION.md:3  **Fecha:** 2025-07-24
  ← las tres son 7-9 meses ANTERIORES a la creación del repo

Fechas coherentes:
REPORT_AUDIT.md:5         **Fecha:** 2026-09-14   ✓
REPORT_LEGACY.md:4        **Fecha:** 2026-07-17   ✓
```
Hipótesis plausible: errata `2025`↔`2026` al escribir, o documentos heredados de un proyecto predecesor (BeyondSight, renombrado en los issues #28/#29).

**Impacto.** Imposible saber si un reporte describe el estado actual o uno de hace un año. `REPORT_OPTIMIZATION.md` es el caso más dañino (ver D6-007): describe una arquitectura que ya no existe y su fecha ambigua no permite descartarlo.

**Acción sugerida.** Corregir las fechas o, mejor, añadir a cada reporte un banner de estado: `> Estado: HISTÓRICO — describe el commit {sha} del {fecha}. No refleja main actual.`

**Esfuerzo:** XS

---

**ID:** D6-007
**Severidad:** 🟠
**Dominio:** Documentación
**Título:** `REPORT_OPTIMIZATION.md` describe una arquitectura Numba/JIT que fue eliminada del código
**Ubicación:** `REPORT_OPTIMIZATION.md` (15 KB) · commits `2cc025e1`, `4b1284af`, `fefc1033`, `f6068106`, `d20e5458`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
REPORT_OPTIMIZATION.md:11-16
  "El proyecto MASSIVE tiene tres problemas de rendimiento críticos …
   1. **Engine Python fallback sin Numba** — 10× más lento que la ruta JIT compilada
   2. **Network inference con loops O(N²)** — inusable para N > 100 agentes
   3. **Historial de estado completo en memoria** — O(steps × N × K) bytes acumulados"

Historial reciente de commits (vía gh api):
  d20e5458 2026-09-15T03:04:48Z  ci: Remove numba from CI workflow (no longer a dependency)
  f6068106 2026-09-15T02:51:24Z  fix: Resolve lint errors from Numba removal cleanup
  fefc1033 2026-09-15T00:31:55Z  docs: Fix remaining JIT reference in OPTIMIZATION_STATUS.md
  2cc025e1 2026-09-15T00:31:40Z  docs: Remove obsolete Numba/JIT references throughout codebase
  4b1284af 2026-09-15T00:28:28Z  docs: Remove obsolete references to Numba, UI-NG naming

$ grep -rn "numba" --include="*.py" .      → 0
$ grep -rn "numba" requirements.txt pyproject.toml → 0
```
Es decir: el 2026-09-15 a las 00:31 se limpiaron las referencias a Numba de los docs, y a las 03:51 se hizo un commit de "humanización" — pero `REPORT_OPTIMIZATION.md` conserva intacta su premisa #1, que ya no aplica.

**Impacto.** El documento de referencia sobre optimización de rendimiento del proyecto identifica como **crítico nº 1** un problema que no existe, y omite los reales (los 6 cálculos descartados de D2-006/D9-004, el `build_narrative` F-57, la ausencia de CI de Rust). Un agente o contribuyente que lo siga como guía invertirá esfuerzo en restaurar Numba.

**Acción sugerida.** Marcar el reporte como histórico con banner, o reescribirlo contra el estado actual usando los datos de esta auditoría (D9-004, D2-011, D9-005). Los puntos 2 y 3 siguen siendo válidos y deberían conservarse.

**Esfuerzo:** S

---

**ID:** D6-008
**Severidad:** 🟠
**Dominio:** Documentación
**Título:** `MASSIVE_SYSTEM_MAP.md` (36 KB, el mapa autoritativo) referencia 11 archivos inexistentes y componentes retirados
**Ubicación:** `MASSIVE_SYSTEM_MAP.md`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ (extracción de los 110 nombres de archivo mencionados, resueltos contra el árbol)
MASSIVE_SYSTEM_MAP.md menciona 110 filenames; 11 NO existen en ninguna parte del repo:
   test_mamba_engine.py      ← módulo Mamba eliminado (D1-005)
   micro_ui.py               ← UI micro retirada con Streamlit (D1-006)
   factbook_test.json        ← .gitignore lo excluye explícitamente (data/factbook/*_test.json)
   App.ts                    ← el real es App.tsx
   build.yml · compose.yml · single.yml   ← nombres truncados de docker-compose.single.yml etc.
   generated.ts              ← nombre truncado de api.generated.ts
   13.json · 26.json · tor.py             ← artefactos del parseo de tablas

Componentes retirados que el mapa sigue describiendo como activos:
   MASSIVE_SYSTEM_MAP.md:145  │  └── supervisord.conf — api (appuser) + streamlit (appuser) + nginx (root)
     → supervisord.conf real gestiona SOLO nginx + uvicorn; el bloque streamlit fue eliminado
       con el comentario "FIX (CRIT-2): Streamlit UI removed (OPS-02)"
   MASSIVE_SYSTEM_MAP.md:464  | streamlit | 8501 | (runtime) | UI micro-MASSIVE |
     → la tabla de puertos sigue listando el 8501
```

**Impacto.** Es el documento de mayor autoridad del repo por tamaño y nombre ("SYSTEM MAP"). Un agente de IA que lo lea para orientarse —que es exactamente el propósito declarado de `repomix.config.json:headerText`: *"Read CLAUDE.md first … then use README.md"*— construirá un modelo mental con módulos y puertos que no existen.

**Acción sugerida.** Regenerar el mapa desde el árbol real con un script (`scripts/gen_system_map.py`) en lugar de mantenerlo a mano, o reducirlo a un grafo Mermaid de componentes con enlaces a los directorios (que sí son estables) en lugar de listar archivos.

**Esfuerzo:** M

---

**ID:** D6-009
**Severidad:** 🟠
**Dominio:** Documentación
**Título:** 35 de 60 documentos de `docs/` son huérfanos del nav de MkDocs — invisibles en el sitio publicado
**Ubicación:** `mkdocs.yml:19-49` · `docs/`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
docs .md files: 60 · en nav: 25 · HUÉRFANOS: 35 (58 %)

Huérfanos de primer nivel (documentos operativos clave):
   DOCKER.md · ENV_VARS.md · OBSERVABILITY_AND_SECURITY.md · NAMING_CONVENTIONS.md
   OPTIMIZATION_STATUS.md · REMEDIATION_STATUS.md · BACKLOG_POST_WORKFLOW.md
   LLM_PROMPTS.md · MASSIVE_LLM_INTERFACE.md · backup_restore.md
   disaster_recovery_plan.md · performance_report.md
   math_physics_extension_plan_ES.md · rust_core_plan_ES.md

Huérfanos de docs/architecture/ (17 de 19 — solo current-state.md y target-state.md están en nav):
   backward_compatibility_aliases.md · checkpoint_status.md · compatibility_map.md
   config_consumers_map.md · consolidation_plan.md · consolidation_vision.md
   consolidation_workflow.md · contracts_and_boundaries.md · domain_ownership.md
   first_execution_slices.md · module_inventory.md · safety_protocol.md
   sensitive_zones.md · simulation_history_contract.md · simulator_dependency_map.md
   simulator_multilayer_boundary.md · validation_baseline.md

Otros: cards/BENCHMARK.md · cards/REPRODUCIBILITY.md
       development_history/micro_massive_workflow_2026-05-17.md
       research/enkf_level_vs_slope.md

Verificación positiva: NAV entries pointing to MISSING files: [] — el nav no tiene enlaces rotos
```
Agravante: `progress.md:19` y varios reportes mandan al lector a `docs/architecture/sensitive_zones.md` *"before editing core engines"* — documento huérfano del sitio.

**Impacto.** El 58 % del conocimiento documentado no es navegable desde el sitio publicado en https://adlgr87.github.io/MASSIVE/ (que `pyproject.toml` declara como `Documentation` oficial). Sólo es alcanzable por búsqueda o URL directa. `docs/architecture/` es precisamente el material que resuelve D3-010/D3-012 (propiedad de dominio) y está invisible.

**Acción sugerida.** Completar el nav con las secciones `Operations` (DOCKER, ENV_VARS, backup_restore, disaster_recovery), `Architecture → Domain maps` (los 17 huérfanos) y `Reference` (NAMING_CONVENTIONS, MASSIVE_LLM_INTERFACE, LLM_PROMPTS). MkDocs ya pasa `--strict`, así que añadir entradas es seguro.

**Esfuerzo:** S

---

**ID:** D6-010
**Severidad:** 🟠
**Dominio:** Documentación
**Título:** La entrada "Spanish Version" del nav de MkDocs apunta a un stub de 5 líneas
**Ubicación:** `mkdocs.yml:22` → `docs/README_ES.md`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
mkdocs.yml:22   - Spanish Version: README_ES.md      ← resuelve a docs/README_ES.md

$ wc -l README_ES.md docs/README_ES.md
  297 README_ES.md          ← la versión española real, en root, NO referenciada por el nav
    5 docs/README_ES.md     ← lo que el sitio publica

$ diff -q README_ES.md docs/README_ES.md → Files differ
```

**Impacto.** El sitio de documentación oficial ofrece una "versión en español" que es un redirect/stub de 5 líneas, mientras la traducción completa de 297 líneas vive en la raíz del repo y no está enlazada. Para un proyecto bilingüe declarado (issues #5 "Soporte i18n (Inglés/Español)", #19, #33, #61) es un fallo visible de la propuesta.

**Acción sugerida.** O (a) `docs/README_ES.md` → symlink/copia generada del root en el build de MkDocs, o (b) cambiar el nav a `- Spanish Version: ../README_ES.md` con el plugin adecuado, o (c) mover `README_ES.md` a `docs/` y dejar un stub en root que enlace al sitio.

**Esfuerzo:** XS

---

**ID:** D6-011
**Severidad:** 🟡
**Dominio:** Documentación
**Título:** 24 de 245 archivos Python no tienen docstring de módulo
**Ubicación:** ver lista
**Estado:** **[CONFIRMADO]** · punto 6.3 del brief

**Evidencia.** Análisis AST (`ast.get_docstring(tree) is None`) sobre los 245 archivos:
```
Código de librería (11):
   massive/core/schemas.py            ← el "canonical" del shim deprecado de root (D3-009)
   massive/core/utils/__init__.py
   massive-ui-ng/backend/__init__.py
   massive-ui-ng/backend/app/routers/__init__.py
   massive-ui-ng/conftest.py
   micro_massive/utils/metrics.py
   schemas.py                          (root; tiene strings literales pero no un docstring válido,
                                        porque `from __future__` va antes — D3-009)
   visualizations.py
Tests (13):
   tests/__init__.py · test_data_assimilation_workflow.py · test_empirical_calibration.py
   test_forecast.py · test_integrated_dynamics.py · test_integration_llm.py
   test_optimization.py · test_rust_core_wrapper.py · test_scientific_benchmarks_and_cfc_data.py
   test_scientific_extensions.py · test_scientific_integration.py · test_scientific_report.py
   test_scientific_runner.py · test_simulator.py · test_social_architect.py · test_visualizations.py

Contraste positivo: massive_core/ — 0 archivos sin docstring (el brief preguntaba específicamente
por `grep -rL '"""' massive_core/`; el paquete está completamente documentado) ✓
```

**Impacto.** `mkdocstrings` genera la referencia de API desde los docstrings; los 11 de librería aparecen vacíos en el sitio. `visualizations.py` y `massive/core/schemas.py` son módulos públicos sin descripción.

**Acción sugerida.** Añadir docstring de una línea a los 11 de librería; habilitar la regla `D100` de pydocstyle en ruff sólo para `massive/`, `massive_core/`, `backend/`, `services/`.

**Esfuerzo:** XS

---

**ID:** D6-012
**Severidad:** 🟡
**Dominio:** Documentación
**Título:** `CHANGELOG.md` tiene dos secciones `[Unreleased]` y ninguna versión SemVer; no hay releases ni tags en GitHub
**Ubicación:** `CHANGELOG.md:6,127,154` · GitHub API
**Estado:** **[CONFIRMADO]** · puntos 6.5 y 8.1 del brief

**Evidencia.**
```
$ grep -n "^## " CHANGELOG.md
  6:  ## [Unreleased] — production-readiness hardening (2026-08-20)
127:  ## [Unreleased] (post-PR #79)
154:  ## [v1.1] — prior productionization release (PR #79)

$ gh api repos/Adlgr87/MASSIVE/releases --jq '.[].tag_name'   → (vacío)
$ gh api repos/Adlgr87/MASSIVE/tags     --jq '.[].name'       → (vacío)

Contradicciones de versión en el repo:
  pyproject.toml:7               version = "0.1.0"
  backend/app/main.py:67         FastAPI(version="1.0.0")
  api.py:26                      FastAPI(title="MASSIVE UIL API", version="1.0.0")
  GET /version (en vivo)         {"version":"1.0.0", …}
  frontend/package.json          "version": "1.0.0"
  massive-ui-ng/frontend/package.json  "version": "2.0.0"
  adapters/mutalambda/target_manifest.yaml  version: "1.0.0"
  CHANGELOG.md                   [v1.1]
  configs/llm_contract/massive_llm_contract.json  (v1.1.0 según README)
  publish.yml                    type=semver,pattern={{version}}  ← requiere un tag que no existe
```
El header dice *"This project follows Keep a Changelog semantics"* — Keep a Changelog exige versiones SemVer ordenadas.

**Impacto.** Nueve números de versión distintos para el mismo producto. `publish.yml` tiene `if: github.event_name == 'release' || startsWith(github.ref, 'refs/tags/')` para publicar a PyPI y GHCR — **condición que nunca se cumple** porque no hay tags ni releases. El pipeline de publicación está escrito pero es inalcanzable. Y `pyproject.toml` publicaría `massive 0.1.0` mientras la API se anuncia como 1.0.0.

**Acción sugerida.** Fijar una versión única (sugerida: `1.1.0`, alineada con el CHANGELOG y el contrato LLM), propagarla a `pyproject.toml`, `FastAPI(version=…)`, ambos `package.json` y el manifiesto del adapter — idealmente leída desde un único `massive/__init__.py:__version__`. Crear el tag `v1.1.0` y el release de GitHub. Colapsar las dos secciones `[Unreleased]`.

**Esfuerzo:** S

---

**ID:** D6-013
**Severidad:** 🟡
**Dominio:** Documentación
**Título:** El README indica servir MkDocs en el puerto 8000, que es el puerto de la API
**Ubicación:** `README.md:297` · `README_ES.md:262`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
README.md:297    | MkDocs site (API reference, validation, science) | `python -m mkdocs serve` → http://localhost:8000 |
README_ES.md:262 | Sitio MkDocs | `python -m mkdocs serve` → http://localhost:8000 |

README.md:52 (Quick start, 45 líneas antes)
    uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
Makefile:  api:  uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
Dockerfile: EXPOSE 80 8000   ·  nginx upstream api_backend { server 127.0.0.1:8000; }
```

**Impacto.** Un desarrollador que siga el Quick start y luego quiera ver la documentación obtendrá `Address already in use`, o peor: mkdocs fallará en silencio y el navegador mostrará la API en lugar de los docs.

**Acción sugerida.** Documentar `mkdocs serve -a localhost:8001` (o añadir un target `make docs` con el puerto correcto).

**Esfuerzo:** XS

---

**ID:** D6-014
**Severidad:** 🟡
**Dominio:** Documentación
**Título:** Recuentos de endpoints desactualizados en README y en el árbol de layout
**Ubicación:** `README.md:262` · `README.md:257-291` · `backend/app/main.py:6-19`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
README.md:262   │   ├── main.py    # FastAPI entrypoint (8 v1 endpoints + infra)
OpenAPI en vivo:  9 rutas /v1/*  (simulate, forecast, engine/energy, engine/architect,
                                  benchmarks, llm/extract, llm/wizard, llm/run_simulation + 1)
                  8 alias /api/v1/*  ·  6 infra  →  22 paths totales
El docstring de backend/app/main.py:6-19 lista 6 endpoints /v1 (omite llm/extract, llm/wizard, benchmarks)

El "Repository layout" del README (README.md:257-291) omite:
  api.py · micro_engine.py · document_intelligence.py · interpreter_layer.py ·
  programmatic_architect.py · social_connectors.py · langchain_workflows.py · uil_adapter.py ·
  cache_manager.py · visualizations.py · benchmark_scalability.py · brexit_calibration.py ·
  train_cfc_*.py · cfc_trainer.py · energy_runner.py · energy_schemas.py · micro_schemas.py ·
  schemas.py · empirical_*.py · state_compression.py · llm_credentials.py   (26 módulos root)
  metrics/ · experiments/ · reports/ · data/ · adapters/ · rust_core/ (parcial) ·
  Dockerfile.optimized · docker-compose.single.yml · nginx.conf · supervisord.conf ·
  gitleaks.toml · mypy.ini · install.sh · repomix.config.json
```

**Impacto.** El árbol de layout presenta un repo de ~20 entradas cuando tiene 106. Los 26 módulos root omitidos son precisamente los que generan la confusión arquitectónica (D3-006). Un lector no puede descubrir desde el README que existen tres motores de micro, un intérprete LLM o un conector de redes sociales.

**Acción sugerida.** Regenerar el árbol con `tree -L 2 -I 'node_modules|__pycache__|site'` y mantenerlo con un check de CI, o reducirlo deliberadamente a los 10 directorios principales con un enlace a `docs/architecture/module_inventory.md` (que existe y está huérfano, D6-009).

**Esfuerzo:** S

---

**ID:** D6-015
**Severidad:** 🟡
**Dominio:** Documentación
**Título:** Seis archivos de instrucciones para agentes/IA con propósitos solapados
**Ubicación:** `AGENTS.md` (14 KB) · `CLAUDE.md` (3.7 KB) · `.github/Agent_Copilot2` (217 líneas) · `.github/agents/my-agent.agent.md` (43 líneas) · `.github/CI_CD_BEST_PRACTICES.md` (78 líneas) · `massive-ui-ng/AGENTS.md` · `repomix-instruction.md`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
AGENTS.md            → instrucciones operativas para agentes (rutas absolutas /home/adlg, D6-005)
CLAUDE.md            → "Behavioral guidelines to reduce common LLM coding mistakes" (10 secciones genéricas)
.github/Agent_Copilot2      → definición de un agente "repo-surgeon" (malformado, D6-016)
.github/agents/my-agent.agent.md → definición de "MASSIVE-Data-Architect" (malformado, D6-017)
massive-ui-ng/AGENTS.md     → instrucciones específicas del subproyecto
repomix-instruction.md      → instrucción inyectada en el bundle de Repomix
repomix.config.json:headerText → "Read CLAUDE.md first for repository-specific development
                                  protocols, then use README.md or README_ES.md for product context."
```
Ninguno referencia a los otros salvo `repomix.config.json` → `CLAUDE.md`.

**Impacto.** Un agente de IA que aterrice en el repo recibe 4 conjuntos de instrucciones parcialmente contradictorios (por ejemplo `CLAUDE.md §3` dice *"Don't refactor things that aren't broken"* mientras `.github/Agent_Copilot2` define un agente cuyo objetivo es *"Does not stop until all issues are resolved"*). Sin jerarquía declarada.

**Acción sugerida.** Consolidar en un único `AGENTS.md` con secciones (protocolo de desarrollo · agentes especializados · contexto de producto), y hacer que `CLAUDE.md` y `repomix-instruction.md` apunten a él. Mover las definiciones de agentes a `.github/agents/*.agent.md` correctamente formateadas.

**Esfuerzo:** S

---

**ID:** D6-016
**Severidad:** 🟡
**Dominio:** Documentación / Config
**Título:** `.github/Agent_Copilot2`: archivo sin extensión, en la ubicación equivocada y con frontmatter malformado
**Ubicación:** `.github/Agent_Copilot2` (217 líneas)
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ ls .github/Agent_Copilot2        → existe, sin extensión, en la raíz de .github/
  (la convención de GitHub Copilot custom agents es .github/agents/<name>.agent.md)

Primeras 12 líneas:
  1  # Fill in the fields below to create a basic custom agent for your repository.
  2  # The Copilot CLI can be used for local testing: https://gh.io/customagents/cli
  3  # To make this agent available, merge this file into the default repository branch.
  4  # For format details, see: https://gh.io/customagents/config
  5  (línea en blanco)
  6  name: repo-surgeon
  7  description: >
  8    Full-repository audit agent. Scans, diagnoses, repairs, optimizes, tests,
  9    and verifies cross-area consistency (backend ↔ UI ↔ docs ↔ config).
 10    Does not stop until all issues are resolved or explicitly escalated.
 11  ---                      ← delimitador de CIERRE sin delimitador de APERTURA
 12  (blank)
 13  # REPO-SURGEON — Full Repository Audit, Repair & Verification Agent
```
El frontmatter YAML no tiene `---` de apertura (las líneas 1-4 son comentarios antes de `name:`), así que ningún parser lo aceptará. Además conserva el texto de plantilla de GitHub ("Fill in the fields below…").

**Impacto.** El agente `repo-surgeon` no está registrado y no es invocable. El archivo es 217 líneas de prompt muerto que sin embargo ocupa un lugar prominente en `.github/`.

**Acción sugerida.** `git mv .github/Agent_Copilot2 .github/agents/repo-surgeon.agent.md`, añadir el `---` de apertura, eliminar el comentario de plantilla.

**Esfuerzo:** XS

---

**ID:** D6-017
**Severidad:** 🟡
**Dominio:** Documentación / Config
**Título:** `.github/agents/my-agent.agent.md` está envuelto en un code fence y tiene nombre de placeholder
**Ubicación:** `.github/agents/my-agent.agent.md` (43 líneas)
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
Línea 1:   ```markdown
Línea 2:   ---
Línea 3:   name: MASSIVE-Data-Architect
Línea 4:   description: Extrae métricas empíricas de eventos históricos, papers y psicología de masas…
Línea 5:   ---
Línea 6:   (blank)
Línea 7:   # MASSIVE Data Architect
…
Línea 43:  ```
```
El documento completo —incluido el frontmatter YAML— está dentro de un bloque ```` ```markdown ````. GitHub lee el archivo crudo, así que la primera línea es `` ```markdown ```, no `---`: el frontmatter no se parsea y el agente no se registra. El nombre de archivo `my-agent` es el del scaffold por defecto y no coincide con el `name:` declarado (`MASSIVE-Data-Architect`).

El contenido en sí es de calidad: define el esquema JSON de salida, el contexto del motor (SDE de Langevin, atractores/repelentes, matriz de pagos) y una sección de verificación de entrada.

**Impacto.** Un agente útil y bien escrito está inactivo por un error de formato de 2 líneas.

**Acción sugerida.** Eliminar las líneas 1 y 43 (los fences) y renombrar a `.github/agents/massive-data-architect.agent.md`.

**Esfuerzo:** XS

---

**ID:** D6-018
**Severidad:** 🟢
**Dominio:** Documentación
**Título:** `mkdocs build --strict` compila sin errores ni warnings
**Ubicación:** `mkdocs.yml` · `docs/`
**Estado:** **[CONFIRMADO — POSITIVO]** · punto 6.4 del brief

**Evidencia.**
```
$ python -m mkdocs build --strict 2>&1 | grep -E "ERROR|WARNING|Aborted"
INFO    -  Building documentation to directory: /home/user/MASSIVE/site
(vacío — 0 ERROR, 0 WARNING)
exit=0
Verificación adicional propia: NAV entries pointing to MISSING files: []
```
El sitio usa mkdocs-material con `navigation.sections`, `navigation.expand`, `content.code.copy`, esquema `slate`, y el plugin `mkdocstrings` con `paths: [.]`.

**Impacto.** Positivo y notable: el punto 6.4 del brief ("¿hay links rotos o páginas referenciadas pero inexistentes?") no arroja hallazgos en el nav. Los 356 enlaces rotos de D6-004 son referencias *en prosa* dentro de los `.md`, no enlaces de navegación — MkDocs no los valida.

**Acción sugerida.** Añadir el plugin `mkdocs-linkcheck` o `htmlproofer` para capturar también los enlaces en prosa (D6-004).

**Esfuerzo:** S

---

**ID:** D6-019
**Severidad:** 🟢
**Dominio:** Documentación
**Título:** Existen `CHANGELOG.md`, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md` y `PULL_REQUEST_TEMPLATE.md`
**Ubicación:** root · `.github/`
**Estado:** **[CONFIRMADO — POSITIVO]** · puntos 6.5 y 8.3 del brief

**Evidencia.**
```
CHANGELOG.md            155 líneas · formato Keep a Changelog · 3 secciones (ver D6-012)
CONTRIBUTING.md          68 líneas
CODE_OF_CONDUCT.md      30 líneas
.github/PULL_REQUEST_TEMPLATE.md   ✓ presente
LICENSE                 10 262 bytes · Apache 2.0 + bloque de copyright añadido (ver D8-003)
docs/security/threat-model.md · docs/security/secrets-and-configuration.md · gitleaks.toml
scripts/security_audit.sh · .github/CI_CD_BEST_PRACTICES.md
```

**Impacto.** Positivo: la gobernanza básica de comunidad existe. Faltan los 4 archivos de D5-024.

**Acción sugerida.** Completar con `SECURITY.md`, `dependabot.yml`, `CODEOWNERS` e issue templates.

**Esfuerzo:** —

---

### DOMINIO 7 — CI/CD Y CONFIGURACIÓN

---

**ID:** D7-001
**Severidad:** 🔴
**Dominio:** CI/CD
**Título:** Los 13 workflows fallan en `main`; HEAD nunca fue validado por CI (bloqueo de facturación de GitHub Actions desde 2026-09-13)
**Ubicación:** `.github/workflows/` · GitHub Actions
**Estado:** **[CONFIRMADO]** · punto 7.1 del brief

**Evidencia.**
```
$ gh api repos/Adlgr87/MASSIVE/actions/runs?per_page=25
2026-09-15T03:51:08Z  Lint & Type Check                              main  completed/failure
2026-09-15T03:51:08Z  Docker E2E Health                              main  completed/failure
2026-09-15T03:51:08Z  Frontend Build & Test                          main  completed/failure
2026-09-15T03:51:08Z  MASSIVE CI Tests                               main  completed/failure
2026-09-15T03:51:08Z  Secret scan                                    main  completed/failure
2026-09-15T03:51:08Z  Build and deploy Python app to Azure Web App   main  completed/failure
2026-09-15T03:51:08Z  Build & Publish                                main  completed/failure
2026-09-15T03:51:08Z  Typecheck slice (non-blocking)                 main  completed/success  ← continue-on-error
2026-09-15T03:51:08Z  Benchmark Runner                               main  completed/failure
2026-09-15T03:51:08Z  Sync to Hugging Face Spaces                    main  completed/failure
2026-09-15T03:51:08Z  Validate TS Types In Sync                      main  completed/failure
2026-09-15T03:51:08Z  Docs Deploy                                    main  completed/failure

Causa (anotaciones de los check-runs, idéntica en TODOS los jobs de TODOS los runs desde 2026-09-13):
  [failure] The job was not started because your account is locked due to a billing issue.

Último run verdaderamente verde:
  2026-09-12T09:06:02Z  commit da4c7e7b  →  MASSIVE CI Tests, Azure deploy, Benchmark Runner,
                                            Secret scan, Docs Deploy, Validate TS Types (6 éxitos reales)
Commits posteriores SIN validación:
  4b1284af 2026-09-15T00:28  docs: Remove obsolete references to Numba, UI-NG naming
  2cc025e1 2026-09-15T00:31  docs: Remove obsolete Numba/JIT references throughout codebase
  fefc1033 2026-09-15T00:31  docs: Fix remaining JIT reference in OPTIMIZATION_STATUS.md
  b3a5e312 2026-09-15T02:46  fix: Resolve lint errors in metrics.py and main.py
  f6068106 2026-09-15T02:51  fix: Resolve lint errors from Numba removal cleanup
  d20e5458 2026-09-15T03:04  ci: Remove numba from CI workflow (no longer a dependency)
  e2900ab0 2026-09-15T03:25  docs: Fix test count consistency in README
  473b04a6 2026-09-15T03:51  refactor: Humanize code — remove AI-generated tells   ← HEAD

Total histórico: 1 735 workflow runs.
```

**Impacto.** **Cero señal de integración continua desde hace 3 días y 8 commits.** Dos de esos commits son `fix: Resolve lint errors` — es decir, se hicieron correcciones de lint **a ciegas**, sin poder verificarlas; de hecho ruff y black siguen rojos (D2-001, D2-002), lo que sugiere que las correcciones no fueron efectivas. El commit `ci: Remove numba from CI workflow` modificó la infraestructura de CI sin que ningún run la ejercitara. Y el commit HEAD es una refactorización masiva de comentarios/divisores sobre 245 archivos, no validada.

**Acción sugerida.** (1) Resolver el bloqueo de facturación de GitHub (fuera del alcance del código). (2) Mientras tanto, establecer un gate local obligatorio: `make lint && make typecheck && make test` documentado en `CONTRIBUTING.md` como requisito pre-push. (3) Al restaurarse Actions, no asumir que lo que había en verde el 12/09 sigue verde: ejecutar la triada completa contra HEAD (los resultados de esta auditoría son esa corrida).

**Esfuerzo:** XS (gate local) · fuera de alcance (billing)

---

**ID:** D7-002
**Severidad:** 🔴
**Dominio:** CI/CD
**Título:** Aun con Actions restaurado, el pipeline está rojo por mérito propio en 7 puntos independientes
**Ubicación:** `.github/workflows/*`
**Estado:** **[CONFIRMADO]** (reproducción local de cada paso) · **[HIPÓTESIS]** en los pasos que requieren Docker

**Evidencia.** Simulación local de cada step de CI:

| Workflow / job | Step | Reproducción local | Resultado |
|---|---|---|---|
| `lint.yml` / lint-python | `ruff check .` | 28 issues | ❌ exit 1 |
| `lint.yml` / lint-python | `black --check .` | 30 archivos | ❌ exit 1 |
| `lint.yml` / type-check | `pip install -r requirements.txt` | OK | ✓ |
| `lint.yml` / type-check | `mypy --config-file mypy.ini massive/ backend/ services/ massive_core/ \|\| true` | 36 errores | ⚠️ enmascarado por `\|\| true` |
| `lint.yml` / lint-frontend | `cd frontend && npm ci && npm run lint` | no ejecutado (sin node_modules) | ❓ |
| `pytest.yml` / core | `pip install <10 deps sin torch>` + `pytest tests/test_simulator.py …` | 21 errores de colección | ❌ |
| `pytest.yml` / api | `python -c "from api import app"` | OK con torch | ✓ |
| `pytest.yml` / full-suite | `pytest tests/ --cov… --cov-fail-under=30` | 12 failed / 669 passed | ❌ |
| `publish.yml` / lint | `ruff check . && black --check .` | ❌ | ❌ bloquea los 8 jobs restantes |
| `publish.yml` / docs | `pip install -e ".[docs]"` | `ModuleNotFoundError: maturin/puccinialin` | ❌ |
| `publish.yml` / build-wheels | `python -m build` | backend maturin sin Rust | ❌ |
| `publish.yml` / build-image | `docker build -f Dockerfile` → `RUN pip install --no-deps -e /app` | idem | ❌ **[HIPÓTESIS]** |
| `docker-e2e.yml` | `docker compose build` (→ `Dockerfile`) | idem | ❌ **[HIPÓTESIS]** |
| `docker-e2e.yml` (si se usara single.yml) | `docker build -f Dockerfile.optimized` | línea 1 no es sintaxis Docker | ❌ (D7-004) |
| `validate_ts_types.yml` | `python scripts/gen_ts_types.py && git diff --exit-code …` | 0 diff | ✓ |
| `typecheck.yml` | `python scripts/typecheck_slice.py` | 1 error, exit 1 | ⚠️ reportado `success` por `continue-on-error` |
| `benchmark.yml` / `pvu-validation.yml` | `python -m benchmarks.runner --offline` | exit 0 (con ConvergenceWarning) | ✓ (ver D4-011) |
| `mkdocs.yml` | `mkdocs build` | 0 warnings | ✓ |
| `secret_scan.yml` | gitleaks | sin secretos en HEAD | ✓ probable |
| `deploy_hf_spaces.yml` | `git push …$HF_TOKEN…` | requiere secret | ❓ |
| `main_massive.yml` | Azure deploy | requiere secrets de Azure | ❓ |

**Impacto.** Restaurar la facturación no pondrá el repo en verde: al menos 7 gates independientes fallarán. Como `publish.yml` tiene `needs: lint` en cadena, **todo** el pipeline de publicación queda bloqueado por el primer step de lint.

**Acción sugerida.** Secuencia de desbloqueo (ver el workflow de remediación, Wave 1): ruff+black → deps de CI (torch/httpx) → pesos `.pt` o skips → maturin/Rust → Dockerfiles. Cada paso es verificable localmente antes de consumir minutos de Actions.

**Esfuerzo:** L (agregado)

---

**ID:** D7-003
**Severidad:** 🔴
**Dominio:** CI/CD
**Título:** El job `core` de `pytest.yml` instala dependencias sin torch y luego ejecuta los tests que requieren torch
**Ubicación:** `.github/workflows/pytest.yml:18-28`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```yaml
  core:
    name: core
    steps:
      - name: Install core deps
        run: |
          pip install "numpy>=1.26" "scipy>=1.12" "pandas>=2.2" "networkx>=3.0" \
            "pydantic>=2.0" "pyyaml>=6.0" "python-dotenv>=1.0.1" "pytest>=8.0" \
            "plotly>=5.18" "requests>=2.31"          ← SIN torch, SIN httpx
      - name: Core tests
        run: |
          PYTHONHASHSEED=42 python -m pytest tests/test_simulator.py tests/test_massive_engine.py \
            tests/test_multilayer.py tests/test_contracts.py tests/test_optimization.py \
            tests/test_uil_mappings.py -q --tb=line
```
```
Reproducción exacta de ese entorno:
$ python -m pytest tests/test_simulator.py --collect-only
ERROR tests/test_simulator.py - AttributeError: 'CfCRouter' object has no attribute '_lambda_corrector'

Y como `full: needs: [core, scientific, api]`:
$ gh api …/runs/…/jobs → JOB: full-suite => skipped
```
Nota: el job `core` tampoco instala `python-multipart`, `fastapi` ni `uvicorn`, pero `tests/test_optimization.py` y `tests/test_uil_mappings.py` pueden requerirlos indirectamente vía `simulator`.

**Impacto.** El job diseñado para ser el más rápido y dar señal temprana es el que falla siempre, y al fallar arrastra `full-suite` a `skipped`. La matriz de CI effectively no cubre nada.

**Acción sugerida.** Extraer la instalación de dependencias a un composite action o a un `requirements-ci.txt` compartido por los 4 jobs; incluir `torch` (o arreglar D1-001/D1-002 y mantenerlo fuera deliberadamente, con un job `no-torch` que verifique el fallback).

**Esfuerzo:** S

---

**ID:** D7-004
**Severidad:** 🔴
**Dominio:** CI/CD
**Título:** `Dockerfile.optimized` tiene una línea 1 que no es sintaxis Docker válida — el archivo no puede construirse
**Ubicación:** `Dockerfile.optimized:1`
**Estado:** **[CONFIRMADO]** (por inspección de sintaxis) · **[HIPÓTESIS]** (sin `docker` en el sandbox) · **[CONOCIDO PREVIO — "dual Dockerfile", peor de lo descrito]**

**Evidencia.**
```dockerfile
$ head -3 Dockerfile.optimized
⚠️ DEPRECATED: Use Dockerfile (main) instead of Dockerfile.optimized

# Multi-stage optimized Dockerfile for MASSIVE-UIL
```
La línea 1 **no** empieza por `#`, `FROM`, `ARG` ni ninguna instrucción Docker. Es texto plano con un emoji. El parser de Docker rechazará el archivo en la primera línea (`unknown instruction: ⚠️`).

Consumidor directo:
```yaml
# docker-compose.single.yml:19-22
services:
  massive:
    build:
      context: .
      dockerfile: Dockerfile.optimized     ← apunta al archivo roto
```
Y `docker-compose.single.yml` es a su vez lo que `docker-compose.yml` declara canónico:
```yaml
# docker-compose.yml:1-3
# ⚠️ LEGACY - Use docker-compose.single.yml (canonical per README)
# This file is maintained for backward compatibility only
```

**Impacto.** `docker compose -f docker-compose.single.yml build` falla inmediatamente. Y el README no documenta en ningún lugar cuál de los dos Dockerfiles usar (búsqueda: 0 menciones de `Dockerfile.optimized` en `README.md`/`README_ES.md`; sólo `docs/DOCKER.md`, que está huérfano del nav de MkDocs — D6-009).

**Acción sugerida.** Comentar la línea (`# ⚠️ DEPRECATED: …`) como arreglo mínimo. Mejor: eliminar `Dockerfile.optimized` y `docker-compose.single.yml` si `Dockerfile` (multi-stage con nginx+supervisord) es el canónico, o viceversa. Ver D7-005.

**Esfuerzo:** XS (parche) / S (decisión y limpieza)

---

**ID:** D7-005
**Severidad:** 🟠
**Dominio:** CI/CD
**Título:** Bucle de contradicción en la ruta de despliegue: cada archivo remite al siguiente, que remite al anterior
**Ubicación:** `docker-compose.yml:1-3` · `docker-compose.single.yml:19-22` · `Dockerfile.optimized:1`
**Estado:** **[CONFIRMADO]** · **[CONOCIDO PREVIO — "dual Dockerfile sin documentación clara"]**

**Evidencia.** El grafo de referencias es circular:
```
docker-compose.yml:1        "# ⚠️ LEGACY - Use docker-compose.single.yml (canonical per README)"
        │
        ▼
docker-compose.single.yml:12  "This variant uses the optimised Dockerfile.optimized"
docker-compose.single.yml:22  dockerfile: Dockerfile.optimized
        │
        ▼
Dockerfile.optimized:1      "⚠️ DEPRECATED: Use Dockerfile (main) instead of Dockerfile.optimized"
        │
        ▼
Dockerfile                  (referido por docker-compose.yml:8, que es LEGACY)
        └──────────────────────────► vuelta al inicio

Verificación de la premisa "canonical per README":
$ grep -n "docker-compose.single\|Dockerfile.optimized" README.md README_ES.md → 0 resultados
→ el README NO declara canónico a docker-compose.single.yml. La premisa del comentario es falsa.
```

**Impacto.** No existe un camino de despliegue Docker documentado y funcional. Un operador que siga las indicaciones de los propios archivos termina en un archivo roto (D7-004) o en un archivo marcado como legacy. Las dos variantes difieren además sustancialmente: `Dockerfile` = nginx+supervisord+frontend build, expone 80 y 8000, `MASSIVE_ENV` default `development`; `Dockerfile.optimized` = uvicorn directo, expone 8000, `MASSIVE_ENV` default `production`, monta `frontend/dist` como volumen. Son dos arquitecturas de despliegue distintas, no dos optimizaciones de la misma.

**Acción sugerida.** Decidir una arquitectura de despliegue y eliminar la otra. Recomendación: mantener `Dockerfile` (multi-stage, no root, healthcheck, frontend embebido) + `docker-compose.yml`; borrar `Dockerfile.optimized` y `docker-compose.single.yml`, o moverlos a `docs/examples/` claramente marcados como alternativas. Documentar la elección en `README.md` y en `docs/DOCKER.md` (y añadir `docs/DOCKER.md` al nav, D6-009).

**Esfuerzo:** M

---

**ID:** D7-006
**Severidad:** 🟠
**Dominio:** CI/CD
**Título:** El type checking no puede fallar CI: `|| true` en `lint.yml` y `continue-on-error` en `typecheck.yml` — y hoy hay un error real que se reporta como éxito
**Ubicación:** `.github/workflows/lint.yml:52-56` · `.github/workflows/typecheck.yml:11` · `services/llm_orchestrator.py:479`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```yaml
# lint.yml:52-56
      - name: Run mypy
        run: |
          PYTHONHASHSEED=42 mypy --config-file mypy.ini \
            massive/ backend/ services/ massive_core/ 2>&1 || true      ← nunca falla

# typecheck.yml:9-11
  typecheck:
    name: mypy-slice
    runs-on: ubuntu-latest
    continue-on-error: true                                             ← nunca falla
```
```
$ mypy --config-file mypy.ini massive/ backend/ services/ massive_core/
Found 36 errors in 16 files (checked 83 source files)          → || true lo traga

$ python scripts/typecheck_slice.py ; echo $?
services/llm_orchestrator.py:479: error: Incompatible types in assignment
  (expression has type "ForecastResult", variable has type "dict[str, Any]")  [assignment]
            result = forecast(
Found 1 error in 1 file (checked 31 source files)
1                                                              → exit 1
$ gh api …/runs/… → "Typecheck slice (non-blocking)  completed/success"
                                                              → CI reporta SUCCESS con exit 1
```
El error es real y tiene implicación funcional: en `services/llm_orchestrator.py:479-486`, `result` está anotado como `dict[str, Any]` en el resto de `_dispatch`, pero la rama `motor == "forecast"` le asigna un `ForecastResult`. La línea siguiente lo compensa defensivamente (`return result.model_dump() if hasattr(result, "model_dump") else dict(result)`), es decir **el código ya sabe que el tipo es inconsistente y lo parchea con `hasattr`**.

**Impacto.** El único mecanismo de verificación de tipos del proyecto está estructuralmente incapacitado para fallar. Los 36 errores del slice y los 198 repo-wide crecerán sin límite. El único workflow que reporta verde es el que tiene `continue-on-error: true` — la señal de CI es literalmente invertida.

**Acción sugerida.** (1) Corregir `services/llm_orchestrator.py:479` (`result: ForecastResult | dict[str, Any]` o renombrar la variable). (2) Quemar los 36 errores del slice. (3) Entonces retirar `|| true` y `continue-on-error`. (4) Añadir `mypy` al gate bloqueante con el scope del slice.

**Esfuerzo:** M

---

**ID:** D7-007
**Severidad:** 🟠
**Dominio:** CI/CD
**Título:** `massive-ui-ng/infra/.github/workflows/ui-ng.yml` es un workflow muerto con rutas incorrectas para su propia ubicación
**Ubicación:** `massive-ui-ng/infra/.github/workflows/ui-ng.yml`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ find .github -type f | grep workflows      → 13 archivos (ninguno es ui-ng.yml)
$ find . -path "*.github/workflows/*" -not -path "./.github/*"
massive-ui-ng/infra/.github/workflows/ui-ng.yml
```
GitHub Actions sólo ejecuta workflows en `.github/workflows/` **en la raíz del repositorio**. Un `.github/workflows/` anidado en un subdirectorio nunca se dispara. Confirmado: el workflow no aparece en los 1 735 runs históricos.

Y si se moviera a la raíz tal cual, fallaría igualmente:
```yaml
on: push: paths: [ "backend/app/**", "frontend/**", "tests/test_ui_ng.py", … ]
   ← estos paths resuelven contra la RAÍZ; los reales son massive-ui-ng/backend/app/**, etc.
   → el filtro de paths nunca coincidiría con cambios en massive-ui-ng/

run: PYTHONHASHSEED=42 python -m pytest tests/test_ui_ng.py tests/test_ui_ng_live.py -q
   ← los archivos están en massive-ui-ng/tests/, no en tests/  (verificado: tests/ no los contiene)
run: python -m backend.app.evaluation
   ← hay DOS módulos `backend.app.evaluation`-candidatos; el real es massive-ui-ng/backend/app/evaluation.py
run: python scripts/gen_ts_types.py
   ← ¿cuál de los dos? el de massive-ui-ng/infra/scripts/ está roto (D3-003)
run: git diff --exit-code frontend/src/types/api.generated.ts
   ← el de massive-ui-ng es massive-ui-ng/frontend/src/types/api.generated.ts
working-directory: frontend   ← debería ser massive-ui-ng/frontend
```
Además `massive-ui-ng/infra/` contiene un segundo `Dockerfile.ui-ng`, un segundo `docker-compose.yml` y un segundo `env.example` — un tercer juego de infraestructura.

**Impacto.** Todo el subproyecto `massive-ui-ng/` (21 módulos backend + 15 archivos frontend + 2 archivos de test + 4 docs propios) está **completamente fuera de CI**: sin lint, sin typecheck, sin tests, sin build. Y contiene el 40 % de la complejidad ciclomática alta del repo (`build_narrative` F-57, `interpret` E-39, `_score_case` E-32) y 6 de los 28 errores de ruff.

**Acción sugerida.** Decidir el destino de `massive-ui-ng/` (D3-002/D3-005). Si se queda: mover el workflow a `.github/workflows/ui-ng.yml` con `paths: massive-ui-ng/**`, `working-directory: massive-ui-ng`, y rutas de test/script corregidas. Si se va: archivarlo.

**Esfuerzo:** M

---

**ID:** D7-008
**Severidad:** 🟠
**Dominio:** CI/CD
**Título:** `publish.yml` encadena 10 jobs detrás de un gate de lint que está rojo y de dos jobs que requieren un toolchain que nadie instala
**Ubicación:** `.github/workflows/publish.yml`
**Estado:** **[CONFIRMADO]**

**Evidencia.** Grafo de dependencias real:
```
lint  ──┬── test ──────────────┐
        ├── frontend-build     │
        ├── benchmark ─────────┼── build-wheels ── publish-pypi   (if: release || tag)
        └── docs ──────────────┴── build-image  ── publish-docker (if: release || tag)

Job `lint`:  ruff check . && black --check .        → ❌ ROJO (D2-001, D2-002)
Job `docs`:  pip install -e ".[docs]"               → ❌ madurin/Rust ausente (D5-002)
Job `build-wheels`: python -m build                 → ❌ backend maturin (D5-002)
Job `build-image`: docker build -f Dockerfile       → ❌ RUN pip install --no-deps -e /app (D5-002)

Confirmado en el run real:
  JOB: Lint => failure
  JOB: Tests, Frontend Build, Docs Build, Benchmark, Build Python Package,
       Build Docker Image, Publish to PyPI, Publish Docker Image, Build on Main => TODOS skipped
```
Y la condición de publicación (`if: github.event_name == 'release' || startsWith(github.ref, 'refs/tags/')`) es inalcanzable: no hay releases ni tags (D6-012).

**Impacto.** El pipeline de publicación a PyPI + GHCR está completamente escrito (10 jobs, OIDC trusted publishing, `id-token: write`, cache GHA, smoke test de Docker) y es **100 % inejecutable**. Tres bloqueos independientes: gate rojo, toolchain ausente, trigger inexistente.

**Acción sugerida.** Secuenciar: (1) verdear lint; (2) resolver el build backend (D5-002); (3) crear el primer tag `v1.1.0` + release; (4) entonces probar el flujo de publicación en un fork o con `push: false`.

**Esfuerzo:** L

---

**ID:** D7-009
**Severidad:** 🟡
**Dominio:** CI/CD
**Título:** Ningún workflow, Dockerfile o target de Make construye o testa el crate Rust
**Ubicación:** `.github/workflows/*` · `Dockerfile*` · `Makefile` · `install.sh`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ grep -rniE "cargo|rustc|maturin|dtolnay" .github/ Dockerfile Dockerfile.optimized Makefile install.sh
.github/CI_CD_BEST_PRACTICES.md:42  …"id-token: write only on publish jobs (OIDC trust for PyPI Trusted Publishing)"
   ← única coincidencia, y es por la palabra "trust", no por Rust
→ 0 jobs, 0 steps, 0 targets.

$ grep -n "rust\|cargo" Makefile install.sh   → 0
```
Complementa D3-017 (dos `Cargo.toml` contradictorios) y D3-018 (extensión nunca compilada).

**Impacto.** El código Rust puede dejar de compilar en cualquier momento y nadie se enteraría. Como `pyproject.toml` usa `build-backend = "maturin"`, **cualquier** `pip install .` intenta construir el crate — así que un `Cargo.toml` roto rompe la instalación Python incluso para quien no quiere Rust (D5-002).

**Acción sugerida.** Job `rust`: `dtolnay/rust-toolchain@stable` → `cargo fmt --check` → `cargo clippy -- -D warnings` → `cargo test` → `pip install maturin && maturin develop` → test de paridad Rust↔NumPy sobre `multi_potential_gradient`, `langevin_opinion_update_inplace`, `active_mask_step`.

**Esfuerzo:** M

---

**ID:** D7-010
**Severidad:** 🟡
**Dominio:** CI/CD
**Título:** `pvu-validation.yml` no se dispara en push a `main`
**Ubicación:** `.github/workflows/pvu-validation.yml:3-6`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```yaml
on:
  pull_request:
    branches: ["main"]
  workflow_dispatch:
    inputs: …
```
Comparativa con los otros 12 workflows: 10 de ellos usan `on: push: branches: ["main","master"]`. Confirmado en el histórico: el último run de `PVU Validation` es de 2026-07-15 (página 14 del histórico), mientras `Benchmark Runner` (que sí corre en push) aparece en cada commit.

**Impacto.** Un push directo a `main` —que es exactamente lo que ocurre en este repo, donde los últimos 8 commits son pushes directos— no ejecuta la validación científica pre-registrada. La validación sólo corre si alguien abre un PR, y este flujo de trabajo no usa PRs.

**Acción sugerida.** Añadir `push: branches: [main]` (con `paths-ignore` para docs) o, si el coste computacional preocupa, programarlo (`schedule: cron`) semanalmente sobre `main`.

**Esfuerzo:** XS

---

**ID:** D7-011
**Severidad:** 🟡
**Dominio:** CI/CD
**Título:** `main_massive.yml` despliega a Azure Web App: objetivo de despliegue huérfano, CRLF, y `python-version: '3.x'`
**Ubicación:** `.github/workflows/main_massive.yml` (75 líneas)
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
name: Build and deploy Python app to Azure Web App - MASSIVE
on: push: branches: [main] · workflow_dispatch
jobs: build: runs-on: ubuntu-latest · steps: actions/setup-python@v5 with: python-version: '3.x'
     deploy: → skipped (porque build falla)

Único archivo del repo con finales de línea CRLF:
$ (barrido de \r sobre 554 archivos trackeados, excluyendo binarios)
CRLF: .github/workflows/main_massive.yml        ← 1 archivo de texto con CRLF
      (+ data/ui_ng/runs.db, *.png, *.pt, *.npz = binarios, esperado)
.gitattributes contiene solo: `* text=auto` — sin declaraciones `binary` para .pt/.npz/.png/.db

Canales de despliegue declarados en el repo: 3
  1. Azure Web App          (main_massive.yml)          ← falla siempre
  2. Hugging Face Spaces    (deploy_hf_spaces.yml)      ← falla (billing + token en URL, D5-016)
  3. Docker / GHCR          (publish.yml, docker-e2e.yml) ← falla (D5-002)
  + nginx.conf + supervisord.conf (despliegue en contenedor propio)
README.md no menciona Azure en ninguna parte. PRODUCTION_ARCHITECTURE_SPEC.md tampoco lo prioriza.
```

**Impacto.** Tres objetivos de despliegue simultáneos sin documentación de cuál es el real. El de Azure usa `python-version: '3.x'` (flotante, puede resolver a 3.13 y romper con `requires-python = ">=3.10"` + torch). Los CRLF en un archivo YAML de Actions son tolerados pero inconsistentes con `* text=auto`.

**Acción sugerida.** Eliminar `main_massive.yml` si Azure no es un destino real, o documentarlo en `docs/DOCKER.md`/README. Fijar `python-version: "3.11"`. Declarar en `.gitattributes`: `*.pt binary`, `*.npz binary`, `*.png binary`, `*.db binary`.

**Esfuerzo:** XS

---

**ID:** D7-012
**Severidad:** 🟡
**Dominio:** CI/CD
**Título:** Clave de API estática y débil en los smoke tests de CI
**Ubicación:** `.github/workflows/docker-e2e.yml:20-24` · `.github/workflows/publish.yml` (smoke test Docker)
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```yaml
# docker-e2e.yml
      - name: Create minimal env files
        run: |
          touch .env .env.local
          echo "MASSIVE_API_KEY=ci-test-key" >> .env
          echo "MASSIVE_CORS_ORIGINS=http://localhost:3000" >> .env

# publish.yml, job build-image, "Run Docker smoke test"
          mkdir -p .env-test
          echo "MASSIVE_API_KEY=ci-test-key" > .env-test/.env
          docker run --rm -e MASSIVE_API_KEY=ci-test-key -e MASSIVE_ENV=development …
```
`ci-test-key` está en el allowlist de `gitleaks.toml` (D5-023). Ningún workflow genera una clave aleatoria (`openssl rand -hex 32`).

**Impacto.** Bajo: el valor sólo vive en runners efímeros. Pero establece el patrón de "clave fija conocida" y, combinado con `MASSIVE_ENV=development` en el smoke test, el contenedor de prueba arranca en modo fallback. Si alguien reutiliza el compose de CI en un entorno real, la clave es adivinable.

**Acción sugerida.** Generar la clave en el step (`echo "MASSIVE_API_KEY=$(openssl rand -hex 32)" >> .env`) y pasarla al curl de healthcheck vía env del runner.

**Esfuerzo:** XS

---

**ID:** D7-013
**Severidad:** 🟡
**Dominio:** CI/CD
**Título:** `secret_scan.yml` hace `fetch-depth: 0` sobre 1 735 runs de historial sin `GITLEAKS_LICENSE` ni `paths-ignore`
**Ubicación:** `.github/workflows/secret_scan.yml`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```yaml
name: Secret scan
on: [pull_request, push]           ← sin filtro de branches ni paths
jobs:
  gitleaks:
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0           ← clona TODO el historial en cada push
      - uses: gitleaks/gitleaks-action@v2
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ← falta GITLEAKS_LICENSE (requerido por gitleaks-action v2 en organizaciones)
```
Contexto: el repo tiene historial de un secreto real commiteado (`.codebuff/` con token MCP de Zapier, issue/PR #81, purgado con `git filter-repo` según `gitleaks.toml:11-15`).

**Impacto.** (a) Cada push descarga el historial completo — lento y costoso en minutos de Actions; (b) el escaneo de historial completo sobre un repo cuyo historial fue reescrito puede producir resultados inconsistentes entre clones shallow y full; (c) sin licencia, la acción puede degradarse o fallar si el repo se transfiere a una organización.

**Acción sugerida.** Separar en dos jobs: `gitleaks` incremental (`fetch-depth: 1`, en cada push) y `gitleaks-full` (schedule semanal, `fetch-depth: 0`). Añadir `GITLEAKS_LICENSE` como secret si aplica. Añadir `paths-ignore: ['**.md']`.

**Esfuerzo:** S

---

**ID:** D7-014
**Severidad:** 🟡
**Dominio:** Configuración
**Título:** `mypy.ini` en modo permisivo, sin `exclude`, con opt-outs por módulo y duplicado de configuración con `pyproject.toml`
**Ubicación:** `mypy.ini` · `pyproject.toml:87-119`
**Estado:** **[CONFIRMADO]** · puntos 7.4 y 7.5 del brief

**Evidencia.**
```ini
[mypy]
python_version = 3.11
strict = False
ignore_missing_imports = True
warn_unused_ignores = True
warn_return_any = False
check_untyped_defs = False        ← no revisa el cuerpo de funciones sin anotar
follow_imports = silent           ← los errores de módulos importados no se reportan
namespace_packages = True
explicit_package_bases = True
# SIN `exclude` → massive-ui-ng/, frontend/node_modules/, site/ entran en el scope (D2-004)
# SIN `files` → hay que pasar los targets por CLI

Adopción gradual: 9 secciones con disallow_untyped_defs = True
  services.* · massive_core.utils.rng · forecast.targets · massive_core.numerics.*
  massive_core.config.* · massive_core.diagnostics.* · massive_core.data_assimilation.*
  massive_core.analysis.* · massive_core.physics.* · massive_core.metalearning.*

Opt-out explícito:
  [mypy-massive_core.numerics.multilayer_engine_sparse]
  disallow_untyped_defs = False
  check_untyped_defs = False
  # comentario: "Sparse engine is large / legacy-shaped; keep typed-defs policy but allow
  #              incomplete internal typing until a dedicated cleanup PR."
  → 789 líneas, 52 % cobertura, sin fecha ni issue asociado al "dedicated cleanup PR"

Duplicación de configuración entre archivos:
  pyproject.toml  → [tool.ruff], [tool.ruff.lint], [tool.ruff.format], [tool.black],
                    [tool.pytest.ini_options], [tool.coverage.run], [tool.coverage.report]
  mypy.ini        → [mypy] + 10 secciones
  → mypy es la ÚNICA herramienta no configurada en pyproject.toml; no hay setup.cfg.
    El comentario de `[tool.ruff.lint] ignore = ["E501","B008"]  # handled by line-length + black`
    es engañoso: black no gestiona E501 (ruff format sí, y no está en uso).
```

**Impacto.** `follow_imports = silent` + `check_untyped_defs = False` significa que la mayor parte del código no se analiza realmente: los 198 errores detectados son sólo la punta. La ausencia de `exclude` hace que `mypy .` aborte (D2-004), así que nadie lo ejecuta repo-wide. La configuración repartida en dos archivos dificulta saber qué regla aplica.

**Acción sugerida.** Migrar `[mypy]` a `[tool.mypy]` en `pyproject.toml` y borrar `mypy.ini`; añadir `exclude`; activar `check_untyped_defs = True` globalmente y gestionar las excepciones por módulo; poner fecha/issue al opt-out de `multilayer_engine_sparse`.

**Esfuerzo:** M

---

**ID:** D7-015
**Severidad:** 🟡
**Dominio:** Configuración
**Título:** Cuatro combinaciones de despliegue sin una ruta canónica documentada
**Ubicación:** root
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
2 Dockerfiles       Dockerfile (nginx+supervisord+frontend embebido, EXPOSE 80 8000)
                    Dockerfile.optimized (uvicorn directo, EXPOSE 8000, LÍNEA 1 INVÁLIDA)
2 compose           docker-compose.yml (usa Dockerfile, marcado LEGACY, mount .env + .env.local)
                    docker-compose.single.yml (usa Dockerfile.optimized, mount .env + frontend/dist)
1 infra paralela    massive-ui-ng/infra/{Dockerfile.ui-ng, docker-compose.yml, env.example}
+ nginx.conf + supervisord.conf (solo los usa Dockerfile)
+ install.sh (venv + pip install -e ".[full]" → ROTO, D5-002)
+ Makefile (api / api-legacy / frontend-* → sin target docker)
+ docs/DOCKER.md (huérfano del nav, D6-009)
README.md quick start: solo `uvicorn backend.app.main:app` — no menciona Docker
```

**Impacto.** Siete archivos de infraestructura de despliegue, ninguno de los cuales tiene un camino verde demostrado. `Makefile` —que es la interfaz de desarrollador— no tiene target `docker`, así que el camino Docker sólo se descubre leyendo `docs/DOCKER.md`, que no está en el sitio.

**Acción sugerida.** Una tabla en README: "Local dev → `make api` · Producción → `docker compose up` · Single-port → …", con **una** sola opción por caso de uso, y eliminar el resto.

**Esfuerzo:** M

---

**ID:** D7-016
**Severidad:** 🟡
**Dominio:** Configuración
**Título:** `supervisord.conf` gestiona 2 procesos en un contenedor (nginx como root + uvicorn como appuser)
**Ubicación:** `supervisord.conf` · `Dockerfile:70-76`
**Estado:** **[CONFIRMADO]** · punto 7.3 del brief

**Evidencia.**
```ini
[supervisord] nodaemon=true  user=root
[program:nginx]    command=/usr/sbin/nginx -g "daemon off;"  user=root   autostart/autorestart=true
[program:uvicorn]  command=/usr/local/bin/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
                   user=appuser  autostart/autorestart=true
# FIX (CRIT-2): Streamlit UI removed (OPS-02). No /ui/ program …
```
```dockerfile
USER appuser
CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
RUN setcap 'cap_net_bind_service=+ep' /usr/sbin/nginx
```
Inconsistencia detectada: el Dockerfile termina con `USER appuser` pero `supervisord.conf` declara `[supervisord] user=root` y `[program:nginx] user=root`. Con el contenedor arrancando como `appuser`, supervisord **no puede** cambiar a `user=root` para nginx — la directiva se ignora o falla. La compensación es el `setcap` del binario nginx, que sí permite bindear :80 sin root; entonces la directiva `user=root` es redundante y engañosa.

`MASSIVE_SYSTEM_MAP.md:145` describe el conjunto como "api (appuser) + streamlit (appuser) + nginx (root)" — desactualizado en dos puntos (D6-008).

**Impacto.** Anti-patrón de contenedor multi-proceso: sin init real (PID 1 es supervisord, que sí reapea, aceptable), pero dos ciclos de vida acoplados — un fallo de nginx reinicia el contenedor entero según `restart: unless-stopped`. La directiva `user=root` inefectiva puede confundir en una auditoría de seguridad. Y el healthcheck del Dockerfile apunta a `:8000/health` mientras `docker-compose.yml` apunta a `:8000/docs` — dos definiciones de "sano".

**Acción sugerida.** O (a) dividir en dos contenedores (nginx + api) en el compose, que es la práctica estándar; o (b) mantener supervisord y eliminar las directivas `user=root` inefectivas, documentando que `setcap` es lo que permite bindear :80. Unificar el healthcheck en `/health`.

**Esfuerzo:** M

---

**ID:** D7-017
**Severidad:** 🟢
**Dominio:** CI/CD
**Título:** Los 13 workflows, los 2 compose, `mkdocs.yml` y los 2 `configs/*.yaml` parsean sin errores
**Ubicación:** `.github/workflows/` · root · `configs/`
**Estado:** **[CONFIRMADO — POSITIVO]**

**Evidencia.**
```
OK   docker-compose.yml · docker-compose.single.yml · massive-ui-ng/infra/docker-compose.yml
OK   mkdocs.yml · configs/multilayer.yaml · configs/pvu.yaml
OK   .github/workflows/{benchmark, deploy_hf_spaces, docker-e2e, frontend-build, lint,
                        main_massive, mkdocs, publish, pvu-validation, pytest, secret_scan,
                        typecheck, validate_ts_types}.yml          (13/13)
→ 20/20 archivos YAML válidos
Adicional: los 13 workflows declaran `permissions:` explícitos o usan el default seguro;
  `publish.yml` usa `id-token: write` solo en los jobs de publish (OIDC Trusted Publishing),
  lo cual es la práctica recomendada y está documentada en .github/CI_CD_BEST_PRACTICES.md.
```

**Impacto.** Positivo: la infraestructura de CI está bien escrita a nivel de sintaxis y de modelo de permisos. El problema es de ejecución y de gates, no de construcción.

**Acción sugerida.** Ninguna.

**Esfuerzo:** —

---

**ID:** D7-018
**Severidad:** 🟢
**Dominio:** Configuración
**Título:** `Makefile` e `install.sh` ofrecen una superficie de desarrollador coherente y auto-documentada
**Ubicación:** `Makefile` (17 targets) · `install.sh`
**Estado:** **[CONFIRMADO — POSITIVO]** (con la salvedad de D5-002 en `install.sh`)

**Evidencia.**
```makefile
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; …'
install · test · test-cov · lint · format · typecheck · api · api-legacy · cli-verify
frontend-install · frontend-dev · frontend-build · benchmark · clean
```
Detalles de calidad: `.PHONY` declarado correctamente; `PYTHON ?= python3` y `VENV ?= .venv` sobre-escribibles; `make api-legacy` documenta explícitamente que `api.py` es legacy; `PYTHONHASHSEED=42` en `make benchmark`; comentario de cabecera que remite a `docs/runbooks/local-development.md`.
`install.sh`: `set -euo pipefail`, detección de `python3`/`python`, verificación de versión, salida en color condicional a `[ -t 1 ]`, 11 subcomandos documentados en la cabecera.

**Impacto.** Positivo. Es la mejor interfaz del repo. Lástima que `make lint` y `make typecheck` fallen (D2-001, D7-006) e `install.sh install` no funcione (D5-002) — la herramienta es correcta, lo que falla es lo que envuelve.

**Acción sugerida.** Añadir targets `docker`, `docker-single`, `rust` y `docs` (con puerto correcto, D6-013); corregir `clean` para incluir `.ruff_cache`, `site/`, `dist/`, `*.egg-info`, `massive_run.log`, `landscapes_cache.db`.

**Esfuerzo:** XS

---

**ID:** D7-019
**Severidad:** 🟡
**Dominio:** Configuración
**Título:** `pyproject.toml` declara `massive-cli` como único script pero el CLI no está probado, y `addopts` desactiva un plugin no declarado
**Ubicación:** `pyproject.toml:56,59`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```toml
[project.scripts]
massive-cli = "massive.cli.main:main"

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
addopts = "-q -p no:libtmux"
```
`-p no:libtmux` desactiva el plugin de pytest de `libtmux`, que **no está** en `requirements.txt` ni en `pyproject.toml` ni se importa en ningún archivo del repo (`grep -rn libtmux .` → 0 resultados fuera de esta línea). Es un workaround para un problema de un entorno de desarrollo concreto que quedó commiteado.
`massive/cli/main.py`: 99 stmts, 0.0 % cobertura, 0 tests (D3-013). El target `cli-verify` existe en el `.PHONY` del Makefile pero **no tiene regla implementada** (el Makefile lo declara en `.PHONY` y en el help, pero el cuerpo del target no aparece en el archivo).

**Impacto.** El entrypoint publicado no está probado. `addopts` con un plugin fantasma añade ruido y puede confundir ("¿por qué se desactiva libtmux?"). Un target de Make declarado y no implementado falla silenciosamente (`make cli-verify` → "Nothing to be done").

**Acción sugerida.** Implementar `cli-verify` (`$(BIN)/massive-cli --help` + una corrida mínima); eliminar `-p no:libtmux` o documentar por qué existe; añadir tests del CLI.

**Esfuerzo:** S

---

**ID:** D7-020
**Severidad:** 🟡
**Dominio:** Configuración
**Título:** `.gitattributes` no declara binarios para `.pt`, `.npz`, `.png` ni `.db` pese a `* text=auto`
**Ubicación:** `.gitattributes` (2 líneas)
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ cat .gitattributes
# Auto detect text files and perform LF normalization
* text=auto

Archivos binarios trackeados: 9 × .pt (396 KB) · 1 × .npz · 3 × .png · 1 × .db (40 KB)
$ grep -n "binary" .gitattributes → 0

Efecto observable: el barrido de \r detecta bytes 0x0D dentro de
  data/ui_ng/runs.db · models/cfc_calibrated/*.pt · *.npz · docs/*.png
  → git los trata como "binarios por detección", que normalmente funciona,
    pero la detección heurística puede fallar con archivos que empiezan por texto.
Contradicción con D5-020: `deploy_hf_spaces.yml` hace checkout con `lfs: true`
  pero no hay ninguna entrada LFS en .gitattributes → el flag es un no-op.
```

**Impacto.** Riesgo bajo pero real de corrupción de binarios en merges/checkouts cross-platform. Y la intención de usar Git LFS (evidenciada por el comentario del `.gitignore` *"Git LFS recommended"* y por `lfs: true` en el checkout) nunca se configuró.

**Acción sugerida.** Declarar `*.pt binary`, `*.pth binary`, `*.npz binary`, `*.png binary`, `*.jpg binary`, `*.db binary`, `*.sqlite binary`. Si se opta por LFS para los pesos (D4-001), añadir `models/**/*.pt filter=lfs diff=lfs merge=lfs -text`.

**Esfuerzo:** XS

---

### DOMINIO 8 — ESTÉTICA DEL REPOSITORIO

---

**ID:** D8-001
**Severidad:** 🟠
**Dominio:** Estética
**Título:** 106 entradas en la raíz del repositorio (78 archivos + 28 directorios) — 7× el umbral razonable
**Ubicación:** root
**Estado:** **[CONFIRMADO]** · puntos 8.5 y 3.1 del brief · **[CONOCIDO PREVIO]**

**Evidencia.**
```
$ ls -A | wc -l              → 106   (tras la corrida de auditoría; 99 en checkout limpio)
$ ls -Ap | grep -v / | wc -l → 78 archivos
$ ls -Ap | grep /   | wc -l  → 28 directorios

Desglose de los 78 archivos root:
  31 × .py        (D3-006, clasificación completa ahí)
  21 × .md        (D6-003, clasificación completa ahí)
   6 × config de herramienta: pyproject.toml, requirements.txt, mypy.ini, mkdocs.yml,
                              gitleaks.toml, repomix.config.json
   4 × Docker/compose: Dockerfile, Dockerfile.optimized, docker-compose.yml, docker-compose.single.yml
   3 × Rust: Cargo.toml, Cargo.lock, (+ rust_core/ dir)
   3 × infra: nginx.conf, supervisord.conf, Makefile
   2 × shell: install.sh, (+ scripts/ dir)
   2 × env: .env.example, .env.local.example
   4 × dotfiles: .gitignore, .gitattributes, .dockerignore, .repomixignore
   1 × LICENSE
   1 × repomix-instruction.md
   1 × .gitattributes

Directorios root (28):
  Código (14): adapters backend benchmarks configs data datasets experiments forecast
               frontend massive massive-ui-ng massive_core metrics micro_massive
               monitoring rust_core scripts services tests        (en realidad 19)
  Meta (3):    docs reports models
  Ocultos (2): .git .github

Umbral de referencia: un repo limpio suele tener 10-15 entradas root.
Comparación con el contexto previo del brief: el conteo de .py root (31) coincide con "~30+" ✓
```

**Impacto.** La primera impresión en github.com/Adlgr87/MASSIVE es una pared de 78 archivos donde el README compite con 5 reportes de auditoría previos, 4 planes de arquitectura y 31 módulos sueltos. Dificulta enormemente responder "¿por dónde empiezo?" — que es la pregunta que un visitante nuevo necesita responder en 30 segundos.

**Acción sugerida.** Objetivo: ≤ 20 entradas root. Ejecutar D6-003 (mover 13 .md) + D3-006 (mover 31 .py a paquetes) + D7-005 (eliminar 2 archivos de infra). Resultado esperado: README, README_ES, CHANGELOG, LICENSE, CONTRIBUTING, CODE_OF_CONDUCT, AGENTS, pyproject.toml, requirements*.txt, Makefile, Dockerfile, docker-compose.yml, nginx.conf, .gitignore, .gitattributes, .dockerignore, .env.example + ~10 directorios.

**Esfuerzo:** L

---

**ID:** D8-002
**Severidad:** 🟠
**Dominio:** Estética / Release management
**Título:** Cero releases, cero tags, cero versiones semánticas — con un pipeline de publicación a PyPI ya escrito
**Ubicación:** GitHub API · `.github/workflows/publish.yml`
**Estado:** **[CONFIRMADO]** · punto 8.1 del brief

**Evidencia.**
```
$ gh api repos/Adlgr87/MASSIVE/releases --jq '.[].tag_name'  → (vacío)
$ gh api repos/Adlgr87/MASSIVE/tags     --jq '.[].name'      → (vacío)
Repo creado: 2026-04-01  · 90 issues cerrados  · 1 735 workflow runs  · 5.5 meses de desarrollo

publish.yml tiene el flujo completo de release:
  on: release: types: ["published"]
  permissions: contents: read · packages: write · id-token: write (OIDC)
  jobs: lint → test → frontend-build → benchmark → docs → build-wheels → build-image
        → publish-pypi (environment: pypi-publish, url: https://pypi.org/project/massive)
        → publish-docker (ghcr.io/${owner}/massive)
  docker/metadata-action@v5 con tags: type=semver,pattern={{version}} · type=semver,pattern={{major}}.{{minor}}

→ Toda la maquinaria de release está implementada y nunca se ha disparado porque no existe ningún tag.
```
Además: el nombre de paquete PyPI `massive` (pyproject `name = "massive"`) es un nombre genérico de alto riesgo de colisión en PyPI; no hay evidencia de que se haya reservado.

**Impacto.** No hay puntos de restauración ni versiones instalables (`pip install massive==x.y.z` imposible). Los usuarios no pueden fijar una versión. Los badges de release no existen. `CHANGELOG.md` no puede vincularse a releases. Y el nombre `massive` en PyPI probablemente ya esté tomado, lo que haría fallar `publish-pypi` incluso si todo lo demás funcionara.

**Acción sugerida.** (1) Verificar disponibilidad de `massive` en PyPI; si está tomado, renombrar el paquete distribuido (p. ej. `massive-simulator` o `massive-social`) manteniendo `massive` como nombre de import. (2) Alinear versiones (D6-012). (3) Crear el tag `v1.1.0` + release con notas generadas desde `CHANGELOG.md`. (4) Configurar Trusted Publishing de PyPI para el environment `pypi-publish`.

**Esfuerzo:** M

---

**ID:** D8-003
**Severidad:** 🟠
**Dominio:** Estética / Legal
**Título:** GitHub no reconoce la licencia (reporta "Other") aunque `pyproject.toml` y el README declaran Apache-2.0
**Ubicación:** `LICENSE` (10 262 bytes) · `pyproject.toml:10` · `README.md:10`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ gh repo view Adlgr87/MASSIVE --json licenseInfo
{"licenseInfo":{"key":"other","name":"Other","nickname":""}}

$ head -3 LICENSE
                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

$ tail -14 LICENSE
   END OF TERMS AND CONDITIONS

   Copyright 2024 MASSIVE Research (Adlgr87)

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0
   …

pyproject.toml:10   license = { text = "Apache-2.0" }
README.md:10        [![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
```
El texto es Apache-2.0 íntegro; el bloque de copyright + re-enunciado de la licencia **añadido después de "END OF TERMS AND CONDITIONS"** es lo que rompe la detección de `licensee` (la librería que usa GitHub), que exige coincidencia casi exacta con el texto canónico. La convención Apache es poner el copyright en el `APPENDIX` dentro del texto, no como bloque posterior.

Detalle adicional: el copyright dice **2024** pero el repo se creó en **2026-04-01** y el proyecto se renombró a MASSIVE en junio 2026 (issues #28/#29).

**Impacto.** (a) GitHub no muestra el badge automático de licencia ni permite filtrar el repo por licencia; (b) un usuario que evalúa reutilizar el código ve "Other" y puede asumir restricciones desconocidas; (c) contradicción entre el badge del README ("Apache 2.0") y la metadata de GitHub ("Other"); (d) el año de copyright es inconsistente con la historia del proyecto.

**Acción sugerida.** Reemplazar `LICENSE` por el texto canónico de Apache-2.0 sin modificaciones, y mover el aviso de copyright al `APPENDIX: How to apply the Apache License to your work` (que es donde Apache lo prevé) o a una sección `NOTICE`. Corregir el año.

**Esfuerzo:** XS

---

**ID:** D8-004
**Severidad:** 🟡
**Dominio:** Estética
**Título:** Topics de GitHub desactualizados y con una errata
**Ubicación:** metadata del repositorio
**Estado:** **[CONFIRMADO]** · punto 8.1 del brief

**Evidencia.**
```
$ gh repo view Adlgr87/MASSIVE --json repositoryTopics
agent-based-models · python · simulation · social-dynamics · streamlit ·
hegselmann-krause · ai-tools · llms · scaleable · simulation-engine · social-network-analysis

Problemas:
  streamlit    ← ELIMINADO del proyecto (OPS-02, CHANGELOG.md:89, 0 imports) — D1-006
  scaleable    ← errata de "scalable"
  ai-tools     ← genérico, bajo valor de descubrimiento

Ausentes (capacidades reales y verificadas del repo):
  fastapi · pydantic · rust · pyo3 · liquid-neural-networks · cfc ·
  closed-form-continuous-time · kalman-filter · ensemble-kalman-filter ·
  opinion-dynamics · polarization · complex-systems · monte-carlo ·
  game-theory · nash-equilibrium · topological-data-analysis ·
  early-warning-signals · docker · mamba · ssm · scientific-computing

Otros metadata:
  description: "MASSIVE is a hybrid simulator of social dynamics outcomes."  ✓ (no expande el acrónimo)
  homepageUrl: "https://adlgr87.github.io/MASSIVE/"  ✓ (coincide con pyproject Documentation)
  stargazerCount: 0 · forkCount: 0 · hasIssuesEnabled: true
```

**Impacto.** El descubrimiento por topics es la vía principal de tráfico orgánico en GitHub. Un topic obsoleto (`streamlit`) atrae al público equivocado; una errata (`scaleable`) no coincide con ninguna búsqueda; y faltan los 15+ topics que describirían las capacidades diferenciales que el README sí destaca (CfC, EnKF, PyO3, TDA, EWS).

**Acción sugerida.** `gh repo edit --remove-topic streamlit --remove-topic scaleable --remove-topic ai-tools --add-topic fastapi --add-topic pydantic --add-topic rust --add-topic liquid-neural-networks --add-topic opinion-dynamics --add-topic kalman-filter --add-topic game-theory --add-topic topological-data-analysis --add-topic complex-systems --add-topic scalable`. Ampliar la descripción con el acrónimo: *"MASSIVE — Mathematical Architecture for Scalable Social Interaction & Virtual Engine. Hybrid physics + AI simulator of opinion dynamics, polarization and intervention outcomes."*

**Esfuerzo:** XS

---

**ID:** D8-005
**Severidad:** 🟡
**Dominio:** Estética
**Título:** Badges del README: 5 presentes (2 de ellos rotos por estado de CI) y 7 relevantes ausentes
**Ubicación:** `README.md:10-14` · `README_ES.md:10-14`
**Estado:** **[CONFIRMADO]** · punto 8.2 del brief

**Evidencia.**
```
Presentes (README.md:10-14):
  [![License: Apache 2.0](img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
       ← contradice la detección de GitHub "Other" (D8-003)
  [![Python: 3.11+](img.shields.io/badge/Python-3.11+-blue?logo=python)](pyproject.toml)
       ← pyproject dice requires-python = ">=3.10"; ruff/black target py311. Inconsistente.
  [![Tests](github.com/Adlgr87/MASSIVE/actions/workflows/pytest.yml/badge.svg?branch=main)]
       ← renderiza "failing" (D7-001)
  [![Type-check: MyPy](…/typecheck.yml/badge.svg)]
       ← renderiza "passing" solo porque continue-on-error: true — señal FALSA (D7-006)
  [![Rust: optional PoC](img.shields.io/badge/Rust-optional_compilable-orange?logo=rust)](rust_core/)
       ← afirma "compilable" pero ningún CI lo compila (D3-018); README_ES enlaza a Cargo.toml

Ausentes:
  Coverage (el repo mide 59.62 % y tiene --cov-report configurado)
  Docs build (mkdocs.yml + workflow mkdocs.yml existen)
  Docker image (publish.yml construye ghcr.io/{owner}/massive)
  PyPI version (publish.yml publica a PyPI)
  GitHub release / tag (no existen, D8-002)
  Code style: black (black está configurado y en CI)
  PRs welcome / good first issue
  DOI o cita (el repo tiene protocolo de validación pre-registrado — candidato a Zenodo)
```

**Impacto.** El badge de MyPy es activamente engañoso: muestra verde permanente por configuración, no por calidad. El de Tests muestra rojo. El de Rust afirma algo no verificado. Un evaluador técnico que lea los badges llega a conclusiones equivocadas en ambos sentidos.

**Acción sugerida.** Retirar el badge de MyPy hasta que el check sea bloqueante (D7-006). Añadir coverage (generado en CI y publicado como artifact/gist), docs, code-style y release. Corregir "Python 3.11+" ↔ `requires-python` (elegir uno: si es 3.10, bajar el `target-version` de ruff/black; si es 3.11, subir `requires-python`).

**Esfuerzo:** S

---

**ID:** D8-006
**Severidad:** 🟡
**Dominio:** Estética / Gobernanza
**Título:** Sin issue templates, sin labels de triaje visibles, 90 issues cerrados y 0 abiertos
**Ubicación:** `.github/` · GitHub issues
**Estado:** **[CONFIRMADO]** · punto 8.3 del brief

**Evidencia.**
```
$ ls .github/ISSUE_TEMPLATE → No such file or directory
$ gh api "repos/Adlgr87/MASSIVE/issues?state=all&per_page=100"
  → 90 issues, TODOS cerrados, 0 abiertos, 0 pull requests en la lista
  Títulos representativos:
    #90 feat: Phase 8-9 — OpenTelemetry, metrics, backup automation
    #88 🔧 MASSIVE Repository Repair - Critical Auditor Fixes
    #85 fix: Hito 0 — unblock CI (tests/frontend/lint) + auth parity + production-readiness docs
    #81 Remove .codebuff folder containing exposed Zapier MCP token
    #58 Consolidate merge   ·  #54 Consolidate merge   ← dos issues con el mismo título genérico
     #5 i18n (Inglés/Español) ·  #1 Build: Organizacion del Repo y CI/CD
  Mezcla de idiomas en los títulos: "Hito 0", "Organizacion", "Consolidate merge", "feat:", "fix(security):"
  Sin convención única de conventional-commits en issues (sí en commits)
```

**Impacto.** El patrón de uso es "issue como unidad de trabajo de un agente, cerrada inmediatamente", no "issue como canal de comunidad". Con 0 issues abiertos y 0 forks, no hay embudo de contribución. Y los 148 hallazgos de esta auditoría no tienen dónde registrarse como trabajo seguible.

**Acción sugerida.** Añadir `.github/ISSUE_TEMPLATE/{bug_report.yml, feature_request.yml, documentation.yml}` con campos estructurados (versión, comando de reproducción, output esperado/obtenido). Crear los labels `good first issue`, `help wanted`, `area:backend`, `area:engines`, `area:docs`, `area:ci`, `severity:critical`. Abrir un issue por cada hallazgo 🔴/🟠 de este reporte (ver el workflow de remediación).

**Esfuerzo:** S

---

**ID:** D8-007
**Severidad:** 🟡
**Dominio:** Estética
**Título:** 0 estrellas, 0 forks, 0 watchers tras 5.5 meses — el repo no tiene tracción ni señales sociales
**Ubicación:** GitHub API
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
$ gh repo view Adlgr87/MASSIVE --json stargazerCount,forkCount,createdAt,pushedAt
{"stargazerCount":0, "forkCount":0, "createdAt":"2026-04-01T04:33:13Z", "pushedAt":"2026-09-15T03:51:06Z"}
Tamaño remoto: 36 401 KB · 554 archivos trackeados · 90 issues cerrados · 1 735 workflow runs
```

**Impacto.** No es un defecto de código, pero es el contexto que explica por qué los defectos de primera impresión (D8-001, D6-003, D6-001) importan más de lo normal: no hay comunidad que compense la fricción inicial, y un visitante que llega por búsqueda decide en segundos.

**Acción sugerida.** Fuera del alcance técnico. Sí es alcanzable: corregir la primera impresión (D8-001, D6-003), los topics (D8-004), la licencia detectable (D8-003), y añadir una sección "Citing MASSIVE" + un `CITATION.cff` (el repo tiene protocolo de validación pre-registrado en `docs/validation/`, que es material publicable).

**Esfuerzo:** S (parte técnica)

---

**ID:** D8-008
**Severidad:** 🟢
**Dominio:** Estética
**Título:** El Quick start del README funciona de punta a punta — verificado en vivo
**Ubicación:** `README.md:40-70`
**Estado:** **[CONFIRMADO — POSITIVO]** · punto 8.4 del brief

**Evidencia.** Ejecución real de los 5 pasos documentados:
```
1. git clone … && cd MASSIVE                                  ✓
2. python3 -m venv .venv && source .venv/bin/activate         ✓
3. pip install -r requirements.txt                            ✓ (ver salvedad D5-005: falta psutil/httpx)
4. cp .env.example .env                                       ✓ (opcional, el servidor arranca sin él)
5. uvicorn backend.app.main:app --host 0.0.0.0 --port 8000    ✓
   INFO: Application startup complete.
   INFO: Uvicorn running on http://0.0.0.0:8000

Sondas al servidor levantado:
  GET /health   → 200 {"status":"healthy","service":"MASSIVE UIL API","version":"1.0.0"}
  GET /ready    → 200 {"status":"ready","mode":"degraded",
                       "checks":{"settings":"ok","simulation_core":"ok",
                                 "llm_provider":"not_configured","uil_adapter":"available"}}
  GET /version  → 200 {"version":"1.0.0","python":"3.11.2","service":"MASSIVE UIL API",
                       "entrypoint":"backend.app.main:app"}
  POST /v1/simulate -H "X-API-Key: dev-secret-key" -d '{"pasos": 30}'
                → 200 con historial completo de 30 pasos, cada paso con
                  _paso, _regla, _regla_nombre, _razon, _rango      ✓ (el comando curl literal del README)
  POST /v1/simulate (sin header)  → 401                            ✓ fail-closed correcto
  GET /openapi.json → 200, 22 paths bien formados                  ✓
Observabilidad en vivo verificada: X-Request-ID, traceparent W3C, access log estructurado
  (request_id/method/path/status/duration_s) — coincide con lo que el README promete ✓
```
El modo `degraded` con `llm_provider: not_configured` es comportamiento correcto y documentado: las simulaciones básicas funcionan sin LLM.

**Impacto.** Positivo y significativo: es el hallazgo más importante a favor del proyecto. **El camino principal documentado funciona.** El quick start tiene exactamente 5 pasos, es copiable/pegable, y produce un servidor operativo en menos de 3 minutos.

**Acción sugerida.** Ninguna sobre el quick start. Sí: añadir la nota de que `pip install -r requirements.txt` no incluye `psutil`/`httpx` (D5-005, D4-006), y un sexto paso opcional para `make test`.

**Esfuerzo:** —

---

**ID:** D8-009
**Severidad:** 🟢
**Dominio:** Estética
**Título:** El ejemplo más simple de `simulator` del brief de auditoría ejecuta y produce salida correcta
**Ubicación:** `simulator.py` (`simular`, `resumen_historial`)
**Estado:** **[CONFIRMADO — POSITIVO, con condición]** · punto 8.4 del brief

**Evidencia.**
```
$ python -c "
import sys; sys.path.insert(0, '.')
from simulator import simular, resumen_historial
estado = {'opinion': 0.5, 'propaganda': 0.7, 'confianza': 0.4,
          'opinion_grupo_a': 0.72, 'opinion_grupo_b': 0.28, 'pertenencia_grupo': 0.65}
h = simular(estado, pasos=30, cada_n_pasos=5, verbose=False)
print(resumen_historial(h))"

[TDA] ripser/persim no instalados — detección topológica desactivada.
{'opinion_inicial': 0.5, 'opinion_final': 0.12750546514701278,
 'delta_total': -0.3724945348529872, 'media': 0.464330525172811,
 'desviacion': 0.20811623514147665, 'minimo': 0.09060509734660604, 'maximo': 1.0,
 'polarizacion_media': 0.35258093426454384, 'pasos': 30,
 'regla_dominante': 'polarizacion', 'neutro': 0.5,
 'rango': '[0, 1] — Probabilístico'}
exit=0
```
**Condición:** sólo funciona con `torch` instalado. Sin torch → `AttributeError` (D1-001). Los parámetros en español del brief (`opinion`, `propaganda`, `confianza`, `opinion_grupo_a`, `pertenencia_grupo`) son **exactamente** las claves reales del estado — la API pública en español es consistente y está documentada correctamente.

Detalle de calidad de la salida: `resumen_historial` devuelve un dict con estadísticas completas, la regla dominante identificada por nombre legible (`polarizacion`) y el rango de opinión etiquetado en español — buena ergonomía.

**Impacto.** Positivo: la API pública principal es estable, los nombres de parámetros coinciden con la documentación, y el resultado es numéricamente plausible (opinión 0.5 → 0.13 bajo propaganda 0.7 con regla dominante de polarización).

**Acción sugerida.** Ninguna sobre la API. Priorizar D1-001 para que el ejemplo funcione también sin torch.

**Esfuerzo:** —

---

**ID:** D8-010
**Severidad:** 🟡
**Dominio:** Estética
**Título:** El README es visualmente rico pero su tabla de arquitectura y su árbol de layout omiten la mitad del repositorio
**Ubicación:** `README.md:22-38` (tabla frontier) · `README.md:256-291` (layout)
**Estado:** **[CONFIRMADO]**

**Evidencia.** Lo que el README hace bien:
```
<div align="center"> con hero + acrónimo expandido + tagline ("from 10 agents to 100 million")
5 badges · barra de navegación con anclas · tabla "Why MASSIVE is different" de 8 filas
  (cada fila con columna "Where" apuntando al archivo responsable)
Quick start de 5 pasos verificado (D8-008) · diagrama Mermaid de arquitectura
Tabla de endpoints · sección "The LLM layer" · tabla de benchmarks
Tabla "Quality & production posture" · árbol de layout · índice de documentación
```
Lo que omite (ver D6-014 para la lista completa): 26 módulos Python root, 21 .md root, `metrics/`, `experiments/`, `reports/`, `data/`, `adapters/`, y 4 archivos de infraestructura. La tabla frontier menciona 8 capacidades; de ellas, **3 apuntan a archivos con problemas**: `massive_engine.py` (D9-004 vars descartadas), `social_architect.py` (14.4 % cobertura, D4-004), `rust_core/` (nunca compilado, D3-018).

**Impacto.** El README comunica una arquitectura más limpia y más pequeña de la que existe. Cuando un lector abre el repo y ve 106 entradas root frente a un árbol de 20, la discrepancia mina la confianza en el resto del documento —incluidas las partes que sí son exactas.

**Acción sugerida.** Dos opciones honestas: (a) mostrar el árbol completo generado automáticamente; o (b) mostrar explícitamente un árbol *curado* de 12 entradas y añadir una línea: *"The repository root also contains 26 legacy engine modules being migrated into `massive/core/` — see `docs/architecture/module_inventory.md`"* (documento que ya existe y está huérfano, D6-009).

**Esfuerzo:** S

---

**ID:** D8-011
**Severidad:** 🟡
**Dominio:** Estética
**Título:** El renombrado UIL → UI-NG → MASSIVE está incompleto en nombres de archivo y de paquete
**Ubicación:** `uil_adapter.py` · `frontend/src/MASSIVE_UIL_demo.jsx` · `massive-ui-ng/frontend/src/MASSIVE_UIL_demo.jsx` · `backend/app/main.py:65` · `tests/test_uil_mappings.py` · `docs/architecture/backward_compatibility_aliases.md`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
Tres generaciones de nombre conviven:
  "UIL"     → uil_adapter.py · MASSIVE_UIL_demo.jsx (×2, 825 líneas idénticas)
              frontend/package.json name: "massive-uil-frontend"
              tests/test_uil_mappings.py · docs/MASSIVE_LLM_INTERFACE.md
              backend/app/main.py:65  title="MASSIVE UIL API"
              api.py:26               title="MASSIVE UIL API"
              GET /health (en vivo)   {"service":"MASSIVE UIL API"}
              container_name: massive-uil  (docker-compose.yml)
              log: "[UIL] Iniciado — provider=groq, model=llama-3.3-70b-versatile"
  "UI-NG"   → massive-ui-ng/ · PLAN_INTEGRACION_UI_NG.md · docs/NEXT_GEN_UI_*_ES.md
              logger names massive.ui_ng.*  (11 módulos)
  "MASSIVE" → massive/ · massive_core/ · micro_massive/ · README · pyproject name="massive"

Historial: #28/#29 "Rename project to MASSIVE" · #40 "rename BeyondSight→MASSIVE across CI"
           #51 "renombrado MASSIVE completo" · commits 4b1284af "Remove obsolete … UI-NG naming"
GET /health devuelve "MASSIVE UIL API" → el nombre del servicio expuesto en producción
  sigue siendo el de la primera generación.
```

**Impacto.** El nombre que la API reporta de sí misma en `/health` y en el título de OpenAPI (`MASSIVE UIL API`) no coincide con el nombre del producto (MASSIVE). Un operador que monitoriza por `service=` ve "UIL". Y `docs/architecture/backward_compatibility_aliases.md` —el documento que debería explicar estos alias— está huérfano del nav (D6-009).

**Acción sugerida.** Fijar `title="MASSIVE API"` y `service: "MASSIVE"` en ambos backends; renombrar `uil_adapter.py` → `massive/core/ui_adapter.py` con shim; renombrar los `.jsx` demo; añadir `backward_compatibility_aliases.md` al nav.

**Esfuerzo:** S

---

**ID:** D8-012
**Severidad:** 🟢
**Dominio:** Estética
**Título:** `test-zapier.txt` y `repomix-output.xml`: ambos items sospechosos del brief están ausentes del árbol
**Ubicación:** root
**Estado:** **[CONFIRMADO — RESUELTO]** · **[CONOCIDO PREVIO]**

**Evidencia.**
```
$ ls -A | grep -iE "zapier|repomix-output"      → (vacío)
$ find . -name "test-*.txt" -o -name "test-*.json"  → (vacío)
$ git ls-files | grep -iE "zapier|repomix-output"   → (vacío)
$ git ls-files | grep -i repomix
   .repomixignore · repomix-instruction.md · repomix.config.json   ← los 3 legítimos

Matiz importante: la ausencia de repomix-output.xml NO está protegida por .gitignore,
que tiene el typo `repomack-output*.xml` (D5-019).
Y la ausencia de test-zapier.txt es resultado de una remediación de seguridad real:
   issue/PR #81 "Remove .codebuff folder containing exposed Zapier MCP token"
   gitleaks.toml:11-15  "…the token was revoked by the owner and the secret was purged
                         from the public git history via git filter-repo
                         (fresh-clone scan verified clean)."
```

**Impacto.** Ambos items del contexto previo quedan **RESUELTOS** en cuanto a presencia. Queda una acción residual: corregir el typo de `.gitignore` (D5-019) para que la ausencia de `repomix-output.xml` sea sostenible en el tiempo, y verificar independientemente el purgado del historial (el clone de auditoría es shallow, 1 commit, y no puede confirmarlo).

**Acción sugerida.** D5-019 + un `gitleaks detect --log-opts="--all"` sobre un clone completo.

**Esfuerzo:** XS

---

### DOMINIO 9 — OPTIMIZACIÓN Y RENDIMIENTO

---

**ID:** D9-001
**Severidad:** 🟠
**Dominio:** Rendimiento
**Título:** `LandscapeCache` no tiene TTL: la columna `created_at` se escribe y nunca se lee, y el dict en memoria crece sin límite
**Ubicación:** `cache_manager.py:26-33` (schema) · `:44-57` (`get`) · `:59-75` (`set`)
**Estado:** **[CONFIRMADO]** · punto 9.4 del brief

**Evidencia.**
```python
# cache_manager.py:28-33
conn.execute("""
    CREATE TABLE IF NOT EXISTS landscapes (
        key TEXT PRIMARY KEY,
        config TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
""")
# cache_manager.py:49
cur = conn.execute("SELECT config FROM landscapes WHERE key = ?", (k,))
#                    ↑ created_at NUNCA aparece en ningún SELECT
# cache_manager.py:22
self._memory: dict[str, dict] = {}    # sin maxlen, sin LRU, sin política de desalojo
```
```
$ grep -n "created_at\|ttl\|TTL\|expire\|maxsize\|lru\|evict" cache_manager.py
28:  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP     ← única aparición: la definición
→ 0 lecturas, 0 TTL, 0 política de expiración, 0 límite de tamaño

Únicas vías de invalidación:
  clear()          → DELETE FROM landscapes + self._memory.clear()  (borrado total, manual)
  set(goal, cfg)   → INSERT OR REPLACE  (sobrescribe por clave idéntica)
Consumidores: programmatic_architect.py:14 · tests/test_energy_core.py:11   (2 únicamente)
```

**Impacto.** (1) **Memoria**: en un servidor de larga vida, cada `goal` distinto añade una entrada permanente al dict en memoria; no hay desalojo. Con objetivos generados por LLM (texto libre) la cardinalidad es efectivamente ilimitada. (2) **Frescura**: un paisaje calculado con una versión del motor queda cacheado para siempre; tras actualizar `energy_engine.py` o los pesos CfC, el cache sirve configuraciones obsoletas indefinidamente. (3) La columna `created_at` ocupa espacio y sugiere una funcionalidad de expiración que no existe — es un affordance engañoso para quien lea el esquema.

**Acción sugerida.** Añadir `MASSIVE_CACHE_TTL_SECONDS` (default p. ej. 3600) y filtrar `WHERE created_at > datetime('now', ?)`; usar `functools.lru_cache` o un `OrderedDict` con maxlen para la capa en memoria; exponer `created_at` en una métrica de edad del cache.

**Esfuerzo:** S

---

**ID:** D9-002
**Severidad:** 🟠
**Dominio:** Rendimiento / Seguridad
**Título:** Clave de cache = MD5 truncado a 48 bits del objetivo, sin componente de versión — riesgo de colisión y de envenenamiento entre versiones
**Ubicación:** `cache_manager.py:41-42`
**Estado:** **[CONFIRMADO]** · punto 9.4 del brief ("¿Hay riesgo de cache poisoning?")

**Evidencia.**
```python
def _key(self, goal: str) -> str:
    return hashlib.md5(goal.lower().strip().encode()).hexdigest()[:12]
```
```
Análisis:
  · MD5                       → roto criptográficamente (colisiones construibles); además
                                hashlib.md5() lanza ValueError en Python compilado con FIPS,
                                lo que tumbaría el backend en entornos gubernamentales/bancarios.
  · [:12] hex = 48 bits       → birthday bound ≈ 2^24 = 16.7M entradas antes de colisión probable.
                                Con objetivos generados por LLM en un servicio público, alcanzable.
  · Normalización goal.lower().strip()  → "Reduce polarization" y "reduce   polarization "
                                comparten clave (bien), pero también "REDUCE POLARIZATION"
                                de dos usuarios distintos con contextos distintos.
  · Componentes AUSENTES de la clave:
      – versión del motor / schema (energy_engine, multilayer_engine)
      – versión o hash de los pesos CfC (models/cfc_calibrated/*.pt)
      – MASSIVE_RUNTIME_PARAMS / perfil empírico activo (empirical_config.py)
      – parámetros de la simulación (temperature, n_steps, seed)
      – país/contexto Factbook (massive/core/factbook/context.py)
    → dos llamadas con el mismo texto pero distinta configuración devuelven el MISMO config cacheado.
```

**Impacto.** Dos clases de fallo: (a) **colisión** — un objetivo diferente recibe el paisaje de otro, produciendo una simulación silenciosamente incorrecta (indetectable: no hay log ni métrica de hit/miss); (b) **poisoning entre versiones** — tras un despliegue con nuevos pesos CfC o un nuevo perfil empírico, el cache persiste en SQLite (`.db` en disco) y sigue sirviendo configuraciones de la versión anterior. Como el `.db` por defecto se escribe en el CWD y `data/ui_ng/runs.db` demuestra que estos archivos acaban commiteados (D5-021), el envenenamiento puede incluso versionarse.

**Acción sugerida.** Sustituir MD5 por `hashlib.blake2b(digest_size=16)` (o `sha256` completo, sin truncar); incluir en el material hasheado un `CACHE_SCHEMA_VERSION` + hash de los pesos CfC activos + `MASSIVE_RUNTIME_PARAMS` fingerprint. Añadir contadores `cache_hits`/`cache_misses` a `/metrics`.

**Esfuerzo:** S

---

**ID:** D9-003
**Severidad:** 🟠
**Dominio:** Rendimiento / Fiabilidad
**Título:** La afirmación de thread-safety del cache es falsa y los tres fallos de E/S se tragan en silencio
**Ubicación:** `cache_manager.py:16-19` (docstring) · `:36` · `:56` · `:74` · `:84`
**Estado:** **[CONFIRMADO]** · punto 9.4 del brief ("¿Se invalida correctamente?")

**Evidencia.**
```python
# cache_manager.py:16-19  (docstring de la clase)
"""
Caché clave-valor para paisajes sociales generados por el LLM.
Prioriza velocidad (dict en memoria) y persistencia (SQLite).
Thread-safe para uso concurrente del backend FastAPI que sirve la UI-NG (check_same_thread=False).
"""
```
Análisis de la afirmación:
```
· `check_same_thread=False` sólo desactiva la comprobación de hilo de sqlite3; NO aporta atomicidad.
· Cada método abre y cierra su propia conexión (connect/execute/close) — no hay transacción
  que agrupe la lectura-modificación-escritura.
· `self._memory[k] = cfg` se hace SIN ningún lock (ni threading.Lock ni asyncio.Lock).
  Bajo el event loop de FastAPI + threadpool (los endpoints que llaman a LandscapeCache son
  `async def`, y el cache es síncrono → se ejecuta en el threadpool), dos hilos pueden
  interleavar `get`/`set`.
· Los tres handlers de excepción son `except Exception: pass`:
     :36  _init_db  → print(...) y continuar solo en memoria   (al menos hay un print)
     :56  get       → pass, devuelve None  (falla de lectura = cache miss silencioso)
     :74  set       → pass                 (falla de ESCRITURA = pérdida de datos silenciosa)
     :84  clear      → pass                 (falla de invalidación = el cache NO se limpia)
· `clear()` que falla en silencio es el caso más grave: la única vía de invalidación puede
  no ejecutar la parte SQLite y no ejecutar la parte de memoria de forma atómica
  (`self._memory.clear()` va primero; si el DELETE falla, disco y memoria divergen).
```

**Impacto.** En un despliegue con `--workers > 1` (el `Dockerfile.optimized` usa `--workers 1`, pero `supervisord.conf` no fija workers) cada worker tiene su propio `_memory` y su propio SQLite → inconsistencia garantizada entre workers. Un `database is locked` (muy probable con conexiones no serializadas bajo concurrencia) se convierte en una pérdida silenciosa del paisaje calculado, que es caro de regenerar (requiere llamada LLM). Y `clear()` puede dejar el sistema en un estado donde la memoria dice "vacío" y el disco dice "lleno".

**Acción sugerida.** (1) Un `threading.Lock` alrededor de las operaciones sobre `_memory` y de cada bloque SQLite; (2) reemplazar los tres `except Exception: pass` por `log.warning(..., exc_info=True)` + una métrica `cache_errors_total`; (3) usar una única conexión de larga vida con `isolation_level` explícito, o `sqlite3.connect(..., timeout=30)`; (4) hacer `clear()` transaccional (disco primero, memoria después, o ambas bajo lock); (5) corregir el docstring si no se implementa el lock.

**Esfuerzo:** M

---

**ID:** D9-004
**Severidad:** 🟠
**Dominio:** Rendimiento
**Título:** `energy_engine.py` computa y descarta 6 valores en el cálculo del paisaje — incluido un coeficiente de Gini
**Ubicación:** `energy_engine.py:360, 365, 366, 372, 373, 466`
**Estado:** **[CONFIRMADO]** (coincide con D2-006, aquí desde el ángulo de rendimiento)

**Evidencia.**
```
F841 energy_engine.py:360  Local variable `sigma2` is assigned to but never used
F841 energy_engine.py:365  Local variable `att_positions` is assigned to but never used
F841 energy_engine.py:366  Local variable `att_strengths` is assigned to but never used
F841 energy_engine.py:372  Local variable `rep_positions` is assigned to but never used
F841 energy_engine.py:373  Local variable `rep_strengths` is assigned to but never used
F841 energy_engine.py:466  Local variable `gini` is assigned to but never used
```
Contexto de coste: el README reporta `EnergyEngine | 0.06 s (1K) | 3.1 s (100K) | 35 s (1M) | 16.8 GB required (100M)` — es el motor más caro en memoria del proyecto. `radon` marca `energy_runner.run_energy_simulation` como D(26).

Cruce con la documentación: `MASSIVE_REACTIVE_COHERENCE_PLAN.md` describe un mecanismo de **acoplamiento reactivo por Gini** (`test_reactive_high_gini_reduces_coupling` en `tests/test_cfc_lambda_integration.py`, hoy fallando por D4-001). Es decir, `gini` **debería** estar cableado al acoplamiento, y no lo está.

**Impacto.** Dos impactos separados: (1) **rendimiento** — extracciones de arrays de atractores/repelentes y un cálculo de Gini por paso de simulación que no alimentan nada; en el motor de 16.8 GB esto no es despreciable; (2) **funcional, más grave** — la hipótesis fuerte es que `gini` es el eslabón perdido del mecanismo de coherencia reactiva que el plan describe y que los tests (fallando) esperan. No es código muerto: es código **desconectado**.

**Acción sugerida.** Verificar contra `MASSIVE_REACTIVE_COHERENCE_PLAN.md` si `gini` debe modular el acoplamiento; si es así, cablearlo y hacer pasar `test_reactive_high_gini_reduces_coupling`. Para los 5 restantes, decidir entre cablear (si `att_positions`/`rep_positions` debían alimentar el cálculo del potencial) o eliminar.

**Esfuerzo:** M

---

**ID:** D9-005
**Severidad:** 🟠
**Dominio:** Rendimiento / Documentación
**Título:** La tabla de escalabilidad del README no es reproducible desde nada que exista en el repositorio
**Ubicación:** `README.md:216-238` · `benchmark_scalability.py` (908 líneas, 483 stmts)
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
README.md:220-223
| Engine                          | 1K agents      | 100K          | 1M            | 100M            |
| **MassiveEngine** (LOD aggregated) | 0.39 s · 0.87 GB | 2.3 s · 0.87 GB | 21 s · 0.88 GB | **44 s · 8.3 GB** |
| EnergyEngine                    | 0.06 s       | 3.1 s         | 35 s          | 16.8 GB required |
README.md:29  "100 million agents run in ~8 GB RAM — near-constant memory with event-driven,
               uint8-quantized sparse updates"

Verificación de la cadena de evidencia:
  benchmark_scalability.py    483 stmts · cobertura 0.0 %
  benchmark_scalability.py:29 import psutil        ← NO declarado en requirements (D5-005)
  $ python -c "import benchmark_scalability"
    ModuleNotFoundError: No module named 'psutil'   ← el script ni siquiera importa
  $ grep -rn "benchmark_scalability" .github/workflows/  → 0 resultados (ningún CI lo ejecuta)
  $ ls profiling_results/     → No such file or directory   (item del brief: NO existe)
  $ git ls-files | grep -iE "benchmark.*\.(json|md)$"
     reports/sota_baselines/{metrics.json,report.md} · reports/cluster_run/… · reports/real_validation/…
     → NINGÚN artefacto con las cifras 0.39 s / 0.87 GB / 44 s / 8.3 GB
  README.md no cita commit, fecha, hardware ni comando para ninguna de las cifras
  Extrapolación independiente (punto 9.3 del brief):
     10k agents uint8 1D → peak 9.9 KB → 100M → 0.094 GB
     vs. 8.3 GB declarados → factor 88×. La diferencia es estado no cuantizado
     (matriz de adyacencia, historial, float64 de 5 capas) que la narrativa
     "uint8-quantized" no menciona.
Contraste: el benchmark PVU SÍ es reproducible — `make benchmark`, `benchmarks/runner.py`,
  `datasets/pvu_cases/`, `pvu-validation.yml`, `publish.yml:job benchmark`. La diferencia
  de rigor entre la validación científica y la afirmación de rendimiento es notable.
```

**Impacto.** Es la afirmación más llamativa del README —está en el tagline de la primera pantalla ("from 10 agents to 100 million") y en la primera fila de la tabla frontier— y es la menos verificable. El script que la generaría no importa, no está declarado, no corre en CI, y no hay artefacto commiteado. Un revisor técnico (o un reviewer de paper) que intente reproducirla se bloquea en el primer paso.

**Acción sugerida.** (1) Añadir `psutil` a requirements (D5-005). (2) Ejecutar el benchmark y commitear el resultado en `reports/scalability/{metrics.json, report.md}` con metadata completa (fecha, commit SHA, CPU, RAM, versión de numpy). (3) Citar ese archivo desde la tabla del README. (4) Añadir un job de CI nocturno que ejecute una configuración reducida (1K/10K) y falle si el tiempo o la RAM se desvían >20 % del baseline commiteado. (5) Reformular "uint8-quantized" para reflejar qué está cuantizado y qué no.

**Esfuerzo:** M

---

**ID:** D9-006
**Severidad:** 🟡
**Dominio:** Rendimiento
**Título:** `profiling_results/` no existe; el material de profiling está disperso en 3 sitios sin conexión con CI
**Ubicación:** `scripts/profile_hotspot.py` · `docs/performance_report.md` · `docs/performance/baseline.md` · `docs/OPTIMIZATION_STATUS.md` · `REPORT_OPTIMIZATION.md`
**Estado:** **[CONFIRMADO — el item del brief está RESUELTO/ausente]** · punto 9.1 del brief

**Evidencia.**
```
$ ls profiling_results/  → No such file or directory
$ ls -d reports/*  → cluster_run enkf_full_i3_s002 enkf_pilot enkf_pilot_i3_s002 factbook_validation_*
                     investigador_de_tendencias.md phase2_synthesis.md phase4_qa_validation.md
                     production_readiness_check.md real_validation research sota_baselines validation
                   → ningún directorio de profiling

Lo que SÍ existe:
  scripts/profile_hotspot.py   (1 991 bytes) — helper cProfile, bien construido:
      docstring con usage, sys.path setup con Path(__file__).resolve().parents[1],
      argparse con --top, carga multilayer + energy, imprime top cumulative.
      Cobertura: no medido (scripts/ no está en el source de coverage).
      CI: 0 referencias → nunca se ejecuta automáticamente.
  docs/performance/baseline.md   ← en el nav de MkDocs, sección "Production Readiness"
  docs/performance_report.md     ← HUÉRFANO del nav (D6-009)
  docs/OPTIMIZATION_STATUS.md    ← HUÉRFANO del nav; tabla FASE 1-5 con estado por fix
  REPORT_OPTIMIZATION.md         ← en root, fecha 2025-07-24, premisa Numba obsoleta (D6-007)
```
Sobre la pregunta del brief *"¿Las optimizaciones identificadas fueron implementadas?"*: `docs/OPTIMIZATION_STATUS.md` responde con una tabla de 5 fases y estado por ítem — **Done / Partial / Rejected (intentional) / Rejected (policy)**. Es un buen artefacto de trazabilidad. Pero los 3 problemas críticos de `REPORT_OPTIMIZATION.md` tienen destino dispar: #1 (Numba) quedó obsoleto, #2 (loops O(N²) en network inference) sigue abierto —`massive_core/network_inference/reconstruct.py` está al 20.7 % de cobertura—, y #3 (historial completo en memoria) no tiene entrada de estado en ningún documento.

**Impacto.** El conocimiento de rendimiento existe pero está fragmentado en 5 documentos, 2 de ellos huérfanos del sitio publicado y 1 con premisa obsoleta. No hay baseline numérico commiteado contra el que comparar (D9-005), así que no se puede saber si una optimización ayudó.

**Acción sugerida.** Consolidar en `docs/performance/baseline.md` (que ya está en el nav): cifras reproducibles + comando + artefacto. Marcar `REPORT_OPTIMIZATION.md` como histórico. Añadir un target `make profile` que ejecute `scripts/profile_hotspot.py` y escriba en `reports/profiling/` (gitignored).

**Esfuerzo:** S

---

**ID:** D9-007
**Severidad:** 🟡
**Dominio:** Rendimiento
**Título:** El fallback Python de `rust_core.py` es correcto y está testeado, pero no existe test de paridad entre las dos implementaciones
**Ubicación:** `massive_core/rust_core.py` · `rust_core/src/lib.rs` · `tests/test_rust_core_wrapper.py`
**Estado:** **[CONFIRMADO]** · punto 9.2 del brief

**Descripción.** Respuesta a la pregunta del brief *"¿El fallback Python está implementado correctamente?"* — **sí**. La verificación línea por línea contra el Rust coincide en los tres kernels y en las guardas de dimensión. El problema no es el fallback: es que la otra rama nunca se ejecuta, así que nada impide que diverja.

**Evidencia.** Comparación expresión por expresión:

| Kernel | Rust (`lib.rs`) | Python (`rust_core.py`) | ¿Idénticos? |
|---|---|---|---|
| `multi_potential_gradient` | `bimodal_grad(op) = 4·op·(op²−0.49)`; `coop: 2·(coop − 0.8·align)` con `align = 0.5(op+1)`; `hier: −2·hier(1−hier)(2hier−1)`; `income: 0.5(inc−0.5)(1+hier)`; `info: 0.3(info−0.5−0.2coop)` | mismas 5 expresiones, mismas constantes | ✓ |
| guardas de dimensión | `if kdim > COL_COOP` … `COL_INFO` | `if arr.shape[1] > 1` … `> 4` | ✓ |
| `langevin_opinion_update_inplace` | clip a `[x_min, x_max]` sobre la columna 0 | `agents[:,0] = clip(agents[:,0] + drift·dt + σ·diffusion + jumps, x_min, x_max)` | ✓ |
| `active_mask_step` | `changed \| neighbor_active` | mismo, con rama vacía para `changed.any() == False` | ✓ |

```
$ cat massive_core/rust_core.py | head -20
RUST_CORE_AVAILABLE: Final[bool] = importlib.util.find_spec("massive_rust_core") is not None
if RUST_CORE_AVAILABLE: import massive_rust_core as _rust_core
else:  # pragma: no cover - exercised implicitly in environments without maturin builds
       _rust_core = None
→ El `# pragma: no cover` está en la rama QUE SIEMPRE SE EJECUTA (D3-018), y las ramas
  `if _rust_core is not None` son las que NUNCA se ejecutan. Es exactamente al revés de lo
  que el pragma sugiere.

coverage.json: massive_core/rust_core.py  48 stmts · 81 % · sin cubrir: 19, 35, 40->44, 44->47,
               47->49, 49->51, 82-92, 119   ← todas las ramas Rust
tests/test_rust_core_wrapper.py: 3 tests, 0 docstring de módulo (D6-011), ejercitan solo el fallback.
```

**Impacto.** El fallback es correcto **hoy**. Pero como la rama Rust jamás se ejecuta en ningún entorno automatizado, cualquier cambio en `lib.rs` puede divergir del Python sin que nada lo detecte. En un código numérico, una divergencia de constantes (p. ej. `0.49` vs `0.5`) produciría resultados científicos distintos según si el usuario compiló la extensión — indetectable y no reproducible.

**Acción sugerida.** Test de paridad parametrizado que, cuando `RUST_CORE_AVAILABLE` sea True, compare las dos implementaciones sobre matrices aleatorias con `np.testing.assert_allclose(rtol=1e-12)` para los 3 kernels. Extraer las constantes a un módulo compartido documentado. Corregir la colocación del `# pragma: no cover`.

**Esfuerzo:** S

---

**ID:** D9-008
**Severidad:** 🟡
**Dominio:** Rendimiento / Arquitectura
**Título:** `multilayer_engine_sparse.py` (789 líneas) duplica `multilayer_engine.py` (1 025 líneas) y está exento de typing
**Ubicación:** `massive_core/numerics/multilayer_engine_sparse.py` · `multilayer_engine.py` · `mypy.ini:47-51`
**Estado:** **[CONFIRMADO]**

**Evidencia.**
```
multilayer_engine.py                          1025 líneas · 339 stmts · 95 % cobertura · 14 defs top-level
massive_core/numerics/multilayer_engine_sparse.py 789 líneas · 286 stmts · 52 % cobertura
   líneas sin cubrir: 53,56,59,67,83,87,102,130-140,145,150,154-158,167-170,197,201-205,248,
     271,281-309,359,404-432,445-452,463-464,479->491,489,543-544,555,620,632-647,663-675,
     709-726,740-743,754-779,783,787-789
mypy.ini:
   [mypy-massive_core.numerics.*]      disallow_untyped_defs = True
   [mypy-massive_core.numerics.multilayer_engine_sparse]
       disallow_untyped_defs = False
       check_untyped_defs = False
       # "Sparse engine is large / legacy-shaped; keep typed-defs policy but allow incomplete
       #  internal typing until a dedicated cleanup PR."
tests/test_sparse_refactor.py: 26 tests  ← la suite más grande del repo tras test_massive_engine
vulture: massive_engine.py:918 unused attribute '_layers_csr'  ← la estructura CSR huérfana
CHANGELOG.md / issue #65: "feat: memory breakdown + sparse CSR event-driven reactivation"
issue #53: "Feature/scientific extensions sparse engine"
```

**Impacto.** Dos implementaciones de la dinámica multicapa que deben producir resultados equivalentes. La densa tiene 95 % de cobertura y typing; la dispersa 52 % y exención de typing. No hay un test de equivalencia denso↔disperso identificado (los 26 tests de `test_sparse_refactor.py` cubren la dispersa, no la paridad). Y el "dedicated cleanup PR" no tiene issue ni fecha asociada.

**Acción sugerida.** Test de paridad denso↔disperso sobre el mismo seed y la misma entrada (tolerancia 1e-10); subir la cobertura de la dispersa al nivel de la densa; poner número de issue al opt-out de mypy; retirar `_layers_csr` si está muerto.

**Esfuerzo:** M

---

**ID:** D9-009
**Severidad:** 🟡
**Dominio:** Rendimiento
**Título:** La narrativa de "uint8-quantized" no explica el footprint real: la extrapolación naive queda 88× por debajo de lo declarado
**Ubicación:** `README.md:29` · `massive_engine.py` · `massive/core/state_compression.py`
**Estado:** **[CONFIRMADO]** · punto 9.3 del brief

**Evidencia.**
```
$ python -c "
import tracemalloc, numpy as np
tracemalloc.start()
agents = np.zeros(10000, dtype=np.uint8)
current, peak = tracemalloc.get_traced_memory()
tracemalloc.stop()
print(f'10k agents peak: {peak/1024:.1f} KB')
print(f'Extrapolación 100M agents: {peak*10000/1024/1024/1024:.2f} GB')"

10k agents peak: 9.9 KB
Extrapolación 100M agents: 0.09 GB          ← el estado puro uint8
README.md:222  MassiveEngine (LOD) 100M → 8.3 GB     ← 88× más
README.md:29   "100 million agents run in ~8 GB RAM — near-constant memory with
                event-driven, uint8-quantized sparse updates"

Qué explica la diferencia (inspección de código, no medición):
  · massive_engine.py usa 5 capas (layer_weights=(0.4,0.3,0.3) en simulation_service) en float64
  · MassiveSimEngine.__init__(config) → self.agents = self.initialize_agents(cfg): matriz N×K float
  · SleepWakeup (massive_engine.py:346) mantiene self._active (bool N), self._history (list[float])
  · state_compression.compress_agent_states hace SVD truncado (max_bond_dim=32, explained_variance=0.99)
    → el LOD sí comprime, pero sobre una matriz float64 que primero se materializa
  · multilayer_engine construye matriz de adyacencia → O(N²) en el caso denso
    (la variante sparse CSR existe pero está al 52 % de cobertura, D9-008)
  · simulator.py almacena historial completo O(steps × estado)  ← REPORT_OPTIMIZATION.md §3, sin estado de fix
Nota: el test del brief es deliberadamente naive (1D uint8 ≠ el estado real de 5 capas),
  así que la discrepancia no invalida la cifra del README — invalida la NARRATIVA:
  el footprint no está dominado por el estado uint8 sino por estructuras auxiliares float64.
```

**Impacto.** La afirmación "near-constant memory with uint8-quantized sparse updates" sugiere al lector que el coste es ~0.1 GB a 100M agentes, cuando la cifra real declarada por el propio README es 8.3 GB. La discrepancia entre la narrativa y el número, dentro del mismo documento, es lo que un lector técnico notará. Además "near-constant" es comprobable: la tabla del README sí muestra 0.87 → 0.87 → 0.88 → 8.3 GB, es decir **constante hasta 1M y luego un salto de 9.4×** — que no es "near-constant", es escalonado.

**Acción sugerida.** Reformular: *"LOD super-agents keep memory flat (~0.9 GB) up to 1M agents; at 100M the quantized super-agent representation requires ~8.3 GB"*. Publicar el desglose de memoria por estructura (el issue #65 "memory breakdown" sugiere que ya se hizo — recuperar ese análisis y commitearlo en `docs/performance/baseline.md`).

**Esfuerzo:** S

---

**ID:** D9-010
**Severidad:** 🟡
**Dominio:** Rendimiento
**Título:** El historial de simulación se acumula en memoria sin política de streaming ni checkpointing documentado
**Ubicación:** `simulator.py` (`simular`, `store_history`) · `massive_engine.py` · issue/PR #83
**Estado:** **[CONFIRMADO]** por cobertura y documentación · **[HIPÓTESIS]** en cuanto al coste medido

**Evidencia.**
```
REPORT_OPTIMIZATION.md:15  "3. **Historial de estado completo en memoria** —
                            O(steps × N × K) bytes acumulados"
   → identificado como crítico nº 3 en 2025-07-24; sin entrada correspondiente en
     docs/OPTIMIZATION_STATUS.md (que cubre FASE 1-5 pero no este punto)

Issue/PR #83  "fix: correct store_history memory bug and dead code from PR #82"
Issue/PR #82  "fix: Phase D/E — PERF-01 streaming aggregation & OBS-01 diagnostics"
CHANGELOG.md  menciona PERF-01 streaming aggregation
   → hubo trabajo de streaming, pero la documentación de rendimiento no registra el estado final

Líneas de simulator.py sin cubrir relevantes para el historial:
   1846-1893 · 1965-1993 · 2013-2024 · 2045-2073 · 2134-2135 · 2146-2149 · 2156-2168 ·
   2321-2422 · 2429-2457   ← los bloques finales (IntegratedSimulator, checkpointing)
   Cobertura simulator.py: 876 stmts · 274 sin cubrir · 67 %
massive/core/state_compression.py  ← compress/decompress_agent_states existe
   $ grep -rn "compress_agent_states" --include="*.py" . | grep -v "state_compression.py"
   → 0 consumidores fuera del propio módulo y del shim de root
   Es decir: la compresión de estado está implementada y NO se usa en ningún engine.
```

**Impacto.** `state_compression.py` (SVD truncado con `max_bond_dim` y `explained_variance`) es exactamente la herramienta para el problema #3, y está implementada, documentada, expuesta vía shim deprecado en root… y no la consume ningún motor. Es capacidad construida y no desplegada. Para simulaciones largas a gran escala, el historial sigue creciendo linealmente.

**Acción sugerida.** Verificar si `PERF-01` (streaming aggregation) ya resuelve el problema y documentarlo en `docs/performance/baseline.md`; si no, cablear `compress_agent_states` en el bucle de historial de `simulator.py`/`massive_engine.py` con un flag de config (`history_compression: {enabled, max_bond_dim, explained_variance}`) y un test de round-trip.

**Esfuerzo:** M

---

**ID:** D9-011
**Severidad:** 🟢
**Dominio:** Rendimiento
**Título:** Complejidad ciclomática media B (9.53) — razonable para un codebase científico de 49 K LOC
**Ubicación:** repo completo
**Estado:** **[CONFIRMADO — POSITIVO]** · punto 2.4 del brief

**Evidencia.**
```
$ radon cc . -s -n B --average
312 blocks (classes, functions, methods) analyzed.
Average complexity: B (9.532051282051283)

Distribución de los peores (12 bloques ≥ D, sobre 312 = 3.8 %):
  F (2):  build_narrative 57 · _dispatch 50            ← ambos con plan de acción (D2-011)
  E (2):  interpret 39 · _score_case 32                ← ambos en massive-ui-ng (fuera de CI)
  D (8):  buscar_estrategia_inversa 27 · run_energy_simulation 26 · simular 26 ·
          compute_median_results 24 · main 24 · test_cultural_profiles 23 ·
          _schema_to_ts 22 · _schema_to_ts 22 (duplicado)
simulator.py:1530 simular → D(26) para una función que implementa 13 reglas de dinámica
  es, en contexto, aceptable.
```

**Impacto.** Positivo. Un promedio B con sólo 3.8 % de bloques en D+ indica que la complejidad está concentrada y localizada, no distribuida. Los dos peores casos están en el subproyecto fuera de CI y en el dispatcher del orquestador — ambos con remedio claro.

**Acción sugerida.** Añadir `radon cc . -n C --average` como check informativo (no bloqueante) en CI, con umbral de regresión sobre el promedio.

**Esfuerzo:** XS

---

## 3. TABLA DE PRIORIDADES

Ordenada por **prioridad de ejecución**: severidad y efecto de desbloqueo, con el esfuerzo como desempate — los *quick wins* primero dentro de cada banda.

### 🚨 Banda 0 — Desbloquear (hacer primero, en este orden)

| # | ID | Título | Sev | Esf | Desbloquea |
|---|---|---|---|---|---|
| 1 | **D1-001** | `_lambda_corrector` no inicializado → `import simulator` falla sin torch | 🔴 | **XS** | D1-004, D1-009, D4-010, D7-003, 25 módulos, 21 archivos de test |
| 2 | **D7-004** | `Dockerfile.optimized:1` no es sintaxis Docker | 🔴 | **XS** | D7-005, docker-e2e |
| 3 | **D2-002** | `black .` (30 archivos) | 🔴 | **XS** | lint.yml, publish.yml |
| 4 | **D2-001** | `ruff check . --fix` + 10 manuales | 🔴 | **S** | lint.yml, publish.yml (8 jobs) |
| 5 | **D5-019** | Typo `.gitignore` `repomack`→`repomix` | 🟡 | **XS** | evita commitear el bundle |
| 6 | **D8-003** | `LICENSE` → texto canónico Apache-2.0 | 🟠 | **XS** | badge de licencia de GitHub |
| 7 | **D6-013** | Puerto de MkDocs en README (8000→8001) | 🟡 | **XS** | — |
| 8 | **D6-016/17** | Arreglar los 2 archivos de agentes de `.github/` | 🟡 | **XS** | 2 agentes actualmente inactivos |
| 9 | **D4-006** | Añadir `httpx` a requirements | 🟠 | **XS** | 3 archivos de test (incl. los de seguridad) |
| 10 | **D5-005** | Añadir `psutil` a requirements | 🟠 | **S** | `benchmark_scalability.py`, D9-005 |

### 🔴 Banda 1 — Críticos restantes

| # | ID | Título | Esf | Nota |
|---|---|---|---|---|
| 11 | **D1-003** | `extended_models` import roto y silencioso | **XS** | Bayes/Nash/SIR desactivados |
| 12 | **D1-002** | Fallback NumPy falso en `cfc_engine.py` | S / L | decidir con D5-008 |
| 13 | **D5-001** | Sin cotas en `pasos`/`n_agents`/`max_intentos` | **M** | DoS; resolver con D3-004 |
| 14 | **D4-001** | 12 tests fallan: faltan 3 archivos `.pt` | **M** | LFS o skips o regenerar |
| 15 | **D7-003** | Job `core` de CI sin torch | **S** | depende de #1 y #12 |
| 16 | **D5-002** | `pip install -e .` imposible (maturin/Rust) | **L** | separar paquete Python de extensión Rust |
| 17 | **D3-001** | `packages.find` omite 31 módulos root + `metrics/` | **L** | bloquea PyPI; acoplado a D5-002 |
| 18 | **D3-003** | Colisión de namespace `backend` | **M** | bloquea `mypy .` (D2-004) |
| 19 | **D7-002** | Verdear los 7 gates de CI | **L** | agregado de #1-#18 |
| 20 | **D6-001** | 4 afirmaciones falsas en la tabla de calidad del README | **M** | hacerla generada por CI |
| 21 | **D7-001** | Restaurar la señal de CI (billing) | XS* | *fuera del alcance del código |

### 🟠 Banda 2 — Altos

| # | ID | Título | Esf |
|---|---|---|---|
| 22 | D3-004 | Cablear los DTOs Pydantic como cuerpos de request | M |
| 23 | D7-006 | Corregir `llm_orchestrator.py:479` y retirar `\|\| true` / `continue-on-error` | M |
| 24 | D2-004 | `exclude` en `mypy.ini` | XS |
| 25 | D9-001/2/3 | TTL + clave blake2b versionada + locks y logging en `cache_manager.py` | M |
| 26 | D9-004 / D2-006 | Las 6 variables descartadas de `energy_engine.py` (¿`gini` desconectado?) | M |
| 27 | D5-003 | Lockfile + pinning | M |
| 28 | D5-004 | Unificar requirements.txt ↔ pyproject.toml | M |
| 29 | D5-006/7 | Retirar `streamlit`/`torchdiffeq`; separar dev de runtime | S |
| 30 | D5-022 | `.dockerignore`: `models/` excluido de la imagen de producción | S |
| 31 | D6-003 | Mover 13 `.md` de root a `docs/` | S |
| 32 | D6-009 | Añadir los 35 docs huérfanos al nav de MkDocs | S |
| 33 | D6-005 | Eliminar las 16 rutas `/home/adlg/` | S |
| 34 | D6-002 | Sincronizar cifras README ↔ README_ES | S |
| 35 | D6-006/7/8 | Fechas imposibles, reporte Numba obsoleto, system map fantasma | S/M |
| 36 | D4-002 | Corregir 68 %→59.6 % y subir `fail_under` de 30 a 55 | S |
| 37 | D4-003/4 | Cobertura: CLI, trainer CfC, extended_models, 4 routers | L |
| 38 | D4-005/14 | 140 tests sin aserción; migrar unittest→pytest | M |
| 39 | D3-002/5 | Decidir el destino de los 3 backends y 2 frontends | XL |
| 40 | D3-006/7 | Split de `simulator.py` (2 457 líneas) y de los 5 engines | XL |
| 41 | D3-017/18 | Un solo `Cargo.toml` + job de CI Rust + test de paridad | M |
| 42 | D7-005 | Resolver el bucle compose↔Dockerfile | M |
| 43 | D7-007 | `massive-ui-ng`: workflow muerto → activar o archivar | M |
| 44 | D7-008 | Hacer alcanzable el pipeline de publicación (tag + release) | L |
| 45 | D8-001/2 | Reducir root de 106 a ≤20 entradas; crear el primer release | L/M |
| 46 | D9-005 | Hacer reproducible la tabla de escalabilidad del README | M |
| 47 | D2-003 | Quemar los 198 errores de mypy (36 del slice primero) | L |
| 48 | D2-005 | 26 excepciones silenciadas → log o re-raise | M |
| 49 | D2-012 | Consolidar los 3 `train_cfc_*.py` clonados | M |
| 50 | D2-013 | Decidir sobre `social_connectors.py` y demás código muerto | M |
| 51 | D5-009/10/13/14/15 | `/metrics` sin auth, `ALLOWED_HOSTS=*`, env default inseguro, CSP, nginx headers | S/M |
| 52 | D6-012 | Unificar las 9 versiones y colapsar el CHANGELOG | S |
| 53 | D4-011/12 | Convergencia de baselines PVU + correr los 12 casos reales | M |

### 🟡 Banda 3 — Medios (69 hallazgos)

Agrupados por afinidad para asignación eficiente:

| Grupo | IDs | Esf |
|---|---|---|
| Logging y observabilidad | D2-008, D2-009, D2-010, D1-008, D3-014 | M |
| Nomenclatura y i18n de identificadores | D2-014, D8-011, D6-015 | M |
| Empaquetado y configuración Python | D3-008, D3-010, D3-012, D3-013, D7-014, D7-019, D7-020 | L |
| Superficie HTTP y versionado | D3-011, D6-014, D5-011, D5-012 | M |
| Seguridad de despliegue | D5-016, D5-023, D7-012, D7-013, D5-024 | M |
| Infraestructura de contenedores | D7-015, D7-016, D5-020, D5-021 | M |
| Documentación y sitio | D6-010, D6-011, D6-018 (+linkcheck), D8-004, D8-005, D8-006, D8-010 | M |
| Tests y validación | D4-007, D4-008, D4-009, D2-017 | M |
| Rendimiento y ciencia | D9-007, D9-008, D9-009, D9-010, D9-006, D9-011 (+CI check) | L |
| Utilidades y scripts | D3-019, D2-011, D2-016, D3-016 | M |

### 🟢 Banda 4 — No requieren acción (17 hallazgos positivos o ya resueltos)

`D1-007` `D1-010` `D2-007` `D2-015` `D3-015` `D3-020` `D4-013` `D5-017` `D5-018` `D6-018` `D6-019` `D7-017` `D7-018` `D8-008` `D8-009` `D8-012` `D9-011` — **preservar explícitamente** durante la remediación: son los activos que no deben romperse. El harness de verificación de la tarea `W0-T01` del workflow los incluye como guardarraíles.

---

## 4. LO QUE FUNCIONA BIEN

Inventario honesto de los activos del proyecto. Estos puntos deben **protegerse** durante cualquier refactorización.

### 4.1 El camino principal funciona, verificado en vivo
- **El Quick start del README es real** (D8-008): 5 pasos, ~3 minutos, y produce un servidor operativo. `GET /health`, `/ready`, `/version`, `POST /v1/simulate` responden correctamente; la ausencia de clave devuelve 401 (fail-closed).
- **La API pública en español es estable y coherente**: `simular(estado, pasos, cada_n_pasos, verbose)` acepta exactamente las claves documentadas (`opinion`, `propaganda`, `confianza`, `opinion_grupo_a/b`, `pertenencia_grupo`) y `resumen_historial` devuelve un dict rico y legible con `regla_dominante` nombrada (D8-009).
- **Modo degradado correcto**: sin claves LLM, `/ready` reporta `mode: degraded` con `llm_provider: not_configured` y las simulaciones básicas siguen funcionando. Es el diseño correcto para un sistema "LLM opcional".

### 4.2 Higiene de código por encima de la media
- **0 `except:` desnudos** en 245 archivos (D2-007). Muchos proyectos maduros no pueden afirmar esto.
- **0 marcadores TODO/FIXME/HACK** en el código Python; la deuda vive en documentos de backlog dedicados (D2-015).
- **0 errores de sintaxis y 0 imports relativos rotos** (D1-010).
- **28 issues de ruff en 49 174 LOC** = 0.57 issues/KLOC con el ruleset del proyecto. Es un número bajo.
- **Complejidad ciclomática media B (9.53)** con sólo 3.8 % de bloques en D+ (D9-011).
- **Todos los paquetes tienen `__init__.py`** y `massive_core/` está 100 % documentado con docstrings de módulo.

### 4.3 Cultura de pruebas real (no teatral)
- **666 funciones de test, 681 tests recolectables, 669 pasan** en entorno completo, en ~28 s.
- **Ratio de mocks de 0.10 por test** — la suite prueba el sistema real, no dobles (D4-013).
- **Sólo 2 `skipif` en toda la suite**, ambos justificados (torch opcional), y **0 `xfail`** — no hay deuda de tests escondida detrás de skips.
- **59 archivos de test** con nombres descriptivos y organización por capacidad (`test_api_security`, `test_rng_reproducibility`, `test_engine_reproducibility`, `test_contracts`, `test_cross_engine_polarization`, `test_obs02_stability`).
- **Cobertura medida del 59.62 %** con 45 archivos al 100 % — por encima del umbral típico de proyectos de investigación.
- Existe `tests/test_api_security.py` diseñado como **test de paridad** entre `api.py` y `backend/app/security.py` para impedir que la autenticación diverja. La intención es exactamente la correcta.

### 4.4 Rigor científico inusual para un repo de este tamaño
- **Protocolo de validación pre-registrado** bilingüe (`docs/validation/PVU_MASSIVE_{EN,ES}.md`) con plantillas de pre-registro y de reporte, y un disclaimer de casos de muestra **escrito en el propio output del runner**.
- **12 casos de validación reales** con datos históricos: Brexit 2016, Elecciones Brasil 2022, Estallido Chile 2019, Paro Colombia 2021, Primavera Árabe Egipto 2011, Gilets Jaunes Francia 2018, PEGIDA Alemania 2014, Hong Kong 2019, Mahsa Amini Irán 2022, Golpe Myanmar 2021, Candlelight Corea del Sur 2016, Elecciones EE.UU. 2020 — cada uno con `meta.json` + `interventions.json` + `timeseries.csv`.
- **10 baselines comparativos** en el runner PVU: naive, seasonal_naive, moving_average, ar1, random_regime, ets, arima, ridge_lags, random_forest, gradient_boosting. Compararse contra baselines es la práctica correcta y pocos simuladores sociales lo hacen.
- **Sembrado de RNG en todas partes**: `PYTHONHASHSEED=42` en los 5 workflows que ejecutan código, `--seed 42` en Makefile/install.sh/CI, `massive_core/utils/rng.py` dedicado, tests de reproducibilidad (`test_rng_reproducibility.py`, `test_engine_reproducibility.py`). La fase 1 del workflow de optimización fue explícitamente *"RNG reproducibility critical fixes"* y está marcada como **Done**.
- **`experiments/` con estructura numerada** (00_smoke → 08_enkf_delta) y resultados commiteados — trazabilidad de la investigación.
- **Capa científica opt-in bien aislada**: `massive_core/` con numéricos (steppers adaptativos, solvers, estabilidad, bifurcación), EnKF, PINNs, inferencia de redes, mecánica estadística, teoría de perturbaciones — todo *"behind explicit config flags that never alter the default dynamics"*. El diseño de no contaminar la dinámica por defecto es correcto.

### 4.5 Seguridad: intención y mecanismos correctos
- **0 secretos trackeados** y `pip-audit` limpio (D5-017, D5-018).
- **`llm_credentials.py` está bien diseñado**: store en memoria en lugar de mutar `os.environ`, con el razonamiento escrito en el código (*"leaks keys to subprocesses, overwrites HF Secrets, leaves stale values"*). Es exactamente la solución correcta a un problema real.
- **Comparación de claves en tiempo constante** con `hmac.compare_digest` en un módulo compartido (`massive_core/config/api_auth.py`) cuyo docstring declara que existe para que `api.py` y `backend/app/security.py` *"cannot diverge again (enforced by tests/test_api_security.py parity tests)"*.
- **`massive_core/config/api_auth.py` como fuente única de verdad** de la semántica de autenticación es la decisión arquitectónica correcta frente a la duplicación de backends.
- **Respuesta madura a un incidente real**: el token de Zapier expuesto en `.codebuff/` fue revocado por el propietario, purgado del historial con `git filter-repo`, verificado con scan de fresh-clone, y documentado en `gitleaks.toml` con fecha (2026-08-22) y referencia al modelo de amenazas. Eso es gestión de incidentes de nivel profesional.
- **Infraestructura de seguridad presente**: `gitleaks.toml` con allowlist razonada y comentada, `secret_scan.yml`, `scripts/security_audit.sh`, `docs/security/threat-model.md`, `docs/security/secrets-and-configuration.md`, `.gitignore` con secciones explícitas anti-fuga de credenciales, `.dockerignore` excluyendo `.env*`.
- **CORS correcto**: sin wildcard cuando hay credenciales, con filtrado explícito de `"*"` en `api.py:59` y fallback a orígenes concretos.
- **Límites de tamaño de cuerpo** (`MASSIVE_MAX_BODY_MB`, 413 antes de procesar), **rate limiting** por IP con backend memory/file, **`X-Request-ID`** y **W3C TraceContext** verificados en vivo, **usuario no-root** en el Dockerfile con `setcap` para bindear :80.

### 4.6 Documentación: volumen y estructura de nivel enterprise
- **60 documentos en `docs/`** con estructura deliberada: `architecture/` (19), `validation/` (7), `runbooks/` (3: local-development, operations, incidents), `security/` (2), `performance/`, `testing/`, `cards/`, `research/`, `development_history/`.
- **`mkdocs build --strict` pasa con 0 warnings y 0 enlaces de nav rotos** (D6-018).
- **Runbooks y DR plan reales**: `docs/disaster_recovery_plan.md` con RTO 30 min / RPO 5 min y 4 escenarios, más 4 scripts de backup/verificación (`backup_factbook.sh`, `backup_models.sh`, `backup_simulations.sh`, `verify_backup.sh`).
- **`docs/OPTIMIZATION_STATUS.md` con trazabilidad por ítem** (FASE 1-5, estado Done/Partial/Rejected con justificación) — es el artefacto correcto para gestionar deuda y pocos repos lo tienen.
- **`docs/architecture/` incluye documentos de alto valor**: `domain_ownership.md`, `sensitive_zones.md`, `module_inventory.md`, `simulator_dependency_map.md`, `contracts_and_boundaries.md`, `backward_compatibility_aliases.md`, `compatibility_map.md`. El problema es que 17 de 19 están huérfanos del nav (D6-009), no que no existan.
- **README bilingüe con estructura idéntica de 11 secciones** (D6-002) — la paridad estructural EN/ES está lograda; sólo divergen las cifras.
- **`docs/NAMING_CONVENTIONS.md`** existe y se cita como justificación de decisiones de no-refactorización.

### 4.7 Herramientas de desarrollador bien construidas
- **`Makefile` con 17 targets y `make help` auto-generado** desde los comentarios `##` — la mejor interfaz del repo (D7-018).
- **`install.sh` con `set -euo pipefail`**, detección de binario Python, verificación de versión, salida en color condicional a TTY y 11 subcomandos documentados.
- **Scripts de utilidad propios de calidad**: `scripts/todo_triage.py` (parser de TODOs con clasificación de prioridad por keywords y salida Markdown), `scripts/profile_hotspot.py` (cProfile con argparse y setup de `sys.path` correcto), `scripts/typecheck_slice.py` (adopción gradual de mypy con lista explícita de targets y flag `--strict-sparse`).
- **`scripts/gen_ts_types.py` funciona y los tipos generados están sincronizados** con los DTOs Pydantic (verificado: diff cero tras regenerar, D3-020), con un workflow dedicado que lo hace cumplir.
- **`repomix.config.json` bien configurado**: security check activado, `.repomixignore` exhaustivo (excluye binarios, caches, secretos, artefactos de build), `headerText` que orienta al agente, `instructionFilePath`.

### 4.8 CI/CD: diseño correcto aunque no ejecutable
- **13 workflows cubriendo** lint, tipos, 4 matrices de tests, frontend, Docker E2E, sync de tipos TS, escaneo de secretos, benchmark, PVU, docs y publicación.
- **Los 20 archivos YAML del repo parsean sin error** (D7-017).
- **`publish.yml` usa OIDC Trusted Publishing** (`id-token: write` sólo en los jobs de publish), `permissions: contents: read` por defecto, cache GHA, `docker/metadata-action` con tags semver — es la práctica recomendada actual, y está documentada en `.github/CI_CD_BEST_PRACTICES.md`.
- **`validate_ts_types.yml` es un buen ejemplo de gate de contrato**: regenera y exige diff vacío. Funciona (verificado).
- **`pytest.yml` con matriz core/scientific/api/full** y gate de cobertura — la idea de segmentar para dar señal rápida es correcta (la ejecución falla por D7-003).

### 4.9 Diseño de componentes individuales destacables
- **`adapters/mutalambda/`** es un adapter ejemplar: delgado, sin dependencia dura del sistema externo, con manifiesto YAML declarativo (bounds, targets con range/unit/semantics/source) e inversión de dependencia correcta (D3-015).
- **`massive_core/rust_core.py`** implementa el patrón de aceleración opcional correctamente: `find_spec` en lugar de try/except, fallbacks NumPy **numéricamente idénticos** al Rust (verificado expresión por expresión, D9-007), y API pública estable.
- **`CfCRouter` con patrón singleton y diseño "nunca bloquea"** — la *intención* arquitectónica es correcta y está explícitamente documentada en el docstring con 4 casos de fallback. Falla la implementación (D1-001), no el diseño.
- **`sleep/wake` event-driven en `massive_engine.py`** con `wake_fraction` acotado (`max(1e-3, min(wake_fraction, 0.1))`) y un *"Liveness guard (Finding 9)"* que despierta una fracción aleatoria cuando todos los agentes duermen — evidencia de que los hallazgos de auditorías previas se corrigieron y se anotaron en el código.
- **`state_compression.py`** con SVD truncado (`max_bond_dim`, `explained_variance`), validación de entrada (`raise ValueError` en ndim≠2 y max_bond_dim<1) y manejo de energía total degenerada (<1e-12). Bien escrito, aunque sin consumidores (D9-010).
- **DTOs Pydantic con `extra="forbid"`** y docstrings que explican la convención de nombrado (*"snake_case in Python and JSON (zero migration friction)"*) — el diseño es correcto; falta cablearlo (D3-004).

---

## 5. DEUDA TÉCNICA ACUMULADA — PATRONES SISTÉMICOS

Los 148 hallazgos no son 148 problemas independientes. Son **9 patrones recurrentes** que se repiten en capas. Corregir los patrones es más eficiente que corregir los síntomas.

---

### Patrón 1 — Migraciones iniciadas y abandonadas a mitad (el patrón dominante)

**Evidencia convergente.** Cada migración del proyecto dejó el estado antiguo **y** el nuevo conviviendo:

| Migración | Estado nuevo | Estado viejo | ¿Se completó? |
|---|---|---|---|
| root → `massive/core/` | `massive/core/{schemas,extended_models,utility_logic,intervention_optimizer,llm_credentials,empirical_*,state_compression}.py` | 31 módulos root + 5 shims | **No**: `extended_models` sin shim (D1-003); los 31 módulos root siguen siendo los reales |
| `api.py` → `backend/app/` | `backend/app/` con routers, DTOs, security, metrics | `api.py` (497 líneas, 10 rutas, 32 % cobertura) | **No**: `frontend/` sigue consumiendo `api.py`; `make api-legacy` lo mantiene vivo |
| `frontend/` → `massive-ui-ng/frontend/` | v2.0.0 con 399 líneas de App.tsx | v1.0.0 con 32 líneas de App.tsx | **No**: ambos viven; el `.jsx` de 825 líneas es byte-idéntico en los dos |
| Streamlit → FastAPI+React | `backend/app/` + `frontend/` | `streamlit` en requirements, topic de GitHub, `PLAN_INTEGRACION_UI_NG.md`, referencias en system map | **No** en la periferia (D1-006) |
| Numba/JIT → NumPy puro | 0 referencias en `.py` | `REPORT_OPTIMIZATION.md` lo lista como crítico nº1 | **No** en docs (D6-007) |
| `uil_adapter` → UI-NG → MASSIVE | `massive/`, `massive_core/` | `uil_adapter.py`, `MASSIVE_UIL_demo.jsx`, `title="MASSIVE UIL API"`, `/health` → `"MASSIVE UIL API"` | **No** (D8-011) |
| `massive_core/numerics/multilayer_engine_sparse` ← `multilayer_engine` | variante dispersa (789 líneas) | variante densa (1 025 líneas, 95 % cobertura) | **No**: coexisten sin test de paridad (D9-008) |
| `cfc_trainer.py` ← `train_cfc_*.py` | trainer unificado (135 stmts, 0 % cobertura) | 3 clones de ~300 líneas (0 % cobertura cada uno) | **No**: el unificado nunca se usó (D2-012) |

**Diagnóstico de causa raíz.** El proyecto opera por **fases de workflow cerradas con un issue** (90 issues, todos cerrados, con títulos como `feat: FASE 5 closeout`, `Phase 8-9 complete`, `Consolidation merge`). Cada fase entrega el estado nuevo y marca el issue como cerrado, pero **ninguna fase tiene como criterio de aceptación la eliminación del estado viejo**. `docs/OPTIMIZATION_STATUS.md` lo hace explícito: *"1.2 Delete root wrappers — **Rejected (intentional)** Deprecated re-exports kept for BC"*. La compatibilidad hacia atrás se eligió como política, pero sin fecha de caducidad ni mecanismo de retirada — es decir, se convirtió en acumulación permanente.

**Consecuencia estructural.** El coste no es sólo tener dos copias: es que **las invariantes se aplican a una copia y no a la otra**. D5-001 es el caso paradigmático: el clamp de `max_intentos` existe en `api.py:303` y no en `backend/app/routers/engine.py:88`; los límites de `n_agents` existen en `massive-ui-ng/…/live.py` y no en `services/simulation_service.py`. Cada fix de seguridad se aplicó al camino que el desarrollador tenía delante, no a los tres.

**Acción sistémica.** Instituir una **política de deprecación con fecha**: todo shim/legacy debe llevar (a) un `DeprecationWarning` real, (b) una fecha de retirada en `docs/architecture/backward_compatibility_aliases.md`, y (c) un test que verifique que el camino nuevo tiene las mismas invariantes que el viejo (el patrón de `tests/test_api_security.py` ya existe y es el modelo correcto — generalizarlo). Y añadir a la definición de "hecho" de cada fase: *"el estado anterior está eliminado o tiene fecha de retirada"*.

---

### Patrón 2 — Documentación escrita antes que el código, y nunca reconciliada

**Evidencia convergente.** 356 referencias rotas en 114 archivos (D6-004). Los casos no son erratas aisladas:
- `docs/FACTBOOK_INTEGRATION_PLAN.md` referencia `agent_initialization.py`, `energy_engine_pure.py` y `optimizer.py` — **tres módulos que nunca existieron**. El plan se escribió antes de la implementación y la implementación usó otros nombres.
- `MASSIVE_REACTIVE_COHERENCE_PLAN.md` referencia `cfc_lambda_corrector.pt`, `cfc_landscape.pt` y `cfc_temperature.pt` — **los tres pesos que faltan** y causan los 12 tests fallando (D4-001). El plan describe el estado final deseado; el estado real se quedó a medias.
- `MASSIVE_SYSTEM_MAP.md` lista `test_mamba_engine.py` y `micro_ui.py` — **componentes eliminados** (D1-005, D1-006). El mapa no se actualizó al retirar.
- `app.py` referenciado 22 veces — **nunca existió** según el propio CHANGELOG (*"Replaces the stale quickstart (`app.py` never existed)"*), y sin embargo sigue en 22 documentos.
- `REPORT_STRUCTURE.md`, `REPORT_BUGS.md`, `REPORT_OPTIMIZATION.md` con fechas **2025** en un repo creado en 2026 (D6-006).
- `README.md` con 4 afirmaciones falsas en su tabla de calidad (D6-001) y `README_ES.md` con cifras distintas (D6-002) — y un commit dedicado a arreglarlo (`e2900ab0 docs: Fix test count consistency in README`) que no lo consiguió.

**Diagnóstico de causa raíz.** Los documentos se tratan como **entregables de una fase** (se escriben, se commitean, se cierra el issue) en lugar de como **artefactos derivados del estado del sistema**. No existe ningún mecanismo que detecte la divergencia: `mkdocs --strict` valida el nav pero no los enlaces en prosa; no hay link-checker; no hay generación automática de cifras; el árbol de layout del README se escribe a mano.

El síntoma más revelador: **el repo tiene la herramienta correcta y no la usa**. `scripts/gen_ts_types.py` genera los tipos TS desde los DTOs Pydantic y `validate_ts_types.yml` verifica que no haya drift — y funciona (D3-020). Ese mismo patrón (generar + gate de CI) no se aplicó al system map, al árbol del README, ni a la tabla de calidad.

**Acción sistémica.** Clasificar la documentación en tres tiers con tratamiento distinto:
1. **Derivada** (system map, árbol de layout, tabla de calidad, recuento de endpoints, lista de módulos) → **generada por script** con gate de CI que exige diff vacío. Exactamente el patrón de `validate_ts_types.yml`.
2. **Viva** (README, runbooks, docs de arquitectura actuales) → con link-checker en CI (`mkdocs-linkcheck`) y un check de "rutas absolutas personales" (`grep -r '/home/'`).
3. **Histórica** (REPORT_*.md, planes cerrados, development_history) → movidos a `docs/archive/` con banner obligatorio `> ⚠️ HISTÓRICO — describe el commit {sha} del {fecha}` y excluidos de los checks.

---

### Patrón 3 — Señal de calidad estructuralmente incapacitada para fallar

**Evidencia convergente.** Cada mecanismo de verificación tiene una válvula de escape:

| Mecanismo | Válvula de escape | Efecto |
|---|---|---|
| `lint.yml` job mypy | `\|\| true` al final del comando | 36 errores no bloquean (D7-006) |
| `typecheck.yml` | `continue-on-error: true` | el script sale 1 y CI reporta **success** (D7-006) |
| `pyproject.toml` coverage | `fail_under = 30` con cobertura real 59.62 % | se podría borrar un tercio de la suite sin que falle (D4-002) |
| `mypy.ini` | `strict=False`, `check_untyped_defs=False`, `follow_imports=silent` + opt-out por módulo | la mayor parte del código no se analiza (D7-014) |
| `pytest.yml` | job `core` sin torch → falla → `full-suite: skipped` | la suite completa nunca corre (D7-003) |
| GitHub Actions | bloqueo de facturación desde 2026-09-13 | **0 señales** en 8 commits (D7-001) |
| `massive-ui-ng/` | workflow en `.github/workflows/` anidado → nunca se dispara | 40 % de la complejidad alta fuera de CI (D7-007) |
| Rust | ningún job con cargo | 162 líneas nunca compiladas (D3-018, D7-009) |
| `tests/test_cfc_engine.py:16` | `except ImportError: pass` cuando el error real es `AttributeError` | el test que debería detectar D1-001/D1-002 no puede (D4-009) |
| `cache_manager.py` | 3 × `except Exception: pass` | fallos de E/S y de invalidación invisibles (D9-003) |
| `simulator.py:73-78` | `except ImportError` **sin log** | Bayes/Nash/SIR desactivados en silencio (D1-003) |

**Diagnóstico de causa raíz.** Dos causas combinadas. **(a) Adopción gradual sin plan de llegada**: `mypy.ini` documenta "FASE 2 slice" y "FASE 5 B4 slice" — la intención es ir endureciendo, pero no hay umbral objetivo ni fecha, así que el estado gradual se vuelve permanente. **(b) Tolerancia al fallo silencioso como estilo de código**: el principio rector *"CfC nunca bloquea"* es correcto para un componente opcional, pero se generalizó a todo el sistema — 127 `except Exception`, 26 de ellos con `pass`. El resultado es un sistema que **prefiere degradarse en silencio a fallar ruidosamente**, lo cual es la política correcta para un componente satélite y la política desastrosa para la suite de tests, el cache y el type checker.

**Consecuencia.** El repo está en el peor estado posible para detectar regresiones: **todo parece verde y nada lo está**. El único workflow que reporta éxito es el que tiene `continue-on-error: true`. Un desarrollador de buena fe que mire el badge de MyPy verá verde permanente.

**Acción sistémica.** Regla de ouro a adoptar: **un check que no puede fallar no es un check**. Plan de endurecimiento con fechas:
1. Retirar `|| true` y `continue-on-error` **después** de quemar los errores actuales (orden obligatorio: primero el código, después el gate).
2. Ratchet de cobertura: `fail_under` = cobertura actual − 2, subiendo 2 puntos por release hasta 75 %.
3. Ratchet de mypy: añadir al slice un paquete por sprint hasta cubrir `backend/`, `services/`, `massive/` y los 5 engines; entonces activar `check_untyped_defs = True`.
4. Convertir los `except Exception: pass` en `log.warning(exc_info=True)` + métrica — el fallback puede seguir siendo degradado, pero debe ser **observable**.
5. Un único job `verify` bloqueante que ejecute `ruff && black --check && mypy-slice && pytest && gen_ts_types --check && linkcheck`, y que sea requisito de merge.

---

### Patrón 4 — Multiplicación de puntos de entrada sin autoridad designada

**Evidencia convergente.**

| Categoría | Instancias | ¿Cuál es la canónica? |
|---|---|---|
| Backend HTTP | `api.py` · `backend/app/` · `massive-ui-ng/backend/app/` | `backend/app/` según su docstring y el Makefile — pero `frontend/` consume `api.py` |
| Frontend | `frontend/` (v1.0.0) · `massive-ui-ng/frontend/` (v2.0.0) | ninguna declarada |
| Dockerfile | `Dockerfile` · `Dockerfile.optimized` · `massive-ui-ng/infra/Dockerfile.ui-ng` | bucle de contradicción (D7-005) |
| docker-compose | `docker-compose.yml` · `docker-compose.single.yml` · `massive-ui-ng/infra/docker-compose.yml` | "LEGACY" apunta al que usa el Dockerfile "DEPRECATED" |
| `Cargo.toml` | root (pyo3 0.28) · `rust_core/` (pyo3 0.22) | root según `Cargo.lock`; el otro es irrespusable |
| `gen_ts_types.py` | `scripts/` · `massive-ui-ng/infra/scripts/` | el segundo no ejecuta (D3-003) |
| env example | `.env.example` (~40 vars) · `.env.local.example` (8 vars) · `massive-ui-ng/infra/env.example` | ambos montados a la vez por compose |
| Paquetes `utils/` | `massive/core/utils/` · `massive_core/utils/` · `micro_massive/utils/` | ninguna |
| Métricas | `metrics/unified_metrics.py` · `micro_massive/utils/metrics.py` · `backend/app/metrics.py` · `massive-ui-ng/backend/app/metrics.py` | `unified_metrics` para engines; los otros 3 son HTTP |
| Instrucciones para agentes | `AGENTS.md` · `CLAUDE.md` · `.github/Agent_Copilot2` · `.github/agents/my-agent.agent.md` · `massive-ui-ng/AGENTS.md` · `repomix-instruction.md` | `repomix.config.json` dice "Read CLAUDE.md first"; los otros no se referencian |
| Docs de rendimiento | `docs/performance/baseline.md` · `docs/performance_report.md` · `docs/OPTIMIZATION_STATUS.md` · `REPORT_OPTIMIZATION.md` · `RESTART_CHECKLIST.md` | contradictorios entre sí (D6-007, D9-006) |
| Despliegue | Azure Web App · HF Spaces · GHCR+PyPI · Docker+nginx+supervisord | 4 destinos, 0 documentados en README |
| Tests | `tests/` (59) · `massive-ui-ng/tests/` (2) | sólo el primero en `testpaths` |

**Diagnóstico de causa raíz.** Ausencia de un **documento único de autoridad** que declare, por categoría, cuál es la instancia canónica y cuál está deprecada. Existe `docs/architecture/domain_ownership.md` — que es exactamente el documento correcto — pero está huérfano del nav de MkDocs (D6-009) y, por tanto, no forma parte del flujo de decisión de nadie.

El mecanismo generador es el mismo que en el Patrón 1: cada fase crea una instancia nueva (a menudo con el sufijo `-ng`, `_v2`, `.optimized`, `_sparse`) en lugar de modificar la existente, porque modificar la existente requiere validar la regresión — y la validación está incapacitada (Patrón 3). Crear algo nuevo es más barato que arreglar lo viejo cuando no hay CI.

**Consecuencia.** Coste de cognición multiplicado. Un contribuyente nuevo debe determinar, para cada categoría, cuál de las N instancias es la relevante — y no hay forma de saberlo sin leer el código. Y los fixes se aplican a una instancia mientras las otras siguen vulnerables (D5-001 es el caso con impacto de seguridad).

**Acción sistémica.** (1) Crear `docs/architecture/CANONICAL_SOURCES.md` con una tabla por categoría: instancia canónica · estado de las demás · fecha de retirada. (2) Añadirlo al nav de MkDocs **y** enlazarlo desde `CONTRIBUTING.md` y `AGENTS.md`. (3) Regla de contribución: *"no se crea una segunda instancia de nada sin declarar deprecada la primera con fecha"*. (4) Ejecutar las consolidaciones de la tabla de arriba en el orden de la Banda 2 del workflow.

---

### Patrón 5 — Contratos declarados pero no aplicados en runtime

**Evidencia convergente.**

| Contrato declarado | Dónde se declara | ¿Se aplica? |
|---|---|---|
| `extra="forbid"` en todos los DTOs | `backend/app/models/dto_*.py` | **No**: 5 de 6 routers aceptan `dict[str, Any]` (D3-004) |
| `Field(..., ge=-1.0, le=1.0)` en `opinion` | `dto_simulation.py:42` | **No**: `/v1/simulate` no usa el DTO |
| *"CfC nunca bloquea. Sin PyTorch → fallback transparente"* | `cfc_router.py:5-12` (docstring) | **No**: `AttributeError` en la primera línea del fallback (D1-001) |
| *"CFC engine usará implementación NumPy fallback"* | `cfc_engine.py:31` (warning runtime) | **No**: no existe implementación NumPy (D1-002) |
| *"Thread-safe para uso concurrente del backend FastAPI"* | `cache_manager.py:18` | **No**: sin locks, 3 × `except: pass` (D9-003) |
| *"`n_agents` cap (prevents 8 TB OOM)"* · *"`max_intentos` clamp (prevents LLM DoS)"* | `README.md:250` | **No** en el backend canónico (D5-001) |
| *"ruff + black + mypy green in CI"* · *"679 tests"* · *"Coverage 68 %"* · *"semgrep"* | `README.md:244-248` | **No**: los 4 falsos (D6-001) |
| *"100M agents run in ~8 GB RAM"* | `README.md:29` | No reproducible desde el repo (D9-005) |
| *"near-constant memory with uint8-quantized sparse updates"* | `README.md:29` | 0.87 GB hasta 1M, salto a 8.3 GB en 100M (D9-009) |
| `license = { text = "Apache-2.0" }` | `pyproject.toml:10` | GitHub detecta "Other" (D8-003) |
| `[project.scripts] massive-cli` | `pyproject.toml:56` | 0 % cobertura, 0 tests, y `pip install -e .` falla (D3-013, D5-002) |
| *"This project follows Keep a Changelog"* | `CHANGELOG.md:3` | 2 secciones `[Unreleased]`, 0 versiones SemVer (D6-012) |
| `*.pt` / `reports/**/*.json` ignorados | `.gitignore:63-72` | 9 `.pt` y 30+ `.json` trackeados (D5-020) |
| `repomix-output*.xml` ignorado | `.gitignore:35` | dice `repomack` (D5-019) |
| *"Replaces the legacy api.py monolith"* | `backend/app/main.py:3` | `api.py` vivo, con `make api-legacy` y consumido por `frontend/` |
| *"All `/v1/*` endpoints require `X-API-Key`"* | `backend/app/main.py:21` | cierto ✓ — pero `/metrics` no (D5-009) |

**Diagnóstico de causa raíz.** El proyecto tiene una **cultura fuerte de declaración de contratos** (docstrings precisos, manifiestos YAML, especificaciones de 29 KB, threat models, protocolos pre-registrados) y una **cultura débil de verificación automática de esos contratos**. Los contratos se escriben para ser leídos por humanos, no para ser ejecutados por máquinas. No hay ningún mecanismo que convierta una afirmación de un docstring en un test.

Es notable que cuando el mecanismo **sí** existe, funciona: `validate_ts_types.yml` hace cumplir el contrato Pydantic↔TypeScript y está verde. Es el único contrato del repo con enforcement automático, y es el único que no ha derivado.

**Consecuencia.** Divergencia creciente entre lo que el sistema promete y lo que hace. El caso con impacto real es D5-001 (protecciones anti-DoS declaradas y ausentes); el caso con impacto de credibilidad es D6-001 (tabla de calidad del README).

**Acción sistémica.** (1) **Contract-first para la API**: cablear los DTOs como cuerpos de request (D3-004) — esto convierte 8 contratos declarados en contratos aplicados con un solo cambio. (2) **Docstring → test**: para cada afirmación de comportamiento en un docstring de módulo, un test con el nombre del contrato (`test_contract_cfc_never_blocks`, `test_contract_cache_is_thread_safe`). (3) **README → CI**: generar las cifras de la tabla de calidad desde un artifact de CI (D6-001). (4) Añadir a la revisión de PR la pregunta: *"¿qué mecanismo automático impide que esta afirmación deje de ser cierta?"*

---

### Patrón 6 — El camino feliz funciona; los caminos de degradación no

**Evidencia convergente.** Todo lo que se verificó en vivo con dependencias completas funcionó:

✓ 146/146 módulos importan (con torch) · ✓ 669/681 tests pasan · ✓ el servidor arranca · ✓ los 22 endpoints responden · ✓ auth fail-closed (401) · ✓ `/ready` reporta `degraded` correctamente · ✓ `mkdocs --strict` limpio · ✓ tipos TS sincronizados · ✓ PVU runner exit 0 · ✓ el ejemplo del README produce resultados numéricamente plausibles

Y todo lo que ejercita un **camino de degradación** falló:

✗ sin torch → 25 módulos rotos (D1-001, D1-002) · ✗ sin `models/*.pt` → 12 tests rojos (D4-001) · ✗ sin `psutil` → `benchmark_scalability` no importa · ✗ sin `httpx` → 3 archivos de test no recolectan (D4-006) · ✗ sin Rust → `pip install -e .` imposible (D5-002) · ✗ sin `MASSIVE_ENV` → auth abierta con clave publicada (D5-013) · ✗ sin `MASSIVE_API_KEY` → fallback a clave conocida · ✗ con `MASSIVE_ALLOWED_HOSTS=*` (el valor del `.env.example`) → host allowlist anulado · ✗ en el contenedor Docker → sin pesos CfC (`.dockerignore` excluye `models/`, D5-022) · ✗ cache bajo concurrencia → pérdida silenciosa (D9-003)

**Diagnóstico de causa raíz.** Los tests y la documentación se construyen sobre el **entorno de desarrollo del autor**, que tiene torch, los pesos entrenados en `models/`, psutil, httpx y Rust disponibles localmente. Nada en el proceso verifica el entorno de un **clone limpio**. No hay ningún job de CI que instale sólo las dependencias mínimas declaradas y verifique que el sistema arranca — que es precisamente lo que el job `core` de `pytest.yml` *intentaba* ser, y falla por D7-003.

Este patrón es la razón por la que el bug de D1-001 sobrevivió: en la máquina del autor, con torch, `_load()` completa y `_lambda_corrector` se asigna. El bug es invisible en el entorno donde se desarrolla y fatal en el entorno donde se consume.

**Consecuencia.** La experiencia de un usuario nuevo —que es la que determina la adopción— es sistemáticamente peor que la del autor. Y el camino de producción (Docker) es el más degradado de todos: sin pesos CfC, sin `datasets/`, con un `Dockerfile` que no puede hacer `pip install -e`.

**Acción sistémica.** (1) **Job `clean-clone`** en CI: checkout → `python -m venv` → `pip install -r requirements.txt` (nada más) → `python -c "import simulator, backend.app.main, massive.cli.main"` → `pytest tests/ -q` → `docker compose build`. Este único job habría detectado D1-001, D4-001, D4-006, D5-002, D5-005 y D7-004. (2) **Matriz de dependencias mínimas vs. completas** para los módulos con fallback (torch, cupy, hdbscan, ripser/persim, rust). (3) **Verificar la imagen Docker construida**, no sólo que construya: `docker run … python -c "from cfc_router import CfCRouter; print(CfCRouter.get().status)"` y afirmar que los modelos esperados están presentes.

---

### Patrón 7 — Artefactos de runtime y estado personal commiteados

**Evidencia convergente.**
```
Binarios de modelo      9 × .pt (396 KB) + 1 × .npz      trackeados, con regla .gitignore que los prohíbe
Estado de aplicación    data/ui_ng/runs.db (40 KB SQLite)  trackeado, sin regla de ignore
Resultados de ejecución 30+ reports/*.json + 12 report.md  trackeados, con regla .gitignore que los prohíbe
Resultados de experiments  4 × .json + 1 × .csv            trackeados
Logs de side-effect     massive_run.log · landscapes_cache.db   creados al IMPORTAR (D1-008), gitignored ✓
Rutas personales        /home/adlg/MASSIVE y /home/adlg/Escritorio/Proyectos/MASSIVE   16 ocurrencias en 9 docs
Fechas personales       2025-07-09 · 2025-07-24 · 2025-09-14   anteriores a la creación del repo
Secretos históricos     .codebuff/ con token Zapier        commiteado, luego purgado (bien gestionado, D5-018)
Caches de build         208 × .pyc en disco                gitignored ✓
```

**Diagnóstico de causa raíz.** No hay separación entre **el repositorio** (código + documentación + datos de referencia) y **el espacio de trabajo** (resultados, logs, bases de datos, caches, modelos entrenados). El `.gitignore` intenta establecerla (tiene 8 secciones bien organizadas) pero llega tarde: los archivos ya estaban trackeados, y las reglas de gitignore no des-trackean (D5-020). Y tiene un typo en la regla más relevante para el flujo de trabajo con IA (D5-019).

El sub-patrón de las **rutas y fechas personales** tiene una causa distinta y más interesante: los documentos los genera un agente de IA trabajando en la máquina del autor, y el output del agente (que incluye su CWD y la fecha del sistema) se commitea sin edición. `REPORT_STRUCTURE.md:4` con `Fecha: 2025-09-14 | Path: /home/adlg/Escritorio/Proyectos/MASSIVE` tiene la forma exacta de un encabezado de reporte generado por agente.

**Consecuencia.** Repo más pesado de lo necesario, diffs ruidosos en binarios, merges conflictivos en SQLite, y documentación que delata que fue generada y no curada. El riesgo mayor es el de D5-021: si la app se usa con datos reales, `data/ui_ng/runs.db` puede capturar contenido de usuarios y acabar en un commit.

**Acción sistémica.** (1) Clasificación explícita en `CONTRIBUTING.md`: qué pertenece al repo (código, docs, datos de referencia inmutables, pesos de modelo vía LFS) y qué no (resultados, logs, DBs, caches). (2) `git rm --cached` de `data/ui_ng/runs.db` + regla de ignore. (3) Decidir sobre los `.pt` y los `reports/` (D5-020) — o son evidencia científica versionada (y entonces se quitan las reglas de ignore contradictorias) o son artefactos (y entonces van a CI artifacts / LFS). (4) Check de CI que rechace `/home/`, `/Users/`, `C:\` en archivos trackeados. (5) Los reportes generados por agentes deben pasar por una plantilla que no incluya CWD ni fecha del sistema, o por una pasada de curaduría antes del commit.

---

### Patrón 8 — La escala se afirma, no se mide

**Evidencia convergente.** El proyecto se posiciona por escala (*"from 10 agents to 100 million"* está en el tagline de la primera pantalla del README) pero la evidencia de escala es la parte menos sólida del repo:
- `benchmark_scalability.py` (483 stmts, 908 líneas): **0 % de cobertura**, no importa sin `psutil` (no declarado), **0 workflows lo ejecutan**.
- Las cifras del README (0.39 s · 0.87 GB · 44 s · 8.3 GB · 16.8 GB): **ningún artefacto commiteado las respalda**, sin fecha, sin commit SHA, sin hardware, sin comando de reproducción.
- `profiling_results/`: **no existe**.
- `scripts/profile_hotspot.py`: bien construido, **nunca ejecutado automáticamente**.
- `docs/performance_report.md`: **huérfano del nav**.
- `massive_core/rust_core.py`: aceleración que **nunca se compila** en ningún entorno automatizado; el README lo admite honestamente (*"a conceptual PoC, not yet a significant speedup"*).
- `massive_core/network_inference/reconstruct.py`: identificado como O(N²) "inusable para N > 100" en 2025-07-24; hoy al **20.7 % de cobertura** y sin entrada de estado en `OPTIMIZATION_STATUS.md`.
- `state_compression.py` (SVD truncado para comprimir el historial): implementado, documentado, con shim deprecado en root, y **0 consumidores**.

**Contraste instructivo.** La **validación científica** sí tiene infraestructura de rigor: protocolo pre-registrado bilingüe, 12 casos reales con datos históricos, 10 baselines comparativos, runner offline determinista con seed, workflow dedicado, artifacts subidos en CI, y un disclaimer auto-generado cuando se usan casos sintéticos. Es exactamente el nivel de rigor que la afirmación de escala no tiene.

**Diagnóstico de causa raíz.** La escalabilidad es la **propuesta de valor de marketing** y la validación es la **propuesta de valor científica**. El proyecto invirtió en instrumentar la segunda y no la primera. Probablemente porque la validación científica se puede ejecutar en CI (2 casos de muestra, ~8 segundos) mientras que un benchmark a 100M agentes requiere una máquina grande que ningún runner de GitHub Actions proporciona.

**Consecuencia.** La afirmación más visible del proyecto es la menos defendible. Y hay evidencia de que el mecanismo de escala **sí existe y funciona** —`sleep/wake` event-driven, LOD super-agents, cuantización uint8, CSR sparse, `state_compression`— pero nada lo demuestra de forma reproducible. Además se detectó una posible regresión funcional en el camino: `gini` calculado y descartado en `energy_engine.py` (D9-004), que según `MASSIVE_REACTIVE_COHERENCE_PLAN.md` debería alimentar el acoplamiento reactivo.

**Acción sistémica.** (1) Separar la evidencia en dos tiers: **tier CI** (1K y 10K agentes, ejecutable en runner estándar, con baseline commiteado y tolerancia de ±20 %) y **tier self-hosted/manual** (1M y 100M, ejecutado bajo demanda con `workflow_dispatch`, resultado commiteado con metadata completa). (2) Commitear `reports/scalability/{metrics.json, report.md}` con `{fecha, commit_sha, cpu_model, ram_gb, numpy_version, python_version, comando}` y citar ese archivo desde la tabla del README. (3) Añadir `psutil` a requirements y `make benchmark-scale` al Makefile. (4) Reformular las afirmaciones del README para que sean exactamente lo que la evidencia soporta (D9-009). (5) Resolver `gini` (D9-004) antes de volver a afirmar el mecanismo de coherencia reactiva.

---

### Patrón 9 — Complejidad añadida más rápido que la capacidad de verificarla

**Evidencia convergente — la relación entre tamaño y verificación:**
```
49 174 LOC Python  ·  245 archivos  ·  1 783 funciones  ·  113 .md  ·  554 archivos trackeados
13 workflows       ·  681 tests      ·  59.62 % cobertura ·  198 errores mypy ·  16 archivos al 0 %

Componentes construidos y NO verificados en ningún entorno automatizado:
  · rust_core/src/lib.rs            162 líneas   → 0 compilaciones en CI
  · massive-ui-ng/backend/app/       21 módulos  → 0 lint, 0 typecheck, 0 tests, 0 build
  · massive-ui-ng/frontend/          15 archivos → 0 lint (no tiene script), 0 tsc, 0 build
  · massive/cli/                     105 stmts   → 0 tests
  · massive/core/extended_models.py  205 stmts   → 0 % cobertura + import roto
  · social_connectors.py             325 líneas  → 0 % cobertura + 0 consumidores
  · train_cfc_*.py + cfc_trainer.py  620 stmts   → 0 % cobertura
  · benchmark_scalability.py         483 stmts   → 0 % cobertura + no importa
  · massive_core/physics/            267 stmts   → 33-57 % cobertura + vulture marca 7 métodos muertos
  · monitoring/                      2 archivos  → 0 consumidores
  · state_compression.py             2 funciones → 0 consumidores
  · 35 de 60 docs/*.md                           → fuera del nav del sitio
```
Aproximadamente **2 400 sentencias Python + 162 líneas Rust + 36 archivos frontend + 35 documentos** existen sin ningún mecanismo automático que verifique que funcionan, son alcanzables o son usados.

**Diagnóstico de causa raíz.** El ritmo de generación de código (asistido por agentes, a juzgar por los 90 issues de tipo "Phase N complete" y el commit HEAD *"Humanize code — remove AI-generated tells"*) supera al ritmo de construcción de verificación. Cada fase añade capacidad; ninguna fase tiene como entregable la instrumentación de la capacidad anterior. Los 8 commits del 2026-09-15 son elocuentes:
```
4b1284af 00:28  docs: Remove obsolete references to Numba, UI-NG naming
2cc025e1 00:31  docs: Remove obsolete Numba/JIT references throughout codebase
fefc1033 00:31  docs: Fix remaining JIT reference in OPTIMIZATION_STATUS.md
b3a5e312 02:46  fix: Resolve lint errors in metrics.py and main.py
f6068106 02:51  fix: Resolve lint errors from Numba removal cleanup
d20e5458 03:04  ci: Remove numba from CI workflow (no longer a dependency)
e2900ab0 03:25  docs: Fix test count consistency in README
473b04a6 03:51  refactor: Humanize code — remove AI-generated tells      ← HEAD
```
Tres de ellos son correcciones de documentación, dos son correcciones de lint **que no lograron verdear el lint** (ruff sigue en 28, black en 30 archivos), uno arregla la consistencia del README **que sigue siendo inconsistente**, y el último es una refactorización cosmética sobre 245 archivos. **Todos se hicieron sin CI** (bloqueado desde el 13/09). Es el Patrón 3 manifestándose en tiempo real: sin señal, el trabajo de corrección no converge.

**Consecuencia.** Deuda que crece más rápido que la capacidad de pagarla. El síntoma observable es que los commits de "fix lint" no arreglan el lint, porque no hay forma de verificarlo antes de commitear.

**Acción sistémica.** (1) **Regla de WIP**: no añadir superficie nueva hasta que la existente tenga verificación. Concretamente, el criterio de "hecho" debe incluir: test que la ejercita + cobertura ≥ umbral del paquete + entrada en el nav si es documentación + entrada en `CANONICAL_SOURCES.md` si es un punto de entrada. (2) **Gate local obligatorio** mientras Actions esté bloqueado: un `make verify` que ejecute ruff+black+mypy-slice+pytest+gen_ts_types+linkcheck, documentado en `CONTRIBUTING.md` como requisito pre-push, e idealmente instalado como pre-commit hook. (3) **Congelar la superficie**: `massive-ui-ng/` no debe crecer hasta que se decida si es canónico o se archiva (D3-002). (4) **Presupuesto de deuda explícito**: los 148 hallazgos de este reporte, convertidos en issues con label `debt`, y un compromiso de cerrar N por sprint antes de aceptar features nuevas.

---

## 6. ANEXO — RESUMEN DE COMANDOS EJECUTADOS Y RESULTADOS

| Comando | Resultado |
|---|---|
| `git rev-parse HEAD` | `473b04a6b4002b258da13f9c553949a6c59d5d5f` |
| `git ls-files \| wc -l` | 554 (245 .py · 113 .md · 74 .json · 19 .yml · 15 .csv · 13 .ts · 12 .tsx · 9 .pt) |
| `find . -name "*.py" \| xargs cat \| wc -l` | 49 174 LOC · 1 783 def/async def |
| `ls -A \| wc -l` (root) | 106 entradas (78 archivos + 28 dirs) · 31 .py · 21 .md |
| `python -c "import simulator"` (sin torch) | ❌ `AttributeError: '_lambda_corrector'` |
| `python -c "import simulator"` (con torch) | ✓ |
| `python -c "from mamba_engine import MambaBaseline"` | ❌ `ModuleNotFoundError` |
| `python -c "from massive_core import run_scientific_simulation"` | ✓ |
| `python -c "from massive.core.factbook import FactbookContext"` | ✓ |
| `python -c "from energy_engine import SocialEnergyEngine"` | ✓ |
| Barrido de importabilidad (146 módulos) | sin torch 121 OK / 25 FAIL · con torch 146 OK / 0 FAIL |
| `pytest tests/ --collect-only` (sin torch) | ❌ Interrupted: 21 errors during collection |
| `pytest tests/ --collect-only` (con torch) | ✓ 681 tests, 0 errores |
| `pytest tests/ -q` | **669 passed · 12 failed** · ~28 s |
| `pytest --cov=. --cov-report=json` | **59.62 %** · 144 archivos · 16 al 0 % · 16 entre 0 y 50 % |
| `pytest tests/test_cfc_engine.py tests/test_cfc_router.py` (torch bloqueado) | ❌ 4 failed |
| `python -m benchmarks.runner --offline --seed 42` | ✓ exit 0 · 2 casos · ⚠ ConvergenceWarning de statsmodels |
| `ruff check .` | ❌ 28 issues · exit 1 |
| `ruff check . --isolated --select ALL` (subset) | 732 errores · 47 auto-fixeables |
| `black --check .` | ❌ 30 archivos · exit 1 |
| `mypy .` | ❌ exit 2 · `Duplicate module named "backend"` (0 archivos analizados) |
| `mypy . --exclude massive-ui-ng/` | ❌ 198 errores en 46 archivos |
| `mypy --config-file mypy.ini massive/ backend/ services/ massive_core/` | ❌ 36 errores en 16 archivos |
| `python scripts/typecheck_slice.py` | ❌ 1 error · exit 1 (CI lo reporta `success`) |
| `vulture . --min-confidence 80` / `60` | 2 / 311 hallazgos |
| `radon cc . -s -n B --average` | B (9.53) · 312 bloques |
| `radon cc . -s -n D` | 12 bloques ≥ D · peores F(57), F(50) |
| `pylint . --disable=all --enable=R0801` | 9 bloques duplicados |
| AST: bare `except:` / `except Exception` / silenciados | 0 / 127 / 26 |
| AST: docstrings de módulo faltantes | 24 de 245 |
| AST: tests sin aserción | 140 de 666 |
| AST: errores de sintaxis / imports relativos rotos | 0 / 0 |
| `grep -rn "print("` / `logging.` / `log.<nivel>(` | 156 / 80 / 267 |
| `grep -rn "logging.basicConfig"` | 13 (2 en tests, 2 a nivel de módulo de librería) |
| `grep -rnE "TODO\|FIXME\|HACK\|XXX"` + `todo_triage.py` | 0 marcadores reales |
| `pip-audit -r requirements.txt --no-deps` | ✓ No known vulnerabilities found |
| `pip install -e .` | ❌ `maturin` → `puccinialin` → metadata-generation-failed |
| `python scripts/gen_ts_types.py --dry-run` | ⚠ ignora el flag y ESCRIBE el archivo |
| diff del archivo regenerado vs commiteado | ✓ 0 diferencias (tipos en sincronía) |
| `python massive-ui-ng/infra/scripts/gen_ts_types.py` | ❌ `ModuleNotFoundError: No module named 'backend'` |
| `mkdocs build --strict` | ✓ 0 errores · 0 warnings · 0 entradas de nav rotas |
| Análisis de nav de MkDocs | 60 docs · 25 en nav · **35 huérfanos** |
| Análisis de refs en 114 .md | **186 rutas inexistentes · 356 referencias rotas** |
| `uvicorn backend.app.main:app` + 7 sondas HTTP | ✓ arranque OK · /health /ready /version /v1/simulate 200 · sin key 401 · /metrics **200 sin auth** |
| `gh api …/actions/runs` | **13/13 workflows en failure** en HEAD · causa: billing lock · último verde real `da4c7e7b` 2026-09-12 · 1 735 runs totales |
| `gh api …/releases` · `…/tags` | vacío · vacío |
| `gh api …/issues?state=all` | 90 issues, todos cerrados, 0 abiertos |
| `gh repo view --json …` | license "Other" · topics incluyen `streamlit` y `scaleable` · 0 stars · 0 forks |
| Validación YAML (20 archivos) | ✓ 20/20 parsean |
| `docker` / `docker-compose` / `cargo` | no disponibles en el sandbox → D7-004, D7-005, D3-017 son **[HIPÓTESIS]** por inspección de sintaxis |

---

*Fin del reporte. 148 hallazgos: 17 🔴 · 45 🟠 · 69 🟡 · 17 🟢.*
*Documento complementario: `AUDIT_REMEDIATION_WORKFLOW.md` — plan de ejecución por olas para un equipo de agentes.*
