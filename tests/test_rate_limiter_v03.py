"""Tests for file-based rate limiter (multi-worker support)."""

from __future__ import annotations

import time
from pathlib import Path

import pytest

from massive_core.config.rate_limit import FileRateLimiter, InMemoryRateLimiter, build_rate_limiter


class TestInMemoryRateLimiter:
    def test_allows_within_limit(self) -> None:
        limiter = InMemoryRateLimiter()
        for _ in range(5):
            assert limiter.allow("user", 5) is True

    def test_blocks_over_limit(self) -> None:
        limiter = InMemoryRateLimiter()
        for _ in range(5):
            limiter.allow("user", 5)
        assert limiter.allow("user", 5) is False


class TestFileRateLimiter:
    def test_shared_state_across_instances(self, tmp_path: Path) -> None:
        """Two FileRateLimiter instances sharing the same file see each other's state."""
        path = tmp_path / "rl.json"
        a = FileRateLimiter(path)
        b = FileRateLimiter(path)

        assert a.allow("user", 3) is True
        assert b.allow("user", 3) is True
        assert b.allow("user", 3) is True
        assert a.allow("user", 3) is False  # 4th request should be denied

    def test_independent_keys(self, tmp_path: Path) -> None:
        path = tmp_path / "rl.json"
        limiter = FileRateLimiter(path)

        limiter.allow("user_a", 2)
        limiter.allow("user_a", 2)
        limiter.allow("user_b", 2)
        limiter.allow("user_b", 2)

        assert limiter.allow("user_a", 2) is False
        assert limiter.allow("user_b", 2) is False
        assert limiter.allow("user_c", 2) is True


class TestBuildRateLimiter:
    def test_memory_backend_default(self) -> None:
        limiter = build_rate_limiter()
        assert isinstance(limiter, InMemoryRateLimiter)

    def test_file_backend_via_env(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        path = tmp_path / "rl.json"
        monkeypatch.setenv("MASSIVE_RATE_LIMIT_BACKEND", "file")
        monkeypatch.setenv("MASSIVE_RATE_LIMIT_PATH", str(path))
        limiter = build_rate_limiter()
        assert isinstance(limiter, FileRateLimiter)
        assert limiter.path == path
