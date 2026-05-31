"""Backward-compatible re-export — implementation lives in massive.core.state_compression."""

from massive.core.state_compression import (  # noqa: F401
    compress_agent_states,
    decompress_agent_states,
)

__all__ = ["compress_agent_states", "decompress_agent_states"]
