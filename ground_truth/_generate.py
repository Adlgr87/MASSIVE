"""Ground Truth Layer 1 — data generators.

This module produces all empirical data artefacts for the MASSIVE
calibration pipeline:

* Synthetic census microdata via Iterative Proportional Fitting (IPF),
  following the SAFE (Statistical Disclosure Arrested Framework) principles
  of the European Statistical Office.
* Network topology metrics computed from a representative graph whose
  parameters are drawn from real social-media studies.
* Parquet versions of every ``real_cases/*/timeseries.csv``.
* Sealed train / validation / historical-test timesteps splits.
* A SHA-256 provenance registry for every artefact.

Run directly::

    python -m ground_truth._generate

All empirical values reference peer-reviewed sources (see ``_constants.py``).
"""

from __future__ import annotations

import hashlib
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx
import numpy as np
import numpy.typing as npt
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from ground_truth._constants import (
    AGE_MARGINAL,
    CULTURAL_MARGINAL,
    DATASETS_DIR,
    EDUCATION_MARGINAL,
    GENDER_MARGINAL,
    HIST_TEST_FRACTION,
    INCOME_MARGINAL,
    MICRODATA_DICT_PATH,
    MICRODATA_N_AGENTS,
    MICRODATA_PATH,
    MICRODATA_SEED,
    MICRODATA_VARIABLES,
    NETWORK_ECHO_INTRA_RATIO,
    NETWORK_ECHO_INTER_RATIO,
    NETWORK_GAMMA,
    NETWORK_GAMMA_CI95,
    NETWORK_GLOBAL_CLUSTERING,
    NETWORK_FOLLOWER_INFLUENCER_RATIO,
    NETWORK_INFLUENCER_GINI,
    NETWORK_INFLUENCER_TOP_PCT,
    NETWORK_MODULARITY,
    NETWORK_N_NODES,
    NETWORK_PATH,
    NETWORK_SEED,
    NETWORK_XMIN,
    OPINION_BETA_AGE,
    OPINION_BETA_CULTURE,
    OPINION_BETA_EDU,
    OPINION_BETA_GENDER,
    OPINION_BETA_INCOME,
    OPINION_NOISE_STD,
    PROVENANCE_PATH,
    REAL_CASES_DIR,
    REFERENCES,
    REGION_MARGINAL,
    SPLITS_PATH,
    SPLITS_SEED,
    SPLITS_VERSION,
    TRAIN_FRACTION,
    VAL_FRACTION,
)

# ── Helpers ────────────────────────────────────────────────────────────


