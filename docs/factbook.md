# Integración CIA World Factbook

MASSIVE puede calibrar simulaciones con datos reales del **CIA World Factbook**
(demografía, economía, política y sociedad de 260+ países). Esta página es la
referencia consolidada de la integración; el historial completo del plan y su
ejecución vive en `docs/archive/process/`.

## Qué aporta

| Dato Factbook | Parámetro MASSIVE | Efecto en el motor |
|---|---|---|
| Población | `n_agents` (escalado a 100 000 máx.) | Tamaño de la simulación |
| Estructura de edad | `demographic_matrix` (5 cohortes) | Modulación θ por edad |
| Grupos étnicos / religiones / lenguas | `social_groups` + `social_pressure_weights` (1 − diversidad) | Presión social conformista → acoplamiento |
| Índice de Gini | `gini_coefficient`, `inequality_factor` | Dispersión de ingreso, σ del paisaje de energía, peso de la red |
| PIB per cápita | `cost_scale_factor` | Costo de intervenciones |
| Balance fiscal | `fiscal_constraint` (factibilidad [0,1]) | Presupuesto de intervención |
| Sectores económicos | `sector_multipliers` | Sesgo sectorial de intervenciones |

## Cómo se usa

### 1. Servicio (`services/factbook_service.py`)

```python
from services.factbook_service import country_params, build_engine_from_country

params = country_params("BR")            # parámetros derivados del país
engine = build_engine_from_country("BR") # MassiveEngine calibrado
```

### 2. Vía LLM (detección automática de país)

`POST /v1/llm/run_simulation` con un intent que mencione un país (p. ej.
*"Simula el paisaje de energía social para Brasil con desigualdad"*) inyecta
los parámetros del país automáticamente y los reporta en `factbook_params`.

### 3. Contexto directo

```python
from massive.core.factbook import get_factbook_context

ctx = get_factbook_context()          # data/factbook/factbook.json
params = ctx.get_massive_params("MX") # o "MEX", "Mexico"
```

## Datos

El repo incluye una **muestra** con 5 países en `data/factbook/` para tests y
desarrollo. El dataset completo se descarga aparte (ver `scripts/backup_factbook.sh`
y `docs/backup_restore.md`); el loader degrada de forma determinista a los
defaults documentados cuando el archivo no existe.

## Módulos

| Módulo | Rol |
|---|---|
| `massive/core/factbook/loader.py` | Carga y normalización del JSON |
| `massive/core/factbook/mappings.py` | Mapeo Factbook → parámetros MASSIVE |
| `massive/core/factbook/context.py` | `FactbookContext` + derivación de parámetros |
| `massive/core/factbook/validator.py` | Validación y reportes de calidad |
| `services/factbook_service.py` | Fachada para API/orquestador |

Las correlaciones derivadas (Gini → dispersión de ingreso y σ del paisaje,
balance fiscal → factibilidad, diversidad → presión social) están bloqueadas
por tests de dirección en `tests/test_correlation_invariants.py`.
