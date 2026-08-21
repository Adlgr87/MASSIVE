# Secretos y configuración — MASSIVE

> Cómo se gestionan secretos y configuración hoy (verificado 2026-08-20) y reglas obligatorias.

## 1. Inventario de variables de entorno

Fuente: `.env.example` (sin valores reales) + código. Ningún secreto real está versionado en HEAD.

### Núcleo
| Variable | Default | Uso | Riesgo si se filtra |
|---|---|---|---|
| `MASSIVE_API_KEY` | — (fallback `dev-secret-key` solo en `development`) | auth de API (`X-API-Key`) | acceso total a la API |
| `MASSIVE_ENV` | `development` | development/staging/production; controla fail-open/closed | — |
| `MASSIVE_CORS_ORIGINS` | localhost:1234,3000 | orígenes CORS | — |
| `MASSIVE_RATE_LIMIT_PER_MIN` | 60 | rate limit | — |
| `MASSIVE_RATE_LIMIT_BACKEND` | memory | memory/file | — |
| `MASSIVE_MAX_UPLOAD_MB` | 10 | límite upload | — |
| `MASSIVE_LOG_FILE`, `PYTHONHASHSEED` | — | logging/reproducibilidad | — |

### LLM
| Variable | Default | Uso |
|---|---|---|
| `PROVIDER` | groq | proveedor por defecto |
| `GROQ_API_KEY` / `OPENAI_API_KEY` / `OPENROUTER_API_KEY` | — | claves de proveedor |
| `OLLAMA_HOST` | http://localhost:11434 | LLM local |
| `MASSIVE_LLM_TIMEOUT_SECONDS` / `MASSIVE_LLM_MAX_RETRIES` | 120 / 3 | resilencia |

### Social / observabilidad
`TWITTER_BEARER_TOKEN`, `REDDIT_CLIENT_ID/SECRET`, `OTEL_EXPORTER_OTLP_ENDPOINT`, `MASSIVE_SLO_*`.

## 2. Reglas verificadas / pendientes

✅ **Correcto hoy**
- `.gitignore` cubre `.env`, `.env.*`, `.codebuff/`; `.dockerignore` excluye `*.env` (no se hornean en imagen).
- Los contenedores montan `.env` read-only en runtime.
- `massive/core/llm_credentials.py` evita propagar claves a `os.environ`/subprocesos (store en memoria).
- gitleaks (CI) verde en HEAD; regex manual de secretos → 0 hallazgos en árbol.

🟠 **Pendiente (plan)**
- **SEC-01**: token Zapier en historial → rotación (owner).
- **SEC-02**: inconsistencia `dev` vs `development` en `api.py`.
- **SEC-03**: `hmac.compare_digest` en ambos backends raíz.
- CI no imprime secretos (workflows revisados: solo `secrets.GITHUB_TOKEN`/`HF_TOKEN` como env, nunca `echo`).

## 3. Reglas obligatorias para contribuidores

1. Nunca commitear `.env*` con valores reales; ejemplos solo con placeholders.
2. Todo secreto nuevo entra a `.env.example` con placeholder + a esta tabla.
3. Los logs no deben contener claves (usar `llm_credentials`; no loguear headers).
4. Toda variable nueva debe leerse vía settings tipadas (`massive_core.config`) cuando sea posible.
5. Al rotar un secreto: actualizar el despliegue **antes** de invalidar el anterior (evitar outage).

## 4. Configuración por entorno

| Entorno | `MASSIVE_ENV` | API key | Comportamiento esperado |
|---|---|---|---|
| local | `development` (o unset en backend canónico) | opcional → fallback dev | fail-open documentado, warning en log |
| staging | `staging` | obligatoria | 503 si falta |
| producción | `production` | obligatoria | 503 si falta; sin fallback |

> Nota: `api.py` legacy solo acepta el valor exacto `dev` (bug SEC-02) — a corregir en Hito 1.
