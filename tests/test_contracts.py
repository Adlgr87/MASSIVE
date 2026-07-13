"""
Tests for MASSIVE Core Contracts

This module contains tests for the canonical contracts defined in massive_core.contracts.
Following CLAUDE.md Section 3.4: "Tests de integración para contratos"
"""

import pytest
import numpy as np
from massive_core.contracts import (
    SimulationState,
    SimulationConfig,
    SimulationResult,
    legacy_dict_to_simulation_state,
    simulation_state_to_legacy_dict,
    legacy_config_to_simulation_config,
    simulation_config_to_legacy_dict,
)


# =============================================================================
# SIMULATION STATE TESTS
# =============================================================================

class TestSimulationState:
    """Tests for SimulationState contract."""
    
    def test_create_with_opinion_only(self):
        """Test creating SimulationState with only opinion."""
        opinion = np.random.randn(100, 2)
        state = SimulationState(opinion=opinion)
        
        assert state.n_agents == 100
        assert state.n_dimensions['opinion'] == 2
        assert np.array_equal(state.opinion, opinion)
    
    def test_create_with_all_states(self):
        """Test creating SimulationState with all state variables."""
        state = SimulationState(
            opinion=np.random.randn(100, 2),
            cooperation=np.random.randn(100, 1),
            hierarchy=np.random.randn(100, 3),
            income=np.random.randn(100, 1),
            info_access=np.random.randn(100, 2),
        )
        
        assert state.n_agents == 100
        assert state.n_dimensions == {
            'opinion': 2,
            'cooperation': 1,
            'hierarchy': 3,
            'income': 1,
            'info_access': 2,
        }
    
    def test_create_with_attributes(self):
        """Test creating SimulationState with additional attributes."""
        state = SimulationState(
            opinion=np.random.randn(100, 2),
            attributes={
                'age': np.random.randint(0, 100, 100),
                'gender': np.random.randint(0, 2, 100),
            }
        )
        
        assert 'age' in state.attributes
        assert 'gender' in state.attributes
        assert len(state.attributes['age']) == 100
    
    def test_create_with_metadata(self):
        """Test creating SimulationState with metadata."""
        state = SimulationState(
            opinion=np.random.randn(100, 2),
            metadata={'simulation_id': 'test-001', 'timestamp': 1234567890}
        )
        
        assert state.metadata['simulation_id'] == 'test-001'
        assert state.metadata['timestamp'] == 1234567890
    
    def test_invalid_no_state_variables(self):
        """Test that creating SimulationState with no variables raises error."""
        with pytest.raises(ValueError, match="At least one state variable"):
            SimulationState()
    
    def test_invalid_opinion_shape(self):
        """Test that invalid opinion shape raises error."""
        with pytest.raises(ValueError, match="opinion must be 2D"):
            SimulationState(opinion=np.random.randn(100))
    
    def test_invalid_agent_count_mismatch(self):
        """Test that mismatched agent counts raise error."""
        with pytest.raises(ValueError, match="same number of agents"):
            SimulationState(
                opinion=np.random.randn(100, 2),
                cooperation=np.random.randn(50, 1),  # Different number of agents
            )
    
    def test_to_dict(self):
        """Test converting SimulationState to dictionary."""
        state = SimulationState(
            opinion=np.array([[1.0, 2.0], [3.0, 4.0]]),
            cooperation=np.array([[0.5], [0.6]]),  # ✅ Same number of agents (2)
            metadata={'test': True}
        )
        
        result = state.to_dict()
        
        assert 'opinion' in result
        assert 'cooperation' in result
        assert 'metadata' in result
        assert result['metadata']['test'] is True
    
    def test_from_dict(self):
        """Test creating SimulationState from dictionary."""
        data = {
            'opinion': [[1.0, 2.0], [3.0, 4.0]],
            'cooperation': [[0.5], [0.6]],  # ✅ Same number of agents (2)
            'metadata': {'test': True}
        }
        
        state = SimulationState.from_dict(data)
        
        assert state.n_agents == 2
        assert state.n_dimensions['opinion'] == 2
        assert state.metadata['test'] is True
    
    def test_copy(self):
        """Test copying SimulationState."""
        state = SimulationState(
            opinion=np.array([[1.0, 2.0], [3.0, 4.0]]),
            metadata={'test': True}
        )
        
        copy = state.copy()
        
        # Modify original
        state.opinion[0, 0] = 999.0
        state.metadata['test'] = False
        
        # Copy should be unchanged
        assert copy.opinion[0, 0] == 1.0
        assert copy.metadata['test'] is True


