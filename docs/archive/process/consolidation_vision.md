# MASSIVE — Visión de consolidación estructural

## Propósito

Definir la visión arquitectónica que guiará la consolidación estructural de MASSIVE sin repetir errores destructivos del pasado.

Esta visión está basada en evidencia del código local y en una premisa explícita:

> MASSIVE es un sistema sinérgico. Sus partes no deben tratarse como funciones o paquetes independientes sin considerar sus interacciones reales.

---

## Visión

MASSIVE debe evolucionar hacia una base de código donde:

1. exista una **fuente de verdad clara por dominio**,
2. la **compatibilidad hacia atrás** permanezca preservada,
3. la **sinergia entre motores, UI, forecast, arquitecto social, contratos tipados y validación** quede explícita,
4. los cambios estructurales sean **reversibles, pequeños y verificables**,
5. y el sistema deje de depender de conocimiento implícito para mantenerse operativo.

---

## Qué significa “consolidar” en MASSIVE

En este proyecto, consolidar **no** significa:
- mover archivos masivamente,
- borrar wrappers por estética,
- imponer una nueva estructura sin pruebas,
- ni reemplazar la superficie legacy de una vez.

Aquí, consolidar significa:
- identificar ownership por dominio,
- hacer explícitas las dependencias sistémicas,
- reducir ambigüedad estructural,
- introducir límites sin romper la red de sinergias,
- y preparar migraciones internas graduales con superficies estables.

---

## Principios rectores

### 1. Conservación antes que reorganización
Si una pieza sostiene compatibilidad o integración, se conserva hasta demostrar equivalencia funcional.

### 2. Sinergia explícita
Los módulos se reorganizan respetando las interacciones reales entre:
- simulador principal,
- UI,
- forecast,
- social architect,
- motores especializados,
- CfC/LLM,
- DTOs y frontend,
- validación y benchmarks.

### 3. Migración por capas, no por entusiasmo
Primero se documenta. Después se encapsula. Después se redirige. Solo al final se elimina duplicación o se contrae superficie legacy.

### 4. La arquitectura observable la fijan los tests
La estructura ideal no prevalece sobre el comportamiento verificado.

### 5. Cada cambio estructural debe tener rollback simple
Si un paso no puede revertirse con facilidad, es demasiado grande para ejecutarse.

---

## Arquitectura objetivo de alto nivel

La meta no es eliminar lo legacy inmediatamente, sino llegar a una arquitectura con capas entendibles.

### Capa 1 — Public surface estable
Entradas públicas que pueden seguir existiendo por compatibilidad:
- `simulator.py`
- `massive_engine.py`
- `multilayer_engine.py`
- `energy_engine.py`
- `social_architect.py`
- `forecast/`
- `app/__init__.py`
- `massive_core/__init__.py`

### Capa 2 — Núcleos de dominio
Dominios internos con ownership explícito:
- simulación/orquestación
- motores especializados
- forecast temporal
- social architect / optimización
- contratos backend/frontend
- CfC / routing / credenciales
- validación científica y benchmarks

### Capa 3 — UI y delivery
- `app.py`
- frontend types
- scripts de generación
- conectores externos

### Capa 4 — Validación y seguridad
- tests
- benchmarks
- scripts de validación
- protocolos documentados

---

## Resultado deseado

Cuando la consolidación esté madura, debe ser posible responder sin ambigüedad:

- cuál es la fuente de verdad de cada dominio,
- qué módulos existen por compatibilidad,
- qué contracts no se pueden romper,
- cómo fluye la información entre subsistemas,
- y qué pruebas verifican cada frontera.

---

## No objetivos en la fase actual

En esta etapa no se busca:
- una reescritura total,
- un rename global,
- una eliminación agresiva de wrappers,
- ni la unificación física inmediata de todos los módulos.

El objetivo actual es preparar una consolidación **segura, entendible y ejecutable**.
