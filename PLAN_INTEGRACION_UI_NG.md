# Plan de Integración: massive-ui-ng-package dentro de MASSIVE

## Contexto

- **Repo MASSIVE**: `https://github.com/Adlgr87/MASSIVE.git` (token auth)
- **Remote UI-NG**: `massive-ui-ng` (actualmente retorna 404 — se usarán comandos de fallback)
- **Estructura actual MASSIVE**: `backend/app/models/` con 4 DTOs, `app.py` (Streamlit), `.streamlit/`, `requirements.txt` con dependencias Streamlit

---

## FASE 1: Integrar `massive-ui-ng-package` vía `git subtree`

### 1.1 Agregar remote de UI-NG

```bash
# Desde /home/adlg/MASSIVE
git remote add ui-ng https://github.com/Adlgr87/massive-ui-ng.git
```

> **Nota**: Si el remote retorna 404, usar el comando alternativo:
```bash
# Si el repo público está disponible sin auth:
git remote add ui-ng https://github.com/Adlgr87/massive-ui-ng.git
# Verificar conexión:
git ls-remote ui-ng
```

### 1.2 Fetch del remote de UI-NG

```bash
# Fetch de todas las ramas y tags
git fetch ui-ng --tags --verbose

# Si falla con 404, intentar con auth token (si aplica):
# git fetch ui-ng --tags --verbose https://TOKEN@github.com/Adlgr87/massive-ui-ng.git
```

### 1.3 Identificar branch/SHA a integrar

```bash
# Listar ramas remotas disponibles
git branch -r --list "ui-ng/*"

# Supongamos que existe ui-ng/main:
git log ui-ng/main --oneline -3
```

### 1.4 Subtree add — integrar como subdirectorio `massive-ui-ng/`

```bash
# Opción A: Si UI-NG tiene una carpeta raíz ya definida (ej: package/ en su repo)
# Ajustar --prefix al root real del paquete:
git subtree add --prefix=massive-ui-ng/ ui-ng main --squash --message="feat: integrate massive-ui-ng package via subtree [SKIP CI]"

# Opción B: Si UI-NG contiene el paquete en una subcarpeta (ej: package/)
# Se necesita extraer solo esa rama/subdirectorio antes del subtree add:
# Paso 1: Crear rama local filtrada
git checkout -b ui-ng-extract ui-ng/main -- .
# Paso 2: Usar git filter-branch o git filter-repo para aislar package/
# Paso 3: Subtree add con el SHA de la rama filtrada
```

### 1.5 Commit de referencia

El `git subtree add` anterior crea automáticamente un commit. Verificar:

```bash
git log --oneline -3
git status
```

### 1.6 Verificar estructura integrada

```bash
ls -la massive-ui-ng/
# Esperado: debe contener archivos de UI-NG, incluyendo dto_ui.py y frontend/
find massive-ui-ng/ -name "dto_ui.py" -type f
find massive-ui-ng/ -name "package.json" -type f
```

---

## FASE 2: Resolver colisiones entre `backend/app/models/__init__.py`

### 2.1 Analizar contenido de UI-NG

```bash
# Inspeccionar archivos clave de UI-NG
cat massive-ui-ng/backend/app/models/__init__.py
cat massive-ui-ng/backend/app/models/dto_ui.py 2>/dev/null || echo "dto_ui.py no encontrado"
find massive-ui-ng/ -name "*.py" -path "*/models/*" -type f
```

### 2.2 Estrategia de fusión

**Escenario esperado**: UI-NG extiende los 4 DTOs existentes con tipos `dto_ui.py`.

#### 2.2.1 Importar DTOs de UI-NG en MASSIVE

Editar `backend/app/models/__init__.py` para agregar:

```python
# --- UI-NG DTOs (extienden los DTOs base de MASSIVE) ---
try:
    from backend.app.models.dto_ui import (
        UIDashboardConfig,
        UIExportRequest,
        UITheme,
        UIWebSocketEvent,
        # ... otros nombres según dto_ui.py de UI-NG
    )
    _UI_DTO_AVAILABLE = True
except ImportError:
    _UI_DTO_AVAILABLE = False
```

#### 2.2.2 Resolver conflictos de nombres

Si UI-NG redefine alguno de los 4 DTOs existentes (architect, forecast, simulation, snapshot):

