# Plan Python Wrapper, Rust Core para MASSIVE

Este documento registra la evaluación de los motores pesados de MASSIVE y la ruta
segura para mover cómputo crítico a Rust con PyO3/Maturin sin romper la API
Python existente.

## Criterios de selección

Una función es buena candidata a Rust cuando cumple estas condiciones:

1. Opera sobre arrays NumPy densos con tipos estables (`float64`, `bool`, `uint8`).
2. No depende de objetos Python, `DataFrame`, grafos NetworkX ni callbacks LLM.
3. Tiene reglas de clipping claras para conservar rangos (`[-1, 1]` o `[0, 1]`).
4. Es llamada dentro de bucles de simulación o sobre poblaciones grandes.
5. Puede mantener la generación aleatoria en Python para reproducibilidad, o aceptar
   ruido ya muestreado como entrada.

## Funciones priorizadas

| Prioridad | Módulo Python | Función/proceso | Decisión | Motivo |
| --- | --- | --- | --- | --- |
| Alta | `simulator.py` | Actualización de opinión Langevin en `IntegratedSimulator.update_agents_with_langevin` | Migrada por wrapper opcional | Bucle por agente simple, sin objetos Python y con clipping bipolar obligatorio. |
| Alta | `massive_engine.py` | `ActiveSet.step` / cálculo de máscara activa | Migrada por wrapper opcional | Operación O(N·K + E) repetida en modo event-driven; entradas son arrays densos. |
| Media | `multilayer_engine.py` | `multi_potential_gradient` | Expuesta en Rust y mantenida como fallback NumPy | Kernel determinista y reusable; puede sustituir gradientes Numba cuando se instale la extensión. |
| Media | `multilayer_engine.py` | `multilayer_langevin_step` completo | Recomendado para una fase posterior | Es el mayor hotspot, pero hoy usa Numba y RNG interno; conviene migrarlo después de fijar compatibilidad estadística del ruido. |
| Baja | `massive_core/data_assimilation/kalman.py` | `EnsembleKalmanFilter.update` | No migrar todavía | La mayor carga está en álgebra lineal NumPy/BLAS; PyO3 añadiría copias o duplicaría BLAS sin ganancia clara. |
| Baja | `state_compression.py` | Compresión/descompresión MPS | No migrar todavía | Depende de SVD NumPy; mejor optimizar con LAPACK/BLAS existente antes de Rust. |
| Baja | `multilayer_engine.py` / `massive_engine.py` | Construcción dinámica de redes | No migrar todavía | Tiene más riesgo de compatibilidad por semántica de grafos y aleatoriedad que beneficio inmediato. |

## Implementación aplicada

- Se agregó un crate Rust `massive-rust-core` con PyO3/Maturin.
- Se agregó `massive_core.rust_core` como wrapper Python estable.
- Si `massive_rust_core` está instalado, el wrapper usa Rust; si no, usa NumPy.
- La API pública de `simular`, `simular_multiples`, `MultilayerEngine`,
  `MassiveEngine` e `IntegratedSimulator` permanece compatible.
- La aleatoriedad se mantiene en Python y Rust solo aplica transformaciones
  deterministas sobre arrays ya muestreados, reduciendo riesgo de cambios
  estadísticos.

## Proceso recomendado para futuras migraciones

1. Medir hotspot con `pytest` y benchmark aislado antes de migrar.
2. Escribir una prueba de equivalencia Python vs Rust con tolerancias exactas o
   numéricas explícitas.
3. Pasar a Rust solo kernels deterministas con arrays contiguos y tipos fijos.
4. Mantener fallback Python para entornos sin compilador Rust.
5. Ejecutar `cargo test`, pruebas unitarias Python y un smoke test de importación.
6. Solo después de validar equivalencia, conectar el wrapper en los motores de
   simulación.

## Compilación local

```bash
pip install maturin
maturin develop --release
python -c "import massive_rust_core; print('Rust core OK')"
```

Para empaquetar wheels reproducibles:

```bash
maturin build --release
```
