#!/bin/bash
# FASE 1 — Entorno base reproducible para benchmarks MASSIVE
# Source: source experiments/configs/env_base.sh

export PYTHONHASHSEED=42
export MASSIVE_LLM_PROVIDER=heuristico
export MASSIVE_BENCHMARK_MODE=true
export PYTHONPATH="/home/adlg/Escritorio/Proyectos/MASSIVE:${PYTHONPATH:-}"

# Python hash seed must be set BEFORE interpreter starts
echo "✅ Entorno MASSIVE configurado:"
echo "   PYTHONHASHSEED=$PYTHONHASHSEED"
echo "   MASSIVE_LLM_PROVIDER=$MASSIVE_LLM_PROVIDER"
echo "   MASSIVE_BENCHMARK_MODE=$MASSIVE_BENCHMARK_MODE"
echo "   PYTHONPATH=$PYTHONPATH"
