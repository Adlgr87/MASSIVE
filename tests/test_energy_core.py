"""
Suite de pruebas para el núcleo Energy de MASSIVE.
Cubre: SocialEnergyEngine, EnergySchemas, LandscapeCache, ProgrammaticArchitect, run_energy_simulation
"""
import pytest
import numpy as np
import json
import sqlite3
from pathlib import Path
from unittest.mock import patch, MagicMock

from energy_engine import SocialEnergyEngine, random_network
from energy_schemas import EnergyConfig, Attractor, Repeller, Dynamics, EnergyParams, Metadata
from cache_manager import LandscapeCache
from programmatic_architect import ProgrammaticArchitect, ARCHETYPES
from energy_runner import run_energy_simulation


# ============================================================
# FIXTURES
# ============================================================

@pytest.fixture
def engine_bipolar():
    return SocialEnergyEngine(range_type="bipolar", temperature=0.0, lambda_social=0.5)


@pytest.fixture
def engine_unipolar():
    return SocialEnergyEngine(range_type="unipolar", temperature=0.0, lambda_social=0.3)


@pytest.fixture
def simple_adj():
    A = np.zeros((3, 3))
    A[0, 1] = A[1, 0] = 1.0
    A[1, 2] = A[2, 1] = 1.0
    return A


@pytest.fixture
def valid_config_dict():
    return {
        "metadata": {"nombre_ui": "Test", "descripcion_ui": "Config de prueba", "icono": "🧪"},
        "energy_params": {
            "attractors": [{"position": -0.5, "strength": 2.0, "label": "A"}],
            "repellers": [{"position": 0.5, "strength": 1.5, "label": "R"}],
            "dynamics": {"temperature": 0.05, "eta": 0.01, "lambda_social": 0.6}
        }
    }


@pytest.fixture
def cache_tmp(tmp_path):
    db_path = str(tmp_path / "test_cache.db")
    return LandscapeCache(db_path=db_path)


# ============================================================
# TestEnergyEngine
# ============================================================

class TestEnergyEngine:

    def test_step_returns_same_shape(self, engine_bipolar, simple_adj):
        opinions = np.array([0.0, 0.5, -0.5])
        result = engine_bipolar.step(opinions, simple_adj, [], [], eta=0.01)
        assert result.shape == opinions.shape

    def test_step_clips_to_bipolar_range(self, engine_bipolar, simple_adj):
        opinions = np.array([0.0, 0.5, -0.5])
        attractors = [{"position": 0.9, "strength": 3.0, "label": "X"}]
        for _ in range(50):
            opinions = engine_bipolar.step(opinions, simple_adj, attractors, [], eta=0.05)
        assert np.all(opinions >= -1.0)
        assert np.all(opinions <= 1.0)

    def test_step_clips_to_unipolar_range(self, engine_unipolar, simple_adj):
        opinions = np.array([0.2, 0.5, 0.8])
        attractors = [{"position": 1.0, "strength": 3.0, "label": "X"}]
        for _ in range(50):
            opinions = engine_unipolar.step(opinions, simple_adj, attractors, [], eta=0.05)
        assert np.all(opinions >= 0.0)
        assert np.all(opinions <= 1.0)

    def test_attractor_pulls_opinions_toward_position(self, simple_adj):
        engine = SocialEnergyEngine(range_type="bipolar", temperature=0.0, lambda_social=0.0)
        opinions = np.array([-0.3, 0.0, 0.3])
        attractors = [{"position": 0.8, "strength": 2.5, "label": "Target"}]
        initial_dist = np.abs(opinions - 0.8).mean()
        for _ in range(30):
            opinions = engine.step(opinions, simple_adj, attractors, [], eta=0.02)
        final_dist = np.abs(opinions - 0.8).mean()
        assert final_dist < initial_dist

    def test_repeller_pushes_opinions_away(self, simple_adj):
        engine = SocialEnergyEngine(range_type="bipolar", temperature=0.0, lambda_social=0.0)
        opinions = np.array([-0.05, 0.0, 0.05])
        repellers = [{"position": 0.0, "strength": 2.5, "label": "Center"}]
        initial_dist = np.abs(opinions).mean()
        for _ in range(30):
            opinions = engine.step(opinions, simple_adj, [], repellers, eta=0.02)
        final_dist = np.abs(opinions).mean()
        assert final_dist > initial_dist

    def test_system_metrics_returns_required_keys(self, engine_bipolar, simple_adj):
        opinions = np.array([0.0, 0.5, -0.5])
        metrics = engine_bipolar.system_metrics(opinions, simple_adj, [], [])
        for key in ("mean_opinion", "std_opinion", "polarizacion", "energia_total", "energia_media", "n_clusters_approx"):
            assert key in metrics

    def test_system_metrics_polarization_bounded(self, engine_bipolar, simple_adj):
        opinions = np.array([0.0, 0.5, -0.5])
        metrics = engine_bipolar.system_metrics(opinions, simple_adj, [], [])
        assert 0.0 <= metrics["polarizacion"] <= 2.0

    def test_zero_temperature_deterministic(self, simple_adj):
        engine = SocialEnergyEngine(range_type="bipolar", temperature=0.0, lambda_social=0.5)
        opinions = np.array([0.1, 0.2, 0.3])
        attractors = [{"position": 0.5, "strength": 1.5, "label": "X"}]
        np.random.seed(0)
        r1 = engine.step(opinions.copy(), simple_adj, attractors, [], eta=0.01)
        np.random.seed(0)
        r2 = engine.step(opinions.copy(), simple_adj, attractors, [], eta=0.01)
        np.testing.assert_array_almost_equal(r1, r2)


