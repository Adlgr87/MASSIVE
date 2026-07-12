"""
interpreter_layer.py — Capa Intérprete Universal (UIL) para MASSIVE
====================================================================

Puente entre el lenguaje natural (coloquial o técnico) y el simulador MASSIVE.
Integra DocumentIntelligence para análisis de archivos y expone cuatro cadenas
LangChain para los flujos de usuario más comunes.

Cadenas disponibles:
    ScenarioWizardChain    — descripción libre → ConfigDict MASSIVE validado
    ConceptExplainerChain  — nombre + valor de parámetro → explicación contextual
    ResultNarratorChain    — historial de simulación → síntesis en prosa
    DocumentExtractionChain— DocumentContext → parámetros MASSIVE

Modo de uso (sin LangChain instalado)::

    layer = InterpreterLayer(provider="groq", api_key="gsk-...")
    cfg   = layer.wizard("hay mucha polarización en mi ciudad")
    # cfg  → dict listo para simular(**cfg)

Con LangChain::

    layer = InterpreterLayer(provider="groq", api_key="gsk-...", use_langchain=True)
    cfg   = layer.wizard("alta polarización, desconfianza institucional")

Con archivos::

    ctx = layer.di.parse_file("informe_encuesta.pdf")
    cfg = layer.from_document(ctx)

Autor: MASSIVE Research
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import BaseModel, Field

from document_intelligence import (
    DocumentContext,
    DocumentIntelligence,
    MASSIVEExtractedConfig,
)
from llm_credentials import resolve_provider_api_key

log = logging.getLogger("massive.interpreter_layer")

# ── Detección de LangChain (opcional) ────────────────────────────────────────

try:
    from langchain_core.output_parsers import JsonOutputParser, StrOutputParser
    from langchain_core.prompts import ChatPromptTemplate
    _LC_AVAILABLE = True
except ImportError:
    _LC_AVAILABLE = False


# ── Prompts del sistema ───────────────────────────────────────────────────────

_WIZARD_SYSTEM = """Eres el Asistente de Configuración de MASSIVE, simulador de dinámica social.
El usuario describe una situación social en lenguaje natural (puede ser coloquial o técnico).
Tu tarea: convertir esa descripción en parámetros de simulación MASSIVE.

PARÁMETROS Y RANGOS:
  opinion         [-1, 1]   opinión media inicial (-1=total rechazo, +1=total apoyo)
  confianza       [0, 1]    confianza institucional (0=nula, 1=absoluta)
  propaganda      [-1, 1]   narrativa mediática dominante
  opinion_grupo_a [-1, 1]   grupo afín/mayoritario
  opinion_grupo_b [-1, 1]   grupo opuesto/minoritario
  identidad_grupo [0, 1]    intensidad de identidad de grupo (0=fluida, 1=tribal)
  sesgo_confirmacion [0,1]  sesgo de confirmación (0=mente abierta, 1=cerrada)
  homofilia_rate  [0, 1]    tendencia a relacionarse con similares
  pasos           [10,500]  duración de la simulación
  regla           string    modelo matemático (degroot, hegselmann_krause,
                            competitive_contagion, threshold, replicator_dynamics,
                            confirmation_bias, axelrod_homophily, nash_equilibrium,
                            bayesian_network, sir_contagion)

EJEMPLOS DE TRADUCCIÓN:
  "hay mucha polarización"          → opinion≈0.0, identidad_grupo≈0.8, regla=hegselmann_krause
  "todos están de acuerdo"          → opinion≈0.7, identidad_grupo≈0.2, regla=degroot
  "fake news muy activas"           → propaganda≈0.8, sesgo_confirmacion≈0.7
  "desconfianza total"              → confianza≈0.1
  "dos bandos irreconciliables"     → opinion_grupo_a≈0.9, opinion_grupo_b≈-0.9

