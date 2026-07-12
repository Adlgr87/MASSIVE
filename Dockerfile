# MASSIVE UIL container image
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    poppler-utils \
    libmagic1 \
    ca-certificates \
    curl \
    git \
    ffmpeg \
    nginx \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt /app/requirements.txt
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && pip install --no-cache-dir "uvicorn[standard]" "streamlit"

# Copy project code
COPY . /app

# Create non-root user
RUN adduser --disabled-password --gecos "" appuser || true
RUN chown -R appuser:appuser /app

USER appuser

# Expose ports (API, Streamlit, Nginx)
EXPOSE 8000 8501 80

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
    CMD curl -f http://127.0.0.1:8000/docs || exit 1

# Multi-process startup with supervisord
CMD ["/usr/bin/supervisord", "-n", "-c", "/app/supervisord.conf"]
