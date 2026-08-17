# Docker Containerization Guide

This document describes how to build and run the MASSIVE UIL container.

## Prerequisites

- Docker installed (v20.10+)
- Docker Compose installed (v2.0+)
- At least 4GB RAM available for the container
- API keys configured in `.env.local` and/or `.env`

## Quick Start

```bash
# 1. Copy environment templates
cp .env.example .env
cp .env.local.example .env.local

# 2. Edit .env and .env.local with your API keys
# See .env.example for available options

# 3. Build and start
docker compose up -d --build

# 4. Access services
# API documentation: http://localhost:8000/docs
# Streamlit UI: http://localhost:8501
```

## Services

The container runs three processes via **supervisord**:

| Service       | Port  | Description                          |
| ------------- | ----- | ------------------------------------ |
| FastAPI API   | 8000  | REST API with OpenAPI docs at `/docs` |
| Streamlit UI  | 8501  | Web interface for MASSIVE           |
| Nginx         | 80    | Reverse proxy (optional)            |

## Commands

```bash
# Build and start in background
docker compose up -d --build

# View logs
docker compose logs -f massive

# Stop services
docker compose down

# Stop and remove volumes
docker compose down -v

# Rebuild without cache
docker compose build --no-cache

# Run a shell inside the container
docker exec -it massive-uil bash

# Check health
docker inspect --format='{{.State.Health.Status}}' massive-uil
```

## File Mounts

| Host File           | Container Path   | Purpose                                |
| ------------------- | ---------------- | -------------------------------------- |
| `.env`              | `/app/.env`      | Standard Python env vars               |
| `.env.local`        | `/app/.env.local`| Streamlit-specific env vars            |
| `reports/validation/` | Volume mount    | Persist benchmark reports              |

## Environment Variables

The `.env.example` file lists all available variables:

- `GROQ_API_KEY` — Groq Cloud API key
- `OPENAI_API_KEY` — OpenAI API key
- `OPENROUTER_API_KEY` — OpenRouter API key
- `OLLAMA_HOST` — Local Ollama endpoint (optional)
- `TWITTER_BEARER_TOKEN` — X/Twitter API token (optional)
- `REDDIT_CLIENT_ID` — Reddit API client ID (optional)
- `REDDIT_CLIENT_SECRET` — Reddit API client secret (optional)

## Dockerfile

The Dockerfile is based on `python:3.11-slim` and includes:

- System dependencies: `build-essential`, `poppler-utils`, `libmagic1`, `nginx`, `supervisor`
- Python dependencies from `requirements.txt`
- Non-root user `appuser` for security
- Health check endpoint on `/health`
- Multi-stage build: wheels built once, frontend built separately, runtime image slim.

### Single-Service Variant (API + UI on :8000)

For deployments that want a single container with the API serving the built
frontend, use the optimised Dockerfile and `docker-compose.single.yml`:

```bash
# Build frontend first
cd frontend && npm ci && npm run build

# Start single-service (API+UI on port 8000)
docker compose -f docker-compose.single.yml up -d --build
```

This variant uses `Dockerfile.optimized` which:
- Builds Python wheels once in a builder stage (no runtime network).
- Serves the FastAPI app directly via uvicorn on :8000.
- Mounts `frontend/dist` as a volume so no nginx/rebuild needed for frontend changes.
- Healthcheck targets `/health`.

### Docker Best Practices Applied

| Practice | How |
|----------|-----|
| Multi-stage builds | Wheels built in `builder-py`, frontend in `builder-fe`, slim runtime. |
| Layer caching | `requirements.txt` copied before app source; wheels cached. |
| Non-root user | `appuser` created and used for app processes. |
| No secrets baked | `.env` / `.env.local` mounted as read-only volumes. |
| `.dockerignore` | Excludes `node_modules/`, caches, data, `.env`, reports. |
| Healthcheck | `/health` liveness probe with 20s start period. |
| Minimal base | `python:3.11-slim`, `--no-install-recommends` for apt. |
| Pinned deps | All package versions pinned via `requirements.txt` / `pyproject.toml`. |

## Troubleshooting

### Container won't start

```bash
# Check logs
docker compose logs massive

# Ensure .env.local exists
ls -la .env.local .env

# Verify Docker is running
docker info
```

### Port already in use

```bash
# Change ports in docker-compose.yml
# Example: "8080:8000" for API, "8510:8501" for Streamlit
```

### Out of memory

The container needs at least 4GB RAM. Adjust in your Docker Desktop settings if needed.

### API not responding

```bash
# Check if the API is running
docker exec -it massive-uil ps aux

# Restart the API process
docker exec -it massive-uil supervisorctl restart api
```

## Security Notes

- The container runs as non-root user `appuser`
- API keys are mounted as read-only volumes
- No secrets are baked into the image
- Use `.env.local.example` as a template, never commit `.env.local`
