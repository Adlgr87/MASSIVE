import os
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
# Forzar cwd (raíz UI-NG) como path[0] para que `backend` importe;
# pytest collection normalmente reemplaza sys.path[0] con el dir del test,
# así que usamos el string relativo '.' que pytest no puede expulsar.
if "." not in sys.path:
    sys.path.insert(0, os.getcwd())

_MASSIVE_ROOT = os.environ.get("MASSIVE_ROOT", "/home/adlg/Escritorio/Proyectos/MASSIVE")
if _MASSIVE_ROOT and Path(_MASSIVE_ROOT).is_dir():
    _MASSIVE_ROOT = str(_MASSIVE_ROOT)
    if _MASSIVE_ROOT not in sys.path:
        sys.path.insert(0, _MASSIVE_ROOT)


def pytest_configure(config):
    sys.path.insert(0, os.getcwd())
    sys.path.insert(0, str(_ROOT))
    if _MASSIVE_ROOT and _MASSIVE_ROOT not in sys.path:
        sys.path.insert(0, _MASSIVE_ROOT)
