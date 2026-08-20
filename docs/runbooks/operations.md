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
| `/ready` | readiness — SOLO dependencias requeridas (settings + núcleo de simulación) | 503 ⇒ problema real del núcleo: revisar arranque/imports. Sin claves LLM devuelve **200 con `mode: "degraded"`** (solo `/v1/llm/*` se degrada; el resto de la API sigue sirviendo) |
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
- Cada request registra una línea estructurada `http request_id=… method=… path=… status=… duration_ms=…`
  y devuelve la cabecera `X-Request-ID` (eco si el cliente la aporta) para correlación.
- **`GET /metrics`** (backend canónico): formato texto Prometheus — contador
  `http_requests_total{method,group,status}` + gauge `massive_uptime_seconds`. Sin secretos.
  Scraping sugerido (30s): `massive_http_requests_total` por grupo `llm|simulate|forecast|engine|benchmarks|infra|other`.
- Límite de body: peticiones con `Content-Length > MASSIVE_MAX_BODY_MB` (default 10 MB) → 413.
- Buscar: `WARNING` (`dev fallback`, `wizard_config failed`), `ERROR` (fallos de dispatch).

## 5. Rollback

```bash
docker compose -f docker-compose.single.yml down
git checkout <tag-anterior> && docker compose -f docker-compose.single.yml up -d --build
```
El estado es stateless (sin DB en backends raíz) → el rollback es solo binario/config.

## 6. Backups

- No hay base de datos. Se consideran datos: `reports/` (resultados), `models/` (artefactos entrenados), `datasets/`. Respaldar por snapshot de volumen o git.
