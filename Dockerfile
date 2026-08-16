# MASSIVE container image — single-service UI-NG (FastAPI backend + Vite frontend)
# Stage 1 — build the frontend (Vite)
FROM node:20-slim AS frontend
WORKDIR /build
COPY massive-ui-ng/frontend/package*.json ./
RUN npm ci --silent
COPY massive-ui-ng/frontend/ ./
RUN npm run build --silent

# Stage 2 — runtime image (Python backend + static frontend)
FROM python:3.11-slim
ENV PYTHONUNBUFFERED=1
ENV MASSIVE_SERVE_FRONTEND=1
WORKDIR /app

# Install system dependencies (nginx dropped: UI-NG is a single-process service)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    libmagic1 \
    ca-certificates \
    curl \
    git \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && pip install --no-cache-dir "uvicorn[standard]"

# Copy project code
COPY . /app
# Inject the built frontend into the path the backend serves
RUN mkdir -p /app/frontend/dist && \
    cp -r /build/dist/* /app/frontend/dist/

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser || true
RUN chown -R appuser:appuser /app

USER appuser

# Expose port (Frontend + API both served by uvicorn on 8000)
EXPOSE 8000

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -f http://127.0.0.1:8000/health || exit 1

# Single-process startup: uvicorn backend.app.main:app serves API + frontend
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
