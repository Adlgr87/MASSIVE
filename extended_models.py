"""
extended_models.py — Modelos extendidos para MASSIVE
Nash Equilibrium, Bayesian Network, SIR Epidemiológico
Todos los modelos son 100% funcionales y se integran como reglas de simulator.py.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import numpy as np
from scipy.integrate import solve_ivp

log = logging.getLogger("massive")

# ── Importaciones opcionales (graceful degradation) ──────────────────────────
try:
    import nashpy as nash
    NASH_AVAILABLE = True
except ImportError:
    NASH_AVAILABLE = False
    log.warning("[ExtModels] nashpy no instalado — regla_nash usará fallback analítico.")

try:
    # pgmpy >= 1.1.0 renamed BayesianNetwork → DiscreteBayesianNetwork
    try:
        from pgmpy.models import DiscreteBayesianNetwork as BayesianNetwork
        log.debug("[ExtModels] pgmpy >= 1.1.0 detectado — usando DiscreteBayesianNetwork.")
    except ImportError:
        from pgmpy.models import BayesianNetwork  # type: ignore[assignment]
        log.debug("[ExtModels] pgmpy < 1.1.0 detectado — usando BayesianNetwork (legacy).")
    from pgmpy.factors.discrete import TabularCPD
    from pgmpy.inference import VariableElimination
    PGMPY_AVAILABLE = True
except ImportError:
    PGMPY_AVAILABLE = False
    log.warning("[ExtModels] pgmpy no instalado — regla_bayesiana usará modelo Beta-Binomial.")


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS (re-implement locally so this module is self-contained)
# ─────────────────────────────────────────────────────────────────────────────

_RANGOS: dict = {
    "[0, 1] — Probabilístico": {"min": 0.0, "max": 1.0, "neutro": 0.5},
    "[-1, 1] — Bipolar":       {"min": -1.0, "max": 1.0, "neutro": 0.0},
}

def _rango(cfg: dict) -> dict:
    return _RANGOS.get(cfg.get("rango", "[0, 1] — Probabilístico"),
                       _RANGOS["[0, 1] — Probabilístico"])

def _clip_em(val: float, cfg: dict) -> float:
    r = _rango(cfg)
    return float(np.clip(val, r["min"], r["max"]))

def _neutro_em(cfg: dict) -> float:
    return _rango(cfg)["neutro"]

def _amp_em(cfg: dict) -> float:
    r = _rango(cfg)
    return r["max"] - r["min"]


# ─────────────────────────────────────────────────────────────────────────────
# RULE 10: NASH EQUILIBRIUM
# Agents choose alignment strategies; Nash equilibrium sets the stable mix.
# Reference: Nash (1950), Fudenberg & Tirole (1991).
# ─────────────────────────────────────────────────────────────────────────────

def _nash_fallback_mixed(A: np.ndarray) -> np.ndarray:
    """Analytic mixed-strategy Nash equilibrium for 2x2 symmetric games."""
    num = A[1, 1] - A[0, 1]
    den = (A[0, 0] - A[1, 0]) + (A[1, 1] - A[0, 1])
    if abs(den) < 1e-9:
        return np.array([0.5, 0.5])
    p = float(np.clip(num / den, 0.0, 1.0))
    return np.array([p, 1.0 - p])


def regla_nash(estado: dict, params: dict, cfg: dict) -> dict:
    """
    Nash Equilibrium rule (Rule 10).

    Models the stable mixed-strategy equilibrium between two social groups.
    Payoffs are derived from the current opinion alignment with each group.
    The Nash equilibrium probability of choosing Group A becomes the new
    group membership weight, which in turn determines the updated opinion.

    Args:
        estado: Current simulation state.
        params: Rule parameters (c_same, c_diff, intensity).
        cfg: Global configuration.

    Returns:
        Updated state with Nash-equilibrium-derived opinion.
    """
    op_a = estado.get("opinion_grupo_a", _rango(cfg).get("max", 1.0) * 0.7)
    op_b = estado.get("opinion_grupo_b", _rango(cfg).get("min", 0.0) + _amp_em(cfg) * 0.3)
    perten = float(estado.get("pertenencia_grupo", 0.6))
    opinion = estado["opinion"]
    amp = _amp_em(cfg)

    c_same = float(params.get("c_same", 2.0))
    c_diff = float(params.get("c_diff", 0.5))
    intensity = float(params.get("intensity", 1.0))

    close_a = 1.0 - abs(opinion - op_a) / max(amp, 1e-9)
    close_b = 1.0 - abs(opinion - op_b) / max(amp, 1e-9)

    # 2×2 symmetric payoff matrix for coordination game
    A = np.array([
        [c_same * close_a,        c_diff * close_a],
        [c_diff * close_b,        c_same * close_b],
    ]) * intensity

    if NASH_AVAILABLE:
        try:
            game = nash.Game(A, A.T)
            eqs = list(game.support_enumeration())
            if eqs:
                sigma_row, _ = eqs[0]
                nuevo_perten = float(np.clip(sigma_row[0], 0.1, 0.9))
            else:
                nuevo_perten = perten
        except Exception as exc:
            log.debug(f"[Nash] support_enumeration error: {exc}; using fallback.")
            sigma = _nash_fallback_mixed(A)
            nuevo_perten = float(np.clip(sigma[0], 0.1, 0.9))
    else:
        sigma = _nash_fallback_mixed(A)
        nuevo_perten = float(np.clip(sigma[0], 0.1, 0.9))

    new_opinion = nuevo_perten * op_a + (1.0 - nuevo_perten) * op_b

    nuevo = estado.copy()
    nuevo["pertenencia_grupo"] = nuevo_perten
    nuevo["opinion"] = _clip_em(new_opinion, cfg)
    nuevo["_nash_sigma_a"] = round(nuevo_perten, 3)
    nuevo["_nash_sigma_b"] = round(1.0 - nuevo_perten, 3)
    return nuevo


# ─────────────────────────────────────────────────────────────────────────────
# BAYESIAN OPINION NETWORK
# Pre-built pgmpy model (built once, reused via module-level cache).
# Falls back to Beta-Binomial conjugate model when pgmpy is unavailable.
# Reference: Pearl (1988), Jensen & Nielsen (2007).
# ─────────────────────────────────────────────────────────────────────────────

_BN_CACHE: dict = {}   # module-level cache keyed by range name

def _build_pgmpy_model(rango_name: str) -> "tuple[BayesianNetwork, VariableElimination]":
    """Build and cache a pgmpy BN for the given range type."""
    model = BayesianNetwork([
        ("Propaganda", "Opinion"),
        ("Confianza", "Opinion"),
        ("PresionSocial", "Opinion"),
    ])

    cpd_prop = TabularCPD(
        variable="Propaganda", variable_card=3,
        values=[[1/3], [1/3], [1/3]],
    )
    cpd_conf = TabularCPD(
        variable="Confianza", variable_card=3,
        values=[[1/3], [1/3], [1/3]],
    )
    cpd_pres = TabularCPD(
        variable="PresionSocial", variable_card=3,
        values=[[1/3], [1/3], [1/3]],
    )

    # Opinion CPD given (Propaganda × Confianza × PresionSocial)
    n_parent_combos = 27
    cpd_vals = np.zeros((3, n_parent_combos))
    combo_idx = 0
    for p_state in range(3):
        for c_state in range(3):
            for s_state in range(3):
                score = (0.5 * p_state + 0.3 * s_state + 0.2 * c_state) / 2.0
                low  = max(0.0, 1.0 - 2 * score)
                high = max(0.0, 2 * score - 1.0)
                mid  = max(0.0, 1.0 - abs(2 * score - 1.0))
                total = low + mid + high + 1e-9
                cpd_vals[0, combo_idx] = low  / total
                cpd_vals[1, combo_idx] = mid  / total
                cpd_vals[2, combo_idx] = high / total
                combo_idx += 1

    cpd_op = TabularCPD(
        variable="Opinion", variable_card=3,
        values=cpd_vals,
        evidence=["Propaganda", "Confianza", "PresionSocial"],
        evidence_card=[3, 3, 3],
    )

    model.add_cpds(cpd_prop, cpd_conf, cpd_pres, cpd_op)
    model.check_model()
    infer = VariableElimination(model)
    return model, infer


def _get_bn_inference(rango_name: str) -> "VariableElimination | None":
    """Return cached VariableElimination engine, building it on first call."""
    if not PGMPY_AVAILABLE:
        return None
    if rango_name not in _BN_CACHE:
        try:
            _, infer = _build_pgmpy_model(rango_name)
            _BN_CACHE[rango_name] = infer
        except Exception as exc:
            log.warning(f"[Bayesian] Error construyendo BN pgmpy: {exc}")
            _BN_CACHE[rango_name] = None
    return _BN_CACHE[rango_name]


def _discretize3(value: float, lo: float, hi: float) -> int:
    """Map a continuous value in [lo, hi] to a 3-state index {0, 1, 2}."""
    if hi <= lo:
        return 1
    norm = (value - lo) / (hi - lo)
    if norm < 1/3:
        return 0
    elif norm < 2/3:
        return 1
    else:
        return 2


def _beta_binom_update(opinion: float, propaganda: float,
                        confianza: float, pres_social: float,
                        amp: float, r_min: float,
                        n_prior: float = 10.0, n_obs: float = 5.0) -> float:
    """
    Beta-Binomial conjugate Bayesian update (used when pgmpy unavailable).
    Returns updated opinion in original opinion space.
    """
    p_op   = (opinion    - r_min) / max(amp, 1e-9)
    p_prop = (propaganda - r_min) / max(amp, 1e-9)
    p_soc  = (pres_social - r_min) / max(amp, 1e-9)

    alpha_prior = p_op * n_prior + 1.0
    beta_prior  = (1.0 - p_op) * n_prior + 1.0

    evidence_p = confianza * p_prop + (1.0 - confianza) * p_soc
    k_obs      = round(evidence_p * n_obs)
    n_obs_int  = max(1, round(n_obs))

    alpha_post = alpha_prior + k_obs
    beta_post  = beta_prior + (n_obs_int - k_obs)

    posterior_mean = alpha_post / (alpha_post + beta_post)
    return r_min + float(np.clip(posterior_mean, 0.0, 1.0)) * amp


def regla_bayesiana(estado: dict, params: dict, cfg: dict) -> dict:
    """
    Bayesian Network rule (Rule 11).

    Uses a Bayesian network (pgmpy) with nodes Propaganda, Confianza,
    PresionSocial → Opinion. Observed values are discretized to 3 states
    and Variable Elimination returns the posterior opinion distribution.
    The posterior mean is mapped back to the continuous opinion space.

    Falls back to Beta-Binomial conjugate model when pgmpy is unavailable.

    Args:
        estado: Current simulation state.
        params: Rule parameters (n_prior, n_obs).
        cfg: Global configuration.

    Returns:
        Updated state with Bayesian posterior opinion + uncertainty metrics.
    """
    r = _rango(cfg)
    r_min, r_max = r["min"], r["max"]
    amp = _amp_em(cfg)
    opinion   = estado["opinion"]
    prop      = estado["propaganda"]
    confianza = estado.get("confianza", 0.5)

    op_a   = estado.get("opinion_grupo_a", r_min + 0.7 * amp)
    op_b   = estado.get("opinion_grupo_b", r_min + 0.3 * amp)
    perten = float(estado.get("pertenencia_grupo", 0.6))
    pres_social = perten * op_a + (1.0 - perten) * op_b

    infer = _get_bn_inference(cfg.get("rango", "[0, 1] — Probabilístico"))

    if infer is not None:
        try:
            ev_prop = _discretize3(prop,        r_min, r_max)
            ev_conf = _discretize3(confianza,   0.0,   1.0)
            ev_pres = _discretize3(pres_social, r_min, r_max)

            result = infer.query(
                variables=["Opinion"],
                evidence={"Propaganda": ev_prop,
                          "Confianza":  ev_conf,
                          "PresionSocial": ev_pres},
                show_progress=False,
            )
            probs = result.values
            midpoint = (r_min + r_max) / 2.0
            new_op = float(
                probs[0] * r_min + probs[1] * midpoint + probs[2] * r_max
            )
            mean_val = np.dot(probs, [0, 0.5, 1])
            uncertainty = float(np.sqrt(np.sum(probs * (np.array([0, 0.5, 1]) - mean_val) ** 2)))
        except Exception as exc:
            log.debug(f"[Bayesian] pgmpy inference error: {exc}; using Beta-Binomial.")
            new_op = _beta_binom_update(opinion, prop, confianza, pres_social,
                                        amp, r_min,
                                        params.get("n_prior", 10.0),
                                        params.get("n_obs", 5.0))
            uncertainty = 0.0
    else:
        new_op = _beta_binom_update(opinion, prop, confianza, pres_social,
                                    amp, r_min,
                                    params.get("n_prior", 10.0),
                                    params.get("n_obs", 5.0))
        uncertainty = 0.0

    inertia = float(params.get("inertia", 0.4))
    blended = inertia * opinion + (1.0 - inertia) * new_op

    nuevo = estado.copy()
    nuevo["opinion"]            = _clip_em(blended, cfg)
    nuevo["_bayes_uncertainty"] = round(uncertainty, 4)
    return nuevo


# ─────────────────────────────────────────────────────────────────────────────
# RULE 12: SIR EPIDEMIOLOGICAL MODEL
# Opinion spread modeled as an epidemic: Susceptible → Influenced → Resistant.
# Reference: Kermack & McKendrick (1927), Daley & Kendall (1964).
# ─────────────────────────────────────────────────────────────────────────────

def regla_sir(estado: dict, params: dict, cfg: dict) -> dict:
    """
    SIR (Susceptible-Influenced-Resistant) epidemiological rule (Rule 12).

    The SIR model treats opinion adoption as epidemic contagion:
      S — Susceptible: could still adopt/reject the opinion
      I — Influenced:  has adopted the propagated opinion
      R — Resistant:   has processed and become immune to further change

    Opinion maps to the Influenced fraction after one SIR step dt.
    Propaganda amplifies the effective infection rate β.

    Args:
        estado: Current simulation state.
        params: Rule parameters (beta, gamma, dt, R0_frac).
        cfg: Global configuration.

    Returns:
        Updated state with SIR-evolved opinion and S/I/R fractions.
    """
    r = _rango(cfg)
    r_min, r_max = r["min"], r["max"]
    amp = _amp_em(cfg)
    opinion = estado["opinion"]
    prop    = estado["propaganda"]

    p_op   = float(np.clip((opinion - r_min) / max(amp, 1e-9), 0.0, 1.0))
    p_prop = float(np.clip((prop    - r_min) / max(amp, 1e-9), 0.0, 1.0))

    beta  = float(params.get("beta",   0.3))
    gamma = float(params.get("gamma",  0.1))
    dt    = float(params.get("dt",     0.2))

    I0 = p_op
    R0 = float(np.clip(estado.get("_sir_R", 0.0), 0.0, 0.9))
    S0 = float(np.clip(1.0 - I0 - R0, 0.0, 1.0))

    beta_eff = beta * (0.5 + p_prop)  # range [0.5β, 1.5β]

    def sir_rhs(t, y):
        S, I, R = y
        dS = -beta_eff * S * I
        dI =  beta_eff * S * I - gamma * I
        dR =  gamma * I
        return [dS, dI, dR]

    try:
        sol = solve_ivp(sir_rhs, [0.0, dt], [S0, I0, R0],
                        method="RK45", dense_output=False,
                        max_step=dt / 5)
        S_new, I_new, R_new = sol.y[:, -1]
    except Exception:
        S_new, I_new, R_new = S0, I0, R0

    S_new = float(np.clip(S_new, 0.0, 1.0))
    I_new = float(np.clip(I_new, 0.0, 1.0))
    R_new = float(np.clip(R_new, 0.0, 1.0))

    new_opinion = r_min + I_new * amp

    nuevo = estado.copy()
    nuevo["opinion"] = _clip_em(new_opinion, cfg)
    nuevo["_sir_S"]  = round(S_new, 4)
    nuevo["_sir_I"]  = round(I_new, 4)
    nuevo["_sir_R"]  = round(R_new, 4)
    return nuevo
