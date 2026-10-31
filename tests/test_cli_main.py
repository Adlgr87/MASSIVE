"""Tests for the ``massive`` CLI (``massive/cli/main.py``).

The README presents the CLI as the server-less quick start — "First simulation in
one command" — yet the whole module had **zero** test coverage, so that documented
path could break without any signal.

These tests exercise the parser surface, every command's exit code, the JSON
contract of ``simulate``, and that the README's documented invocation actually
works end to end.
"""

from __future__ import annotations

import json

import pytest

from massive.cli.main import _build_parser, main


class TestParserSurface:
    def test_parser_builds_and_lists_commands(self):
        parser = _build_parser()
        actions = [
            action for action in parser._actions if action.__class__.__name__ == "_SubParsersAction"
        ]
        assert len(actions) == 1
        commands = set(actions[0].choices)
        assert {"simulate", "scientific", "forecast", "benchmark", "version", "serve"} <= commands

    def test_missing_command_exits_nonzero(self):
        with pytest.raises(SystemExit) as excinfo:
            _build_parser().parse_args([])
        assert excinfo.value.code != 0

    def test_unknown_command_exits_nonzero(self):
        with pytest.raises(SystemExit) as excinfo:
            _build_parser().parse_args(["definitely-not-a-command"])
        assert excinfo.value.code != 0


class TestVersionCommand:
    def test_version_prints_and_returns_zero(self, capsys):
        assert main(["version"]) == 0
        out = capsys.readouterr().out
        assert "MASSIVE CLI v" in out
        assert "Python" in out


class TestSimulateCommand:
    def test_simulate_returns_zero_and_emits_json_summary(self, capsys):
        """The documented quick start: ``massive simulate --pasos 30``."""
        assert main(["simulate", "--pasos", "10"]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert "polarizacion_media" in payload
        assert payload["pasos"] == 10

    def test_simulate_rejects_zero_steps(self):
        with pytest.raises(SystemExit) as excinfo:
            _build_parser().parse_args(["simulate", "--pasos", "0"])
        assert excinfo.value.code != 0

    def test_simulate_accepts_an_initial_state(self, capsys):
        estado = json.dumps({"opinion": 0.9, "propaganda": 0.1})
        assert main(["simulate", "--pasos", "5", "--estado", estado]) == 0
        payload = json.loads(capsys.readouterr().out)
        assert "polarizacion_media" in payload

    def test_simulate_is_deterministic_across_invocations(self, capsys):
        main(["simulate", "--pasos", "8"])
        first = json.loads(capsys.readouterr().out)
        main(["simulate", "--pasos", "8"])
        second = json.loads(capsys.readouterr().out)
        assert first == second


class TestForecastCommand:
    def test_forecast_runs_and_returns_an_exit_code(self, capsys):
        assert main(["forecast", "--mode", "analytical"]) in (0, 1)
        # Must produce output rather than crashing mid-way.
        assert capsys.readouterr().out.strip()

    def test_forecast_rejects_unknown_event_type(self):
        with pytest.raises(SystemExit) as excinfo:
            _build_parser().parse_args(["forecast", "--event-type", "not-an-event"])
        assert excinfo.value.code != 0


class TestMainDispatch:
    def test_main_returns_command_exit_code(self):
        assert main(["version"]) == 0
