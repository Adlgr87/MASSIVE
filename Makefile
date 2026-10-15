# MASSIVE — developer workflow targets
# All targets verified from a clean clone (docs/runbooks/local-development.md).

PYTHON ?= python3
VENV ?= .venv
BIN := $(VENV)/bin

.PHONY: help install test test-cov lint format typecheck api api-legacy \
        verify verify-baseline cli-verify frontend-install frontend-dev \
        frontend-build benchmark benchmark-all baselines backtests \
        validate-cfc clean

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

install: ## Create venv and install all dependencies (requirements.txt)
	$(PYTHON) -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r requirements.txt
	@$(BIN)/pip install -e . 2>/dev/null || true
	@echo "Activate with: source $(VENV)/bin/activate"

test: ## Run the full test suite
	$(BIN)/python -m pytest tests/ -q

test-cov: ## Run tests with coverage report
	$(BIN)/python -m pytest tests/ -q --cov --cov-report=term-missing

lint: ## ruff + black --check
	$(BIN)/ruff check .
	$(BIN)/black --check .

format: ## Apply ruff --fix + black
	$(BIN)/ruff check . --fix
	$(BIN)/black .

typecheck: ## Gradual mypy slice
	$(BIN)/python scripts/typecheck_slice.py

verify: ## Full verification harness (lint, types, tests, docs, G-1 guardrails)
	$(PYTHON) scripts/verify_harness.py

verify-baseline: ## Snapshot audit baseline -> reports/audit_baseline.json
	$(PYTHON) scripts/verify_harness.py --baseline

api: ## Start canonical /v1 API on :8000
	$(BIN)/uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

api-legacy: ## Start legacy /api API on :8000 (used by frontend/)
	$(BIN)/uvicorn api:app --host 0.0.0.0 --port 8000

frontend-install: ## Install frontend deps
	cd frontend && npm ci

frontend-dev: ## Vite dev server on :3000 (proxies /api -> :8000)
	cd frontend && npm run dev

frontend-build: ## Production build of frontend/
	cd frontend && npm run build

baselines: ## Run G0 baselines (6 baselines x 12 cases, walk-forward)
	PYTHONHASHSEED=42 $(BIN)/python scripts/run_baselines.py --cases 12

backtests: ## Run G4 blind backtests (day-0 conditions)
	PYTHONHASHSEED=42 $(BIN)/python scripts/run_backtests.py

validate-cfc: ## Walk-forward validation of CfC corrector (audit)
	PYTHONHASHSEED=42 $(BIN)/python scripts/validate_cfc_walkforward.py

benchmark: ## PVU-MASSIVE offline validation benchmark
	PYTHONHASHSEED=42 $(BIN)/python -m benchmarks.runner \
		--cases datasets/pvu_cases --offline --out reports/validation/local --seed 42

benchmark-all: ## Run full reproducible benchmark suite (baselines + backtests + cfc + benchmark)
	@echo "=== FASE 4: Full reproducible benchmark suite ==="
	@echo "--- [1/4] G0 Baselines ---"
	PYTHONHASHSEED=42 $(BIN)/python scripts/run_baselines.py --cases 12
	@echo "--- [2/4] G4 Backtests ---"
	PYTHONHASHSEED=42 $(BIN)/python scripts/run_backtests.py
	@echo "--- [3/4] CFC Walk-Forward Validation ---"
	PYTHONHASHSEED=42 $(BIN)/python scripts/validate_cfc_walkforward.py
	@echo "--- [4/4] PVU-MASSIVE Offline Benchmark ---"
	PYTHONHASHSEED=42 $(BIN)/python -m benchmarks.runner \
		--cases datasets/pvu_cases --offline --out reports/validation/local --seed 42
	@echo "=== Benchmark suite complete ==="

clean: ## Remove caches and build artifacts
	rm -rf .pytest_cache .mypy_cache .coverage htmlcov frontend/dist
	find . -type d -name __pycache__ -not -path "./.git/*" -exec rm -rf {} +
