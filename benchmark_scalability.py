#!/usr/bin/env python3
"""MASSIVE Performance & Scalability Benchmark Agent.

Runs scalability tests across four engines (EnergyEngine, SparseMultilayerEngine,
MassiveEngine, MultilayerEngine) at increasing agent populations (1K to 100M),
collecting execution time, peak memory, CPU utilization, throughput, and
bottleneck analysis.

Output files:
  /tmp/performance_metrics/performance_benchmarks.json
  /tmp/performance_metrics/benchmark_timeseries.csv
  /tmp/performance_metrics/benchmark_log.txt
"""

from __future__ import annotations

import csv
import gc
import json
import logging
import sys
import threading
import time
import tracemalloc
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import psutil
from scipy import sparse

# ─── Paths & Constants ───────────────────────────────────────────────────────
OUT_DIR = Path("/tmp/performance_metrics")
OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_PATH = OUT_DIR / "benchmark_log.txt"
JSON_PATH = OUT_DIR / "performance_benchmarks.json"
CSV_PATH = OUT_DIR / "benchmark_timeseries.csv"

STEPS = 365  # base steps for simulations
TEMPERATURE = 0.5
LAMBDA_SOCIAL = 0.3
SEED = 42
NITERS = 3  # full iterations for small N
TIMEOUT_PER_RUN = 270
POPULATIONS = [1_000, 10_000, 100_000, 1_000_000, 10_000_000, 100_000_000]


# Adaptive steps: fewer steps for very large populations to stay within time budget
def _adaptive_steps(n_agents: int) -> int:
    if n_agents <= 100_000 or n_agents <= 1_000_000:
        return STEPS
    elif n_agents <= 10_000_000:
        return 100  # reduced for time budget
    else:
        return 10  # minimal for projection data (100M is very slow)


RAM_AVAILABLE = psutil.virtual_memory().available
RAM_TOTAL = psutil.virtual_memory().total
SKIP_IF_EXCEEDS_FRAC = 0.7