# =============================================================================
# SIMULATION CONFIG TESTS
# =============================================================================

class TestSimulationConfig:
    """Tests for SimulationConfig contract."""
    
    def test_create_default(self):
        """Test creating SimulationConfig with defaults."""
        config = SimulationConfig(N=100)
        
        assert config.N == 100
        assert config.K == 3
        assert config.dt == 0.01
        assert config.steps == 1000
        assert config.temperature == 0.1
        assert config.M is not None  # Should be auto-calculated
    
    def test_create_with_all_params(self):
        """Test creating SimulationConfig with all parameters."""
        config = SimulationConfig(
            N=100,
            K=2,
            dt=0.001,
            steps=500,
            M=20,
            layer_weights=(0.6, 0.4),
            temperature=0.5,
            seed=42,
        )
        
        assert config.N == 100
        assert config.K == 2
        assert config.dt == 0.001
        assert config.steps == 500
        assert config.M == 20
        assert config.layer_weights == (0.6, 0.4)
        assert config.temperature == 0.5
        assert config.seed == 42
    
    def test_auto_calculate_M(self):
        """Test that M is auto-calculated when not provided."""
        config = SimulationConfig(N=100, K=3)
        
        # M should be min(N, max(50, sqrt(N)))
        # sqrt(100) = 10, max(50, 10) = 50, min(100, 50) = 50
        assert config.M == 50
    
    def test_auto_calculate_layer_weights(self):
        """Test that layer_weights are auto-calculated when not provided."""
        config = SimulationConfig(N=100, K=3)
        
        # Should be equal weights
        assert config.layer_weights == (1/3, 1/3, 1/3)
    
    def test_invalid_N(self):
        """Test that invalid N raises error."""
        with pytest.raises(ValueError, match="N must be > 0"):
            SimulationConfig(N=0)
        
        with pytest.raises(ValueError, match="N must be > 0"):
            SimulationConfig(N=-10)
    
    def test_invalid_K(self):
        """Test that invalid K raises error."""
        with pytest.raises(ValueError, match="K must be > 0"):
            SimulationConfig(N=100, K=0)
    
    def test_invalid_dt(self):
        """Test that invalid dt raises error."""
        with pytest.raises(ValueError, match="dt must be > 0"):
            SimulationConfig(N=100, dt=0)
        
        with pytest.raises(ValueError, match="dt must be > 0"):
            SimulationConfig(N=100, dt=-0.01)
    
    def test_invalid_steps(self):
        """Test that invalid steps raises error."""
        with pytest.raises(ValueError, match="steps must be > 0"):
            SimulationConfig(N=100, steps=0)
    
    def test_invalid_temperature(self):
        """Test that invalid temperature raises error."""
        with pytest.raises(ValueError, match="temperature must be >= 0"):
            SimulationConfig(N=100, temperature=-0.1)
    
    def test_invalid_M_too_large(self):
        """Test that M > N raises error."""
        with pytest.raises(ValueError, match="M must be <= N"):
            SimulationConfig(N=100, M=150)
    
    def test_invalid_layer_weights_length(self):
        """Test that wrong length layer_weights raises error."""
        with pytest.raises(ValueError, match="layer_weights must have length K"):
            SimulationConfig(N=100, K=3, layer_weights=(0.5, 0.5))  # Only 2 weights for K=3
    
    def test_invalid_layer_weights_sum(self):
        """Test that zero sum layer_weights raises error."""
        with pytest.raises(ValueError, match="sum\(layer_weights\) must be > 0"):
            SimulationConfig(N=100, K=3, layer_weights=(0.0, 0.0, 0.0))
    
    def test_to_dict(self):
        """Test converting SimulationConfig to dictionary."""
        config = SimulationConfig(
            N=100,
            K=2,
            dt=0.001,
            steps=500,
            M=20,
            layer_weights=(0.6, 0.4),
            temperature=0.5,
            seed=42,
        )
        
        result = config.to_dict()
        
        assert result['N'] == 100
        assert result['K'] == 2
        assert result['dt'] == 0.001
        assert result['steps'] == 500
        assert result['M'] == 20
        assert result['layer_weights'] == [0.6, 0.4]
        assert result['temperature'] == 0.5
        assert result['seed'] == 42
    
    def test_from_dict(self):
        """Test creating SimulationConfig from dictionary."""
        data = {
            'N': 100,
            'K': 2,
            'dt': 0.001,
            'steps': 500,
            'M': 20,
            'layer_weights': [0.6, 0.4],
            'temperature': 0.5,
            'seed': 42,
        }
        
        config = SimulationConfig.from_dict(data)
        
        assert config.N == 100
        assert config.K == 2
        assert config.dt == 0.001
        assert config.steps == 500
        assert config.M == 20
        assert config.layer_weights == (0.6, 0.4)
        assert config.temperature == 0.5
        assert config.seed == 42