# ============================================================
# TestRandomNetwork
# ============================================================

class TestRandomNetwork:

    def test_shape(self):
        adj = random_network(10)
        assert adj.shape == (10, 10)

    def test_symmetric(self):
        adj = random_network(20, connectivity=0.4, seed=1)
        np.testing.assert_array_equal(adj, adj.T)

    def test_no_self_loops(self):
        adj = random_network(15, seed=7)
        assert np.all(np.diag(adj) == 0)

    def test_connectivity_range(self):
        adj = random_network(30, connectivity=0.5, seed=3)
        assert np.all((adj == 0) | (adj == 1))

    def test_reproducible_with_seed(self):
        a1 = random_network(10, seed=42)
        a2 = random_network(10, seed=42)
        np.testing.assert_array_equal(a1, a2)

    def test_invalid_n_agents_raises(self):
        with pytest.raises(ValueError):
            random_network(1)


# ============================================================
# TestEnergySchemas
# ============================================================

class TestEnergySchemas:

    def test_valid_config_parses(self, valid_config_dict):
        cfg = EnergyConfig.model_validate(valid_config_dict)
        assert cfg.metadata.nombre_ui == "Test"
        assert len(cfg.energy_params.attractors) == 1
        assert len(cfg.energy_params.repellers) == 1

    def test_to_engine_dict_structure(self, valid_config_dict):
        cfg = EnergyConfig.model_validate(valid_config_dict)
        d = cfg.to_engine_dict()
        assert "attractors" in d
        assert "repellers" in d
        assert "dynamics" in d
        assert isinstance(d["attractors"], list)

    def test_attractor_position_out_of_range_raises(self):
        with pytest.raises(Exception):
            Attractor(position=1.5, strength=1.0)

    def test_repeller_strength_too_low_raises(self):
        with pytest.raises(Exception):
            Repeller(position=0.0, strength=0.1)

    def test_duplicate_attractor_positions_raises(self):
        data = {
            "metadata": {"nombre_ui": "T", "descripcion_ui": "desc", "icono": "🧪"},
            "energy_params": {
                "attractors": [
                    {"position": 0.5, "strength": 1.0, "label": "A"},
                    {"position": 0.5, "strength": 1.5, "label": "B"},
                ],
                "repellers": [],
                "dynamics": {"temperature": 0.05, "eta": 0.01, "lambda_social": 0.5}
            }
        }
        with pytest.raises(Exception):
            EnergyConfig.model_validate(data)

    def test_empty_attractors_and_repellers_allowed(self):
        data = {
            "metadata": {"nombre_ui": "Caos", "descripcion_ui": "Sin estructura", "icono": "🌀"},
            "energy_params": {
                "attractors": [],
                "repellers": [],
                "dynamics": {"temperature": 0.15, "eta": 0.01, "lambda_social": 0.3}
            }
        }
        cfg = EnergyConfig.model_validate(data)
        assert cfg.energy_params.attractors == []

    def test_extra_fields_forbidden(self):
        with pytest.raises(Exception):
            Attractor(position=0.0, strength=1.0, label="X", unknown_field="bad")


# ============================================================
# TestLandscapeCache
# ============================================================

class TestLandscapeCache:

    def test_set_and_get_from_memory(self, cache_tmp):
        cache_tmp.set("test goal", {"key": "value"})
        result = cache_tmp.get("test goal")
        assert result == {"key": "value"}

    def test_get_missing_returns_none(self, cache_tmp):
        assert cache_tmp.get("nonexistent goal") is None

    def test_persists_to_sqlite(self, tmp_path):
        db_path = str(tmp_path / "persist_test.db")
        c1 = LandscapeCache(db_path=db_path)
        c1.set("persistent", {"data": 42})

        c2 = LandscapeCache(db_path=db_path)
        result = c2.get("persistent")
        assert result == {"data": 42}

    def test_clear_removes_all(self, cache_tmp):
        cache_tmp.set("goal1", {"a": 1})
        cache_tmp.set("goal2", {"b": 2})
        cache_tmp.clear()
        assert cache_tmp.get("goal1") is None
        assert cache_tmp.get("goal2") is None

    def test_key_is_case_insensitive(self, cache_tmp):
        cache_tmp.set("My Goal", {"x": 1})
        assert cache_tmp.get("my goal") == {"x": 1}
        assert cache_tmp.get("MY GOAL") == {"x": 1}

    def test_overwrite_existing_key(self, cache_tmp):
        cache_tmp.set("goal", {"v": 1})
        cache_tmp.set("goal", {"v": 2})
        assert cache_tmp.get("goal") == {"v": 2}