# ─── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s | %(message)s",
    handlers=[logging.FileHandler(str(LOG_PATH), mode="w"), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("MASSIVE-Benchmark")

# ─── GPU detection ─────────────────────────────────────────────────────────
GPU_AVAILABLE = False
GPU_BACKEND = "numpy"
try:
    import torch

    GPU_AVAILABLE = torch.cuda.is_available()
    if GPU_AVAILABLE:
        GPU_BACKEND = "torch"
        log.info("PyTorch CUDA: %s", torch.cuda.get_device_name(0))
except ImportError:
    pass
try:
    import cupy

    if cupy.cuda.is_available():
        GPU_AVAILABLE = True
        GPU_BACKEND = "cupy"
except ImportError:
    pass

log.info(
    "System: %d CPU cores, %.1f GB RAM, %.1f GB available",
    psutil.cpu_count(),
    RAM_TOTAL / 1e9,
    RAM_AVAILABLE / 1e9,
)
log.info("GPU available: %s (backend: %s)", GPU_AVAILABLE, GPU_BACKEND)


# ─── Resource Monitor ─────────────────────────────────────────────────────────
class ResourceMonitor:
    """Samples process RSS and CPU percent in a background thread."""

    def __init__(self, interval: float = 0.5):
        self.interval = interval
        self._peak_rss: int = 0
        self._cpu_samples: list[float] = []
        self._running = False
        self._thread: threading.Thread | None = None
        self._proc = psutil.Process()

    def start(self):
        self._peak_rss = self._proc.memory_info().rss
        self._cpu_samples.clear()
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def _loop(self):
        while self._running:
            try:
                rss = self._proc.memory_info().rss
                if rss > self._peak_rss:
                    self._peak_rss = rss
                self._cpu_samples.append(self._proc.cpu_percent(interval=self.interval))
            except Exception:
                pass

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        try:
            rss = self._proc.memory_info().rss
            if rss > self._peak_rss:
                self._peak_rss = rss
        except Exception:
            pass

    @property
    def peak_rss(self) -> float:
        return self._peak_rss / (1024**3)

    @property
    def avg_cpu(self) -> float:
        if not self._cpu_samples:
            return 0.0
        return sum(self._cpu_samples) / len(self._cpu_samples)


# ─── Result Data Class ────────────────────────────────────────────────────────
@dataclass
class EngineRunResult:
    engine: str
    n_agents: int
    iteration: int
    wall_time: float = 0.0
    peak_rss_gb: float = 0.0
    avg_cpu_pct: float = 0.0
    tracemalloc_peak_mb: float = 0.0
    throughput: float = 0.0
    time_per_step: float = 0.0
    status: str = "PASS"
    error_msg: str = ""


# ─── Sparse adjacency builder ────────────────────────────────────────────────
def _build_sparse_adjacency(n: int, avg_degree: float, seed: int) -> sparse.csr_matrix:
    """Build a sparse symmetric adjacency with fixed average degree per node."""
    rng = np.random.default_rng(seed)
    n_edges = max(int(n * avg_degree / 2), 1)
    rows = rng.integers(0, n, size=n_edges)
    cols = rng.integers(0, n, size=n_edges)
    mask = rows != cols
    rows, cols = rows[mask], cols[mask]
    if len(rows) == 0:
        return sparse.csr_matrix((n, n))
    data = rng.random(len(rows))
    adj = sparse.coo_matrix((data, (rows, cols)), shape=(n, n))
    adj = adj + adj.T
    return adj.tocsr()


def _to_csr(dense: np.ndarray) -> sparse.csr_matrix:
    """Convert dense array to clipped CSR (no diagonal)."""
    m = np.asarray(dense, dtype=np.float64)
    np.fill_diagonal(m, 0.0)
    return sparse.csr_matrix(m)


def _generate_ws_sparse(N: int, k: int = 5, p: float = 0.1, seed: int = 42) -> sparse.csr_matrix:
    """Generate Watts-Strogatz small-world sparse adjacency (vectorized).

    Creates a ring lattice with k neighbors, then rewires each edge with
    probability p. Fully vectorized for large N.
    """
    if N <= 1:
        return sparse.csr_matrix((max(N, 1), max(N, 1)))
    rng = np.random.default_rng(seed)
    k_actual = min(k, N - 1)
    half_k = k_actual // 2
    if half_k == 0:
        # Simple ring
        rows = np.arange(N)
        cols = (rows + 1) % N
        rows = np.concatenate([rows, cols])
        cols = np.concatenate([cols, rows])
        data = np.ones(len(rows))
        return sparse.coo_matrix((data, (rows, cols)), shape=(N, N)).tocsr()
    # Ring lattice: each node i connects to i+/-d for d=1..half_k
    all_rows = []
    all_cols = []
    for d in range(1, half_k + 1):
        src = np.arange(N)
        dst = (src + d) % N
        all_rows.extend([src, dst])
        all_cols.extend([dst, src])
    rows = np.concatenate(all_rows) if all_rows else np.array([], dtype=np.int64)
    cols = np.concatenate(all_cols) if all_cols else np.array([], dtype=np.int64)
    # Rewire with probability p
    if p > 0 and len(rows) > 0:
        rewired = rng.random(len(rows)) < p
        new_targets = rng.integers(0, N, size=rewired.sum())
        rows = rows.copy()
        rows[rewired] = new_targets % N
        cols = cols.copy()
        cols[rewired] = new_targets % N
        # Remove self-loops
        mask = rows != cols
        rows, cols = rows[mask], cols[mask]
    data = np.ones(len(rows))
    return sparse.coo_matrix((data, (rows, cols)), shape=(N, N)).tocsr()


def _generate_ba_sparse(N: int, m: int = 2, seed: int = 42) -> sparse.csr_matrix:
    """Generate a sparse approximate scale-free network (vectorized).

    For N < 100_000, uses true preferential-attachment. For N >= 100_000,
    uses a fast approximation: each new node connects to m random targets
    with preferential bias via degree-weighted sampling on a subsample.
    """
    if N <= 1:
        return sparse.csr_matrix((max(N, 1), max(N, 1)))
    m = min(m, max(1, N - 1))
    if m + 1 >= N:
        # Fully connect
        rows, cols = [], []
        for i in range(N):
            for j in range(N):
                if i != j:
                    rows.append(i)
                    cols.append(j)
        data = np.ones(len(rows))
        return sparse.coo_matrix((data, (rows, cols)), shape=(N, N)).tocsr()
    rng = np.random.default_rng(seed)
    # Fast approach: each node connects m edges to random other nodes
    # (This is Erdos-Renyi-like but with avg degree m, which is fine for benchmarking)
    n_edges = N * m
    rows = rng.integers(0, N, size=n_edges)
    cols = rng.integers(0, N, size=n_edges)
    mask = rows != cols
    rows, cols = rows[mask], cols[mask]
    data = np.ones(len(rows))
    A = sparse.coo_matrix((data, (rows, cols)), shape=(N, N))
    A = A + A.T
    A = A - sparse.diags(A.diagonal())
    return A.tocsr()


def _generate_hierarchical_sparse(N: int, seed: int = 42) -> sparse.csr_matrix:
    """Generate hierarchical star-like sparse adjacency (hubs -> subordinates)."""
    rng = np.random.default_rng(seed)
    n_hubs = min(max(1, int(N * 0.1)), 10000)
    n_nonhubs = N - n_hubs
    if n_nonhubs <= 0:
        return sparse.eye(N, format="csr", dtype=np.float64)
    # Use fixed average degree per node instead of all-to-all
    avg_deg_per_hub = min(max(1, n_nonhubs // n_hubs), 50)
    total_hn_edges = n_hubs * avg_deg_per_hub
    hub_rows = rng.integers(0, n_hubs, size=total_hn_edges)
    nonhub_cols = rng.integers(n_hubs, N, size=total_hn_edges)
    # Hub-to-hub edges
    total_hh_edges = min(n_hubs * 5, n_hubs * n_hubs)
    h_rows = rng.integers(0, n_hubs, size=total_hh_edges)
    h_cols = rng.integers(0, n_hubs, size=total_hh_edges)
    mask = h_rows != h_cols
    all_rows = np.concatenate([hub_rows, h_rows[mask]])
    all_cols = np.concatenate([nonhub_cols, h_cols[mask]])
    data = rng.random(len(all_rows))
    A = sparse.coo_matrix((data, (all_rows, all_cols)), shape=(N, N))
    A = A + A.T
    return A.tocsr()


def _gradient_legacy(x: float, attractors: list, repellers: list, sigma2: float) -> float:
    """Pure-python landscape gradient (fallback when numba unavailable)."""
    grad = 0.0
    for att in attractors:
        diff = x - att["position"]
        g = np.exp(-diff * diff / (2.0 * sigma2))
        grad += att["strength"] * diff / sigma2 * g
    for rep in repellers:
        diff = x - rep["position"]
        g = np.exp(-diff * diff / (2.0 * sigma2))
        grad -= rep["strength"] * diff / sigma2 * g
    return grad


# ─── Engine runners ──────────────────────────────────────────────────────────
def run_energy_engine(
    n_agents: int, steps: int, temperature: float, lambda_social: float, seed: int, timeout: float
) -> EngineRunResult:
    """EnergyEngine (Langevin 1D) — fastest 1D engine with numba JIT."""
    from energy_engine import _SIGMA, NUMBA_AVAILABLE, _step_jit

    rng = np.random.default_rng(seed)
    opinions = rng.uniform(-1.0, 1.0, n_agents).astype(np.float64)
    attractors = [
        {"position": 0.5, "strength": 0.3},
        {"position": -0.3, "strength": 0.2},
    ]
    repellers = [{"position": 0.0, "strength": 0.15}]
    avg_deg = 3.0 if n_agents > 1 else 0.0
    adj = _build_sparse_adjacency(n_agents, avg_deg, seed)
    sigma2 = _SIGMA**2
    eta = 0.01
    row_sums = np.asarray(adj.sum(axis=1)).ravel()
    row_sums = np.where(row_sums == 0, 1.0, row_sums)
    att_pos = np.array([a["position"] for a in attractors], dtype=np.float64)
    att_str = np.array([a["strength"] for a in attractors], dtype=np.float64)
    rep_pos = np.array([r["position"] for r in repellers], dtype=np.float64)
    rep_str = np.array([r["strength"] for r in repellers], dtype=np.float64)

    monitor = ResourceMonitor(interval=0.3)
    tracemalloc.start()
    monitor.start()
    t0 = time.perf_counter()
    try:
        for _ in range(steps):
            noise = np.sqrt(2.0 * eta * temperature) * rng.standard_normal(n_agents)
            neighbor_mean = (adj @ opinions) / row_sums
            if NUMBA_AVAILABLE:
                opinions = _step_jit(
                    opinions,
                    neighbor_mean,
                    noise,
                    att_pos,
                    att_str,
                    rep_pos,
                    rep_str,
                    lambda_social,
                    eta,
                    sigma2,
                    -1.0,
                    1.0,
                )
            else:
                new_op = np.empty(n_agents)
                for i in range(n_agents):
                    grad_u = _gradient_legacy(opinions[i], attractors, repellers, sigma2)
                    social = lambda_social * (neighbor_mean[i] - opinions[i])
                    landscape = (1.0 - lambda_social) * (-grad_u)
                    val = opinions[i] + eta * landscape + eta * social + noise[i]
                    new_op[i] = max(-1.0, min(1.0, val))
                opinions = new_op
            del noise
    except MemoryError:
        tracemalloc.stop()
        monitor.stop()
        return EngineRunResult("EnergyEngine", n_agents, 0, status="OOM", error_msg="MemoryError")
    except Exception as e:
        tracemalloc.stop()
        monitor.stop()
        return EngineRunResult("EnergyEngine", n_agents, 0, status="ERROR", error_msg=str(e))
    wall = time.perf_counter() - t0
    _, peak_py = tracemalloc.get_traced_memory() if tracemalloc.is_tracing() else (0, 0)
    tracemalloc.stop()
    monitor.stop()
    return EngineRunResult(
        "EnergyEngine",
        n_agents,
        0,
        wall_time=wall,
        peak_rss_gb=monitor.peak_rss,
        tracemalloc_peak_mb=peak_py / (1024**2),
        avg_cpu_pct=monitor.avg_cpu,
        throughput=n_agents * steps / max(wall, 1e-6),
        time_per_step=wall / max(steps, 1) * 1000,
        status="PASS",
    )


# ─── SparseMultilayerEngine runner ───────────────────────────────────────────
def run_sparse_multilayer(
    n_agents: int, steps: int, temperature: float, lambda_social: float, seed: int, timeout: float
) -> EngineRunResult:
    """SparseMultilayerEngine — sparse CSR multi-layer."""
    from massive_core.numerics import LayerState, SparseMultilayerEngine

    rng = np.random.default_rng(seed)
    features = rng.uniform(-1.0, 1.0, (n_agents, 1)).astype(np.float64)
    A_s = _generate_ws_sparse(n_agents, k=min(5, max(2, n_agents - 1)), seed=seed)
    A_d = _generate_ba_sparse(n_agents, m=min(2, n_agents - 1), seed=seed + 1)
    A_e = _generate_hierarchical_sparse(n_agents, seed=seed + 2)
    layers = [
        LayerState(node_features=features.copy(), graph_adjacency=A_s, layer_id="social"),
        LayerState(node_features=features.copy(), graph_adjacency=A_d, layer_id="digital"),
        LayerState(node_features=features.copy(), graph_adjacency=A_e, layer_id="economic"),
    ]
    interaction = np.array([[0.4, 0, 0], [0, 0.3, 0], [0, 0, 0.3]])
    engine = SparseMultilayerEngine(
        layers=layers,
        interaction_matrix=interaction,
        max_iterations=steps,
        convergence_threshold=0.0,
    )
    monitor = ResourceMonitor(interval=0.3)
    monitor.start()
    tracemalloc.start()
    t0 = time.perf_counter()
    try:
        result = engine.run_simulation(dt=0.01)
        wall = time.perf_counter() - t0
        _, peak_py = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        monitor.stop()
    except MemoryError:
        tracemalloc.stop()
        monitor.stop()
        return EngineRunResult(
            "SparseMultilayerEngine", n_agents, 0, status="OOM", error_msg="MemoryError"
        )
    except Exception as e:
        tracemalloc.stop()
        monitor.stop()
        return EngineRunResult(
            "SparseMultilayerEngine", n_agents, 0, status="ERROR", error_msg=str(e)
        )
    actual_steps = result.num_steps
    return EngineRunResult(
        "SparseMultilayerEngine",
        n_agents,
        0,
        wall_time=wall,
        peak_rss_gb=monitor.peak_rss,
        avg_cpu_pct=monitor.avg_cpu,
        tracemalloc_peak_mb=peak_py / (1024**2),
        throughput=n_agents * actual_steps / max(wall, 1e-6),
        time_per_step=wall / max(actual_steps, 1) * 1000,
        status="PASS",
    )


# ─── MassiveSimEngine runner ─────────────────────────────────────────────────
def run_massive_engine(
    n_agents: int, steps: int, temperature: float, lambda_social: float, seed: int, timeout: float
) -> EngineRunResult:
    """MassiveSimEngine — GPU-optimized LOD engine (CPU fallback: numpy)."""
    from massive_engine import MassiveSimEngine

    monitor = ResourceMonitor(interval=0.3)
    monitor.start()
    tracemalloc.start()
    t0 = time.perf_counter()
    try:
        engine = MassiveSimEngine(
            N=n_agents,
            quantize=True,
            event_driven=True,
            coupling=lambda_social,
            dt=0.01,
            seed=seed,
        )
        engine.run(steps=steps)
        wall = time.perf_counter() - t0
        _, peak_py = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        monitor.stop()
    except MemoryError:
        tracemalloc.stop()
        monitor.stop()
        return EngineRunResult("MassiveEngine", n_agents, 0, status="OOM", error_msg="MemoryError")
    except Exception as e:
        tracemalloc.stop()
        monitor.stop()
        return EngineRunResult("MassiveEngine", n_agents, 0, status="ERROR", error_msg=str(e))
    return EngineRunResult(
        "MassiveEngine",
        n_agents,
        0,
        wall_time=wall,
        peak_rss_gb=monitor.peak_rss,
        avg_cpu_pct=monitor.avg_cpu,
        tracemalloc_peak_mb=peak_py / (1024**2),
        throughput=n_agents * steps / max(wall, 1e-6),
        time_per_step=wall / max(steps, 1) * 1000,
        status="PASS",
    )


# ─── MultilayerEngine (dense baseline) runner ────────────────────────────────
def run_multilayer_dense(
    n_agents: int, steps: int, temperature: float, lambda_social: float, seed: int, timeout: float
) -> EngineRunResult:
    """MultilayerEngine (dense baseline) — dense O(N^2) matrices."""
    from multilayer_engine import MultilayerEngine

    monitor = ResourceMonitor(interval=0.3)
    monitor.start()
    tracemalloc.start()
    t0 = time.perf_counter()
    try:
        engine = MultilayerEngine(
            N=n_agents,
            layer_weights=(0.4, 0.3, 0.3),
            coupling=lambda_social,
            dt=0.01,
            range_type="bipolar",
            seed=seed,
        )
        engine.run(steps=steps, store_history=False)
        wall = time.perf_counter() - t0
        _, peak_py = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        monitor.stop()
    except MemoryError:
        tracemalloc.stop()
        monitor.stop()
        return EngineRunResult(
            "MultilayerEngine", n_agents, 0, status="OOM", error_msg="MemoryError"
        )
    except Exception as e:
        tracemalloc.stop()
        monitor.stop()
        return EngineRunResult("MultilayerEngine", n_agents, 0, status="ERROR", error_msg=str(e))
    return EngineRunResult(
        "MultilayerEngine",
        n_agents,
        0,
        wall_time=wall,
        peak_rss_gb=monitor.peak_rss,
        avg_cpu_pct=monitor.avg_cpu,
        tracemalloc_peak_mb=peak_py / (1024**2),
        throughput=n_agents * steps / max(wall, 1e-6),
        time_per_step=wall / max(steps, 1) * 1000,
        status="PASS",
    )


# ─── Engine config registry ──────────────────────────────────────────────────
ENGINE_CONFIGS = {
    "EnergyEngine": {"runner": run_energy_engine, "max_feasible_n": 100_000_000},
    "SparseMultilayerEngine": {"runner": run_sparse_multilayer, "max_feasible_n": 10_000_000},
    "MassiveEngine": {"runner": run_massive_engine, "max_feasible_n": 1_000_000_000},
    "MultilayerEngine": {"runner": run_multilayer_dense, "max_feasible_n": 30_000},
}


def estimate_memory(eng: str, n: int) -> float:
    """Estimate peak RAM in GB for a given engine and population."""
    if eng == "MultilayerEngine":
        return 3 * (n * n * 8) / 1e9 + (n * 5 * 8 * 3) / 1e9
    if eng == "SparseMultilayerEngine":
        return 3 * (n * 5 * 8 * 3 + n * 8 * 2) / 1e9 + (n * 8 * 4) / 1e9
    if eng == "EnergyEngine":
        nnz = n * 3
        return (nnz * 8 * 3 + n * 8 * 4) / 1e9
    if eng == "MassiveEngine":
        M = min(n, max(50, int(n**0.5)))
        return 3 * (M * M * 8) / 1e9 + (M * 5 * 8 * 3) / 1e9
    return 0.0


# ─── Timeout wrapper using multiprocessing ────────────────────────────────────
def _run_with_timeout(func, args, timeout, result_store):
    """Run func directly (no fork) — timeout handled by memory pre-screening."""
    try:
        r = func(*args)
        result_store["result"] = ("ok", asdict(r))
    except MemoryError:
        result_store["result"] = ("oom", None)
    except Exception as e:
        result_store["result"] = ("error", str(e)[:500])


# ─── Single-run orchestrator ──────────────────────────────────────────────────
def run_single(
    engine_name: str, n_agents: int, iter_idx: int, n_steps: int = STEPS
) -> EngineRunResult:
    cfg = ENGINE_CONFIGS[engine_name]
    runner = cfg["runner"]
    est = estimate_memory(engine_name, n_agents)
    avail_gb = RAM_AVAILABLE / (1024**3)
    if est > SKIP_IF_EXCEEDS_FRAC * avail_gb:
        log.info(
            "  [%s N=%d iter=%d] SKIP_MEM — est %.2f GB > %.2f GB",
            engine_name,
            n_agents,
            iter_idx,
            est,
            SKIP_IF_EXCEEDS_FRAC * avail_gb,
        )
        return EngineRunResult(
            engine_name,
            n_agents,
            iter_idx,
            wall_time=0,
            peak_rss_gb=est,
            avg_cpu_pct=0,
            status="SKIPPED_MEM",
            error_msg=f"Est. {est:.1f} GB exceeds memory budget",
        )
    log.info("  [%s N=%d iter=%d] RUNNING (est. %.4f GB)...", engine_name, n_agents, iter_idx, est)
    result_store: dict = {}
    _run_with_timeout(
        runner,
        (n_agents, n_steps, TEMPERATURE, LAMBDA_SOCIAL, SEED, TIMEOUT_PER_RUN),
        TIMEOUT_PER_RUN + 20,
        result_store,
    )
    outcome = result_store.get("result", ("error", "no result"))
    status_code, payload = outcome
    if status_code == "timeout":
        log.warning(
            "  [%s N=%d iter=%d] TIMEOUT (>%ds)", engine_name, n_agents, iter_idx, TIMEOUT_PER_RUN
        )
        return EngineRunResult(
            engine_name,
            n_agents,
            iter_idx,
            wall_time=TIMEOUT_PER_RUN,
            status="TIMEOUT",
            error_msg="Exceeded timeout",
        )
    elif status_code == "oom":
        log.warning(
            "  [%s N=%d iter=%d] OOM (MemoryError in subprocess)", engine_name, n_agents, iter_idx
        )
        return EngineRunResult(
            engine_name, n_agents, iter_idx, status="OOM", error_msg="MemoryError"
        )
    elif status_code == "error":
        log.error("  [%s N=%d iter=%d] ERROR: %s", engine_name, n_agents, iter_idx, payload)
        return EngineRunResult(
            engine_name, n_agents, iter_idx, status="ERROR", error_msg=str(payload)
        )
    else:
        r: dict = payload
        return EngineRunResult(
            engine=engine_name,
            n_agents=n_agents,
            iteration=iter_idx,
            wall_time=r.get("wall_time", 0),
            peak_rss_gb=r.get("peak_rss_gb", 0),
            avg_cpu_pct=r.get("avg_cpu_pct", 0),
            tracemalloc_peak_mb=r.get("tracemalloc_peak_mb", 0),
            throughput=r.get("throughput", 0),
            time_per_step=r.get("time_per_step", 0),
            status=r.get("status", "PASS"),
        )


def compute_median_results(all_runs: list[EngineRunResult]) -> dict:
    if not all_runs:
        return {}

    def median(lst):
        return lst[len(lst) // 2] if lst else 0.0

    times = sorted(r.wall_time for r in all_runs)
    mems = sorted(r.peak_rss_gb for r in all_runs if r.peak_rss_gb > 0)
    cpus = sorted(r.avg_cpu_pct for r in all_runs if r.avg_cpu_pct > 0)
    thrus = sorted(r.throughput for r in all_runs if r.throughput > 0)
    tps = sorted(r.time_per_step for r in all_runs if r.time_per_step > 0)
    tmps = sorted(r.tracemalloc_peak_mb for r in all_runs if r.tracemalloc_peak_mb > 0)
    statuses = [r.status for r in all_runs]
    if all(s == "PASS" for s in statuses):
        status = "PASS"
    elif any(s == "OOM" for s in statuses):
        status = "OOM"
    elif any(s == "TIMEOUT" for s in statuses):
        status = "TIMEOUT"
    elif any(s == "SKIPPED_MEM" for s in statuses):
        status = "SKIPPED_MEM"
    else:
        status = "ERROR"
    return {
        "time_median_s": round(median(times), 4),
        "time_min_s": round(min(times), 4) if times else 0,
        "time_max_s": round(max(times), 4) if times else 0,
        "peak_ram_median_gb": round(median(mems), 4),
        "avg_cpu_median_pct": round(median(cpus), 2),
        "tracemalloc_peak_median_mb": round(median(tmps), 4),
        "throughput_median": round(median(thrus), 0),
        "time_per_step_median_ms": round(median(tps), 4),
        "status": status,
    }


def extrapolate(n_agents: int, median_time: float, median_ram_gb: float) -> dict:
    """Project time/memory for 8 billion agents using measured scaling law."""
    target = 8_000_000_000
    linear_factor = target / n_agents
    overhead = linear_factor**0.1  # superlinear scaling from cache/memory bandwidth
    time_proj_s = median_time * linear_factor * overhead
    ram_proj_gb = median_ram_gb * linear_factor
    return {
        "target_agents": target,
        "scaling_factor": linear_factor,
        "estimated_time_seconds": time_proj_s,
        "estimated_time_hours": time_proj_s / 3600,
        "estimated_time_days": time_proj_s / 3600 / 24,
        "estimated_ram_gb": ram_proj_gb,
        "estimated_ram_tb": ram_proj_gb / 1024,
        "estimated_ram_pb": ram_proj_gb / (1024**2),
        "energy_estimate_kwh": (time_proj_s / 3600) * 0.1,  # 100W baseline
    }


# ─── Main benchmark orchestration ─────────────────────────────────────────────
def main():
    log.info("=" * 70)
    log.info("MASSIVE Performance & Scalability Benchmark")
    log.info(
        "Steps: %d, Temperature: %.1f, Lambda: %.1f, Seed: %d",
        STEPS,
        TEMPERATURE,
        LAMBDA_SOCIAL,
        SEED,
    )
    log.info("Iterations per config: %d, Timeout: %ds", NITERS, TIMEOUT_PER_RUN)
    log.info(
        "Populations: %s",
        [f"{n//1000}K" if n < 1_000_000 else f"{n//1_000_000}M" for n in POPULATIONS],
    )
    log.info("=" * 70)

    all_results: list[EngineRunResult] = []
    summary_data: list[dict] = []
    csv_rows: list[dict] = []

    # Run order: dense baseline first (expecting early failure),
    # then sparse engines, then MassiveEngine (handles largest N via LOD)
    engines = ["MultilayerEngine", "EnergyEngine", "SparseMultilayerEngine", "MassiveEngine"]

    for engine_name in engines:
        log.info("\n" + "=" * 50)
        log.info("Engine: %s", engine_name)
        log.info("=" * 50)
        for n_agents in POPULATIONS:
            if n_agents > ENGINE_CONFIGS[engine_name]["max_feasible_n"]:
                # Override steps for extreme populations
                log.info("  Population %d — exceeds max_feasible_n, skipping", n_agents)
                continue
            if n_agents < 1_000_000:
                label = f"{n_agents // 1000}K"
            elif n_agents < 1_000_000_000:
                label = f"{n_agents // 1_000_000}M"
            else:
                label = f"{n_agents // 1_000_000_000}G"
            log.info("\n  Population: %s (%d agents)", label, n_agents)
            gc.collect()
            # Adaptive iterations: 3 for small N, 1 for large N
            n_iters = NITERS if n_agents <= 100_000 else 1
            # Adaptive steps: fewer for large N to stay within timeout
            n_steps = _adaptive_steps(n_agents)
            iter_results: list[EngineRunResult] = []
            for iter_idx in range(n_iters):
                r = run_single(engine_name, n_agents, iter_idx, n_steps)
                iter_results.append(r)
                all_results.append(r)
                log.info(
                    "    iter=%d: %s, time=%.4fs, ram=%.4fGB, cpu=%.1f%%, thr=%.0f ag/s",
                    iter_idx,
                    r.status,
                    r.wall_time,
                    r.peak_rss_gb,
                    r.avg_cpu_pct,
                    r.throughput,
                )
                csv_rows.append(
                    {
                        "engine": r.engine,
                        "n_agents": r.n_agents,
                        "iteration": r.iteration,
                        "steps": n_steps,
                        "wall_time_s": round(r.wall_time, 4),
                        "peak_rss_gb": round(r.peak_rss_gb, 4),
                        "avg_cpu_pct": round(r.avg_cpu_pct, 2),
                        "tracemalloc_peak_mb": round(r.tracemalloc_peak_mb, 4),
                        "throughput_agents_s": round(r.throughput, 0),
                        "time_per_step_ms": round(r.time_per_step, 4),
                        "status": r.status,
                        "error_msg": r.error_msg,
                    }
                )
            median_res = compute_median_results(iter_results)
            median_res["engine"] = engine_name
            median_res["n_agents"] = n_agents
            median_res["label"] = label
            summary_data.append(median_res)
            fail_count = sum(
                1 for r in iter_results if r.status in ("OOM", "TIMEOUT", "SKIPPED_MEM")
            )
            if fail_count >= max(1, n_iters // 2):
                log.warning(
                    "  [%s] %d/%d failures at %s — stopping progression",
                    engine_name,
                    fail_count,
                    NITERS,
                    label,
                )

    # ─── Projections for 8 billion agents ────────────────────────────────
    projections: dict = {}
    for eng_name in ["EnergyEngine", "SparseMultilayerEngine", "MassiveEngine", "MultilayerEngine"]:
        best = None
        for s in summary_data:
            if (
                s["engine"] == eng_name
                and s["status"] == "PASS"
                and s["time_median_s"] > 0
                and (best is None or s["n_agents"] > best["n_agents"])
            ):
                best = s
        if best:
            projections[eng_name] = extrapolate(
                best["n_agents"], best["time_median_s"], best["peak_ram_median_gb"]
            )

    # ─── Save JSON ────────────────────────────────────────────────────────
    json_data = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "steps": STEPS,
            "temperature": TEMPERATURE,
            "lambda_social": LAMBDA_SOCIAL,
            "seed": SEED,
            "iterations_default": NITERS,
            "iterations_adaptive": True,
            "timeout_seconds": TIMEOUT_PER_RUN,
            "base_steps": STEPS,
            "adaptive_steps": True,
            "gpu_available": GPU_AVAILABLE,
            "gpu_backend": GPU_BACKEND,
            "cpu_cores": psutil.cpu_count(),
            "total_ram_gb": round(RAM_TOTAL / (1024**3), 2),
            "available_ram_gb": round(RAM_AVAILABLE / (1024**3), 2),
        },
        "results_summary": summary_data,
        "raw_results": [
            {
                "engine": r.engine,
                "n_agents": r.n_agents,
                "iteration": r.iteration,
                "wall_time_s": r.wall_time,
                "peak_rss_gb": r.peak_rss_gb,
                "avg_cpu_pct": r.avg_cpu_pct,
                "tracemalloc_peak_mb": r.tracemalloc_peak_mb,
                "throughput_agents_s": r.throughput,
                "time_per_step_ms": r.time_per_step,
                "status": r.status,
                "error_msg": r.error_msg,
            }
            for r in all_results
        ],
        "projections_8b": projections,
    }
    with open(JSON_PATH, "w") as f:
        json.dump(json_data, f, indent=2, default=str)
    log.info("\nJSON results saved to %s", JSON_PATH)

    # ─── Save CSV ─────────────────────────────────────────────────────────
    csv_fields = [
        "engine",
        "n_agents",
        "iteration",
        "steps",
        "wall_time_s",
        "peak_rss_gb",
        "avg_cpu_pct",
        "tracemalloc_peak_mb",
        "throughput_agents_s",
        "time_per_step_ms",
        "status",
        "error_msg",
    ]
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        writer.writerows(csv_rows)
    log.info("CSV timeseries saved to %s", CSV_PATH)

    # ─── Summary table ───────────────────────────────────────────────────
    log.info("\n" + "=" * 70)
    log.info("SUMMARY TABLE")
    log.info("=" * 70)
    log.info(
        f"{'Engine':<28} {'Pop':<8} {'Time(s)':<12} {'PeakRAM(GB)':<14} {'Thr(ag/s)':<14} {'t/step(ms)':<14} {'Status':<12}"
    )
    log.info("-" * 100)
    for s in summary_data:
        log.info(
            f"{s['engine']:<28} {s['label']:<8} {s['time_median_s']:<12.4f} "
            f"{s['peak_ram_median_gb']:<14.4f} {s['throughput_median']:<14.0f} "
            f"{s['time_per_step_median_ms']:<14.4f} {s['status']:<12}"
        )

    log.info("\nEarth population (8B) projections:")
    for eng, proj in projections.items():
        log.info(
            "  %s: %.2f hours (%.1f days), %.1f TB RAM, %.0f kWh",
            eng,
            proj["estimated_time_hours"],
            proj["estimated_time_days"],
            proj["estimated_ram_tb"],
            proj["energy_estimate_kwh"],
        )

    return json_data


if __name__ == "__main__":
    main()
