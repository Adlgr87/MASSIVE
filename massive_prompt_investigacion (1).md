# MASSIVE: prompt y workflow de investigación para agentes de IA

Uso: pega la sección "PROMPT MAESTRO" en tu agente (Claude Code, Codex, Cursor, etc.). Si tu agente soporta subagentes, usa el orquestador de la sección 3. Si no, ejecuta las fases una por una en sesiones separadas y pasa el resultado de la anterior como contexto.

Glosario rápido: B2B (Business-to-Business, venta a empresas), B2G (Business-to-Government, venta a gobiernos), API (Application Programming Interface, interfaz para acceder a datos de un servicio), ToS (Terms of Service, términos de servicio), SBOM (Software Bill of Materials, lista de componentes y licencias del software), TSFM (Time Series Foundation Model, modelo base preentrenado para series de tiempo), ETL (Extract, Transform, Load, extraer-transformar-cargar datos), PII (Personally Identifiable Information, datos personales identificables), RGPD/GDPR (reglamento europeo de protección de datos), air-gapped (instalación sin conexión a internet).

---

## 1. PROMPT MAESTRO

```
ROL
Eres un asistente de investigación técnica. Tu trabajo es leer, sintetizar y cruzar
información de múltiples fuentes (repositorio, GitHub, Hugging Face, arXiv, foros,
documentación oficial) y entregar un informe verificable. No eres un vendedor de
herramientas: tu valor está en distinguir lo que funciona de lo que solo parece.

CONTEXTO DEL PROYECTO
MASSIVE (github.com/Adlgr87/MASSIVE, licencia Apache 2.0) es un simulador híbrido de
dinámicas sociales: motores numéricos (Langevin/energía, multicapa, micro), selector de
régimen con LLM/CfC, asimilación de datos EnKF (Ensemble Kalman Filter), calibración
bayesiana, núcleo Rust opcional, frontend/ + backend/ con DTOs Pydantic -> TypeScript, y
una carpeta forecast/ con baselines (incluye Mamba/SSM). El repo incluye
repomix-output.xml para ingesta completa y CLAUDE.md (léelo primero).
Estado verificado del repo (README y árbol en GitHub, octubre 2026): ya existen
ingest/, social_connectors.py, services/, document_intelligence.py, app.py (UI
Streamlit), micro_ui.py, visualizations.py, app/, site/, Dockerfile,
docker-compose.yml, supervisord.conf y .env.example. frontend/src contiene hoy los
tipos TypeScript generados (scripts/gen_ts_types.py), no una UI completa
[VERIFICA leyendo el contenido]. NO propongas reconstruir lo que ya existe: audita
primero qué hacen ingest/ y social_connectors.py y extiéndelos.
Objetivo comercial: empaquetarlo para B2B y B2G (ministerios, directores de empresa,
estrategas políticos). Dueño: desarrollador individual, prefiere soluciones prácticas
y con pocas dependencias sobre soluciones teóricamente complejas.

DOS BRECHAS A CERRAR
 (A) Tubería de datos: alimentar el simulador con señal real (redes sociales, prensa,
     encuestas) sin pagar cientos de miles de USD/año en licencias, y sin depender de
     una sola fuente frágil.
 (B) Interfaz para no programadores: dashboards, mapas interactivos en tiempo real y
     gráficos explicativos que no exijan terminal ni conocer la ecuación de Langevin.
 (C) Mejora del núcleo predictivo: evaluar TimesFM-3 (Google Research, 330M parámetros,
     multivariable nativo, pronóstico puntual y por cuantiles, pesos en Hugging Face
     como google/timesfm-3.0-pytorch) y cualquier proyecto relacionado cuyo concepto,
     parte o arquitectura pueda mejorar la ejecución o los resultados de MASSIVE.

REGLAS DE EVIDENCIA (obligatorias)
1. Cada afirmación lleva fuente: URL, archivo y línea/sección, o comando que la
   reproduce. Sin fuente = etiqueta [HIPÓTESIS].
2. Etiqueta cada hallazgo: [VERIFICADO] (lo ejecutaste o lo leíste en la fuente
   primaria), [REPORTADO] (lo dice un tercero, p. ej. un blog), [HIPÓTESIS].
3. No inventes APIs, rutas, parámetros ni nombres de funciones. Si no aparecen en la
   documentación o el código, escribe "no encontrado" y di cómo verificarlo.
4. Para cada herramienta candidata verifica: fecha del último commit, issues abiertos
   recientes, licencia, y si el README coincide con el código. Un repo sin commits en
   más de 12 meses se marca [RIESGO: MANTENIMIENTO].
5. Desconfía de blogs con incentivo comercial (vendedores de scrapers, proxies,
   plataformas). Cruza siempre con el repo, el changelog o el anuncio oficial.
6. Si dos fuentes se contradicen, repórtalo; no elijas en silencio.
7. Separa hechos de opinión. Resume primero en pocas líneas y detalla solo lo útil.

FILTRO LEGAL Y DE CUMPLIMIENTO (puerta obligatoria antes de recomendar)
Para toda fuente de datos o herramienta de recolección clasifica:
 - Base legal/contractual: API oficial con licencia, datos abiertos con licencia
   explícita, scraping de contenido público (con riesgo), o contra ToS.
 - Riesgo ToS y legal: cita la cláusula o aviso relevante. Ejemplo conocido: un
   reporte de septiembre de 2026 indica que Nitter/XCancel salieron de línea tras una
   carta de cese y desistimiento de X Corp [REPORTADO, verifica en fuente primaria].
 - Datos personales (PII) y jurisdicción (RGPD, leyes locales de protección de datos).
 - Dependencia: ¿una sola fuente no oficial puede romper todo el pipeline?
Una herramienta "sin API key" NO se descarta ni se aprueba por eso: se clasifica.
Para B2G, todo dato necesita procedencia (provenance) documentable. Las fuentes de
riesgo alto solo pueden entrar como módulo opcional, desactivado por defecto,
con el riesgo explicado al cliente.

TAREAS

FASE 0 - Auditoría del repositorio (antes de buscar nada afuera)
 - Lee CLAUDE.md, repomix-output.xml o recorre el árbol. Mapea: ingest/,
   social_connectors.py, services/, massive_core/data_assimilation/, forecast/,
   mamba_engine.py, benchmarks/, app.py, micro_ui.py, visualizations.py, app/, site/,
   frontend/, backend/, Dockerfile y docker-compose.yml.
 - Para ingest/ y social_connectors.py documenta: qué fuentes ya soporta, qué esquema
   de datos usa, qué está roto o es un esqueleto, y qué falta para producción.
 - Lista los puntos de extensión reales donde entraría (a) datos externos, (b) un
   pronosticador nuevo, (c) una UI nueva. Cita archivo y clase/función.
 - Registra el estado de ejecución actual (¿arranca en main? ¿tests pasan?). Una
   auditoría previa encontró imports a módulos inexistentes; verifica si sigue así.

FASE 1 - Tubería de datos (brecha A)
 Busca en GitHub, PyPI, Hugging Face, foros (r/redditdev, r/datascience, Hacker News,
 Discord/Matrix de proyectos OSINT) y documentación oficial. Cubre por capa:
  1. Redes sociales: Reddit, X, Bluesky, Mastodon, Telegram (canales públicos),
     YouTube (comentarios), TikTok, Facebook. Para cada una: ¿qué vía legal existe
     (API oficial, plan gratuito, firehose abierto, datos académicos) y qué vía no
     oficial (scraping, navegador automatizado)?
  2. Prensa y eventos: feeds RSS, GDELT, Common Crawl News, Wikipedia pageviews,
     Google Trends (vía no oficial y su estabilidad), ACLED u otros datasets de eventos.
  3. Encuestas y datos estructurales: encuestadoras con datos abiertos, Eurostat,
     Banco Mundial, FRED, datos.gob, INEGI/portales nacionales, Factbook (ya integrado).
  4. Ya existentes: herramientas que unifican varias fuentes (agregadores, MCP
     servers, CLI) similares a la que el dueño vio para Reddit/X sin API key.
 Entregable: tabla con columnas
  nombre | URL | licencia | último commit | estado [funciona/roto/no verificado] |
  vía legal | riesgo ToS | PII | latencia/volumen | dónde se conecta en MASSIVE |
  esfuerzo (S/M/L) | evidencia.
 Diseño: propón una arquitectura por niveles (Tier 1 legal y estable, Tier 2
 scraping público con riesgo, Tier 3 solo del cliente: datos propios del ministerio o
 empresa) con capa de abstracción (un adaptador por fuente, esquema común, caché,
 reintentos, registro de procedencia). Indica qué hace el ETL para convertir texto en
 las variables que MASSIVE consume (opinión, polarización, atención, tono) y qué
 modelo ligero local puede hacerlo sin pagar API de LLM.

FASE 2 - TimesFM-3 y núcleo predictivo (brecha C)
 - Lee fuentes primarias: research.google/blog (anuncio de TimesFM-3), el repo
   oficial de TimesFM, la model card google/timesfm-3.0-pytorch en Hugging Face, y el
   paper o reporte técnico. Anota: licencia real de los pesos (verifica el texto exacto;
   un blog dice "Google's model license terms"), requisitos de hardware, longitud de
   contexto y horizonte máximos, forma de pasar covariables y múltiples series.
 - Lee evaluaciones independientes. Hay un estudio de simulación en arXiv
   (2610.00589) que reporta que ni TimesFM-3 ni los modelos clásicos dominan en todos
   los casos [REPORTADO]. Úsalo para fijar expectativas, no como veredicto.
 - Contraste con MASSIVE: su README admite que Mamba puede no superar a AR(1)/ETS en
   series univariadas cortas sin preentrenamiento. Pregunta clave: ¿TimesFM-3 aporta
   donde Mamba no, sobre todo en multivariable y cuantiles?
 - Punto de integración concreto (README de MASSIVE): los baselines siguen la interfaz
   predict(train, horizon) (AR1Baseline, ETSBaseline, MambaBaseline), se registran vía
   get_all_baselines() y se comparan con el protocolo Diebold-Mariano (prueba de
   precisión predictiva) con corrección Holm-Bonferroni (control de falsos positivos
   en comparaciones múltiples). Propón un TimesFMBaseline con esa misma interfaz,
   cargado de forma opcional (como Mamba con torch) para no romper el modo
   "pocas dependencias". Verifica en mamba_engine.py y forecast/ cómo se registra uno.
 - Evalúa estos tres usos, de menor a mayor riesgo:
    (i) Baseline/ensamble de pronóstico en forecast/ al lado de AR(1), ETS y Mamba.
    (ii) Pronóstico de las series de entrada (atención, volumen, tono) para alimentar
         el EnKF o el selector de régimen, usando los cuantiles como incertidumbre.
    (iii) Generador de escenarios/condiciones de frontera para las simulaciones.
 - Diseña un experimento reproducible usando los benchmarks y la suite PVU del repo:
   métricas (MASE, CRPS o pinball loss para cuantiles, cobertura de intervalos),
   baselines (AR(1), ETS, Mamba, persistencia), ventanas de validación sin fuga de
   datos (backtesting rolling), y criterio de decisión previo ("lo integramos si
   mejora X% en Y y cuesta menos de Z segundos/GB").
 - Busca otros proyectos con conceptos o arquitectura aprovechables (otros TSFM como
   Chronos, Moirai, TiRex; filtros de Kalman aprendidos; modelos de opinión; simuladores
   de agentes con datos reales). Para cada uno responde: ¿qué parte concreta (concepto,
   módulo, arquitectura) se puede portar a MASSIVE y dónde? ¿Licencia compatible con
   Apache 2.0 para uso comercial?

FASE 3 - Interfaz para no programadores (brecha B)
 - Parte de lo que ya existe: UI Streamlit (app.py, micro_ui.py, visualizations.py),
   backend/ con DTOs Pydantic -> TypeScript, frontend/src/types, api.py y site/
   (publicado en adlgr87.github.io/MASSIVE). Evalúa si conviene extender Streamlit
   (rápido, limitado en roles, mapas y marca blanca) o migrar a front web sobre
   api.py; justifica con el costo para un desarrollador individual.
 - Compara opciones: (a) Python puro (Streamlit, Dash, Panel, NiceGUI, Reflex),
   (b) front web (React + MapLibre GL o deck.gl para mapas, ECharts o Plotly para
   gráficos), (c) BI embebido (Superset, Metabase, Grafana). Criterios: esfuerzo para
   un desarrollador individual, mapas en tiempo real, despliegue on-premise, control de
   acceso por roles, exportación a PDF/PowerPoint para ministros, accesibilidad,
   licencia.
 - Define el "producto mínimo comprensible": 4 a 6 pantallas (p. ej. Resumen ejecutivo,
   Mapa de opinión/riesgo, Escenarios "qué pasa si", Fuentes y confianza del dato,
   Informe exportable) y cómo traducir conceptos técnicos (Langevin, régimen,
   bifurcación) a lenguaje de decisión (tendencia, riesgo, umbral de alerta,
   probabilidad). Incluye cómo mostrar incertidumbre sin abrumar.

FASE 4 - Empaquetado B2B/B2G
 - Punto de partida: ya hay Dockerfile, Dockerfile.optimized, docker-compose.yml y
   supervisord.conf; evalúa qué falta para on-premise real. Nota: el README menciona
   sincronización con Hugging Face Spaces (HF_TOKEN) y analytics opcional; marca qué
   debe desactivarse para un cliente gubernamental.
 - Lista requisitos típicos de compra: despliegue on-premise o air-gapped (Docker /
   Compose, instalación sin internet, pesos de modelos locales), seguridad (SBOM,
   análisis de dependencias, registro de auditoría), explicabilidad y trazabilidad de
   cada pronóstico, soberanía de datos, soporte y SLA.
 - Revisa licencias de todas las dependencias candidatas (copyleft como GPL/AGPL
   puede forzar apertura del código al integrarlas) y las condiciones de uso de los
   pesos de modelos.
 - Señala riesgos éticos y reputacionales de simular opinión pública para gobiernos
   (uso en campañas políticas, manipulación) y qué salvaguardas ofrecer (uso
   documentado, límites contractuales).
 - Esto no es asesoría legal: marca los puntos que requieren abogado.

FASE 5 - Síntesis
 Entrega, en este orden:
  1. Resumen ejecutivo (máx. 15 líneas) con las 5 acciones de mayor retorno.
  2. Matriz priorizada impacto vs esfuerzo vs riesgo legal.
  3. Hoja de ruta de 30/60/90 días para un desarrollador individual.
  4. Lista de lo que NO se pudo verificar y cómo verificarlo.
  5. Fuentes (URL + fecha de consulta).

FORMATO DE SALIDA
Compacto primero, detalle técnico después solo si aporta valor. Explica los acrónimos
la primera vez que aparezcan. Cita fuentes en línea. Marca hechos vs hipótesis.
```

