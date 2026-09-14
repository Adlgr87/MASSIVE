"""Minimal Prometheus text-format metrics for the canonical backend.

Deliberately dependency-free (no prometheus_client): a tiny thread-safe
registry that renders counters and histograms in the Prometheus exposition
format. This keeps the operational surface observable without adding runtime deps.

Usage:
    from backend.app.metrics import registry
    registry.inc("http_requests_total", {"method": "GET", "status": "200"})
    registry.observe("http_request_duration_seconds", 0.042, {"method": "GET", "group": "simulate"})
    text = registry.render()

SLOs (defined in PRODUCTION_ARCHITECTURE_SPEC.md §5.3):
    - Error budget: < 5% error rate (500/502 responses)
    - P95 latency:  < 2s  (simulations < 100 steps)
                     < 30s (LLM calls)
    - Availability:  99.9% (max ~8.77 min/month downtime)
"""

from __future__ import annotations

import math
import threading
import time
from collections import defaultdict

_START = time.time()

# Prometheus histogram bucket boundaries (seconds)
_DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0)


def _escape_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n")


class Histogram:
    """Thread-safe histogram with configurable bucket boundaries."""

    def __init__(self, name: str, buckets: tuple[float, ...] | None = None) -> None:
        self.name = name
        self.buckets = tuple(sorted(buckets or _DEFAULT_BUCKETS))
        self._lock = threading.Lock()
        # count per (bucket, labels)
        self._counts: dict[str, dict[tuple[tuple[str, str], ...], int]] = defaultdict(
            lambda: defaultdict(int)
        )
        self._sum: dict[tuple[tuple[str, str], ...], float] = defaultdict(float)
        self._total_count: dict[tuple[tuple[str, str], ...], int] = defaultdict(int)

    def observe(self, value: float, labels: dict[str, str] | None = None) -> None:
        key = tuple(sorted((k, str(v)) for k, v in (labels or {}).items()))
        with self._lock:
            self._sum[key] += value
            self._total_count[key] += 1
            for i, bound in enumerate(self.buckets):
                if value <= bound:
                    bucket_key = f"{self.name}_bucket{{{','.join(f'{k}=\"{_escape_label(v)}\"' for k, v in key) if key else ''},le=\"{bound}\"}}"
                    self._counts[bucket_key][()] += 1

    def render(self, lines: list[str]) -> None:
        with self._lock:
            total_count = dict(self._total_count)
            sum_vals = dict(self._sum)

        inf_count = sum(total_count.values())

        # Render each bucket
        for bound in self.buckets:
            bucket_name = f"{self.name}_bucket"
            for key, count in total_count.items():
                # Count observations <= this bound
                cum_count = 0
                for b_idx, b_bound in enumerate(self.buckets):
                    if b_bound <= bound:
                        # Find this bucket's count
                        bk = f"{self.name}_bucket{{{','.join(f'{k}=\"{_escape_label(v)}\"' for k, v in key) if key else ''},le=\"{b_bound}\"}}"
                        cum_count += self._counts.get(bk, {}).get((), 0)
                if key:
                    label_str = ",".join(f'{k}="{_escape_label(v)}"' for k, v in key)
                    lines.append(f"{bucket_name}{{{label_str},le=\"{bound}\"}} {cum_count}")
                else:
                    lines.append(f"{bucket_name}{{le=\"{bound}\"}} {cum_count}")

        # +Inf bucket
        for key in total_count:
            if key:
                label_str = ",".join(f'{k}="{_escape_label(v)}"' for k, v in key)
                lines.append(f"{bucket_name}{{{label_str},le=\"+Inf\"}} {total_count[key]}")
            else:
                lines.append(f"{bucket_name}{{le=\"+Inf\"}} {total_count.get((), 0)}")

        # Sum and Count
        for key in total_count:
            if key:
                label_str = ",".join(f'{k}="{_escape_label(v)}"' for k, v in key)
                lines.append(f"{self.name}_sum{{{label_str}}} {sum_vals[key]:g}")
                lines.append(f"{self.name}_count{{{label_str}}} {total_count[key]}")
            else:
                lines.append(f"{self.name}_sum {sum_vals.get(key, 0):g}")
                lines.append(f"{self.name}_count {total_count.get(key, 0)}")


class MetricsRegistry:
    """Thread-safe registry with counters and histograms for Prometheus text rendering."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, dict[tuple[tuple[str, str], ...], float]] = defaultdict(
            lambda: defaultdict(float)
        )
        self._histograms: dict[str, Histogram] = {}

    def inc(self, name: str, labels: dict[str, str] | None = None, amount: float = 1.0) -> None:
        """Increment a counter (creating it on first use)."""
        key = tuple(sorted((k, str(v)) for k, v in (labels or {}).items()))
        with self._lock:
            self._counters[name][key] += amount

    def observe(self, name: str, value: float, labels: dict[str, str] | None = None) -> None:
        """Record a histogram observation."""
        if name not in self._histograms:
            self._histograms[name] = Histogram(name)
        self._histograms[name].observe(value, labels)

    def render(self) -> str:
        """Render all counters + histograms + process uptime in Prometheus text format."""
        lines: list[str] = []
        with self._lock:
            snapshot = {name: dict(series) for name, series in self._counters.items()}

        # Render counters
        for name in sorted(snapshot):
            lines.append(f"# HELP {name} Monotonic counter.")
            lines.append(f"# TYPE {name} counter")
            for labels, value in sorted(snapshot[name].items()):
                if labels:
                    label_str = ",".join(f'{k}="{_escape_label(v)}"' for k, v in labels)
                    lines.append(f"{name}{{{label_str}}} {value:g}")
                else:
                    lines.append(f"{name} {value:g}")

        # Render histograms
        with self._lock:
            for hist in sorted(self._histograms.values(), key=lambda h: h.name):
                lines.append(f"# HELP {hist.name} Request duration histogram.")
                lines.append(f"# TYPE {hist.name} histogram")
                hist.render(lines)

        # Uptime gauge
        uptime = time.time() - _START
        lines.append("# HELP massive_uptime_seconds Process uptime in seconds.")
        lines.append("# TYPE massive_uptime_seconds gauge")
        lines.append(f"massive_uptime_seconds {uptime:.2f}")

        # SLO target annotations
        lines.append("# HELP massive_slo_error_budget Maximum allowable 5xx error rate (0.05 = 5%).")
        lines.append("# TYPE massive_slo_error_budget gauge")
        lines.append("massive_slo_error_budget 0.05")
        lines.append("# HELP massive_slo_p95_latency_max Maximum P95 latency in seconds (<100 steps).")
        lines.append("# TYPE massive_slo_p95_latency_max gauge")
        lines.append("massive_slo_p95_latency_max 2.0")
        lines.append("# HELP massive_slo_p95_latency_llm Maximum P95 latency in seconds (LLM).")
        lines.append("# TYPE massive_slo_p95_latency_llm gauge")
        lines.append("massive_slo_p95_latency_llm 30.0")
        lines.append("# HELP massive_slo_availability_target Availability target (0.999 = 99.9%).")
        lines.append("# TYPE massive_slo_availability_target gauge")
        lines.append("massive_slo_availability_target 0.999")

        return "\n".join(lines) + "\n"


registry = MetricsRegistry()
