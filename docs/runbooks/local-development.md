# Runbook — Desarrollo local

> Verificado desde clonación limpia el 2026-08-20 (Python 3.11.2, Node 22). Linux/macOS.

## 1. Setup backend

```bash
git clone https://github.com/Adlgr87/MASSIVE.git && cd MASSIVE
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt     # incluye torch; ~90 s-10 min según red
cp .env.example .env                # NO commitear .env
```

## 2. Tests / lint / tipos

```bash
python -m pytest tests/ -q                        # suite completa (~40 s)
ruff check . && black --check .                   # lint/format
python scripts/typecheck_slice.py                 # mypy gradual
```

## 3. Arrancar APIs

```bash
# Backend canónico /v1/*
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
# → docs: http://localhost:8000/docs ; smoke: curl localhost:8000/health

# API legacy /api/* (la que usa el frontend React)
uvicorn api:app --host 0.0.0.0 --port 8000

# Auth en dev: X-API-Key: dev-secret-key (solo MASSIVE_ENV=development/unset en backend canónico)
curl -H "X-API-Key: dev-secret-key" -X POST localhost:8000/v1/simulate -H 'Content-Type: application/json' -d '{"pasos":5}'
```

> ⚠️ En `api.py` legacy el fallback dev exige `MASSIVE_ENV=dev` exacto (inconsistencia conocida SEC-02).

## 4. Frontend React (`frontend/`)

```bash
cd frontend && npm ci
npm run dev        # Vite :3000 con proxy /api → :8000
npm run build      # verifica build de producción (requiere fix de alias en HEAD de trabajo)
```

## 5. Rust (opcional)

```bash
# requiere toolchain Rust estable + maturin
pip install maturin && maturin develop --release
python -c "import massive_rust_core; print('ok')"
```

> Si `massive_rust_core` no está compilado, los motores usan fallbacks numpy (comportamiento soportado).

## 6. Docker (local)

```bash
cp .env.example .env
docker compose up --build          # nginx :80, API :8000
# variante single-service:
docker compose -f docker-compose.single.yml up --build
```

## 7. Problemas conocidos (2026-08-20)

| Síntoma | Causa | Estado |
|---|---|---|
| `python app.py` no existe | README desactualizado (UI Streamlit eliminada del repo) | corrección en camino (DOCS-01) |
| `npm run build` falla con `@/components/ui/button` | alias Vite ausente | corrección en camino (FE-01) |
| 2 módulos de tests no coleccionan | divergencia de contrato PR #84 | corrección en camino (TEST-01) |
