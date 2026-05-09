#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

INSTALL_QISKIT=false
if [[ "${1:-}" == "--with-qiskit" ]]; then
  INSTALL_QISKIT=true
fi

echo "[setup_quantum] Instalando dependencias base..."
pip install numpy scipy numba

if [[ "$INSTALL_QISKIT" == "true" ]]; then
  echo "[setup_quantum] Instalando stack cuántico opcional (qiskit + aer)..."
  pip install qiskit qiskit-aer
else
  echo "[setup_quantum] Omitiendo Qiskit (usa --with-qiskit para activarlo)."
fi

python - <<'PY'
from pathlib import Path

root = Path('.')

social_path = root / 'social_architect.py'
multilayer_path = root / 'multilayer_engine.py'

social = social_path.read_text(encoding='utf-8')
if 'from quantum.integration import quantum_optimize_interventions' not in social:
    social = social.replace(
        'from simulator import run_with_schedule, resumen_historial, DEFAULT_CONFIG\n',
        'from simulator import run_with_schedule, resumen_historial, DEFAULT_CONFIG\n'
        'from quantum.integration import quantum_optimize_interventions\n',
    )

if 'def find_optimal_interventions(' not in social:
    social += (
        '\n\n'
        'def find_optimal_interventions(evaluate_fn, n_agents, n_phases, max_iter=100):\n'
        '    """Drop-in replacement para optimización de intervenciones."""\n'
        '    return quantum_optimize_interventions(\n'
        '        evaluate_fn=evaluate_fn,\n'
        '        n_agents=n_agents,\n'
        '        n_phases=n_phases,\n'
        '        max_iter=max_iter,\n'
        '    )\n'
    )
social_path.write_text(social, encoding='utf-8')

multi = multilayer_path.read_text(encoding='utf-8')
if 'from quantum.integration import compress_agent_states, decompress_agent_states' not in multi:
    multi = multi.replace(
        'import networkx as nx\n',
        'import networkx as nx\nfrom quantum.integration import compress_agent_states, decompress_agent_states\n',
    )

if 'self.mps_state = None' not in multi:
    multi = multi.replace(
        '        self._history: list[np.ndarray] = [self.x.copy()]\n',
        '        self._history: list[np.ndarray] = [self.x.copy()]\n'
        '        self.mps_state = None\n',
    )

if 'def update_opinions(self, new_opinions: np.ndarray) -> None:' not in multi:
    marker = '    def behavior_correlation_matrix(self) -> np.ndarray:\n'
    methods = (
        '    def update_opinions(self, new_opinions: np.ndarray) -> None:\n'
        '        """Actualiza el estado del motor y comprime opcionalmente en MPS."""\n'
        '        arr = np.asarray(new_opinions, dtype=np.float64)\n'
        '        if arr.shape != (self.N, K):\n'
        '            raise ValueError(f"new_opinions debe tener forma ({self.N}, {K})")\n'
        '        arr[:, COL_OPINION] = np.clip(arr[:, COL_OPINION], self.x_min, self.x_max)\n'
        '        arr[:, 1:] = np.clip(arr[:, 1:], 0.0, 1.0)\n'
        '        self.x = arr\n'
        '        self._history.append(self.x.copy())\n'
        '        self.mps_state = compress_agent_states(arr) if self.N > 1000 else None\n\n'
        '    def get_opinions(self) -> np.ndarray:\n'
        '        """Devuelve el estado actual (descomprimiendo MPS cuando aplique)."""\n'
        '        if self.mps_state is not None:\n'
        '            return decompress_agent_states(self.mps_state)\n'
        '        return self.x\n\n'
    )
    multi = multi.replace(marker, methods + marker)

multilayer_path.write_text(multi, encoding='utf-8')
print('[setup_quantum] Integración de código aplicada.')
PY

echo "[setup_quantum] Ejecutando tests cuánticos..."
python -m pytest tests/test_quantum.py -v

echo "[setup_quantum] Listo ✅"
