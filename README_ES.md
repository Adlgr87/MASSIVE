---
title: MASSIVE
emoji: 🌊
colorFrom: blue
colorTo: indigo
sdk: streamlit
app_file: app.py
pinned: false
---

# MASSIVE
### Mathematical Architecture for Scalable Social Interaction & Virtual Engine

> *"Many behaving as One"*

<p align="center">
  <img src="https://github.com/user-attachments/assets/04c5860f-36d4-433c-a142-5761d0f16824" alt="MASSIVE Social Simulator" width="260"/>
</p>

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)
[![tests](https://github.com/Adlgr87/MASSIVE/actions/workflows/pytest.yml/badge.svg)](https://github.com/Adlgr87/MASSIVE/actions/workflows/pytest.yml)
[![docs](https://github.com/Adlgr87/MASSIVE/actions/workflows/mkdocs.yml/badge.svg)](https://github.com/Adlgr87/MASSIVE/actions/workflows/mkdocs.yml)
[![PVU Validación](https://github.com/Adlgr87/MASSIVE/actions/workflows/pvu-validation.yml/badge.svg)](https://github.com/Adlgr87/MASSIVE/actions/workflows/pvu-validation.yml)

![MASSIVE UI Demo](docs/massive_ui_mockup.png)

MASSIVE es un simulador híbrido de dinámica social que combina un núcleo matemático riguroso con el razonamiento contextual de los Modelos de Lenguaje de Gran Escala (LLMs). Modela cómo se forman y evolucionan las opiniones, los comportamientos y las estructuras sociales — desde pequeños grupos hasta poblaciones de millones.

Los simuladores tradicionales preguntan *"¿qué ocurrirá?"*. MASSIVE también responde: **"¿qué secuencia de intervenciones nos lleva adonde queremos?"** — a través del agente de ingeniería inversa Arquitecto Social.

> 📘 Documentación en inglés: [README.md](README.md)

---

## Contenido

- [Qué hace](#qué-hace)
- [Características Clave](#características-clave)
- [Arquitectura](#arquitectura)
- [Reglas de Simulación](#reglas-de-simulación)
- [Instalación](#instalación)
- [Ejecutar la App](#ejecutar-la-app)
- [API Programática](#api-programática)
- [Configuración](#configuración)
- [Rendimiento a Escala](#rendimiento-a-escala)
- [Integración con Redes Sociales](#integración-con-redes-sociales)
- [Protocolo de Validación (PVU-BS)](#protocolo-de-validación-pvu-bs)
- [Decisiones de Diseño](#decisiones-de-diseño)
- [Limitaciones](#limitaciones)
- [Estructura del Proyecto](#estructura-del-proyecto)
- [Tests](#tests)
- [Contribuir](#contribuir)
- [Licencia](#licencia)

---

## Qué hace

MASSIVE te permite:

1. **Ejecutar simulaciones hacia adelante** — elige una de 13 reglas matemáticas, configura opinión, propaganda, confianza y composición de grupos, y observa cómo evoluciona una red social paso a paso con gráficos en tiempo real y alertas de señales de advertencia temprana.
2. **Ingeniería inversa de resultados** — describe el estado social deseado en lenguaje natural; el Arquitecto Social usa un LLM en un bucle iterativo proponer-simular-puntuar-refinar para encontrar la secuencia de intervenciones que te lleva ahí.
3. **Modelar complejidad estructural** — cada agente lleva un vector de estado 5D `(opinión, cooperación, jerarquía, ingreso, acceso_info)` sobre tres capas de red superpuestas (social, digital, económica), modulado por atributos demográficos.
4. **Escalar a millones** — simulación a escala poblacional en un portátil, combinando clusterización de super-agentes, cuantización uint8, actualizaciones dirigidas por eventos y descarga opcional en GPU.
5. **Inicializar desde datos reales** — obtén sentimiento en vivo desde Twitter/X o Reddit para inicializar simulaciones a partir de distribuciones de opinión reales.

---

## Características Clave

### Núcleo de Simulación
- **13 reglas de simulación** basadas en literatura académica de dinámica de opinión (DeGroot, Friedkin-Johnsen, Hegselmann-Krause, Granovetter, Axelrod, Nash, Pearl, Kermack-McKendrick y más).
- **LLM como selector de régimen** — en lugar de codificar qué modelo corre cuándo, el LLM lee el estado actual de la red y selecciona la regla más coherente sociológicamente en cada paso.
- **Dos rangos de opinión** — probabilístico `[0, 1]` (neutro = 0.5) y bipolar `[-1, 1]` (neutro = 0.0), seleccionables por ejecución.
- **Tres mecanismos transversales** aplicados sobre cada regla: Sesgo de Confirmación, Homofilia Dinámica y Fuerza Estratégica de Teoría de Juegos.

### Arquitecto Social
- Agente LLM iterativo que **ingeniería inversa las secuencias de intervención** para alcanzar un resultado social definido por el usuario.
- Bucle de retroalimentación cerrado: el LLM propone una `StrategyMatrix` → la simulación Langevin la ejecuta → se calcula una puntuación (0–100) → el LLM refina hasta puntuación ≥ 90 o agotar intentos.
- Dos modos: **Macro** (opinión pública, elecciones, movimientos sociales) y **Corporativo** (cambio organizacional, alineación de equipos, liderazgo informal).
- Produce un cronograma estructurado con justificación sociológica + narrativa en lenguaje natural de calidad consultora.

### Motor Multicapa Sociodemográfico
- Cada agente es un **vector de estado 5D** `(opinión, cooperación, jerarquía, ingreso, acceso_info)` que evoluciona simultáneamente.
- **Tres capas de red superpuestas**: Watts-Strogatz (social), Barabási-Albert (digital), estrella jerárquica + hubs (económica).
- **Modulación demográfica (matriz θ)**: religión, educación, edad y género ajustan la sensibilidad al ruido de cada agente por dimensión conductual, produciendo heterogeneidad realista sin configuración manual por agente.
- **Potencial social multidimensional** con gradientes independientes pero acoplados: polarización de doble pozo (opinión), clustering de cooperación, bifurcación de jerarquía, centrado de ingresos y decaimiento de acceso a información.

### Motor de Paisaje Energético
- **Dinámica estocástica de Langevin** sobre un paisaje configurable de atractores y repulsores gaussianos.
- **Bucle interno compilado JIT con Numba** (`@njit`) — compilado una vez, ejecutado a velocidad nativa en todas las llamadas posteriores.
- **8 arquetipos sociales pre-construidos** (`polarizacion_extrema`, `consenso_moderado`, `radicalizacion_progresiva`, …) para configuración instantánea de escenarios.
- **Pipeline de resolución** para objetivos en texto libre: coincidencia exacta de arquetipo → caché RAM → caché SQLite (persiste entre reinicios) → LLM one-shot → fallback.

### Motor de Simulación Masiva
- **LOD Sociológico (super-agentes)**: N agentes colapsan en M clústeres; el tamaño de matriz cae de O(N²) a O(M²).
- **Cuantización de estado uint8**: reducción de RAM del 87.5% por parámetro con resolución ≈ 0.008 unidades de opinión.
- **Conjuntos activos dirigidos por eventos**: los agentes dormidos (en consenso estable) consumen cero CPU hasta que un cambio de vecino los despierta.
- **Descarga en GPU**: CuPy → PyTorch+CUDA → NumPy, seleccionado automáticamente al inicio — sin configuración.

### Análisis y Monitoreo
- **Señales de Advertencia Temprana (EWS)**: varianza en ventana deslizante, autocorrelación lag-1 y asimetría — señaliza ⚠️ proximidad a puntos de inflexión social.
- **Análisis de Datos Topológicos (TDA)**: homología persistente opcional vía embedding de Takens + filtración Vietoris-Rips (`ripser` + `persim`), detecta cambios de régimen estructural que las métricas escalares pasan por alto.
- **Métricas de grafo de red**: centralidad de grado/intermediación, densidad e identificación de clústeres vía NetworkX.

### Extensión Científica

#### Motor multicapa disperso (sparse)

Una implementación completamente dispersa del motor multicapa basada en
``scipy.sparse`` que reduce consumo de memoria y acelera la iteración en
sistemas grandes:

```python
from massive_core.numerics import SparseMultilayerEngine, LayerState
from scipy import sparse

layer = LayerState(
    node_features=np.random.randn(100, 8),
    graph_adjacency=sparse.random(100, 100, density=0.05, format="csr"),
    layer_id="social",
)
engine = SparseMultilayerEngine(layers=[layer])
result = engine.run_simulation()
```

#### Análisis de estabilidad y perturbación

``StabilityAnalyzer`` y ``PerturbationTheorySolver`` calculan la Jacobiana
en equilibrio, clasifican estabilidad local mediante análisis espectral y
proporcionan diagnósticos de sensibilidad de parámetros:

```python
from massive_core.numerics import StabilityAnalyzer
from massive_core.physics import PerturbationTheorySolver

analyzer = StabilityAnalyzer(system_fn, equilibrium)
report = analyzer.analyze()
print(report.is_stable)
```

#### Filtro de Kalman de conjunto disperso

``SparseEnsembleKalmanFilter`` ejecuta análisis EnKF sobre un subconjunto de
variables observables, ideal para sistemas sociales de alta dimensión donde
solo se mide una fracción del estado:

```python
from massive_core.data_assimilation import SparseEnsembleKalmanFilter

ekf = SparseEnsembleKalmanFilter(
    n_ensemble=50,
    n_state_dim=200,
    n_obs_dim=20,
    observable_indices=list(range(20)),
    observation_covariance=np.eye(20) * 0.1,
)
state_estimate, ensemble = ekf.assimilate_step(model_fn, observations)
```

### Integración e Infraestructura
- **Cadenas tipadas LangChain** (`strategy_chain`, `narrative_chain`, `landscape_chain`) con validación de salida JSON y fallback HTTP transparente.
- **Simulación múltiple paralela con Dask** en todos los núcleos CPU disponibles vía `dask.delayed`.
- **Optimización y compresión escalable**: búsqueda estocástica para planes de intervención + compresión SVD para matrices de estado de agentes grandes.
- **Base de calibración empírica de 43 parámetros** (v1.1.0, 88.4% de cobertura), validada cruzadamente desde más de 40 fuentes académicas revisadas por pares, con varianza cultural por bloque. Todos los parámetros completos en v1.1.0. **Recordatorio: la sociedad es más compleja que 43 variables; esta área requiere evaluación, ampliación y evolución constantes.**
- **Protocolo de validación formal PVU-BS** con pruebas Diebold-Mariano y corrección Holm-Bonferroni.
- **UI Streamlit bilingüe** (inglés / español) con selector de idioma en tiempo de ejecución.
- **Conectores de redes sociales**: Twitter/X (API v2 Recent Search) y Reddit (praw) para inicialización con sentimiento en vivo.

---

## Paquete del repositorio para IA con Repomix

MASSIVE incluye una configuración de Repomix para que cualquier asistente de IA pueda revisar el repositorio como un único archivo XML estructurado, sin versionar paquetes generados.

```bash
npx --yes repomix@latest --config repomix.config.json
```

El comando genera `repomix-output.xml` usando `.gitignore`, `.repomixignore` y `repomix-instruction.md` para excluir secretos locales, cachés, artefactos de compilación, binarios y salidas generadas. Para obtener una vista estructural más compacta, ejecuta:

```bash
npx --yes repomix@latest --config repomix.config.json --compress -o repomix-output-compressed.xml
```

## Arquitectura

```
┌──────────────────────────────────────────────────────────────┐
│                   Streamlit UI  (app.py)                      │
│  Tab 1: Simulación │ Tab 2: Arquitecto │ Tab 3: Multicapa │ Tab 4: Masiva │
└─────┬──────────────────┬──────────────────┬──────────────────┘
      │                  │                  │
┌─────▼──────┐  ┌────────▼────────┐  ┌──────▼──────────────┐
│ simulator  │  │ social_architect │  │ multilayer_engine    │
│ (13 reglas)│  │ (bucle LLM +    │  │ (5D × 3 capas +     │
│ EWS / TDA  │  │  StrategyMatrix) │  │  matriz θ + Numba)  │
└─────┬──────┘  └────────┬────────┘  └──────┬──────────────-┘
      │                  │                  │
      └──────────┬────────┘                  │
                 ▼                           │
    ┌─────────────────────────────────────── ┘
    │  energy_engine (Langevin / Numba JIT)
    │  massive_engine (LOD / uint8 / evento / GPU)
    └────────────────────────────────────────────
                 │
    ┌────────────▼────────────────────────────────────┐
    │  Proveedores LLM (vía llm_credentials.py):       │
    │  heurístico │ Ollama │ Groq │ OpenAI │ OpenRouter│
    │  (cadenas LangChain opcionales en langchain_workflows.py) │
    └──────────────────────────────────────────────────┘
```

### La ecuación de Langevin en cada paso

```
x(t + Δt) = f(x(t), r(t)) · α  +  b(x(t)) · (1 − α)  +  G(x(t))  +  η(t)
```

| Término | Significado |
|---------|------------|
| `f(x(t), r(t))` | Salida de la regla dinámica activa `r` (HK, umbral, replicador, …) |
| `α` | Peso de mezcla entre modelo seleccionado por LLM y tendencia base (por defecto 0.80) |
| `b(x(t))` | Tendencia base: `0.92 · opinión + 0.08 · propaganda` |
| `G(x(t))` | Polarización de grupo: influencia ponderada de clústeres A/B |
| `η(t) ~ 𝒩(0, σ²)` | Incremento estocástico de Wiener |

El ruido se adapta a la confianza institucional: `σ(t) = σ_base + σ_desconfianza · (1 − confianza(t))`. A medida que la confianza se erosiona, el sistema se vuelve más difícil de dirigir y produce oscilaciones de opinión más amplias.

### Bucle del Arquitecto Social

```
Objetivo del usuario (texto libre) + estado inicial de la red
        │
        ▼
LLM propone StrategyMatrix (cronograma JSON de intervenciones)
        │
        ▼
run_with_schedule() → motor Langevin ejecuta cada fase
        │
        ▼
evaluar_resultado() → puntuación 0–100 (polarización, delta, varianza)
        │
   Puntuación ≥ 90? ──SÍ──► generar_narrativa_final() ──► Listo
        │
       NO
        │
inyectar retroalimentación en contexto LLM → repetir (hasta max_intentos)
```

### Ecuación multicapa

```
dx_i/dt = −∇U(x_i) + Σ_ℓ w_ℓ · (A_ℓ · G(x))_i + θ(a_i) · η_i
```

Tres capas de red diferenciadas corren simultáneamente:

| Capa | Topología | Fenómeno capturado |
|------|-----------|-------------------|
| Social | Watts-Strogatz (mundo pequeño) | Contactos cara a cara, comunidad local |
| Digital | Barabási-Albert (libre de escala) | Redes sociales, cámaras de eco, contenido viral |
| Económica | Jerárquica (estrella + hubs) | Flujo de autoridad, salarios, poder organizacional |

---

## Reglas de Simulación

| # | Regla | Fundamento teórico |
|---|-------|-------------------|
| 0 | `lineal` | Cambio proporcional suave |
| 1 | `umbral` | Salto al cruzar punto crítico |
| 2 | `memoria` | Inercia del estado pasado |
| 3 | `backlash` | La propaganda refuerza posición contraria |
| 4 | `polarizacion` | Atractor de cámara de eco |
| 5 | `hk` | Hegselmann-Krause (2002) — confianza acotada |
| 6 | `contagio_competitivo` | Dos narrativas compitiendo — Beutel et al. (2012) |
| 7 | `umbral_heterogeneo` | Distribución de umbrales Granovetter (1978) — cascadas sociales |
| 8 | `homofilia` | Red co-evolutiva — Axelrod (1997) |
| 9 | `replicador` | EDO replicadora integrada con RK45 — Taylor & Jonker (1978) |
| 10 | `nash` | Juego de coordinación Nash equilibrium (1950) — vía `nashpy` |
| 11 | `bayesiano` | Red bayesiana de opinión — Pearl (1988), construida con `pgmpy` |
| 12 | `sir` | Contagio epidemiológico SIR — Kermack & McKendrick (1927) |

**Mecanismos transversales** (aplicados sobre cada regla en cada paso):
- **Sesgo de Confirmación** (Sunstein 2009, Nickerson 1998) — la información contraria se atenúa proporcionalmente a la posición actual del agente.
- **Homofilia Dinámica** (Axelrod 1997, Flache et al. 2017) — los pesos de influencia de grupo se actualizan en cada paso según similitud de opinión.
- **Fuerza Estratégica de Teoría de Juegos** (`utility_logic.py`) — sesgo basado en payoff hacia cooperación o deserción según la posición media de los vecinos.

---

## Instalación

**Requisitos:** Python 3.9+

```bash
git clone https://github.com/Adlgr87/MASSIVE.git
cd MASSIVE
pip install -r requirements.txt
```

**Aceleradores opcionales** (instalar por separado):

```bash
pip install numba             # Motor Langevin compilado JIT (~10–50× aceleración)
pip install cupy-cuda12x      # Descarga en GPU via CUDA (se detecta automáticamente; fallback a CPU)
pip install dask              # Simulaciones múltiples paralelas
pip install ripser persim     # Análisis de Datos Topológicos (homología persistente)
```

---

## Ejecutar la App

### Local (Streamlit)

```bash
streamlit run app.py
```

### Docker

```bash
docker build -t massive:latest .
docker run --rm -p 8501:8501 --env-file .env massive:latest
```

`--env-file .env` lee variables de tu archivo local en el host y las inyecta al contenedor (el archivo `.env` no se copia a la imagen).

Luego, abre: `http://localhost:8501`

La interfaz tiene cuatro pestañas:

| Pestaña | Función |
|---------|---------|
| **Simulación** | Configura y ejecuta simulaciones hacia adelante con cualquiera de las 13 reglas; visualiza trayectorias, alertas EWS, TDA y grafo de red |
| **Arquitecto Social** | Describe un resultado objetivo en lenguaje natural; el agente LLM ingeniería inversa el cronograma de intervención |
| **Multicapa** | Ejecuta el motor sociodemográfico 5D sobre tres capas de red con desglose demográfico |
| **Masiva** | Simula millones de agentes usando el motor LOD/uint8/eventos/GPU |

El selector de idioma (inglés ↔ español) está disponible en la parte superior de la barra lateral.

### Hugging Face Spaces

Este repositorio está listo para desplegar como un Space de Streamlit. Conecta el repositorio y configura tus API keys como Secretos.

---

## API Programática

```python
# Simulación hacia adelante — 13 reglas, selector LLM, EWS
from simulator import simular

result = simular(
    opinion_inicial=0.5,
    regla="hk",                  # Hegselmann-Krause: confianza acotada
    pasos=100,
    propaganda=0.3,
    provider="groq",             # heuristico | ollama | groq | openai | openrouter
)

# Motor multicapa — vectores 5D, tres capas de red
from multilayer_engine import MultilayerEngine

engine = MultilayerEngine(
    N=200,
    layer_weights=(0.4, 0.3, 0.3),   # social, digital, económica
    coupling=0.3,
    attr_config={"religion_prob": 0.35, "age_dist": (0.25, 0.45, 0.30)},
)
history   = engine.run(steps=500)
traj_df   = engine.trajectories_by_attribute("age_group")
corr      = engine.behavior_correlation_matrix()

# Motor de escala masiva — millones de agentes, todas las optimizaciones
from massive_engine import MassiveSimEngine

engine = MassiveSimEngine(
    N=1_000_000,
    quantize=True,
    event_driven=True,
    layer_weights=(0.4, 0.3, 0.3),
    seed=42,
)
result = engine.run(steps=300)
print(f"Ahorro de memoria: {result['memory_savings_pct']:.1f}%")  # ≈ 99.99%
print(f"Pasos/segundo:     {result['steps_per_second']:.0f}")

# Aplicar un shock de noticias al 20% de la red
engine.apply_shock(shock_value=0.4, fraction=0.2)
```

---

## Configuración

### Variables de entorno

Copia `.env.example` a `.env`:

```env
# Proveedores LLM (al menos uno requerido para modo no-heurístico)
GROQ_API_KEY=tu_clave
OPENAI_API_KEY=tu_clave
OPENROUTER_API_KEY=tu_clave

# Conectores de redes sociales (opcionales)
TWITTER_BEARER_TOKEN=tu_token
REDDIT_CLIENT_ID=tu_id
REDDIT_CLIENT_SECRET=tu_secreto
```

Todos los proveedores LLM resuelven credenciales a través de `llm_credentials.py`. En Hugging Face Spaces, configúralas como Secretos en lugar de un archivo `.env`.

### Configuración multicapa

Los pesos de capa, parámetros de red y distribuciones de atributos demográficos se pueden cambiar sin modificar código via `configs/multilayer.yaml`.

### Calibración empírica

`empirical_config.py` es la fuente única de verdad para los 43 parámetros empíricos (v1.1.0, 88.4% de cobertura, validados desde más de 40 fuentes académicas). `empirical_calibration.py` los traduce a defaults nativos del motor vía `build_empirical_engine_config(cultural_profile)`. Los valores de ejecución se derivan con agregados ponderados: influencia social → `efecto_vecinos_peso`, homofilia → `hk_epsilon` / `homofilia_tasa`, decaimiento de atención → ruido adaptativo, evidencia de tipping social → `umbral_media = 0.25 ± 0.05` (Centola et al. 2018; Everall et al. 2025). Se admiten siete perfiles culturales: `"mixed"` (por defecto), `"latin"`, `"anglosaxon"`, `"east_asian"`, `"middle_east"`, `"south_asian"`, `"subsaharan_africa"`. Aplícalos vía `apply_empirical_profile(cfg)` en la UI o `get_runtime_params(cultural_profile)` de forma programática. Todos los 43 parámetros están completos en v1.1.0 — sin etiquetas `pending_empirical_data` activas. Recordatorio: la sociedad es más compleja que 43 variables y esta área debe mantenerse en evaluación, ampliación y evolución continua.

---

## Rendimiento a Escala

`massive_engine.py` combina cuatro estrategias para hacer tractable la simulación a escala poblacional en hardware estándar:

### 1 — LOD Sociológico (super-agentes)

N agentes colapsan en M clústeres estadísticos. Solo M << N representantes son evolucionados; el resto se reconstruye en tiempo de consulta.

| N agentes | M clústeres (auto) | Tamaño matriz | RAM (float64) |
|-----------|-------------------|---------------|---------------|
| 10 000 | 100 | 100 × 100 | ~0.08 MB |
| 100 000 | 316 | 316 × 316 | ~0.8 MB |
| 1 000 000 | 1 000 | 1 000 × 1 000 | ~8 MB |

### 2 — Cuantización de estado uint8

Los parámetros de agentes se almacenan como enteros de 8 bits sin signo en lugar de float64: **reducción de RAM del 87.5%** por parámetro con resolución ≈ 0.008 unidades de opinión.

### 3 — Conjuntos activos dirigidos por eventos

Solo los super-agentes cuyo estado cambió más de `sleep_threshold` se actualizan. Los agentes en consenso estable están congelados — costo de CPU cero hasta que un vecino los despierte.

### 4 — Descarga en GPU

Las operaciones matriciales se delegan automáticamente a GPU cuando se detectan CuPy o PyTorch+CUDA. Cae automáticamente a NumPy — sin configuración requerida.

**Efecto combinado en N = 1 M agentes:** >99.99% de reducción de RAM vs. una implementación ingenua con float64.

---

## Integración con Redes Sociales

Inicializa simulaciones con datos de opinión en vivo desde plataformas reales:

### Twitter / X

Requiere un Bearer Token del [Portal de Desarrolladores de Twitter](https://developer.twitter.com). El conector consulta la API v2 Recent Search, aplica puntuación de sentimiento basada en palabras clave y devuelve una distribución de opiniones ponderada.

### Reddit

Requiere una aplicación de tipo script en [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) (Client ID + Secret). Usa `praw` para puntuar títulos y cuerpos de publicaciones por sentimiento, ponderado por puntuación de votos de Reddit.

Ambos conectores soportan rangos bipolar `[-1, 1]` y unipolar `[0, 1]`.

---

## Protocolo de Validación (PVU-BS)

MASSIVE incluye un **Protocolo de Uso Validado (PVU-BS)** formal que define el estándar mínimo de evidencia para afirmar rendimiento predictivo validado en datos reales.

| Concepto | Descripción |
|----------|------------|
| **Caso independiente** | Una tupla `{red, serie_temporal, intervenciones, metadatos}` — casos con confusores comparten `cluster_id` |
| **Variable objetivo** | Compuesta: Índice de Polarización P(t) + Habilidad en Puntos de Inflexión (F1 en transiciones de régimen) |
| **Anti-filtración** | Las métricas de test nunca deben verse antes de congelar la configuración del modelo |
| **Estadísticas** | Prueba Diebold-Mariano + corrección Holm-Bonferroni; tamaños de efecto (ΔMAE, ΔRMSE, TPS F1) obligatorios |

```bash
# Offline (sin API key requerida — por defecto en CI):
PYTHONHASHSEED=42 python -m benchmarks.runner \
    --cases datasets/pvu_cases --offline \
    --out reports/validation/ci --seed 42

# Modo LLM (requiere OPENROUTER_API_KEY o OPENAI_API_KEY):
PYTHONHASHSEED=42 python -m benchmarks.runner \
    --cases datasets/pvu_cases --llm \
    --out reports/validation/llm_run --seed 42
```

Protocolo completo: [Inglés](docs/validation/PVU_BeyondSight_EN.md) · [Español](docs/validation/PVU_BeyondSight_ES.md)

> **Nota:** `datasets/pvu_cases/` contiene actualmente casos sintéticos solo para pruebas de pipeline. La validación PVU-BS real requiere N ≥ 10 casos reales independientes.

---

## Decisiones de Diseño

**Opinión como sistema físico.** Modelar la evolución de opinión como dinámica de Langevin trae herramientas de la física estadística — pozos de energía, difusión estocástica, teoría de puntos de inflexión — mientras permanece anclado a literatura sociológica en lugar de metáforas físicas.

**LLM como selector de régimen, no como oráculo.** El LLM no predice resultados. Selecciona qué modelo matemático es más apropiado para el contexto social actual en cada paso. Esto mantiene los resultados interpretables: cada predicción se rastrea hasta una regla matemática definida y su fundamento académico.

**Inversa antes que adelante.** El Arquitecto Social fue diseñado junto al simulador, no agregado posteriormente. El bucle proponer-simular-puntuar-refinar es una característica arquitectónica de primer nivel, no un envoltorio.

**Responsabilidad empírica por defecto.** Cada parámetro de calibración tiene una cita de fuente y un estimado de varianza cultural. Las brechas se señalan explícitamente — el simulador muestra lo que no sabe en lugar de llenar silencios con valores por defecto.

**Escala sin clúster.** La combinación LOD + uint8 + eventos degrada graciosamente: un portátil ejecuta simulaciones significativas, un clúster GPU ejecuta proporcionalmente más rápido. Sin requisito de infraestructura.

Modernized assets joined overlays, refreshed interface tuning yielded reliable experience; polished outputs reflect today.

---

## Limitaciones

- **Optimización de intervenciones:** La búsqueda actual es estocástica y puede converger a óptimos locales; para análisis críticos se recomienda ejecutar múltiples semillas y comparar estabilidad del plan.
- **Cobertura de base empírica:** Los 43 parámetros están completos en v1.1.0 (88.4% de cobertura; sin etiquetas `pending_empirical_data` activas). Bloques de calibración cultural adicionales (Nórdico, Asia del Sur) están planificados para versiones futuras. Recordatorio: la sociedad es más compleja que 43 variables y este bloque debe revisarse, ampliarse y evolucionar de forma permanente.
- **Validación en el mundo real:** Los casos de benchmark PVU-BS actuales son sintéticos (para pruebas de pipeline). La validación con datos de opinión reales (N ≥ 10 casos independientes) está en progreso.
- **Dependencia del LLM:** El Arquitecto Social y el selector de régimen funcionan mejor con un LLM en la nube. Hay siempre disponible un fallback heurístico, pero produce estrategias menos coherentes contextualmente.
- **Conectores de redes sociales:** El acceso a la API v2 de Twitter/X requiere una cuenta de desarrollador con el nivel apropiado; el rendimiento depende de los límites de tasa de terceros.

---

## Roadmap

- [ ] Casos de validación PVU-BS reales desde conjuntos de datos de opinión pública
- [ ] Bloques de calibración cultural adicionales (Nórdico, Asia del Sur, Oriente Medio)
- [ ] Ejecutores de agentes LangChain con acceso a herramientas (búsqueda web, recuperación de datos en tiempo real)
- [ ] Arquitecto Social orientado a nodos (programación de intervenciones guiada por centralidad de intermediación)
- [ ] Exportar ejecuciones de simulación a formatos estándar (NetLogo, GEXF, CSV)

---

## Estructura del Proyecto

```
MASSIVE/
├── app.py                        # UI Streamlit — 4 pestañas
├── simulator.py                  # Núcleo: 13 reglas, selector LLM, EWS, TDA, paralelo Dask
├── social_architect.py           # Arquitecto Social: agente LLM de ingeniería inversa
├── energy_engine.py              # Motor Langevin (JIT compilado con Numba)
├── energy_runner.py              # Orquestador de simulación Langevin
├── energy_schemas.py             # Esquemas Pydantic v2 para EnergyConfig
├── multilayer_engine.py          # Motor sociodemográfico 5D × 3 capas (Numba + θ-matriz)
├── massive_engine.py             # Motor de escala: LOD, uint8, eventos, GPU
├── extended_models.py            # Reglas 10–12: Nash, Red Bayesiana (pgmpy), SIR
├── langchain_workflows.py        # Cadenas tipadas LangChain: estrategia, narrativa, paisaje
├── programmatic_architect.py     # Librería de arquetipos + caché RAM/SQLite + generador LLM
├── social_connectors.py          # Conectores Twitter/X (v2) y Reddit (praw)
├── empirical_config.py           # Diccionario maestro empírico (BEYONDSIGHT_EMPIRICAL_MASTER, v1.1.0, 88.4%)
├── empirical_calibration.py      # Traduce la base empírica → defaults nativos del motor
├── utility_logic.py              # Calculador de fuerza estratégica de teoría de juegos
├── cache_manager.py              # Caché de paisaje en RAM + SQLite
├── llm_credentials.py            # Resolución centralizada de claves API para todos los proveedores
├── schemas.py                    # Esquemas Pydantic: StrategyMatrix, GamePayoff
├── visualizations.py             # Ayudantes de visualización de red (Plotly + NetworkX)
├── i18n.py                       # Internacionalización (inglés / español)
├── intervention_optimizer.py     # Optimizador estocástico para estrategia por fases
├── state_compression.py          # Compresión SVD para estados grandes de agentes
├── benchmarks/                   # Ejecutor de benchmark offline PVU-BS
├── configs/
│   ├── multilayer.yaml           # Configuración de capas y atributos demográficos
│   └── pvu.yaml                  # Configuración del ejecutor PVU
├── datasets/pvu_cases/           # Carpetas de casos de benchmark (actualmente sintéticos)
├── docs/validation/              # Protocolo PVU-BS (inglés + español)
├── reports/validation/           # Salidas de benchmark auto-generadas
├── tests/                        # 200+ pruebas unitarias e de integración
├── massive_core/                 # Capa científica: solvers, estabilidad, EnKF, perturbación, multicapa disperso, inferencia
├── massive_core/numerics/        # Steppers adaptativos, Solver de perturbación disperso, Análisis de estabilidad, Motor multicapa disperso
├── massive_core/data_assimilation/  # EnKF completo, filtro EnKF disperso, workflows de asimilación
├── massive_core/physics/         # Mecánica estadística, hidro dinámica, teoría de perturbación
├── massive_core/network_inference/  # Reconstrucción de red (DE, CG, correlación, entropía transferida)
├── .env.example                  # Plantilla de variables de entorno
├── README.md                     # Documentación en inglés
└── README_ES.md                  # Este archivo
```

---

## Tests

```bash
pytest tests/
```

La suite cubre: núcleo del simulador, motor de energía, motor multicapa, motor de escala masiva, capa de teoría de juegos, arquitecto social, calibración empírica, ejecutor PVU, visualizaciones e integración LLM. Los tests se ejecutan en CI en cada push.

---

## Contribuir

Las contribuciones son bienvenidas. Por favor:

1. Haz fork del repositorio y crea una rama de feature.
2. Sigue el estilo de código existente (docstrings Google-style, type hints, `pytest` para tests).
3. Agrega o actualiza tests para cualquier comportamiento modificado y ejecuta `pytest tests/` antes de abrir un PR.
4. Para nuevos parámetros empíricos, incluye referencias de fuente y metadatos de varianza cultural en el mismo formato que `BEYONDSIGHT_EMPIRICAL_MASTER`.

Consulta [CONTRIBUTING.md](CONTRIBUTING.md) para guías completas y [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) para estándares de la comunidad.

---

## Licencia

[Apache License 2.0](LICENSE) — libre para uso personal, académico y comercial con atribución.

Diseño, arquitectura y lógica del sistema por [Adlgr87](https://github.com/Adlgr87).  
Para consultoría o colaboraciones, contacta via [GitHub](https://github.com/Adlgr87).

---

*Many behaving as One.*


## Nota de despliegue
El CI ya no usa push forzado a Hugging Face Spaces. Configure HF_TOKEN en los secretos del repositorio.
