# World Factbook Integration Plan for MASSIVE

## Executive Summary

This document provides a complete integration plan for incorporating CIA World Factbook data into the MASSIVE framework. The integration enables **empirically-grounded simulations** by initializing agent populations with real-world country data, validating results against actual metrics, and enabling cross-country comparative analysis.

---

## 1. Architecture Overview

### 1.1 Integration Philosophy

```
┌─────────────────────────────────────────────────────────────┐
│                    MASSIVE Framework                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────┐         ┌──────────────────────┐         │
│  │   Factbook   │         │   Simulation Engine  │         │
│  │   Context    │────────▶│                      │         │
│  │   Module     │         │  - Agent Init        │         │
│  │              │         │  - Parameter Config  │         │
│  └──────────────┘         │  - Validation        │         │
│                           └──────────────────────┘         │
│                                                             │
│  Data Flow: Factbook → Context → MASSIVE → Results         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Core Components

**1. FactbookLoader** - Carga y cachea datos del World Factbook  
**2. ContextMapper** - Mapea datos Factbook → parámetros MASSIVE  
**3. AgentInitializer** - Inicializa agentes con datos reales  
**4. SimulationValidator** - Valida resultados contra datos reales  
**5. ComparativeAnalyzer** - Ejecuta simulaciones cross-country  

---

## 2. Data Structure Analysis

### 2.1 World Factbook Structure

El World Factbook organiza datos en **categorías jerárquicas**:

```json
{
  "countries": {
    "CountryName": {
      "Introduction": {...},
      "Geography": {...},
      "People and Society": {...},
      "Economy": {...},
      "Government": {...},
      "Military and Security": {...},
      "Communications": {...},
      "Transportation": {...},
      "Transnational Issues": {...}
    }
  }
}
```

### 2.2 Key Metrics for MASSIVE

**People and Society** (Crítico para inicialización de agentes):
- `Population`: Tamaño de población
- `Population growth rate`: Tasa de crecimiento
- `Urbanization`: % población urbana
- `Ethnic groups`: Distribución étnica
- `Religions`: Distribución religiosa
- `Gini Index`: Desigualdad de ingresos

**Economy** (Para dinámicas económicas):
- `GDP`: Producto interno bruto
- `GDP - per capita`: PIB per cápita
- `GDP - real growth rate`: Tasa de crecimiento
- `Inflation rate`: Tasa de inflación
- `Unemployment rate`: Tasa de desempleo
- `Public debt`: Deuda pública (% del PIB)

**Government** (Para estructura política):
- `Government type`: Tipo de gobierno
- `Administrative divisions`: Divisiones administrativas

**Military and Security** (Para conflictos y seguridad):
- `Military expenditures`: Gasto militar
- `Military and security force personnel`: Personal militar

**Communications** (Para difusión de información):
- `Internet users`: Usuarios de internet
- `Broadband subscriptions`: Suscripciones de banda ancha

---

## 3. Integration Points in MASSIVE

### 3.1 Agent Initialization (CRITICAL)

**Location**: `massive/core/agent_initialization.py`

**When**: Al crear la población de agentes al inicio de una simulación

**What**: Reemplaza parámetros abstractos con datos reales

```python
# BEFORE: Parámetros abstractos
agents = initialize_agents(
    population=10000,
    urbanization=0.8,
    gini_index=0.4
)

# AFTER: Datos reales del World Factbook
context = FactbookContext("Germany")
agents = initialize_agents(
    population=context.population,
    urbanization=context.urbanization_rate,
    gini_index=context.gini_index,
    ethnic_groups=context.ethnic_distribution,
    religious_groups=context.religious_distribution
)
```

**Impact**: Los agentes representan una población real con características demográficas verificadas.

---

### 3.2 Social Pressure Calculation (HIGH PRIORITY)

**Location**: `massive/core/utility_logic.py` → `calculate_social_pressure()`

**When**: Durante cada paso de simulación al calcular influencia entre agentes

**What**: Usa datos étnicos/religiosos para modelar afinidad grupal

```python
# BEFORE: Influencia uniforme entre todos los agentes
def calculate_social_pressure(agents, network):
    # Todos los agentes se influyen igual
    pressure = np.sum(opinion_diffs * adjacency_matrix, axis=1)

