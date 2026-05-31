# MASSIVE — Mapa de compatibilidad y wrappers

## Propósito

Catalogar las superficies públicas, wrappers, adapters y reexports reales observados en el código local de `MASSIVE actualizado`.

Este documento corresponde al **Slice A — Mapa de wrappers y compatibilidad** del plan de consolidación.

---

## 1. Principio operativo

La compatibilidad observable actual de MASSIVE no está definida por una modularización interna completa, sino por una combinación de:
- módulos raíz consumidos directamente,
- wrappers ligeros,
- paquetes adaptadores,
- y contratos públicos estabilizados por tests.

Por eso, antes de cualquier consolidación, hay que distinguir:
1. **public surface activa**,
2. **wrapper/adapter**,
3. **API interna**,
4. **zona residual o parcial**.

---

## 2. Wrappers y adapters confirmados

## 2.1. `massive_core/__init__.py`

### Tipo
Wrapper / adapter explícito.

### Evidencia
- añade la raíz del repositorio a `sys.path`
- reexporta directamente desde `simulator`
- expone `__all__` con símbolos legacy del simulador

### Función actual
Actúa como superficie estable para consumidores nuevos **sin independizar aún la implementación**.

### Estado
- útil
- activo
- no redundante todavía

### Regla de consolidación
No tocar ni adelgazar sin prueba de equivalencia y sin mapa completo de consumidores.

---

## 2.2. `app/__init__.py`

### Tipo
Wrapper / compatibility surface.

### Evidencia
- permite `import app` como superficie de librería
- reexporta directamente desde `simulator`
- evita depender del runtime de Streamlit solo para imports básicos

### Función actual
Separar la UI interactiva (`app.py`) de una superficie importable de API básica.

### Estado
- útil
- activo
- compatible con consumers externos ligeros

### Regla de consolidación
Preservar mientras exista cualquier consumer que espere `import app`.

---

## 2.3. `forecast/__init__.py`

### Tipo
Public package surface.

### Evidencia
- reexporta:
  - `TemporalConfig`
  - `ForecastResult`
  - `forecast`
  - `ScenarioReport`
  - `compare_scenarios`
  - `apply_intervention`
- declara `__all__`

### Función actual
Sirve como superficie pública limpia del subdominio temporal.

### Estado
- estable
- útil
- ejemplo positivo de frontera de paquete bien definida

### Regla de consolidación
Tomarlo como modelo para futuros dominios, no desestructurarlo.

---

## 2.4. `backend/app/models/__init__.py`

### Tipo
Public surface agregadora.

### Evidencia
- reexporta DTOs desde:
  - `dto_architect`
  - `dto_forecast`
  - `dto_simulation`
  - `dto_snapshot`
- declara `__all__`
- es consumido por `scripts/gen_ts_types.py` y tests

### Función actual
Constituye la frontera pública del contrato backend/frontend.

### Estado
- estable
- importante
- contract-critical

### Regla de consolidación
No fragmentar ni modificar sin sincronizar tests y generación TS.

---

## 3. Superficies públicas activas sin wrapper intermedio

Estas superficies hoy son consumidas directamente por tests o por otros módulos.

### 3.1. `simulator.py`
Superficie pública principal del sistema.

Consumers observados directa o indirectamente:
- tests
- `app.py`
- `app/__init__.py`
- `massive_core/__init__.py`
- `social_architect.py`
- `forecast/engine.py`
- `forecast/scenarios.py`
- `cfc_trainer.py`
- `benchmarks/runner.py`
- `multilayer_engine.py` (consulta `PROVEEDORES` en fallback específico)

Conclusión:
- `simulator.py` es la mayor superficie de compatibilidad del repositorio.
- No debe tratarse como detalle interno aún.

### 3.2. `massive_engine.py`
Consumido directamente por tests y por `simulator.py`.

### 3.3. `multilayer_engine.py`
Consumido directamente por tests y por `simulator.py`.

### 3.4. `intervention_optimizer.py`
Consumido directamente por tests y por `social_architect.py`.

### 3.5. `social_architect.py`
Consumido por `app.py` y tests.

### 3.6. `forecast/`
Subdominio con superficie de paquete bien formada y uso transversal.

---

## 4. Zonas de compatibilidad semántica

## 4.1. Naming canónico completado

Las constantes empíricas tienen nombres `MASSIVE_*` como única forma activa:
- `MASSIVE_EMPIRICAL_MASTER`
- `MASSIVE_RUNTIME_PARAMS`

No existen aliases legacy en el código activo.

---

## 5. Zonas residuales o parciales

## 5.1. `massive/`

Hallazgo:
- la carpeta existe, pero el reconocimiento no muestra una migración operativa amplia dentro de ella
- `massive/core/micro/` existe como isla parcial

Conclusión:
- `massive/` no puede asumirse hoy como fuente de verdad global
- es una zona de modularización parcial o incompleta

## 5.2. `micro_massive/`

Hallazgo:
- en esta copia local parece residual: solo contiene `__pycache__`
- no apareció `__init__.py` ni módulos Python activos

Conclusión:
- es una zona históricamente relevante en documentos previos, pero en esta copia no funciona como superficie viva
- cualquier decisión sobre `micro_massive/` debe partir del estado real actual, no de documentación antigua

---

## 6. Clasificación operativa de compatibilidad

### Clase A — No tocar en fases tempranas
- `simulator.py`
- `massive_core/__init__.py`
- `app/__init__.py`
- `backend/app/models/__init__.py`
- `forecast/__init__.py`
- aliases backward-compatible ya usados en runtime

### Clase B — Tocar solo con slice dedicado
- `social_architect.py`
- `forecast/engine.py`
- `forecast/scenarios.py`
- `cfc_trainer.py`
- `benchmarks/runner.py`
- `multilayer_engine.py` (por dependencia puntual de `PROVEEDORES`)

### Clase C — Zonas a clarificar antes de intervenir
- `massive/`
- `massive/core/micro/`
- `micro_massive/`

---

## 7. Reglas prácticas derivadas

1. No eliminar wrappers actuales.
2. No suponer que `massive_core` reemplaza a `simulator` como implementación real.
3. No tocar superficies de paquete bien definidas (`forecast`, `backend.app.models`) sin plan específico.
4. Incluir aliases de naming en cualquier inventario de compatibilidad.
5. Tratar `massive/` como objetivo potencial de consolidación, no como realidad consolidada.

---

## 8. Conclusión

El mapa de compatibilidad actual de MASSIVE confirma una arquitectura híbrida:
- el runtime observable depende aún de módulos de raíz,
- los wrappers existentes sí cumplen una función real,
- hay subdominios con fronteras limpias (`forecast`, DTOs),
- y la modularización hacia `massive/` permanece parcial.

Por tanto, la consolidación segura debe seguir esta secuencia:
1. preservar superficies activas,
2. clarificar ownership y consumers,
3. fortalecer fronteras limpias ya existentes,
4. y solo después redirigir implementación interna.
