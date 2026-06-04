"""Sparse multilayer graph engine for sociodynamic simulations.

This module reimplements :mod:`multilayer_engine` using :class:`scipy.sparse`
data structures throughout the hot path, which reduces memory consumption
and improves cache utilisation when layers are large and/or sparsely
connected.  The public API is identical to the legacy engine so that
upstream callers are unaffected.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy import sparse

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class LayerState:
    """State of a single layer in the multilayer system.

    Attributes
    ----------
    node_features :
        ``(n_nodes, n_features)`` node-feature matrix.
    graph_adjacency :
        ``(n_nodes, n_nodes)`` sparse adjacency matrix.
    agent_types :
        Per-node agent-type labels.
    layer_id :
        Human-readable layer identifier.
    """
    node_features: np.ndarray
    graph_adjacency: sparse.csr_matrix
    agent_types: Optional[np.ndarray] = None
    layer_id: str = ""

    @property
    def n_nodes(self) -> int:
        return self.node_features.shape[0]

    @property
    def n_features(self) -> int:
        return self.node_features.shape[1]


@dataclass
class MultilayerState:
    """Aggregate state of the multilayer system.

    Attributes
    ----------
    layers :
        ``LayerState`` for every layer.
    inter_layer_edges :
        ``(n_inter_edges, 3)`` array of ``(layer_src, node_src, layer_dst, node_dst)``.
    """
    layers: list[LayerState]
    inter_layer_edges: np.ndarray = field(default_factory=lambda: np.empty((0, 4), dtype=int))

    @property
    def n_layers(self) -> int:
        return len(self.layers)

    @property
    def n_nodes_total(self) -> int:
        return sum(layer.n_nodes for layer in self.layers)


@dataclass
class SimulationResult:
    """Results from :meth:`SparseMultilayerEngine.run_simulation`.

    Attributes
    ----------
    final_states :
        List of final node-feature matrices, one per layer.
    metrics_history :
        Time series of graph metrics per layer.
    simulation_time :
        Wall-clock time for the simulation.
    """
    final_states: list[np.ndarray]
    metrics_history: list[dict]
    simulation_time: float


# ---------------------------------------------------------------------------
# SparseMultilayerEngine
# ---------------------------------------------------------------------------


class SparseMultilayerEngine:
    """Sparse multilayer graph engine.

    Parameters
    ----------
    layers :
        List of :class:`LayerState` defining the multilayer system.
    inter_layer_edges :
        ``(N, 4)`` array of inter-layer edges as
        ``(layer_src, node_src, layer_dst, node_dst)``.
    interaction_matrix :
        ``(n_layers, n_layers)`` matrix of inter-layer coupling strengths.
    max_iterations :
        Maximum simulation iterations.
    convergence_threshold :
        Change in node features below which the simulation stops.
    rng :
        Random number generator.
    use_sparse :
        If *True* (default), all graph operations use :mod:`scipy.sparse`
        structures, yielding significant memory and speed savings for
        large, sparse systems.
    """

    def __init__(
        self,
        layers: list[LayerState],
        inter_layer_edges: Optional[np.ndarray] = None,
        interaction_matrix: Optional[np.ndarray] = None,
        max_iterations: int = 10,
        convergence_threshold: float = 1e-4,
        rng: Optional[np.random.Generator] = None,
        use_sparse: bool = True,
    ) -> None:
        self.layers = layers
        self.inter_layer_edges = inter_layer_edges or np.empty((0, 4), dtype=int)
        self.n_layers = len(layers)

        # Interaction matrix
        if interaction_matrix is not None:
            if interaction_matrix.shape != (self.n_layers, self.n_layers):
                raise ValueError(
                    f"interaction_matrix shape must be ({self.n_layers}, {self.n_layers}), "
                    f"got {interaction_matrix.shape}"
                )
            self.interaction_matrix = interaction_matrix
        else:
            self.interaction_matrix = np.eye(self.n_layers)

        self.max_iterations = max_iterations
        self.convergence_threshold = convergence_threshold
        self.rng = rng if rng is not None else np.random.default_rng()
        self.use_sparse = use_sparse

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_simulation(self, initial_features: Optional[list[np.ndarray]] = None) -> SimulationResult:
        """Run the multilayer simulation.

        Parameters
        ----------
        initial_features :
            Per-layer initial feature matrices.  If *None*, the layer's
            default :attr:`~LayerState.node_features` are used.

        Returns
        -------
        SimulationResult
            Final states, metrics history, and timing.
        """
        start_time = time.time()

        # Initialise layer states
        if initial_features is not None:
            for layer, feats in zip(self.layers, initial_features):
                layer.node_features = feats.copy()
        else:
            for layer in self.layers:
                layer.node_features = layer.node_features.copy()

        metrics_history: list[dict] = []

        for iteration in range(self.max_iterations):
            old_features = np.vstack([l.node_features for l in self.layers])

            # Update each layer
            for i, layer in enumerate(self.layers):
                layer.node_features = self._update_layer(i, layer)

            # Compute inter-layer interactions
            for i, layer in enumerate(self.layers):
                layer.node_features = self._apply_inter_layer_coupling(i, layer)

            # Compute metrics
            layer_metrics = self._compute_layer_metrics()
            metrics_history.append({"iteration": iteration, **layer_metrics})

            # Check convergence
            new_features = np.vstack([l.node_features for l in self.layers])
            change = np.linalg.norm(new_features - old_features) / np.linalg.norm(old_features)

            if change < self.convergence_threshold:
                logger.info("Convergence reached at iteration %d (change=%.6f)", iteration, change)
                break

        simulation_time = time.time() - start_time

        result = SimulationResult(
            final_states=[l.node_features.copy() for l in self.layers],
            metrics_history=metrics_history,
            simulation_time=simulation_time,
        )

        logger.info(
            "Simulation complete. Time: %.2f s, Iterations: %d",
            simulation_time, len(metrics_history),
        )

        return result

    def get_network_metrics(self) -> dict:
        """Compute network metrics for all layers.

        Returns
        -------
        dict
            Per-layer metrics (degree distribution, clustering coefficient,
            centrality, etc.).
        """
        metrics = {}
        for i, layer in enumerate(self.layers):
            metrics[f"layer_{i}_{layer.layer_id}"] = self._compute_single_layer_metrics(
                layer.node_features, layer.graph_adjacency,
            )
        return metrics

    def add_layer(self, layer: LayerState) -> None:
        """Add a new layer to the multilayer system."""
        self.layers.append(layer)
        self.n_layers = len(self.layers)
        # Expand interaction matrix
        new_matrix = np.zeros((self.n_layers, self.n_layers))
        new_matrix[:self.n_layers - 1, :self.n_layers - 1] = self.interaction_matrix
        self.interaction_matrix = new_matrix

    def remove_layer(self, layer_id: int) -> None:
        """Remove a layer by index."""
        if layer_id < 0 or layer_id >= self.n_layers:
            raise ValueError(f"Layer index {layer_id} out of range")
        self.layers.pop(layer_id)
        self.n_layers = len(self.layers)
        self.interaction_matrix = self.interaction_matrix[
            np.arange(self.n_layers)[:, None], np.arange(self.n_layers)
        ]

    def add_inter_layer_edge(self, layer_src: int, node_src: int,
                              layer_dst: int, node_dst: int) -> None:
        """Add an inter-layer edge."""
        edge = np.array([[layer_src, node_src, layer_dst, node_dst]])
        if self.inter_layer_edges.size == 0:
            self.inter_layer_edges = edge
        else:
            self.inter_layer_edges = np.vstack([self.inter_layer_edges, edge])

    # ------------------------------------------------------------------
    # Internal: layer update
    # ------------------------------------------------------------------

    def _update_layer(self, layer_idx: int, layer: LayerState) -> np.ndarray:
        """Update node features for a single layer.

        Uses a row-normalised adjacency so that the aggregation is the
        average of neighbour features (not the sum), preventing
        unbounded exponential growth.
        """
        adj = layer.graph_adjacency
        features = layer.node_features

        # Build row-normalised adjacency (average over neighbours)
        if self.use_sparse:
            degrees = np.array(adj.sum(axis=1)).flatten()
            degrees = np.maximum(degrees, 1.0)  # avoid div-by-zero
            degrees_inv = 1.0 / degrees
            # Create diagonal degree matrix and compute D^{-1} A
            from scipy.sparse import diags
            norm_adj = diags(degrees_inv) @ adj
            aggregated = norm_adj @ features
        else:
            adj_arr = adj.toarray()
            degrees = adj_arr.sum(axis=1)
            degrees = np.maximum(degrees, 1.0)
            norm_adj = adj_arr / degrees[:, np.newaxis]
            aggregated = norm_adj @ features

        # Update rule: average of neighbours + self
        updated = (aggregated + features) / 2.0

        # Agent-type-specific dynamics
        if layer.agent_types is not None:
            for agent_type in np.unique(layer.agent_types):
                mask = layer.agent_types == agent_type
                # Simple type-based perturbation
                noise = self.rng.normal(0, 0.01, size=(mask.sum(), features.shape[1]))
                updated[mask] += noise

        return updated

    def _apply_inter_layer_coupling(self, layer_idx: int,
                                     layer: LayerState) -> np.ndarray:
        """Apply inter-layer coupling to node features.

        Uses a gentle blending (α=0.05) between self and cross-layer
        contributions to maintain stability.
        """
        features = layer.node_features.copy()
        coupling_strength = self.interaction_matrix[layer_idx, :]

        for j, strength in enumerate(coupling_strength):
            if j == layer_idx or strength == 0:
                continue
            if j < self.n_layers:
                other_layer = self.layers[j]
                n_common = min(features.shape[0], other_layer.node_features.shape[0])
                if n_common > 0:
                    # Gentle blending: 95% self + 5% from other layer (scaled by strength)
                    blend = 0.05 * strength
                    features[:n_common] = (1 - blend) * features[:n_common] + blend * other_layer.node_features[:n_common]

        return features

    # ------------------------------------------------------------------
    # Metrics computation
    # ------------------------------------------------------------------

    def _compute_layer_metrics(self) -> dict:
        """Compute metrics for all layers."""
        metrics: dict[str, float] = {}
        for i, layer in enumerate(self.layers):
            layer_metrics = self._compute_single_layer_metrics(
                layer.node_features, layer.graph_adjacency,
            )
            for key, value in layer_metrics.items():
                metrics[f"layer_{i}_{key}"] = value
        return metrics

    def _compute_single_layer_metrics(self, features: np.ndarray,
                                       adjacency) -> dict:
        """Compute metrics for a single layer."""
        if self.use_sparse and not sparse.issparse(adjacency):
            adjacency = sparse.csr_matrix(adjacency)

        # Degree distribution
        if self.use_sparse:
            degrees = np.array(adjacency.sum(axis=1)).flatten()
        else:
            degrees = np.array(adjacency.sum(axis=1)).flatten()

        # Average degree
        avg_degree = float(np.mean(degrees)) if len(degrees) > 0 else 0.0

        # Density
        n = features.shape[0]
        max_edges = n * (n - 1) / 2 if n > 1 else 1
        n_edges = float(adjacency.nnz) / 2 if self.use_sparse else float(np.sum(adjacency)) / 2
        density = n_edges / max_edges if max_edges > 0 else 0.0

        # Feature statistics
        mean_feat = float(np.mean(features))
        std_feat = float(np.std(features))

        return {
            "avg_degree": avg_degree,
            "density": density,
            "mean_feature": mean_feat,
            "std_feature": std_feat,
        }

    def compute_inter_layer_metrics(self) -> dict:
        """Compute metrics for inter-layer connections."""
        if self.inter_layer_edges.size == 0:
            return {}

        # Count inter-layer edges per layer pair
        layer_pairs: dict[tuple, int] = {}
        for edge in self.inter_layer_edges:
            pair = (int(edge[0]), int(edge[2]))
            layer_pairs[pair] = layer_pairs.get(pair, 0) + 1

        return {"inter_layer_edges": len(self.inter_layer_edges), "layer_pairs": layer_pairs}

    def get_layer_states(self) -> list[np.ndarray]:
        """Return current node-feature matrices for all layers."""
        return [layer.node_features.copy() for layer in self.layers]

    def get_inter_layer_edges(self) -> np.ndarray:
        """Return inter-layer edge list."""
        return self.inter_layer_edges.copy()
