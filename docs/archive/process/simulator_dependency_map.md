# MASSIVE — Mapa de dependencias transversales de `simulator.py`

## Propósito

Documentar, con base en evidencia del código local, cómo `simulator.py` articula el sistema MASSIVE y por qué debe tratarse como un nodo central de alto riesgo estructural.

Este documento corresponde al backlog recomendado como:
- **Slice D — Dependencias transversales del simulador**

---

## 1. Tesis central

`simulator.py` no es solo un módulo de simulación. En el estado actual del proyecto funciona como:

- API pública principal,
- orquestador de reglas y dinámicas,
- puente con LLM/CfC,
- punto de integración con motores internos,
- fuente de configuración compartida,
- proveedor de compatibilidad para wrappers,
- y dependencia transversal de múltiples subsistemas.

En otras palabras:

> `simulator.py` es actualmente uno de los principales núcleos sistémicos de MASSIVE.

---

## 2. Superficies públicas observadas en `simulator.py`

Funciones/clases clave observadas:
- `llamar_llm`
- `llamar_llm_heuristico`
- `simular`
- `simular_multiples`
- `simular_multiples_dask`
- `IntegratedSimulator`
- `run_with_schedule`

Estas superficies no solo sirven al propio módulo, sino que son consumidas desde varias capas del sistema.

---

## 3. Dependencias entrantes hacia `simulator.py`

## 3.1. UI principal

### Consumer
`app.py`

### Uso observado
Importa desde `simulator`:
- configuración (`DEFAULT_CONFIG`, `PROVEEDORES`, rangos)
- datos empíricos
- API principal de simulación
- métricas y helpers

### Implicación
La UI depende directamente del simulador como backend operativo principal.

---

## 3.2. Wrappers de compatibilidad

### Consumers
- `app/__init__.py`
- `massive_core/__init__.py`

### Uso observado
Reexportan la API pública del simulador.

### Implicación
Cambiar `simulator.py` impacta no solo a consumidores directos, sino a dos superficies de compatibilidad adicionales.

---

## 3.3. Social Architect

### Consumer
`social_architect.py`

### Uso observado
Importa:
- `run_with_schedule`
- `resumen_historial`
- `DEFAULT_CONFIG`

### Implicación
El arquitecto social depende del simulador para:
- ejecutar planes de intervención,
- evaluar resultados,
- y compartir configuración base.

---

## 3.4. Forecast temporal

### Consumers
- `forecast/engine.py`
- `forecast/scenarios.py`

### Uso observado
- `forecast/engine.py` importa `DEFAULT_CONFIG`
- `forecast/scenarios.py` importa `run_with_schedule`

### Implicación
El forecast no es completamente autónomo: usa al simulador como fuente de config y como ejecutor de estrategias.

---

## 3.5. Entrenamiento CfC

### Consumer
`cfc_trainer.py`

### Uso observado
Importa:
- `simular`
- `DEFAULT_CONFIG`

### Implicación
El pipeline de entrenamiento CfC depende del simulador como profesor o generador de dataset.

---

## 3.6. Benchmarks

### Consumer
`benchmarks/runner.py`

### Uso observado
En modo LLM intenta importar `simular`.

### Implicación
El benchmark runner considera al simulador como implementación real o proxy del comportamiento MASSIVE.

---

## 3.7. Motores y módulos auxiliares con dependencia puntual

### Consumer
`multilayer_engine.py`

### Uso observado
Consulta `PROVEEDORES` desde `simulator` dentro de `targeted_llm_bias`.

### Implicación
Existe acoplamiento inverso: no solo `simulator` depende de motores; al menos un motor depende también de datos del simulador.

---

## 4. Dependencias salientes desde `simulator.py`

## 4.1. Motores internos

### Imports observados
- `from massive_engine import MassiveEngine`
- `from multilayer_engine import MultilayerEngine`

### Implicación
`simulator.py` coordina o integra motores especializados dentro del sistema global.

---

## 4.2. Diagnóstico y benchmark interno

### Import observado
- `from benchmarks.butterfly_diagnostic import run_butterfly_diagnostic_core`

### Implicación
El simulador consume capacidades de benchmark/diagnóstico, no vive aislado de ellas.

---

## 4.3. Capa empírica

### Imports observados
Desde `empirical_calibration`:
- maestros empíricos
- runtime params
- metadata keys
- profile application helpers

### Implicación
La calibración empírica es parte estructural del simulador, no addon periférico.

---

## 4.4. Capa LLM / credenciales

