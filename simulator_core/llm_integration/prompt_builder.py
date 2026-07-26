"""
Prompt builder for LLM rule selector.
"""

import json
from typing import Dict, List


def construir_prompt(estado: dict, escenario: str,
                     historial_reciente: list[dict], cfg: dict) -> str:
    """
    Constructs the prompt for the LLM selector.

    Args:
        estado: Current state of the simulation.
        escenario: The current simulation scenario.
        historial_reciente: Last N steps of history.
        cfg: Global configuration.

    Returns:
        The formatted prompt string.
    """
    from simulator_core.config import _es_bipolar, _amplitud

    es_bipolar = _es_bipolar(cfg)
    tendencia  = [round(h["opinion"], 3) for h in historial_reciente]
    delta      = round(tendencia[-1] - tendencia[0], 3) if len(tendencia) > 1 else 0.0
    direccion  = "rising" if delta > 0.02 else ("falling" if delta < -0.02 else "stable")

    estado_fmt = {
        k: round(v, 3) if isinstance(v, float) else v
        for k, v in estado.items() if not k.startswith("_")
    }

    rango_desc = (
        "[-1, 1]: 0=neutral, negative=active rejection, positive=support"
        if es_bipolar else
        "[0, 1]: 0.5=neutral, 0=total rejection, 1=total support"
    )

    ejemplos = """
Decision Examples:
- opinion near neutral, low propaganda, stable system → memoria
- intense propaganda crosses threshold, system moves → umbral
- groups very distant from each other → hk (bounded confidence)
- established rejection + active propaganda → backlash
- two active and tense narratives → contagio_competitivo
- strong trend already started → polarizacion
- social cascade effect desired → umbral_heterogeneo
- groups tend to cluster by similarity → homofilia
- evolutionary pressure between group strategies → replicador
- groups converging, coordination equilibrium → nash
- probabilistic belief update with evidence → bayesiano
- epidemic-like opinion spread → sir"""

    base_prompt = f"""You are a rule selector for a social dynamics simulation.
Scenario: {escenario} | Range: {rango_desc}

State:
{json.dumps(estado_fmt, ensure_ascii=False)}

Opinion Trend (last {len(tendencia)} steps): {tendencia}
Direction: {direccion} (Δ={delta:+.3f})
{ejemplos}

Available Rules:
0: lineal               — smooth proportional change
1: umbral               — jump when crossing critical point
2: memoria              — past state inertia
3: backlash             — propaganda reinforces opposite position
4: polarizacion         — moves away from neutral (echo chamber)
5: hk                   — bounded confidence, only listen to similar ones
6: contagio_competitivo — two narratives compete simultaneously
7: umbral_heterogeneo   — social cascades (Granovetter)
8: homofilia            — co-evolutionary network, groups by similarity
9: replicador           — evolutionary game theory, strategy frequencies
10: nash               — Nash equilibrium, stable coordination strategies
11: bayesiano          — Bayesian network, probabilistic belief update
12: sir                — SIR epidemiological contagion

Respond ONLY with JSON:
{{"regla": <0-12>, "params": {{...}}, "razon": "<explanation>"}}
Fallback: {{"regla": 0, "params": {{}}, "razon": "fallback"}}
"""

    ews_flags = estado.get("_ews_flags", {})
    ews_context = ""
    if ews_flags:
        ews_context = (
            f"\n[EWS] high_variance={ews_flags.get('high_variance', False)}, "
            f"high_autocorr={ews_flags.get('high_autocorr', False)}, "
            f"high_skewness={ews_flags.get('high_skewness', False)}. "
            "These indicate proximity to a bifurcation tipping point "
            "(B-tipping via Critical Slowing Down)."
        )
    return base_prompt + ews_context
