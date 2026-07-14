"""
MASSIVE Core Contracts Module

This module defines the canonical contracts (data classes and protocols) for the MASSIVE
simulation framework. These contracts ensure type safety, consistency, and interoperability
between different components of the system.

Following CLAUDE.md Section 3: Canonical state and configuration contracts.

Classes:
    SimulationState: Canonical simulation state representation
    SimulationConfig: Canonical simulation configuration
    SimulationResult: Canonical simulation result
    EngineProtocol: Protocol for all MASSIVE engines
    StepperProtocol: Protocol for numerical steppers
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List, Tuple, Union, Protocol, runtime_checkable
import numpy as np


# =============================================================================
# SIMULATION STATE CONTRACT
# =============================================================================

@dataclass
class SimulationState:
    """
    Canonical simulation state contract.
    
    This class defines the standard representation of a simulation state across
    all MASSIVE engines. It encapsulates the opinion, cooperation, hierarchy, 
    income, and information access dimensions for all agents.
    
    Following CLAUDE.md §3.1: "Definir SimulationState canónico"
    
    Attributes:
        opinion: Agent opinions (N x D_opinion)
        cooperation: Agent cooperation levels (N x D_cooperation)
        hierarchy: Agent hierarchy levels (N x D_hierarchy)
        income: Agent income levels (N x D_income)
        info_access: Agent information access (N x D_info)
        attributes: Additional agent attributes (optional)
        metadata: Additional metadata (optional)
    
    Note:
        N = number of agents
        D_* = dimensionality of each state variable
    """
    
    # Core state variables (all optional but at least one must be provided)
    opinion: Optional[np.ndarray] = None
    cooperation: Optional[np.ndarray] = None
    hierarchy: Optional[np.ndarray] = None
    income: Optional[np.ndarray] = None
    info_access: Optional[np.ndarray] = None
    
    # Additional data
    attributes: Optional[Dict[str, np.ndarray]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate simulation state after initialization."""
        # Check that at least one state variable is provided
        if all(v is None for v in [self.opinion, self.cooperation, self.hierarchy, 
                                       self.income, self.info_access]):
            raise ValueError("At least one state variable must be provided")
        
        # Validate shapes if provided
        self._validate_shapes()
    
    def _validate_shapes(self) -> None:
        """Validate that all state arrays have consistent shapes."""
        shapes = {}
        
        if self.opinion is not None:
            if self.opinion.ndim != 2:
                raise ValueError(f"opinion must be 2D array, got {self.opinion.ndim}D")
            shapes['opinion'] = self.opinion.shape
        
        if self.cooperation is not None:
            if self.cooperation.ndim != 2:
                raise ValueError(f"cooperation must be 2D array, got {self.cooperation.ndim}D")
            shapes['cooperation'] = self.cooperation.shape
        
        if self.hierarchy is not None:
            if self.hierarchy.ndim != 2:
                raise ValueError(f"hierarchy must be 2D array, got {self.hierarchy.ndim}D")
            shapes['hierarchy'] = self.hierarchy.shape
        
        if self.income is not None:
            if self.income.ndim != 2:
                raise ValueError(f"income must be 2D array, got {self.income.ndim}D")
            shapes['income'] = self.income.shape
        
        if self.info_access is not None:
            if self.info_access.ndim != 2:
                raise ValueError(f"info_access must be 2D array, got {self.info_access.ndim}D")
            shapes['info_access'] = self.info_access.shape
        
        # Check that all state variables have the same number of agents (first dimension)
        if shapes:
            n_agents = list(shapes.values())[0][0]
            for name, shape in shapes.items():
                if shape[0] != n_agents:
                    raise ValueError(
                        f"All state variables must have the same number of agents. "
                        f"{name} has {shape[0]}, expected {n_agents}"
                    )
    
    @property
    def n_agents(self) -> int:
        """Number of agents in the simulation."""
        if self.opinion is not None:
            return self.opinion.shape[0]
        elif self.cooperation is not None:
            return self.cooperation.shape[0]
        elif self.hierarchy is not None:
            return self.hierarchy.shape[0]
        elif self.income is not None:
            return self.income.shape[0]
        elif self.info_access is not None:
            return self.info_access.shape[0]
        else:
            raise RuntimeError("No state variable available to determine n_agents")
    
    @property
    def n_dimensions(self) -> Dict[str, int]:
        """Number of dimensions for each state variable."""
        dims = {}
        if self.opinion is not None:
            dims['opinion'] = self.opinion.shape[1]
        if self.cooperation is not None:
            dims['cooperation'] = self.cooperation.shape[1]
        if self.hierarchy is not None:
            dims['hierarchy'] = self.hierarchy.shape[1]
        if self.income is not None:
            dims['income'] = self.income.shape[1]
        if self.info_access is not None:
            dims['info_access'] = self.info_access.shape[1]
        return dims
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert simulation state to dictionary."""
        result = {}
        
        if self.opinion is not None:
            result['opinion'] = self.opinion.tolist()
        if self.cooperation is not None:
            result['cooperation'] = self.cooperation.tolist()
        if self.hierarchy is not None:
            result['hierarchy'] = self.hierarchy.tolist()
        if self.income is not None:
            result['income'] = self.income.tolist()
        if self.info_access is not None:
            result['info_access'] = self.info_access.tolist()
        
        if self.attributes is not None:
            result['attributes'] = {k: v.tolist() for k, v in self.attributes.items()}
        
        result['metadata'] = self.metadata
        
        return result
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimulationState':
        """Create SimulationState from dictionary."""
        kwargs = {}
        
        if 'opinion' in data:
            kwargs['opinion'] = np.array(data['opinion'])
        if 'cooperation' in data:
            kwargs['cooperation'] = np.array(data['cooperation'])
        if 'hierarchy' in data:
            kwargs['hierarchy'] = np.array(data['hierarchy'])
        if 'income' in data:
            kwargs['income'] = np.array(data['income'])
        if 'info_access' in data:
            kwargs['info_access'] = np.array(data['info_access'])
        
        if 'attributes' in data:
            kwargs['attributes'] = {k: np.array(v) for k, v in data['attributes'].items()}
        
        kwargs['metadata'] = data.get('metadata', {})
        
        return cls(**kwargs)
    
    def copy(self) -> 'SimulationState':
        """Create a deep copy of the simulation state."""
        return SimulationState(
            opinion=self.opinion.copy() if self.opinion is not None else None,
            cooperation=self.cooperation.copy() if self.cooperation is not None else None,
            hierarchy=self.hierarchy.copy() if self.hierarchy is not None else None,
            income=self.income.copy() if self.income is not None else None,
            info_access=self.info_access.copy() if self.info_access is not None else None,
            attributes={k: v.copy() for k, v in self.attributes.items()} if self.attributes is not None else None,
            metadata=self.metadata.copy(),
        )


# =============================================================================
# SIMULATION CONFIG CONTRACT
# =============================================================================

@dataclass
class SimulationConfig:
    """
    Canonical simulation configuration contract.
    
    This class defines the standard configuration for a MASSIVE simulation.
    It includes all parameters needed to initialize and run a simulation.
    
    Following CLAUDE.md §3.1: "Definir SimulationConfig canónico"
    
    Attributes:
        N: Number of agents
        M: Number of super-agents (optional, defaults to min(N, max(50, sqrt(N))))
        K: Number of layers
        dt: Time step for simulation
        steps: Number of simulation steps
        layer_weights: Weights for each layer (length K)
        temperature: Temperature parameter for stochastic dynamics
        seed: Random seed for reproducibility (optional)
        metadata: Additional configuration metadata (optional)
    
    Raises:
        ValueError: If any parameter has an invalid value
    """
    
    # Core parameters
    N: int
    K: int = 3
    dt: float = 0.01
    steps: int = 1000
    
    # Optional parameters with defaults
    M: Optional[int] = None
    layer_weights: Optional[Union[Tuple[float, ...], List[float]]] = None
    temperature: float = 0.1
    seed: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """Validate simulation configuration after initialization."""
        # Following CLAUDE.md §3.3: "Validación de parámetros"
        
        # N must be positive
        if self.N < 1:
            raise ValueError(f"N must be > 0, got {self.N}")
        
        # K must be positive
        if self.K < 1:
            raise ValueError(f"K must be > 0, got {self.K}")
        
        # dt must be positive
        if self.dt <= 0:
            raise ValueError(f"dt must be > 0, got {self.dt}")
        
        # steps must be positive
        if self.steps < 1:
            raise ValueError(f"steps must be > 0, got {self.steps}")
        
        # temperature must be non-negative
        if self.temperature < 0:
            raise ValueError(f"temperature must be >= 0, got {self.temperature}")
        
        # M must be positive and <= N
        if self.M is not None:
            if self.M < 1:
                raise ValueError(f"M must be > 0, got {self.M}")
            if self.M > self.N:
                raise ValueError(f"M must be <= N, got M={self.M}, N={self.N}")
        
        # layer_weights must have length K and sum > 0
        if self.layer_weights is not None:
            weights = np.asarray(self.layer_weights)
            if weights.ndim != 1:
                raise ValueError(f"layer_weights must be 1D array, got {weights.ndim}D")
            if len(weights) != self.K:
                raise ValueError(
                    f"layer_weights must have length K={self.K}, got {len(weights)}"
                )
            if weights.sum() <= 0:
                raise ValueError(f"sum(layer_weights) must be > 0, got {weights.sum()}")
        else:
            # Default: equal weights
            self.layer_weights = tuple(1.0 / self.K for _ in range(self.K))
        
        # Set default M if not provided
        if self.M is None:
            self.M = min(self.N, max(50, int(np.sqrt(self.N))))
    
    @property
    def effective_M(self) -> int:
        """Effective number of super-agents."""
        return self.M if self.M is not None else min(self.N, max(50, int(np.sqrt(self.N))))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert simulation config to dictionary."""
        return {
            'N': self.N,
            'K': self.K,
            'dt': self.dt,
            'steps': self.steps,
            'M': self.M,
            'layer_weights': list(self.layer_weights) if self.layer_weights is not None else None,
            'temperature': self.temperature,
            'seed': self.seed,
            'metadata': self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SimulationConfig':
        """Create SimulationConfig from dictionary."""
        kwargs = {}
        
        for key in ['N', 'K', 'dt', 'steps', 'M', 'temperature', 'seed']:
            if key in data:
                kwargs[key] = data[key]
        
        # Convert layer_weights to tuple if provided
        if 'layer_weights' in data and data['layer_weights'] is not None:
            kwargs['layer_weights'] = tuple(data['layer_weights'])
        
        if 'metadata' in data:
            kwargs['metadata'] = data['metadata']
        
        return cls(**kwargs)


# =============================================================================
# SIMULATION RESULT CONTRACT
# =============================================================================

@dataclass
class SimulationResult:
    """
    Canonical simulation result contract.
    
    This class defines the standard result of a simulation run, including
    final states, history, metrics, and diagnostics.
    
    Attributes:
        final_state: Final state of the simulation
        history: List of states at each time step (optional)
        metrics: Dictionary of simulation metrics
        diagnostics: Diagnostic information
        metadata: Additional metadata (optional)
    """
    
    final_state: SimulationState
    history: Optional[List[SimulationState]] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def num_steps(self) -> int:
        """Number of simulation steps."""
        if self.history is not None:
            return len(self.history)
        return 0
    
    def get_state_at(self, step: int) -> SimulationState:
        """Get state at a specific step."""
        if self.history is None:
            raise ValueError("No history available")
        if step < 0 or step >= len(self.history):
            raise IndexError(f"Step {step} out of range (0-{len(self.history)-1})")
        return self.history[step]


# =============================================================================
# PROTOCOLS
# =============================================================================

@runtime_checkable
class EngineProtocol(Protocol):
    """
    Protocol for all MASSIVE engines.
    
    This protocol defines the interface that all MASSIVE engines must implement.
    Following CLAUDE.md §3.1: "Definir interfaces canónicas"
    """
    
    def reset(self, state: Optional[SimulationState] = None) -> None:
        """Reset engine state."""
        ...
    
    def step(self, dt: Optional[float] = None) -> SimulationState:
        """Perform one simulation step."""
        ...
    
    def run(self, steps: int) -> SimulationResult:
        """Run simulation for given steps."""
        ...
    
    def metrics(self) -> Dict[str, Any]:
        """Return engine metrics."""
        ...


@runtime_checkable
class StepperProtocol(Protocol):
    """
    Protocol for numerical steppers.
    
    This protocol defines the interface for numerical integration steppers.
    """
    
    def step(
        self,
        x: np.ndarray,
        dt: float,
        drift: Optional[Any] = None,
        diffusion: Optional[Any] = None,
        bounds: Optional[Tuple[Any, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Perform one integration step."""
        ...


# =============================================================================
# LEGACY ADAPTERS
# =============================================================================

def legacy_dict_to_simulation_state(legacy_dict: Dict[str, Any]) -> SimulationState:
    """
    Convert legacy Spanish-keyed dictionary to SimulationState.
    
    This adapter handles the conversion from the legacy format (used in
    massive_sim_engine.py and other legacy modules) to the canonical
    SimulationState format.
    
    Following CLAUDE.md §3.2: "Crear adaptadores Legacy → Contratos"
    
    Args:
        legacy_dict: Dictionary with legacy keys (e.g., 'opinion', 'cooperacion')
        
    Returns:
        SimulationState object with canonical format
    """
    # Mapping from legacy keys to canonical keys
    legacy_to_canonical = {
        'opinion': 'opinion',
        'cooperacion': 'cooperation',
        'jerarquia': 'hierarchy',
        'ingresos': 'income',
        'acceso_info': 'info_access',
    }
    
    kwargs = {}
    for legacy_key, canonical_key in legacy_to_canonical.items():
        if legacy_key in legacy_dict:
            value = legacy_dict[legacy_key]
            if isinstance(value, (list, tuple)):
                kwargs[canonical_key] = np.array(value)
            elif isinstance(value, np.ndarray):
                kwargs[canonical_key] = value
    
    # Handle additional attributes
    attributes = {}
    for key, value in legacy_dict.items():
        if key not in legacy_to_canonical and key not in ['metadata']:
            if isinstance(value, (list, tuple, np.ndarray)):
                attributes[key] = np.array(value)
    
    if attributes:
        kwargs['attributes'] = attributes
    
    # Handle metadata
    if 'metadata' in legacy_dict:
        kwargs['metadata'] = legacy_dict['metadata']
    
    return SimulationState(**kwargs)


def simulation_state_to_legacy_dict(state: SimulationState) -> Dict[str, Any]:
    """
    Convert SimulationState to legacy dictionary format.
    
    This adapter handles the conversion from the canonical SimulationState
    format to the legacy format (used in massive_sim_engine.py and other
    legacy modules).
    
    Args:
        state: SimulationState object
        
    Returns:
        Dictionary with legacy keys
    """
    # Mapping from canonical keys to legacy keys
    canonical_to_legacy = {
        'opinion': 'opinion',
        'cooperation': 'cooperacion',
        'hierarchy': 'jerarquia',
        'income': 'ingresos',
        'info_access': 'acceso_info',
    }
    
    legacy = {}
    
    for canonical_key, legacy_key in canonical_to_legacy.items():
        value = getattr(state, canonical_key)
        if value is not None:
            legacy[legacy_key] = value.tolist() if isinstance(value, np.ndarray) else value
    
    # Handle additional attributes
    if state.attributes is not None:
        for key, value in state.attributes.items():
            legacy[key] = value.tolist() if isinstance(value, np.ndarray) else value
    
    # Handle metadata
    if state.metadata:
        legacy['metadata'] = state.metadata
    
    return legacy


def legacy_config_to_simulation_config(legacy_config: Dict[str, Any]) -> SimulationConfig:
    """
    Convert legacy configuration to SimulationConfig.
    
    Args:
        legacy_config: Dictionary with legacy configuration
        
    Returns:
        SimulationConfig object
    """
    # Mapping from legacy keys to canonical keys
    legacy_to_canonical = {
        'N': 'N',
        'M': 'M',
        'K': 'K',
        'dt': 'dt',
        'steps': 'steps',
        'layer_weights': 'layer_weights',
        'temperature': 'temperature',
        'seed': 'seed',
    }
    
    kwargs = {}
    for legacy_key, canonical_key in legacy_to_canonical.items():
        if legacy_key in legacy_config:
            # Convert layer_weights to tuple
            if canonical_key == 'layer_weights' and legacy_config[legacy_key] is not None:
                kwargs[canonical_key] = tuple(legacy_config[legacy_key])
            else:
                kwargs[canonical_key] = legacy_config[legacy_key]
    
    # Handle metadata
    if 'metadata' in legacy_config:
        kwargs['metadata'] = legacy_config['metadata']
    
    return SimulationConfig(**kwargs)


def simulation_config_to_legacy_dict(config: SimulationConfig) -> Dict[str, Any]:
    """
    Convert SimulationConfig to legacy dictionary format.
    
    Args:
        config: SimulationConfig object
        
    Returns:
        Dictionary with legacy keys
    """
    legacy = {
        'N': config.N,
        'K': config.K,
        'dt': config.dt,
        'steps': config.steps,
        'M': config.M,
        'layer_weights': list(config.layer_weights) if config.layer_weights is not None else None,
        'temperature': config.temperature,
    }
    
    if config.seed is not None:
        legacy['seed'] = config.seed
    
    if config.metadata:
        legacy['metadata'] = config.metadata
    
    return legacy
