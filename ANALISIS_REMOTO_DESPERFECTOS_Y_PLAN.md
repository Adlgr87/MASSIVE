# Auditoría del REPOSITORIO REMOTO — MASSIVE

**Fecha:** 2026-10-31
**Fuente de verdad analizada:** `https://github.com/Adlgr87/MASSIVE.git` → `origin/main` @ `b59c2ba` ("Prod readiness (#159)")
**Método:** worktree aislado en `/tmp/MASSIVE_REMOTE` (no se tocó la carpeta local) + ejecución real de los motores.
**Alcance de esta etapa:** SOLO análisis de desperfectos, áreas rotas, obsoletas y de optimización. Sin cambios de código.

---

## 0. Sincronización local ↔ remoto: tu sospecha era correcta

| Elemento | Valor |
|---|---|
| HEAD local (`prod-readiness`) | `cfebab2` — 2026-10-15 17:54 |
| `origin/prod-readiness` | `cfebab2` (idéntico al local, árbol limpio) |
| `origin/main` (rama por defecto) | `b59c2ba` — 2026-10-15 17:38 |
| Commits en `prod-readiness` NO presentes en `main` | **39** |
| Archivos que difieren entre local y `main` | **13** |
| Ramas remotas totales / fusionadas-obsoletas | **16 / 5** |

**Diagnóstico:** el trabajo NO está en `main` como commits. La PR #159 se fusionó como *squash* (`b59c2ba`), que contiene 37 de los 39 commits, pero **los 2 commits más recientes de `prod-readiness` (`a8ea32c`, `cfebab2`) quedaron sin integrar**.

**Consecuencia concreta y verificable:** `origin/main` está ROTO y `prod-readiness` ya lo arregló.

```
$ git show origin/main:pyproject.toml | sed -n '82p'
  "social_architect", "social_connectors",     ← módulo BORRADO, main lo sigue declarando

$ git show HEAD:pyproject.toml | sed -n '82p'
  "social_architect",                          ← prod-readiness corregido
```

`social_connectors.py` no existe (se eliminó en `bfcdd79`) pero `main` lo declara en `py-modules`. La rueda se construye igual (setuptools ignora el faltante con *warning*), pero es una declaración inválida en la rama pública.

**Veredicto:** `main` NO es la fuente de verdad del estado más avanzado. Es una foto desactualizada con un defecto de empaquetado. Cualquier análisis o release hecho sobre `main` arrastra ese defecto.

---

## 1. El corazón del asunto: conexiones entre variables

El vector de estado del motor principal (`multilayer_engine.py`, K=5) es:

| idx | variable | rango | significado |
|---|---|---|---|
| 0 | `opinion` | [-1, 1] | posición ideológica |
| 1 | `cooperation` | [0, 1] | disposición a cooperar |
| 2 | `hierarchy` | [0, 1] | reconocimiento de autoridad |
| 3 | `income` | [0, 1] | ingreso normalizado |
| 4 | `info_access` | [0, 1] | acceso a información |

La dinámica es `dx_i/dt = -∇U(x_i) + Σ_ℓ w_ℓ (A_ℓ · x)_i + θ(a_i)·η_i`.

### 1.1 Matriz de acoplamiento REAL (jacobiano de la deriva)

Calculada simbólicamente y verificada por diferencias finitas sobre `multi_potential_gradient`. Fila = variable que cambia, columna = variable que la mueve.

|  | opinion | cooperation | hierarchy | income | info_access |
|---|---:|---:|---:|---:|---:|
| **opinion** | −1.04 | 0 | 0 | 0 | 0 |
| **cooperation** | **+0.80** | −2.00 | 0 | 0 | 0 |
| **hierarchy** | 0 | 0 | ±bistable | 0 | 0 |
| **income** | 0 | 0 | ~0 | −0.75 | 0 |
| **info_access** | 0 | **+0.06** | 0 | 0 | −0.30 |

**Resultado duro:**

- **Densidad de acoplamiento cruzado: 2 de 20 = 10 %. 18 de 20 pares son estructuralmente cero.**
- **Acoplamientos negativos: CERO.** No existe ni una sola relación "si una sube, la otra baja" en todo el potencial.
- Los dos únicos vínculos permanentes son **positivos** (misma dirección):
  - `opinion → cooperation` con ganancia **+0.80** (teórica +0.4 sobre el objetivo, amplificada por el pozo doble)
  - `cooperation → info_access` con ganancia **+0.06** (prácticamente ruido)
- `hierarchy → income` existe como `(0.25 − 0.5·income)` pero **se anula exactamente en el punto fijo de `income`** (`income* = 0.5`), así que no sobrevive al régimen estacionario.

### 1.2 Verificación empírica: perturbando cada variable +0.25 y midiendo la respuesta

Ejecución real, N=600, 400 pasos, mismo seed/red/theta. Δ respecto al baseline.

| shock +0.25 en ↓ | Δmean_op | Δpolariz | Δcoop | Δhier | Δhier_std | Δinfo |
|---|---:|---:|---:|---:|---:|---:|
| **opinion** | **+0.4295** | **−0.1404** | **+0.1713** | 0.0000 | 0.0000 | +0.0296 |
| cooperation | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | +0.0007 |
| hierarchy | 0.0000 | 0.0000 | 0.0000 | **+0.3606** | −0.1676 | 0.0000 |
| income | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| info_access | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | +0.0201 |

**Interpretación directa de tu pregunta:**

