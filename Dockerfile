# =============================================================================
# Dockerfile — MASSIVE UIL (multi-stage: wheels + frontend build + runtime)
#   Stage 1  builder-py    — pre-build python wheels (torch, torchdiffeq, …)
#   Stage 2  builder-fe    — build the React/Vite frontend into static files
#   Stage 3  runtime       — slim python:3.11-slim + nginx + supervisord
# =============================================================================

# --- Stage 1: Python wheels -------------------------------------------------
FROM python:3.11-slim AS builder-py
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /wheels

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential curl git libmagic1 poppler-utils ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /wheels/requirements.txt
RUN python -m pip install --upgrade pip setuptools wheel \
    && pip wheel --wheel-dir=/wheels -r /wheels/requirements.txt

# --- Stage 2: Frontend build ------------------------------------------------
FROM node:20-alpine AS builder-fe
WORKDIR /src

COPY frontend/package.json frontend/package-lock.json /src/
RUN npm ci --prefer-offline

COPY frontend /src
RUN npm run build

# --- Stage 3: Runtime -------------------------------------------------------
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
ENV PIP_NO_CACHE_DIR=1
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app

# OS deps: nginx + runtime libs needed by wheels (libmagic, poppler, ffmpeg)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl libmagic1 poppler-utils ffmpeg \
        nginx supervisor \
    && rm -rf /var/lib/apt/lists/*

# Non-root user for app processes
RUN adduser --disabled-password --gecos "" appuser

# Install python deps from wheels built in Stage 1 (no network at runtime)
COPY --from=builder-py /wheels /wheels
COPY requirements.txt /app/requirements.txt
RUN python -m pip install --upgrade pip setuptools \
    && pip install --no-index --find-links /wheels -r /app/requirements.txt \
    && pip install --no-cache-dir "uvicorn[standard]"

# Frontend static files -> served by nginx
COPY --from=builder-fe /src/dist /usr/share/nginx/html
# nginx runtime config
COPY nginx.conf /etc/nginx/nginx.conf
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# App sources (chown to appuser)
COPY . /app
RUN chown -R appuser:appuser /app /usr/share/nginx/html

USER appuser

# Ports: 80 (nginx front), 8000 (FastAPI), 8501 (Streamlit)
EXPOSE 80 8000 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

CMD ["/usr/bin/supervisord", "-n", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