# =============================================================================
# LEGACY ADAPTER TESTS
# =============================================================================

class TestLegacyAdapters:
    """Tests for legacy adapter functions."""
    
    def test_legacy_dict_to_simulation_state_basic(self):
        """Test basic legacy dict to SimulationState conversion."""
        legacy_dict = {
            'opinion': [[1.0, 2.0], [3.0, 4.0]],
            'cooperacion': [[0.5], [0.6]],
        }
        
        state = legacy_dict_to_simulation_state(legacy_dict)
        
        assert state.n_agents == 2
        assert state.n_dimensions['opinion'] == 2
        assert state.n_dimensions['cooperation'] == 1
    
    def test_legacy_dict_to_simulation_state_all_fields(self):
        """Test conversion with all legacy fields."""
        legacy_dict = {
            'opinion': [[1.0, 2.0], [3.0, 4.0]],
            'cooperacion': [[0.5], [0.6]],
            'jerarquia': [[1.0, 2.0], [3.0, 4.0]],
            'ingresos': [[100.0], [200.0]],
            'acceso_info': [[0.8, 0.9], [0.7, 0.6]],
            'metadata': {'test': True},
        }
        
        state = legacy_dict_to_simulation_state(legacy_dict)
        
        assert state.n_agents == 2
        assert 'opinion' in state.n_dimensions
        assert 'cooperation' in state.n_dimensions
        assert 'hierarchy' in state.n_dimensions
        assert 'income' in state.n_dimensions
        assert 'info_access' in state.n_dimensions
        assert state.metadata['test'] is True
    
    def test_simulation_state_to_legacy_dict(self):
        """Test SimulationState to legacy dict conversion."""
        state = SimulationState(
            opinion=np.array([[1.0, 2.0], [3.0, 4.0]]),
            cooperation=np.array([[0.5], [0.6]]),
        )
        
        legacy_dict = simulation_state_to_legacy_dict(state)
        
        assert 'opinion' in legacy_dict
        assert 'cooperacion' in legacy_dict
        assert legacy_dict['opinion'] == [[1.0, 2.0], [3.0, 4.0]]
    
    def test_roundtrip_legacy_state(self):
        """Test roundtrip conversion: legacy -> canonical -> legacy."""
        original = {
            'opinion': [[1.0, 2.0], [3.0, 4.0]],
            'cooperacion': [[0.5], [0.6]],
            'jerarquia': [[1.0], [2.0]],
        }
        
        # Legacy -> Canonical
        canonical = legacy_dict_to_simulation_state(original)
        
        # Canonical -> Legacy
        converted = simulation_state_to_legacy_dict(canonical)
        
        # Check that all fields are preserved
        assert 'opinion' in converted
        assert 'cooperacion' in converted
        assert 'jerarquia' in converted
    
    def test_legacy_config_to_simulation_config(self):
        """Test legacy config to SimulationConfig conversion."""
        legacy_config = {
            'N': 100,
            'K': 3,
            'dt': 0.01,
            'steps': 1000,
            'M': 50,
            'layer_weights': [0.4, 0.3, 0.3],  # ✅ Length matches K=3
            'temperature': 0.1,
            'seed': 42,
        }
        
        config = legacy_config_to_simulation_config(legacy_config)
        
        assert config.N == 100
        assert config.K == 3
        assert config.dt == 0.01
        assert config.steps == 1000
        assert config.M == 50
        assert config.layer_weights == (0.4, 0.3, 0.3)
        assert config.temperature == 0.1
        assert config.seed == 42
    
    def test_simulation_config_to_legacy_dict(self):
        """Test SimulationConfig to legacy dict conversion."""
        config = SimulationConfig(
            N=100,
            K=3,
            dt=0.01,
            steps=1000,
            M=50,
            layer_weights=(0.4, 0.3, 0.3),
            temperature=0.1,
            seed=42,
        )
        
        legacy_dict = simulation_config_to_legacy_dict(config)
        
        assert legacy_dict['N'] == 100
        assert legacy_dict['K'] == 3
        assert legacy_dict['dt'] == 0.01
        assert legacy_dict['steps'] == 1000
        assert legacy_dict['M'] == 50
        assert legacy_dict['layer_weights'] == [0.4, 0.3, 0.3]
        assert legacy_dict['temperature'] == 0.1
        assert legacy_dict['seed'] == 42
    
    def test_roundtrip_legacy_config(self):
        """Test roundtrip conversion: legacy -> canonical -> legacy."""
        original = {
            'N': 100,
            'K': 3,
            'dt': 0.01,
            'steps': 1000,
        }
        
        # Legacy -> Canonical
        canonical = legacy_config_to_simulation_config(original)
        
        # Canonical -> Legacy
        converted = simulation_config_to_legacy_dict(canonical)
        
        # Check that all fields are preserved
        assert converted['N'] == original['N']
        assert converted['K'] == original['K']
        assert converted['dt'] == original['dt']
        assert converted['steps'] == original['steps']


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for contracts with other MASSIVE components."""
    
    def test_simulation_config_with_multilayer_engine(self):
        """Test that SimulationConfig works with MultilayerEngine."""
        from multilayer_engine import MultilayerEngine
        
        config = SimulationConfig(N=100, K=3)
        
        # Create engine with config parameters
        engine = MultilayerEngine(
            N=config.N,
            layer_weights=config.layer_weights,
        )
        
        assert engine.N == config.N
        assert len(engine.layer_weights) == config.K
    
    def test_simulation_state_compatibility(self):
        """Test that SimulationState is compatible with legacy code."""
        # Create a state using canonical contract
        state = SimulationState(
            opinion=np.random.randn(100, 2),
            cooperation=np.random.randn(100, 1),
        )
        
        # Convert to legacy format
        legacy = simulation_state_to_legacy_dict(state)
        
        # Verify it has the expected legacy keys
        assert 'opinion' in legacy
        assert 'cooperacion' in legacy
        
        # Convert back to canonical
        canonical = legacy_dict_to_simulation_state(legacy)
        
        # Verify it matches the original
        assert canonical.n_agents == state.n_agents