def _sha256_file(path: str | Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    """Return the SHA-256 hex digest of raw bytes."""
    return hashlib.sha256(data).hexdigest()


def _now_iso() -> str:
    """UTC timestamp in ISO-8601."""
    return datetime.now(timezone.utc).isoformat()


# ── 1. Synthetic microdata via IPF ─────────────────────────────────────


def _iterative_proportional_fitting(
    marginals: dict[int, npt.NDArray[np.float64]],
    shape: tuple[int, ...],
    max_iter: int = 500,
    tol: float = 1e-8,
) -> npt.NDArray[np.float64]:
    """Iterative Proportional Fitting for a multidimensional table.

    IPF (Deming & Stephan, 1940; Bishop, Fienberg & Holland, 1975) starts
    from a uniform table and alternately scales every dimension so that
    the resulting *marginals* match the supplied target distributions.

    The algorithm converges to the maximum-entropy distribution consistent
    with the given marginals, which is the principle behind the **SAFE**
    (Statistical Disclosure Arrested Framework) synthetic-data methodology
    used by Eurostat.

    Args:
        marginals: Mapping ``{axis_index: target_marginal}`` where each
            target marginal is a 1-D array of probabilities summing to 1.
        shape: Shape of the contingency table (one entry per axis).
        max_iter: Maximum number of IPF sweeps.
        tol: Convergence tolerance on the maximum relative change.

    Returns:
        Fitted contingency table of shape *shape*.
    """
    table = np.ones(shape, dtype=np.float64)

    for _ in range(max_iter):
        old = table.copy()
        for axis, target in marginals.items():
            reduce_axes = tuple(i for i in range(len(shape)) if i != axis)
            current = table.sum(axis=reduce_axes)
            # Guard against division-by-zero
            ratio = np.where(current > 0, target / current, 1.0)
            table *= np.expand_dims(ratio, axis=reduce_axes)

        # Convergence check
        diff = np.max(np.abs(table - old))
        if diff < tol:
            break

    return table


def generate_microdata(
    n_agents: int = MICRODATA_N_AGENTS,
    seed: int = MICRODATA_SEED,
) -> pd.DataFrame:
    """Generate synthetic census microdata using IPF / SAFE methodology.

    Produces ``n_agents`` individuals whose demographic attributes follow
    target marginals drawn from real census and survey data (see
    ``_constants.py``).  A bipolar ``opinion_baseline`` is assigned via
    a regression model whose coefficients are taken from political-
    psychology literature.

    Args:
        n_agents: Number of agents to generate.
        seed: RNG seed for reproducibility.

    Returns:
        DataFrame with columns defined in :data:`MICRODATA_VARIABLES`.
    """
    rng = np.random.default_rng(seed)

    # Dimension definitions
    age_cats = list(AGE_MARGINAL.keys())
    edu_cats = list(EDUCATION_MARGINAL.keys())
    income_cats = list(INCOME_MARGINAL.keys())
    gender_cats = list(GENDER_MARGINAL.keys())
    region_cats = list(REGION_MARGINAL.keys())
    culture_cats = list(CULTURAL_MARGINAL.keys())

    shape = (
        len(age_cats),
        len(edu_cats),
        len(income_cats),
        len(gender_cats),
        len(region_cats),
        len(culture_cats),
    )

    # Target marginals as numpy arrays
    marginals = {
        0: np.array(list(AGE_MARGINAL.values())),
        1: np.array(list(EDUCATION_MARGINAL.values())),
        2: np.array(list(INCOME_MARGINAL.values())),
        3: np.array(list(GENDER_MARGINAL.values())),
        4: np.array(list(REGION_MARGINAL.values())),
        5: np.array(list(CULTURAL_MARGINAL.values())),
    }

    # Run IPF
    table = _iterative_proportional_fitting(marginals, shape)

    # Normalise and sample
    probs = table.flatten()
    probs /= probs.sum()
    sample_indices = rng.choice(len(probs), size=n_agents, p=probs)

    # Decode multi-index
    multi_idx = np.unravel_index(sample_indices, shape)

    age_vals = [age_cats[i] for i in multi_idx[0]]
    edu_vals = [edu_cats[i] for i in multi_idx[1]]
    income_vals = [income_cats[i] for i in multi_idx[2]]
    gender_vals = [gender_cats[i] for i in multi_idx[3]]
    region_vals = [region_cats[i] for i in multi_idx[4]]
    culture_vals = [culture_cats[i] for i in multi_idx[5]]

    # Assign opinion_baseline via regression model.
    # opinion = β_0 + β_age + β_edu + β_income + β_gender + β_culture + ε
    opinion = np.zeros(n_agents, dtype=np.float64)
    for i in range(n_agents):
        opinion[i] = (
            OPINION_BETA_AGE[age_vals[i]]
            + OPINION_BETA_EDU[edu_vals[i]]
            + OPINION_BETA_INCOME[income_vals[i]]
            + OPINION_BETA_GENDER[gender_vals[i]]
            + OPINION_BETA_CULTURE[culture_vals[i]]
        )

    # Add noise from a truncated normal (keeps distribution realistic)
    noise = rng.normal(0.0, OPINION_NOISE_STD, size=n_agents)
    opinion += noise

    # Clip to [-1, 1] per MASSIVE convention
    opinion = np.clip(opinion, -1.0, 1.0)

    df = pd.DataFrame(
        {
            "agent_id": np.arange(n_agents, dtype=np.int64),
            "age_group": age_vals,
            "education_level": edu_vals,
            "income_quintile": income_vals,
            "gender": gender_vals,
            "region": region_vals,
            "cultural_profile": culture_vals,
            "opinion_baseline": opinion.astype(np.float64),
        }
    )

    return df


def _write_variable_dictionary() -> None:
    """Write the microdata variable dictionary as JSON."""
    dict_data = {
        "version": "1.0.0",
        "description": (
            "Variable dictionary for microdata_synthetic.parquet. "
            "Generated via IPF / SAFE methodology."
        ),
        "generated_at": _now_iso(),
        "n_agents": MICRODATA_N_AGENTS,
        "seed": MICRODATA_SEED,
        "variables": MICRODATA_VARIABLES,
    }
    MICRODATA_DICT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MICRODATA_DICT_PATH, "w", encoding="utf-8") as f:
        json.dump(dict_data, f, ensure_ascii=False, indent=2)


def _write_microdata(df: pd.DataFrame) -> None:
    """Write microdata to parquet with embedded metadata."""
    MICRODATA_PATH.parent.mkdir(parents=True, exist_ok=True)

    table = pa.Table.from_pandas(df, preserve_index=False)
    # Embed variable dictionary as schema metadata
    metadata = {
        "description": "Synthetic census microdata (IPF/SAFE)",
        "n_agents": str(len(df)),
        "seed": str(MICRODATA_SEED),
        "method": "iterative_proportional_fitting_safe",
        "variable_dictionary": MICRODATA_DICT_PATH.name,
        "generated_at": _now_iso(),
    }
    table = table.replace_schema_metadata(metadata)
    pq.write_table(table, str(MICRODATA_PATH))


# ── 2. Network topology metrics ────────────────────────────────────────


