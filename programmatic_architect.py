"""
programmatic_architect.py — Arquitecto Social de MASSIVE (Actualizado)
Traduce intenciones del usuario en configuraciones matemáticas para el EnergyEngine.
FLUJO: Arquetipo → Caché (RAM+SQLite) → LLM One-Shot → Fallback
"""
import json
import os
import time
import requests
from typing import Optional
from cache_manager import LandscapeCache
from energy_schemas import EnergyConfig

ARCHETYPES: dict[str, dict] = {
    "polarizacion_extrema": {
        "metadata": {"nombre_ui": "Polarización Extrema", "descripcion_ui": "Dos bandos irreconciliables. El centro es tierra de nadie.", "icono": "⚡"},
        "energy_params": {
            "attractors": [{"position": -0.85, "strength": 2.5, "label": "Polo Izquierdo"}, {"position": 0.85, "strength": 2.5, "label": "Polo Derecho"}],
            "repellers": [{"position": 0.0, "strength": 1.5, "label": "Centro / Moderación"}],
            "dynamics": {"temperature": 0.03, "eta": 0.01, "lambda_social": 0.4},
        },
    },
    "polarizacion_moderada": {
        "metadata": {"nombre_ui": "División Moderada", "descripcion_ui": "Dos grupos, pero con diálogo posible en el centro.", "icono": "🔀"},
        "energy_params": {
            "attractors": [{"position": -0.5, "strength": 1.5, "label": "Grupo A"}, {"position": 0.5, "strength": 1.5, "label": "Grupo B"}],
            "repellers": [],
            "dynamics": {"temperature": 0.04, "eta": 0.01, "lambda_social": 0.5},
        },
    },
    "consenso_moderado": {
        "metadata": {"nombre_ui": "Búsqueda de Consenso", "descripcion_ui": "La sociedad tiende a acuerdos. El centro atrae a todos.", "icono": "🤝"},
        "energy_params": {
            "attractors": [{"position": 0.0, "strength": 2.0, "label": "Punto de Acuerdo"}],
            "repellers": [],
            "dynamics": {"temperature": 0.02, "eta": 0.01, "lambda_social": 0.6},
        },
    },
    "consenso_forzado": {
        "metadata": {"nombre_ui": "Uniformidad Forzada", "descripcion_ui": "Presión institucional fuerte hacia una sola posición.", "icono": "📢"},
        "energy_params": {
            "attractors": [{"position": 0.3, "strength": 3.5, "label": "Posición Oficial"}],
            "repellers": [{"position": -0.5, "strength": 2.0, "label": "Disidencia"}],
            "dynamics": {"temperature": 0.01, "eta": 0.02, "lambda_social": 0.2},
        },
    },
    "fragmentacion_3_grupos": {
        "metadata": {"nombre_ui": "Tres Facciones", "descripcion_ui": "La sociedad se divide en tres grupos que coexisten sin fusionarse.", "icono": "🔺"},
        "energy_params": {
            "attractors": [{"position": -0.7, "strength": 1.5, "label": "Facción A"}, {"position": 0.0, "strength": 1.2, "label": "Facción B"}, {"position": 0.7, "strength": 1.5, "label": "Facción C"}],
            "repellers": [],
            "dynamics": {"temperature": 0.04, "eta": 0.01, "lambda_social": 0.5},
        },
    },
    "fragmentacion_4_grupos": {
        "metadata": {"nombre_ui": "Cuatro Tribus", "descripcion_ui": "Cuatro comunidades con identidades distintas. Alta segmentación.", "icono": "🔷"},
        "energy_params": {
            "attractors": [{"position": -0.8, "strength": 1.2, "label": "Tribu A"}, {"position": -0.25, "strength": 1.2, "label": "Tribu B"}, {"position": 0.25, "strength": 1.2, "label": "Tribu C"}, {"position": 0.8, "strength": 1.2, "label": "Tribu D"}],
            "repellers": [],
            "dynamics": {"temperature": 0.05, "eta": 0.01, "lambda_social": 0.5},
        },
    },
    "caos_social": {
        "metadata": {"nombre_ui": "Caos Social", "descripcion_ui": "Sin estructura clara. Cada agente actúa por impulso propio.", "icono": "🌀"},
        "energy_params": {
            "attractors": [],
            "repellers": [],
            "dynamics": {"temperature": 0.15, "eta": 0.01, "lambda_social": 0.3},
        },
    },
    "radicalizacion_progresiva": {
        "metadata": {"nombre_ui": "Radicalización Progresiva", "descripcion_ui": "Los agentes empiezan al centro pero son jalados hacia los extremos.", "icono": "📉"},
        "energy_params": {
            "attractors": [{"position": -0.9, "strength": 3.0, "label": "Extremo Izq"}, {"position": 0.9, "strength": 3.0, "label": "Extremo Der"}],
            "repellers": [{"position": 0.0, "strength": 2.5, "label": "Moderación"}],
            "dynamics": {"temperature": 0.02, "eta": 0.015, "lambda_social": 0.35},
        },
    },
}

_cache = LandscapeCache()