- Solo `opinion` propaga. Todo lo demás está muerto hacia los outputs del producto.
- `cooperation` **no afecta a nada**, ni siquiera a `info_access` de forma medible (Δ=+0.0007).
- `income` **no afecta a absolutamente nada** (Δ=0.0000 en las 9 columnas).
- `hierarchy` solo se mueve a sí misma (`+0.36`) y reduce su propia dispersión — un dial de un solo sentido.
- **4 de 5 variables del estado declarado son decorativas.**

### 1.3 Por qué: tres defectos de diseño, no de tuning

**D1 — `income` es una variable muerta por construcción.**
```
grad[:, COL_INCOME] = 0.5 * (inc - 0.5) * (1.0 + hier)
```
Atractor único en 0.5. `hierarchy` solo modula la *velocidad*, nunca el nivel. Medido: la desviación colapsa de 0.177 → 0.099 y la media queda clavada en 0.5043. `income` no tiene aristas de entrada desde `opinion`, `cooperation` ni `info_access`. Es una constante ruidosa que ocupa el 20 % del vector de estado.

**D2 — `hierarchy` es biestable pero está desconectada.**
Verificado: 49.2 % de agentes en `h < 0.15` (rebelde) y 46.7 % en `h > 0.85` (conformista), solo 0.2 % en la zona media. El doble pozo funciona perfectamente. Pero **`hierarchy` no empuja ninguna otra variable en régimen estacionario**. Se paga el coste de integrar un sistema biestable cuyos estados no cambian ningún resultado.

**D3 — La única fuerza de red actúa solo sobre `opinion`.**
```python
social_force[:, COL_OPINION] += coupling * w * contribution   # ← única columna tocada
```
Las "capas" social/digital/económica **no influyen en cooperación, jerarquía, ingreso ni acceso a información**. La palabra "multicapa" describe la topología del término de opinión, no un acoplamiento multivariable. El sistema completo es una **cadena feed-forward** (`opinion → cooperation → info_access`), no un sistema acoplado: **ningún bucle de retroalimentación existe**.

### 1.4 La consecuencia grave: el resultado es casi una constante

| palanca | polarization resultante |
|---|---:|
| `coupling=0.0` | 0.6983 |
| `coupling=0.3` (default) | 0.6970 |
| `coupling=1.0` | 0.6613 |
| **`coupling=3.0`** | **0.0047** ← colapso a consenso total (+0.9988) |
| `layer_weights` planos | 0.6963 |
| `layer_weights` social (0.9) | 0.7004 |
| `layer_weights` digital (0.9) | 0.6987 |
| `dt=0.01` | 0.6971 |
| `dt=0.2` | 0.6976 |
| seed 42 vs seed 7 | 0.6970 vs 0.6945 |
| N=100 / 300 / 600 / 1200 | 0.7009 / 0.7021 / 0.6970 / 0.6985 |

**La polarización es ≈ 0.697 ± 0.005 para casi cualquier configuración.** Los pesos de capa — que son el argumento de venta "multicapa" y el único parámetro que la API expone junto a `n_agents`, `steps` y `seed` — **no mueven el resultado en más de 0.004**. La semilla apenas importa. El tamaño de población no importa.

**Único dial real:** `coupling`. Y es un dial de fase brusco: 1.0 → 0.66, 3.0 → 0.005. Entre 1 y 3 hay una transición que nadie declaró ni documentó.

Esto es el hallazgo más importante: **el modelo no tiene superficie de respuesta**. Optimizarlo "para que dé los mejores resultados" es imposible mientras 4 de 5 variables sean inertes y el único parámetro libre sea un interruptor de fase.

---

## 2. ÁREAS ROTAS (defectos verificados)

| # | Severidad | Defecto | Evidencia |
|---|---|---|---|
| R1 | **CRÍTICA** | `/v1` devuelve la MISMA serie 3 veces bajo las claves `social`, `digital`, `economic` | `run_multilayer_simulation`: `social == digital == economic → True` (comparación de listas completa). El comentario en el código lo admite: *"the same trajectory is returned for each layer key until per-layer tracking is implemented"* |
| R2 | **CRÍTICA** | Los tests **reescriben artefactos "sellados" versionados** | Correr `pytest` modifica 6 archivos rastreados: 4 `prereg_*.yaml` (`registered_at`), `datasets/ground_truth/splits.json` (`sealed_at`), `massive/core/_provenance_registry.json`. Un sello criptográfico que cambia en cada ejecución no es un sello |
| R3 | ALTA | `origin/main` declara el módulo inexistente `social_connectors` | `pyproject.toml:82` |
| R4 | MEDIA | `compare_arms.py:67` importa de `social_connectors` (borrado) como fallback | Sólo se activa si falla `massive.core.sentiment`; deuda silenciosa |
| R5 | MEDIA | 10 knobs de configuración muertos en `simular()` | `n_agents, n_ticks, diffusion_sigma, levy_lambda, alpha_stable, jump_magnitude_scale, topology_intensity, butterfly_threshold, enable_levy_jumps, enable_dynamic_topology` — todos en `DEFAULT_CONFIG`, 0 lecturas en `simular()`, solo en `IntegratedSimulator` |
| R6 | MEDIA | Clipping `[0,1]`/`[-1,1]` **enmascara inestabilidad numérica** | Con `dt=0.5` el sistema sigue "finito" y aparentemente estable; el blow-up queda oculto tras el clip. No hay guarda de estabilidad en `dt` |
| R7 | MEDIA | `monitoring*` declarado como paquete Python | Sólo contiene `alerts.yml` y `dashboard.json`; no hay paquete. 0 coincidencias |
| R8 | MEDIA | Bandit: 7 MEDIUM | `B104` bind-all (×2: `backend/app/main.py:226`, `massive/cli/main.py:201`), `B614` `torch.load` sin `weights_only` (×2 en `docs/examples/`), `B113` request sin timeout (×2), `B310` urlopen (`compare_arms.py:147`) |
| R9 | BAJA | Bandit: 41 LOW | 26 `assert` en código no-test, 5 subprocess, 2 `try/except/pass`, 2 `random` no-cripto, 2 `try/except/continue` |
| R10 | BAJA | Vulture: 5 variables asignadas y nunca usadas | `compare_arms.py:322`, `factbook/validator.py:277,728`, `conftest.py:43,61` |