Devuelve SOLO JSON válido con los parámetros inferidos (null para los no mencionados).
Incluye "razon" con breve explicación de las decisiones de mapeo en español.
Incluye "advertencias" (lista) con posibles ambigüedades."""

_EXPLAINER_SYSTEM = """Eres un experto en dinámica social que explica conceptos científicos de forma accesible.
Dado un parámetro del simulador MASSIVE y su valor actual, genera una explicación:

ESTRUCTURA DE LA RESPUESTA (JSON):
  "explicacion_simple": str  — analogía cotidiana, máx 2 oraciones
  "explicacion_tecnica": str — base científica (referencia si aplica)
  "efecto_simulacion": str   — qué cambia en la simulación con este valor
  "consejo_ajuste": str      — cuándo subirlo/bajarlo y por qué
  "rango_tipico": str        — valores típicos en estudios reales

Devuelve SOLO JSON."""

_NARRATOR_SYSTEM = """Eres un analista de ciencias sociales. Se te da el resultado de una simulación MASSIVE.
Genera una síntesis narrativa profesional en español que incluya:

1. DIAGNÓSTICO: ¿Qué pasó en la simulación? (2-3 oraciones)
2. DINÁMICA CLAVE: ¿Qué mecanismo dominó y por qué? (2-3 oraciones)
3. IMPLICACIONES: ¿Qué sugiere esto para la situación real? (2-3 oraciones)
4. RECOMENDACIONES: 2-3 acciones concretas derivadas de los resultados

Usa lenguaje claro. Evita jerga técnica innecesaria.
Si el usuario pide modo técnico, usa terminología académica con referencias.
Si pide modo coloquial, usa analogías y ejemplos cotidianos.

Devuelve JSON con claves: diagnostico, dinamica_clave, implicaciones, recomendaciones (lista)."""

_TRANSLATOR_SYSTEM = """Eres un traductor bidireccional entre lenguaje coloquial y lenguaje técnico-científico
en el dominio de la dinámica social y simulación de sistemas complejos.

Para cada texto recibido:
1. Detecta automáticamente si es coloquial o técnico.
2. Traduce en la dirección opuesta.
3. Mantén el significado exacto, solo cambia el registro.

