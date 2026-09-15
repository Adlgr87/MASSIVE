"""
energy_runner.py — Orquestador de simulaciones Langevin para MASSIVE
Conecta: ProgrammaticArchitect → EnergyConfig → SocialEnergyEngine
Devuelve historial y métricas compatibles con simulator.py y la UI-NG (consumida vía API del backend).
"""

import numpy as np

from energy_engine import SocialEnergyEngine, random_network
from energy_schemas import EnergyConfig
from programmatic_architect import ProgrammaticArchitect
from simulator import calculate_ews_metrics, check_ews_signals


def run_energy_simulation(
    user_goal: str,
    n_agents: int = 50,
    steps: int = 100,
    connectivity: float = 0.3,
    range_type: str = "bipolar",
    seed: int = 42,
    llm_client=None,
    config_overrides: dict | None = None,
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
        lambda_social=params["dynamics"]["lambda_social"],
        seed=seed,
    )
    eta = params["dynamics"]["eta"]
    adj = random_network(n_agents, connectivity=connectivity, seed=seed)

    min_val, max_val = (0.0, 1.0) if range_type == "unipolar" else (-1.0, 1.0)
    rng = np.random.default_rng(seed)
    opinions = rng.uniform(min_val, max_val, size=n_agents)

    history = []
    metrics_timeline = []

    for t in range(steps + 1):
        history.append(
            {
                "_paso": t,
                "mean_opinion": float(np.mean(opinions)),
                "std_opinion": float(np.std(opinions)),
                "opinions_snapshot": opinions.tolist() if t % 10 == 0 or t == steps else None,
            }
        )

        if t % metrics_every_n == 0:
            mets = engine.system_metrics(opinions, adj, params["attractors"], params["repellers"])
            mets["_paso"] = t
            metrics_timeline.append(mets)

        if t < steps:
            # ── EWS Detection: compute instability signals from rolling window ──
            ews_flags = None
            if len(history) >= 10:
                window = [h["mean_opinion"] for h in history[-10:]]
                ews_metrics = calculate_ews_metrics(window)
                ews_flags = check_ews_signals(ews_metrics, {})
                # Augment EWS flags with numeric features for the trained
                # CfC temperature modulator (which needs polarization, deltas,
                # skewness, Gini — not just boolean signals).
                ews_flags["polarization"] = float(np.std(opinions))
                ews_flags["delta_p1"] = float(window[-1] - window[-2]) if len(window) >= 2 else 0.0
                ews_flags["delta_p5"] = float(window[-1] - window[-5]) if len(window) >= 5 else 0.0
                ews_flags["skewness"] = float(np.mean(np.abs(ews_metrics["skewness"])))
                ews_flags["gini"] = engine.gini_coefficient
                history[-1]["ews"] = {
                    "metrics": ews_metrics,
                    "flags": ews_flags,
                }

            opinions = engine.step(
                opinions,
                adj,
                params["attractors"],
                params["repellers"],
                eta=eta,
                ews_flags=ews_flags,
            )

    initial_op = history[0]["mean_opinion"]
    final_op_uncorrected = history[-1]["mean_opinion"]

    # CfC residual correction (calibration_log.md §6). When enabled, loads the
    # trained CfCResidualCorrector via CfCRouter and applies:
    #   final(t) = ŷ(t) + r̂(t) — adaptive bias correction scaled 50% toward
    #   the known baseline error. Transparent fallback: skipped if torch/model
    #   missing, leaving final_op unchanged.
    use_cfc = bool(config_overrides.get("use_cfc_correction", False)) if config_overrides else False
    if use_cfc:
        from cfc_router import CfCRouter

        router = CfCRouter.get()
        if router.status.get("residual_corrector"):
            sim_series = [h["mean_opinion"] for h in history]
            # Bipolar [-1,1] → convert to leave% scale for the residual model.
            sim_leave = [(v + 1.0) / 2.0 for v in sim_series]
            actual_leave = config_overrides.get("actual_leave_pct")
            corrected, src = router.correct_residual(
                history=sim_leave,
                simulated=sim_leave[-1],
                actual=actual_leave,
            )
            final_op = (corrected * 2.0) - 1.0  # back to bipolar
            history[-1]["mean_opinion_cfc_corrected"] = final_op
            history[-1]["cfc_correction_source"] = src
        else:
            final_op = final_op_uncorrected
    else:
        final_op = final_op_uncorrected
    delta = final_op - initial_op
    neutro = 0.0 if range_type == "bipolar" else 0.5
    all_means = [h["mean_opinion"] for h in history]
    all_polar = [m["polarizacion"] for m in metrics_timeline] if metrics_timeline else [0.0]

    return {
        "history": history,
        "metrics_timeline": metrics_timeline,
        "final_state": {
            "opinions": opinions.tolist(),
            "mean_opinion": final_op,
            "std_opinion": float(np.std(opinions)),
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
            "rango": f"[{min_val}, {max_val}]",
        },
        "config_used": validated.model_dump(),
        "archetype_info": landscape.get("metadata", {}),
    }
