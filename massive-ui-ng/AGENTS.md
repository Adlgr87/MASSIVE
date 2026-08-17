# AGENTS.md — MASSIVE UI-NG (Next-Gen UI)

## Project location
- Local: `/home/adlg/Escritorio/Proyectos/MASSIVE_UI/massive-ui-ng-package`
- Git repo root: **same dir** (independent repo, `main` branch)
- GitHub remote configured in `.git/config`:
  - `origin -> https://github.com/Adlgr87/MASSIVE_UI.git`
  - ⚠️ **IMPORTANT**: That GitHub repo returned 404 Not Found on `git fetch`.
    The real upstream is `https://github.com/Adlgr87/MASSIVE` (the simulator).
    UI-NG depends on `massive_core` from the MASSIVE repo on PYTHONPATH.

## Cross-repo dependency
- `massive_core` — located at `/home/adlg/Escritorio/Proyectos/MASSIVE/massive_core`
- Must be importable: set `MASSIVE_ROOT=/home/adlg/Escritorio/Proyectos/MASSIVE` OR add it to `PYTHONPATH`.
- `backend/app/main.py` inserts MASSIVE_ROOT into sys.path at runtime, but pytest
  collection happens *before* main.py runs, so the root `conftest.py` must do it.

## Pytest layout (known pitfall)
- rootdir == UI-NG package root (`conftest.py` lives here).
- pytest collection replaces `sys.path[0]` with the test file's dir (`tests/`),
  which hides the `backend/` package. Solution: use `pytest_configure` hook to
  re-insert `os.getcwd()` + repo root; do NOT rely on `tests/conftest.py` being
  loaded before import. `pytest_configure` is robust across collection modes.

## Run tests
```
cd /home/adlg/Escritorio/Proyectos/MASSIVE_UI/massive-ui-ng-package
MASSIVE_ROOT=/home/adlg/Escritorio/Proyectos/MASSIVE python -m pytest tests/ -q
```

## Git workflow note
- After cloning, run `git init` here and set remote origin to the correct repo.
- Push to GitHub requires either (a) user creates `Adlgr87/MASSIVE_UI` repo, or
  (b) point this repo's origin at `Adlgr87/MASSIVE`. Ask before changing remote.
