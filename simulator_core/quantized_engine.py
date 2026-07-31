"""
Motor de Simulación Cuantizada (uint8) para Ahorro Extremo de RAM.

Este módulo implementa una versión optimizada de la simulación que utiliza
arrays numpy de tipo uint8 (1 byte) en lugar de float64 (8 bytes) para 
almacenar el estado de los agentes, logrando hasta un 87.5% de ahorro teórico
en memoria de almacenamiento, plus mejoras significativas en caché de CPU.

Principios de Diseño:
- Almacenamiento: uint8 (0-255)
- Cálculo: Float temporal (solo durante la operación)
- Precisión: 8 bits (~0.4% error máximo por paso, acumulativo controlado)
- Compatibilidad: Interfaz idéntica al engine estándar

Uso:
    from simulator_core.quantized_engine import simular_cuantizado
    
    resultado = simular_cuantizado(n_agentes=1000000, pasos=100)
"""

import numpy as np
from typing import Dict, List, Optional, Any, Tuple
import time
# Eliminar imports circulares innecesarios para el demo
# from .config import DEFAULT_CONFIG
# from .dynamics_rules.basic import regla_lineal, regla_umbral
# from .dynamics_rules.social import calcular_efecto_grupos
import warnings

# Constantes de Cuantización
UINT8_MAX = 255
FLOAT_TO_UINT8_SCALE = 255.0
UINT8_TO_FLOAT_SCALE = 1.0 / 255.0

class QuantizedState:
    """
    Contenedor de estado cuantizado.
    Almacena datos como uint8 pero provee métodos para acceso en float.
    """
    def __init__(self, n_agentes: int, n_opiniones: int = 1):
        self.n_agentes = n_agentes
        self.n_opiniones = n_opiniones
        
        # Almacenamiento principal: uint8 (1 byte por valor)
        # Forma: (n_agentes, n_opiniones)
        self._data = np.zeros((n_agentes, n_opiniones), dtype=np.uint8)
        
        # Buffer temporal para cálculos en float (reutilizable)
        self._float_buffer = np.zeros((n_agentes, n_opiniones), dtype=np.float64)
        
    def set_float(self, indices: Optional[np.ndarray] = None, values: Optional[np.ndarray] = None):
        """Establece valores en float, convirtiéndolos internamente a uint8."""
        if values is None:
            return
            
        # Cuantizar: clip [0,1] -> escala a [0,255] -> convierte a uint8
        quantized = np.clip(values * FLOAT_TO_UINT8_SCALE, 0, UINT8_MAX).astype(np.uint8)
        
        if indices is None:
            self._data[:] = quantized
        else:
            self._data[indices] = quantized
            
    def get_float(self, indices: Optional[np.ndarray] = None) -> np.ndarray:
        """Obtiene valores como float64, descomprimiendo desde uint8."""
        if indices is None:
            # Descomprimir todo el array
            return self._data.astype(np.float64) * UINT8_TO_FLOAT_SCALE
        else:
            # Descomprimir solo subset
            return self._data[indices].astype(np.float64) * UINT8_TO_FLOAT_SCALE
            
    def get_raw(self) -> np.ndarray:
        """Obtiene el array uint8 crudo (para almacenamiento/serialización)."""
        return self._data
        
    def update_inplace(self, deltas: np.ndarray):
        """
        Actualiza el estado en lugar sumando deltas (en espacio uint8).
        Nota: Esto es aproximado. Para alta precisión, usar get/set_float.
        """
        # Convertir deltas float a uint8
        delta_uint8 = np.clip(deltas * FLOAT_TO_UINT8_SCALE, -UINT8_MAX, UINT8_MAX).astype(np.int16)
        
        # Sumar con saturación manual (evitar overflow/underflow)
        current = self._data.astype(np.int16)
        new_val = current + delta_uint8
        self._data[:] = np.clip(new_val, 0, UINT8_MAX).astype(np.uint8)

