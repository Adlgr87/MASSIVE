"""Central settings for the UI-NG backend (environment-driven, dev defaults).

Production deployments configure these via environment variables (see
``docs/NEXT_GEN_UI_PRODUCTION_ES.md``). Every value has a safe default so
local development works with zero configuration.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes", "on")


@dataclass
class UISettings:
    """Runtime settings for the UI-NG FastAPI application."""

    # ── Service ──────────────────────────────────────────────────────────
    env: str = field(default_factory=lambda: os.getenv("MASSIVE_ENV", "development"))
    serve_frontend: bool = field(default_factory=lambda: _env_bool("MASSIVE_SERVE_FRONTEND", True))
    frontend_dist: Path = field(default_factory=lambda: _REPO_ROOT / "frontend" / "dist")

    # ── Data ─────────────────────────────────────────────────────────────
    data_dir: Optional[Path] = field(
        default_factory=lambda: (
            Path(os.getenv("MASSIVE_DATA_DIR")) if os.getenv("MASSIVE_DATA_DIR") else _REPO_ROOT / "data" / "ui_ng"
        )
    )
    run_store_capacity: int = field(default_factory=lambda: _env_int("MASSIVE_RUN_STORE_CAPACITY", 500))

    # ── Security ─────────────────────────────────────────────────────────
    api_keys: list[str] = field(
        default_factory=lambda: [
            k.strip()
            for k in os.getenv("MASSIVE_API_KEYS", os.getenv("MASSIVE_API_KEY", "")).split(",")
            if k.strip()
        ]
    )
    cors_origins: list[str] = field(
        default_factory=lambda: [
            o.strip()
            for o in os.getenv(
                "MASSIVE_CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
            ).split(",")
            if o.strip()
        ]
    )
    allowed_hosts: list[str] = field(
        default_factory=lambda: [
            h.strip() for h in os.getenv("MASSIVE_ALLOWED_HOSTS", "*").split(",") if h.strip()
        ]
    )
    trust_proxy_headers: bool = field(default_factory=lambda: _env_bool("MASSIVE_TRUST_PROXY", False))

    # ── Rate limiting (per client IP; see docs for multi-worker notes) ───
    rate_limit_enabled: bool = field(default_factory=lambda: _env_bool("MASSIVE_RATE_LIMIT_ENABLED", True))
    rate_limit_per_minute: int = field(default_factory=lambda: _env_int("MASSIVE_RATE_LIMIT_PER_MIN", 120))
    rate_limit_simulate_per_minute: int = field(
        default_factory=lambda: _env_int("MASSIVE_RATE_LIMIT_SIMULATE_PER_MIN", 12)
    )

    # ── LLM ──────────────────────────────────────────────────────────────
    llm_timeout: float = field(default_factory=lambda: _env_float("MASSIVE_LLM_TIMEOUT", 45.0))
    llm_max_tokens: int = field(default_factory=lambda: _env_int("MASSIVE_LLM_MAX_TOKENS", 1400))

    @property
    def is_production(self) -> bool:
        return self.env.lower() in ("production", "prod")

    @property
    def db_path(self) -> Path | None:
        if self.data_dir is None:
            return None
        self.data_dir.mkdir(parents=True, exist_ok=True)
        return self.data_dir / "runs.db"