**Nota sobre R2:** es el defecto más caro. El README vende *"Validación primero: protocolo anti-fuga pre-registrado"*. Si `prereg_*.yaml` se re-sella en cada `pytest`, la pre-registración no prueba nada: no hay forma de demostrar que los umbrales se fijaron **antes** de ver los datos.

---

## 3. ÁREAS OBSOLETAS

| # | Elemento | Evidencia | Coste |
|---|---|---|---|
| O1 | `api.py` raíz (506 líneas) — duplicado legacy de `backend/app/main.py` | Sólo usado por `massive.cli serve --legacy`, `install.sh:85`, `Makefile:50` y un test. Cobertura **32 %** | Dos apps FastAPI en paralelo; riesgo de divergencia de contrato |
| O2 | `simulator.py` (2463 líneas) — motor de reglas legacy con **semántica distinta** | CLI usa `rango=[0,1]`, `neutro=0.5`, `polarización=0.8186`. `multilayer_engine` usa `[-1,1]`, `neutro=0.0`, `polarización=0.70`. `massive_engine` da 0.577 | Tres verdades sobre "opinión" y "polarización" coexistiendo |
| O3 | Rastros de la capa Rust | 45 referencias a `rust_core` cuando el directorio se eliminó y el commit `30eee99` dice "all Rust audit findings resolved" | Documentación que describe arquitectura inexistente |
| O4 | Módulos referenciados que no existen | `mamba_engine` (14 refs), `neural_physics/pinns` (19/15), `llm_chat` (19), `energy_engine_pure` (9), `opinion_sources` (1), `MASSIVE_URCC_CONTRACT.md` (1), `CANONICAL_SOURCES.md` (15) | Onboarding: se documentan piezas fantasma |
| O5 | 29 referencias a `social_connectors` | Archivo borrado | Ruido de navegación |
| O6 | Explosión documental | **113 archivos `.md`**, 136 bajo `docs/`, incluyendo `docs/archive/process/AUDIT_REPORT_2026-09-15.md` (1400+ líneas) y `docs/audit/00_baseline.md` | Auditorías duplicadas; nadie sabe cuál manda |
| O7 | 16 ramas remotas, 5 fusionadas/obsoletas | `feature/hf-deployment`, `feature/phase10-production-hardening`, `fix/simular-multiples-clipping`, `phase3-v2-critical-fixes`, y `main` misma | Higiene |
| O8 | CfC cargado aunque está descalificado | En cada `MultilayerEngine.__init__` se importa `CfCRouter` y se calcula `tau_matrix`; el router imprime `R²=-18.732 → DISQUALIFIED` y no aplica nada | Trabajo desperdiciado en cada instanciación |

---

## 4. ÁREAS DE OPTIMIZACIÓN

### 4.1 Rendimiento y memoria

| # | Hallazgo | Medición |
|---|---|---|
| P1 | `_layers_flat` **denso (3, N, N) float64 se construye SIEMPRE**, aunque el paso real use la versión sparse CSR | N=200: 0.96 MB · N=500: 6 MB · N=1 000: 24 MB · **N=2 000: 96 MB** · extrapolado N=10 000: **2.4 GB** · N=100 000: **240 GB**. Pico de init medido en N=2 000: **293 MB** |
| P2 | `_multilayer_langevin_step_core` (ruta densa) es un **triple bucle Python O(L·N²)** | Sigue siendo alcanzable; la ruta sparse es O(L·N·k). Diferencia de órdenes de magnitud |
| P3 | `_create_drift_function` (ruta del stepper científico) usa `self._layers_flat[ell] @ ...` → **denso garantizado** | El modo "científico" es el más lento, contra toda intuición |
| P4 | CLIP como red de seguridad numérica en vez de guarda de estabilidad | Sin control adaptativo de `dt` en la ruta legacy (sí existe `AdaptiveStepper`, pero es opt-in) |

### 4.2 Cobertura de pruebas (total: **69.02 %**, mínimo exigido 30 %)

Peores módulos con ≥15 sentencias:

| Módulo | Cobertura | Sentencias sin cubrir |
|---|---:|---:|
| `massive/core/sentiment.py` | **0.0 %** | 17 |
| `massive/cli/main.py` | **0.0 %** | 100 |
| `ground_truth/_generate.py` | **0.0 %** | 324 |
| `backend/routers/benchmark.py` | 18.0 % | 29 |
| `massive_core/network_inference/reconstruct.py` | 20.7 % | 144 |
| `massive/core/extended_models.py` | 26.5 % | 147 |
| `backend/routers/forecast.py` | 29.0 % | 20 |
| `api.py` (legacy) | 32.2 % | 145 |
| `massive_core/physics/perturbation_theory.py` | 33.0 % | 104 |
| `backend/routers/engine.py` | 33.3 % | 22 |
| `massive/core/utility_logic.py` | 37.7 % | 41 |
| `backend/routers/llm.py` | 40.0 % | 50 |
| `massive/core/factbook/loader.py` | 50.0 % | 81 |
| `multilayer_engine_sparse.py` | 51.6 % | 121 |

