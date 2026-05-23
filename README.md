# MASSIVE — Multi-Agent Social Simulation & Intervention Engine

<div align="center">

![Python](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python)
![Streamlit](https://img.shields.io/badge/Streamlit-1.35+-red?style=for-the-badge&logo=streamlit)
![PyTorch](https://img.shields.io/badge/PyTorch-2.2+-orange?style=for-the-badge&logo=pytorch)
![License](https://img.shields.io/badge/License-GPL--3.0-green?style=for-the-badge)
![Tests](https://img.shields.io/badge/Tests-19%20suites-brightgreen?style=for-the-badge)
![Empirical](https://img.shields.io/badge/Base%20Emp%C3%ADrica-43%20par%C3%A1metros-purple?style=for-the-badge)

**El primer motor de simulación social que combina física estadística, redes neuronales de tiempo continuo y agentes LLM para modelar, predecir e intervenir en dinámicas humanas a escala.**

[🚀 Demo](#instalación) · [📖 Documentación](docs/) · [🧪 Tests](tests/) · [📊 Datos Empíricos](#base-empírica)

</div>

---

## ¿Qué es MASSIVE?

MASSIVE es una plataforma de **simulación social computacional** que permite modelar cómo evolucionan las opiniones, comportamientos y tensiones dentro de redes humanas — desde grupos pequeños de 3 personas hasta redes masivas de millones de agentes.

A diferencia de los simuladores tradicionales que operan con reglas fijas, MASSIVE integra tres capas de inteligencia que trabajan juntas:

1. **Física del comportamiento social** — Ecuaciones de Langevin multicapa que modelan la dinámica real de opiniones como un sistema físico con atractores, ruido y acoplamiento entre capas.
2. **Redes neuronales CfC** — Arquitecturas de tiempo continuo (Closed-form Continuous-time) entrenadas sobre datos históricos de simulación para proponer estrategias de intervención sin necesidad de llamar a una API LLM.
3. **Arquitecto Social con LLM** — Un agente de IA que realiza ingeniería inversa: dado un estado objetivo (ej. "reducir la polarización"), busca iterativamente la secuencia de intervenciones que lleva la red a ese estado.

---

## Por qué MASSIVE es disruptivo

### El problema que resuelve

La mayoría de herramientas de análisis social responden preguntas del pasado. MASSIVE responde preguntas del futuro:

- ¿Qué campaña comunicacional tiene más probabilidad de despolarizar esta comunidad?
- ¿Qué líder informal debo involucrar primero para acelerar el cambio organizacional?
- ¿Cuándo aparecerán los primeros signos de conflicto laboral en este equipo?
- ¿Cómo reaccionará esta red ante un shock externo (crisis, escándalo, noticia viral)?

### Lo que ninguna otra herramienta hace

| Capacidad | MASSIVE | Simuladores clásicos | Encuestas | Análisis de redes |
|-----------|:-------:|:--------------------:|:---------:|:-----------------:|
| Simulación de millones de agentes | ✅ | ❌ | ❌ | ❌ |
| Base empírica calibrada (~90% cobertura) | ✅ | ❌ | Parcial | ❌ |
| Ingeniería inversa de intervenciones | ✅ | ❌ | ❌ | ❌ |
| Redes neuronales de tiempo continuo | ✅ | ❌ | ❌ | ❌ |
| Detección temprana de conflictos | ✅ | ❌ | ❌ | Parcial |
| Modo corporativo + macro simultáneos | ✅ | ❌ | ❌ | ❌ |
| GPU offloading automático | ✅ | Rara vez | ❌ | ❌ |

---

## Arquitectura del Sistema

```
┌─────────────────────────────────────────────────────────────────┐
│                        app.py  (Streamlit UI)                    │
│   Tab1: Simulación  │  Tab2: Multicapa  │  Tab3: Arquitecto      │
│   Tab4: Energía     │  Tab5: Micro      │  Tab6: Micro-Familias  │
└──────────────────────────────┬──────────────────────────────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        ▼                      ▼                      ▼
┌──────────────┐    ┌─────────────────┐    ┌──────────────────┐
│  simulator.py │    │multilayer_engine│    │  micro_massive/  │
│  (13 reglas) │    │ (Langevin ODE)  │    │  (3-15 agentes)  │
└──────┬───────┘    └────────┬────────┘    └────────┬─────────┘
       │                     │                      │
       └─────────────────────┼──────────────────────┘
                             ▼
                   ┌──────────────────┐
                   │   massive_core/  │  ← Adapter layer estable
                   └────────┬─────────┘
                            │
              ┌─────────────┼─────────────┐
              ▼             ▼             ▼
     ┌──────────────┐ ┌──────────┐ ┌──────────────┐
     │  cfc_router  │ │ forecast │ │    ingest/   │
     │  (CfC NN)   │ │ (temporal│ │  (fuentes    │
     └──────┬───────┘ │  predict)│ │   de datos)  │
            │         └──────────┘ └──────────────┘
            ▼
   ┌─────────────────────┐
   │  social_architect   │  ← Agente LLM de ingeniería inversa
   └─────────────────────┘
```

---

## Componentes Principales

### 🧠 El Simulador de Opiniones (`simulator.py`)

El núcleo de MASSIVE. Implementa **13 reglas de dinámica de opinión** fundamentadas en investigación académica:

| Regla | Modelo matemático | Fenómeno social |
|-------|-------------------|-----------------|
| `lineal` | Promedio ponderado | Influencia directa |
| `umbral` | Función escalón | Adopción por masa crítica |
| `hk` | Hegselmann-Krause | Polarización por similitud |
| `memoria` | Media ponderada histórica | Inercia de creencias |
| `backlash` | Rebote por contrariedad | Efecto Backfire |
| `polarizacion` | Pozo doble (double-well) | Radicalización |
| `contagio_competitivo` | SIR modificado | Narrativas en competencia |
| `umbral_heterogeneo` | Thresholds variables | Heterogeneidad social |
| `homofilia` | Similitud de atracción | Cámaras de eco |
| + 4 más | ... | ... |

Soporta hasta **50,000 agentes** en la versión estándar y **millones** con `MassiveSimEngine`.

---

### ⚡ Motor de Escala Masiva (`massive_engine.py`)

Cuatro estrategias de eficiencia que trabajan juntas para simular **millones de agentes** en hardware doméstico:

#### Estrategia 1: LOD Sociológico (Super-Agentes)
N agentes reales → M clústeres representativos (M << N).
Reduce la complejidad de O(N²) a O(M²).
**Ejemplo:** 100,000 agentes → 316 super-agentes → **100,000× menos operaciones matriciales**

#### Estrategia 2: Cuantización de Estado (uint8)
Almacena el estado como enteros 0-255 en lugar de float64.
**Ahorro: ~87.5% de RAM** con resolución de ≈0.008 por parámetro.

#### Estrategia 3: Simulación por Eventos (Event-Driven)
Solo los super-agentes que cambian significativamente se actualizan.
Los agentes en "consenso estable" duermen hasta que un vecino cambia.
**Ahorro de CPU proporcional a la fracción convergida.**

#### Estrategia 4: GPU Offloading
Detección automática de CuPy → PyTorch+CUDA → NumPy (fallback).
**Sin dependencias obligatorias:** si no hay GPU, todo funciona en CPU.

```python
from massive_engine import MassiveSimEngine

engine = MassiveSimEngine(N=500_000, quantize=True, event_driven=True)
result = engine.run(steps=300)
print(f"Ahorro RAM: {result['memory_savings_pct']:.1f}%")  # ≈ 99.8%
```

---

### 🌐 Motor Multicapa Sociodemográfico (`multilayer_engine.py`)

Cada agente no es un punto — es un **vector de 5 dimensiones** que evoluciona según la dinámica de Langevin multicapa:

```
dx_i/dt = −∇U(x_i) + Σ_ℓ w_ℓ · (A_ℓ · G(x))_i + θ(a_i) · η_i
```

**Las 5 dimensiones del estado por agente:**
- `opinion` — posición de opinión principal `[-1, 1]`
- `cooperation` — tendencia a cooperar `[0, 1]`
- `hierarchy` — reconocimiento de autoridad `[0, 1]`
- `income` — nivel de ingreso normalizado `[0, 1]`
- `info_access` — acceso a información `[0, 1]`

**Las 3 capas de red:**
- **Social** — Red Watts-Strogatz (mundo pequeño): contactos cercanos cotidianos
- **Digital** — Red Barabási-Albert (libre de escala): redes sociales y viralizaciones
- **Económica** — Red jerárquica: relaciones laborales y de poder

El término θ(a_i) modula el ruido de cada agente según sus atributos sociodemográficos (religión, educación, edad, género), calibrados con literatura académica.

---

### 🔬 Motor Micro — Familias de Futuros (`micro_massive/`)

Para grupos pequeños de **3 a 15 personas** (equipos, células, juntas directivas), `micro_massive` implementa dos modos complementarios:

#### Modo Directo (Forward Dynamics)
Simula la evolución real del grupo paso a paso:
- **Personalidades** basadas en el Efecto Forer (rasgos psicológicos calibrados)
- **Matriz de influencia** entre miembros
- **Teoría de juegos evolutiva** para decisiones colectivas

#### Modo Inverso — Familias de Futuros (Inverse Ensemble Search)
Dado un grupo real, identifica los **clusters de trayectorias posibles** (familias de futuros):
- ¿Cuáles son los escenarios más probables para este equipo en 90 días?
- ¿Cuáles son los parámetros de bifurcación críticos?
- ¿Qué intervención pequeña redirige la trayectoria más desfavorable?

```python
from micro_massive import analyze_group, MicroSocialArchitect

group = analyze_group(members_data)
architect = MicroSocialArchitect()
futures = architect.compute_families(group, horizon=90)
```

---

### 🤖 Redes Neuronales CfC (`cfc_engine.py` + `cfc_router.py`)

MASSIVE integra una arquitectura neuronal de **tiempo continuo** (Closed-form Continuous-time networks) — un tipo de red neuronal donde el estado evoluciona según una ODE diferencial:

```
dx/dt = −x/τ + B(u) + C · tanh(Wx·x + Wu·u)
```

Donde **τ es aprendido dinámicamente** a partir del estado y la entrada — no es un hiperparámetro fijo. Esto le permite a la red adaptarse a la velocidad intrínseca de cada situación social.

**Los 4 modelos CfC:**

| Modelo | Función | Reemplaza |
|--------|---------|-----------|
| `CfCCell` | Celda ODE base | — |
| `CfCRegimeSelector` | Selecciona el régimen óptimo (1 de 13) | Llamada LLM en hot-path |
| `CfCTauMatrix` | Genera la matriz θ sociodemográfica | Cálculo manual de theta |
| `CfCArchitectPolicy` | Propone estrategias de intervención | Intento 0 del LLM |

#### El Intento 0 Neuronal
Antes de hacer cualquier llamada LLM (costosa y lenta), el `CfCArchitectPolicy` propone una estrategia completa basada en el estado inicial y el objetivo codificado. Si el score ≥ 90/100, **el LLM nunca se invoca**.

---

### 🏛️ El Arquitecto Social (`social_architect.py`)

El módulo más único de MASSIVE. Implementa **ingeniería inversa social**: dado un estado objetivo, encuentra la secuencia de intervenciones matemáticas que lleva la red a ese estado.

**Flujo de búsqueda (3 capas):**

```
Estado Inicial + Objetivo
        │
        ▼
[Intento 0] CfCArchitectPolicy ──→ Score ≥ 90? ──→ Retorna (sin LLM)
        │ No
        ▼
[LangChain path] LangChainSocialArchitect (si disponible)
        │ Fallo
        ▼
[HTTP directo] OpenAI/Groq/OpenRouter
        │
        ▼
Evaluación → Feedback → Refinamiento (hasta max_intentos)
        │
        ▼
Pronóstico Temporal (forecast/) + Narrativa final
```

**Dos modos de operación:**

- **Modo Macro** — Política, redes sociales masivas, polarización pública. Vocabulario: campañas mediáticas, hashtags virales, cámaras de eco, movimientos sociales.
- **Modo Corporativo** — RRHH, cambio organizacional, liderazgo. Vocabulario: planes 30-60-90, OKRs, líderes informales, resistencia al cambio.

En modo corporativo, el Arquitecto identifica automáticamente los **ejecutores topológicos**: los nodos con mayor betweenness centrality (líderes informales) a impactar primero, antes que los directivos formales.

---

### 📡 Detección Temprana y Pronóstico (`forecast/`)

El módulo de pronóstico temporal calcula la probabilidad y el tiempo estimado de un evento crítico (conflicto laboral, crisis política, ruptura organizacional) basándose en el historial de simulación.

**Métricas generadas:**
- `p_event` — Probabilidad del evento en el horizonte temporal
- `days_to_event` — Días estimados hasta el evento crítico
- `confidence` — Intervalo de confianza del pronóstico
- `p_event_no_intervention` — Probabilidad sin intervención (baseline)
- `feasibility_vs_deadline` — ¿Es factible intervenir antes del evento?

Los **signos tempranos** (early signs) son detectados cuando la divergencia entre la trayectoria actual y los atractores del sistema supera umbrales calibrados empíricamente. El sistema alerta antes de que la dinámica se vuelva irreversible.

---

### 📊 Base Empírica de Calibración (`empirical_config.py`)

Todos los parámetros del simulador están **anclados en investigación académica real**, no en suposiciones arbitrarias.

**43 parámetros cubiertos** en 7 categorías, con cobertura del **88.4%**:

| Categoría | Ejemplos de parámetros |
|-----------|------------------------|
| Dinámica de redes | Deriva algorítmica (Bonchi 2024), Homofilia (McPherson 2001), Amplificación viral (Brady 2017) |
| Psicología individual | Sesgo de confirmación (Nickerson 1998), Efecto Backfire (Nyhan 2010), Disonancia cognitiva (Festinger 1957) |
| Psicología de masas | Contagio emocional (Kramer 2014), Cascadas informacionales (Bikhchandani 1992), Espiral del silencio (Noelle-Neumann 1974) |
| Variables culturales | Individualismo/Colectivismo, Distancia al poder, Evitación de incertidumbre (Hofstede 2010) |
| Temporal | Media-vida digital (Wu & Huberman 2007, ≈69 min), Ciclo de atención (Lorenz-Spreen 2019) |
| Teoría de juegos | Equilibrio de Nash social (Nash 1950), Dilema del prisionero (Axelrod 1984), Caza del ciervo (Skyrms 2004) |
| Estatus social | Modulación por clase (Gidron & Hall 2017), Brecha generacional (Inglehart 2018) |

Los parámetros soportan **varianza cultural**: los mismos modelos producen comportamientos distintos según el perfil (`latin`, `anglosaxon`, `east_asian`, `nordic`, etc.).

```python
from empirical_config import get_runtime_params

params = get_runtime_params(cultural_profile="latin")
# → temperature: 0.467, social_influence_lambda: 0.513, ...
```

---

### 🔌 Ingesta de Datos Reales (`ingest/`)

MASSIVE puede alimentarse con datos reales de múltiples fuentes:

- **Twitter/X** — Análisis de sentimiento y posiciones de opinión via Tweepy
- **Reddit** — Extracción de debates y posiciones via PRAW
- **Encuestas** — Normalización de datos de soporte/oposición con varianza Bernoulli
- **Fuentes personalizadas** — API extensible para cualquier fuente

```python
from ingest import normalize_support_oppose, get_source_config

config = get_source_config("twitter")
data = normalize_support_oppose(raw_survey_data)
```

---

## Instalación

### Requisitos
- Python 3.11+
- 4GB RAM mínimo (8GB recomendado para simulaciones grandes)
- GPU opcional (CuPy o PyTorch+CUDA para aceleración)

```bash
# Clonar el repositorio
git clone https://github.com/Adlgr87/MASSIVE.git
cd MASSIVE

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Edita .env con tu API key (OpenAI, Groq, o OpenRouter)

# Ejecutar la aplicación
streamlit run app.py
```

### Con Docker
```bash
docker build -t massive .
docker run -p 8501:8501 --env-file .env massive
```

---

## Uso Rápido

### Simulación básica
```python
from simulator import simular, DEFAULT_CONFIG

config = {**DEFAULT_CONFIG, "n_agentes": 500, "pasos": 100, "regla": "hk"}
historial = simular(config)
```

### Ingeniería inversa con el Arquitecto Social
```python
from social_architect import buscar_estrategia_inversa
from simulator import DEFAULT_CONFIG

estado_inicial = {"opinion_media": 0.1, "polarizacion": 0.7}
estrategia, narrativa, intentos, historial = buscar_estrategia_inversa(
    estado_inicial=estado_inicial,
    objetivo_usuario="Despolarizar la red y generar consenso en 60 pasos",
    max_intentos=3,
    config=DEFAULT_CONFIG,
    modo_simulacion="macro",
)
print(f"Estrategia encontrada en {intentos} intentos")
print(narrativa)
```

### Simulación masiva (millones de agentes)
```python
from massive_engine import MassiveSimEngine

engine = MassiveSimEngine(N=1_000_000, quantize=True, event_driven=True, use_gpu=True)
result = engine.run(steps=500)
print(f"RAM usada: {result['final_MB']:.1f} MB vs {result['float64_MB']:.0f} MB sin optimización")
```

### Pronóstico temporal
```python
from forecast import TemporalConfig, forecast

config = TemporalConfig(event_type="labor_conflict", time_horizon_days=90)
result = forecast(simulation_state, config, mode="analytical")
print(f"P(conflicto en 90 días): {result.p_event:.1%}")
print(f"Días estimados: {result.days_to_event}")
```

---

## Estructura del Proyecto

```
MASSIVE/
├── app.py                    # Interfaz Streamlit principal
├── simulator.py              # 13 reglas de dinámica de opinión
├── multilayer_engine.py      # Motor multicapa sociodemográfico (Langevin ODE)
├── massive_engine.py         # Motor masivo (LOD + uint8 + Event-Driven + GPU)
├── social_architect.py       # Arquitecto Social (ingeniería inversa + LLM)
├── cfc_engine.py             # Arquitecturas neuronales CfC (tiempo continuo)
├── cfc_router.py             # Router unificado de modelos CfC
├── cfc_trainer.py            # Entrenamiento de los modelos CfC
├── empirical_config.py       # Base empírica: 43 parámetros calibrados
├── empirical_calibration.py  # Motor de calibración empírica
├── extended_models.py        # Modelos extendidos de comportamiento
├── programmatic_architect.py # Arquitecto sin dependencia LLM
├── langchain_workflows.py    # Flujos LangChain opcionales
├── energy_engine.py          # Motor de energía social
├── intervention_optimizer.py # Optimizador clásico de intervenciones
├── schemas.py                # Modelos Pydantic
├── i18n.py                   # Internacionalización
├── visualizations.py         # Visualizaciones Plotly
│
├── massive_core/             # Adapter layer estable sobre simulator
├── micro_massive/            # Simulación de grupos pequeños (3-15 agentes)
│   ├── micro_engine.py       # Motor de familias de futuros
│   ├── micro_schemas.py      # Schemas Pydantic micro
│   ├── micro_ui.py           # UI Streamlit micro
│   ├── core/                 # agent, game, influence, orchestrator
│   └── utils/                # forer, metrics
├── forecast/                 # Pronóstico temporal y detección temprana
│   ├── engine.py, scenarios.py, intervention_map.py, temporal_config.py
├── ingest/                   # Ingesta de datos reales
│   ├── sources.py, normalize.py, clean.py, metrics.py
│
├── models/                   # Modelos CfC pre-entrenados (.pt)
├── configs/                  # Configuraciones YAML
├── tests/                    # 19 suites de pruebas
├── docs/                     # Documentación MkDocs
└── benchmarks/               # Benchmarks de rendimiento
```

---

## Tests

```bash
pytest tests/
```

**19 suites de tests** cubriendo: simulador, motor multicapa, motor masivo, CfC, arquitecto social, micro, forecast, energía, calibración empírica, modelos DTO, LLM, visualizaciones y más.

---

## Casos de Uso

### Análisis Político y Social
- Modelar la evolución de la opinión pública ante una campaña electoral
- Predecir el efecto de una noticia viral en la polarización social
- Diseñar estrategias de comunicación para despolarizar comunidades

### Gestión Organizacional
- Identificar líderes informales clave antes de una reestructuración
- Predecir resistencia al cambio y diseñar planes de mitigación
- Simular el efecto de intervenciones de RRHH (talleres, 1:1, comunicados)

### Investigación Académica
- Reproducir fenómenos documentados (espiral del silencio, cascadas informacionales)
- Validar hipótesis de dinámica social con datos reales calibrados
- Explorar bifurcaciones y puntos de no-retorno en sistemas sociales

### Inteligencia de Riesgos
- Detectar signos tempranos de conflicto laboral, polarización o crisis institucional
- Estimar ventanas temporales para intervención efectiva
- Comparar escenarios con y sin intervención

---

## Configuración LLM

```env
OPENAI_API_KEY=sk-...        # OpenAI (GPT-4o, GPT-4o-mini)
GROQ_API_KEY=gsk_...         # Groq — recomendado por velocidad
OPENROUTER_API_KEY=sk-or-... # OpenRouter (acceso a múltiples modelos)
OPENAI_MODEL=gpt-4o-mini     # Modelo por defecto
```

Sin API key configurada, el sistema opera en modo heurístico usando `CfCArchitectPolicy` y `ProgrammaticArchitect`.

---

## Contribuir

Consulta [CONTRIBUTING.md](CONTRIBUTING.md) y [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

**Convenciones clave (ver [CLAUDE.md](CLAUDE.md)):**
- Kernels Numba JIT (`@njit`) solo aceptan arrays NumPy planos
- Valores de opinión siempre en rango declarado; usar `np.clip` después de cada update
- La API principal (`simular`, `simular_multiples`) debe permanecer backward-compatible
- Build: `pip install -r requirements.txt` · Run: `streamlit run app.py` · Test: `pytest tests/`

---

## Roadmap

- [ ] Panel de monitoreo en tiempo real con datos de redes sociales
- [ ] API REST para integración con sistemas externos
- [ ] Módulo de calibración automática por país/región con datos de World Values Survey
- [ ] Interfaz de administración de modelos CfC (entrenamiento desde UI)

---

## Licencia

GNU General Public License v3.0 — ver [LICENSE](LICENSE) para detalles.

---

## Citación

```bibtex
@software{massive2025,
  title  = {MASSIVE: Multi-Agent Social Simulation & Intervention Engine},
  author = {Adlgr87 and contributors},
  year   = {2025},
  url    = {https://github.com/Adlgr87/MASSIVE},
  note   = {GPL-3.0 License}
}
```

---

<div align="center">

**MASSIVE** — Donde la física social, la inteligencia artificial y la ciencia del comportamiento convergen para entender y transformar sistemas humanos complejos.

[⭐ Star en GitHub](https://github.com/Adlgr87/MASSIVE) · [🐛 Reportar Bug](https://github.com/Adlgr87/MASSIVE/issues) · [💡 Sugerir Feature](https://github.com/Adlgr87/MASSIVE/issues)

</div>
