# Runbook — Operaciones

> Operación del servicio en staging/producción. Revisado 2026-08-20.

## 1. Despliegue (Docker Compose, single-service recomendado)

```bash
# 1. Preparar secrets (fuera del repo)
cp .env.example .env.prod   # editar: MASSIVE_ENV=production, MASSIVE_API_KEY=<fuerte>,
                            # MASSIVE_CORS_ORIGINS=https://<dominio>, claves LLM si aplica
# 2. Build frontend + imagen
cd frontend && npm ci && npm run build && cd ..
docker compose -f docker-compose.single.yml up -d --build
# 3. Verificar
curl -fsS http://localhost:8000/health
curl -fsS http://localhost:8000/ready   # debe reflejar dependencias (LLM configurado)
```

## 2. Health / readiness

| Endpoint | Semántica | Acción si falla |
|---|---|---|
| `/health` | liveness (proceso vivo) | reinicio del contenedor (restart: unless-stopped) |
| `/ready` | readiness (dependencias: LLM creds, adapter) | NO reiniciar: revisar `.env` (claves LLM) — el servicio deliberadamente devuelve 503 si `/v1/llm` no es utilizable |
| `/version` | build metadata | — |

## 3. Configuración crítica de producción (checklist)

- [ ] `MASSIVE_ENV=production` (elimina fallback dev-secret-key).
- [ ] `MASSIVE_API_KEY` generada (≥32 chars aleatorios) y distribuida a clientes.
- [ ] `MASSIVE_CORS_ORIGINS` = dominios reales (sin `*`).
- [ ] `MASSIVE_RATE_LIMIT_BACKEND=file` si hay múltiples workers (+ `MASSIVE_RATE_LIMIT_PATH` en volumen compartido).
- [ ] `.env` montado read-only (compose ya lo hace).
- [ ] TLS terminado en el proxy externo (nginx interno no tiene TLS).

## 4. Logs y métricas

- Logs a stdout (supervisord los redirige); `MASSIVE_LOG_FILE` opcional para archivo.
- Kit UI-NG expone `/metrics` Prometheus (no cableado en despliegue actual).
- Buscar: `WARNING` (`dev fallback`, `wizard_config failed`), `ERROR` (fallos de dispatch).

## 5. Rollback

```bash
docker compose -f docker-compose.single.yml down
git checkout <tag-anterior> && docker compose -f docker-compose.single.yml up -d --build
```
El estado es stateless (sin DB en backends raíz) → el rollback es solo binario/config.

## 6. Backups

- No hay base de datos. Se consideran datos: `reports/` (resultados), `models/` (artefactos entrenados), `datasets/`. Respaldar por snapshot de volumen o git.
