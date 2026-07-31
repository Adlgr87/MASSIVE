#!/usr/bin/env python3
"""
Sistema de Profiling Automático para MASSIVE
Analiza CPU, Memoria y Tiempo de ejecución para identificar cuellos de botella

Uso:
    python benchmarks/profile_performance.py --scenario quick --mode all
    python benchmarks/profile_performance.py --scenario small --mode cpu
    python benchmarks/profile_performance.py --list-scenarios
"""

import argparse
import json
import os
import sys
import time
import cProfile
import pstats
import io
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List
import subprocess

# Agregar ruta del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️  psutil no disponible. Instalando: pip install psutil")

try:
    from memory_profiler import profile as memory_profile
    MEMORY_PROFILER_AVAILABLE = True
except ImportError:
    MEMORY_PROFILER_AVAILABLE = False
    print("⚠️  memory_profiler no disponible. Instalando: pip install memory_profiler")


class PerformanceProfiler:
    """Profiling automático de rendimiento para MASSIVE"""
    
    def __init__(self, config_path: str = "benchmarks/profiling_config.json"):
        self.config = self._load_config(config_path)
        self.results_dir = Path("profiling_results")
        self.results_dir.mkdir(exist_ok=True)
        self.process = psutil.Process() if PSUTIL_AVAILABLE else None
        
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """Carga configuración desde JSON"""
        try:
            with open(config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"⚠️  Config {config_path} no encontrado, usando defaults")
            return self._default_config()
            
    def _default_config(self) -> Dict[str, Any]:
        """Configuración por defecto"""
        return {
            "scenarios": {
                "quick": {"agents": 1000, "steps": 10, "rules": ["lineal"]},
                "small": {"agents": 10000, "steps": 50, "rules": ["lineal", "hk"]},
                "medium": {"agents": 100000, "steps": 100, "rules": ["lineal", "hk", "umbral"]},
                "large": {"agents": 1000000, "steps": 50, "rules": ["lineal"]}
            },
            "profiling": {
                "top_functions": 20,
                "time_threshold_ms": 10,
                "memory_threshold_mb": 1.0
            }
        }
        
    def run_cpu_profile(self, func, *args, **kwargs) -> Dict[str, Any]:
        """Ejecuta profiling de CPU con cProfile"""
        print("\n🔍 Iniciando CPU Profiling...")
        
        profiler = cProfile.Profile()
        start_time = time.time()
        
        profiler.enable()
        result = func(*args, **kwargs)
        profiler.disable()
        
        total_time = time.time() - start_time
        
        # Analizar resultados
        stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats('cumulative')
        stats.print_stats(self.config['profiling']['top_functions'])
        
        profile_data = stream.getvalue()
        
        # Guardar archivo .prof
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prof_file = self.results_dir / f"cpu_profile_{timestamp}.prof"
        stats.dump_stats(str(prof_file))
        
        # Parsear top functions
        top_functions = self._parse_profile_stats(profile_data)
        
        return {
            "total_time_sec": total_time,
            "profile_file": str(prof_file),
            "top_functions": top_functions,
            "raw_output": profile_data
        }
        
    def _parse_profile_stats(self, profile_text: str) -> List[Dict[str, Any]]:
        """Parsea output de pstats a estructura JSON"""
        functions = []
        lines = profile_text.split('\n')[5:]  # Saltar header
        
        for line in lines[:self.config['profiling']['top_functions']]:
            if line.strip() and len(line.split()) >= 4:
                parts = line.split()
                try:
                    functions.append({
                        "ncalls": parts[0],
                        "tottime": float(parts[1]),
                        "percall": float(parts[2]),
                        "cumtime": float(parts[3]),
                        "filename_lineno": ' '.join(parts[4:])
                    })
                except (ValueError, IndexError):
                    continue
                    
        return functions
        
    def run_memory_profile(self, func, *args, **kwargs) -> Dict[str, Any]:
        """Ejecuta profiling de memoria"""
        print("\n💾 Iniciando Memory Profiling...")
        
        if not MEMORY_PROFILER_AVAILABLE:
            print("⚠️  memory_profiler no disponible, saltando...")
            return {"error": "memory_profiler not available"}
            
        initial_mem = self.process.memory_info().rss / 1024 / 1024 if self.process else 0
        peak_mem = initial_mem
        
        # Ejecutar función monitoreando memoria
        @memory_profile
        def wrapper():
            nonlocal peak_mem
            result = func(*args, **kwargs)
            current_mem = self.process.memory_info().rss / 1024 / 1024 if self.process else 0
            peak_mem = max(peak_mem, current_mem)
            return result
            
        result = wrapper()
        final_mem = self.process.memory_info().rss / 1024 / 1024 if self.process else 0
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        mem_report = {
            "initial_mb": initial_mem,
            "peak_mb": peak_mem,
            "final_mb": final_mem,
            "delta_mb": final_mem - initial_mem,
            "peak_delta_mb": peak_mem - initial_mem
        }
        
        # Guardar reporte
        mem_file = self.results_dir / f"memory_profile_{timestamp}.json"
        with open(mem_file, 'w') as f:
            json.dump(mem_report, f, indent=2)
            
        return mem_report
        
    def run_time_profile(self, func, *args, **kwargs) -> Dict[str, Any]:
        """Profiling detallado de tiempos"""
        print("\n⏱️  Iniciando Time Profiling...")
        
        timings = {}
        
        # Medir tiempo total
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        
        timings["total_execution"] = end - start
        
        # Si es simulación, extraer tiempos internos
        if hasattr(result, 'get'):
            if 'timing_info' in result:
                timings.update(result['timing_info'])
                
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        time_file = self.results_dir / f"time_profile_{timestamp}.json"
        
        with open(time_file, 'w') as f:
            json.dump(timings, f, indent=2)
            
        return timings
        
    def generate_summary(self, results: Dict[str, Any]) -> str:
        """Genera resumen legible de resultados"""
        summary = []
        summary.append("=" * 80)
        summary.append("REPORTE DE PROFILING - MASSIVE")
        summary.append("=" * 80)
        summary.append(f"Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        summary.append("")
        
        if 'cpu' in results:
            cpu = results['cpu']
            summary.append("📊 CPU PROFILING:")
            summary.append(f"  Tiempo total: {cpu['total_time_sec']:.2f}s")
            summary.append(f"  Archivo: {cpu['profile_file']}")
            summary.append("  Top 5 funciones:")
            for i, func in enumerate(cpu['top_functions'][:5], 1):
                summary.append(f"    {i}. {func['filename_lineno']} ({func['cumtime']:.3f}s)")
            summary.append("")
            
        if 'memory' in results and 'error' not in results['memory']:
            mem = results['memory']
            summary.append("💾 MEMORY PROFILING:")
            summary.append(f"  Inicial: {mem['initial_mb']:.2f} MB")
            summary.append(f"  Pico: {mem['peak_mb']:.2f} MB (+{mem['peak_delta_mb']:.2f} MB)")
            summary.append(f"  Final: {mem['final_mb']:.2f} MB")
            summary.append("")
            
        if 'time' in results:
            time_data = results['time']
            summary.append("⏱️  TIME PROFILING:")
            for key, value in time_data.items():
                summary.append(f"  {key}: {value*1000:.2f}ms" if isinstance(value, float) else f"  {key}: {value}")
            summary.append("")
            
        # Detectar bottlenecks potenciales
        summary.append("🔍 BOTTLENECKS POTENCIALES:")
        if 'cpu' in results:
            for func in results['cpu'].get('top_functions', [])[:3]:
                if func['cumtime'] > 1.0:  # Más de 1 segundo
                    summary.append(f"  ⚠️  {func['filename_lineno']} - {func['cumtime']:.2f}s")
                    
        summary.append("")
        summary.append("=" * 80)
        
        return "\n".join(summary)
        
    def save_summary(self, summary: str, scenario: str):
        """Guarda resumen en archivo"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        summary_file = self.results_dir / f"summary_{scenario}_{timestamp}.txt"
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)
            
        print(f"\n📄 Resumen guardado en: {summary_file}")
        

def run_simulation_benchmark(scenario_config: Dict[str, Any]):
    """Ejecuta simulación para profiling"""
    from simulator import simular
    import numpy as np
    
    agents = scenario_config.get('agents', 1000)
    steps = scenario_config.get('steps', 10)
    rules = scenario_config.get('rules', [0])  # Usar IDs numéricos por defecto
    
    print(f"🚀 Ejecutando simulación: {agents} agentes, {steps} pasos, reglas: {rules}")
    
    # Mapeo de nombres a IDs (si se usan nombres en lugar de IDs)
    NOMBRE_A_ID = {
        'lineal': 0, 'umbral': 1, 'memoria': 2, 'backlash': 3,
        'polarizacion': 4, 'hk': 5, 'contagio_competitivo': 6,
        'umbral_heterogeneo': 7, 'homofilia': 8, 'replicador': 9
    }
    
    # Ejecutar múltiples simulaciones escalares para evitar problemas con arrays
    resultados = []
    n_muestras = min(100, agents)  # Máximo 100 muestras para profiling
    
    for i in range(n_muestras):
        # Estado inicial escalar para un solo agente
        estado_inicial = {
            'opinion': float(np.random.rand()),
            'propaganda': 0.0,
            'confianza': 0.75
        }
        
        # Convertir nombre a ID si es necesario
        rule_input = rules[i % len(rules)]
        rule_id = NOMBRE_A_ID.get(rule_input, rule_input) if isinstance(rule_input, str) else rule_input
        
        # Configurar parámetros según firma de simular()
        # Usar config anidada para forzar regla específica
        params = {
            'estado_inicial': estado_inicial,
            'escenario': 'campana',  # Siempre usar 'campana' como escenario
            'pasos': steps,
            'cada_n_pasos': steps,  # No cambiar de regla durante la simulación
            'verbose': False,
            'config': {
                'regla_forzada': rule_id,  # Forzar regla específica por ID en config
                'llm_provider': 'heuristico',  # Usar selector heurístico para evitar LLM calls
                'heuristic_override_rule': rule_id  # Override directo en selector heurístico
            }
        }
        
        # Ejecutar simulación individual
        resultado = simular(**params)
        resultados.append(resultado)
    
    return {
        'resultados': resultados,
        'n_muestras': n_muestras,
        'agentes_totales': n_muestras,
        'pasos_totales': n_muestras * steps
    }


def main():
    parser = argparse.ArgumentParser(description="Profiling automático para MASSIVE")
    parser.add_argument('--scenario', type=str, default='quick',
                       choices=['quick', 'small', 'medium', 'large'],
                       help='Escenario de prueba')
    parser.add_argument('--mode', type=str, default='all',
                       choices=['cpu', 'memory', 'time', 'all'],
                       help='Tipo de profiling')
    parser.add_argument('--config', type=str, default='benchmarks/profiling_config.json',
                       help='Ruta al archivo de configuración')
    parser.add_argument('--list-scenarios', action='store_true',
                       help='Lista escenarios disponibles')
    
    args = parser.parse_args()
    
    if args.list_scenarios:
        profiler = PerformanceProfiler(args.config)
        print("\n📋 Escenarios disponibles:")
        for name, config in profiler.config['scenarios'].items():
            print(f"  {name}: {config['agents']} agentes, {config['steps']} pasos")
        return
        
    # Inicializar profiler
    profiler = PerformanceProfiler(args.config)
    
    # Obtener configuración del escenario
    scenario_config = profiler.config['scenarios'].get(args.scenario)
    if not scenario_config:
        print(f"❌ Escenario '{args.scenario}' no encontrado")
        return
        
    # Ejecutar profiling
    results = {}
    
    if args.mode in ['cpu', 'all']:
        results['cpu'] = profiler.run_cpu_profile(run_simulation_benchmark, scenario_config)
        
    if args.mode in ['memory', 'all']:
        results['memory'] = profiler.run_memory_profile(run_simulation_benchmark, scenario_config)
        
    if args.mode in ['time', 'all']:
        results['time'] = profiler.run_time_profile(run_simulation_benchmark, scenario_config)
        
    # Generar y guardar resumen
    summary = profiler.generate_summary(results)
    print(summary)
    profiler.save_summary(summary, args.scenario)
    
    print("\n✅ Profiling completado. Revisa la carpeta profiling_results/")


if __name__ == "__main__":
    main()
