#!/usr/bin/env bash
# =============================================================================
# install.sh — MASSIVE unified install / run / docker / clean script
# =============================================================================
# Usage:
#   ./install.sh install          # pip install -e .[dev]       (editable + dev deps)
#   ./install.sh install-dev      # pip install -e .[full]      (all extras incl. ML/SCI)
#   ./install.sh run             # uvicorn backend.app.main:app (API only)
#   ./install.sh docker          # docker compose up -d --build
#   ./install.sh test            # pytest tests/  (PYTHONHASHSEED=42)
#   ./install.sh lint            # ruff + black + mypy (Python) + eslint (frontend)
#   ./install.sh benchmark       # python -m benchmarks.runner --offline (PVU-BS)
#   ./install.sh benchmark-llm   # python -m benchmarks.runner --llm (requires API keys)
#   ./install.sh docs            # mkdocs serve (local) or mkdocs build
#   ./install.sh clean           # remove venvs, caches, __pycache__
#
# Environment variables (see .env.example for full reference):
#   MASSIVE_API_KEY, MASSIVE_ENV, MASSIVE_CORS_ORIGINS, GROQ_API_KEY, etc.
# =============================================================================

set -euo pipefail

# Color output helpers
if [ -t 1 ]; then
    GREEN='\033[0;32m'
    YELLOW='\033[1;33m'
    RED='\033[0;31m'
    NC='\033[0m'
else
    GREEN=''
    YELLOW=''
    RED=''
    NC=''
fi

# Project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Python binary detection
if command -v python3 &>/dev/null; then
    PY="python3"
elif command -v python &>/dev/null; then
    PY="python"
else
    echo -e "${RED}ERROR: Python not found. Install Python 3.11+ and try again.${NC}"
    exit 1
fi

PYTHON_VERSION=$($PY --version 2>&1 | grep -oP '\d+\.\d+')
if [ "$(printf '%s\n' "3.11" "$PYTHON_VERSION" | sort -V | head -n1)" != "3.11" ]; then
    echo -e "${YELLOW}WARNING: Python $PYTHON_VERSION detected. MASSIVE requires 3.11+.${NC}"
fi

pip_cmd() {
    $PY -m pip "$@"
}

# --- Commands ----------------------------------------------------------------

cmd_install() {
    echo -e "${GREEN}>>> Installing MASSIVE (editable + dev dependencies)${NC}"
    pip_cmd install --upgrade pip setuptools wheel
    pip_cmd install -e ".[dev]"
    echo -e "${GREEN}>>> Installation complete.${NC}"
    echo -e "   Run: ${YELLOW}./install.sh run${NC} to start the backend server"
}

cmd_install_dev() {
    echo -e "${GREEN}>>> Installing MASSIVE (editable + ALL extras)${NC}"
    pip_cmd install --upgrade pip setuptools wheel
    pip_cmd install -e ".[full]"
    echo -e "${GREEN}>>> Full installation complete.${NC}"
    echo -e "   Run: ${YELLOW}./install.sh run${NC} to start the backend server"
}

cmd_run() {
    echo -e "${GREEN}>>> Starting MASSIVE backend (backend.app.main:app)${NC}"
    export PYTHONUNBUFFERED=1
    # Prefer backend.app.main:app; fall back to legacy api:app
    if $PY -c "import backend.app.main" 2>/dev/null; then
        $PY -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
    else
        echo -e "${YELLOW}>>> backend.app.main not importable, falling back to api:app${NC}"
        $PY -m uvicorn api:app --host 0.0.0.0 --port 8000
    fi
}

cmd_docker() {
    echo -e "${GREEN}>>> Building and starting MASSIVE via Docker Compose${NC}"
    docker compose build
    docker compose up -d
    echo -e "${GREEN}>>> Stack started.${NC}"
    echo -e "   Frontend + API gateway:  ${YELLOW}http://localhost${NC}"
    echo -e "   API (direct):            ${YELLOW}http://localhost:8000${NC}"
    echo -e "   Streamlit UI:            ${YELLOW}http://localhost:8501${NC}"
    echo -e "   Logs:             ${YELLOW}docker compose logs -f${NC}"
}