### Import observado
- `from llm_credentials import resolve_provider_api_key`

### Implicación
El simulador contiene acceso directo a la infraestructura de proveedores LLM.

---

## 4.5. Capa CfC

### Import observado
- `from cfc_router import CfCRouter` (opcional)

### Implicación
El simulador puede elegir rutas neuronales rápidas además del selector heurístico/LLM.

---

## 4.6. Capa de modelos extendidos

### Import observado
- `from extended_models import regla_nash, regla_bayesiana, regla_sir` (opcional)

### Implicación
`simulator.py` concentra la ampliación del espacio de reglas dinámicas.

---

## 4.7. Utilidades matemáticas y de dominio

### Imports observados
- `schemas.GamePayoff`
- `utility_logic.calculate_strategic_force`

### Implicación
El simulador también es punto de composición de lógica matemática de teoría de juegos.

---

## 5. `IntegratedSimulator` como subcentro sistémico

La clase `IntegratedSimulator` merece atención especial.

### Responsabilidad observada
- crea `MassiveEngine`
- crea `MultilayerEngine`
- maneja drift, Lévy jumps y topology updates
- ejecuta butterfly diagnostics
- expone hooks contextuales
- emite runtime context reutilizable

### Implicación
Dentro de `simulator.py` ya existe un segundo nivel de orquestación de alto acoplamiento.

Conclusión:
- el archivo no solo contiene la simulación legacy “simple”
- también contiene un coordinador de dinámica integrada de orden superior

---

## 6. Tipos de acoplamiento detectados

## 6.1. Acoplamiento por API pública
Casos:
- `simular`
- `simular_multiples`
- `run_with_schedule`
- `DEFAULT_CONFIG`

## 6.2. Acoplamiento por configuración compartida
Casos:
- `PROVEEDORES`
- parámetros empíricos
- defaults usados por UI, forecast y training

## 6.3. Acoplamiento por ejecución
Casos:
- social architect ejecuta schedules vía simulador
- benchmark runner usa simulador
- trainer CfC usa simulador

## 6.4. Acoplamiento por fallback
Casos:
- CfC opcional
- LLM opcional
- modelos extendidos opcionales
- Dask opcional
- TDA opcional

## 6.5. Acoplamiento bidireccional parcial
Caso observado:
- `simulator.py` importa `multilayer_engine`
- `multilayer_engine.py` consulta `PROVEEDORES` desde `simulator`

Esto sugiere vigilancia especial: esa frontera puede ser frágil en un refactor estructural.

---

## 7. Riesgos estructurales específicos

### Riesgo 1 — Tratar `simulator.py` como mero módulo legacy
Sería incorrecto. Hoy sigue actuando como centro de integración.

### Riesgo 2 — Extraer piezas sin mapa de consumidores
Hay múltiples consumidores transversales con expectativas distintas:
- UI
- forecast
- architect
- trainer
- benchmark
- tests
- wrappers

### Riesgo 3 — Cambiar defaults/config compartida sin considerar efectos sistémicos
`DEFAULT_CONFIG` y símbolos asociados son consumidos desde varias áreas.

### Riesgo 4 — Romper flujos indirectos
Un cambio en `run_with_schedule`, `DEFAULT_CONFIG` o `PROVEEDORES` puede no romper el simulador principal, pero sí forecast, architect, training o UI.

---

## 8. Reglas derivadas para consolidación futura

1. No mover `simulator.py` en bloque como primer paso.
2. No separar `DEFAULT_CONFIG` ni `PROVEEDORES` sin mapa de consumers.
3. Cualquier extracción interna desde `simulator.py` debe mantener wrapper estable.
4. `IntegratedSimulator` requiere slice propio si se toca.
5. La frontera `simulator.py` ↔ `multilayer_engine.py` debe analizarse con cuidado por el acoplamiento bidireccional parcial.
6. Cualquier cambio en `run_with_schedule` debe validar también `forecast/scenarios.py` y `social_architect.py`.

---

## 9. Conclusión

El análisis confirma que `simulator.py` es hoy un **hub arquitectónico** de MASSIVE.

No es únicamente:
- un archivo legacy,
- ni un simple motor 1D,
- ni una API vieja pendiente de ser reemplazada.

Es, en la práctica, un nodo que enlaza:
- UI,
- engines,
- forecast,
- architect,
- benchmarks,
- entrenamiento CfC,
- compatibilidad pública,
- y configuración compartida.

Por ello, toda consolidación seria del proyecto debe diseñarse alrededor de este hecho y no contra él.