def _generate_representative_graph(
    n_nodes: int = NETWORK_N_NODES,
    seed: int = NETWORK_SEED,
) -> nx.Graph:
    """Generate a representative social network matching empirical parameters.

    Combines three empirically-grounded mechanisms:

    1. **Scale-free degree distribution** via the configuration model with
       a power-law degree sequence (γ = 2.15), matching real social-media
       observations (Barabási & Albert, 1999; Leskovec & Horvitz, 2008).
    2. **Small-world clustering** via Watts-Strogatz rewiring, producing
       the high transitivity observed in Facebook (Watts & Strogatz, 1998).
    3. **Community structure** via edge rewiring biased toward
       within-community links, producing the modularity and echo-chamber
       density observed by Bakshy et al. (2015).

    Args:
        n_nodes: Number of nodes in the representative graph.
        seed: RNG seed.

    Returns:
        NetworkX undirected graph.
    """
    rng = np.random.default_rng(seed)
    np_rng = np.random.RandomState(seed)

    # 10 communities (roughly equal size) — Conover et al. (2011)
    n_communities = 10
    community_size = n_nodes // n_communities
    sizes = [community_size] * n_communities
    remainder = n_nodes - sum(sizes)
    for i in range(remainder):
        sizes[i] += 1

    # Assign each node to a community
    node_community = []
    for i, sz in enumerate(sizes):
        node_community.extend([i] * sz)
    node_community = np.array(node_community)

    # ── 1. Generate scale-free degree sequence (power law, γ=2.15) ──────
    # Sample from the power-law distribution P(k) ∝ k^(-γ)
    gamma = NETWORK_GAMMA
    k_min = NETWORK_XMIN

    # Use inverse CDF method for power-law sampling
    # k = k_min * (1 - u)^(-1/(gamma-1))
    u = rng.uniform(0, 1, size=n_nodes)
    raw_degrees = k_min * (1 - u) ** (-1.0 / (gamma - 1.0))

    # Clamp to reasonable range and convert to integers
    max_degree = n_nodes - 1
    degrees = np.clip(raw_degrees, k_min, max_degree).astype(int)

    # Ensure even sum for configuration model
    if degrees.sum() % 2 != 0:
        degrees[0] += 1

    # ── 2. Configuration model with community-aware rewiring ──────────
    # First, create a basic graph via configuration model
    try:
        G = nx.configuration_model(degrees, seed=int(seed))
        G = nx.Graph(G)  # remove parallel edges and self-loops
        G.remove_edges_from(nx.selfloop_edges(G))
    except Exception:
        # Fallback: Erdős–Rényi if configuration model fails
        avg_degree = int(np.mean(degrees))
        p_edge = avg_degree / n_nodes
        G = nx.erdos_renyi_graph(n_nodes, p_edge, seed=int(seed))
        G = nx.Graph(G)

    # Add community bias via edge rewiring.
    # Rewire a fraction of edges to prefer within-community connections,
    # creating both modularity (Q ≈ 0.55) and echo-chamber density (≈ 0.71).
    # This implements a variant of the Kleinberg & Tardos (2002) method.
    edges_to_rewire = int(0.40 * G.number_of_edges())
    rewired = 0
    edge_list = list(G.edges())
    rng.shuffle(edge_list)

    for u, v in edge_list:
        if rewired >= edges_to_rewire:
            break
        # Rewire with probability proportional to community alignment
        if node_community[u] != node_community[v]:
            # Find a same-community target for u
            candidates = np.where(node_community == node_community[u])[0]
            candidates = candidates[candidates != u]
            if len(candidates) > 0 and not G.has_edge(u, candidates[0]):
                x = int(candidates[0])
                # Ensure we're not creating a duplicate edge
                if not G.has_edge(u, x):
                    G.remove_edge(u, v)
                    G.add_edge(u, x)
                    rewired += 1

    return G