```bash
# Generar diff para identificar colisiones
diff -ru backend/app/models/__init__.py massive-ui-ng/backend/app/models/__init__.py
diff -ru backend/app/models/dto_simulation.py massive-ui-ng/backend/app/models/dto_simulation.py 2>/dev/null
```

**Decisión**: Si hay colisión en `__init__.py`:
- **Prioridad 1**: Mantener los DTOs de MASSIVE como base (architect, forecast, simulation, snapshot).
- **Prioridad 2**: Importar tipos nuevos de `dto_ui.py` con namespaces o aliases.
- **Ejemplo de fusión**:

```python
# backend/app/models/__init__.py (fusión)
from backend.app.models.dto_architect import (...)
from backend.app.models.dto_forecast import (...)
from backend.app.models.dto_simulation import (...)
from backend.app.models.dto_snapshot import (...)

# UI-NG extensions — prefixed to avoid collision
try:
    from backend.app.models.dto_ui import (
        UIDashboardConfig as UIDashboardConfig,
        UIExportRequest as UIExportRequest,
        UITheme as UITheme,
        UIWebSocketEvent as UIWebSocketEvent,
    )
except ImportError:
    pass  # dto_ui no integrado todavía
```

#### 2.2.3 Unificar archivos si es necesario

Si UI-NG tiene modificaciones a `dto_simulation.py` por ejemplo:

```bash
# Comparar contenido
diff backend/app/models/dto_simulation.py massive-ui-ng/backend/app/models/dto_simulation.py

# SI hay diferencias: aplicar UI-NG como supersención si extiende, o mantener MASSIVE base
# Si MASSIVE base ya incluye los campos de UI-NG, no cambiar nada
```

### 2.3 Commit de fusión de modelos

```bash
git add backend/app/models/__init__.py
git commit -m "fix: merge UI-NG DTOs into backend/app/models/__init__.py

- Preserve 4 base DTOs from MASSIVE (architect, forecast, simulation, snapshot)
- Import UI-NG extensions from dto_ui.py with explicit namespace
- Guard imports with try/except for backward compatibility"
```

---

## FASE 3: Reemplazar Streamlit — preservar API y simulator

### 3.1 Eliminar `app.py` (Streamlit)

```bash
# Backup temporal (opcional)
git mv app.py app.py.streamlit-backup

# O eliminar directamente:
git rm app.py

# Si se quiere preservar históricamente:
# git rm --cached app.py && echo "app.py" >> .gitignore
```

### 3.2 Eliminar `.streamlit/`

```bash
git rm -r .streamlit/
```

### 3.3 Limpiar dependencias de Streamlit

#### requirements.txt:

```bash
# Editar requirements.txt:
# Eliminar o comentar:
sed -i '/^streamlit>/d' requirements.txt
sed -i '/^plotly>/d' requirements.txt  # plotly es opcional, revisar uso

# Verificar:
cat requirements.txt
```

#### pyproject.toml:

```python
# Editar [project.optional-dependencies]:
# De: ui = ["streamlit>=1.35", "plotly>=5.18"]
# A: ui = ["plotly>=5.18"]  # opcional, si se usa en frontend

# Actualizar [project].dependencies eliminar streamlit si está listado allí
```

### 3.4 Preservar funcionalidad de `api.py` y `simulator.py`

Verificar que los endpoints existentes siguen funcionando:

```bash
# api.py ya expone:
# POST /api/extract
# POST /api/wizard
# POST /api/simulate-uil
# POST /api/v1/architect
# POST /api/v1/forecast
# POST /api/v1/energy
# GET /health, /ready, /version, /

# simulator.py contiene:
# simular(), simular_multiples(), save_checkpoint(), load_checkpoint(), etc.
# app/__init__.py reexporta simular y utilidades de simulator.py
```

**No hay cambios necesarios en api.py ni simulator.py** — ya son endpoints FastAPI que no dependen de Streamlit.

### 3.5 Verificar re-exports de `app/`

```bash
# app/__init__.py importa de simulator.py — verificar que simulator.py
# no importe streamlit en su scope:
grep -n "import streamlit" simulator.py
# Si hay imports de streamlit en simulator.py, mover/condicionar:
# ```python
# try:
#     import streamlit as st
# except ImportError:
#     st = None
# ```
```

### 3.6 Commit de remoción Streamlit

```bash
git add backend/app/models/__init__.py  # ya modificado en fase 2
# app.py y .streamlit/ ya fueron borrados con git rm
git commit -m "refactor: remove Streamlit, rely on FastAPI endpoints