# AFTER: Influencia modulada por similitud grupal
def calculate_social_pressure(agents, network, ethnic_groups, religious_groups):
    # Agentes del mismo grupo étnico/religioso se influyen más
    similarity_matrix = compute_group_similarity(
        agents, ethnic_groups, religious_groups
    )
    weighted_adjacency = adjacency_matrix * similarity_matrix
    pressure = np.sum(opinion_diffs * weighted_adjacency, axis=1)
```

**Impact**: La presión social refleja dinámicas reales de afinidad grupal.

---

### 3.3 Energy Engine (MEDIUM PRIORITY)

**Location**: `massive/core/energy_engine_pure.py` → `calculate_energy()`

**When**: Al calcular la energía del sistema (termodinámica social)

**What**: Usa Gini index para calibrar el potencial de interacción

```python
# BEFORE: Potencial de interacción uniforme
def calculate_energy(state, momentum, interaction_matrix):
    potential = -0.5 * state.T @ interaction_matrix @ state

# AFTER: Potencial modulado por desigualdad (Gini)
def calculate_energy(state, momentum, interaction_matrix, gini_index):
    # Mayor desigualdad → mayor fricción social → mayor energía potencial
    inequality_factor = 1 + (gini_index / 100)
    potential = -0.5 * inequality_factor * (state.T @ interaction_matrix @ state)
```

**Impact**: Sociedades desiguales tienen mayor energía (tensión) social.

---

### 3.4 Intervention Optimizer (HIGH PRIORITY)

**Location**: `massive/intervention/optimizer.py` → `evaluate_strategies()`

**When**: Al evaluar estrategias de intervención

**What**: Usa datos económicos para calcular costo/beneficio realista

```python
# BEFORE: Costo abstracto
def evaluate_strategies(strategies, agents, budget):
    cost = calculate_abstract_cost(strategy)

# AFTER: Costo basado en economía real del país
def evaluate_strategies(strategies, agents, budget, gdp_per_capita, inflation_rate):
    # Costo ajustado por poder adquisitivo real
    purchasing_power = gdp_per_capita / (1 + inflation_rate/100)
    cost = calculate_real_cost(strategy, purchasing_power)
```

**Impact**: Las intervenciones consideran el contexto económico real.

---

### 3.5 Social Architect Analytics (MEDIUM PRIORITY)

**Location**: `massive/analysis/social_architect_pure.py` → `calculate_polarization()`

**When**: Al calcular métricas de polarización y consenso

**What**: Compara resultados con polarización real del país

```python
# BEFORE: Solo métricas internas
def calculate_polarization(opinions):
    return np.mean(np.abs(opinions[:, None] - opinions))

# AFTER: Métricas + validación contra datos reales
def calculate_polarization(opinions, country_context=None):
    simulated_polarization = np.mean(np.abs(opinions[:, None] - opinions))
    
    if country_context:
        actual_polarization = country_context.actual_polarization_index
        accuracy = 1 - abs(simulated_polarization - actual_polarization)
        return {
            "simulated": simulated_polarization,
            "actual": actual_polarization,
            "accuracy": accuracy
        }
    
    return simulated_polarization
```

**Impact**: Validación empírica de las métricas de polarización.

---

## 4. Workflow Integration

### 4.1 Standard Simulation Workflow (Without Factbook)

```
1. Define parameters abstractos
2. Inicializar agentes con parámetros
3. Ejecutar simulación
4. Analizar resultados
5. Visualizar métricas
```

### 4.2 Enhanced Workflow (With Factbook)

```
1. Seleccionar país del World Factbook
2. Cargar contexto del país
3. Mapear datos Factbook → parámetros MASSIVE
4. Inicializar agentes con datos reales
5. Ejecutar simulación con contexto
6. Validar resultados contra datos reales
7. Comparar con otros países (opcional)
8. Generar reporte con accuracy metrics
```

### 4.3 Step-by-Step Workflow

#### Step 1: Load Factbook Context

```python
from massive.context.factbook_context import FactbookContext

