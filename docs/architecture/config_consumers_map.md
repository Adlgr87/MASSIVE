# MASSIVE — Mapa de consumidores de configuración compartida

## Propósito

Documentar quién consume actualmente las constantes compartidas del núcleo, en particular:
- `DEFAULT_CONFIG`
- `PROVEEDORES`
- `RANGOS_DISPONIBLES`

Este documento implementa el **Slice 2 — Inventario de consumers de `DEFAULT_CONFIG` y `PROVEEDORES`** y extiende el análisis a `RANGOS_DISPONIBLES` por su cercanía contractual.

---

## 1. Tesis

Estas constantes no son simples detalles internos de `simulator.py`. En el estado actual del proyecto funcionan como **contrato de configuración compartida** entre:
- simulador,
- UI,
- wrappers,
- forecast,
- training CfC,
- y al menos un motor especializado.

Por tanto, moverlas, renombrarlas o cambiar su shape sin plan dedicado tendría impacto sistémico.

---

## 2. `DEFAULT_CONFIG`

## 2.1. Owner actual
`simulator.py`

## 2.2. Rol
Configuración base compartida del sistema.

No solo define defaults del simulador principal; también actúa como fallback para otros subsistemas.

## 2.3. Consumidores observados

### A. `simulator.py`
#### Tipo de consumo
Interno, estructural, de alta criticidad.

#### Uso observado
- merge con `config` runtime en:
  - `simular`
  - `simular_multiples`
  - `simular_multiples_dask`
  - `resumen_historial`
  - `IntegratedSimulator`
- fallback para timeouts y temperatura LLM

#### Implicación
Es núcleo de comportamiento del simulador.

---

### B. `app.py`
#### Tipo de consumo
Directo, UI-facing, de alta criticidad.

#### Uso observado
- usa `DEFAULT_CONFIG["ollama_host"]` como default visible en UI

#### Implicación
Cambiar shape o mover esta constante afecta configuración visible al usuario.

---

### C. `app/__init__.py`
#### Tipo de consumo
Reexport / compatibilidad.

#### Implicación
Forma parte de la superficie pública estable.

---

### D. `massive_core/__init__.py`
#### Tipo de consumo
Reexport / adapter.

#### Implicación
Es parte de la compatibilidad de imports nuevos.

---

### E. `cfc_trainer.py`
#### Tipo de consumo
Directo, dataset generation, criticidad media-alta.

#### Uso observado
- base para construir `cfg` heurístico durante generación de dataset

#### Implicación
Cambios en shape o valores pueden alterar generación de datos de entrenamiento.

---

### F. `forecast/engine.py`
#### Tipo de consumo
Directo, fallback de cálculo, criticidad media.

#### Uso observado
- fallback de `ruido_base`
- fallback de `ruido_desconfianza`

#### Implicación
El forecast depende de defaults del simulador cuando el estado no trae config explícita.

---

## 2.4. Clasificación de criticidad

### Shape sensitivity
Alta.
Consumers esperan llaves concretas como:
- `ollama_host`
- `ruido_base`
- `ruido_desconfianza`

### Value sensitivity
Media-alta.
Cambios en valores por defecto pueden alterar UI, forecast y training.

### Move sensitivity
Muy alta.
El problema no es solo el contenido; también el path de import actual está ampliamente asumido.

---

## 3. `PROVEEDORES`

## 3.1. Owner actual
`simulator.py`

## 3.2. Rol
Registro de proveedores LLM y metadatos operativos.

Define por proveedor:
- `descripcion`
- `requiere_key`
- `base_url`
- `modelos_sugeridos`

## 3.3. Consumidores observados

### A. `simulator.py`
#### Tipo de consumo
Interno, estructural.

#### Uso observado
- dispatch de `llamar_llm`
- validación de proveedor
- resolución de modelos por defecto

---

### B. `app.py`
#### Tipo de consumo
Directo, UI-facing, de muy alta criticidad.