**`massive/cli/main.py` al 0 %** mientras el README lo presenta como la vía "sin servidor". El quickstart #2 no tiene ni un test.

### 4.3 Tipado

- `mypy` sólo protege **25 archivos** (slices explícitos) y pasa limpio: `Success: no issues found in 25 source files`.
- `check_untyped_defs = false` y `strict = false` → el resto del código (**~230 archivos**) no está verificado.
- El "Type-check: MyPy (blocking)" del badge es real pero cubre ~10 % de la base.

### 4.4 Duplicación de conceptos

Cuatro métricas de polarización convivieron y se unificaron en `metrics/unified_metrics.py` (documentado). Pero los **valores siguen divergiendo** porque las dinámicas son distintas:

| motor | polarización medida |
|---|---:|
| `simulator.py` (CLI, [0,1]) | 0.8186 |
| `multilayer_engine.py` ([-1,1]) | 0.6970 |
| `massive_engine.py` (LOD) | 0.5774 |

La "única fuente de verdad" es la *fórmula*, no el *número*. Sin una tabla de referencia declarada, no hay forma de detectar regresiones entre motores.

### 4.5 Superficie de la API

`run_multilayer_simulation` expone `n_agents`, `steps`, `seed`, `layer_weights`. De esos cuatro, tres son irrelevantes para el output (ver §1.4). **La API no expone `coupling`, el único parámetro que importa.** El usuario no puede influir en el resultado aunque quiera.

---

## 5. PLAN DE CORRECCIÓN PROPUESTO (por orden de impacto, sin ejecutar aún)

### FASE 0 — Restaurar la verdad (bloqueante, ~1 día)
1. **Sincronizar `main`**: fusionar `a8ea32c` + `cfebab2` de `prod-readiness` (arregla R3), o abrir PR y mergear. Sin esto todo lo demás se construye sobre una foto muerta.
2. **R2 — Tests no deben escribir artefactos sellados**: aislar el sellado a `tmp_path`; los `prereg_*.yaml` y `splits.json` versionados deben ser de sólo lectura en tests. Añadir un test que falle si `git status` queda sucio tras `pytest`.
3. **R1 — `/v1` debe devolver series distintas por capa o dejar de fingirlo**: o se implementa el seguimiento por capa, o se sustituye por un único campo `series.opinion` y se elimina la ilusión de tres capas.

### FASE 1 — Reconstruir el acoplamiento (el núcleo, ~3-4 días)
4. **Definir la matriz de acoplamiento deseada** y codificarla explícitamente (no implícita en un potencial). Partir de hipótesis sociológicas declaradas con signo:
   - `info_access → opinion` (negativa o positiva según teoría de exposición selectiva) — hoy **no existe**
   - `cooperation → opinion` (retroalimentación) — hoy **no existe**
   - `hierarchy → cooperation` — hoy **no existe**
   - `income → info_access` — hoy **no existe**
5. **Hacer que `income` y `hierarchy` hagan algo**, o **sacarlas del vector de estado**. Mantener variables decorativas es peor que no tenerlas: inflan el estado, el coste y la ilusión de riqueza.
6. **Extender la fuerza de red a las 5 dimensiones** (o a las que queden) con pesos independientes por capa. Sin esto, "multicapa" no significa nada.
7. **Añadir un test de superficie de respuesta**: la polarización debe variar > 0.05 entre configuraciones declaradas razonables. Hoy varía < 0.005.

### FASE 2 — Limpieza de lo obsoleto (~2 días)
8. Purgar `api.py` raíz o congelarlo explícitamente como legacy con sunset date (O1).
9. Unificar `simulator.py` con la semántica de rango del motor principal, o retirarlo (O2, R5).
10. Eliminar las 29 + 45 + 14 + 19 referencias a módulos borrados (O3, O4, O5).
11. Consolidar `docs/`: un índice único, `docs/archive/` claramente marcado como histórico (O6).
12. Podar ramas remotas fusionadas (O7).
13. Cargar CfC de forma perezosa y sólo si el gate de calidad pasa (O8).

### FASE 3 — Rendimiento y calidad (~2 días)
14. Eliminar la construcción densa de `_layers_flat`; mantener CSR y materializar denso sólo bajo demanda explícita (P1, P3). Objetivo: N=10 000 viable.
15. Eliminar o reescribir la ruta densa con triple bucle Python (P2).
16. Sustituir el clip por detección de inestabilidad + `dt` adaptativo (P4, R6).
17. Cobertura: llevar `massive/cli/main.py`, `sentiment.py`, `backend/routers/*` y `network_inference` por encima del 60 %. Subir `fail_under` de 30 → 65 (P4.2).
18. Ampliar mypy más allá de los 25 archivos (P4.3).
19. Añadir tests de regresión numérica cross-engine con tabla de referencia (P4.4).

### FASE 4 — Exponer lo que importa (~1 día)
20. Añadir `coupling` (y las ganancias de acoplamiento de la Fase 1) al contrato de `/v1`. Hoy el único parámetro con efecto real es inaccesible (P4.5).
21. Publicar la curva `polarization(coupling)` con su punto de transición, que hoy es un comportamiento no documentado.

