"""
energy_runner.py — Orquestador de simulaciones Langevin para MASSIVE
Conecta: ProgrammaticArchitect → EnergyConfig → SocialEnergyEngine
Devuelve historial y métricas compatibles con simulator.py y Streamlit.
"""
import numpy as np
from typing import Optional
from energy_engine import SocialEnergyEngine, random_network
from programmatic_architect import ProgrammaticArchitect
from energy_schemas import EnergyConfig


def run_energy_simulation(
    user_goal: str,
    n_agents: int = 50,
    steps: int = 100,
    connectivity: float = 0.3,
    range_type: str = "bipolar",
    seed: int = 42,
    llm_client=None,
    config_overrides: dict = None,
    metrics_every_n: int = 1,
) -> dict:
    if n_agents < 2 or steps < 1:
        raise ValueError("n_agents debe ser >= 2 y steps >= 1")

    architect = ProgrammaticArchitect(range_type=range_type, llm_client=llm_client)
    landscape = architect.get_landscape(user_goal)

    validated = EnergyConfig.model_validate(landscape)
    params = validated.to_engine_dict()

    if config_overrides:
        dyn = params["dynamics"]
        if "temperature" in config_overrides:
            dyn["temperature"] = float(np.clip(config_overrides["temperature"], 0.01, 0.20))
        if "lambda_social" in config_overrides:
            dyn["lambda_social"] = float(np.clip(config_overrides["lambda_social"], 0.0, 1.0))
        if "eta" in config_overrides:
            dyn["eta"] = float(np.clip(config_overrides["eta"], 0.001, 0.1))

    engine = SocialEnergyEngine(
        range_type=range_type,
        temperature=params["dynamics"]["temperature"],
        lambda_social=params["dynamics"]["lambda_social"]
    )
    eta = params["dynamics"]["eta"]
    adj = random_network(n_agents, connectivity=connectivity, seed=seed)

    min_val, max_val = (0.0, 1.0) if range_type == "unipolar" else (-1.0, 1.0)
    rng = np.random.default_rng(seed)
    np.random.seed(seed)  # seed global RNG for Langevin noise in engine.step()
    opinions = rng.uniform(min_val, max_val, size=n_agents)

    history = []
    metrics_timeline = []

    for t in range(steps + 1):
        history.append({
            "_paso": t,
            "mean_opinion": float(np.mean(opinions)),
            "std_opinion": float(np.std(opinions)),
            "opinions_snapshot": opinions.tolist() if t % 10 == 0 or t == steps else None
        })

        if t % metrics_every_n == 0:
            mets = engine.system_metrics(opinions, adj, params["attractors"], params["repellers"])
            mets["_paso"] = t
            metrics_timeline.append(mets)

        if t < steps:
            opinions = engine.step(opinions, adj, params["attractors"], params["repellers"], eta=eta)

    initial_op = history[0]["mean_opinion"]
    final_op   = history[-1]["mean_opinion"]
    delta      = final_op - initial_op
    neutro     = 0.0 if range_type == "bipolar" else 0.5
    all_means  = [h["mean_opinion"] for h in history]
    all_polar  = [m["polarizacion"] for m in metrics_timeline] if metrics_timeline else [0.0]

    return {
        "history": history,
        "metrics_timeline": metrics_timeline,
        "final_state": {
            "opinions": opinions.tolist(),
            "mean_opinion": final_op,
            "std_opinion": float(np.std(opinions))
        },
        "summary": {
            "opinion_inicial": initial_op,
            "opinion_final": final_op,
            "delta_total": delta,
            "media": float(np.mean(all_means)),
            "desviacion": float(np.std(all_means)),
            "polarizacion_media": float(np.mean(all_polar)),
            "pasos": steps,
            "regla_dominante": "langevin_energy",
            "neutro": neutro,
            "rango": f"[{min_val}, {max_val}]"
        },
        "config_used": validated.model_dump(),
        "archetype_info": landscape.get("metadata", {})
    }