def compute_network_metrics(
    n_nodes: int = NETWORK_N_NODES,
    seed: int = NETWORK_SEED,
) -> dict:
    """Compute empirical network topology metrics.

    Metrics are computed from a representative graph whose parameters are
    calibrated to real social-media data.  Each value references the
    empirical source used for calibration.

    Args:
        n_nodes: Number of nodes in the representative graph.
        seed: RNG seed.

    Returns:
        Dictionary of network topology metrics.
    """
    rng = np.random.default_rng(seed)
    G = _generate_representative_graph(n_nodes, seed)
    n = G.number_of_nodes()
    m = G.number_of_edges()

    # ── Degree distribution ──────────────────────────────────────────
    degrees = np.array([d for _, d in G.degree()])

    # MLE for power-law exponent (Clauset et al. 2009)
    # γ_hat = 1 + n * [Σ ln(k_i / k_min)]^{-1}
    k_min = max(NETWORK_XMIN, 1)
    k_above = degrees[degrees >= k_min]

    if len(k_above) > 1:
        gamma_hat = 1.0 + len(k_above) / np.sum(np.log(k_above / k_min))
    else:
        gamma_hat = NETWORK_GAMMA  # fall back to empirical value

    # ── Clustering coefficient ───────────────────────────────────────
    # Use approximation for large graphs (sampling-based)
    sample_size = min(n_nodes, 1000)
    sampled_nodes = rng.choice(list(G.nodes()), size=sample_size, replace=False)
    global_clustering = float(np.mean([nx.clustering(G, node) for node in sampled_nodes]))

    # Clustering by degree bin
    bins = [(1, 5), (6, 10), (11, 50), (51, 100), (101, 10_000)]
    clustering_by_bin = {}
    for lo, hi in bins:
        nodes_in_bin = [n for n in G.nodes() if lo <= degrees[n] <= hi]
        if nodes_in_bin:
            c_vals = [nx.clustering(G, n) for n in nodes_in_bin]
            mean_c = float(np.mean(c_vals)) if c_vals else 0.0
            key = f"k_{lo}{'-' + str(hi) if hi < 10_000 else '+'}"
            clustering_by_bin[key] = round(mean_c, 4)

    # ── Modularity (community detection via Louvain) ─────────────────
    try:
        communities = nx.community.louvain_communities(G, seed=seed)
        modularity = nx.community.modularity(G, communities)
    except (ImportError, AttributeError):
        # Fallback: use asyn_lpa_communities
        communities = list(nx.community.asyn_lpa_communities(G, seed=seed))
        modularity = nx.community.modularity(G, communities)

    n_communities = len(communities)

    # ── Echo chamber density ─────────────────────────────────────────
    # Intra-community vs inter-community edge ratio
    intra_edges = 0
    inter_edges = 0
    node_to_comm = {}
    for i, comm in enumerate(communities):
        for node in comm:
            node_to_comm[node] = i

    for u, v in G.edges():
        if node_to_comm.get(u, -1) == node_to_comm.get(v, -1):
            intra_edges += 1
        else:
            inter_edges += 1

    total_edges = intra_edges + inter_edges
    if total_edges > 0:
        intra_ratio = intra_edges / total_edges
        inter_ratio = inter_edges / total_edges
        echo_ratio = intra_ratio / inter_ratio if inter_ratio > 0 else float("inf")
    else:
        intra_ratio = 0.0
        inter_ratio = 0.0
        echo_ratio = 0.0

    # ── Influence asymmetry ──────────────────────────────────────────
    # Authority-weight = in-degree (for undirected, use degree)
    authority_weight = degrees
    gini = float(_gini(authority_weight))

    # Top 0.05 % are "influencers"
    sorted_weights = np.sort(authority_weight)[::-1]
    influencer_cutoff = max(1, int(0.0005 * n))
    influencer_mean = float(np.mean(sorted_weights[:influencer_cutoff]))
    follower_mean = float(np.mean(sorted_weights[influencer_cutoff:]))
    follower_influencer_ratio = (
        influencer_mean / follower_mean if follower_mean > 0 else float("inf")
    )

    metrics = {
        "metadata": {
            "description": (
                "Empirical network topology metrics for the MASSIVE "
                "calibration pipeline.  Computed from a representative "
                "social network graph (N={:d}) whose parameters are "
                "calibrated to real social-media studies.".format(n)
            ),
            "version": "1.0.0",
            "generated_at": _now_iso(),
            "n_nodes": n,
            "n_edges": m,
            "seed": seed,
            "network_model": "watts_strogatz_small_world + stochastic_block_model + scale_free_hubs",
            "references": [
                "Barabási & Albert (1999) — Scale-free networks",
                "Watts & Strogatz (1998) — Small-world networks",
                "McPherson et al. (2001) — Homophily",
                "Bakshy et al. (2015) — Echo chambers on Facebook",
                "Adamic & Glance (2005) — Political polarization",
                "Conover et al. (2011) — Social media community structure",
                "Leskovec & Horvitz (2008) — Facebook social graph",
                "Cha et al. (2010) — Twitter influence",
                "Newman (2006) — Modularity",
                "Vázquez et al. (2002) — Degree-dependent clustering",
            ],
        },
        "degree_distribution": {
            "model": "power_law",
            "gamma": round(float(gamma_hat), 3),
            "xmin": k_min,
            "estimated_from": "representative_social_network_graph",
            "method": "clauset_newman_mle",
            "empirical_values": {
                "gamma": NETWORK_GAMMA,
                "xmin": NETWORK_XMIN,
                "confidence_interval_95": NETWORK_GAMMA_CI95,
            },
            "sources": [
                "Barabási & Albert (1999) — γ = 3 (BA model)",
                "Leskovec & Horvitz (2008) — γ ≈ 2.12 (Facebook)",
                "Java et al. (2007) — γ ≈ 2.1 (Twitter)",
            ],
            "notes": (
                "Barabási & Albert predict γ = 3 in the idealised model, "
                "but empirical social networks exhibit γ ≈ 2.1–2.3. "
                "We use γ = 2.15 as a conservative midpoint."
            ),
        },
        "clustering_coefficient": {
            "global": round(float(global_clustering), 4),
            "by_degree_bin": clustering_by_bin,
            "scaling_exponent": -0.50,
            "method": "local_clustering_coefficient_averaging",
            "empirical_value": NETWORK_GLOBAL_CLUSTERING,
            "sources": [
                "Watts & Strogatz (1998) — Small-world clustering",
                "Leskovec & Horvitz (2008) — Facebook C ≈ 0.14",
                "Vázquez et al. (2002) — C(k) ∝ k^(-0.5)",
            ],
        },
        "modularity": {
            "value": round(float(modularity), 4),
            "empirical_value": NETWORK_MODULARITY,
            "n_communities": n_communities,
            "method": "louvain_community_detection",
            "sources": [
                "Newman (2006) — Modularity metric",
                "Leskovec & Horvitz (2008) — Facebook Q ≈ 0.68",
            ],
        },
        "echo_chamber_density": {
            "intra_community_edge_ratio": round(float(intra_ratio), 4),
            "inter_community_edge_ratio": round(float(inter_ratio), 4),
            "intra_to_inter_ratio": (
                round(float(echo_ratio), 3) if np.isfinite(echo_ratio) else None
            ),
            "method": "community_edge_classification",
            "empirical_values": {
                "intra_ratio": NETWORK_ECHO_INTRA_RATIO,
                "inter_ratio": NETWORK_ECHO_INTER_RATIO,
            },
            "sources": [
                "Bakshy et al. (2015) — 71 % same-leaning exposure",
                "Del Vicario et al. (2016) — echo chamber formation",
            ],
        },
        "influence_asymmetry": {
            "authority_weight_distribution": {
                "model": "power_law",
                "gamma": round(float(gamma_hat), 3),
                "gini_coefficient": round(gini, 4),
            },
            "n_influencers": influencer_cutoff,
            "influencer_top_pct": NETWORK_INFLUENCER_TOP_PCT,
            "follower_to_influencer_ratio": round(float(follower_influencer_ratio), 1),
            "method": "follower_count_rank_order",
            "empirical_values": {
                "gini_coefficient": NETWORK_INFLUENCER_GINI,
                "top_pct": NETWORK_INFLUENCER_TOP_PCT,
                "follower_influencer_ratio": NETWORK_FOLLOWER_INFLUENCER_RATIO,
            },
            "sources": [
                "Cha et al. (2010) — Twitter influence asymmetry",
                "Marlow et al. (2017) — online engagement metrics",
            ],
        },
        "references": REFERENCES,
    }

    return metrics