SYSTEM_PROMPT = """Eres un Diseñador de Dinámicas Sociales para MASSIVE.
Tu única tarea es generar configuraciones matemáticas en formato JSON.
REGLAS ESTRICTAS:
Responde SOLO con JSON válido. Sin texto adicional, sin explicaciones, sin markdown.
Todos los valores de "position" deben estar en el rango [-1.0, 1.0].
Los "strength" (fuerza) deben estar entre 0.5 y 4.0.
"temperature" entre 0.01 y 0.20. "lambda_social" entre 0.1 y 0.9.
ESQUEMA OBLIGATORIO:
{
 "metadata": {"nombre_ui": "string", "descripcion_ui": "string", "icono": "string"},
 "energy_params": {
   "attractors": [{"position": float, "strength": float, "label": "string"}],
   "repellers":  [{"position": float, "strength": float, "label": "string"}],
   "dynamics": {"temperature": float, "eta": 0.01, "lambda_social": float}
 }
}"""


def call_llm(user_goal: str, llm_client=None, provider: str = None, api_key: str = None, model: str = None, use_langchain: bool = False) -> Optional[dict]:
    provider = (provider or os.getenv("LLM_PROVIDER", "groq")).lower()
    api_key  = api_key or os.getenv(f"{provider.upper()}_API_KEY") or os.getenv("OPENAI_API_KEY")
    model    = model or os.getenv("LLM_MODEL", "llama-3.1-8b-instant")

    # ── LangChain path ────────────────────────────────────────────────────────
    if use_langchain:
        try:
            from langchain_workflows import build_llm, LangChainProgrammaticArchitect, LANGCHAIN_AVAILABLE
            if LANGCHAIN_AVAILABLE:
                llm = build_llm(provider, api_key or "", model, temperature=0.2)
                if llm is not None:
                    architect = LangChainProgrammaticArchitect(llm)
                    result = architect.generate_landscape(user_goal)
                    if result is not None:
                        return result
        except Exception as lc_err:
            print(f"[Architect] LangChain error: {lc_err}. Falling back to HTTP.")

    # ── Standard HTTP path ────────────────────────────────────────────────────
    base_urls = {
        "groq": "https://api.groq.com/openai/v1",
        "openai": "https://api.openai.com/v1",
        "openrouter": "https://openrouter.ai/api/v1",
        "ollama": os.getenv("OLLAMA_HOST", "http://localhost:11434")
    }
    base_url = base_urls.get(provider, base_urls["groq"])

    if provider != "ollama" and not api_key:
        print("[Architect] ⚠️ API key missing. Falling back to archetypes.")
        return None

    prompt = f"Objetivo del usuario: {user_goal}"
    messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]

    for attempt in range(2):
        try:
            if provider == "ollama":
                resp = requests.post(f"{base_url}/api/generate", json={"model": model, "prompt": prompt, "system": SYSTEM_PROMPT, "stream": False, "options": {"temperature": 0.2}}, timeout=30)
                resp.raise_for_status()
                raw_json = resp.json().get("response", "{}")
            else:
                headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
                if provider == "openrouter":
                    headers["HTTP-Referer"] = "https://github.com/Adlgr87/MASSIVE"
                    headers["X-Title"] = "MASSIVE Architect"
                resp = requests.post(f"{base_url}/chat/completions", headers=headers, json={"model": model, "messages": messages, "temperature": 0.2, "max_tokens": 500}, timeout=30)
                resp.raise_for_status()
                raw_json = resp.json()["choices"][0]["message"]["content"]

            raw_json = raw_json.strip()
            if raw_json.startswith("```json"):
                raw_json = raw_json[7:]
            if raw_json.endswith("```"):
                raw_json = raw_json[:-3]
            return json.loads(raw_json.strip())
        except requests.exceptions.Timeout:
            time.sleep(1)
        except Exception as e:
            print(f"[Architect] 🌐 LLM Error: {e}")
            break
    return None


class ProgrammaticArchitect:
    def __init__(self, range_type: str = "bipolar", llm_client=None):
        self.range_type = range_type
        self.llm_client = llm_client

    def get_landscape(self, user_goal: str) -> dict:
        goal_clean = user_goal.lower().strip()
        if goal_clean in ARCHETYPES:
            print(f"[Architect] ✅ Arquetipo encontrado: '{goal_clean}'")
            return ARCHETYPES[goal_clean]

        cached = _cache.get(goal_clean)
        if cached:
            print(f"[Architect] 💾 Desde caché: '{goal_clean}'")
            return cached

        print(f"[Architect] 🤖 Consultando LLM para: '{goal_clean}'")
        llm_result = call_llm(goal_clean, self.llm_client)

        if llm_result and self._validate_config(llm_result):
            _cache.set(goal_clean, llm_result)
            print(f"[Architect] 💾 Guardado en caché.")
            return llm_result

        print(f"[Architect] ⚠️ Fallback a 'caos_social'.")
        return ARCHETYPES["caos_social"]

    def list_available_archetypes(self) -> list[dict]:
        return [{"key": k, **v["metadata"]} for k, v in ARCHETYPES.items()]

    @staticmethod
    def _validate_config(config: dict) -> bool:
        try:
            EnergyConfig.model_validate(config)
            return True
        except Exception as e:
            print(f"[Architect] ❌ Validación fallida: {e}")
            return False
