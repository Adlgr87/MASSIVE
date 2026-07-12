"""Lightweight meta-regime selector for MASSIVE rules."""

from __future__ import annotations

import numpy as np

Array = np.ndarray


class MetaRegimeSelector:
    """Selects rule probabilities from state features and reward history.

    This is a deterministic NumPy baseline that can later be replaced by a
    neural selector without changing the surrounding contract.

    Args:
        n_rules: Number of available MASSIVE rules.
        learning_rate: Exponential moving-average rate for reward updates.
    """

    def __init__(self, n_rules: int = 13, learning_rate: float = 0.1) -> None:
        if n_rules < 1:
            raise ValueError("n_rules must be positive")
        if not 0.0 < learning_rate <= 1.0:
            raise ValueError("learning_rate must be in (0, 1]")
        self.n_rules = n_rules
        self.learning_rate = learning_rate
        self.rule_performance = np.zeros(n_rules, dtype=float)

    def predict_proba(self, state_history: Array, current_state: Array, metadata: dict[str, object] | None = None) -> Array:
        """Return probabilities over rules.

        Args:
            state_history: Recent state trajectory.
            current_state: Current state vector or matrix.
            metadata: Optional context. Numeric values contribute weak context.

        Returns:
            Probability vector with length ``n_rules``.
        """

        features = self._extract_features(state_history, current_state, metadata or {})
        logits = self.rule_performance.copy()
        logits += np.linspace(-0.05, 0.05, self.n_rules) * features[0]
        logits += features[1] * np.cos(np.arange(self.n_rules)) * 0.05
        return self._softmax(logits)

    def update_performance(self, rule_id: int, reward: float) -> None:
        """Update one rule's reward baseline.

        Args:
            rule_id: Rule index to update.
            reward: Observed scalar reward.
        """

        if not 0 <= rule_id < self.n_rules:
            raise ValueError("rule_id out of range")
        alpha = self.learning_rate
        self.rule_performance[rule_id] = alpha * reward + (1.0 - alpha) * self.rule_performance[rule_id]

    def _extract_features(self, state_history: Array, current_state: Array, metadata: dict[str, object]) -> Array:
        state = np.asarray(current_state, dtype=float)
        history = np.asarray(state_history, dtype=float)
        volatility = float(np.std(history)) if history.size else 0.0
        polarization = float(np.std(state)) if state.size else 0.0
        numeric_context = [float(v) for v in metadata.values() if isinstance(v, (int, float))]
        context = float(np.mean(numeric_context)) if numeric_context else 0.0
        return np.array([volatility, polarization, context], dtype=float)

    def _softmax(self, logits: Array) -> Array:
        shifted = logits - np.max(logits)
        exp = np.exp(shifted)
        return exp / np.sum(exp)