cmd_test() {
    echo -e "${GREEN}>>> Running test suite (PYTHONHASHSEED=42)${NC}"
    PYTHONHASHSEED=42 $PY -m pytest tests/ -q --tb=short
}

cmd_lint() {
    echo -e "${GREEN}>>> Linting (Python)${NC}"
    $PY -m pip install --quiet ruff black mypy 2>/dev/null || true
    $PY -m ruff check . || true
    $PY -m black --check . || true
    $PY -m mypy --config-file mypy.ini massive/ backend/ services/ 2>/dev/null || true
    echo -e "${GREEN}>>> Linting (Frontend)${NC}"
    if [ -d "frontend/node_modules" ]; then
        (cd frontend && npm run lint 2>/dev/null) || true
    fi
    echo -e "${GREEN}>>> Lint complete.${NC}"
}

cmd_benchmark() {
    echo -e "${GREEN}>>> Running PVU-BS benchmark (offline mode)${NC}"
    $PY -m benchmarks.runner --cases datasets/pvu_cases --offline \
        --out reports/validation/ci --seed 42
}

cmd_benchmark_llm() {
    echo -e "${GREEN}>>> Running PVU-BS benchmark (LLM mode)${NC}"
    _llm_key="${OPENROUTER_API_KEY:-${OPENAI_API_KEY:-${GROQ_API_KEY:-}}}"
    if [ -z "$_llm_key" ]; then
        echo -e "${YELLOW}WARNING: No LLM API key found in environment.${NC}"
        echo -e "   Set OPENROUTER_API_KEY, OPENAI_API_KEY, or GROQ_API_KEY"
        exit 1
    fi
    $PY -m benchmarks.runner --cases datasets/pvu_cases --llm \
        --out reports/validation/ci --seed 42
}

cmd_docs() {
    if command -v mkdocs &>/dev/null || $PY -m mkdocs --version &>/dev/null 2>&1; then
        echo -e "${GREEN}>>> Starting MkDocs server (http://localhost:8000)${NC}"
        $PY -m mkdocs serve
    else
        echo -e "${YELLOW}>>> Installing MkDocs...${NC}"
        pip_cmd install -e ".[docs]"
        $PY -m mkdocs build
        echo -e "${GREEN}>>> Docs built in site/${NC}"
    fi
}

cmd_clean() {
    echo -e "${YELLOW}>>> Cleaning build artifacts, caches, and virtual environments${NC}"
    rm -rf .venv venv .eggs "*.egg-info" build/ dist/
    find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
    find . -type f -name "*.pyc" -delete 2>/dev/null || true
    rm -f .coverage
    echo -e "${GREEN}>>> Clean complete.${NC}"
}

cmd_help() {
    cat <<'EOF'
MASSIVE install.sh — Unified management script

Usage: ./install.sh <command>

Commands:
  install        pip install -e .[dev]     (editable + dev deps)
  install-dev    pip install -e .[full]    (all extras incl. ML/SCI)
  run            Start backend (backend.app.main:app) on :8000
  docker         docker compose up -d --build
  test           pytest tests/ (PYTHONHASHSEED=42)
  lint           ruff + black + mypy + eslint
  benchmark      PVU-BS benchmark (offline mode)
  benchmark-llm  PVU-BS benchmark (LLM mode, requires API keys)
  docs           mkdocs serve (or build if no server)
  clean          Remove venvs, caches, __pycache__
  help           Show this help

Environment:
  See .env.example — copy to .env for Docker, .env.local for Streamlit.
EOF
}

# --- Dispatch ----------------------------------------------------------------
case "${1:-help}" in
    install)         cmd_install ;;
    install-dev)     cmd_install_dev ;;
    run)             cmd_run "$@" ;;
    docker)          cmd_docker ;;
    test)            cmd_test ;;
    lint)            cmd_lint ;;
    benchmark)       cmd_benchmark ;;
    benchmark-llm)   cmd_benchmark_llm ;;
    docs)            cmd_docs ;;
    clean)           cmd_clean ;;
    help|--help|-h)  cmd_help ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        cmd_help
        exit 1
        ;;
esac
