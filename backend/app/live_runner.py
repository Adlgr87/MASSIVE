"""Live simulation runners for the UI-NG WebSocket endpoint.

Two engines are exposed tick-by-tick over WebSocket:

- **energy**: ``SocialEnergyEngine`` stepped one tick at a time over a
  generated network. Snapshots include every agent (``SimAgentLite``) with a
  stable 2D position, so the frontend can render the social network live.
- **massive**: ``MassiveSimEngine`` advanced in chunks; snapshots are
  aggregate-only (super-agents, no per-agent payload). Accepts mid-run
  shocks (``apply_shock``) for interactive what-if analysis.

Both runners emit the existing contract in ``backend/app/models/
dto_simulation.py`` (``SimSnapshotMessage`` / ``SimEventMessage``) — the DTOs
the repository already reserved for live streaming.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import networkx as nx
import numpy as np

from backend.app.models.dto_simulation import (
    SimAgentLite,
    SimAggregateMetrics,
    SimMode,
    SimulationSnapshotPayload,
)

log = logging.getLogger("massive.ui_ng.live")

SCHEMA_VERSION = "2.0.0"


def _clip_payload_opinion(v: float) -> float:
    return float(max(-1.0, min(1.0, v)))


class LiveEnergySim:
    """Step-wise Langevin social-energy simulation with agent-level snapshots."""

    def __init__(
        self,
        *,
        n_agents: int = 60,
        connectivity: float = 0.25,
        range_type: str = "bipolar",
        seed: int = 42,
        user_goal: str = "polarizacion_moderada",
        temperature: Optional[float] = None,
        lambda_social: Optional[float] = None,
    ) -> None:
        from energy_engine import SocialEnergyEngine, random_network
        from energy_schemas import EnergyConfig
        from programmatic_architect import ProgrammaticArchitect

        self.n_agents = int(n_agents)
        self.range_type = range_type
        self.min_val = -1.0 if range_type == "bipolar" else 0.0
        self.max_val = 1.0

        # Landscape: archetype lookup (deterministic, no LLM call needed).
        architect = ProgrammaticArchitect(range_type=range_type, llm_client=None)
        landscape = architect.get_landscape(user_goal)
        params = EnergyConfig.model_validate(landscape).to_engine_dict()
        self.attractors = params["attractors"]
        self.repellers = params["repellers"]
        dynamics = params["dynamics"]
        self.temperature = float(
            temperature if temperature is not None else dynamics.get("temperature", 0.05)
        )
        self.lambda_social = float(
            lambda_social if lambda_social is not None else dynamics.get("lambda_social", 0.5)
        )
        self.eta = float(dynamics.get("eta", 0.01))

        self.engine = SocialEnergyEngine(
            range_type=range_type,
            temperature=self.temperature,
            lambda_social=self.lambda_social,
            seed=seed,
        )
        rng = np.random.default_rng(seed)
        self.adj = random_network(self.n_agents, connectivity=connectivity, seed=seed)
        self.opinions = rng.uniform(self.min_val, self.max_val, size=self.n_agents)
        self._prev_opinions = self.opinions.copy()

        # Stable 2D positions for rendering (spring layout of the network).
        graph = nx.from_numpy_array(self.adj)
        pos = nx.spring_layout(graph, seed=seed, iterations=60)
        raw = np.array([pos[i] for i in range(self.n_agents)], dtype=float)
        raw -= raw.min(axis=0)
        span = raw.max(axis=0)
        span[span == 0] = 1.0
        self.positions = (raw / span) * 2.0 - 1.0  # → [-1, 1]²

        self.tick = 0

    # ── public API ────────────────────────────────────────────────────────
    def step(self) -> None:
        """Advance exactly one integration tick."""
        self.opinions = self.engine.step(
            self.opinions, self.adj, self.attractors, self.repellers, eta=self.eta
        )
        self._prev_opinions = self.opinions.copy()
        self.tick += 1

    def snapshot(self) -> SimulationSnapshotPayload:
        """Build the aggregate metrics + agent list for the current tick."""
        metrics_dict = self.engine.system_metrics(
            self.opinions, self.adj, self.attractors, self.repellers
        )
        n = self.n_agents
        mean = float(metrics_dict["mean_opinion"])
        std = float(metrics_dict["std_opinion"])
        # Consensus: fraction within a narrow band around the mean.
        consensus_rate = float(np.mean(np.abs(self.opinions - mean) < 0.15))
        # Fragmentation: approximate opinion clusters, normalized to [0, 1].
        n_clusters = int(metrics_dict.get("n_clusters_approx", 1))
        fragmentation = min(1.0, n_clusters / max(1, n / 8))
        # Active agents: those still moving (>1e-4 change last tick).
        moved = np.abs(self.opinions - self._prev_opinions) > 1e-4
        active_agents = int(np.sum(moved)) if self.tick > 0 else n

        metrics = SimAggregateMetrics(
            mean_opinion=mean,
            std_opinion=std,
            polarization=float(metrics_dict["polarizacion"]),
            dominant_rule="langevin_energy",
            consensus_rate=consensus_rate,
            fragmentation_index=fragmentation,
            active_agents=active_agents,
            schema_version=SCHEMA_VERSION,
        )
        agents = [
            SimAgentLite(
                id=f"a{i}",
                layer="social",
                x=float(self.positions[i, 0]),
                y=float(self.positions[i, 1]),
                opinion=_clip_payload_opinion(float(self.opinions[i])),
                metadata={
                    "energy": float(metrics_dict["energia_media"]),
                },
            )
            for i in range(n)
        ]
        return SimulationSnapshotPayload(
            tick=self.tick, metrics=metrics, agents=agents, mode=SimMode.live
        )


class LiveMassiveSim:
    """Chunked super-agent simulation with interactive shocks."""

    def __init__(
        self,
        *,
        n_agents: int = 5_000,
        seed: int = 42,
        quantize: bool = True,
        event_driven: bool = True,
        chunk_steps: int = 5,
    ) -> None:
        from massive_engine import MassiveSimEngine

        self.chunk_steps = int(chunk_steps)
        self.engine = MassiveSimEngine(
            N=int(n_agents),
            M=None,
            seed=seed,
            quantize=quantize,
            event_driven=event_driven,
        )
        self.n_agents = int(self.engine.N)
        self.n_clusters = int(self.engine.M)
        self.tick = 0
        self._mean_history: list[float] = []
        self._active_history: list[float] = []

    def step(self) -> None:
        """Advance one chunk of integration ticks."""
        result = self.engine.run(steps=self.chunk_steps)
        self.tick += self.chunk_steps
        history = np.asarray(result["opinion_history"], dtype=float)
        active = np.asarray(result["active_history"], dtype=float)
        self._mean_history = history.tolist()
        self._active_history = active.tolist()
        self._last_result = result

    def shock(self, value: float, fraction: float) -> None:
        """Apply an external perturbation to a fraction of super-agents."""
        self.engine.apply_shock(
            shock_value=float(value),
            fraction=float(np.clip(fraction, 0.01, 1.0)),
            seed=self.tick,  # deterministic per tick
        )
        log.info("massive shock applied: value=%s fraction=%s", value, fraction)

    def snapshot(self) -> SimulationSnapshotPayload:
        result = self._last_result
        active_frac = (
            float(np.asarray(result["active_history"])[-1])
            if len(np.asarray(result["active_history"])) > 0
            else 1.0
        )
        metrics = SimAggregateMetrics(
            mean_opinion=float(result["mean_opinion"]),
            std_opinion=float(result["std_opinion"]),
            polarization=float(result["polarization"]),
            dominant_rule="super_agents_langevin",
            consensus_rate=float(1.0 - active_frac),
            fragmentation_index=float(np.clip(result["polarization"], 0.0, 1.0)),
            active_agents=int(round(active_frac * self.n_clusters)),
            schema_version=SCHEMA_VERSION,
        )
        return SimulationSnapshotPayload(
            tick=self.tick,
            metrics=metrics,
            agents=None,  # aggregate-only: no per-agent payload at this scale
            mode=SimMode.live,
        )
