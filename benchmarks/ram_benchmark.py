#!/usr/bin/env python3
"""
Benchmark de Consumo de RAM para MASSIVE
=========================================

Mide el consumo real de memoria en simulaciones a gran escala (10K - 10M agentes)
y compara optimizaciones vs implementación base.

Uso:
    python benchmarks/ram_benchmark.py --scenario small
    python benchmarks/ram_benchmark.py --scenario all
    python benchmarks/ram_benchmark.py --agentes 1000000 --pasos 20

Requisitos:
    pip install psutil numpy
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import numpy as np

# Agregar root al path
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.memory_tracker import MemoryTracker, estimate_theoretical_memory
from simulator import simular


def cargar_escenarios() -> Dict[str, Any]:
    """Carga configuración de escenarios desde JSON"""
    config_path = Path(__file__).parent / "scenarios.json"
    with open(config_path, 'r') as f:
        return json.load(f)


def ejecutar_simulacion_benchmark(
    agentes: int,
    pasos: int,
    regla: str = "lineal",
    rango_opinion: tuple = (0, 1),
    proveedor_llm: str = "heuristico",
    trackear_memoria: bool = True
) -> Dict[str, Any]:
    """
    Ejecuta una simulación benchmark midiendo consumo de RAM.
    
    Returns:
        Diccionario con resultados de la simulación y métricas de memoria
    """
    resultado = {
        'configuracion': {
            'agentes': agentes,
            'pasos': pasos,
            'regla': regla,
            'rango_opinion': list(rango_opinion),
            'proveedor_llm': proveedor_llm
        },
        'memoria': {},
        'rendimiento': {},
        'resultado_simulacion': {}
    }
    
    # Iniciar tracker de memoria
    tracker = MemoryTracker(sampling_interval=0.5) if trackear_memoria else None
    
    try:
        # Medir memoria inicial
        if tracker:
            tracker.start()
            tiempo_espera = 1.0  # Esperar para estabilizar mediciones
            time.sleep(tiempo_espera)
        
        # Ejecutar simulación
        inicio = time.time()
        
        print(f"\n🚀 Iniciando simulación: {agentes:,} agentes, {pasos} pasos, regla='{regla}'")
        print(f"📊 Memoria inicial: {tracker.get_current_mb():.2f} MB" if tracker else "")
        
        resultado_sim = simular(
            n_agentes=agentes,
            pasos=pasos,
            regla=regla,
            rango_opinion=rango_opinion,
            proveedor_llm=proveedor_llm,
            guardar_historial=True
        )
        
        fin = time.time()
        
        # Detener tracker
        reporte_memoria = None
        if tracker:
            reporte_memoria = tracker.stop()
        
        # Calcular métricas
        duracion = fin - inicio
        
        resultado['rendimiento'] = {
            'tiempo_total_segundos': round(duracion, 2),
            'agentes_por_segundo': round(agentes / duracion, 2) if duracion > 0 else 0,
            'pasos_por_segundo': round(pasos / duracion, 2) if duracion > 0 else 0
        }
        
        if reporte_memoria:
            resultado['memoria'] = reporte_memoria.to_dict()
            
            # Calcular eficiencia
            mb_promedio = reporte_memoria.average_mb
            resultado['rendimiento']['mb_por_agente'] = round(mb_promedio / agentes, 6)
            resultado['rendimiento']['mb_por_agente_paso'] = round(
                mb_promedio / (agentes * pasos), 8
            )
        
        # Guardar resultado de simulación (resumen)
        if isinstance(resultado_sim, dict):
            resultado['resultado_simulacion'] = {
                'tipo': type(resultado_sim).__name__,
                'tiene_historial': 'historial' in resultado_sim if isinstance(resultado_sim, dict) else False,
                'longitud_historial': len(resultado_sim.get('historial', [])) if isinstance(resultado_sim, dict) else 0
            }
        
        print(f"✅ Simulación completada en {duracion:.2f}s")
        if reporte_memoria:
            print(f"📈 Memoria pico: {reporte_memoria.peak_mb:.2f} MB")
            print(f"📉 Memoria promedio: {reporte_memoria.average_mb:.2f} MB")
        
        return resultado
        
    except Exception as e:
        print(f"❌ Error en simulación: {e}")
        if tracker:
            tracker.stop()
        raise
    finally:
        # Forzar garbage collection
        import gc
        gc.collect()


def comparar_con_teoria(resultados: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compara resultados reales con estimaciones teóricas.
    
    Returns:
        Diccionario con comparación y porcentaje de ahorro real
    """
    agentes = resultados['configuracion']['agentes']
    memoria_real_mb = resultados['memoria'].get('average_mb', 0)
    
    # Estimación teórica sin optimizar (float64)
    teoria = estimate_theoretical_memory(agentes, dtype_bits=64)
    memoria_teorica_base = teoria['memoria_base_float64_mb']
    
    # Estimación teórica optimizada (uint8)
    teoria_opt = estimate_theoretical_memory(agentes, dtype_bits=8)
    memoria_teorica_opt = teoria_opt['memoria_optimizada_uint8_mb']
    
    # Calcular ahorro real vs base teórico
    if memoria_teorica_base > 0:
        ahorro_real_mb = memoria_teorica_base - memoria_real_mb
        ahorro_real_porcentaje = (ahorro_real_mb / memoria_teorica_base) * 100
    else:
        ahorro_real_mb = 0
        ahorro_real_porcentaje = 0
    
    # Comparar con óptimo teórico
    if memoria_teorica_opt > 0:
        eficiencia_vs_optimo = (memoria_teorica_opt / memoria_real_mb) * 100 if memoria_real_mb > 0 else 0
    else:
        eficiencia_vs_optimo = 0
    
    return {
        'memoria_real_mb': round(memoria_real_mb, 2),
        'memoria_teorica_base_mb': round(memoria_teorica_base, 2),
        'memoria_teorica_optima_mb': round(memoria_teorica_opt, 2),
        'ahorro_real_mb': round(ahorro_real_mb, 2),
        'ahorro_real_porcentaje': round(ahorro_real_porcentaje, 2),
        'eficiencia_vs_optimo_porcentaje': round(eficiencia_vs_optimo, 2),
        'claim_99_8_porcentaje_validado': ahorro_real_porcentaje >= 99.0
    }


