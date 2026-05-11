# Contributing to MASSIVE 🌊

First off, thank you for considering contributing to MASSIVE! It's people like you that make MASSIVE such a great tool for understanding and simulating social dynamics.

## 1. How you can help
We welcome contributions in various forms:
- **Mathematical Models:** Submitting new deterministic or stochastic rules for social cascades.
- **LLM Integrations:** Testing and providing support for new Large Language Model APIs via OpenRouter, Anthropic, etc.
- **Visuals:** Creating new algorithms for `visualizations.py` to support 3D interactions.
- **Bug Reporting & Docs:** Reporting issues and fixing typos or i18n bugs.
- **PVU Validation Cases:** Adding new real-world PVU cases to `datasets/pvu_cases/` following the schema in [docs/validation/PVU_BeyondSight_EN.md](docs/validation/PVU_BeyondSight_EN.md).

## 2. Setting up your environment
1. Fork the repo and clone it locally.
2. Create a virtual environment (`python -m venv venv`) and activate it.
3. Run `pip install -r requirements.txt`.
4. Copy `.env.example` to `.env` and configure your API Keys.
5. Create a new branch: `git checkout -b feature/your-feature-name`.

## 3. Running tests
```bash
# Run the full test suite:
python -m pytest tests/

# Run only PVU runner tests:
python -m pytest tests/test_pvu_runner.py -v

# Run the offline benchmark:
PYTHONHASHSEED=42 python -m benchmarks.runner \
    --cases datasets/pvu_cases --offline \
    --out reports/validation/ci --seed 42
```

## 4. PVU Validation Cases

To contribute a new PVU case:

1. Create a sub-folder under `datasets/pvu_cases/` (e.g. `case_003/`).
2. Add the required files:
   - `timeseries.csv` — columns: `date` (ISO 8601), `P` (float [0,1]), optional extras.
   - `interventions.json` — list of `{date, label, source}`.
   - `meta.json` — with `case_id`, `domain`, `source`, `cluster_id`, `license`, `note`.
3. Verify the case loads: `python -m benchmarks.runner --cases datasets/pvu_cases --offline --out /tmp/pvu_test`.
4. If the data is real (not synthetic), ensure it is appropriately licensed and anonymised.

> ⚠️ **Anti-leakage reminder:** Pre-register your analysis plan **before** running the benchmark on real data (use `docs/validation/preregistration_template_EN.md`).

## 5. Pull Request Process
- Ensure any install or build dependencies are removed before the end of the layer when doing a build.
- Update the `README.md` and `README_ES.md` with details of changes to the interface, this includes new environment variables, exposed ports, useful file locations and container parameters.
- Provide a clear PR description outlining the mathematical logic if adding a new rule.

Happy simulating!