- Delete app.py (Streamlit UI replaced by frontend/)
- Delete .streamlit/ config directory
- Remove streamlit/plotly deps from requirements.txt and pyproject.toml
- Preserve /api/* and /api/v1/* endpoints (api.py, simulator.py)
- app/__init__.py still reexports simulator functions for backward compat"
```

---

## FASE 4: Integrar frontend de UI-NG (si aplica)

### 4.1 Verificar si UI-NG incluye frontend

```bash
ls -la massive-ui-ng/frontend/ 2>/dev/null
cat massive-ui-ng/frontend/package.json 2>/dev/null
```

### 4.2 Fusionar frontend (opcional)

Si UI-NG incluye un frontend:
- Decidir si se sobreescribe `frontend/` de MASSIVE o se integra como `massive-ui-ng/frontend/`
- Si UI-NG frontend consume los `/api/v1/*` endpoints, enlazarlos

### 4.3 Build del frontend

```bash
cd frontend/
npm install
npm run build
# Verificar salida en dist/
```

---

## FASE 5: Checkpoints de Validación

### Checkpoint A: Tests unitarios

```bash
# Desde /home/adlg/MASSIVE
python -m pytest tests/test_dto_models.py -v
python -m pytest tests/test_api_security.py -v
python -m pytest tests/test_forecast.py -v
```

### Checkpoint B: Import de modelos

```bash
# Verificar que imports funcionen
python -c "from backend.app.models import SimSnapshotMessage, UIDashboardConfig; print('OK')"
```

### Checkpoint C: Build frontend

```bash
cd frontend/
npm run build 2>&1 | tail -5
```

### Checkpoint D: API health

```bash
# Si uvicorn está configurado:
python -c "from backend.app.api import app; print('API import OK')"
```

### Checkpoint E: Git status limpio

```bash
git status
git diff --stat
```

---

## FASE 6: Push y Documentación

### 6.1 Push de cambios

```bash
git push origin main
```

### 6.2 Actualizar AGENTS.md (repositorio skill memory)

```bash
cat >> AGENTS.md << 'EOF'

## UI-NG Integration

- massive-ui-ng-package is integrated via git subtree under massive-ui-ng/
- UI-NG DTOs (dto_ui.py) extend base DTOs; see backend/app/models/__init__.py
- Streamlit has been removed; use frontend/ (React+Vite+TS) with /api/v1/*
- Key endpoints: /api/extract, /api/wizard, /api/v1/architect, /api/v1/forecast
EOF
```

---

## Comandos Resumen (Ejecución Secuencial)

```bash
# Fase 1: Subtree
cd /home/adlg/MASSIVE
git remote add ui-ng https://github.com/Adlgr87/massive-ui-ng.git 2>/dev/null || git remote set-url ui-ng https://github.com/Adlgr87/massive-ui-ng.git
git fetch ui-ng --tags
git subtree add --prefix=massive-ui-ng/ ui-ng main --squash --message="chore: integrate massive-ui-ng via subtree"

# Fase 2: Merge models
# (Editar backend/app/models/__init__.py según diff)
git add backend/app/models/__init__.py
git commit -m "fix: merge UI-NG DTOs"

# Fase 3: Remove Streamlit
git rm app.py
git rm -r .streamlit/
sed -i '/^streamlit>/d; /^plotly>/d' requirements.txt
# Editar pyproject.toml manualmente
git add requirements.txt pyproject.toml
git commit -m "refactor: remove Streamlit, rely on FastAPI"

# Fase 5: Validar
python -m pytest tests/test_dto_models.py -q
cd frontend && npm run build && cd ..

# Fase 6: Push
git push origin main
```

---

## Riesgos y Mitigaciones

| Riesgo | Mitigación |
|--------|-----------|
| UI-NG remote 404 | Usar token GitHub o fork local; el plan incluye fallback con `git filter-branch` |
| Colisión de nombres en DTOs | Guardar imports base de MASSIVE con prioridad; alias en dto_ui.py |
| simulator.py importa streamlit | Verificar y condicionar imports con try/except |
| Frontend duplicado | Decidir política: sobrescribir o mantener en paralelo |
| Tests fallidos por imports rotos | Ejecutar checkpoints A-E antes de push |

---

**Creado por**: OpenHands (openhands@all-hands.dev)  
**Fecha**: 2026-08-16  
**Repo context**: MASSIVE (Adlgr87/MASSIVE) + massive-ui-ng (Adlgr87/massive-ui-ng)
