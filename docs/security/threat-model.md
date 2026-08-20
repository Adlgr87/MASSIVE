# Modelo de amenazas — MASSIVE

> Alcance: aplicación (APIs HTTP, workers, contenedores), cadena de suministro (dependencias, CI/CD),
> y superficie LLM. Fecha: 2026-08-20. HEAD: `288ba9a`.

## 1. Activos y confianza

| Activo | Descripción | Nivel de confianza requerido |
|--------|-------------|------------------------------|
| Motores científicos | simulador y su correctitud numérica | interno confiable |
| Claves LLM (GROQ/OPENAI/OPENROUTER) | env vars del servidor | secreto — nunca al cliente |
| `MASSIVE_API_KEY` | autenticación de la API | secreto de operador |
| Tokens sociales (Twitter/Reddit) | seeding opcional | secreto — nunca al cliente |
| Uploads (`/api/extract`) | PDF/CSV/JSON/XLSX/TXT/MD de usuarios | **no confiable** |
| Prompts de usuario (`/v1/llm/run_simulation`, `/api/wizard`) | entrada natural | **no confiable** (prompt injection) |
| Datos Factbook | JSON local | confiable (repo) |
| Respuestas LLM | salida de proveedor externo | **no confiable** (validar antes de usar como config) |

## 2. Superficie de ataque (verificada)

1. **HTTP público**
   - `api.py` (legacy): `/api/extract` (upload), `/api/wizard` (LLM), `/api/simulate-uil`, `/api/v1/*`. Auth `X-API-Key` (comparación `!=`, no constant-time — SEC-03). Rate limit por IP (60/min por defecto, configurable). Límite de upload `MASSIVE_MAX_UPLOAD_MB=10` y allowlist de extensiones — correcto.
   - `backend/app` (canónico): `/v1/*` con DTOs pydantic `extra=forbid` — buena validación de borde. Mismo esquema de auth.
   - CORS: orígenes por env, sin `*` cuando hay credentials — correcto.
   - Kit UI-NG (no expuesto actualmente): auth multi-key constant-time, security headers, TrustedHost.
2. **Contenedores**: runtime no-root (`appuser`) — correcto. nginx sin TLS (se asume terminator externo). supervisord con streamlit fantasma (OPS-02).
3. **CI/CD**: `secret_scan` (gitleaks) verde; workflows con `permissions` mínimos en lint/validate; **deploy a Azure en push a main** sin gate de tests (revisar `main_massive.yml`); HF sync requiere `HF_TOKEN` (fallo actual, no riesgo).
4. **Cadena de suministro**: `pip-audit` limpio (2026-08-20); lockfile Rust (`Cargo.lock`) versionado; `package-lock.json` frontend versionado.

## 3. Amenazas (STRIDE resumido) con estado

| ID | Amenaza | Vectores | Estado/mitigación actual | Gap |
|----|---------|----------|--------------------------|-----|
| T1 | Fuga de secreto versionado | historial git | gitleaks en HEAD ✅; **token Zapier en historial** | 🔴 rotar (SEC-01) |
| T2 | Timing attack sobre API key | `!=` en auth | parcial | 🟡 SEC-03 |
| T3 | Enumeración/abuso de API sin auth | fallback dev key | fallback solo en `development`; legacy además exige `dev` (inconsistencia SEC-02) | 🟠 unificar + tests |
| T4 | Prompt injection → config maliciosa | intent NL → wizard LLM → config de motores | respuestas LLM pasan por `wizard_config`; campos finales validados por DTOs `extra=forbid` en `/v1`; `/api/wizard` (legacy) devuelve config sin aplicar | 🟡 revisar allowlist de claves de config en el merge (`partial_config`, `config_overrides`) |
| T5 | SSRF vía `OLLAMA_HOST` | env controlado por operador (no usuario) | no user-controlled | ✅ (verificar que ningún endpoint acepte URLs de usuario) |
| T6 | Path traversal en uploads | `tempfile.NamedTemporaryFile(suffix=_safe_suffix(...))` con allowlist de extensiones | allowlist implementada; archivo temporal; sin path de usuario | ✅ (mantener test) |
| T7 | DoS por payloads enormes | JSON body sin límite global explícito (upload sí limitado a 10 MB) | rate limit 60/min | 🟡 límite de body para JSON endpoints (Hito 4) |
| T8 | Ejecución arbitraria vía deserialización | JSON/pydantic únicamente; sin pickle/yaml.load inseguros en superficie auditada | `grep` sin hallazgos en endpoints | ✅ |
| T9 | Stack traces / rutas internas al cliente | legacy `_public_error` en extract; otros endpoints envuelven en HTTPException | parcial | 🟡 revisar handlers globales (Hito 2) |
| T10 | Abuso de LLM (coste) | llamadas a proveedores por request | rate limit; `MASSIVE_LLM_TIMEOUT_SECONDS`/retries | 🟡 presupuesto por key (futuro) |

## 4. Acciones requeridas

1. **Owner (urgente)**: rotar `ZAPIER_MCP_TOKEN` (SEC-01). El token es recuperable por cualquier persona desde el historial público.
2. Hito 1 del plan: SEC-02/SEC-03 con tests.
3. Revisión de `main_massive.yml` (deploy Azure post-push) para que dependa de checks verdes.
