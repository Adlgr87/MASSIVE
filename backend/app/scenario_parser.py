"""Deterministic scenario interpreter (heuristic translator fallback).

When no LLM provider is configured, this module performs the same job as the
LLM translator with keyword matching: it reads a free-text description and
produces a structured ``ConversationResponse`` — a config draft, explicit
assumptions and follow-up questions — so the UI flow is identical with or
without an API key.

Nothing here is scientific inference; it is a transparent, conservative
mapping from common scenario vocabulary to MASSIVE parameters, and every
assumption is reported as an assumption.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from backend.app.models.dto_ui import (
    AssumptionItem,
    ChatMessage,
    ConversationResponse,
)

log = logging.getLogger("massive.ui_ng.scenario_parser")

# ── Country mentions (natural language → CIA Factbook code) ──────────────
_COUNTRIES: dict[str, tuple[str, str]] = {
    # regex fragment → (code, label)
    r"\bestados unidos\b|\bee\.?uu\.?\b|\busa\b|\bunited states\b": ("US", "Estados Unidos"),
    r"\bm[eé]xico\b|\bmexico\b": ("MX", "México"),
    r"\bespa[ñn]a\b|\bspain\b": ("ES", "España"),
    r"\bargentina\b": ("AR", "Argentina"),
    r"\bcolombia\b": ("CO", "Colombia"),
    r"\bchile\b": ("CL", "Chile"),
    r"\bbrasil\b|\bbrazil\b": ("BR", "Brasil"),
    r"\balemania\b|\bgermany\b": ("DE", "Alemania"),
    r"\bchina\b": ("CN", "China"),
    r"\bfrancia\b|\bfrance\b": ("FR", "Francia"),
    r"\breino unido\b|\buk\b|\bunited kingdom\b": ("UK", "Reino Unido"),
    r"\bcanad[aá]\b|\bcanada\b": ("CA", "Canadá"),
    r"\bper[uú]\b": ("PE", "Perú"),
    r"\bvenezuela\b": ("VE", "Venezuela"),
    r"\becuador\b": ("EC", "Ecuador"),
}

# ── Keyword groups (lowercased text is matched) ───────────────────────────
_KEYWORDS = {
    "polarizacion": [
        r"polariz", r"divisi[oó]n", r"extremos", r"radicaliz",
        r"c[aá]maras? de eco", r"echo chamber", r"polariz", r"grieta",
        r"partidismo", r"facciones", r"bandos",
    ],
    "campana": [
        r"campa[ñn]a", r"propaganda", r"publicidad", r"marketing",
        r"difusi[oó]n", r"desinformaci", r"fake news", r"noticias falsas",
        r"campaign", r"advertis", r"bombardeo medi[aá]tico",
    ],
    "desconfianza": [
        r"desconf[ií]an", r"desconf[ií]a", r"descr[eé]dit",
        r"instituciones (desacreditadas|d[eé]biles|en crisis)", r"corrupci",
        r"crisis de confianza", r"distrust", r"mistrust", r"trust in",
        r"p[eé]rdida de confianza",
    ],
    "elecciones": [
        r"elecci[oó]n", r"electoral", r"votaci[oó]n", r"votantes",
        r"candidat", r"election", r"vote", r"ballot", r"urna",
    ],
    "crisis": [
        r"crisis", r"protesta", r"manifestaci", r"disturbio", r"estallido",
        r"huelga", r"emergencia", r"esc[aá]ndalo", r"protest", r"riot",
        r"unrest", r"scandal",
    ],
    "corporativo": [
        r"empresa", r"corporativ", r"empleados", r"equipo de trabajo",
        r"organizaci", r"rrhh", r"recursos humanos", r"cultura organiz",
        r"company", r"workplace", r"employees", r"hr ",
    ],
    "red_social": [
        r"redes sociales", r"twitter", r"\bx\b(?: la red)?", r"tiktok",
        r"facebook", r"instagram", r"whatsapp", r"viral", r"social media",
    ],
    "rechazo": [
        r"rechazo", r"oposici[oó]n", r"en contra", r"antipat", r"boicot",
        r"rejection", r"opposition", r"against",
    ],
    "grupos": [
        r"grupos", r"comunidades", r"barrios", r"j[oó]venes", r"adultos",
        r"generaciones", r"religios", r"[eé]tnic", r"ind[ií]genas",
        r"group", r"communit",
    ],
    "confianza_alta": [
        r"conf[ií]an", r"conf[ií]a", r"credibilidad", r"legitim", r"transparen",
        r"high trust", r"confidence in",
    ],
    "incertidumbre": [
        r"incertidumbre", r"vol[aá]til", r"impredecible", r"cambiante",
        r"uncertain", r"volatile", r"unpredictable",
    ],
}

# ── Rule/mechanism mentions → preferred regime hint ───────────────────────
_RULE_HINTS = {
    "hk": [r"\bhk\b", r"confianza acotada", r"bounded confidence",
           r"solo escuchan a", r"mismos c[ií]rculos"],
    "backlash": [r"backlash", r"efecto rebote", r"reactancia", r"reacci[oó]n adversa",
                 r"boomerang", r"contraproducente", r"rechazan la propaganda"],
    "replicador": [r"teor[ií]a de juegos", r"replicador", r"evolutionary game",
                   r"estrategias", r"juego de la", r"dilema del prisionero",
                   r"payoff", r"game theory"],
    "sir": [r"\bsir\b", r"epid[eé]mi", r"adopci[oó]n viral", r"contagi", r"spread"],
    "umbral": [r"umbral", r"tipping point", r"punto de quiebre", r"granovetter",
               r"cascada", r"threshold", r"masa cr[ií]tica"],
    "homofilia": [r"homofil", r"afines", r"se juntan con", r"homophily"],
}


def _detect_language(text: str) -> str:
    es_markers = [
        "polarización", "polarizacion", "desconfianza", "campaña", "campaña",
        "elecciones", "instituciones", "gobierno", "ciudad", "país", "pais",
        "personas", "gente", "qué", "que ", "¿",
    ]
    hits = sum(1 for m in es_markers if m in text.lower())
    return "es" if hits >= 1 else "en"


def _find_country(text: str) -> tuple[str, str] | None:
    low = text.lower()
    for pattern, (code, label) in _COUNTRIES.items():
        if re.search(pattern, low):
            return code, label
    return None


def _match_groups(text_low: str) -> dict[str, bool]:
    found: dict[str, bool] = {}
    for group, patterns in _KEYWORDS.items():
        found[group] = any(re.search(p, text_low) for p in patterns)
    return found


def _parse_number(text: str, patterns: list[str]) -> float | None:
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1))
            except ValueError:
                return None
    return None


def interpret(
    description: str,
    *,
    language: str | None = None,
) -> ConversationResponse:
    """Interpret a free-text scenario into a structured assistant turn.

    Args:
        description: User's scenario description.
        language: Override language detection ("es"/"en").

    Returns:
        Structured ConversationResponse with draft, assumptions and questions.
    """
    lang = language or _detect_language(description)
    text_low = description.lower()
    groups = _match_groups(text_low)

    assumptions: list[AssumptionItem] = []
    questions: list[str] = []
    config: dict[str, Any] = {}
    estado: dict[str, Any] = {"opinion": 0.5, "propaganda": 0.6, "confianza": 0.5}

    # ── Percentages / numbers → initial opinion & propaganda ─────────────
    pct = _parse_number(
        description, [r"(\d{1,3})\s*%", r"(\d{1,2}(?:\.\d+)?)\s*por ciento",
                      r"(\d{1,3})\s*percent"]
    )
    if pct is not None:
        val = max(0.0, min(100.0, pct)) / 100.0
        if groups["rechazo"]:
            # percentage expressed as active rejection → bipolar range
            estado["opinion"] = round(-val, 3)
            config["rango"] = "[-1, 1] — Bipolar"
            assumptions.append(AssumptionItem(
                parameter="opinion_inicial",
                value=f"{pct:g}% de rechazo activo → {estado['opinion']:+.2f} (bipolar)",
                reason="interpreté el porcentaje como rechazo activo y usé el rango bipolar [-1,1]",
                confidence=0.55,
            ))
        else:
            estado["opinion"] = round(val, 3)
            assumptions.append(AssumptionItem(
                parameter="opinion_inicial",
                value=f"{pct:g}% → {estado['opinion']:.2f} en [0,1]",
                reason="tomé el porcentaje mencionado como apoyo inicial a la posición",
                confidence=0.6,
            ))
    else:
        assumptions.append(AssumptionItem(
            parameter="opinion_inicial",
            value="0.50 (neutro)",
            reason="no mencionaste un punto de partida; asumí una opinión neutra",
            confidence=0.5,
        ))

    # ── Propaganda / campaign intensity ─────────────────────────────────
    if groups["campana"]:
        fuerte = bool(re.search(r"agresiv|intens|masiv|fuerte|fuerte|heavy|strong|massive", text_low))
        estado["propaganda"] = 0.85 if fuerte else 0.7
        assumptions.append(AssumptionItem(
            parameter="propaganda",
            value=str(estado["propaganda"]),
            reason="hay una campaña activa" + (" descrita como agresiva/intensa" if fuerte else ""),
            confidence=0.65,
        ))
    else:
        estado["propaganda"] = 0.3
        assumptions.append(AssumptionItem(
            parameter="propaganda",
            value="0.30",
            reason="no describiste campaña activa; asumí presión propagandística baja",
            confidence=0.5,
        ))

    # ── Institutional trust ──────────────────────────────────────────────
    if groups["desconfianza"]:
        estado["confianza"] = 0.25
        config["ruido_desconfianza"] = 0.12
        assumptions.append(AssumptionItem(
            parameter="confianza",
            value="0.25",
            reason="mencionas desconfianza institucional → mayor volatilidad por ruido adaptativo",
            confidence=0.7,
        ))
    elif groups["confianza_alta"]:
        estado["confianza"] = 0.75
        assumptions.append(AssumptionItem(
            parameter="confianza",
            value="0.75",
            reason="describes confianza alta → la dinámica será más estable (menos ruido)",
            confidence=0.6,
        ))
    else:
        assumptions.append(AssumptionItem(
            parameter="confianza",
            value="0.50",
            reason="no especificaste confianza institucional; asumí nivel medio",
            confidence=0.5,
        ))

    # ── Range: bipolar vs unipolar (never overwrite an earlier decision) ──
    if "rango" not in config:
        if groups["rechazo"]:
            config["rango"] = "[-1, 1] — Bipolar"
            assumptions.append(AssumptionItem(
                parameter="rango",
                value="[-1, 1] Bipolar",
                reason="hay rechazo activo en juego: el rango bipolar distingue oposición activa de indiferencia",
                confidence=0.65,
            ))
        else:
            config["rango"] = "[0, 1] — Probabilístico"
            assumptions.append(AssumptionItem(
                parameter="rango",
                value="[0, 1] Probabilístico",
                reason="sin mención de rechazo activo, usé el rango probabilístico por defecto",
                confidence=0.55,
            ))

    # ── Group dynamics ───────────────────────────────────────────────────
    if groups["grupos"]:
        estado.setdefault("opinion_grupo_a", 0.68)
        estado.setdefault("opinion_grupo_b", 0.32)
        config["efecto_vecinos_peso"] = 0.12
        assumptions.append(AssumptionItem(
            parameter="efecto_vecinos_peso",
            value="0.12 (↑ del default 0.05)",
            reason="mencionas grupos/comunidades → aumenté el peso de la influencia grupal",
            confidence=0.6,
        ))
        questions.append(
            "¿Los grupos que mencionas tienen posiciones opuestas entre sí o solo niveles distintos de apoyo?"
            if lang == "es" else
            "Do the groups you mention hold opposing positions, or just different levels of support?",
        )

    # ── Polarization & echo chambers ─────────────────────────────────────
    if groups["polarizacion"]:
        config["sesgo_confirmacion"] = 0.6
        config["hk_epsilon"] = 0.2
        assumptions.append(AssumptionItem(
            parameter="sesgo_confirmacion",
            value="0.6 (↑ del default 0.3)",
            reason="escenario polarizado: la propaganda contraria pierde peso (cámaras de eco)",
            confidence=0.65,
        ))
        assumptions.append(AssumptionItem(
            parameter="hk_epsilon",
            value="0.20 (↓ del default 0.30)",
            reason="con menos confianza acotada, los grupos se escuchan menos entre sí",
            confidence=0.55,
        ))

    # ── Backlash mechanism ───────────────────────────────────────────────
    if groups["campana"] and groups["rechazo"]:
        config["modelo_matematico"] = "backlash"
        assumptions.append(AssumptionItem(
            parameter="modelo_matematico",
            value="backlash",
            reason="campaña + rechazo: la propaganda puede reforzar la posición contraria",
            confidence=0.5,
        ))

    # ── Explicit mechanism mentions ──────────────────────────────────────
    for rule, patterns in _RULE_HINTS.items():
        if any(re.search(p, text_low) for p in patterns):
            config["modelo_matematico"] = rule
            assumptions.append(AssumptionItem(
                parameter="modelo_matematico",
                value=rule,
                reason=f"mencionaste un mecanismo compatible con la regla '{rule}'",
                confidence=0.6,
            ))
            break

    # ── Scenario / steps ─────────────────────────────────────────────────
    if groups["elecciones"]:
        escenario = "campana"
        pasos = 90
        assumptions.append(AssumptionItem(
            parameter="pasos",
            value="90",
            reason="contexto electoral: usé un horizonte más largo (ciclo de campaña)",
            confidence=0.5,
        ))
    elif groups["crisis"]:
        escenario = "campana"
        pasos = 40
        assumptions.append(AssumptionItem(
            parameter="pasos",
            value="40",
            reason="contexto de crisis: horizontes cortos capturan mejor cambios abruptos",
            confidence=0.5,
        ))
    else:
        escenario = "campana"
        pasos = 60
        assumptions.append(AssumptionItem(
            parameter="pasos",
            value="60",
            reason="no diste horizonte temporal; usé 60 pasos como valor medio",
            confidence=0.45,
        ))

    # ── Country → Factbook integration note ──────────────────────────────
    country = _find_country(description)
    if country:
        config["factbook_country"] = country[0]
        assumptions.append(AssumptionItem(
            parameter="factbook_country",
            value=f"{country[0]} ({country[1]})",
            reason=f"mencionaste {country[1]}: puedo calibrar con datos reales del World Factbook "
                   "(demografía, Gini, diversidad) si lo confirmas",
            confidence=0.75,
        ))
        if lang == "es":
            questions.append(
                f"¿Quieres que calibre la simulación con datos reales de {country[1]} "
                f"(población, índice de Gini, diversidad étnica/religiosa del World Factbook)?"
            )
        else:
            questions.append(
                f"Do you want me to calibrate the simulation with real {country[1]} data "
                f"(population, Gini index, ethnic/religious diversity from the World Factbook)?"
            )

    # ── Follow-up questions (max 3) ──────────────────────────────────────
    if lang == "es":
        if not groups["rechazo"] and not groups["campana"]:
            questions.append("¿Quién impulsa el cambio de opinión: una campaña, un evento, o la conversación entre personas?")
        if pct is None:
            questions.append("Si conoces el apoyo actual aproximado (%), dímelo y lo usaré como punto de partida.")
        questions.append("¿En qué plazo te interesa el resultado: semanas, meses o un ciclo electoral completo?")
    else:
        if not groups["rechazo"] and not groups["campana"]:
            questions.append("What is driving opinion change: a campaign, an event, or people talking to each other?")
        if pct is None:
            questions.append("If you know the current support level (%), tell me and I will use it as the starting point.")
        questions.append("What time horizon matters to you: weeks, months, or a full election cycle?")
    questions = questions[:3]

    # ── Compose reply ────────────────────────────────────────────────────
    mechanism = config.get("modelo_matematico")
    if lang == "es":
        reply_parts = ["Interpreté tu escenario y preparé un borrador de simulación."]
        if groups["campana"] and groups["desconfianza"]:
            reply_parts.append(
                "Veo una campaña activa sobre una población desconfiada: es un escenario "
                "donde el efecto rebote (backlash) es probable, así que lo dejé como mecanismo candidato."
            )
        if groups["polarizacion"]:
            reply_parts.append("Como hay señales de polarización, subí el sesgo de confirmación.")
        if mechanism:
            reply_parts.append(f"Mecanismo propuesto: {mechanism}.")
        reply_parts.append(
            "Abajo están los supuestos que hice (puedes editarlos) y algunas preguntas "
            "que mejorarían la precisión. Cuando estés listo, pulsa 'Ejecutar simulación'."
        )
        reply = " ".join(reply_parts)
    else:
        reply_parts = ["I interpreted your scenario and prepared a simulation draft."]
        if groups["campana"] and groups["desconfianza"]:
            reply_parts.append(
                "I see an active campaign over a distrustful population — a scenario where "
                "backlash is likely, so I left it as a candidate mechanism."
            )
        if groups["polarizacion"]:
            reply_parts.append("Because there are polarization signals, I raised the confirmation bias.")
        if mechanism:
            reply_parts.append(f"Proposed mechanism: {mechanism}.")
        reply_parts.append(
            "Below are the assumptions I made (editable) and a few questions that would improve "
            "accuracy. When ready, hit 'Run simulation'."
        )
        reply = " ".join(reply_parts)

    return ConversationResponse(
        reply=reply,
        action="propose",
        assumptions=assumptions,
        questions=questions,
        config_draft={
            "estado_inicial": estado,
            "escenario": escenario,
            "pasos": pasos,
            "config": config,
        },
        mode="heuristic",
    )


def interpret_turn(messages: list[ChatMessage], language: str) -> ConversationResponse:
    """Interpret the last user message, aware of the conversation so far.

    This fallback keeps the same shape as the LLM path. Refinements like
    "make distrust higher" are handled with light patch heuristics.
    """
    user_msgs = [m for m in messages if m.role == "user"]
    if not user_msgs:
        return interpret("", language=language)
    description = user_msgs[-1].content
    if not description.strip():
        return interpret("", language=language)

    low = description.lower()
    # Simple refinement: numbers like "sube X" / "baja Y" / percentages.
    if re.search(r"\d+(\.\d+)?", low):
        pass  # interpret() already handles percentages.

    return interpret(description, language=language)
