"""Template narrator — deterministic natural-language translation of results.

When no LLM is configured this module produces the "reverse translation":
it converts a run's technical payload (summary, scientific report, series)
into readable prose in two audiences and two languages. When an LLM *is*
configured, ``routers/simulation.py`` may still prefer this narrator because
it can never hallucinate — it only states what the numbers say, plus the
explicit honesty disclaimer required by the PVU-BS philosophy.

Input is engine-agnostic: each engine adapter builds the same ``summary`` +
``series`` + ``meta`` structure, so this module stays engine-agnostic too.
"""

from __future__ import annotations

import math
from typing import Any

from backend.app.models.dto_ui import Highlight

# ── Plain-language meanings of regime rules ───────────────────────────────
_RULE_MEANING = {
    "lineal": {
        "es": "la opinión cambió de forma gradual y proporcional a la presión recibida",
        "en": "opinion shifted gradually, in proportion to the pressure applied",
    },
    "umbral": {
        "es": "la opinión saltó al cruzar un punto crítico: cambios pequeños acumulados hasta dispararse",
        "en": "opinion jumped once a critical point was crossed: small changes accumulated until they triggered a jump",
    },
    "memoria": {
        "es": "pesó la inercia: la opinión pasada frenó los cambios nuevos",
        "en": "inertia dominated: past opinion damped new changes",
    },
    "backlash": {
        "es": "la propaganda provocó el efecto contrario: reforzó la posición opuesta",
        "en": "propaganda backfired: it reinforced the opposite position",
    },
    "polarizacion": {
        "es": "las posiciones se alejaron del centro: la moderación perdió terreno",
        "en": "positions moved away from the center: moderation lost ground",
    },
    "hk": {
        "es": "la gente solo escuchó a quienes pensaban parecido: se formaron burbujas",
        "en": "people only listened to those who thought alike: bubbles formed",
    },
    "contagio_competitivo": {
        "es": "dos narrativas compitieron por la atención y una fue ganando terreno",
        "en": "two narratives competed for attention and one gained ground",
    },
    "umbral_heterogeneo": {
        "es": "distintas personas tenían distintos umbrales: el cambio se propagó como cascada",
        "en": "different people had different thresholds: change spread like a cascade",
    },
    "homofilia": {
        "es": "los lazos se reconfiguraron: la gente se acercó a quienes ya pensaban como ella",
        "en": "ties rewired themselves: people drifted toward those who already thought like them",
    },
    "replicador": {
        "es": "las estrategias más ventajosas se copiaron: dinámica evolutiva de juegos",
        "en": "the most advantageous strategies were copied: evolutionary game dynamics",
    },
    "nash": {
        "es": "los agentes se movieron hacia un equilibrio de Nash (estratégico)",
        "en": "agents moved toward a Nash equilibrium (strategic)",
    },
    "bayesiana": {
        "es": "los agentes actualizaron sus creencias con la evidencia disponible",
        "en": "agents updated their beliefs with the available evidence",
    },
    "sir": {
        "es": "la opinión se propagó como un contagio: susceptible → expuesto → adoptante",
        "en": "opinion spread like a contagion: susceptible → exposed → adopter",
    },
}

_STABILITY_MEANING = {
    "stable": {
        "es": "el punto final es estable: pequeñas perturbaciones volverían a él",
        "en": "the end state is stable: small perturbations would return to it",
    },
    "unstable": {
        "es": "el punto final es inestable: está cerca de un punto de quiebre",
        "en": "the end state is unstable: it sits near a tipping point",
    },
    "neutral": {
        "es": "la estabilidad es marginal: el sistema podría ir a cualquiera de los dos lados",
        "en": "stability is marginal: the system could go either way",
    },
}


def _fmt(x: float, digits: int = 2) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return "—"
    return f"{x:+.{digits}f}" if isinstance(x, (int, float)) else str(x)


def _neutral_value(meta: dict[str, Any]) -> float:
    return float(meta.get("neutro", 0.5))


def _direction(delta: float, neutro: float, lang: str) -> str:
    """Human description of the total change."""
    mag = abs(delta)
    if mag < 0.02:
        return "apenas cambió" if lang == "es" else "barely changed"
    verb = "subió" if delta > 0 else "bajó"
    verb_en = "rose" if delta > 0 else "fell"
    qual = "fuertemente" if mag > 0.35 else ("notablemente" if mag > 0.15 else "ligeramente")
    qual_en = "sharply" if mag > 0.35 else ("noticeably" if mag > 0.15 else "slightly")
    return f"{verb} {qual}" if lang == "es" else f"{qual_en} {verb_en}"


