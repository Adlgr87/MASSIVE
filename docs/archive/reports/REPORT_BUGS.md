# Reporte de Errores y Bugs — MASSIVE

> ⚠️ HISTÓRICO — describe el commit 2b70984 del 14 de septiembre de 2026. No refleja main actual.

**Fecha:** 2026-09-14  
**Estado tests:** ✅ 668 passed, 0 failed (32.2s)  
**Advertencia:** `StarletteDeprecationWarning` → httpx/starlette.testclient  
**Importaciones principales:** ✅ `backend.app.main:app` carga correctamente (20 endpoints)

---

## Tests Fallidos Actuales

| Test | Error | Estado | Prioridad |
|------|-------|--------|-----------|
| *(ninguno)* | — | Todos pasan | — |

---

## Bugs Conocidos

### BUG-01: InMemoryRateLimiter — Memory Leak por Acumulación de Keys
| Ubicación | Descripción | Workaround | Prioridad |
|-----------|-------------|------------|-----------|
| `massive_core/config/rate_limit.py:31-41` | `self._hits` es un `defaultdict(list)` que nunca elimina keys antigüas. Aunque la lista de timestamps por key se poda a 60s, la key en sí permanece en el diccionario para siempre. Con suficientes IPs distintas, el diccionario crece sin límite. | Usar `FileRateLimiter` en producción multi-IP, o añadir limpieza periódica. | 🔴 **Critical** |

```python
# Código actual (problemático):
def allow(self, key: str, limit_per_min: int) -> bool:
    now = time.time()
    window = [t for t in self._hits[key] if now - t < 60.0]  # Lista podada
    if len(window) >= limit_per_min:
        self._hits[key] = window
        return False
    window.append(now)
    self._hits[key] = window
    return True
    # ^ self._hits nunca se limpia de keys inactive
```

### BUG-02: LLM Router — `HTTPException` no atrapada explícitamente
| Ubicación | Descripción | Workaround | Prioridad |
|-----------|-------------|------------|-----------|
| `backend/app/routers/llm.py:114-131` | El `try/except` atrapa `ValueError` y `RuntimeError` pero no `HTTPException`. Si `run_llm_simulation` lanza una `HTTPException` interna, se propaga sin el `log.exception()` de seguridad, filtrando detalles internos. | Añadir `except HTTPException: raise` explícito en el bloque. | 🟡 **Medium** |

```python
# Faltante:
except HTTPException:
    raise
```

### BUG-03: Sim Router — Variable `_exc` sin uso (dead binding)
| Ubicación | Descripción | Workaround | Prioridad |
|-----------|-------------|------------|-----------|
| `backend/app/routers/sim.py:53` | `except Exception as _exc:` captura la excepción pero el logging usa `"v1/simulate error"` sin incluir el mensaje. El `from _exc` al final preserva el chain pero el log no muestra el detalle. | Cambiar a `logging.getLogger(...).exception("v1/simulate error: %s", _exc)` | 🟢 **Low** |

---

## Potenciales Race Conditions

| Código | Problema | Recomendación |
|--------|----------|---------------|
| `massive_core/config/rate_limit.py:33` — `InMemoryRateLimiter.allow()` | **No usa locking**. `defaultdict(list)` + lectura/escritura no atómica en Python GIL no garantiza atomicidad para `self._hits[key]`. En workers multi-hilo (uvicorn con `--workers > 1`), dos requests concurrentes pueden leer el mismo estado y ambos permitir o ambos rechazar. | Añadir `threading.Lock()` o usar `FileRateLimiter` para producción. |
| `backend/app/metrics.py:122-124` — `MetricsRegistry.observe()` | Acceso a `self._histograms` sin lock antes de verificar si existe. Aunque el GIL de Python lo hace seguro en CPython, es una práctica riesgosa que rompe en otras implementaciones (PyPy, Jython). | Mover la creación del histograma dentro del lock o usar `dict.get()` con locking. |
| `services/llm_orchestrator.py:720` — `uuid.uuid4()` | `sim_id` generado por `uuid.uuid4()` es seguro pero la combinación de `sim_id` + variables de estado compartido en el llamador podría crear condiciones de carrera si se usa en contexto asíncrono concurrente. | Asegurar que cada request tenga su propio scope de ejecución. |

