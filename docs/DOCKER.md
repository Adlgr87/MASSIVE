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
- Health check endpoint on `/docs`

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
