"""
Dynamics Rules - Basic Models

Reglas básicas de dinámica de opiniones:
- regla_lineal: Cambio proporcional suave
- regla_umbral: Salto al cruzar punto crítico
- regla_memoria: Inercia del estado pasado
- regla_backlash: Propaganda refuerza posición contraria
- regla_polarizacion: Aleja la opinión del neutro (cámara de eco)
"""

import numpy as np
from typing import Dict, Any


def regla_lineal(estado: dict, params: dict, cfg: dict) -> dict:
    """
    Regla lineal: cambio proporcional suave.
    
    La opinión cambia proporcionalmente a la diferencia con el promedio ponderado.
    
    Args:
        estado: Estado actual del sistema
        params: Parámetros de la regla
        cfg: Configuración del simulador
        
    Returns:
        Nuevo estado con opiniones actualizadas
    """
    opiniones = estado["opiniones"]
    pesos = estado.get("pesos", np.ones_like(opiniones))
    
    # Calcular promedio ponderado
    promedio = np.average(opiniones, weights=pesos)
    
    # Tasa de cambio (learning rate)
    tasa = params.get("tasa", 0.1)
    
    # Actualizar opiniones: acercamiento al promedio
    nuevas_opiniones = opiniones + tasa * (promedio - opiniones)
    
    return {
        "opiniones": nuevas_opiniones,
        "pesos": pesos,
    }


def regla_umbral(estado: dict, params: dict, cfg: dict) -> dict:
    """
    Regla de umbral: salto al cruzar punto crítico.
    
    Modelo de umbral social: los agentes cambian abruptamente cuando
    la presión social supera un umbral individual.
    
    Args:
        estado: Estado actual del sistema
        params: Parámetros de la regla (umbral, magnitud_salto)
        cfg: Configuración del simulador
        
    Returns:
        Nuevo estado con opiniones actualizadas
    """
    opiniones = estado["opiniones"].copy()
    pesos = estado.get("pesos", np.ones_like(opiniones))
    
    umbral = params.get("umbral", 0.5)
    magnitud_salto = params.get("magnitud_salto", 0.3)
    
    # Calcular presión social (promedio ponderado)
    presion_social = np.average(opiniones, weights=pesos)
    
    # Agentes que cruzan el umbral saltan abruptamente
    mask_cruce = np.abs(opiniones - presion_social) > umbral
    
    # Dirección del salto: hacia o lejos del promedio según configuración
    direccion = params.get("direccion", 1)  # 1=hacia, -1=lejos
    
    opiniones[mask_cruce] += direccion * magnitud_salto * np.sign(presion_social - opiniones[mask_cruce])
    
    # Clip al rango configurado
    from simulator_core.config import opinion_range_clip
    opiniones = np.array([opinion_range_clip(o, cfg) for o in opiniones])
    
    return {
        "opiniones": opiniones,
        "pesos": pesos,
    }


def regla_memoria(estado: dict, params: dict, cfg: dict) -> dict:
    """
    Regla de memoria: inercia del estado pasado.
    
    Las opiniones tienen inercia: resisten el cambio basado en
    su historial reciente.
    
    Args:
        estado: Estado actual del sistema (debe incluir 'historial')
        params: Parámetros de la regla (factor_memoria)
        cfg: Configuración del simulador
        
    Returns:
        Nuevo estado con opiniones actualizadas
    """
    opiniones = estado["opiniones"]
    pesos = estado.get("pesos", np.ones_like(opiniones))
    historial = estado.get("historial", [])
    
    factor_memoria = params.get("factor_memoria", 0.7)
    
    # Calcular influencia del pasado
    if len(historial) > 0:
        opinion_pasada = historial[-1]
        inercia = factor_memoria * opinion_pasada + (1 - factor_memoria) * opiniones
    else:
        inercia = opiniones
    
    # Aplicar dinámica con inercia
    promedio = np.average(opiniones, weights=pesos)
    tasa = params.get("tasa", 0.1)
    
    nuevas_opiniones = inercia + tasa * (promedio - inercia)
    
    return {
        "opiniones": nuevas_opiniones,
        "pesos": pesos,
    }


def regla_backlash(estado: dict, params: dict, cfg: dict) -> dict:
    """
    Regla de backlash: propaganda refuerza posición contraria.
    
    Cuando hay propaganda externa, algunos agentes reaccionan
    moviéndose en dirección opuesta (efecto reactancia).
    
    Args:
        estado: Estado actual del sistema
        params: Parámetros de la regla (intensidad_propaganda, susceptibilidad)
        cfg: Configuración del simulador
        
    Returns:
        Nuevo estado con opiniones actualizadas
    """
    opiniones = estado["opiniones"].copy()
    pesos = estado.get("pesos", np.ones_like(opiniones))
    
    intensidad_propaganda = params.get("intensidad_propaganda", 0.2)
    susceptibilidad = params.get("susceptibilidad", 0.3)
    
    # Dirección de la propaganda (hacia +1 o -1)
    direccion_propaganda = params.get("direccion_propaganda", 1)
    
    # Agentes susceptibles reaccionan en contra
    mask_susceptible = np.random.random(len(opiniones)) < susceptibilidad
    
    # Reactancia: se mueven en dirección opuesta a la propaganda
    opiniones[mask_susceptible] -= intensidad_propaganda * direccion_propaganda
    
    # No susceptibles siguen la dinámica normal
    mask_no_susceptible = ~mask_susceptible
    if np.any(mask_no_susceptible):
        promedio = np.average(opiniones[mask_no_susceptible], weights=pesos[mask_no_susceptible])
        tasa = params.get("tasa", 0.1)
        opiniones[mask_no_susceptible] += tasa * (promedio - opiniones[mask_no_susceptible])
    
    # Clip al rango
    from simulator_core.config import opinion_range_clip
    opiniones = np.array([opinion_range_clip(o, cfg) for o in opiniones])
    
    return {
        "opiniones": opiniones,
        "pesos": pesos,
    }


def regla_polarizacion(estado: dict, params: dict, cfg: dict) -> dict:
    """
    Regla de polarización: aleja la opinión del neutro (cámara de eco).
    
    Las opiniones tienden a extremarse, alejándose del punto neutro.
    Modela efectos de cámara de eco y radicalización.
    
    Args:
        estado: Estado actual del sistema
        params: Parámetros de la regla (factor_polarizacion)
        cfg: Configuración del simulador
        
    Returns:
        Nuevo estado con opiniones actualizadas
    """
    opiniones = estado["opiniones"].copy()
    pesos = estado.get("pesos", np.ones_like(opiniones))
    
    factor_polarizacion = params.get("factor_polarizacion", 0.1)
    
    # Obtener punto neutro del rango
    from simulator_core.config import get_neutro, is_bipolar
    neutro = get_neutro(cfg)
    
    # Polarizar: alejar del neutro
    diferencias = opiniones - neutro
    direcciones = np.sign(diferencias)
    
    # Magnitud de polarización depende de qué tan lejos está del neutro
    magnitudes = np.abs(diferencias)
    nuevas_magnitudes = magnitudes + factor_polarizacion * (1 - magnitudes)
    
    opiniones = neutro + direcciones * nuevas_magnitudes
    
    # Clip al rango
    from simulator_core.config import opinion_range_clip
    opiniones = np.array([opinion_range_clip(o, cfg) for o in opiniones])
    
    return {
        "opiniones": opiniones,
        "pesos": pesos,
    }


__all__ = [
    'regla_lineal',
    'regla_umbral',
    'regla_memoria',
    'regla_backlash',
    'regla_polarizacion',
]
