"""@deprecated — re-export only. Use massive.core.state_compression directly."""

from massive.core.state_compression import (  # noqa: F401
    compress_agent_states,
    decompress_agent_states,
)

__all__ = ["compress_agent_states", "decompress_agent_states"]
