# Plan orgánico para extensiones matemáticas, algorítmicas y físicas de MASSIVE

Este documento convierte la propuesta de extensiones en un plan de integración incremental para MASSIVE. El objetivo no es insertar clases aisladas, sino crear una capa científica coherente que pueda activarse gradualmente sin romper el motor actual, la UI, el Arquitecto Social ni los tests existentes.

## 1. Diagnóstico del estado actual

MASSIVE ya contiene una base funcional y útil:

- Un motor de energía social con dinámica de Langevin en una dimensión de opinión.
- Un motor multicapa con estado vectorial 5D y actualización estocástica Euler-Maruyama.
- Un selector CfC opcional que nunca bloquea el comportamiento LLM/heurístico.
- Validación, benchmarks, tests y documentación inicial.

La brecha principal es que el núcleo numérico está muy acoplado a un único esquema explícito. Eso limita estabilidad, análisis formal, transferibilidad a dominios rígidos y asimilación de datos reales. La integración debe preservar el comportamiento actual como `baseline` y agregar capacidades nuevas mediante módulos opt-in.

## 2. Principios de diseño

1. **Compatibilidad hacia atrás:** ninguna simulación existente debe cambiar si el usuario no selecciona una extensión nueva.
2. **Capas pequeñas y testeables:** cada capacidad nueva debe exponer una API mínima y tener tests unitarios antes de conectarse a la UI.
3. **Separación entre dinámica y diagnóstico:** los solvers actualizan estados; los analizadores miden estabilidad, bifurcación, caos o transición de fase sin mutar el sistema.
4. **Degradación elegante:** dependencias pesadas como PyTorch avanzado, statsmodels o scipy sparse deben ser opcionales cuando sea viable.
5. **Escalabilidad explícita:** todo algoritmo O(N³) debe tener alternativa aproximada para redes grandes.
6. **Trazabilidad científica:** cada extensión debe declarar supuestos, límites numéricos y métricas de validación.

## 3. Arquitectura objetivo

La integración propuesta crea paquetes científicos alrededor del núcleo existente:

```text
massive_core/
  numerics/
    solvers.py              # Euler-Maruyama, Milstein, RK4, implícitos, adaptativo
    stability.py            # Jacobianos, radio espectral, Lyapunov, condición
    diagnostics.py          # errores, tolerancias, eventos de inestabilidad
  dynamical_systems/
    bifurcation.py          # diagramas, puntos críticos, tipping probability
  physics/
    statistical_mechanics.py
    perturbation_theory.py
    hydrodynamics.py
  data_assimilation/
    kalman.py               # EnKF y operadores de observación
  network_inference/
    reconstruct.py          # correlación, TE, Granger, MI
  multiscale/
    hierarchical_time.py    # micro/meso/macro dynamics
  neural_physics/
    pinns.py                # PINNs opcionales con PyTorch
  metalearning/
    regime_selector.py      # selector meta-regimen sobre CfC/LLM/heurístico
```

El punto de conexión con el código actual debe ser un contrato común:

```python
class DynamicsStepper:
    def step(self, state, dt, drift, diffusion=None, context=None):
        ...
```

Así, `energy_engine.py` y `multilayer_engine.py` pueden mantener Euler-Maruyama por defecto, pero delegar en un `DynamicsStepper` cuando se configure otro solver.

## 4. Priorización técnica

| Fase | Extensión | Prioridad | Motivo | Dependencias |
| --- | --- | --- | --- | --- |
| 0 | Contratos internos y feature flags | Crítica | Evita acoplar clases nuevas al motor actual | Ninguna |
| 1 | Solvers adaptativos | Alta | Mayor estabilidad y precisión con impacto directo | NumPy/SciPy |
| 1 | StabilityAnalyzer | Alta | Permite decidir cuándo cambiar solver o reducir `dt` | NumPy/SciPy |
| 1 | EnKF | Alta | Conecta simulación con observaciones reales | NumPy |
| 2 | BifurcationAnalyzer | Alta | Formaliza transiciones de fase y tipping points | StabilityAnalyzer |
| 2 | StatisticalMechanicsEngine | Media | Entropía, energía libre y susceptibilidad para métricas globales | NumPy |
| 2 | MultiTimescaleEngine | Media | Mejora realismo temporal sin requerir datos externos | Solvers |
| 3 | NetworkReconstructor | Media | Aumenta transferibilidad cuando la red real no se conoce | SciPy/statsmodels opcional |
| 3 | MetaRegimeSelector | Media | Evoluciona CfC hacia selección con aprendizaje de rendimiento | PyTorch opcional |
| 4 | PINNs | Media | Útil para datos escasos, pero requiere diseño de pérdidas | PyTorch |
| 4 | PerturbationTheorySolver | Baja | Potente pero menos urgente para el producto base | Solvers/Stability |
| 4 | AgentHydrodynamics | Baja | Aproximación continua útil para N grande, más experimental | SciPy |