def _polarization_verdict(pol: float, lang: str) -> str:
    if pol is None:
        return ""
    if pol < 0.15:
        return (
            "la población quedó poco polarizada: las posiciones se mantuvieron cercanas al centro"
            if lang == "es"
            else "the population ended with low polarization: positions stayed near the center"
        )
    if pol < 0.35:
        return (
            "quedó una polarización moderada: hay bloques definidos pero no extremos"
            if lang == "es"
            else "moderate polarization remained: defined blocs, but nothing extreme"
        )
    return (
        "la polarización fue alta: la población terminó dividida en extremos"
        if lang == "es"
        else "polarization was high: the population ended split between extremes"
    )


def _ews_meaning(flags: dict[str, Any], lang: str) -> str:
    if not flags:
        return ""
    active = [k for k, v in flags.items() if v]
    if not active:
        return ""
    names = ", ".join(active)
    if lang == "es":
        return (
            f"Se detectaron señales tempranas de inestabilidad ({names}): "
            "varianza o autocorrelación crecientes. En sistemas sociales esto suele "
            "anteceder cambios abruptos de régimen (critical slowing down)."
        )
    return (
        f"Early warning signals fired ({names}): rising variance or autocorrelation. "
        "In social systems this often precedes abrupt regime shifts (critical slowing down)."
    )


def _engine_intro(engine: str, meta: dict[str, Any], lang: str) -> str:
    n = meta.get("n_agents")
    if engine == "scalar":
        return ""
    if engine == "energy" and lang == "es":
        return (
            f"Se simularon {n} agentes sobre un paisaje de energía social "
            "(dinámica de Langevin): cada agente se movió entre atractores, "
            "influencia de vecinos y ruido."
        )
    if engine == "energy":
        return (
            f"We simulated {n} agents over a social-energy landscape "
            "(Langevin dynamics): each agent moved between attractors, "
            "neighbor influence and noise."
        )
    if engine == "multilayer" and lang == "es":
        return (
            f"Se simularon {n} agentes en tres capas (social, digital, económica) "
            "con atributos sociodemográficos: opinión, cooperación, jerarquía, "
            "ingreso y acceso a información."
        )
    if engine == "multilayer":
        return (
            f"We simulated {n} agents across three layers (social, digital, economic) "
            "with sociodemographic attributes: opinion, cooperation, hierarchy, "
            "income and information access."
        )
    if engine == "massive" and lang == "es":
        m = meta.get("n_clusters", "?")
        saving = meta.get("memory_savings_pct")
        saving_txt = f" (con {saving:.0f}% de ahorro de RAM)" if saving else ""
        return (
            f"Se simuló una población de {n} agentes agrupada en {m} super-agentes"
            f"{saving_txt}: los agentes en consenso 'duermen' y solo se actualizan "
            "los activos (simulación dirigida por eventos)."
        )
    if engine == "massive":
        m = meta.get("n_clusters", "?")
        saving = meta.get("memory_savings_pct")
        saving_txt = f" (with {saving:.0f}% RAM savings)" if saving else ""
        return (
            f"We simulated a population of {n} agents grouped into {m} super-agents"
            f"{saving_txt}: agents in consensus 'sleep' and only active ones are "
            "updated (event-driven simulation)."
        )
    return ""


