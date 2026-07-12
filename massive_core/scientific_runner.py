"""High-level scientific simulation runner for MASSIVE.

The runner keeps the legacy simulator untouched and adds an opt-in envelope that
can return legacy summaries together with scientific reports for UI/API callers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

from massive_core.config import ScientificRuntimeConfig
from massive_core.data_assimilation import AssimilationResult, assimilate_history_observations
from massive_core.diagnostics import ScientificReport, build_scientific_report


@dataclass(frozen=True)
class ScientificSimulationResult:
    """Serializable result of a MASSIVE run with optional diagnostics.

    Args:
        history: Legacy MASSIVE history returned by ``simular``.
        summary: Legacy summary returned by ``resumen_historial``.
        scientific_report: Optional scientific trajectory report.
        assimilation_result: Optional EnKF assimilation result.
        scientific_config: Runtime scientific configuration used for the run.
    """

    history: list[dict[str, Any]]
    summary: dict[str, Any]
    scientific_report: ScientificReport | None
    assimilation_result: AssimilationResult | None
    scientific_config: ScientificRuntimeConfig

    def to_dict(self) -> dict[str, Any]:
        """Convert the result to a JSON-friendly dictionary.

        Returns:
            Dictionary containing history, summary, config and optional report.
        """

        return {
            "history": self.history,
            "summary": self.summary,
            "scientific_report": (
                self.scientific_report.to_dict() if self.scientific_report is not None else None
            ),
            "assimilation_result": (
                self.assimilation_result.to_dict() if self.assimilation_result is not None else None
            ),
            "scientific_config": asdict(self.scientific_config),
        }


def run_scientific_simulation(
    estado_inicial: dict[str, Any],
    escenario: str = "campana",
    pasos: int = 50,
    cada_n_pasos: int = 5,
    config: dict[str, Any] | None = None,
    scientific_config: dict[str, Any] | ScientificRuntimeConfig | None = None,
    observations: dict[int, Any] | list[tuple[int, Any]] | None = None,
    verbose: bool = True,
) -> ScientificSimulationResult:
    """Run the legacy simulator and attach opt-in scientific diagnostics.

    Args:
        estado_inicial: Initial state accepted by ``simular``.
        escenario: Scenario key accepted by the legacy simulator.
        pasos: Number of simulation steps.
        cada_n_pasos: LLM/rule-selection update frequency.
        config: Optional legacy simulator config overrides.
        scientific_config: Optional scientific feature flags. If
            ``enable_scientific_report`` is true, a ``ScientificReport`` is
            computed from the returned history. If ``enable_data_assimilation``
            is true and observations are supplied, an EnKF analysis is computed.
        observations: Optional sparse observations keyed by simulation step.
        verbose: Whether to keep legacy simulator logging enabled.

    Returns:
        ``ScientificSimulationResult`` containing legacy outputs plus optional
        scientific diagnostics.
    """

    runtime_config = _coerce_scientific_config(scientific_config)

    from simulator import resumen_historial, simular

    history = simular(
        estado_inicial,
        escenario=escenario,
        pasos=pasos,
        cada_n_pasos=cada_n_pasos,
        config=config,
        verbose=verbose,
    )
    summary = resumen_historial(history, config)
    report = None
    if runtime_config.enable_scientific_report:
        dt = float((config or {}).get("dt", 1.0))
        report = build_scientific_report(history, dt=dt)

    assimilation = None
    if runtime_config.enable_data_assimilation and observations is not None:
        assimilation = assimilate_history_observations(history, observations)

    return ScientificSimulationResult(
        history=history,
        summary=summary,
        scientific_report=report,
        assimilation_result=assimilation,
        scientific_config=runtime_config,
    )

@dataclass(frozen=True)
class ScientificEngineResult:
    """Serializable result for non-legacy scientific engine runs.

    Args:
        history: Array snapshots produced by an engine.
        scientific_report: Optional scientific report.
        numerical_diagnostics: Per-step numerical diagnostics, when available.
        scientific_config: Runtime scientific configuration.
    """

    history: list[Any]
    scientific_report: ScientificReport | None
    numerical_diagnostics: list[dict[str, Any]]
    scientific_config: ScientificRuntimeConfig

    def to_dict(self) -> dict[str, Any]:
        """Convert the engine result to a JSON-friendly dictionary.

        Returns:
            Serializable result payload.
        """

        return {
            "history": [np.asarray(item).tolist() for item in self.history],
            "scientific_report": (
                self.scientific_report.to_dict() if self.scientific_report is not None else None
            ),
            "numerical_diagnostics": self.numerical_diagnostics,
            "scientific_config": asdict(self.scientific_config),
        }


def run_energy_scientific_simulation(
    opinions: Any,
    adj: Any,
    attractors: list[dict[str, Any]] | None = None,
    repellers: list[dict[str, Any]] | None = None,
    steps: int = 50,
    eta: float = 0.01,
    range_type: str = "bipolar",
    temperature: float = 0.05,
    lambda_social: float = 0.5,
    scientific_config: dict[str, Any] | ScientificRuntimeConfig | None = None,
) -> ScientificEngineResult:
    """Run ``SocialEnergyEngine`` with optional scientific diagnostics.

    Args:
        opinions: Initial opinion vector.
        adj: Social adjacency matrix.
        attractors: Optional energy attractors.
        repellers: Optional energy repellers.
        steps: Number of integration steps.
        eta: Time step.
        range_type: Energy engine opinion range.
        temperature: Langevin temperature.
        lambda_social: Social coupling weight.
        scientific_config: Optional scientific feature flags.

    Returns:
        Scientific engine result.
    """

    if steps < 1:
        raise ValueError("steps must be positive")
    runtime_config = _coerce_scientific_config(scientific_config)
    from energy_engine import SocialEnergyEngine

    engine = SocialEnergyEngine(
        range_type=range_type,
        temperature=temperature,
        lambda_social=lambda_social,
        scientific_config=asdict(runtime_config),
    )
    state = np.asarray(opinions, dtype=float)
    history = [state.copy()]
    diagnostics = []
    for _ in range(steps):
        state = engine.step(state, np.asarray(adj, dtype=float), attractors or [], repellers or [], eta=eta)
        history.append(state.copy())
        diagnostics.append(_diagnostics_to_dict(engine.last_numerical_diagnostics))
    report = build_scientific_report(history, dt=eta) if runtime_config.enable_scientific_report else None
    return ScientificEngineResult(history, report, diagnostics, runtime_config)


def run_multilayer_scientific_simulation(
    steps: int = 100,
    scientific_config: dict[str, Any] | ScientificRuntimeConfig | None = None,
    **engine_kwargs: Any,
) -> ScientificEngineResult:
    """Run ``MultilayerEngine`` with optional scientific diagnostics.

    Args:
        steps: Number of integration steps.
        scientific_config: Optional scientific feature flags.
        **engine_kwargs: Keyword arguments forwarded to ``MultilayerEngine``.

    Returns:
        Scientific engine result.
    """

    if steps < 1:
        raise ValueError("steps must be positive")
    runtime_config = _coerce_scientific_config(scientific_config)
    from multilayer_engine import MultilayerEngine

    engine = MultilayerEngine(scientific_config=asdict(runtime_config), **engine_kwargs)
    history = [engine.x.copy()]
    diagnostics = []
    for _ in range(steps):
        history.append(engine.step().copy())
        diagnostics.append(_diagnostics_to_dict(engine.last_numerical_diagnostics))
    report = build_scientific_report(history, dt=engine.dt) if runtime_config.enable_scientific_report else None
    return ScientificEngineResult(history, report, diagnostics, runtime_config)


def _diagnostics_to_dict(diagnostics: Any) -> dict[str, Any]:
    if diagnostics is None:
        return {}
    payload = asdict(diagnostics)
    return payload


def _coerce_scientific_config(
    config: dict[str, Any] | ScientificRuntimeConfig | None,
) -> ScientificRuntimeConfig:
    if isinstance(config, ScientificRuntimeConfig):
        return config
    return ScientificRuntimeConfig.from_dict(config)
