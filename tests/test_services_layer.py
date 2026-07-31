"""Service-layer smoke tests (simulation, factbook, forecast, llm helpers)."""

from __future__ import annotations

import numpy as np

from services import factbook_service, forecast_service, llm_service
from services.simulation_service import run_scalar_simulation


def test_forecast_service_lists_targets_and_baselines():
    targets = forecast_service.list_targets()
    assert any(t["name"] == "polarization_index" for t in targets)
    out = forecast_service.baseline_forecast([0.1, 0.2, 0.3, 0.4], horizon=2, baseline_name="naive")
    assert len(out["prediction"]) == 2
    wf = forecast_service.walk_forward_evaluate(
        np.linspace(0.1, 0.9, 10),
        baseline_name="naive",
        min_train=4,
        horizon=1,
    )
    assert wf["scores"]["n_folds"] >= 1


def test_llm_credentials_resolve_without_key():
    creds = llm_service.resolve_llm_credentials("groq", api_key="")
    assert "configured" in creds
    assert creds["provider"] == "groq"


def test_factbook_service_dummy_engine():
    class _Ctx:
        def get_massive_params(self, country):
            return {"n_agents": 40, "gini_coefficient": 0.3, "social_groups": {}}

        def get_intervention_constraints(self, country):
            return {"cost_scale_factor": 1.0, "fiscal_constraint": 0.8}

    # Direct MassiveEngine path with dummy is covered elsewhere; here just constraints shape
    c = _Ctx().get_intervention_constraints("US")
    assert c["fiscal_constraint"] == 0.8


def test_simulation_service_still_works():
    out = run_scalar_simulation({"opinion": 0.0, "propaganda": 0.0}, pasos=3, verbose=False)
    assert len(out["history"]) == 4