# Cargar datos de un país específico
context = FactbookContext("Germany")

# O cargar múltiples países para comparación
contexts = FactbookContext.multiple(["Germany", "France", "USA"])
```

#### Step 2: Map to MASSIVE Parameters

```python
# Mapeo automático de datos Factbook → parámetros MASSIVE
massive_params = context.to_massive_parameters()

# Resultado:
# {
#     "population": 83294633,
#     "urbanization_rate": 0.775,
#     "gini_index": 31.9,
#     "ethnic_groups": {"german": 0.87, "turkish": 0.037, "other": 0.093},
#     "religious_groups": {"protestant": 0.26, "catholic": 0.25, ...},
#     "gdp_per_capita": 53200,
#     "inflation_rate": 6.0,
#     "internet_penetration": 0.936,
#     ...
# }
```

#### Step 3: Initialize Agents with Real Data

```python
from massive.core import initialize_agents

# Inicializar agentes con datos reales de Alemania
agents = initialize_agents(
    population=context.population,
    urbanization=context.urbanization_rate,
    ethnic_groups=context.ethnic_distribution,
    religious_groups=context.religious_distribution,
    economic_status=context.gdp_per_capita,
    inequality=context.gini_index
)
```

#### Step 4: Run Simulation with Context

```python
from massive.core import simulate

# Ejecutar simulación con contexto del país
result = simulate(
    parameters=massive_params,
    agents=agents,
    context=context,  # Contexto del World Factbook
    intervention="climate_policy",
    years=10
)
```

#### Step 5: Validate Against Real Data

```python
from massive.validation import FactbookValidator

validator = FactbookValidator()
validation = validator.validate(result, context)

# Resultado:
# {
#     "polarization_accuracy": 0.87,
#     "consensus_accuracy": 0.92,
#     "economic_impact_accuracy": 0.78,
#     "overall_accuracy": 0.86
# }
```

#### Step 6: Cross-Country Comparison (Optional)

```python
from massive.analysis import ComparativeAnalyzer

analyzer = ComparativeAnalyzer()
comparison = analyzer.compare_countries(
    countries=["Germany", "France", "USA", "China"],
    intervention="climate_policy",
    years=10
)

# Resultado:
# {
#     "Germany": {"acceptance_rate": 0.72, "accuracy": 0.86},
#     "France": {"acceptance_rate": 0.68, "accuracy": 0.84},
#     "USA": {"acceptance_rate": 0.54, "accuracy": 0.79},
#     "China": {"acceptance_rate": 0.81, "accuracy": 0.88}
# }
```

---

## 5. Data Mapping Specification

### 5.1 Factbook → MASSIVE Parameter Mapping

| Factbook Field | MASSIVE Parameter | Type | Priority |
|----------------|-------------------|------|----------|
| `Population.value` | `population` | int | CRITICAL |
| `Urbanization.urban_population` | `urbanization_rate` | float (0-1) | CRITICAL |
| `Gini Index.value` | `gini_index` | float (0-100) | CRITICAL |
| `Ethnic groups` | `ethnic_groups` | dict | HIGH |
| `Religions` | `religious_groups` | dict | HIGH |
| `GDP - per capita.value` | `gdp_per_capita` | float | HIGH |
| `Inflation rate.value` | `inflation_rate` | float | MEDIUM |
| `Unemployment rate.value` | `unemployment_rate` | float | MEDIUM |
| `Internet users.percent_of_population` | `internet_penetration` | float (0-1) | MEDIUM |
| `Military expenditures.percent_gdp` | `military_spending_pct` | float | LOW |
| `Public debt.value` | `public_debt_pct` | float | LOW |

### 5.2 Derived Metrics

Algunas métricas se calculan a partir de datos del Factbook:

```python
# Desigualdad económica normalizada (0-1)
inequality_index = gini_index / 100

# Poder adquisitivo ajustado por inflación
purchasing_power = gdp_per_capita / (1 + inflation_rate/100)

# Conectividad social (proxy para difusión de información)
social_connectivity = internet_penetration * (1 + broadband_rate)

# Tensión social (combinación de desigualdad + desempleo)
social_tension = (gini_index/100) * 0.6 + (unemployment_rate/100) * 0.4

