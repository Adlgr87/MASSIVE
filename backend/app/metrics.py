"""Minimal Prometheus text-format metrics for the canonical backend.

Deliberately dependency-free (no prometheus_client): a tiny thread-safe
registry that renders counters in the Prometheus exposition format. This
keeps the operational surface observable without adding runtime deps.

Usage:
    from backend.app.metrics import registry
    registry.inc("http_requests_total", {"method": "GET", "status": "200"})
    text = registry.render()
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict

_START = time.time()


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class MetricsRegistry:
    """Thread-safe counter registry with Prometheus text rendering."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, dict[tuple[tuple[str, str], ...], float]] = defaultdict(
            lambda: defaultdict(float)
        )

    def inc(self, name: str, labels: dict[str, str] | None = None, amount: float = 1.0) -> None:
        """Increment a counter (creating it on first use)."""
        key = tuple(sorted((k, str(v)) for k, v in (labels or {}).items()))
        with self._lock:
            self._counters[name][key] += amount

    def render(self) -> str:
        """Render all counters + process uptime in Prometheus text format."""
        lines: list[str] = []
        with self._lock:
            snapshot = {name: dict(series) for name, series in self._counters.items()}
        for name in sorted(snapshot):
            lines.append(f"# HELP {name} Monotonic counter.")
            lines.append(f"# TYPE {name} counter")
            for labels, value in sorted(snapshot[name].items()):
                if labels:
                    label_str = ",".join(f'{k}="{_escape_label(v)}"' for k, v in labels)
                    lines.append(f"{name}{{{label_str}}} {value:g}")
                else:
                    lines.append(f"{name} {value:g}")
        uptime = time.time() - _START
        lines.append("# HELP massive_uptime_seconds Process uptime in seconds.")
        lines.append("# TYPE massive_uptime_seconds gauge")
        lines.append(f"massive_uptime_seconds {uptime:.2f}")
        return "\n".join(lines) + "\n"


registry = MetricsRegistry()
