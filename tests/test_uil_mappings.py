"""Tests for Document Intelligence / Wizard → simulator key mappings."""

from document_intelligence import MASSIVEExtractedConfig
from interpreter_layer import WizardResult


def test_extracted_config_maps_homofilia_to_tasa():
    cfg = MASSIVEExtractedConfig(homofilia=0.12, opinion_inicial=0.3)
    flat = cfg.to_simular_kwargs()
    assert "homofilia_tasa" in flat
    assert flat["homofilia_tasa"] == 0.12
    assert "homofilia_rate" not in flat
    assert flat["opinion"] == 0.3


def test_config_dict_alias_matches_to_simular_kwargs():
    cfg = MASSIVEExtractedConfig(sesgo_confirmacion=0.4, pasos=40)
    assert cfg.config_dict == cfg.to_simular_kwargs()


def test_to_simulation_request_splits_estado_and_config():
    cfg = MASSIVEExtractedConfig(
        opinion_inicial=-0.2,
        propaganda=0.1,
        confianza_institucional=0.5,
        homofilia=0.08,
        pasos=33,
        regla_sugerida="campana",
    )
    req = cfg.to_simulation_request()
    assert req["estado_inicial"]["opinion"] == -0.2
    assert req["estado_inicial"]["propaganda"] == 0.1
    assert req["estado_inicial"]["confianza"] == 0.5
    assert req["config"]["homofilia_tasa"] == 0.08
    assert req["escenario"] == "campana"
    assert req["pasos"] == 33


def test_wizard_result_aliases_homofilia_rate():
    wr = WizardResult(config={"homofilia_rate": 0.09, "opinion": 0.1, "unused": None})
    out = wr.to_simular_kwargs()
    assert out["homofilia_tasa"] == 0.09
    assert "homofilia_rate" not in out
    assert "unused" not in out
    assert out["opinion"] == 0.1
