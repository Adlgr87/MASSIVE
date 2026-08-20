# Runbook — Incidentes

> Plantillas y diagnóstico. Revisado 2026-08-20.

## 1. Detección

- CI roja en main (`gh run list --branch main`) — la señalización principal actual.
- Healthcheck Docker falla (`/health`) → contenedor reinicia automáticamente.
- Cliente reporta 401/429/503/5xx.

## 2. Diagnóstico rápido

| Síntoma | Causas probables | Comandos |
|---|---|---|
| 401 en todo | `MASSIVE_API_KEY` mal montada o cliente sin `X-API-Key` | `docker exec <c> env \| grep -c MASSIVE_API_KEY` (sólo contar, no imprimir valores); revisar header del cliente |
| 503 "API key not configured" | `MASSIVE_ENV=production|staging` sin key | montar `.env` correcto |
| 503 desde `/v1/llm/*` | claves LLM ausentes (dependencia declarada) | revisar `GROQ_API_KEY`/`PROVIDER` |
| 429 | rate limit (60/min default) | subir `MASSIVE_RATE_LIMIT_PER_MIN` o usar backend `file` |
| Contenedor reinicia en bucle | proceso supervisord muriendo (p.ej. streamlit fantasma histórico OPS-02) | `docker logs <c>`; buscar `FATAL Exited too quickly` |
| Latencia alta en simulate | motores con muchos pasos/agentes | reducir `pasos`/`n_agents`; revisar CPU del host |

## 3. Incidente conocido: secreto expuesto

- **Token Zapier en historial git** (SEC-01): mitigación = rotación en el proveedor (owner). Hasta rotar, tratar el token como comprometido; el repo es público.

## 4. Escalamiento y comunicación

1. Congelar merges a main (owner).
2. Documentar en este archivo: síntoma, impacto, causa raíz, fix, prevención.
3. Post-incidente: añadir test de regresión si aplica.

## 5. Roles

- **Owner (Adlgr87)**: secrets, rotaciones, branch protection, deploys externos (Azure/HF/PyPI/Docker Hub).
- **Agent/contribuidores**: código, tests, docs; nunca rotación de secretos.