#### Uso observado
- poblar selectores de proveedor
- mostrar descripciones
- validar si el proveedor requiere API key
- poblar modelos sugeridos

#### Implicación
Es parte de la experiencia operativa de la UI.

---

### C. `app/__init__.py`
#### Tipo de consumo
Reexport / compatibilidad.

---

### D. `massive_core/__init__.py`
#### Tipo de consumo
Reexport / compatibilidad.

---

### E. `multilayer_engine.py`
#### Tipo de consumo
Directo puntual, pero arquitectónicamente sensible.

#### Uso observado
- `targeted_llm_bias` consulta `PROVEEDORES[proveedor]["base_url"]`

#### Implicación
Esto crea una dependencia del motor multicapa hacia datos de configuración del simulador.

## 3.4. Clasificación de criticidad

### Shape sensitivity
Muy alta.
La UI y el dispatch LLM esperan estructura exacta por proveedor.

### Value sensitivity
Alta.
Cambios en `base_url`, `requiere_key` o `modelos_sugeridos` impactan ejecución y UX.

### Move sensitivity
Muy alta.
Hay consumidores directos y reexports públicos.

---

## 4. `RANGOS_DISPONIBLES`

## 4.1. Owner actual
`simulator.py`

## 4.2. Rol
Catálogo de espacios de opinión y defaults asociados.

## 4.3. Consumidores observados

### A. `simulator.py`
#### Tipo de consumo
Interno, estructural.

#### Uso observado
- `_get_rango`
- defaults y clipping
- bloque `__main__`

---

### B. `app.py`
#### Tipo de consumo
Directo, UI-facing, de alta criticidad.

#### Uso observado
- poblar selector de espacio de opinión
- extraer `min`, `max`, `neutro`, `defaults`, descripción

#### Implicación
Es frontera entre core matemático y UI.

---

### C. `app/__init__.py`
#### Tipo de consumo
Reexport / compatibilidad.

---

### D. `massive_core/__init__.py`
#### Tipo de consumo
Reexport / compatibilidad.

## 4.4. Clasificación de criticidad

### Shape sensitivity
Alta.
La UI espera llaves como:
- `min`
- `max`
- `neutro`
- `defaults`
- `descripcion`

### Value sensitivity
Alta.
Cualquier cambio altera semántica de sliders, clipping y resultados.

### Move sensitivity
Alta.
Se reexporta y se consume directamente.

---

## 5. Resumen por criticidad

## `DEFAULT_CONFIG`
- criticidad global: **muy alta**
- uso principal: runtime + fallback + training + UI

## `PROVEEDORES`
- criticidad global: **muy alta**
- uso principal: dispatch LLM + UI + un cruce con `multilayer_engine`

## `RANGOS_DISPONIBLES`
- criticidad global: **alta**
- uso principal: clipping del core + interfaz de usuario + defaults

---

## 6. Reglas derivadas para consolidación

1. No extraer estas constantes de `simulator.py` sin inventario completo de consumers.
2. Si alguna se mueve, debe mantenerse wrapper estable en `simulator.py` durante transición.
3. `PROVEEDORES` y `RANGOS_DISPONIBLES` deben tratarse también como contrato de UI, no solo del core.
4. `DEFAULT_CONFIG` debe separarse por slice propio si se decide modularizar, porque afecta comportamiento y no solo imports.
5. La dependencia puntual de `multilayer_engine.py` sobre `PROVEEDORES` merece seguimiento específico.

---

## 7. Conclusión

El análisis confirma que `DEFAULT_CONFIG`, `PROVEEDORES` y `RANGOS_DISPONIBLES` forman una **frontera de configuración compartida**.

No son constantes locales del simulador en sentido estricto. Son parte del contrato sistémico del proyecto.

Por ello, cualquier consolidación futura debe tratarlas como activos arquitectónicos de alta sensibilidad.