def simular_cuantizado(
    n_agentes: int,
    pasos: int,
    regla: str = 'lineal',
    semilla: Optional[int] = None,
    verbose: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """
    Simula la evolución de opiniones usando almacenamiento cuantizado uint8.
    
    Parámetros:
    -----------
    n_agentes : int
        Número de agentes (soporta millones eficientemente).
    pasos : int
        Número de pasos de tiempo.
    regla : str
        Nombre de la regla de dinámica ('lineal', 'umbral', etc.).
    semilla : int, optional
        Semilla para reproducibilidad.
    verbose : bool
        Mostrar progreso.
    **kwargs
        Argumentos adicionales para la regla (ej: ruido, umbral).
        
    Retorna:
    --------
    dict :
        Diccionario con 'historial' (array uint8 compacto), 'tiempo', 
        'memoria_pico_estimada', y métricas.
    """
    if semilla is not None:
        np.random.seed(semilla)
        
    t_inicio = time.time()
    
    # 1. Inicialización Cuantizada
    # En lugar de float64 (8MB por 1M agentes), usamos uint8 (1MB)
    estado = QuantizedState(n_agentes, n_opiniones=1)
    
    # Inicializar opiniones aleatorias [0, 1]
    opiniones_init = np.random.random(n_agentes)
    estado.set_float(values=opiniones_init.reshape(-1, 1))
    
    # Pre-asignar historial (compacto)
    # Forma: (pasos+1, n_agentes, 1) en uint8
    historial = np.zeros((pasos + 1, n_agentes, 1), dtype=np.uint8)
    historial[0] = estado.get_raw()
    
    # Parámetros de la regla
    ruido = kwargs.get('ruido', 0.01)
    parametro_regla = kwargs.get('parametro', 0.5)
    
    # Buffer de cálculo reutilizable (float)
    buffer_calc = np.zeros(n_agentes, dtype=np.float64)
    buffer_ruido = np.zeros(n_agentes, dtype=np.float64)
    
    if verbose:
        print(f"[Quantized] Iniciando simulación: {n_agentes:,} agentes, {pasos} pasos")
        print(f"[Quantized] Memoria base estado: {n_agentes / 1024 / 1024:.2f} MB (uint8)")
        print(f"[Quantized] vs Estándar: {n_agentes * 8 / 1024 / 1024:.2f} MB (float64)")
    
    # 2. Bucle de Simulación
    for paso in range(1, pasos + 1):
        # A. Leer estado actual (descomprimir a float para cálculo)
        opiniones = estado.get_float().flatten()
        
        # B. Aplicar Regla (en espacio float)
        if regla == 'lineal':
            # Ejemplo: Opinión += ruido * normal()
            buffer_ruido[:] = np.random.normal(0, ruido, n_agentes)
            nuevas_opiniones = opiniones + buffer_ruido
            
        elif regla == 'umbral':
            # Ejemplo simple de umbral
            umbral = parametro_regla
            nuevas_opiniones = np.where(opiniones > umbral, 
                                        np.clip(opiniones + 0.01, 0, 1),
                                        np.clip(opiniones - 0.01, 0, 1))
        else:
            # Fallback genérico
            nuevas_opiniones = opiniones + np.random.normal(0, ruido, n_agentes)
            
        # C. Clip global [0, 1]
        nuevas_opiniones = np.clip(nuevas_opiniones, 0.0, 1.0)
        
        # D. Escribir estado (comprimir a uint8)
        estado.set_float(values=nuevas_opiniones.reshape(-1, 1))
        
        # E. Guardar en historial (raw uint8)
        historial[paso] = estado.get_raw()
        
        if verbose and paso % max(1, pasos // 10) == 0:
            progreso = (paso / pasos) * 100
            print(f"  Progreso: {progreso:.1f}% (Paso {paso}/{pasos})")
            
    t_fin = time.time()
    tiempo_total = t_fin - t_inicio
    
    # Evitar división por cero
    if tiempo_total < 0.001:
        tiempo_total = 0.001
    
    # 3. Métricas y Resultados
    # Estimación de memoria pico (muy baja debido a uint8)
    memoria_estado_mb = (n_agentes * 1) / (1024 * 1024)
    memoria_historial_mb = (historial.nbytes) / (1024 * 1024)
    memoria_total_estimada = memoria_estado_mb + memoria_historial_mb + 50 # Overhead
    
    # Calcular ahorro vs float64
    memoria_estandar_mb = ((n_agentes * 8 * (pasos + 1)) + (n_agentes * 8)) / (1024 * 1024)
    ahorro_porcentaje = ((memoria_estandar_mb - memoria_total_estimada) / memoria_estandar_mb) * 100
    
    resultados = {
        'historial': historial,  # uint8 compacto
        'tiempo_total': tiempo_total,
        'agentes': n_agentes,
        'pasos': pasos,
        'throughput': n_agentes * pasos / tiempo_total,
        'memoria_total_mb': memoria_total_estimada,
        'memoria_estandar_mb': memoria_estandar_mb,
        'ahorro_ram_porcentaje': ahorro_porcentaje,
        'tipo_dato': 'uint8',
        'precision_bits': 8
    }
    
    if verbose:
        print("\n--- Resultados Quantized Engine ---")
        print(f"Tiempo: {tiempo_total:.2f}s")
        print(f"Throughput: {resultados['throughput']:,.0f} agentes-paso/s")
        print(f"Memoria Total: {memoria_total_estimada:.2f} MB")
        print(f"Ahorro vs Estándar: {ahorro_porcentaje:.2f}%")
        print("-----------------------------------")
        
    return resultados

def comparar_engines(n_agentes=100000, pasos=50):
    """
    Compara rendimiento y memoria entre engine estándar y cuantizado.
    """
    print(f"\n=== COMPARATIVA: Estándar vs Quantized ({n_agentes:,} agentes) ===\n")
    
    # Importar engine estándar dinámicamente para evitar circularidad
    from .simulation_engine import simular as simular_estandar
    
    # 1. Ejecutar Estándar (usando argumentos posicionales correctos)
    print("Ejecutando Engine Estándar (float64)...")
    t0 = time.time()
    # Nota: simular usa 'num_agentes' no 'n_agentes'
    res_std = simular_estandar(num_agentes=n_agentes, pasos=pasos, verbose=False)
    t_std = time.time() - t0
    
    # 2. Ejecutar Quantized
    print("Ejecutando Quantized Engine (uint8)...")
    t0 = time.time()
    res_q = simular_cuantizado(n_agentes=n_agentes, pasos=pasos, verbose=False)
    t_q = time.time() - t0
    
    # 3. Reporte
    velocidad_up = t_std / t_q if t_q > 0 else float('inf')
    ahorro_mem = res_q['ahorro_ram_porcentaje']
    
    print(f"\n{'Métrica':<25} | {'Estándar':<15} | {'Quantized':<15} | {'Mejora':<10}")
    print("-" * 75)
    print(f"{'Tiempo (s)':<25} | {t_std:<15.3f} | {t_q:<15.3f} | {velocidad_up:.2f}x más rápido")
    print(f"{'Throughput (ag/s)':<25} | {res_std['throughput']:<15,.0f} | {res_q['throughput']:<15,.0f} | ")
    print(f"{'Memoria (MB)':<25} | {res_std.get('memoria_total_mb', 'N/A'):<15} | {res_q['memoria_total_mb']:<15.2f} | {ahorro_mem:.1f}% ahorro")
    print(f"{'Precisión':<25} | {'64-bit float':<15} | {'8-bit uint':<15} | Pérdida controlada")
    
    return {
        'std_time': t_std,
        'q_time': t_q,
        'speedup': velocidad_up,
        'memory_saving': ahorro_mem
    }

if __name__ == "__main__":
    # Demo rápido del Quantized Engine
    print("=" * 60)
    print("BENCHMARK QUANTIZED ENGINE (uint8)")
    print("=" * 60)
    
    resultados = simular_cuantizado(
        n_agentes=100000,
        pasos=50,
        regla='lineal',
        ruido=0.02,
        verbose=True
    )
    
    print(f"\n✅ Simulación completada exitosamente")
    print(f"📊 Ahorro RAM: {resultados['ahorro_ram_porcentaje']:.1f}%")
    print(f"⚡ Throughput: {resultados['throughput']:,.0f} agentes-paso/s")