---

## 6. Resumen ejecutivo en cinco líneas

1. **Local y remoto NO están sincronizados**: 39 commits, 2 sin integrar; `main` está roto y `prod-readiness` lo arregla.
2. **El sistema de 5 variables sólo tiene 2 acoplamientos reales de 20 posibles, y ambos son positivos: no existe ninguna relación "una sube / otra baja" en el modelo.**
3. **4 de 5 variables son inertes**: perturbarlas no cambia ningún output del producto.
4. **El resultado es casi constante** (polarización ≈ 0.697 ± 0.005) para cualquier seed, tamaño, `dt` o pesos de capa; sólo `coupling` la mueve, y bruscamente (0.697 → 0.005).
5. **Antes de optimizar hay que reparar**: sellos que se re-escriben solos, endpoint que devuelve los datos tres veces, y 96 MB → 2.4 GB de matriz densa innecesaria.

---

*Análisis generado sobre `origin/main` @ b59c2ba en worktree aislado. Herramientas ejecutadas: pytest 9.1.1 (883 tests, 0 fallos), coverage 69.02 %, ruff 0.16.3 (limpio), mypy 2.4.0 (slices limpios), bandit 1.9.4 (48 hallazgos), vulture 2.16, más sondas empíricas propias de jacobiano, sensibilidad, escalado y estabilidad.*

---

## 7. Bitácora de ejecución del plan

### FASE 0.1 — Sincronizar `main` ✅
- Rama `sync/main-prod-readiness` creada desde `origin/main` + cherry-pick de `a8ea32c` y `cfebab2`.
- **PR #160 abierto**: https://github.com/Adlgr87/MASSIVE/pull/160 (13 archivos, +28/−40).
- Verificado: `grep -rn social_connectors --include=*.py` → 0 resultados.

### FASE 0.2 — Sellos inmutables (R2) ✅
Causa raíz: los sellos se re-escribían en cada ejecución porque
(a) `seal_splits()` estampaba `sealed_at = now()` siempre, y
(b) `pre_register()` estampaba `registered_at = now()` siempre, y
(c) los tests escribían en los directorios canónicos con parámetros propios.

Cambios:
- `ground_truth/_seals.py`: `seal_splits(splits_path=None)`; `sealed_at` **solo avanza si cambia el hash del payload**; eliminado el bug `sealed_at = _sha256_str` (asignaba un objeto función a un campo serializable).
- `massive/core/data_provenance.py`: caché por ruta resuelta (antes un `dict` global filtraba entradas entre registro real y de test); `registered_at` se preserva si el hash no cambió; `registry_path` opcional en `register_dataset` / `verify_integrity` / `get_registry`.
- `massive/core/backtesting.py`: `Backtester(prereg_dir=…, registry_path=…)`; una sola escritura autoritativa en vez de dos.
- `tests/conftest.py`: fixture de sesión que redirige los tres artefactos mutables a un directorio temporal + **guardia que falla la sesión** si un sello cambió (verificada: dispara correctamente).
- Tests endurecidos: `test_seal_splits_idempotent` ahora exige `sealed_at` estable; nuevos `test_seal_advances_only_when_payload_changes` y `test_registration_timestamp_is_immutable`.

Resultado: `pytest` deja el árbol **limpio** (antes ensuciaba 6 archivos versionados).

### FASE 0.3 — `/v1` deja de fingir tres capas (R1) + hallazgo R11 ✅
- `MultilayerEngine` gana `layer_opinion_profile()`: señal **real** por capa, `mean(A_ℓ · opinión)`.
  Aprovecha que las capas son row-stochastic → `mean(A_ℓ·x) = colsum(A_ℓ)/N · x`, un producto
  escalar O(N) por paso en vez de un segundo matvec.
- `series` pasa de `{social, digital, economic}` (idénticos) a
  `{opinion, layer_signal{social, digital, economic}}` con valores **distintos y veraces**.
- `llm_orchestrator` actualizado al nuevo contrato.

**Hallazgo R11 (nuevo, encontrado al implementar lo anterior):** `dynamic_rewiring()` refrescaba
solo `_layers_flat`, pero `step()` lee `_layers_sparse`. Medido: censura al 90 % eliminaba 720
aristas en la vista densa y **0** en la sparse → **las intervenciones de censura y viral-hub no
tenían ningún efecto sobre la simulación**. Ahora ambas vistas se reconstruyen juntas
(`_rebuild_layer_views()`). Verificado: el resultado final cambia con la intensidad de censura.

### FASE 1 — Reconstruir el acoplamiento ✅

**Matriz declarativa.** El acoplamiento deja de estar enterrado en el álgebra del potencial y pasa a
una tabla auditable: `DEFAULT_COUPLING_GAINS` (origen → destino, ganancia) con `COUPLING_RATIONALE`
(mecanismo citado por término). `multi_potential_gradient` la lee directamente.

| origen → destino | ganancia | mecanismo |
|---|---:|---|
| opinion → cooperation | +0.40 | alineación social *(ya existía)* |
| hierarchy → cooperation | +0.30 | conformidad / legitimidad **(nuevo)** |
| hierarchy → income | +0.40 | estratificación **(nuevo, sustituye al vínculo que se anulaba)** |
| cooperation → info_access | +0.20 | compromiso cívico *(ya existía)* |
| income → info_access | +0.30 | brecha digital **(nuevo)** |
| info_access → opinion | +0.50 | exposición selectiva — **cierra el ciclo** **(nuevo)** |