---

## Memory Leaks Potenciales

| Código | Problema | Recomendación |
|--------|----------|---------------|
| `massive_core/config/rate_limit.py:31` — `InMemoryRateLimiter._hits` | Dictionary grows unboundedly — cada IP única crea una entry que nunca se elimina. En un servidor con alto tráfico de IPs únicas, esto crece linearmente. | Agregar periodic pruning: eliminar keys con listas vacías después de la ventana de 60s. |
| `backend/app/metrics.py:45-49` — `Histogram._counts`, `_sum`, `_total_count` | Los diccionarios indexados por `key` (tuple de labels) nunca se limpian. Cada combinación única de `{method, group, status}` agrega una entrada permanente. Con muchas etiquetas dinámicas (ej. user IDs en paths), esto es un leak. | Implementar eviction LRU o limitar el número de keys por histograma. |
| `services/llm_orchestrator.py:163` — `_aliases()` lru_cache(maxsize=1) | El cache está diseñado para una sola entrada. Como las llamadas ocurren con diferentes países, cada llamada nueva invalida la anterior (maxsize=1), causando que el cache sea prácticamente inútil y generando carga adicional de re-cálculo. | Aumentar `maxsize` a un valor razonable (ej. 32 o 64) o usar `maxsize=None` si el número de países es acotado. |
| `massive/core/factbook/loader.py` | Loader acumula datos de países sin TTL de expiración. Las llamadas repetidas a `load_country` con `force_reload=False` mantienen los datos en memoria indefinidamente. | Añadir TTL o implementar `weakref` para objetos grandes. |

---

## Error Handling Deficiente

| Ubicación | Problema | Mejora Sugerida |
|-----------|----------|-----------------|
| `backend/app/routers/sim.py:49-52` | `except HTTPException: raise` y `except ValidationError: raise` son redundantes — FastAPI ya re-lanza estas excepciones. El código funciona pero añade complejidad innecesaria. | Eliminar estos bloques y dejar que FastAPI maneje las excepciones naturalmente. |
| `backend/app/main.py:313-318` — `readiness_check` | `except Exception as exc:` captura todo pero solo registra el tipo. Si falla la importación de `simulator`, el error real se pierde en el log pero el healthcheck responde 503 sin el detalle. | Usar `except Exception as exc:` con logging del mensaje completo, o especificar `except (ImportError, ModuleNotFoundError)` para dar más contexto. |
| `backend/app/main.py:343` | `except Exception:` sin captura de variable — imposible loggear el error. | `except Exception as exc:` con `log.warning("UIL adapter unavailable: %s", exc)` |
| `services/llm_orchestrator.py:760` | `except Exception:` en `_sanitize_for_json` sin logging — silencia errores de serialización que podrían indicar bugs en los engines. | `except Exception as exc:` con `log.debug("sanitize skip: %s", exc)` |
| `services/llm_orchestrator.py:776` | Segundo `except Exception:` sin variable capturada en el bloque numpy check. | Unificar en un solo try/except al inicio de la función. |
| `massive_core/numerics/stability.py:298` | `except Exception:` sin captura — silencia errores de ARPACK/eigsh que podrían ser diagnósticos importantes. | `except Exception as exc:` con logging del error para debugging. |
| `massive/core/factbook/context.py:235` | `except Exception as e:` captura todo pero luego usa `f-string` en lugar de parámetros de logging (puede causar problemas de performance si el logging está disabled). | Usar `log.warning("...: %s", e)` en vez de f-string. |
| `massive/core/intervention_optimizer.py:118,244,317` | Tres bloques `except Exception as e:` sin logging de traceback. Los errores de Factbook se pierden silenciosamente. | Agregar `log.exception()` o `log.warning(..., exc_info=True)` para debugging. |
| `backend/app/routers/llm.py:218` | `except Exception as exc:` llama a `_public_error(exc)` que loguea con `log.exception()`. Correcto, pero el mensaje dice "Internal server error" que no ayuda al debugging del cliente. | Mantener el pattern actual pero agregar un campo `request_id` al detail para correlación. |

---

## Bugs de Lógica / Comportamiento

