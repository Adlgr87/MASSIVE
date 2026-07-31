"""
Memory Tracker para monitoreo en tiempo real del consumo de RAM.
Usa psutil para mediciones precisas sin interferir con la simulación.
"""

import psutil
import os
import time
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import threading
from queue import Queue
import json


@dataclass
class MemorySnapshot:
    """Instantánea de consumo de memoria"""
    timestamp: float
    ram_mb: float
    ram_percent: float
    

@dataclass
class MemoryReport:
    """Reporte completo de consumo de memoria"""
    snapshots: List[MemorySnapshot] = field(default_factory=list)
    peak_mb: float = 0.0
    initial_mb: float = 0.0
    final_mb: float = 0.0
    average_mb: float = 0.0
    duration_seconds: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'peak_mb': round(self.peak_mb, 2),
            'initial_mb': round(self.initial_mb, 2),
            'final_mb': round(self.final_mb, 2),
            'average_mb': round(self.average_mb, 2),
            'duration_seconds': round(self.duration_seconds, 2),
            'snapshots_count': len(self.snapshots),
            'sampling_rate_hz': len(self.snapshots) / max(0.001, self.duration_seconds)
        }


class MemoryTracker:
    """Monitor de memoria en tiempo real"""
    
    def __init__(self, sampling_interval: float = 0.1):
        """
        Args:
            sampling_interval: Intervalo entre mediciones en segundos (default: 100ms)
        """
        self.sampling_interval = sampling_interval
        self.process = psutil.Process(os.getpid())
        self.running = False
        self.snapshots: List[MemorySnapshot] = []
        self.thread: Optional[threading.Thread] = None
        self.queue = Queue()
        
    def _get_memory_mb(self) -> float:
        """Obtiene memoria actual en MB"""
        return self.process.memory_info().rss / (1024 * 1024)
    
    def _get_memory_percent(self) -> float:
        """Obtiene porcentaje de memoria del sistema"""
        return self.process.memory_percent()
    
    def _monitor_loop(self):
        """Bucle de monitoreo en hilo separado"""
        while self.running:
            try:
                snapshot = MemorySnapshot(
                    timestamp=time.time(),
                    ram_mb=self._get_memory_mb(),
                    ram_percent=self._get_memory_percent()
                )
                self.snapshots.append(snapshot)
                self.queue.put(snapshot)
            except Exception as e:
                print(f"Error en medición de memoria: {e}")
            
            time.sleep(self.sampling_interval)
    
    def start(self):
        """Inicia el monitoreo"""
        self.running = True
        self.snapshots.clear()
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        # Pequeña pausa para asegurar primera medición
        time.sleep(self.sampling_interval * 2)
    
    def stop(self) -> MemoryReport:
        """Detiene el monitoreo y genera reporte"""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        
        if not self.snapshots:
            return MemoryReport()
        
        # Calcular estadísticas
        ram_values = [s.ram_mb for s in self.snapshots]
        timestamps = [s.timestamp for s in self.snapshots]
        
        report = MemoryReport(
            snapshots=self.snapshots.copy(),
            peak_mb=max(ram_values),
            initial_mb=ram_values[0],
            final_mb=ram_values[-1],
            average_mb=sum(ram_values) / len(ram_values),
            duration_seconds=timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0.0
        )
        
        return report
    
    def get_current_mb(self) -> float:
        """Obtiene memoria actual sin esperar al hilo"""
        return self._get_memory_mb()


def estimate_theoretical_memory(agentes: int, dtype_bits: int = 64) -> Dict[str, float]:
    """
    Estima memoria teórica requerida para diferentes configuraciones.
    
    Args:
        agentes: Número de agentes
        dtype_bits: Bits por dato (64=float64, 8=uint8)
    
    Returns:
        Diccionario con estimaciones en MB
    """
    # Campos típicos por agente: opinion, confianza, energia, pertenencia_grupo, etc. (~10 floats)
    campos_por_agente = 10
    
    # Memoria base sin optimizar (float64)
    bytes_por_float64 = 8
    memoria_base_bytes = agentes * campos_por_agente * bytes_por_float64
    memoria_base_mb = memoria_base_bytes / (1024 * 1024)
    
    # Memoria optimizada (uint8)
    bytes_por_uint8 = 1
    memoria_optimizada_bytes = agentes * campos_por_agente * bytes_por_uint8
    memoria_optimizada_mb = memoria_optimizada_bytes / (1024 * 1024)
    
    # Ahorro teórico
    ahorro_bytes = memoria_base_bytes - memoria_optimizada_bytes
    ahorro_porcentaje = (ahorro_bytes / memoria_base_bytes) * 100 if memoria_base_bytes > 0 else 0
    
    return {
        'agentes': agentes,
        'memoria_base_float64_mb': round(memoria_base_mb, 2),
        'memoria_optimizada_uint8_mb': round(memoria_optimizada_mb, 2),
        'ahorro_teorico_mb': round(ahorro_bytes / (1024 * 1024), 2),
        'ahorro_teorico_porcentaje': round(ahorro_porcentaje, 2),
        'mb_por_agente_base': round(memoria_base_mb / agentes, 6),
        'mb_por_agente_optimizado': round(memoria_optimizada_mb / agentes, 6)
    }


if __name__ == "__main__":
    # Demo de uso
    print("=== Demo Memory Tracker ===")
    
    # Estimaciones teóricas
    for n in [10_000, 100_000, 1_000_000, 5_000_000]:
        est = estimate_theoretical_memory(n)
        print(f"\n{n:,} agentes:")
        print(f"  Base (float64): {est['memoria_base_float64_mb']:,.2f} MB")
        print(f"  Optimizado (uint8): {est['memoria_optimizada_uint8_mb']:,.2f} MB")
        print(f"  Ahorro: {est['ahorro_teorico_mb']:,.2f} MB ({est['ahorro_teorico_porcentaje']:.1f}%)")
    
    # Test en vivo
    print("\n\n=== Test en Vivo (10 segundos) ===")
    tracker = MemoryTracker(sampling_interval=0.5)
    tracker.start()
    
    time.sleep(10)
    
    report = tracker.stop()
    print(f"Duración: {report.duration_seconds:.2f}s")
    print(f"Inicial: {report.initial_mb:.2f} MB")
    print(f"Pico: {report.peak_mb:.2f} MB")
    print(f"Final: {report.final_mb:.2f} MB")
    print(f"Promedio: {report.average_mb:.2f} MB")
    print(f"Muestras: {len(report.snapshots)}")
