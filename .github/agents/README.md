# Agent prompts (ubicación canónica)

Este directorio es la **única ubicación canónica** para prompts y definiciones de
agentes de IA del repositorio. No hay definiciones de agentes en `docs/` ni en
otros archivos sueltos: si necesitas un prompt de agente, vive aquí.

| Prompt | Propósito |
|---|---|
| [`massive-data-architect.agent.md`](massive-data-architect.agent.md) | Extraer métricas empíricas de eventos históricos y traducirlas a parámetros JSON calibrados para el motor de simulación (SDE de Langevin). |
| [`repo-surgeon.agent.md`](repo-surgeon.agent.md) | Auditoría y reparación integral del repositorio (mapeo → diagnóstico → fix → verificación). |

Estos prompts son herramientas de trabajo para asistentes de código; no forman
parte del runtime de MASSIVE ni de sus tests.