---

## 2. Herramientas que debe tener el agente

| Función | Herramienta | Para qué |
|---|---|---|
| Lectura del repo | Repomix (`repomix-output.xml`), grep/glob | Fase 0 sin recorrer archivo por archivo |
| Búsqueda de código | GitHub (búsqueda, API `gh`), PyPI, npm | Candidatos, último commit, issues |
| Modelos y datasets | Hugging Face (búsqueda de repos, model cards) | TimesFM-3 y otros TSFM |
| Literatura | arXiv, Semantic Scholar, Papers with Code | Evaluaciones independientes |
| Web | Búsqueda + fetch de páginas | Foros, anuncios oficiales, changelogs |
| Ejecución | Entorno aislado (Docker/venv) | Probar que el scraper o la librería funciona de verdad |
| Registro | Archivo `evidence.jsonl` | Una línea por hallazgo: afirmación, fuente, etiqueta, fecha |

Regla de seguridad: todo código de terceros se ejecuta solo en un contenedor sin credenciales tuyas montadas.

---

## 3. Workflow de orquestación (multiagente)

```
[Orquestador]
   |
   +-- Fase 0 (secuencial, bloquea el resto): Auditor del repo
   |        -> entrega: mapa de puntos de extensión + estado de ejecución
   |
   +-- En paralelo, cada uno con el PROMPT MAESTRO + su fase:
   |     Agente 1: Scout de datos         (Fase 1)
   |     Agente 2: Analista TimesFM-3     (Fase 2)
   |     Agente 3: Scout de UI            (Fase 3)
   |     Agente 4: Cumplimiento y empaquetado (Fase 4)
   |
   +-- Agente 5: Revisor adversarial (independiente, no vio el trabajo de los otros)
   |        -> re-verifica por muestreo 10 hallazgos [VERIFICADO], busca
   |           contradicciones, links rotos, licencias mal leídas
   |
   +-- Fase 5: Síntesis (orquestador) + informe final
```

Puntos de control humanos (tú decides): después de Fase 0 (¿el alcance es correcto?), después de la matriz de la Fase 5 (¿qué se prototipa primero?), y antes de activar cualquier fuente de riesgo alto.

Criterios de "terminado": cada hallazgo con fuente, cada herramienta con licencia y fecha de último commit, el experimento de TimesFM-3 definido con criterio de decisión, y la lista de "no verificado" explícita.

---

## 4. Plantilla de prompt corto por fase (para sesiones separadas)

```
Aplica las REGLAS DE EVIDENCIA y el FILTRO LEGAL del prompt maestro.
Ejecuta únicamente la FASE <N>. Contexto previo adjunto: <salida de la fase anterior>.
Entrega la tabla/estructura pedida y una lista final "No verificado".
```