# Apertura económica (trade/GDP ratio)
trade_openness = (exports + imports) / gdp
```

---

## 6. Implementation Guide

### 6.1 File Structure

```
massive/
├── context/
│   ├── __init__.py
│   ├── factbook_context.py          # Cargador y mapeador de datos
│   └── context_mapper.py            # Mapeo Factbook → MASSIVE
├── core/
│   ├── agent_initialization.py      # Modificar para aceptar contexto
│   ├── utility_logic.py             # Modificar para usar grupos étnicos
│   └── energy_engine_pure.py        # Modificar para usar Gini index
├── intervention/
│   └── optimizer.py                 # Modificar para usar economía real
├── analysis/
│   └── social_architect_pure.py     # Modificar para validación
├── validation/
│   ├── __init__.py
│   ├── factbook_validator.py        # Validador contra datos reales
│   └── comparative_analyzer.py      # Análisis cross-country
└── data/
    └── factbook/
        ├── factbook.json            # Dataset completo
        └── factbook_sample.json     # Dataset de ejemplo
```

### 6.2 Core Module: FactbookContext

```python
# massive/context/factbook_context.py

import json
from pathlib import Path
from typing import Dict, List, Optional

class FactbookContext:
    """
    Carga y proporciona acceso a datos del World Factbook.
    
    Usage:
        context = FactbookContext("Germany")
        print(context.population)  # 83294633
        print(context.gini_index)  # 31.9
    """
    
    def __init__(self, country_name: str, data_path: str = None):
        """
        Args:
            country_name: Nombre del país (ej: "Germany", "United States")
            data_path: Ruta al archivo factbook.json (default: data/factbook/factbook.json)
        """
        self.country_name = country_name
        self.data_path = Path(data_path or self._default_path())
        self.data = self._load_country_data()
    
    def _default_path(self) -> Path:
        """Ruta por defecto al dataset del Factbook"""
        return Path(__file__).parent.parent / "data" / "factbook" / "factbook.json"
    
    def _load_country_data(self) -> Dict:
        """Carga datos del país desde el JSON"""
        with open(self.data_path, 'r', encoding='utf-8') as f:
            factbook = json.load(f)
        
        if self.country_name not in factbook['countries']:
            raise ValueError(f"Country '{self.country_name}' not found in Factbook")
        
        return factbook['countries'][self.country_name]
    
    # ========== People and Society ==========
    
    @property
    def population(self) -> int:
        """Población total"""
        return self.data['People and Society']['Population']['value']
    
    @property
    def population_growth_rate(self) -> float:
        """Tasa de crecimiento poblacional (%)"""
        return self.data['People and Society']['Population growth rate']['value']
    
    @property
    def urbanization_rate(self) -> float:
        """% de población urbana (0-1)"""
        return self.data['People and Society']['Urbanization']['urban population'] / 100
    
    @property
    def ethnic_distribution(self) -> Dict[str, float]:
        """Distribución étnica (proporciones 0-1)"""
        groups = self.data['People and Society']['Ethnic groups']
        return {k: v/100 for k, v in groups.items() if isinstance(v, (int, float))}
    
    @property
    def religious_distribution(self) -> Dict[str, float]:
        """Distribución religiosa (proporciones 0-1)"""
        religions = self.data['People and Society']['Religions']
        return {k: v/100 for k, v in religions.items() if isinstance(v, (int, float))}
    
    @property
    def gini_index(self) -> float:
        """Índice de Gini (0-100)"""
        return self.data['People and Society']['Gini Index']['value']
    
    # ========== Economy ==========
    
    @property
    def gdp(self) -> float:
        """PIB total (USD)"""
        return self.data['Economy']['GDP']['value']
    
    @property
    def gdp_per_capita(self) -> float:
        """PIB per cápita (USD)"""
        return self.data['Economy']['GDP - per capita']['value']
    
    @property
    def gdp_growth_rate(self) -> float:
        """Tasa de crecimiento del PIB (%)"""
        return self.data['Economy']['GDP - real growth rate']['value']
    
    @property
    def inflation_rate(self) -> float:
        """Tasa de inflación (%)"""
        return self.data['Economy']['Inflation rate']['value']
    
    @property
    def unemployment_rate(self) -> float:
        """Tasa de desempleo (%)"""
        return self.data['Economy']['Unemployment rate']['value']
    
    @property
    def public_debt_pct(self) -> float:
        """Deuda pública (% del PIB)"""
        return self.data['Economy']['Public debt']['value']
    
    # ========== Communications ==========
    
    @property
    def internet_penetration(self) -> float:
        """% de usuarios de internet (0-1)"""
        return self.data['Communications']['Internet users']['percent_of_population'] / 100
    
    # ========== Military ==========
    
    @property
    def military_spending_pct(self) -> float:
        """Gasto militar (% del PIB)"""
        return self.data['Military and Security']['Military expenditures']['percent_gdp']
    
    # ========== Derived Metrics ==========
    
    @property
    def inequality_index(self) -> float:
        """Índice de desigualdad normalizado (0-1)"""
        return self.gini_index / 100
    
    @property
    def purchasing_power(self) -> float:
        """Poder adquisitivo ajustado por inflación"""
        return self.gdp_per_capita / (1 + self.inflation_rate/100)
    
    @property
    def social_tension(self) -> float:
        """Tensión social (combinación de desigualdad + desempleo)"""
        return (self.gini_index/100) * 0.6 + (self.unemployment_rate/100) * 0.4
    
    # ========== Export Methods ==========
    
    def to_massive_parameters(self) -> Dict:
        """
        Exporta todos los datos relevantes como parámetros de MASSIVE.
        
        Returns:
            Dict con parámetros listos para MASSIVE
        """
        return {
            # People and Society
            "population": self.population,
            "urbanization_rate": self.urbanization_rate,
            "gini_index": self.gini_index,
            "ethnic_groups": self.ethnic_distribution,
            "religious_groups": self.religious_distribution,
            
            # Economy
            "gdp_per_capita": self.gdp_per_capita,
            "inflation_rate": self.inflation_rate,
            "unemployment_rate": self.unemployment_rate,
            "public_debt_pct": self.public_debt_pct,
            
            # Communications
            "internet_penetration": self.internet_penetration,
            
            # Military
            "military_spending_pct": self.military_spending_pct,
            
            # Derived
            "inequality_index": self.inequality_index,
            "purchasing_power": self.purchasing_power,
            "social_tension": self.social_tension,
        }
    
    @classmethod
    def multiple(cls, country_names: List[str], data_path: str = None) -> Dict[str, 'FactbookContext']:
        """
        Carga múltiples países para análisis comparativo.
        
        Args:
            country_names: Lista de nombres de países
            data_path: Ruta al archivo factbook.json
        
        Returns:
            Dict {country_name: FactbookContext}
        """
        return {name: cls(name, data_path) for name in country_names}
