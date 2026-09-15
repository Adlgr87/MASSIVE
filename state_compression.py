"""Backward-compatibility re-export for legacy imports.

.. deprecated:: Use ``massive.core.state_compression`` instead.
"""
from massive.core.state_compression import (  # noqa: F401
    compress_agent_states,
    decompress_agent_states,
)