Devuelve JSON con:
  "original_registro": "coloquial" | "tecnico"
  "traduccion": str
  "terminos_mapeados": dict  (término original → término traducido)"""


# ── Modelos de respuesta ──────────────────────────────────────────────────────

class WizardResult(BaseModel):
    """Resultado del ScenarioWizardChain."""
    config: dict[str, Any] = Field(default_factory=dict)
    razon: str = ""
    advertencias: list[str] = Field(default_factory=list)
    confianza: float = 0.5

    def to_simular_kwargs(self) -> dict[str, Any]:
        """Filtra nulls y devuelve kwargs listos para simular()."""
        return {k: v for k, v in self.config.items() if v is not None}


class ExplainerResult(BaseModel):
    """Resultado del ConceptExplainerChain."""
    parametro: str = ""
    valor: Any = None
    explicacion_simple: str = ""
    explicacion_tecnica: str = ""
    efecto_simulacion: str = ""
    consejo_ajuste: str = ""
    rango_tipico: str = ""


class NarratorResult(BaseModel):
    """Resultado del ResultNarratorChain."""
    diagnostico: str = ""
    dinamica_clave: str = ""
    implicaciones: str = ""
    recomendaciones: list[str] = Field(default_factory=list)
    modo: str = "equilibrado"   # "coloquial", "tecnico", "equilibrado"


class TranslatorResult(BaseModel):
    """Resultado del BiTranslatorChain."""
    original_registro: str = ""
    traduccion: str = ""
    terminos_mapeados: dict[str, str] = Field(default_factory=dict)


# ── Clase principal ───────────────────────────────────────────────────────────

class InterpreterLayer:
    """
    Capa Intérprete Universal (UIL) de MASSIVE.

    Centraliza todas las interacciones LLM orientadas al usuario final:
    configuración asistida, explicación de conceptos, narración de resultados
    y extracción de parámetros desde documentos.

    Args:
        provider: Proveedor LLM ("groq", "openai", "openrouter", "ollama").
        api_key: Clave de API. Si vacío, se intenta desde variables de entorno.
        model: Modelo a usar. Si vacío, se usa el default del proveedor.
        use_langchain: Usar cadenas LangChain si está disponible.
        lang: Idioma de las respuestas ("es" o "en").
    """

    # Defaults por proveedor
    _PROVIDER_DEFAULTS: dict[str, dict] = {
        "groq":        {"model": "llama-3.3-70b-versatile", "base_url": None},
        "openai":      {"model": "gpt-4o-mini",             "base_url": None},
        "openrouter":  {"model": "mistralai/mistral-7b-instruct", "base_url": "https://openrouter.ai/api/v1"},
        "ollama":      {"model": "llama3",                  "base_url": "http://localhost:11434/v1"},
    }

    def __init__(
        self,
        provider: str = "groq",
        api_key: str = "",
        model: str = "",
        use_langchain: bool = True,
        lang: str = "es",
    ) -> None:
        self.provider = provider.lower()
        self.lang = lang
        self._use_langchain = use_langchain and _LC_AVAILABLE

        resolved_key = resolve_provider_api_key(provider, api_key)
        defaults = self._PROVIDER_DEFAULTS.get(self.provider, {})
        self.model = model or defaults.get("model", "llama3")

        # Construir cliente OpenAI-compatible
        try:
            from openai import OpenAI
            init_kwargs: dict[str, Any] = {"api_key": resolved_key or "ollama"}
            base_url = defaults.get("base_url")
            if base_url:
                init_kwargs["base_url"] = base_url
            if provider == "groq":
                try:
                    from groq import Groq
                    self._client = Groq(api_key=resolved_key)
                except ImportError:
                    init_kwargs["base_url"] = "https://api.groq.com/openai/v1"
                    self._client = OpenAI(**init_kwargs)
            else:
                self._client = OpenAI(**init_kwargs)
        except ImportError:
            log.warning("[UIL] openai no instalado. Funcionamiento limitado.")
            self._client = None

        # DocumentIntelligence integrado
        self.di = DocumentIntelligence(
            llm_client=self._client,
            model=self.model,
        )

        # LangChain chains (si disponible)
        self._chains: dict[str, Any] = {}
        if self._use_langchain:
            self._build_lc_chains()

        log.info(
            f"[UIL] Iniciado — provider={provider}, model={self.model}, "
            f"langchain={self._use_langchain}"
        )

    # ── Construcción de cadenas LangChain ────────────────────────────────────

    def _build_lc_chains(self) -> None:
        """Construye y cachea las cadenas LangChain."""
        try:
            if self.provider == "groq":
                from langchain_groq import ChatGroq
                llm = ChatGroq(model=self.model, temperature=0.1)
            elif self.provider == "openai":
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(model=self.model, temperature=0.1)
            else:
                from langchain_openai import ChatOpenAI
                defaults = self._PROVIDER_DEFAULTS.get(self.provider, {})
                llm = ChatOpenAI(
                    model=self.model,
                    temperature=0.1,
                    base_url=defaults.get("base_url", ""),
                )

            json_parser = JsonOutputParser()
            str_parser  = StrOutputParser()

            self._chains["wizard"] = (
                ChatPromptTemplate.from_messages([
                    ("system", _WIZARD_SYSTEM),
                    ("human",  "{scenario}"),
                ])
                | llm | json_parser
            )
            self._chains["explainer"] = (
                ChatPromptTemplate.from_messages([
                    ("system", _EXPLAINER_SYSTEM),
                    ("human",  "Parámetro: {param}\nValor actual: {value}\nContexto: {context}"),
                ])
                | llm | json_parser
            )
            self._chains["narrator"] = (
                ChatPromptTemplate.from_messages([
                    ("system", _NARRATOR_SYSTEM),
                    ("human",  "Modo: {mode}\n\nResultados:\n{results}"),
                ])
                | llm | json_parser
            )
            self._chains["translator"] = (
                ChatPromptTemplate.from_messages([
                    ("system", _TRANSLATOR_SYSTEM),
                    ("human",  "{text}"),
                ])
                | llm | json_parser
            )
            log.info("[UIL] Cadenas LangChain construidas correctamente.")
        except Exception as exc:
            log.warning(f"[UIL] No se pudieron construir cadenas LangChain: {exc}")
            self._use_langchain = False

    # ── Llamada LLM genérica (fallback sin LangChain) ─────────────────────────

    def _call_llm(
        self,
        system: str,
        user: str,
        temperature: float = 0.2,
        as_json: bool = True,
    ) -> Any:
        if self._client is None:
            raise RuntimeError("No hay cliente LLM configurado.")
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            temperature=temperature,
            max_tokens=1200,
        )
        content = resp.choices[0].message.content.strip()
        if as_json:
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            return json.loads(content)
        return content

    # ── API pública ───────────────────────────────────────────────────────────

    def wizard(self, scenario: str) -> WizardResult:
        """
        ScenarioWizardChain: descripción libre → configuración MASSIVE.

        Args:
            scenario: Descripción del escenario en lenguaje natural.

        Returns:
            WizardResult con config validada y razones del mapeo.

        Ejemplo::

            result = layer.wizard("hay mucha polarización, la gente no confía en el gobierno")
            kwargs = result.to_simular_kwargs()
            historial, _ = simular(**kwargs)
        """
        try:
            if self._use_langchain and "wizard" in self._chains:
                raw = self._chains["wizard"].invoke({"scenario": scenario})
            else:
                raw = self._call_llm(_WIZARD_SYSTEM, scenario)

            config = {k: v for k, v in raw.items()
                      if k not in ("razon", "advertencias", "confianza")}
            return WizardResult(
                config=config,
                razon=raw.get("razon", ""),
                advertencias=raw.get("advertencias", []),
                confianza=float(raw.get("confianza", 0.5)),
            )
        except Exception as exc:
            log.error(f"[UIL] wizard falló: {exc}")
            return WizardResult(advertencias=[f"Error: {exc}"])

    def explain(
        self,
        param: str,
        value: Any,
        context: str = "",
    ) -> ExplainerResult:
        """
        ConceptExplainerChain: explica un parámetro en lenguaje accesible.

        Args:
            param: Nombre del parámetro (ej: "sesgo_confirmacion").
            value: Valor actual del parámetro.
            context: Contexto adicional (opcional).

        Returns:
            ExplainerResult con explicación simple y técnica.
        """
        try:
            if self._use_langchain and "explainer" in self._chains:
                raw = self._chains["explainer"].invoke({
                    "param": param, "value": value, "context": context
                })
            else:
                raw = self._call_llm(
                    _EXPLAINER_SYSTEM,
                    f"Parámetro: {param}\nValor actual: {value}\nContexto: {context}",
                )
            return ExplainerResult(parametro=param, valor=value, **raw)
        except Exception as exc:
            log.error(f"[UIL] explain falló: {exc}")
            return ExplainerResult(
                parametro=param,
                valor=value,
                explicacion_simple=f"Error al explicar: {exc}",
            )

    def narrate(
        self,
        simulation_results: dict[str, Any],
        mode: str = "equilibrado",
    ) -> NarratorResult:
        """
        ResultNarratorChain: convierte resultados en síntesis narrativa.

        Args:
            simulation_results: Dict con opinión final, polarización, régimen
                dominante, historial, etc. (salida de simular() o resumen_historial()).
            mode: "coloquial", "tecnico" o "equilibrado".

        Returns:
            NarratorResult con diagnóstico, dinámica, implicaciones y recomendaciones.
        """
        results_text = json.dumps(simulation_results, ensure_ascii=False, indent=2)
        try:
            if self._use_langchain and "narrator" in self._chains:
                raw = self._chains["narrator"].invoke({
                    "mode": mode, "results": results_text
                })
            else:
                raw = self._call_llm(
                    _NARRATOR_SYSTEM,
                    f"Modo: {mode}\n\nResultados:\n{results_text}",
                )
            return NarratorResult(modo=mode, **raw)
        except Exception as exc:
            log.error(f"[UIL] narrate falló: {exc}")
            return NarratorResult(
                diagnostico=f"Error al generar narrativa: {exc}",
                modo=mode,
            )

    def translate(self, text: str) -> TranslatorResult:
        """
        BiTranslatorChain: convierte entre lenguaje coloquial y técnico.

        Args:
            text: Texto a traducir (se detecta automáticamente la dirección).

        Returns:
            TranslatorResult con traducción y mapa de términos.
        """
        try:
            if self._use_langchain and "translator" in self._chains:
                raw = self._chains["translator"].invoke({"text": text})
            else:
                raw = self._call_llm(_TRANSLATOR_SYSTEM, text)
            return TranslatorResult(**raw)
        except Exception as exc:
            log.error(f"[UIL] translate falló: {exc}")
            return TranslatorResult(traduccion=text)

    def from_document(
        self,
        ctx: DocumentContext,
        extra_instructions: str = "",
    ) -> MASSIVEExtractedConfig:
        """
        DocumentExtractionChain: extrae parámetros MASSIVE de un DocumentContext.

        Wrapper sobre DocumentIntelligence.extract_massive_params() que
        añade logging UIL y permite instrucciones adicionales contextuales.

        Args:
            ctx: DocumentContext ya parseado.
            extra_instructions: Instrucciones adicionales para la extracción.

        Returns:
            MASSIVEExtractedConfig validado.
        """
        log.info(f"[UIL] Extrayendo parámetros de: {ctx.filename}")
        result = self.di.extract_massive_params(ctx, extra_instructions)
        log.info(
            f"[UIL] Extracción completa — "
            f"confianza={result.confianza_extraccion:.2f}, "
            f"campos_inferidos={result.campos_inferidos}"
        )
        return result

    def full_pipeline(
        self,
        file_path: str | None = None,
        file_bytes: bytes | None = None,
        filename: str = "",
        scenario_text: str = "",
        extra_instructions: str = "",
    ) -> dict[str, Any]:
        """
        Pipeline completo: archivo + texto → parámetros MASSIVE fusionados.

        Si se proporcionan tanto archivo como texto, los parámetros del
        archivo tienen prioridad sobre los del wizard (el texto puede
        complementar o corregir).

        Returns:
            Dict con claves:
                "config"      → kwargs para simular()
                "doc_result"  → MASSIVEExtractedConfig (si hubo archivo)
                "wizard_result"→ WizardResult (si hubo texto)
                "warnings"    → lista de advertencias
        """
        warnings: list[str] = []
        merged_config: dict[str, Any] = {}
        doc_result   = None
        wizard_result = None

        # 1. Parsear archivo
        if file_path or file_bytes:
            if file_bytes and filename:
                ctx = self.di.parse_bytes(file_bytes, filename)
            elif file_path:
                ctx = self.di.parse_file(file_path)
            else:
                ctx = DocumentContext()

            warnings.extend(ctx.parse_warnings)
            doc_result = self.from_document(ctx, extra_instructions)
            merged_config.update(doc_result.to_simular_kwargs())

        # 2. Procesar texto libre
        if scenario_text.strip():
            wizard_result = self.wizard(scenario_text)
            warnings.extend(wizard_result.advertencias)
            # El texto complementa, no sobreescribe campos ya extraídos del archivo
            for k, v in wizard_result.to_simular_kwargs().items():
                if k not in merged_config:
                    merged_config[k] = v

        return {
            "config":        merged_config,
            "doc_result":    doc_result,
            "wizard_result": wizard_result,
            "warnings":      warnings,
        }