# ============================================================
# TestProgrammaticArchitect
# ============================================================

class TestProgrammaticArchitect:

    def test_archetype_lookup_returns_correct(self):
        arch = ProgrammaticArchitect()
        result = arch.get_landscape("consenso_moderado")
        assert result["metadata"]["nombre_ui"] == "Búsqueda de Consenso"

    def test_all_archetypes_are_valid_configs(self):
        for key, cfg in ARCHETYPES.items():
            assert ProgrammaticArchitect._validate_config(cfg), f"Arquetipo inválido: {key}"

    def test_list_archetypes_returns_all(self):
        arch = ProgrammaticArchitect()
        keys = [a["key"] for a in arch.list_available_archetypes()]
        assert set(keys) == set(ARCHETYPES.keys())

    def test_fallback_to_caos_social_on_unknown_goal(self):
        arch = ProgrammaticArchitect()
        with patch("programmatic_architect.call_llm", return_value=None):
            result = arch.get_landscape("objetivo completamente desconocido xyz")
        assert result["metadata"]["nombre_ui"] == "Caos Social"

    def test_validate_config_rejects_invalid(self):
        bad_config = {"metadata": {}, "energy_params": {}}
        assert ProgrammaticArchitect._validate_config(bad_config) is False

    def test_llm_result_cached_after_success(self, tmp_path):
        db_path = str(tmp_path / "arch_cache.db")
        new_cache = LandscapeCache(db_path=db_path)

        fake_llm_response = ARCHETYPES["polarizacion_extrema"].copy()

        import programmatic_architect
        with patch.object(programmatic_architect, "_cache", new_cache):
            with patch("programmatic_architect.call_llm", return_value=fake_llm_response):
                arch = ProgrammaticArchitect()
                arch.get_landscape("escenario inventado unico")

        cached = new_cache.get("escenario inventado unico")
        assert cached is not None


# ============================================================
# TestRunEnergySimulation
# ============================================================

class TestRunEnergySimulation:

    def test_returns_required_keys(self):
        result = run_energy_simulation("consenso_moderado", n_agents=10, steps=5)
        for key in ("history", "metrics_timeline", "final_state", "summary", "config_used", "archetype_info"):
            assert key in result

    def test_history_length(self):
        result = run_energy_simulation("caos_social", n_agents=5, steps=10)
        assert len(result["history"]) == 11  # steps + 1 (includes step 0)

    def test_summary_structure(self):
        result = run_energy_simulation("polarizacion_extrema", n_agents=8, steps=5)
        summary = result["summary"]
        for key in ("opinion_inicial", "opinion_final", "delta_total", "polarizacion_media", "pasos"):
            assert key in summary
        assert summary["pasos"] == 5

    def test_opinions_in_bipolar_range(self):
        result = run_energy_simulation("radicalizacion_progresiva", n_agents=20, steps=10, range_type="bipolar")
        opinions = result["final_state"]["opinions"]
        assert all(-1.0 <= o <= 1.0 for o in opinions)

    def test_opinions_in_unipolar_range(self):
        result = run_energy_simulation("consenso_moderado", n_agents=20, steps=10, range_type="unipolar")
        opinions = result["final_state"]["opinions"]
        assert all(0.0 <= o <= 1.0 for o in opinions)

    def test_invalid_n_agents_raises(self):
        with pytest.raises(ValueError):
            run_energy_simulation("caos_social", n_agents=1, steps=5)

    def test_invalid_steps_raises(self):
        with pytest.raises(ValueError):
            run_energy_simulation("caos_social", n_agents=5, steps=0)

    def test_config_overrides_applied(self):
        result = run_energy_simulation(
            "consenso_moderado",
            n_agents=5,
            steps=3,
            config_overrides={"temperature": 0.15, "lambda_social": 0.9}
        )
        assert result["summary"]["pasos"] == 3

    def test_reproducible_with_same_seed(self):
        r1 = run_energy_simulation("fragmentacion_3_grupos", n_agents=10, steps=5, seed=0)
        r2 = run_energy_simulation("fragmentacion_3_grupos", n_agents=10, steps=5, seed=0)
        assert r1["final_state"]["mean_opinion"] == pytest.approx(r2["final_state"]["mean_opinion"])