Densidad: **2/20 (10 %) → 6/20 (30 %)**, y ahora **existe un ciclo de retroalimentación**
(op → coop → info → op) donde antes solo había una cadena.

**Tres defectos de diseño corregidos:**
1. `income` era muerta: relajaba a 0.5 sin aristas de entrada. Ahora la jerarquía desplaza su *nivel*
   (no solo la velocidad). Dispersión medida: **0.099 → 0.199**.
2. `hierarchy` era biestable pero desconectada. Ahora mueve cooperación e ingreso.
3. La fuerza de red sólo tocaba `opinion`. Ahora actúa sobre las 5 dimensiones con
   `NETWORK_SUSCEPTIBILITY` (opinión 1.0, cooperación 0.30, jerarquía 0.20, ingreso 0.10, info 0.15),
   y con **un solo matmul sparse para las K columnas** en vez de K matvec separados.

**El acoplamiento de opinión se reformuló**: el acceso a información ya no aplica una fuerza lineal
(que daba un empujón del 1 %) sino que desplaza la *posición del pozo* del potencial bimodal. Es la
lectura correcta del efecto burbuja y produce el rango de respuesta que faltaba.

**Superficie de respuesta medida (antes: 0.697 ± 0.005 con todo):**

| palanca | rango de polarización | Δ |
|---|---|---:|
| ganancia exposición selectiva 0.0→0.75 | 0.6909 → 0.7820 | **0.091** |
| `coupling` 0.0→1.0 | 0.7249 → 0.8408 | **0.116** |
| `layer_weights` (social vs económico) | coop 0.4284 ↔ 0.5148, info 0.8213 ↔ 0.8447 | real |

**Ablación término por término — los 6 importan** (Δ en el output primario de cada uno):

| término eliminado | efecto medido |
|---|---|
| info_access → opinion | Δpolarización −0.0787 |
| cooperation → info_access | Δpolarización −0.0364 · Δinfo −0.0926 |
| hierarchy → income | Δincome −0.0407 |
| income → info_access | Δinfo −0.0165 |
| opinion → cooperation | Δcooperation −0.0335 |
| hierarchy → cooperation | Δcooperation −0.0348 |

**Tests.** Nuevo `tests/test_coupling_structure.py` (23 tests): la matriz está declarada y justificada,
la densidad no es una cadena, existe ciclo, cada término es funcional bajo ablación, `income` no es
muerta, `hierarchy` sigue biestable y consecuente, la red alcanza las 5 dimensiones, los signos
positivos mueven en la misma dirección y **un término negativo invierte la relación** (capacidad que
el modelo no tenía), la superficie de respuesta existe, y no hay saturación por clip.

**De paso:** el núcleo denso `_multilayer_langevin_step_core` pasó de triple bucle Python O(L·N²) a
un `matmul` vectorizado (P2).

### FASE 4 — Exponer los diales reales en el contrato `/v1` ✅
Antes, la API sólo ofrecía `n_agents`, `steps`, `seed` y `layer_weights`; los tres primeros no mueven
el resultado y `coupling` —el único dial con efecto— era inalcanzable.

- Nuevo DTO `MultilayerRequest` (`extra="forbid"`, cotas anti-DoS) con `coupling` (0–5),
  `dt` (acotado al límite de estabilidad de Euler explícito), `layer_weights` y `coupling_gains`.
- Nuevo endpoint **`POST /v1/engine/multilayer`**. Devuelve `landscape`, `series` (opinión + señal
  real por capa), `diagnostics` y `parameters` con la matriz de acoplamiento resuelta.
- `coupling_gains` acepta claves `"origen->destino"`, lo que permite ablacionar términos y plantear
  contrafactuales por HTTP. Claves inválidas → **422** con el nombre del error.
- `run_multilayer_simulation` acepta `coupling`, `dt`, `coupling_gains`.
- 10 tests de contrato nuevos (`tests/test_multilayer_endpoint.py`), incluido 401 sin clave,
  422 con campo desconocido, 422 con `dt` inestable y reproducibilidad por semilla.

### FASE 3 (parcial) — Memoria y núcleo denso ✅
- Eliminada la **copia densa duplicada** `_layers_flat` (L, N, N). Sólo la usaba la función de deriva,
  que ahora usa la vista sparse. La copia costaba exactamente lo mismo que `self.layers`: 96 MB en
  N=2 000 → 2,4 GB proyectados en N=10 000.
  **Pico de inicialización medido: 293 MB → 132 MB en N=2 000 (−55 %).**
- El núcleo denso `_multilayer_langevin_step_core` pasó de triple bucle Python O(L·N²) a un `matmul`
  vectorizado (ya en Fase 1).
- Suite: **918 tests, 0 fallos**.

### FASE 2 (resto) + FASE 3 (resto) ✅

**Hallazgo nuevo y grave — el gate de tipos del CI estaba roto.**
`.github/workflows/lint.yml` ejecutaba `mypy --config-file mypy.ini`, pero `mypy.ini` se había
eliminado al mover `[tool.mypy]` a `pyproject.toml`. mypy sale con código 2
(*"Cannot find config file"*) → **el job "Lint & Type Check" fallaba en cada ejecución** y el badge
*"Type-check: MyPy (blocking)"* del README no respaldaba nada. Además duplicaba el gate que
`typecheck.yml` sí hacía bien.
- `lint.yml` delega ahora en `scripts/typecheck_slice.py` (una sola definición autoritativa del slice).
- `PRODUCTION_ARCHITECTURE_SPEC.md` corregido (apuntaba a `mypy.ini`).
- Slice de tipos ampliado: **25 → 32 archivos**, incluyendo `multilayer_engine.py`,
  que quedó fuera de todo gate y por eso conservó la pila densa duplicada y el rewiring inerte.