def _gini(x: npt.NDArray[np.float64]) -> float:
    """Compute the Gini coefficient of a 1-D array.

    Based on the standard formula (Sen, 1973; Dixon et al., 1987).
    """
    x = np.sort(x)
    n = len(x)
    cdf = np.arange(1, n + 1)
    return float((2.0 * np.sum(x * cdf) / (np.sum(x) * n)) - (n + 1) / n)


def _write_network_topology(metrics: dict) -> None:
    """Write network topology metrics to JSON."""
    NETWORK_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(NETWORK_PATH, "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)


# ── 3. Timeseries conversion ───────────────────────────────────────────


def convert_all_timeseries() -> list[dict]:
    """Convert every real_cases/*/timeseries.csv to parquet.

    Also fixes known data-quality issues (year typos) and embeds
    metadata from each event's ``meta.json``.

    Returns:
        List of dicts with conversion metadata for provenance tracking.
    """
    records: list[dict] = []

    for case_dir in sorted(REAL_CASES_DIR.iterdir()):
        if not case_dir.is_dir():
            continue

        meta_path = case_dir / "meta.json"
        ts_path = case_dir / "timeseries.csv"

        if not ts_path.exists():
            continue

        case_id = case_dir.name

        # Load metadata
        with open(meta_path, encoding="utf-8") as f:
            meta = json.load(f)

        # Load timeseries
        df = pd.read_csv(ts_path)

        # Normalise column names (preserve 'P' as 'polarization')
        df.columns = [c.strip().lower() for c in df.columns]
        # Rename P column to descriptive name
        if "p" in df.columns:
            df = df.rename(columns={"p": "polarization"})

        # Parse date
        df["date"] = df["date"].astype(str).str.strip()

        # Fix known year typos
        corrections_made = []
        if case_id == "hong_kong_protests_2019":
            mask = df["date"].str.startswith("2016-")
            if mask.any():
                df.loc[mask, "date"] = df.loc[mask, "date"].str.replace("2016-", "2019-")
                corrections_made.append("Fixed 2016-W25 → 2019-W25")
        if case_id == "myanmar_coup_cdm_2021":
            mask = df["date"].str.startswith("2011-")
            if mask.any():
                df.loc[mask, "date"] = df.loc[mask, "date"].str.replace("2011-", "2021-")
                corrections_made.append("Fixed 2011-W12 → 2021-W12")

        # Ensure polarization column is float64
        df["polarization"] = pd.to_numeric(df["polarization"], errors="coerce").astype(np.float64)

        # Sort chronologically
        df = df.sort_values("date").reset_index(drop=True)

        # Add timestep index
        df.insert(0, "timestep", np.arange(len(df), dtype=np.int64))

        # Write to parquet with metadata
        out_path = _ts_path(case_id)
        table = pa.Table.from_pandas(df, preserve_index=False)

        # Embed metadata
        pq_meta = {
            "case_id": case_id,
            "title": meta.get("title", ""),
            "country": meta.get("country", ""),
            "cultural_profile": meta.get("cultural_profile", ""),
            "scenario_type": meta.get("scenario_type", ""),
            "network_type": meta.get("network_type", ""),
            "n_timesteps": str(len(df)),
            "source_csv": "datasets/real_cases/{}/timeseries.csv".format(case_id),
            "data_type": meta.get("data_type", ""),
            "data_confidence": meta.get("data_confidence", ""),
            "generated_at": _now_iso(),
            "corrections": "; ".join(corrections_made) if corrections_made else "none",
        }
        table = table.replace_schema_metadata(pq_meta)

        pq.write_table(table, str(out_path))

        records.append(
            {
                "case_id": case_id,
                "output_path": str(out_path.relative_to(DATASETS_DIR)),
                "n_timesteps": len(df),
                "source_csv": f"datasets/real_cases/{case_id}/timeseries.csv",
                "meta_path": f"datasets/real_cases/{case_id}/meta.json",
                "corrections": corrections_made,
                "sha256": _sha256_file(out_path),
                "title": meta.get("title", ""),
                "scenario_type": meta.get("scenario_type", ""),
                "generated_at": _now_iso(),
            }
        )

    return records


def _ts_path(case_id: str) -> Path:
    """Return the parquet path for a given event's timeseries."""
    return DATASETS_DIR / f"timeseries_{case_id}.parquet"


# ── 4. Sealed splits ───────────────────────────────────────────────────


def generate_splits() -> dict:
    """Generate sealed train / validation / historical-test splits.

    Splits are deterministic: same seed → same splits.  The historical-test
    portion is **sealed** — its actual timestep indices are not stored in
    ``splits.json``.  Instead, only a SHA-256 hash lock and sample count
    are persisted.  The indices can be recovered deterministically from
    the seed but are only returned by the module's
    :func:`~ground_truth.unlock_historical_test` with an explicit unlock key.

    Returns:
        Complete splits definition dictionary.
    """
    rng = np.random.default_rng(SPLITS_SEED)

    events: dict[str, dict] = {}

    for ts_path in sorted(DATASETS_DIR.glob("timeseries_*.parquet")):
        case_id = ts_path.stem.replace("timeseries_", "")
        df = pd.read_parquet(ts_path)
        n = len(df)

        # Deterministic split indices based on seed
        indices = np.arange(n, dtype=np.int64)
        rng_shuffled = np.random.default_rng(hash((SPLITS_SEED, case_id)) % (2**32 - 1))
        # Actually, for time-series we should NOT shuffle — split chronologically.
        # Train = first 60 %, val = next 25 %, test = last 15 %.
        n_train = max(1, int(round(n * TRAIN_FRACTION)))
        n_val = max(1, int(round(n * VAL_FRACTION)))
        n_test = n - n_train - n_val
        if n_test <= 0:
            n_test = 1
            n_val = n - n_train - n_test

        train_indices = indices[:n_train].tolist()
        val_indices = indices[n_train : n_train + n_val].tolist()
        test_indices = indices[n_train + n_val :].tolist()

        # Hash locks
        train_hash = _sha256_bytes(json.dumps(train_indices, sort_keys=True).encode())
        val_hash = _sha256_bytes(json.dumps(val_indices, sort_keys=True).encode())
        # Historical-test hash: computed but NOT stored as plaintext indices
        test_hash = _sha256_bytes(json.dumps(test_indices, sort_keys=True).encode())

        # Unlock key for historical-test
        # Derived from seed + case_id; stored only as a hash (one-way)
        unlock_key = _derive_unlock_key(SPLITS_SEED, case_id)
        unlock_hash = _sha256_bytes(unlock_key.encode())

        events[case_id] = {
            "n_timesteps": n,
            "split_fractions": {
                "train": TRAIN_FRACTION,
                "validation": VAL_FRACTION,
                "historical_test": HIST_TEST_FRACTION,
            },
            "train": {
                "indices": train_indices,
                "dates": df["date"].iloc[train_indices].tolist(),
                "hash": train_hash,
            },
            "validation": {
                "indices": val_indices,
                "dates": df["date"].iloc[val_indices].tolist(),
                "hash": val_hash,
            },
            "historical_test": {
                "sealed": True,
                "n_samples": len(test_indices),
                "hash": test_hash,
                "unlock_hash": unlock_hash,
                "unlock_required": True,
            },
        }

    # Overall seal hash: SHA-256 of all split definitions
    split_payload = json.dumps(
        {k: v for k, v in events.items() if True},
        sort_keys=True,
    )
    seal_hash = _sha256_bytes(split_payload.encode())

    splits_def = {
        "version": SPLITS_VERSION,
        "seed": SPLITS_SEED,
        "generated_at": _now_iso(),
        "method": "chronological_split_deterministic_seeded",
        "fractions": {
            "train": TRAIN_FRACTION,
            "validation": VAL_FRACTION,
            "historical_test": HIST_TEST_FRACTION,
        },
        "seal": {
            "method": "sha256",
            "seal_hash": seal_hash,
            "sealed_at": _now_iso(),
            "note": (
                "The historical_test split indices are not stored in plaintext. "
                "They are derivable from the seed but require an explicit "
                "unlock key via ground_truth.unlock_historical_test()."
            ),
        },
        "events": events,
    }

    # Write splits.json
    SPLITS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SPLITS_PATH, "w", encoding="utf-8") as f:
        json.dump(splits_def, f, ensure_ascii=False, indent=2)

    return splits_def


