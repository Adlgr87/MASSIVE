# MASSIVE — Compatibilidad de naming

## Estado actual

La transición de naming desde el nombre anterior del proyecto a `MASSIVE` está
**completamente terminada**.

Las constantes canónicas activas son:
- `MASSIVE_EMPIRICAL_MASTER`
- `MASSIVE_RUNTIME_PARAMS`

No existen aliases legacy en el código. Todos los consumers internos usan los
nombres `MASSIVE_*` directamente.

---

## Reglas de naming para código nuevo

1. Usar siempre `MASSIVE_EMPIRICAL_MASTER` y `MASSIVE_RUNTIME_PARAMS`.
2. No introducir referencias al nombre anterior del proyecto.
