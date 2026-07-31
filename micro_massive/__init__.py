"""
micro_massive — Simulación de dinámicas en grupos pequeños (3-15 agentes).

Tres pilares:
  1. Personalidades (Efecto Forer) — arquetipos psicológicos
  2. Matriz de influencia — contagio de opinión/emociones
  3. Teoría de juegos evolutiva — estrategias adaptativas
"""

from micro_massive.core.orchestrator import MicroOrchestrator
from micro_massive.utils.forer import ForerPersonalityGenerator
from micro_massive.utils.metrics import GroupMetrics

__all__ = ["MicroOrchestrator", "ForerPersonalityGenerator", "GroupMetrics"]