**Obsoleto**
- CfC: ya no se carga por defecto (era un `torch` import + matriz τ + disclaimer en **cada**
  instanciación para aplicar cero corrección). Ahora opt-in (`use_cfc=True` / `MASSIVE_ENABLE_CFC=1`).
- `docs/archive/README.md`: el archivo se declara histórico y no normativo, con la lista de módulos
  muertos. Es lo que faltaba para que ~120 referencias a `rust_core`, `social_connectors`,
  `neural_physics`, `mamba_engine`… fueran *historia* en vez de documentación engañosa.
- **0 referencias en código** a módulos eliminados (blindado por test).

**Seguridad (bandit 48 → 41 hallazgos, 7 MEDIUM → 0)**
- `simulator.py`: timeout HTTP coercido con `_positive_timeout()`; antes un `llm_timeout` nulo dejaba
  la petición sin timeout y podía colgar el bucle de simulación.
- `compare_arms.py`: validación de esquema antes de `urlopen` (rechaza `file://`, `data:`, `ftp://`).
- `docs/examples/*`: `torch.load(..., weights_only=True)`.
- `massive serve`: bind por defecto **0.0.0.0 → 127.0.0.1**; exponer en todas las interfaces ahora es
  explícito.
- Falsos positivos documentados con `# nosec` + justificación (allow-list de Host, timeouts indirectos).

**Cobertura y calidad**
- `massive/cli/main.py`: **0 % → 74 %** (el quickstart del README no tenía ni un test).
- `massive/core/sentiment.py`: **0 % → 100 %** (decide el resultado de `compare_arms`).
- Total: **69.02 % → 70.03 %**. `fail_under` **30 → 65** (con 30 % el umbral no podía detectar nada).
- `--pasos` / `--n-runs` acotados como sus equivalentes HTTP; `--seed` añadido.

**Reproducibilidad — defecto de honestidad científica**
`DEFAULT_CONFIG` no tenía `seed`, así que **dos ejecuciones idénticas del CLI devolvían resultados
distintos**, pese a que el README promete *"seeded RNG everywhere"*. Lo detectó un test de
determinismo. Ahora la semilla por defecto es 42 y es sobreescribible.

**Contrato de empaquetado** (`tests/test_packaging_contract.py`) — encontró dos defectos reales:
- `metrics/py.typed` declarado como package-data pero **ausente** → los type-checkers ignoraban el paquete. Creado (PEP 561).
- el glob `adapters*` no resolvía a ningún paquete (`adapters/__init__.py` faltaba). Añadido.
- glob muerto `monitoring*` eliminado (no hay paquete Python; sólo hay YAML/JSON de despliegue).

---

## 8. Estado final verificado

| Gate | Antes | Después |
|---|---|---|
| `ruff check .` | limpio | limpio |
| `black --check .` | limpio | limpio |
| `mypy` (slice bloqueante) | **CI roto** (`mypy.ini` inexistente), 25 archivos | ✅ verde, **32 archivos** |
| `pytest` | 883 tests | **918 tests, 0 fallos** |
| Cobertura | 69.02 % (umbral 30) | **70.03 % (umbral 65)** |
| `bandit` | 48 (7 MEDIUM) | **41 (0 MEDIUM)** |
| Árbol tras `pytest` | **6 archivos sellados reescritos** | **limpio** |
| Acoplamientos entre variables | 2/20, sin ciclos, 0 negativos | **6/20, con ciclo, signo configurable** |
| Superficie de respuesta (polarización) | 0.697 ± 0.005 | **0.6909 → 0.8408** según palancas |
| Diales efectivos en la API | ninguno (`coupling` inaccesible) | `coupling`, `dt`, `coupling_gains` |
| Memoria init (N=2 000) | 293 MB | **132 MB** |

### Medición final del modelo reconstruido

| configuración | polarización | coop | `income` sd | `hierarchy` sd | `info` |
|---|---:|---:|---:|---:|---:|
| baseline (6 términos, coupling 0.3) | 0.7696 | 0.4834 | **0.1985** | 0.4432 | **0.6773** |
| ganancia exposición selectiva = 0.0 | 0.6909 | 0.4763 | 0.1985 | 0.4432 | 0.6767 |
| ganancia exposición selectiva = 0.75 | 0.7820 | 0.4814 | 0.1985 | 0.4432 | 0.6769 |
| `coupling` = 0.0 | 0.7249 | 0.4282 | 0.2088 | 0.4511 | 0.5688 |
| `coupling` = 1.0 | 0.8408 | 0.6398 | 0.1324 | 0.2914 | 0.9108 |
| **todos los acoplamientos ablacionados** | 0.6909 | 0.4202 | **0.0885** | 0.4432 | **0.5659** |

La última fila es la prueba de regresión más elocuente: ablacionar los seis términos **reproduce
exactamente la patología del modelo original** — `income` vuelve a morir (`sd` 0.1985 → 0.0885, el
0.099 medido en la auditoría) y `info_access` deja de estar acoplado. Si alguien deshace la matriz,
el comportamiento antiguo reaparece de inmediato y los tests lo detectan.

---