## 5. Workflow de implementación

### Fase 0 — Preparación arquitectónica

**Objetivo:** preparar el proyecto para extensiones sin alterar resultados actuales.

1. Crear paquetes vacíos con `__init__.py` bajo `massive_core/`.
2. Definir `DynamicsStepper`, `DriftFunction`, `DiffusionFunction` y `NumericalDiagnostics`.
3. Agregar configuración opt-in:
   - `solver: "euler_maruyama"` por defecto.
   - `enable_stability_diagnostics: false` por defecto.
   - `enable_data_assimilation: false` por defecto.
4. Añadir tests de compatibilidad que comparen el motor actual contra el wrapper Euler-Maruyama.

**Criterio de salida:** todos los tests actuales pasan y el solver por defecto reproduce el comportamiento existente dentro de tolerancia estadística.

### Fase 1 — Núcleo numérico y observacional

**Objetivo:** entregar valor inmediato sin tocar la lógica sociológica de reglas.

1. Implementar `massive_core/numerics/solvers.py`:
   - `EulerMaruyamaSolver` como baseline.
   - `MilsteinSolver` para SDEs con difusión derivable.
   - `RK4Solver` para drift determinista.
   - `AdaptiveSolver` con heurística de stiffness y control de paso.
2. Implementar `massive_core/numerics/stability.py`:
   - estimación de Jacobiano por diferencias finitas;
   - radio espectral por power iteration;
   - clasificación estable/marginal/inestable;
   - estimador de Lyapunov máximo basado en divergencia de trayectorias.
3. Implementar `massive_core/data_assimilation/kalman.py`:
   - EnKF con covarianza de estado correcta `(state_dim, state_dim)`;
   - operador de observación `H` configurable;
   - inflación de ensemble y clipping opcional al rango de estado.
4. Conectar solo mediante APIs programáticas, no UI todavía.

**Criterio de salida:** tests unitarios para precisión relativa, estabilidad de shapes y EnKF con observación sintética.

### Fase 2 — Diagnóstico de transiciones y física estadística

**Objetivo:** convertir alertas cualitativas en métricas científicas explícitas.

1. Implementar `BifurcationAnalyzer` con barrido de parámetros y clasificación por eigenvalores.
2. Implementar tipping probability con advertencia explícita para ruido fuerte.
3. Implementar entropía, función de partición estable con log-sum-exp, energía libre y susceptibilidad.
4. Agregar un objeto `ScientificReport` serializable para que UI/API puedan mostrar:
   - estabilidad lineal;
   - radio espectral;
   - Lyapunov máximo;
   - entropía;
   - susceptibilidad;
   - puntos críticos detectados.

**Criterio de salida:** benchmarks pequeños con sistemas conocidos: punto fijo estable, oscilador simple y doble pozo.

### Fase 3 — Transferibilidad: red desconocida, multiescala y meta-régimen

**Objetivo:** permitir usar MASSIVE en escenarios con datos parciales, múltiples escalas temporales y selección de régimen más autónoma.

1. Implementar `MultiTimescaleEngine` como capa de drift adicional, no como sustituto del motor base.
2. Implementar `NetworkReconstructor` en niveles:
   - correlación como baseline obligatorio;
   - mutual information y transfer entropy discretizada;
   - Granger opcional si la dependencia está disponible.
3. Extender CfC con `MetaRegimeSelector` de forma compatible:
   - CfC actual permanece como fast path;
   - meta-selector agrega historial de performance y recompensas;
   - fallback a LLM/heurística se mantiene.
4. Agregar datasets sintéticos para validar reconstrucción y selección de régimen.

**Criterio de salida:** reconstrucción supera baseline aleatorio en datos sintéticos y no degrada la latencia cuando está desactivada.

### Fase 4 — Extensiones avanzadas: PINNs, perturbación e hidrodinámica

**Objetivo:** añadir capacidades científicas avanzadas sin comprometer mantenimiento.

