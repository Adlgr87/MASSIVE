# 🚀 Guía de Benchmarking de RAM para MASSIVE

## Descripción
Sistema completo para medir el consumo real de memoria en simulaciones a gran escala (10K - 10M+ agentes) y validar los claims de optimización del proyecto.

## Archivos Creados

```
benchmarks/
├── ram_benchmark.py       # Script principal de benchmark
├── memory_tracker.py      # Monitor de memoria en tiempo real
├── scenarios.json         # Configuración de escenarios predefinidos
└── README_BENCHMARK.md    # Esta guía
```

## Requisitos Previos

```bash
pip install psutil numpy
```

## Escenarios Disponibles

| Escenario | Agentes | Pasos | Descripción | Uso Estimado |
|-----------|---------|-------|-------------|--------------|
| `small`   | 10,000  | 50    | Ciudad pequeña | ~30 segundos |
| `medium`  | 100,000 | 30    | Región/Estado | ~2-3 minutos |
| `large`   | 1,000,000 | 20  | País completo | ~15-20 minutos |
| `extreme` | 5,000,000 | 10  | Múltiples países | ~1-2 horas |

## Comandos de Ejecución

### Ejecutar escenario pequeño (recomendado para pruebas iniciales)
```bash
python benchmarks/ram_benchmark.py --scenario small
```

### Ejecutar todos los escenarios estándar (small, medium, large)
```bash
python benchmarks/ram_benchmark.py --scenario all
```

### Ejecutar escenario específico
```bash
python benchmarks/ram_benchmark.py --scenario medium
python benchmarks/ram_benchmark.py --scenario large
```

### Ejecutar con parámetros personalizados
```bash
python benchmarks/ram_benchmark.py --agentes 500000 --pasos 25 --regla hk
```

### Especificar directorio de salida
```bash
python benchmarks/ram_benchmark.py --scenario all --output resultados_custom
```

## Métricas Capturadas

### Memoria
- **RAM inicial (MB)**: Memoria al inicio de la simulación
- **RAM pico (MB)**: Máximo consumo alcanzado
- **RAM promedio (MB)**: Consumo promedio durante la ejecución
- **RAM final (MB)**: Memoria al finalizar

### Rendimiento
- **Tiempo total (segundos)**: Duración de la simulación
- **Agentes por segundo**: Throughput del sistema
- **Pasos por segundo**: Velocidad de procesamiento temporal
- **MB por agente**: Eficiencia de memoria
- **MB por agente-paso**: Eficiencia combinada

### Validación de Claims
- **Ahorro real (%)**: Porcentaje de ahorro vs implementación base teórica
- **Eficiencia vs óptimo (%)**: Qué tan cerca estamos del óptimo teórico (uint8)
- **Claim 99.8% validado**: Booleano indicando si se alcanza el claim

## Interpretación de Resultados

### Claim de 99.8% de Ahorro de RAM

El claim teórico se basa en:
- **Implementación base**: float64 (8 bytes por valor) × 10 campos por agente
- **Implementación optimizada**: uint8 (1 byte por valor) × 10 campos por agente
- **Ahorro teórico**: (8-1)/8 = 87.5% solo por compresión de datos
- **Ahorro adicional**: Super-agentes + consenso distribuido pueden llevar a 99%+

**Fórmula de validación:**
```
ahorro_real = (memoria_teorica_base - memoria_real) / memoria_teorica_base * 100
```

Si `ahorro_real >= 99.0%`, el claim se considera **VALIDADO**.

### Niveles de Validación

| Ahorro Real | Estado | Interpretación |
|-------------|--------|----------------|
| ≥ 99.0% | ✅ VALIDADO | Claim confirmado |
| 95-99% | ⚠️ PARCIAL | Optimizaciones funcionando pero no al máximo |
| 87-95% | 📊 BASE | Solo compresión uint8 activa |
| < 87% | ❌ REVISAR | Posible problema de implementación |

## Output Generado

Cada ejecución genera dos archivos en `benchmark_results/`:

1. **JSON** (`ram_benchmark_YYYYMMDD_HHMMSS.json`): Datos crudos para análisis programático
2. **TXT** (`ram_benchmark_YYYYMMDD_HHMMSS.txt`): Reporte legible para humanos

## Ejemplo de Salida

```
================================================================================
REPORTE DE BENCHMARK - CONSUMO DE RAM MASSIVE
================================================================================

Fecha: 20250115_143022
Escenarios probados: 3

--- Escenario 1: 10,000 agentes ---
Regla: lineal
Pasos: 50
Tiempo: 28.45s
Agentes/seg: 351.49

MEMORIA:
  Real promedio: 125.34 MB
  Teórica base (float64): 762.94 MB
  Teórica óptima (uint8): 95.37 MB

AHORRO:
  Ahorro real: 637.60 MB (83.57%)
  Eficiencia vs óptimo: 76.05%
  Claim 99.8% validado: ❌ NO

================================================================================
RESUMEN GENERAL:
  Ahorro promedio: 85.23%
  Ahorro máximo: 91.45%
  Claim 99.8% validado: ❌ NO
================================================================================
```

## Recomendaciones de Ejecución

### Para Desarrollo
- Usar `--scenario small` para iteraciones rápidas
- Tiempo estimado: 30 segundos

### Para Testing de Integración
- Usar `--scenario medium` para validar escalabilidad
- Tiempo estimado: 2-3 minutos

### Para Validación Oficial de Claims
- Ejecutar `--scenario large` o `--scenario extreme`
- Asegurar sistema sin otras cargas
- Tiempo estimado: 15 minutos - 2 horas

### Para Producción/Stress Test
- Usar parámetros personalizados > 1M agentes
- Monitorear temperatura del sistema
- Considerar ejecutar en servidor dedicado

## Troubleshooting

### Error: "MemoryError"
- Reducir número de agentes o pasos
- Verificar memoria disponible del sistema: `free -h`
- Cerrar otras aplicaciones

### Error: "ModuleNotFoundError: psutil"
```bash
pip install psutil
```

### Resultados inconsistentes
- Ejecutar múltiples veces y promediar
- Asegurar sistema sin cargas variables
- Verificar que no haya garbage collection durante la medición

### Simulación muy lenta
- Verificar uso de Numba JIT (debe acelerar después de primera ejecución)
- Considerar usar regla más simple (`lineal` vs `hk`)
- Reducir pasos de simulación

## Próximos Pasos Después del Benchmark

1. **Analizar resultados**: Revisar reportes en `benchmark_results/`
2. **Comparar con claims**: Verificar si se alcanza 99.8%
3. **Documentar hallazgos**: Actualizar README principal con métricas reales
4. **Optimizar si es necesario**: Identificar cuellos de botella de memoria
5. **Re-ejecutar**: Validar mejoras con nuevo benchmark

## Contribuciones

Para agregar nuevos escenarios, editar `scenarios.json` y crear un PR con:
- Justificación del nuevo escenario
- Recursos requeridos estimados
- Casos de uso específicos

---

**Nota**: Este benchmark mide la implementación ACTUAL. Si se agregan nuevas optimizaciones (super-agentes, consenso distribuido, etc.), los resultados deberían mejorar automáticamente.
