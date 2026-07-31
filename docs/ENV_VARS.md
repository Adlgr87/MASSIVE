# MASSIVE environment variables

Canonical map for process configuration. YAML defaults live in
`massive_core/config/defaults.yaml` and are loaded by `get_app_settings()`.

## Core application

| Variable | Default | Description |
|----------|---------|-------------|
| `MASSIVE_API_KEY` | *(insecure dev fallback)* | API key expected in `X-API-Key` header |
| `MASSIVE_CORS_ORIGINS` | from YAML (`localhost:1234,3000`) | Comma-separated origins; overrides YAML when set |
| `MASSIVE_RATE_LIMIT_PER_MIN` | `60` | Max requests per client key per minute |
| `MASSIVE_RATE_LIMIT_BACKEND` | `memory` | `memory` (single worker) or `file` (multi-worker) |
| `MASSIVE_RATE_LIMIT_PATH` | `/tmp/massive_rate_limit.json` | Path when backend is `file` |
| `MASSIVE_MAX_UPLOAD_MB` | `10` | Max upload size for API file endpoints |
| `MASSIVE_LOG_FILE` | *(unset)* | If set, enables rotating file logging |
| `PYTHONHASHSEED` | *(unset)* | Use `42` in CI/experiments for hash stability |

## Logging (settings / YAML)

| Key / env | Default | Description |
|-----------|---------|-------------|
| `logging.level` / level override | `INFO` | Root log level |
| `logging.file` / `MASSIVE_LOG_FILE` | none | Rotating file path |
| `logging.max_bytes` | `10485760` | Rotate after this many bytes |
| `logging.backup_count` | `5` | Rotated file count |

## LLM / providers (services & architect)

| Variable | Used by |
|----------|---------|
| `GROQ_API_KEY` | Groq provider |
| `OPENAI_API_KEY` | OpenAI / fallback |
| `OPENROUTER_API_KEY` | OpenRouter |
| `PROVIDER` | Default provider label in some API paths |

## Scientific / runtime

Engine seeds are **not** global env vars — pass `seed=` / `config={"seed": …}` /
`ScientificRuntimeConfig` explicitly for reproducibility.

## Examples

```bash
export MASSIVE_API_KEY="replace-me"
export MASSIVE_CORS_ORIGINS="http://localhost:1234,http://localhost:3000"
export MASSIVE_RATE_LIMIT_PER_MIN=120
export MASSIVE_RATE_LIMIT_BACKEND=file
export MASSIVE_RATE_LIMIT_PATH=/var/tmp/massive_rl.json
export MASSIVE_LOG_FILE=logs/massive.log
export PYTHONHASHSEED=42
```