### BUG-04: LLM Router — `resolved` es unreferenced cuando `motor_hint` está presente
| Ubicación | Descripción | Prioridad |
|-----------|-------------|-----------|
| `backend/app/routers/llm.py:95-110` | La variable `resolved` se asigna dentro del bloque `if not motor_hint:` pero se referencia fuera en `"motor": motor_hint or resolved`. Python evalúa `motor_hint` primero (truthy → corta), pero si `motor_hint` es `None`/vacío, `resolved` debe estar definido. **Funciona**, pero es frágil: si la lógica cambia, puede causar `NameError`. | 🟡 Medium |

### BUG-05: Forecast Router — `confidence_lower` hardcoded a 0.05
| Ubicación | Descripción | Prioridad |
|-----------|-------------|-----------|
| `backend/app/routers/forecast.py:74-75` | Los intervals de confianza usan `±0.05` fijos en lugar de usar los valores reales del engine (`data.get("confidence_lower")`, etc.). Esto produce respuestas engañosas con CI arbitrario. | 🟡 Medium |

### BUG-06: Benchmark Router — No valida path de `cases`
| Ubicación | Descripción | Prioridad |
|-----------|-------------|-----------|
| `backend/app/routers/benchmark.py:51` | `cases = payload.get("cases", "datasets/pvu_cases")` acepta cualquier string. Un path malicioso como `../../etc/passwd` podría leer archivos del servidor. | 🟠 **High** |

### BUG-07: FileRateLimiter — Lock no se mantiene en error path
| Ubicación | Descripción | Prioridad |
|-----------|-------------|-----------|
| `massive_core/config/rate_limit.py:65-93` | El `fcntl.flock` se adquiere antes del `try` y se libera en el `finally`. Sin embargo, si `json.loads(raw)` falla (archivo corrupto), el lock se libera correctamente, pero el archivo queda sin cambios. Esto es **correcto**, pero si el archivo es persistentemente corrupto, cada request fallará con un error no manejado (no hay `except` alrededor del `json.loads`). | 🟢 Low |

---

## Lista de Reparaciones Priorizadas

1. **[Critical] InMemoryRateLimiter memory leak** — `massive_core/config/rate_limit.py`  
   Añadir limpieza de keys vacías después de la ventana de 60s.

2. **[High] Benchmark path injection** — `backend/app/routers/benchmark.py:51`  
   Validar que `cases` y `out` son paths relativos (no empiezan con `/` o `..`).

3. **[High] Race condition en InMemoryRateLimiter** — `massive_core/config/rate_limit.py:33`  
   Añadir `threading.Lock()` para acceso thread-safe.

4. **[Medium] Forecast confidence hardcoded** — `backend/app/routers/forecast.py:74-75`  
   Usar valores del engine en vez de ±0.05 fijo.

5. **[Medium] LLM router exception gap** — `backend/app/routers/llm.py:114-131`  
   Añadir `except HTTPException: raise` explícito.

6. **[Medium] LLM orchestrator lru_cache maxsize=1** — `services/llm_orchestrator.py:163`  
   Aumentar a `maxsize=64` para evitar thrashing.

7. **[Medium] Stability.py silent exception** — `massive_core/numerics/stability.py:298`  
   Capturar con logging para debugging de eigenvalue failures.

8. **[Low] Dead binding `_exc` en sim router** — `backend/app/routers/sim.py:53`  
   Usar `_exc` en el mensaje de log.

9. **[Low] Redundant HTTPException/ValidationError re-raise** — `backend/app/routers/sim.py:49-52`  
   Eliminar bloques redundantes.

10. **[Low] Readiness check exception detail** — `backend/app/main.py:316,325,343`  
    Mejorar logging con `exc_info=True` para diagnosticar fallos de import.

---

## Resumen Estadístico

| Categoría | Cantidad |
|-----------|----------|
| Bugs Critical | 1 |
| Bugs High | 1 |
| Bugs Medium | 4 |
| Bugs Low | 4 |
| Race Conditions | 2 |
| Memory Leaks | 4 |
| Error Handling Deficiente | 9 ubicaciones |
| Tests Fallidos | 0 |

**Total de hallazgos:** 21 issues identificados
