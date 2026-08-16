"""Minimal Prometheus text-format metrics registry (no external dependency).

Counters are exposed at ``GET /metrics`` and consumed by Prometheus /
Grafana. This is intentionally tiny: a lock-protected counter registry with
a text exporter. For production scale, swap the registry internals for
``prometheus_client`` without touching the call sites.
"""

from __future__ import annotations

import threading
from collections import defaultdict
from typing import Any

_METRIC_HELP = {
    "http_requests_total": "HTTP requests served (counter)",
    "simulations_total": "Simulation runs by engine (counter)",
    "ws_connections_total": "Live WebSocket connections opened (counter)",
    "ws_snapshots_total": "Live snapshots emitted (counter)",
    "ws_shocks_total": "Interactive shocks applied (counter)",
    "ws_stops_total": "Client-requested live stops (counter)",
    "rate_limit_hits_total": "Requests rejected by the rate limiter (counter)",
    "llm_requests_total": "LLM provider requests by outcome (counter)",
}


class MetricsRegistry:
    """Thread-safe counters with Prometheus text exposition."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, dict[tuple[tuple[str, str], ...], float]] = defaultdict(
            lambda: defaultdict(float)
        )

    def inc(self, name: str, labels: dict[str, str] | None = None, amount: float = 1.0) -> None:
        key = tuple(sorted((labels or {}).items()))
        with self._lock:
            self._counters[name][key] += amount

    def render(self) -> str:
        with self._lock:
            names = sorted(self._counters.keys())
            out: list[str] = []
            for name in names:
                out.append(f"# HELP {name} {_METRIC_HELP.get(name, name)}")
                out.append(f"# TYPE {name} counter")
                series = self._counters[name]
                if not series:
                    out.append(f"{name} 0")
                    continue
                for key_tuple in sorted(series.keys()):
                    value = series[key_tuple]
                    if key_tuple:
                        label_str = ",".join(
                            f'{k}="{v}"' for k, v in dict(key_tuple).items()
                        )
                        out.append(f"{name}{{{label_str}}} {value:g}")
                    else:
                        out.append(f"{name} {value:g}")
            return "\n".join(out) + "\n"


registry = MetricsRegistry()