```

### 6.3 Example Usage Script

```python
# examples/factbook_simulation.py

"""
Ejemplo completo de simulación con datos del World Factbook.

Este script demuestra cómo:
1. Cargar datos de un país del World Factbook
2. Inicializar agentes con datos reales
3. Ejecutar una simulación
4. Validar resultados contra datos reales
5. Comparar con otros países
"""

from massive.context.factbook_context import FactbookContext
from massive.core import initialize_agents, simulate
from massive.validation import FactbookValidator
from massive.analysis import ComparativeAnalyzer

def main():
    print("=" * 60)
    print("MASSIVE Simulation with World Factbook Data")
    print("=" * 60)
    
    # ========== Step 1: Load Country Context ==========
    print("\n[1/5] Loading country context...")
    context = FactbookContext("Germany")
    print(f"✓ Loaded data for: {context.country_name}")
    print(f"  Population: {context.population:,}")
    print(f"  GDP per capita: ${context.gdp_per_capita:,}")
    print(f"  Gini index: {context.gini_index}")
    
    # ========== Step 2: Initialize Agents ==========
    print("\n[2/5] Initializing agents with real data...")
    agents = initialize_agents(
        population=context.population,
        urbanization=context.urbanization_rate,
        ethnic_groups=context.ethnic_distribution,
        religious_groups=context.religious_distribution,
        economic_status=context.gdp_per_capita,
        inequality=context.gini_index
    )
    print(f"✓ Initialized {len(agents):,} agents")
    
    # ========== Step 3: Run Simulation ==========
    print("\n[3/5] Running simulation...")
    massive_params = context.to_massive_parameters()
    result = simulate(
        parameters=massive_params,
        agents=agents,
        context=context,
        intervention="climate_policy",
        years=10
    )
    print(f"✓ Simulation complete")
    print(f"  Final polarization: {result.polarization_index:.3f}")
    print(f"  Consensus rate: {result.consensus_rate:.1%}")
    
    # ========== Step 4: Validate Results ==========
    print("\n[4/5] Validating against real data...")
    validator = FactbookValidator()
    validation = validator.validate(result, context)
    print(f"✓ Validation complete")
    print(f"  Overall accuracy: {validation['overall_accuracy']:.1%}")
    
    # ========== Step 5: Cross-Country Comparison ==========
    print("\n[5/5] Comparing with other countries...")
    analyzer = ComparativeAnalyzer()
    comparison = analyzer.compare_countries(
        countries=["Germany", "France", "USA", "China"],
        intervention="climate_policy",
        years=10
    )
    print(f"✓ Comparison complete")
    for country, metrics in comparison.items():
        print(f"  {country}: acceptance={metrics['acceptance_rate']:.1%}, accuracy={metrics['accuracy']:.1%}")
    
    print("\n" + "=" * 60)
    print("Simulation workflow complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
```

---

## 7. Validation Strategy

### 7.1 Validation Metrics

Para validar que las simulaciones con datos del Factbook son precisas:

**1. Polarization Accuracy**
```python
simulated_polarization = result.polarization_index
actual_polarization = context.actual_polarization_index  # De fuentes externas
accuracy = 1 - abs(simulated_polarization - actual_polarization)
```

**2. Consensus Accuracy**
```python
simulated_consensus = result.consensus_rate
actual_consensus = context.actual_consensus_rate  # De encuestas reales
accuracy = 1 - abs(simulated_consensus - actual_consensus)
```

**3. Economic Impact Accuracy**
```python
simulated_impact = result.economic_impact
actual_impact = context.actual_economic_impact  # De datos del Banco Mundial
accuracy = 1 - abs(simulated_impact - actual_impact) / actual_impact
```

### 7.2 Expected Accuracy Benchmarks

| Metric | Target Accuracy | Acceptable Range |
|--------|----------------|------------------|
| Polarization | 85% | 75-95% |
| Consensus | 80% | 70-90% |
| Economic Impact | 75% | 65-85% |
| Overall | 80% | 70-90% |

---

## 8. Data Sources

### 8.1 Primary Source

**CIA World Factbook**
- URL: https://www.cia.gov/the-world-factbook/
- Format: JSON por país
- License: Public Domain
- Update Frequency: Weekly

### 8.2 Alternative Sources (More Complete)

**1. GitHub: wmccaffrey/cia_world_factbook**
- JSON consolidado de todos los países
- Fácil de integrar
- https://github.com/wmccaffrey/cia_world_factbook

**2. GitHub: OpenIntelLabs/World-Factbook**
- Datos en CSV, JSON, SQLite
- Histórico de versiones
- https://github.com/OpenIntelLabs/World-Factbook

**3. Kaggle: CIA World Factbook Dataset**
- Formato CSV limpio
- Ejemplos de análisis
- https://www.kaggle.com/datasets/cia-world-factbook

### 8.3 Supplementary Data Sources

Para validación, combinar con:
- **World Bank Open Data**: Indicadores económicos
- **UN Data**: Estadísticas demográficas
- **OECD Data**: Datos de países desarrollados
- **World Values Survey**: Valores culturales y políticos

---

## 9. Implementation Checklist

### Phase 1: Data Infrastructure (2-3 days)

- [ ] Descargar dataset completo del World Factbook
- [ ] Crear `massive/context/factbook_context.py`
- [ ] Implementar carga y cacheo de datos
- [ ] Crear dataset de ejemplo (`factbook_sample.json`)
- [ ] Tests unitarios para FactbookContext

### Phase 2: Integration Points (3-4 days)

- [ ] Modificar `agent_initialization.py` para aceptar contexto
- [ ] Modificar `utility_logic.py` para usar grupos étnicos/religiosos
- [ ] Modificar `energy_engine_pure.py` para usar Gini index
- [ ] Modificar `optimizer.py` para usar economía real
- [ ] Tests de integración

### Phase 3: Validation Framework (2-3 days)

- [ ] Crear `validation/factbook_validator.py`
- [ ] Implementar métricas de accuracy
- [ ] Crear `analysis/comparative_analyzer.py`
- [ ] Tests de validación

### Phase 4: Documentation & Examples (2 days)

- [ ] Escribir tutorial: "Simulando con datos reales"
- [ ] Crear 3-5 ejemplos de uso
- [ ] Actualizar README con sección de Factbook
- [ ] Documentar API de FactbookContext

### Phase 5: Testing & Refinement (1-2 days)

- [ ] Ejecutar simulaciones para 10-20 países
- [ ] Calcular métricas de accuracy
- [ ] Ajustar parámetros si es necesario
- [ ] Documentar resultados

**Total Estimated Time: 10-14 days**

---

## 10. Expected Outcomes

### 10.1 Scientific Benefits

1. **Empirical Grounding**: Simulaciones basadas en datos reales
2. **Validation**: Capacidad de validar resultados contra el mundo real
3. **Reproducibility**: Otros investigadores pueden replicar simulaciones
4. **Cross-Country Analysis**: Comparación sistemática entre países

### 10.2 Practical Benefits

1. **Credibility**: Mayor credibilidad académica y política
2. **Accuracy**: Mejores predicciones al usar datos reales
3. **Insights**: Descubrimiento de patrones cross-country
4. **Impact**: Mayor impacto en policy-making

### 10.3 Competitive Advantages

1. **Differentiation**: Único framework de ABM con integración de World Factbook
2. **Validation**: Validación empírica directa
3. **Scalability**: Fácil extensión a más países y métricas
4. **Open Science**: Datos públicos y reproducibles

---

## 11. Risks and Mitigations

### Risk 1: Data Quality

**Risk**: Datos del Factbook pueden tener sesgos o errores

**Mitigation**:
- Cross-validate con otras fuentes (World Bank, UN)
- Documentar limitaciones de datos
- Permitir override manual de parámetros

### Risk 2: Temporal Lag

**Risk**: Datos del Factbook pueden estar desactualizados

**Mitigation**:
- Usar datos más recientes disponibles
- Implementar proyecciones temporales
- Documentar año de referencia de cada dato

### Risk 3: Granularity

**Risk**: Datos a nivel país, no regional

**Mitigation**:
- Para países grandes, permitir subdivisión manual
- Combinar con datos regionales cuando estén disponibles
- Documentar limitación de granularidad

### Risk 4: Political Bias

**Risk**: Perspectiva USA en análisis políticos

**Mitigation**:
- Cross-validate con fuentes independientes
- Documentar perspectiva de la fuente
- Permitir fuentes alternativas

---

## 12. Conclusion

La integración del World Factbook en MASSIVE representa un **salto cualitativo** en la capacidad del framework para:

1. **Inicializar simulaciones** con datos reales
2. **Validar resultados** contra el mundo real
3. **Comparar países** sistemáticamente
4. **Generar insights** basados en evidencia empírica

Esta integración posiciona a MASSIVE como el **framework de ABM más empíricamente fundamentado** disponible, con ventajas competitivas significativas en credibilidad académica y utilidad práctica.

**Recomendación**: Proceder con la implementación según el plan detallado en este documento.

---

## Appendix A: Sample Data Structure

Ver archivo: `data/factbook/factbook_sample.json`

Contiene datos de ejemplo para:
- United States
- China
- Germany

## Appendix B: API Reference

Ver documentación inline en: `massive/context/factbook_context.py`

## Appendix C: Example Scripts

Ver: `examples/factbook_simulation.py`

---

**Document Version**: 1.0  
**Date**: 2026-06-26  
**Status**: Implementation Plan Ready