## 9. Segunda pasada: el CI real estaba en rojo (y por qué)

Al abrir los PRs descubrí que **`main` tenía 4 jobs de CI en rojo**, no por mi cambio sino por
defectos preexistentes que ningún análisis estático local podía ver. Los logs de GitHub Actions los
expusieron uno por uno.

| Job | Causa real | Estado |
|---|---|---|
| `Type Check (MyPy)` | `mypy: error: Cannot find config file 'mypy.ini'` → exit 2 | ✅ arreglado en Fase 2 |
| `Python Lint` | CI instalaba `ruff black mypy` **sin pin**, obteniendo un black más nuevo que el que el repo fija (`black==24.10.0`), que exigía reformatear `cache_manager.py` y `compare_arms.py` | ✅ arreglado |
| `incremental` (Secret scan) | gitleaks escanea `BASE^..HEAD`; con `fetch-depth` por defecto (1) el padre del commit base no existe → `ambiguous argument`, 0 bytes escaneados, exit 1 | ✅ arreglado |
| `compose-build-health` (Docker E2E) | **`Dockerfile:61-62` hace `COPY nginx.conf` y `COPY supervisord.conf`, y NINGUNO de los dos archivos existía en el repositorio.** `failed to compute cache key: "/supervisord.conf": not found` | ✅ arreglado |

### R12 — El Dockerfile no podía construir la imagen (CRÍTICO)

La imagen Docker era **imposible de construir**, no lenta ni frágil: faltaban dos archivos de
entrada. Se han creado, escritos para las restricciones que el propio Dockerfile impone:

- **`nginx.conf`** — sirve el SPA desde `/usr/share/nginx/html` y hace de gateway inverso a uvicorn.
  Escrito para nginx **sin root** (`USER appuser` + `setcap`): sin directiva `user`, `pid` y todos
  los directorios `*_temp_path` en `/tmp`, logs en `/var/log/nginx` (chown a appuser en el
  Dockerfile). Proxy para `/v1/*`, `/api/v1/*`, `/health`, `/ready`, `/metrics`, `/version`,
  `/docs`, `/redoc`, `/openapi*.json`; caché inmutable para `/assets/` (hashes de Vite) y
  `no-store` para `index.html`; fallback SPA.
- **`supervisord.conf`** — `uvicorn` en 127.0.0.1:8000 (loopback: nginx es la única entrada pública)
  y `nginx -g "daemon off;"`. Sin `user=`, porque el contenedor ya arranca como `appuser` y
  supervisord sólo puede *bajar* privilegios desde root, no cambiar entre usuarios no privilegiados.
  Sin `[eventlistener]`: un listener debe implementar el protocolo por stdin, y poner
  `supervisorctl status` ahí bloquearía el bucle de eventos.

**Verificación real, no asumida:**
- `nginx -t` en contenedor → `syntax is ok` / `test is successful`.
- Parseo con el propio parser de supervisor (`ServerOptions.realize`) → `CONFIG PARSED OK`, con
  ambos programas y `nodaemon=True`.
- `docker build` completo: no termina en tiempo razonable porque `requirements.txt` fija
  `torch>=2.2.0` sin índice CPU y descarga **~2,6 GB de stack CUDA** (`torch 539 MB`, `cudnn 519 MB`,
  `cublas 405 MB`, `triton 286 MB`…). **Hallazgo R13:** la imagen de un simulador que corre en CPU
  arrastra el stack CUDA completo; `torch --index-url .../whl/cpu` lo reduciría a ~200 MB. No lo
  cambié porque altera la resolución de dependencias para todos los usuarios.

### Corrección a mi propia auditoría — `api.py` sí es obsoleto, y el runbook era el defecto

Había clasificado `api.py` como "duplicado legacy" sin resolver quién lo consumía. Lo verifiqué y la
respuesta es contundente:

- `frontend/src/services/api.ts` usa `baseURL: "/v1"` y sus rutas son `/simulate`, `/llm/extract`,
  `/llm/wizard`, `/forecast`, `/engine/architect`, `/engine/energy`. **Cero** consumidores de `/api/*`,
  y el propio archivo lo documenta: *"The deprecated /api/* aliases are no longer referenced by this
  client."*
- El runbook `docs/runbooks/local-development.md` decía literalmente *"API legacy /api/* (la que usa
  el frontend React)"*. **Era falso**, y era lo que mantenía viva la API antigua.

Acciones: runbook corregido; `api.py` emite `DeprecationWarning` al importarse (con el destino
canónico en el mensaje); `massive serve --legacy` avisa en voz alta; 3 tests nuevos blindan las
afirmaciones (que el warning se emita, que nombre `backend.app.main`/`/v1`, y que el frontend no
vuelva a referenciar `/api/*`).

### Documentación

- `docs/architecture/coupling_matrix.md` — nuevo documento de referencia: vector de estado, matriz
  declarada con mecanismos citados, autodinámica, susceptibilidad de red, superficie de respuesta
  medida, tabla de ablación, invariantes que exigen los tests y guía para cambiar el modelo
  (incluido el recordatorio de re-derivar la calibración).
- `docs/api.md` — documentado `POST /v1/engine/multilayer` con su tabla de parámetros, forma de la
  respuesta y ejemplos de ablación por HTTP.
- `docs/index.md` — tabla **canónico vs histórico** que dice en qué confiar y para qué: no todos los
  `.md` valen igual, y ahora eso está escrito.
- `mkdocs.yml` — añadido al nav. `mkdocs build` verificado.