def generar_reporte(resultados: list, output_dir: str = "benchmark_results") -> str:
    """
    Genera reporte completo en JSON y texto.
    
    Returns:
        Ruta del archivo de reporte
    """
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Reporte JSON
    reporte_json = {
        'timestamp': timestamp,
        'total_escenarios': len(resultados),
        'resultados': resultados,
        'comparaciones': []
    }
    
    for res in resultados:
        comparacion = comparar_con_teoria(res)
        reporte_json['comparaciones'].append(comparacion)
    
    # Agregar resumen
    ahorros = [c['ahorro_real_porcentaje'] for c in reporte_json['comparaciones']]
    reporte_json['resumen'] = {
        'ahorro_promedio_porcentaje': round(sum(ahorros) / len(ahorros), 2) if ahorros else 0,
        'ahorro_maximo_porcentaje': round(max(ahorros), 2) if ahorros else 0,
        'ahorro_minimo_porcentaje': round(min(ahorros), 2) if ahorros else 0,
        'claim_99_8_validado': all(c['claim_99_8_porcentaje_validado'] for c in reporte_json['comparaciones'])
    }
    
    # Guardar JSON
    json_path = output_path / f"ram_benchmark_{timestamp}.json"
    with open(json_path, 'w') as f:
        json.dump(reporte_json, f, indent=2, default=str)
    
    # Guardar TXT legible
    txt_path = output_path / f"ram_benchmark_{timestamp}.txt"
    with open(txt_path, 'w') as f:
        f.write("=" * 80 + "\n")
        f.write("REPORTE DE BENCHMARK - CONSUMO DE RAM MASSIVE\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Fecha: {timestamp}\n")
        f.write(f"Escenarios probados: {len(resultados)}\n\n")
        
        for i, (res, comp) in enumerate(zip(resultados, reporte_json['comparaciones']), 1):
            f.write(f"--- Escenario {i}: {res['configuracion']['agentes']:,} agentes ---\n")
            f.write(f"Regla: {res['configuracion']['regla']}\n")
            f.write(f"Pasos: {res['configuracion']['pasos']}\n")
            f.write(f"Tiempo: {res['rendimiento']['tiempo_total_segundos']:.2f}s\n")
            f.write(f"Agentes/seg: {res['rendimiento']['agentes_por_segundo']:,.2f}\n\n")
            
            f.write("MEMORIA:\n")
            f.write(f"  Real promedio: {comp['memoria_real_mb']:,.2f} MB\n")
            f.write(f"  Teórica base (float64): {comp['memoria_teorica_base_mb']:,.2f} MB\n")
            f.write(f"  Teórica óptima (uint8): {comp['memoria_teorica_optima_mb']:,.2f} MB\n\n")
            
            f.write("AHORRO:\n")
            f.write(f"  Ahorro real: {comp['ahorro_real_mb']:,.2f} MB ({comp['ahorro_real_porcentaje']:.2f}%)\n")
            f.write(f"  Eficiencia vs óptimo: {comp['eficiencia_vs_optimo_porcentaje']:.2f}%\n")
            f.write(f"  Claim 99.8% validado: {'✅ SÍ' if comp['claim_99_8_porcentaje_validado'] else '❌ NO'}\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("RESUMEN GENERAL:\n")
        f.write(f"  Ahorro promedio: {reporte_json['resumen']['ahorro_promedio_porcentaje']:.2f}%\n")
        f.write(f"  Ahorro máximo: {reporte_json['resumen']['ahorro_maximo_porcentaje']:.2f}%\n")
        f.write(f"  Claim 99.8% validado: {'✅ SÍ' if reporte_json['resumen']['claim_99_8_validado'] else '❌ NO'}\n")
        f.write("=" * 80 + "\n")
    
    print(f"\n📄 Reporte guardado en:")
    print(f"   JSON: {json_path}")
    print(f"   TXT:  {txt_path}")
    
    return str(txt_path)


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark de consumo de RAM para MASSIVE",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python benchmarks/ram_benchmark.py --scenario small
  python benchmarks/ram_benchmark.py --scenario all
  python benchmarks/ram_benchmark.py --agentes 1000000 --pasos 20
        """
    )
    
    parser.add_argument(
        '--scenario', '-s',
        choices=['small', 'medium', 'large', 'extreme', 'all'],
        help='Escenario predefinido a ejecutar'
    )
    parser.add_argument('--agentes', '-n', type=int, help='Número de agentes (override)')
    parser.add_argument('--pasos', '-p', type=int, help='Número de pasos (override)')
    parser.add_argument('--regla', '-r', type=str, default='lineal', help='Regla de dinámica')
    parser.add_argument('--output', '-o', type=str, default='benchmark_results', help='Directorio de salida')
    
    args = parser.parse_args()
    
    # Cargar escenarios
    config = cargar_escenarios()
    escenarios = config['scenarios']
    
    resultados = []
    
    if args.scenario == 'all' or not args.scenario:
        # Ejecutar todos los escenarios
        for key in ['small', 'medium', 'large']:  # Skip extreme por defecto
            esc = escenarios[key]
            if args.agentes or args.pasos:
                esc = esc.copy()
                if args.agentes:
                    esc['agentes'] = args.agentes
                if args.pasos:
                    esc['pasos'] = args.pasos
            
            try:
                resultado = ejecutar_simulacion_benchmark(
                    agentes=esc['agentes'],
                    pasos=esc['pasos'],
                    regla=esc['configuracion']['regla'],
                    rango_opinion=tuple(esc['configuracion']['rango_opinion']),
                    proveedor_llm=esc['configuracion']['proveedor_llm']
                )
                resultados.append(resultado)
            except Exception as e:
                print(f"⚠️  Error en escenario {key}: {e}")
                continue
    
    elif args.scenario:
        # Ejecutar escenario específico
        esc = escenarios[args.scenario]
        if args.agentes or args.pasos:
            esc = esc.copy()
            if args.agentes:
                esc['agentes'] = args.agentes
            if args.pasos:
                esc['pasos'] = args.pasos
        
        resultado = ejecutar_simulacion_benchmark(
            agentes=esc['agentes'],
            pasos=esc['pasos'],
            regla=esc['configuracion']['regla'],
            rango_opinion=tuple(esc['configuracion']['rango_opinion']),
            proveedor_llm=esc['configuracion']['proveedor_llm']
        )
        resultados.append(resultado)
    
    # Generar reporte
    if resultados:
        reporte_path = generar_reporte(resultados, args.output)
        
        # Imprimir resumen final
        print("\n" + "=" * 80)
        print("BENCHMARK COMPLETADO")
        print("=" * 80)
        
        with open(reporte_path, 'r') as f:
            # Leer últimas líneas del reporte
            lineas = f.readlines()
            print(''.join(lineas[-15:]))
    else:
        print("❌ No se ejecutaron escenarios")
        sys.exit(1)


if __name__ == "__main__":
    main()
