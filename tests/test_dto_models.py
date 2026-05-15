"""Tests for backend DTO models (Pydantic v2).

Verifies that:
- All models import cleanly from ``backend.app.models``.
- ``extra="forbid"`` rejects unknown fields.
- Enum values are correct.
- Optional fields accept ``None``.
- Required field validators enforce constraints (e.g. opinion range).
- The TypeScript generation script exits without errors.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.app.models import (
    ArchitectEventMessage,
    Feasibility,
    ForecastPoint,
    ForecastResponse,
    InterventionLogEntry,
    InterventionRecord,
    SimAgentLite,
    SimAggregateMetrics,
    SimEventKind,
    SimEventMessage,
    SimMode,
    SimSnapshotMessage,
    SimulationSnapshotPayload,
    SnapshotRecord,
    TimelineTick,
    TimelineResponse,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)

_METRICS = dict(
    mean_opinion=0.1,
    std_opinion=0.4,
    polarization=0.6,
    dominant_rule="hk",
    consensus_rate=0.3,
    fragmentation_index=0.2,
    active_agents=500,
)


def _agent(**kw) -> dict:
    base = dict(id="a1", layer="social", x=0.1, y=0.2, opinion=0.5)
    base.update(kw)
    return base


# ---------------------------------------------------------------------------
# SimAgentLite
# ---------------------------------------------------------------------------


class TestSimAgentLite:
    def test_minimal_valid(self):
        a = SimAgentLite(**_agent())
        assert a.id == "a1"
        assert a.z == 0.0
        assert a.metadata is None

    def test_with_metadata(self):
        a = SimAgentLite(**_agent(metadata={"cluster": 3}))
        assert a.metadata == {"cluster": 3}

    def test_opinion_upper_bound(self):
        with pytest.raises(ValidationError):
            SimAgentLite(**_agent(opinion=1.5))

    def test_opinion_lower_bound(self):
        with pytest.raises(ValidationError):
            SimAgentLite(**_agent(opinion=-2.0))

    def test_extra_field_forbidden(self):
        with pytest.raises(ValidationError):
            SimAgentLite(**_agent(unknown_field="oops"))


# ---------------------------------------------------------------------------
# SimAggregateMetrics
# ---------------------------------------------------------------------------


class TestSimAggregateMetrics:
    def test_valid(self):
        m = SimAggregateMetrics(**_METRICS)
        assert m.dominant_rule == "hk"
        assert m.schema_version is None

    def test_extra_forbidden(self):
        with pytest.raises(ValidationError):
            SimAggregateMetrics(**_METRICS, surprise=True)


# ---------------------------------------------------------------------------
# SimulationSnapshotPayload
# ---------------------------------------------------------------------------


class TestSimulationSnapshotPayload:
    def test_minimal(self):
        p = SimulationSnapshotPayload(tick=10, metrics=SimAggregateMetrics(**_METRICS))
        assert p.mode == SimMode.live
        assert p.agents is None

    def test_with_agents(self):
        agents = [SimAgentLite(**_agent(id=str(i))) for i in range(3)]
        p = SimulationSnapshotPayload(
            tick=5, metrics=SimAggregateMetrics(**_METRICS), agents=agents
        )
        assert len(p.agents) == 3

    def test_replay_mode(self):
        p = SimulationSnapshotPayload(
            tick=0, metrics=SimAggregateMetrics(**_METRICS), mode=SimMode.replay
        )
        assert p.mode == SimMode.replay


# ---------------------------------------------------------------------------
# SimSnapshotMessage
# ---------------------------------------------------------------------------


class TestSimSnapshotMessage:
    def _payload(self):
        return SimulationSnapshotPayload(tick=1, metrics=SimAggregateMetrics(**_METRICS))

    def test_valid(self):
        msg = SimSnapshotMessage(sim_id="run-1", timestamp=_NOW, payload=self._payload())
        assert msg.type == "snapshot"

    def test_extra_forbidden(self):
        with pytest.raises(ValidationError):
            SimSnapshotMessage(
                sim_id="x",
                timestamp=_NOW,
                payload=self._payload(),
                extra_junk=True,
            )


# ---------------------------------------------------------------------------
# SimEventMessage
# ---------------------------------------------------------------------------


class TestSimEventMessage:
    def test_started(self):
        msg = SimEventMessage(sim_id="run-1", event=SimEventKind.started)
        assert msg.type == "event"
        assert msg.detail is None

    def test_error_with_detail(self):
        msg = SimEventMessage(
            sim_id="run-1", event=SimEventKind.error, detail="OOM at tick 99"
        )
        assert msg.detail == "OOM at tick 99"

    def test_invalid_event(self):
        with pytest.raises(ValidationError):
            SimEventMessage(sim_id="x", event="exploded")


# ---------------------------------------------------------------------------
# dto_snapshot
# ---------------------------------------------------------------------------


class TestSnapshotRecord:
    def test_valid(self):
        r = SnapshotRecord(
            snapshot_id="s1",
            sim_id="run-1",
            tick=5,
            timestamp=_NOW,
            data={"mean": 0.3},
        )
        assert r.tick == 5

    def test_extra_forbidden(self):
        with pytest.raises(ValidationError):
            SnapshotRecord(
                snapshot_id="s1",
                sim_id="r",
                tick=0,
                timestamp=_NOW,
                data={},
                oops=1,
            )


class TestTimelineResponse:
    def test_empty_ticks(self):
        r = TimelineResponse(sim_id="run-1", ticks=[], total=0)
        assert r.total == 0

    def test_with_ticks(self):
        tick = TimelineTick(tick=3, mean_opinion=0.2, polarization=0.5, dominant_rule="hk")
        r = TimelineResponse(sim_id="run-1", ticks=[tick], total=100)
        assert r.ticks[0].tick == 3


# ---------------------------------------------------------------------------
# dto_forecast
# ---------------------------------------------------------------------------


class TestForecastResponse:
    def test_valid(self):
        pt = ForecastPoint(
            tick=10,
            mean_opinion=0.3,
            polarization=0.4,
            confidence_lower=0.1,
            confidence_upper=0.5,
        )
        feasibility = Feasibility(score=0.8, label="high", rationale="stable trend")
        r = ForecastResponse(sim_id="run-1", horizon_ticks=20, points=[pt], feasibility=feasibility)
        assert r.horizon_ticks == 20

    def test_feasibility_score_bounds(self):
        with pytest.raises(ValidationError):
            Feasibility(score=1.5, label="impossible")


# ---------------------------------------------------------------------------
# dto_architect
# ---------------------------------------------------------------------------


class TestInterventionRecord:
    def test_valid(self):
        rec = InterventionRecord(
            intervention_id="i1",
            sim_id="run-1",
            time_start=0,
            time_end=10,
            model_name="hk",
            parameters={"epsilon": 0.3},
        )
        assert rec.target_nodes is None

    def test_with_target_nodes(self):
        rec = InterventionRecord(
            intervention_id="i2",
            sim_id="run-1",
            time_start=5,
            time_end=15,
            model_name="umbral",
            parameters={"umbral": 0.5},
            target_nodes=["node-1", "node-2"],
        )
        assert len(rec.target_nodes) == 2


class TestArchitectEventMessage:
    def _record(self):
        return InterventionRecord(
            intervention_id="i1",
            sim_id="run-1",
            time_start=0,
            time_end=10,
            model_name="hk",
            parameters={},
        )

    def test_valid(self):
        msg = ArchitectEventMessage(
            sim_id="run-1", intervention=self._record(), timestamp=_NOW
        )
        assert msg.type == "architect_event"

    def test_extra_forbidden(self):
        with pytest.raises(ValidationError):
            ArchitectEventMessage(
                sim_id="x",
                intervention=self._record(),
                timestamp=_NOW,
                extra=True,
            )


# ---------------------------------------------------------------------------
# gen_ts_types script
# ---------------------------------------------------------------------------


class TestGenTsTypes:
    def test_script_runs_without_error(self, tmp_path):
        """Script must exit 0 and regenerate api.generated.ts cleanly."""
        result = subprocess.run(
            [sys.executable, "scripts/gen_ts_types.py"],
            cwd=str(Path(__file__).resolve().parent.parent),
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr

    def test_generated_file_exists(self):
        root = Path(__file__).resolve().parent.parent
        out = root / "frontend" / "src" / "types" / "api.generated.ts"
        assert out.exists(), "api.generated.ts was not generated"

    def test_generated_file_contains_all_interfaces(self):
        root = Path(__file__).resolve().parent.parent
        content = (root / "frontend" / "src" / "types" / "api.generated.ts").read_text()
        expected = [
            "SimAgentLite",
            "SimAggregateMetrics",
            "SimulationSnapshotPayload",
            "SimSnapshotMessage",
            "SimEventMessage",
            "SnapshotRecord",
            "TimelineTick",
            "TimelineResponse",
            "ForecastPoint",
            "Feasibility",
            "ForecastResponse",
            "InterventionRecord",
            "InterventionLogEntry",
            "ArchitectEventMessage",
            "SimMode",
            "SimEventKind",
        ]
        for name in expected:
            assert name in content, f"Missing: {name}"