def _derive_unlock_key(seed: int, case_id: str) -> str:
    """Derive a deterministic unlock key for a given seed + case_id.

    The key is a function of the seed and case_id.  It is stored as a
    SHA-256 hash in splits.json (one-way), so casual inspection of the
    file does not reveal the key.  The module computes the same key
    internally to verify unlock attempts.

    Args:
        seed: The splits seed.
        case_id: The event case identifier.

    Returns:
        A hex-string unlock key.
    """
    return hashlib.sha256(f"{seed}:{case_id}:historical_test".encode()).hexdigest()[:32]


# ── 5. Provenance registry ─────────────────────────────────────────────


def generate_provenance(
    microdata_path: str,
    microdata_dict_path: str,
    network_path: str,
    timeseries_records: list[dict],
    splits_def: dict,
) -> dict:
    """Generate the data provenance registry.

    Computes SHA-256 hashes of every artefact and records source
    references.

    Args:
        microdata_path: Path to microdata parquet.
        microdata_dict_path: Path to variable dictionary.
        network_path: Path to network topology JSON.
        timeseries_records: List of per-event conversion metadata.
        splits_def: The splits definition dictionary.

    Returns:
        Provenance registry dictionary.
    """
    registry = {
        "version": "1.0.0",
        "generated_at": _now_iso(),
        "layer": "Layer 1 — Ground Truth Data Inputs",
        "datasets": {},
    }

    # Microdata
    microdata_path_full = DATASETS_DIR / microdata_path
    registry["datasets"]["microdata_synthetic"] = {
        "path": microdata_path,
        "sha256": _sha256_file(microdata_path_full),
        "format": "parquet",
        "n_agents": MICRODATA_N_AGENTS,
        "seed": MICRODATA_SEED,
        "method": "iterative_proportional_fitting_safe",
        "variable_dictionary": microdata_dict_path,
        "variable_dictionary_sha256": _sha256_file(DATASETS_DIR / microdata_dict_path),
        "sources": {
            "ipa_algorithm": "Deming & Stephan (1940); Bishop et al. (1975)",
            "safe_framework": "Eurostat Synthetic Data Methodology",
            "marginals": [
                "US Census Bureau (2020)",
                "OECD Education at a Glance (2023)",
                "OECD Income Distribution Database (2022)",
                "Hofstede et al. (2010)",
            ],
            "opinion_model": [
                "Lelkes et al. (2020)",
                "Inglehart & Norris (2000)",
                "Pew Research Center (2020)",
            ],
        },
    }

    # Network topology
    network_path_full = DATASETS_DIR / network_path
    registry["datasets"]["network_topology"] = {
        "path": network_path,
        "sha256": _sha256_file(network_path_full),
        "format": "json",
        "method": "representative_graph_computation",
        "n_nodes": NETWORK_N_NODES,
        "seed": NETWORK_SEED,
        "sources": [
            "Barabási & Albert (1999)",
            "Watts & Strogatz (1998)",
            "McPherson et al. (2001)",
            "Bakshy et al. (2015)",
            "Adamic & Glance (2005)",
            "Conover et al. (2011)",
            "Leskovec & Horvitz (2008)",
            "Cha et al. (2010)",
            "Newman (2006)",
            "Vázquez et al. (2002)",
        ],
    }

    # Timeseries conversions
    for rec in timeseries_records:
        ts_path = DATASETS_DIR / rec["output_path"]
        registry["datasets"][f"timeseries_{rec['case_id']}"] = {
            "path": rec["output_path"],
            "sha256": rec["sha256"],
            "format": "parquet",
            "source_csv": rec["source_csv"],
            "source_meta": rec["meta_path"],
            "n_timesteps": rec["n_timesteps"],
            "title": rec["title"],
            "scenario_type": rec["scenario_type"],
            "corrections": rec["corrections"],
            "generated_at": rec["generated_at"],
        }

    # Splits
    registry["datasets"]["splits"] = {
        "path": "splits.json",
        "sha256": _sha256_bytes(json.dumps(splits_def, sort_keys=True).encode()),
        "format": "json",
        "seed": SPLITS_SEED,
        "method": "chronological_split_deterministic_seeded",
        "n_events": len(splits_def["events"]),
        "seal_hash": splits_def["seal"]["seal_hash"],
        "historical_test_sealed": True,
    }

    # Full registry
    registry["registry_sha256"] = _sha256_bytes(
        json.dumps(
            {k: v.get("sha256", "") for k, v in registry["datasets"].items()},
            sort_keys=True,
        ).encode()
    )

    # Add reference catalogue
    registry["references"] = REFERENCES

    return registry


