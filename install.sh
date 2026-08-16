#!/usr/bin/env bash
# MASSIVE — one-command install & run (UI-NG single-service)
#
# Uso:
#   ./install.sh            # instala deps (python venv + npm) y construye frontend
#   ./install.sh run        # además lanza uvicorn en :8000 (API + frontend)
#   ./install.sh docker     # en lugar de local, construye/lanza la imagen Docker
#   ./install.sh clean      # elimina node_modules, dist, venv, __pycache__
#
# Requisitos: python3.11+, node 20+, npm, docker (opcional)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

# ── colores ──────────────────────────────────────────────────────────────
C_RESET=$'\033[0m' C_INFO=$'\033[36m' C_OK=$'\033[32m' C_WARN=$'\033[33m'
info(){ printf '%s[INFO]%s  %s\n' "$C_INFO" "$C_RESET" "$*"; }
ok(){   printf '%s[OK]%s  %s\n'   "$C_OK"   "$C_RESET" "$*"; }
warn(){ printf '%s[WARN]%s  %s\n' "$C_WARN" "$C_RESET" "$*"; }

# ── detección del paquete de frontend ────────────────────────────────────
# El repo principal espeja frontend/ → massive-ui-ng/frontend
# (repo standalone massive-ui-ng-package también funciona igual)
FRONTEND_DIR="$ROOT/frontend"
if [ ! -d "$FRONTEND_DIR" ]; then
  FRONTEND_DIR="$ROOT/massive-ui-ng/frontend"
fi
if [ ! -f "$FRONTEND_DIR/package.json" ]; then
  warn "No se encontró frontend/package.json — se omite build del frontend"
  FRONTEND_DIR=""
fi

# ── entorno python ───────────────────────────────────────────────────────
PY_BIN="${PYTHON:-python3}"
VENV_DIR="$ROOT/.venv"
if [ ! -x "$VENV_DIR/bin/python" ]; then
  info "Creando venv en $VENV_DIR"
  "$PY_BIN" -m venv "$VENV_DIR"
fi
# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
info "Instalando dependencias Python"
pip install --quiet --upgrade pip
pip install --quiet -r "$ROOT/requirements.txt"
pip install --quiet uvicorn[standard]
ok "Dependencias Python listas"

# ── frontend ─────────────────────────────────────────────────────────────
if [ -n "$FRONTEND_DIR" ] && [ -f "$FRONTEND_DIR/package.json" ]; then
  info "Construyendo UI-NG en $FRONTEND_DIR"
  ( cd "$FRONTEND_DIR"
    [ ! -d node_modules ] && npm ci --silent
    npm run build
  )
  ok "Frontend compilado → $FRONTEND_DIR/dist"
fi

# ── sub-comandos ─────────────────────────────────────────────────────────
CMD="${1:-install}"
case "$CMD" in
  install)
    ok "Instalación completada. Ejecuta ./install.sh run para lanzar el servidor."
    ;;
  run)
    info "Iniciando MASSIVE en http://localhost:8000"
    if [ -n "$FRONTEND_DIR" ] && [ -d "$FRONTEND_DIR/dist" ]; then
      export MASSIVE_SERVE_FRONTEND=1
    else
      export MASSIVE_SERVE_FRONTEND=0
      warn "Sin frontend/dist — modo API-only"
    fi
    exec uvicorn backend.app.main:app --host 0.0.0.0 --port 8000
    ;;
  docker)
    info "Construyendo imagen Docker"
    docker build -t massive-ui-ng "$ROOT"
    info "Ejecutando contenedor (http://localhost:8000 )"
    docker run --rm -p 8000:8000 \
      -v "$ROOT/.env.local:/app/.env.local:ro" \
      -v "$ROOT/.env:/app/.env:ro" \
      -e MASSIVE_SERVE_FRONTEND=1 \
      massive-ui-ng
    ;;
  clean)
    info "Limpiando artefactos"
    rm -rf "$VENV_DIR" "$FRONTEND_DIR/node_modules" "$FRONTEND_DIR/dist" \
      "$ROOT"/.pytest_cache "$ROOT"/__pycache__
    ok "Limpieza completada"
    ;;
  *)
    echo "Uso: $0 [install|run|docker|clean]" >&2
    exit 1
    ;;
esac