def _honesty_note(lang: str, mode: str) -> str:
    if lang == "es":
        note = (
            "Esto es una **simulación**, no una predicción empírica: los resultados "
            "dependen de los supuestos de entrada y del mecanismo elegido."
        )
        if mode == "heuristic":
            note += (
                " Además, esta corrida usó el modo heurístico (sin LLM). Para validar "
                "contra datos reales se requiere el protocolo PVU-BS."
            )
        return note
    note = (
        "This is a **simulation**, not an empirical prediction: results depend on "
        "the input assumptions and the chosen mechanism."
    )
    if mode == "heuristic":
        note += (
            " Additionally, this run used heuristic mode (no LLM). Validation against "
            "real data requires the PVU-BS protocol."
        )
    return note


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_narrative(
    *,
    engine: str,
    summary: dict[str, Any],
    scientific_report: dict[str, Any] | None,
    series: dict[str, Any] | None,
    meta: dict[str, Any] | None,
    language: str,
    audience: str,
    mode: str = "heuristic",
) -> tuple[str, list[Highlight]]:
    """Build the narrative text and highlights for one run.

    Args:
        engine: Engine name (scalar/energy/multilayer/massive).
        summary: Engine summary dict (see each router adapter).
        scientific_report: Optional ScientificReport dict.
        series: Optional series dict (opinion trajectory, rules…).
        meta: Engine metadata (n_agents, memory savings, neutro…).
        language: "es" or "en".
        audience: "general" or "tecnico".
        mode: "llm" or "heuristic" (affects the honesty note).

    Returns:
        (narrative_markdown, highlights_list)
    """
    meta = meta or {}
    summary = summary or {}
    lang = language if language in ("es", "en") else "es"
    tech = audience == "tecnico"
    t = _T[lang]

    opin_ini = summary.get("opinion_inicial")
    opin_fin = summary.get("opinion_final")
    delta = summary.get("delta_total")
    if delta is None and opin_ini is not None and opin_fin is not None:
        delta = opin_fin - opin_ini
    pol = summary.get("polarizacion_media") or summary.get("polarization")
    rule = summary.get("regla_dominante")
    stab = (scientific_report or {}).get("stability_label")
    flags = (scientific_report or {}).get("ews_flags") or {}
    neutro = _neutral_value(meta)

    lines: list[str] = []

    # ── 1. Opening: what happened ─────────────────────────────────────────
    lines.append(f"## {t['what_happened']}")
    intro = _engine_intro(engine, meta, lang)
    if intro:
        lines.append(intro + "\n")
    if opin_ini is not None and opin_fin is not None:
        if lang == "es":
            lines.append(
                f"La opinión partió de **{_fmt(opin_ini)}** y terminó en **{_fmt(opin_fin)}** "
                f"(neutro = {_fmt(neutro, 1)}): {_direction(delta, neutro, lang)} "
                f"un total de **{_fmt(delta)}**."
            )
        else:
            lines.append(
                f"Opinion started at **{_fmt(opin_ini)}** and ended at **{_fmt(opin_fin)}** "
                f"(neutral = {_fmt(neutro, 1)}): it {_direction(delta, neutro, lang)} "
                f"by **{_fmt(delta)}** overall."
            )
        lines.append("")

    # ── 2. Why: dominant mechanism (causal chain) ─────────────────────────
    if rule:
        meaning = _RULE_MEANING.get(rule, {}).get(lang, "")
        if lang == "es":
            lines.append(f"## {t['why']}")
            lines.append(
                f"El mecanismo dominante fue **{rule}**"
                + (f": {meaning}." if meaning else ".")
                + " Es la fuerza que más moldeó la trayectoria durante la corrida."
            )
        else:
            lines.append(f"## {t['why']}")
            lines.append(
                f"The dominant mechanism was **{rule}**"
                + (f": {meaning}." if meaning else ".")
                + " It is the force that most shaped the trajectory during the run."
            )
        lines.append("")
        # Rule timeline support from series.
        if series and series.get("regla_nombre"):
            from collections import Counter

            rules = [r for r in series["regla_nombre"] if r]
            counts = Counter(rules)
            top = counts.most_common(3)
            if lang == "es":
                parts = "; ".join(f"{name} ({n} pasos)" for name, n in top)
                lines.append(f"Secuencia de regímenes aplicados: {parts}.")
            else:
                parts = "; ".join(f"{name} ({n} steps)" for name, n in top)
                lines.append(f"Applied regime sequence: {parts}.")
            lines.append("")

    # ── 3. Polarization ───────────────────────────────────────────────────
    if pol is not None:
        verdict = _polarization_verdict(pol, lang)
        if verdict:
            lines.append(f"- {verdict}." if lang == "es" else f"- {verdict}.")
            if tech:
                lines.append(
                    f"- Polarización media (|op − neutro|): **{_fmt(pol)}**."
                    if lang == "es"
                    else f"- Mean polarization (|op − neutral|): **{_fmt(pol)}**."
                )
            lines.append("")

    # ── 4. Stability / EWS (scientific layer) ─────────────────────────────
    if stab:
        meaning = _STABILITY_MEANING.get(stab, {}).get(lang, "")
        lines.append(f"## {t['stability']}")
        if tech and (scientific_report or {}).get("max_real_eigenvalue") is not None:
            ev = scientific_report["max_real_eigenvalue"]
            lines.append(
                f"Etiqueta: **{stab}** (eigenvalor real máximo {_fmt(ev, 3)}){f' — {meaning}' if meaning else ''}."
                if lang == "es"
                else f"Label: **{stab}** (max real eigenvalue {_fmt(ev, 3)}){f' — {meaning}' if meaning else ''}."
            )
        else:
            lines.append(f"Estado: **{stab}**{f' — {meaning}' if meaning else ''}.")
        lines.append("")
    ews = _ews_meaning(flags, lang)
    if ews:
        lines.append(f"⚠️ {ews}")
        lines.append("")

    # ── 5. Scale facts (non-scalar engines) ───────────────────────────────
    extras: list[str] = []
    if engine == "massive" and meta.get("memory_savings_pct"):
        s = meta["memory_savings_pct"]
        extras.append(
            f"Ahorro de RAM vs. float64: **{s:.1f}%** (estado cuantizado + super-agentes)."
            if lang == "es"
            else f"RAM savings vs. float64: **{s:.1f}%** (quantized state + super-agents)."
        )
        if meta.get("steps_per_second"):
            extras.append(
                f"Rendimiento: **{meta['steps_per_second']:,.0f}** pasos/segundo."
                if lang == "es"
                else f"Throughput: **{meta['steps_per_second']:,.0f}** steps/second."
            )
    if engine == "massive" and meta.get("active_history"):
        act = meta["active_history"]
        frac = act[-1] if act else 1.0
        extras.append(
            f"Fracción activa al final: **{frac * 100:.0f}%** de los super-agentes."
            if lang == "es"
            else f"Active fraction at the end: **{frac * 100:.0f}%** of super-agents."
        )
    if extras:
        lines.append(f"## {t['scale']}")
        for e in extras:
            lines.append(f"- {e}")
        lines.append("")

    # ── 6. Honesty note ───────────────────────────────────────────────────
    lines.append("---")
    lines.append(_honesty_note(lang, mode))

    narrative = "\n".join(lines)

    # ── Highlights (compact cards for the UI) ─────────────────────────────
    highlights: list[Highlight] = []
    if opin_fin is not None:
        highlights.append(
            Highlight(
                label=t["opinion_final"],
                value=_fmt(opin_fin),
                meaning=(
                    f"respecto al neutro {_fmt(neutro, 1)}"
                    if lang == "es"
                    else f"relative to neutral {_fmt(neutro, 1)}"
                ),
            )
        )
    if delta is not None:
        highlights.append(
            Highlight(
                label=t["change"],
                value=_fmt(delta),
                meaning=(_direction(delta, neutro, lang)),
            )
        )
    if pol is not None:
        highlights.append(
            Highlight(
                label=t["polarization"],
                value=_fmt(pol),
                meaning=_polarization_verdict(pol, lang),
            )
        )
    if rule:
        meaning = _RULE_MEANING.get(rule, {}).get(lang, "")
        highlights.append(
            Highlight(
                label=t["mechanism"],
                value=rule,
                meaning=meaning,
            )
        )
    if stab:
        highlights.append(
            Highlight(
                label=t["stability_label"],
                value=stab,
                meaning=_STABILITY_MEANING.get(stab, {}).get(lang, ""),
            )
        )

    return narrative, highlights


# ── UI strings ─────────────────────────────────────────────────────────────
_T = {
    "es": {
        "what_happened": "¿Qué pasó?",
        "why": "¿Por qué pasó?",
        "stability": "Estabilidad",
        "scale": "Escala y rendimiento",
        "opinion_final": "Opinión final",
        "change": "Cambio total",
        "polarization": "Polarización",
        "mechanism": "Mecanismo dominante",
        "stability_label": "Estabilidad",
    },
    "en": {
        "what_happened": "What happened?",
        "why": "Why did it happen?",
        "stability": "Stability",
        "scale": "Scale & performance",
        "opinion_final": "Final opinion",
        "change": "Total change",
        "polarization": "Polarization",
        "mechanism": "Dominant mechanism",
        "stability_label": "Stability",
    },
}