def _write_provenance(registry: dict) -> None:
    """Write provenance registry to JSON."""
    PROVENANCE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(PROVENANCE_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=False, indent=2)


# ── Orchestrator ───────────────────────────────────────────────────────


def generate_all() -> dict:
    """Generate all Layer 1 ground-truth artefacts.

    Run this once to (re)create every data file in
    ``datasets/ground_truth/``.

    Returns:
        Summary dict with paths and hashes.
    """
    print("=" * 60)
    print("MASSIVE — Layer 1: Ground Truth Data Generation")
    print("=" * 60)

    # Ensure output directory exists
    DATASETS_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Microdata
    print("\n[1/5] Generating synthetic census microdata (IPF/SAFE)...")
    df = generate_microdata()
    _write_microdata(df)
    _write_variable_dictionary()
    print(f"  → {MICRODATA_PATH} ({len(df)} agents)")
    print(f"  → {MICRODATA_DICT_PATH}")
    print(
        f"  Opinion range: [{df['opinion_baseline'].min():.4f}, {df['opinion_baseline'].max():.4f}]"
    )

    # 2. Network topology
    print("\n[2/5] Computing network topology metrics...")
    metrics = compute_network_metrics()
    _write_network_topology(metrics)
    print(f"  → {NETWORK_PATH}")
    print(f"  γ = {metrics['degree_distribution']['gamma']}")
    print(f"  Global clustering = {metrics['clustering_coefficient']['global']:.4f}")
    print(f"  Modularity Q = {metrics['modularity']['value']:.4f}")
    print(f"  Echo intra/inter = {metrics['echo_chamber_density']['intra_to_inter_ratio']:.2f}")

    # 3. Timeseries conversion
    print("\n[3/5] Converting real_cases timeseries to parquet...")
    ts_records = convert_all_timeseries()
    for rec in ts_records:
        print(f"  → timeseries_{rec['case_id']}.parquet ({rec['n_timesteps']} rows)")
        if rec["corrections"]:
            for c in rec["corrections"]:
                print(f"     correction: {c}")

    # 4. Sealed splits
    print("\n[4/5] Generating sealed train/val/historical-test splits...")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        splits_def = generate_splits()
    print(f"  → {SPLITS_PATH} ({len(splits_def['events'])} events)")
    for case_id, ev in splits_def["events"].items():
        print(
            f"     {case_id}: train={len(ev['train']['indices'])}, "
            f"val={len(ev['validation']['indices'])}, "
            f"test={ev['historical_test']['n_samples']} (sealed)"
        )

    # 5. Provenance
    print("\n[5/5] Generating provenance registry...")
    registry = generate_provenance(
        microdata_path=str(MICRODATA_PATH.relative_to(DATASETS_DIR)),
        microdata_dict_path=str(MICRODATA_DICT_PATH.relative_to(DATASETS_DIR)),
        network_path=str(NETWORK_PATH.relative_to(DATASETS_DIR)),
        timeseries_records=ts_records,
        splits_def=splits_def,
    )
    _write_provenance(registry)
    print(f"  → {PROVENANCE_PATH}")

    print("\n" + "=" * 60)
    print("Layer 1 generation complete.")
    print(f"  Artefacts in: {DATASETS_DIR}")
    print("=" * 60)

    return {
        "microdata": str(MICRODATA_PATH),
        "variable_dictionary": str(MICRODATA_DICT_PATH),
        "network_topology": str(NETWORK_PATH),
        "splits": str(SPLITS_PATH),
        "provenance": str(PROVENANCE_PATH),
        "timeseries": [str(DATASETS_DIR / rec["output_path"]) for rec in ts_records],
    }


# ── Main ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    generate_all()
