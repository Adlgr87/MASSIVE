"""CLI main entry-point for MASSIVE.

Provides subcommands:
    simulate      Run a scalar simulation via the service layer.
    scientific    Run a scientific/multilayer simulation with diagnostics.
    forecast      Run temporal risk forecasting (analytical or Monte Carlo).
    benchmark     Run the PVU-BS benchmark suite.
    version       Print version and exit.
    serve         Start the FastAPI server (uvicorn).
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from collections.abc import Sequence

from massive import __version__ as __VERSION__

log = logging.getLogger(__name__)

log = logging.getLogger(__name__)


def _configure_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(name)-28s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )


def _cmd_simulate(args: argparse.Namespace) -> int:
    """Run ``services.simulation_service.run_scalar_simulation``."""
    from services.simulation_service import run_scalar_simulation

    result = run_scalar_simulation(
        estado_inicial=json.loads(args.estado) if args.estado else None,
        escenario=args.escenario,
        pasos=args.pasos,
        verbose=args.verbose if args.verbose else False,
    )
    print(json.dumps(result["summary"], indent=2, default=str))
    log.info("simulation complete: %d steps", result.get("n_steps", args.pasos))
    return 0


def _cmd_benchmark(args: argparse.Namespace) -> int:
    """Run ``benchmarks.runner`` as a subprocess-equivalent call."""
    from benchmarks import runner as bench_runner

    argv = ["--cases", args.cases, "--out", args.out, "--seed", str(args.seed)]
    if getattr(args, "llm", False):
        argv.append("--llm")
    elif getattr(args, "real", False):
        argv.append("--real")
    else:
        argv.append("--offline")
    return bench_runner.main(argv)


def _cmd_scientific(args: argparse.Namespace) -> int:
    """Run ``massive_core scientific_runner`` with report + EnKF."""
    from massive_core.scientific_runner import run_scientific_simulation

    result = run_scientific_simulation(
        estado_inicial=json.loads(args.estado) if args.estado else None,
        escenario=args.escenario,
        pasos=args.pasos,
        scientific_config={
            "enable_scientific_report": args.report,
            "enable_enkf": args.enkf,
        },
    )
    print(json.dumps(result.summary, indent=2, default=str))
    if args.report and getattr(result, "scientific_report", None):
        print(f"\nScientific report at: {result.scientific_report}")
    return 0


def _cmd_forecast(args: argparse.Namespace) -> int:
    """Run the temporal forecast engine on a simulation snapshot."""
    from forecast.engine import forecast
    from forecast.temporal_config import TemporalConfig

    sim_state = json.loads(args.state) if args.state else {"opinion": 0.0}
    tc = TemporalConfig(event_type=args.event_type)
    result = forecast(
        sim_state,
        temporal_config=tc,
        mode=args.mode,
        n_runs=args.n_runs,
    )
    print(json.dumps(result.model_dump(), indent=2, default=str))
    return 0


def _cmd_version(_args: argparse.Namespace) -> int:
    """Print version information."""
    print(f"MASSIVE CLI v{__VERSION__}")
    print(f"Python {sys.version.split()[0]}")
    return 0


def _cmd_serve(args: argparse.Namespace) -> int:
    """Start the uvicorn server.

    Prefer ``backend.app.main:app``; fall back to legacy ``api:app``.
    """
    import uvicorn

    app_target = "backend.app.main:app" if not args.legacy else "api:app"
    config = uvicorn.Config(
        app_target,
        host=args.host,
        port=args.port,
        log_level="info",
        workers=args.workers,
    )
    server = uvicorn.Server(config)
    log.info("Starting MASSIVE API server on %s:%d (%s)", args.host, args.port, app_target)
    return server.run()  # type: ignore[func-returns-value]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="massive",
        description="MASSIVE — Mathematical Architecture for Scalable Social Interaction & Virtual Engine",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    sub = parser.add_subparsers(dest="command", required=True)

    # simulate
    p_sim = sub.add_parser("simulate", help="Run a scalar MASSIVE simulation")
    p_sim.add_argument("--estado", type=str, default=None, help="JSON initial state dict")
    p_sim.add_argument("--escenario", type=str, default="campana", help="Scenario key")
    p_sim.add_argument("--pasos", type=int, default=50, help="Number of simulation steps")
    p_sim.set_defaults(func=_cmd_simulate)

    # scientific
    p_sci = sub.add_parser(
        "scientific", help="Run a scientific/multilayer simulation with diagnostics"
    )
    p_sci.add_argument("--estado", type=str, default=None, help="JSON initial state dict")
    p_sci.add_argument("--escenario", type=str, default="campana", help="Scenario key")
    p_sci.add_argument("--pasos", type=int, default=100, help="Number of simulation steps")
    p_sci.add_argument("--report", action="store_true", help="Generate scientific report")
    p_sci.add_argument(
        "--enkf", action="store_true", help="Enable Ensemble Kalman Filter data assimilation"
    )
    p_sci.set_defaults(func=_cmd_scientific)

    # forecast
    p_fc = sub.add_parser("forecast", help="Run temporal risk forecasting")
    p_fc.add_argument("--state", type=str, default=None, help="JSON simulation state snapshot")
    p_fc.add_argument(
        "--event-type",
        type=str,
        default="policy_adoption",
        choices=[
            "viral_online",
            "protest_campaign",
            "labor_conflict",
            "electoral_campaign",
            "policy_adoption",
            "cultural_shift",
        ],
        help="Event type for step-duration mapping",
    )
    p_fc.add_argument(
        "--mode",
        type=str,
        default="analytical",
        choices=["analytical", "monte_carlo"],
        help="Forecast mode",
    )
    p_fc.add_argument("--n-runs", type=int, default=200, help="Monte Carlo iterations")
    p_fc.set_defaults(func=_cmd_forecast)

    # benchmark
    p_bench = sub.add_parser("benchmark", help="Run the PVU-BS benchmark suite")
    p_bench.add_argument("--cases", type=str, default="datasets/pvu_cases", help="Cases directory")
    p_bench.add_argument(
        "--out", type=str, default="reports/validation/ci", help="Output directory"
    )
    p_bench.add_argument("--seed", type=int, default=42, help="RNG seed")
    p_bench_mode = p_bench.add_mutually_exclusive_group()
    p_bench_mode.add_argument("--offline", action="store_true", help="Offline mode (no LLM)")
    p_bench_mode.add_argument("--real", action="store_true", help="Real MASSIVE engine mode")
    p_bench_mode.add_argument("--llm", action="store_true", help="LLM mode (requires API key)")
    p_bench.set_defaults(func=_cmd_benchmark)

    # version
    p_ver = sub.add_parser("version", help="Print version and exit")
    p_ver.set_defaults(func=_cmd_version)

    # serve
    p_serve = sub.add_parser("serve", help="Start the FastAPI server (uvicorn)")
    p_serve.add_argument("--host", type=str, default="0.0.0.0", help="Bind host")
    p_serve.add_argument("--port", type=int, default=8000, help="Bind port")
    p_serve.add_argument("--workers", type=int, default=1, help="Number of uvicorn workers")
    p_serve.add_argument("--legacy", action="store_true", help="Use legacy api:app entry point")
    p_serve.set_defaults(func=_cmd_serve)

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI main entry-point.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code (0 on success).
    """
    parser = _build_parser()
    args = parser.parse_args(argv)
    _configure_logging(getattr(args, "verbose", False))
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