1. Implementar PINNs como paquete opcional con tests marcados `pytest.mark.optional_torch`.
2. Implementar teoría de perturbaciones solo para operadores bien condicionados y con regularización configurable.
3. Implementar hidrodinámica de agentes como aproximación para N grande con documentación clara de validez.
4. Publicar notebooks o ejemplos mínimos en documentación antes de exponerlos en UI.

**Criterio de salida:** ejemplos reproducibles y tests que se saltan limpiamente si faltan dependencias opcionales.

## 6. Workflow de ramas, commits y revisión

Para mantener cambios elegantes y auditables:

1. **Una rama por fase:** `feature/scientific-core-f0`, `feature/scientific-core-f1`, etc.
2. **Un PR por capacidad vertical:** por ejemplo, solver + tests + docs, no todos los módulos a la vez.
3. **Orden de commit recomendado:**
   - contratos y estructura;
   - implementación mínima;
   - tests;
   - documentación;
   - integración opcional con API/UI.
4. **Regla de no regresión:** antes de fusionar, ejecutar como mínimo:
   - `python -m pytest tests/test_massive_engine.py tests/test_multilayer.py tests/test_energy_core.py`;
   - `python -m pytest tests` en PRs de fase completa;
   - benchmark pequeño si se toca integración numérica.
5. **Revisión científica:** cada PR debe incluir supuestos matemáticos, complejidad temporal y condiciones de fallo.

## 7. Decisiones de implementación clave

### 7.1 Stiffness y selección adaptativa

La heurística inicial debe usar métricas baratas:

- `spectral_radius(J) * dt` para estabilidad explícita;
- norma relativa del drift para detectar explosión;
- reducción de `dt` si el estado propuesto sale masivamente del dominio válido;
- método implícito o paso menor cuando `spectral_radius(J) * dt >= 1`.

### 7.2 EnKF con covarianza correcta

El ensemble debe organizarse como `(n_ensemble, state_dim)`. La covarianza de estado debe calcularse como:

```python
X = ensemble - ensemble.mean(axis=0)
P = X.T @ X / (n_ensemble - 1)
```

Esto evita el error común de producir una covarianza `(n_ensemble, n_ensemble)` que no puede combinarse correctamente con `H`.

### 7.3 Estadística numéricamente estable

La energía libre y partición deben usar log-sum-exp:

```python
logZ = logsumexp(-beta * energy)
F = -temperature * logZ
```

Esto evita underflow/overflow en temperaturas bajas o paisajes energéticos profundos.

### 7.4 Network reconstruction como inferencia, no verdad

Todas las redes reconstruidas deben marcarse como estimadas y devolver intervalos, scores o pesos. No deben reemplazar silenciosamente la red configurada por el usuario.

## 8. Riesgos y mitigaciones

| Riesgo | Mitigación |
| --- | --- |
| Cambiar el comportamiento histórico del motor | Mantener Euler-Maruyama como default y tests de compatibilidad |
| Coste O(N³) en eigenvalores | Power iteration, Lanczos o muestreo de subredes |
| Dependencias pesadas | Extras opcionales y tests con skip limpio |
| API demasiado compleja | Contrato único `DynamicsStepper` y objetos reporte serializables |
| Métricas mal interpretadas como certezas | Documentar supuestos, rangos de validez e incertidumbre |
| Meta-learning inestable | Modo sombra antes de activar decisiones automáticas |

## 9. Definition of Done por extensión

Una extensión se considera lista cuando cumple:

- API pública documentada.
- Tests unitarios de shapes, límites y casos conocidos.
- Ejemplo mínimo de uso.
- Complejidad temporal documentada.
- Integración opt-in con configuración.
- No rompe tests existentes.
- Métricas serializables para UI/API si aplica.

## 10. Orden recomendado de ejecución

1. `DynamicsStepper` + wrapper Euler-Maruyama.
2. `StabilityAnalyzer` mínimo.
3. `AdaptiveSolver` con Milstein/RK4 y control de paso.
4. `EnsembleKalmanFilter`.
5. `BifurcationAnalyzer` + `ScientificReport`.
6. `StatisticalMechanicsEngine`.
7. `MultiTimescaleEngine`.
8. `NetworkReconstructor`.
9. `MetaRegimeSelector` sobre CfC.
10. PINNs, perturbación e hidrodinámica como módulos avanzados.

Este orden maximiza impacto temprano, minimiza riesgo de regresión y deja las capacidades más experimentales para cuando el contrato científico ya esté estabilizado.
