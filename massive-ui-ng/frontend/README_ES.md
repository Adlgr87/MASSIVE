# MASSIVE UI-NG — Frontend (React + Vite + TypeScript)

Interfaz de nueva generación para MASSIVE: el LLM actúa como **traductor**
entre el usuario y las capas científicas del simulador (ver
`docs/NEXT_GEN_UI_WORKFLOW_ES.md`).

## Stack

- **React 18 + TypeScript + Vite 6** (dev server con proxy `/api` → backend)
- **Recharts** para las gráficas de trayectoria
- Sin dependencias externas de fuentes/estilos (system fonts, CSS propio)
- Tipos espejo del contrato Pydantic en `backend/app/models/dto_ui.py`

## Desarrollo

```bash
# 1) Backend (desde la raíz del repo)
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

# 2) Frontend
cd frontend
npm install
npm run dev        # → http://localhost:5173

# Build de producción
npm run build      # genera dist/ (servible por cualquier servidor estático)
```

## Estructura

```
src/
├─ App.tsx                 # orquestador (estado global, flujo conversacional)
├─ api.ts                  # cliente HTTP tipado (misma-origen, proxy /api)
├─ stream.ts               # cliente SSE sobre fetch (POST con stream)
├─ live.ts                 # cliente WebSocket para /ws/live
├─ types.ts                # contrato TS espejo de backend/app/models/dto_ui.py
├─ i18n.ts                 # diccionario ES/EN de la UI
├─ theme.css               # sistema de diseño (paleta MASSIVE, modo oscuro)
└─ components/
   ├─ StatusBar.tsx        # píldoras de estado (LLM/CfC/Rust/versión)
   ├─ ChatPanel.tsx        # conversación con el traductor (streaming SSE)
   ├─ DraftEditor.tsx      # supuestos (chips con confianza) + borrador editable
   ├─ GuidedForm.tsx       # formulario guiado (sin lenguaje natural)
   ├─ ResultsPanel.tsx     # highlights, gráficas, línea de regímenes, narrativa
   ├─ LiveControls.tsx     # panel del modo en vivo (motor, paisaje, arranque)
   └─ LiveView.tsx         # red de agentes (canvas) / métricas en streaming
```

## Configuración del LLM (opcional)

Sin API key la app completa funciona en **modo heurístico**. Para activar el
traductor LLM real, exporta las variables en el proceso del backend:

```bash
export PROVIDER=groq                  # groq | openai | openrouter | ollama
export GROQ_API_KEY=gsk_...
# o bien: PROVIDER=ollama OLLAMA_HOST=http://localhost:11434 OLLAMA_MODEL=llama3.2
```

## Nota de compatibilidad

`src/MASSIVE_UIL_demo.jsx` (mockup estático original) se conserva como
referencia de lenguaje visual; no es parte de la app.
