# Validation — PVU-BS / Validación

> **EN:** This folder contains the MASSIVE Protocol of Validated Use (PVU-BS) in both languages, plus pre-registration and report templates.  
> **ES:** Esta carpeta contiene el Protocolo de Uso Validado de MASSIVE (PVU-BS) en ambos idiomas, junto con plantillas de pre-registro y reporte.

---

## Documents / Documentos

| Document / Documento | English | Español |
|----------------------|---------|---------|
| PVU Protocol | [PVU_MASSIVE_EN.md](PVU_MASSIVE_EN.md) | [PVU_MASSIVE_ES.md](PVU_MASSIVE_ES.md) |
| Pre-registration template | [preregistration_template_EN.md](preregistration_template_EN.md) | [preregistration_template_ES.md](preregistration_template_ES.md) |
| Validation report template | [validation_report_template_EN.md](validation_report_template_EN.md) | [validation_report_template_ES.md](validation_report_template_ES.md) |
| Data sourcing plan | [DATA_SOURCES.md](DATA_SOURCES.md) | |
| Agent team prompt | [PROMPT_CALIBRACION_EQUIPO_AGENTES.md](PROMPT_CALIBRACION_EQUIPO_AGENTES.md) ||

---

## Quick Start / Inicio Rápido

```bash
# 1. Validate dataset (all 12 cases must pass):
python scripts/validate_dataset.py

# 2. Run baselines on all 12 cases (G0-quarter):
python scripts/run_baselines.py

# 3. Run historical backtests (G4, pre-registered):
python scripts/run_backtests.py

# 4. Validate CfC walk-forward (arena rule check):
python scripts/validate_cfc_walkforward.py

# 5. Full test suite:
pytest tests/ -q
```

Results are saved to `reports/`:
- `baselines_12cases.json` — per-case baseline metrics
- `backtest_results.json` — per-case backtest gate results
- `cfc_validation.json` — CfC disqualification evidence
- `audit_baseline.json` — baseline audit report

---

## Sample vs Real Validation / Casos de Muestra vs Validación Real

> ⚠️ **EN:** The `datasets/pvu_cases/sample_case_*` folders contain **synthetic** test data.  
> They are provided only to verify the pipeline works. No scientific claims may be drawn from them.  
> Real PVU validation requires **N ≥ 10 independent real-world cases** (see PVU § 2.1).  
> The 12 real historical cases in `datasets/real_cases/` satisfy this requirement.

> ⚠️ **ES:** Las carpetas `datasets/pvu_cases/sample_case_*` contienen datos de **prueba sintéticos**.  
> Existen solo para verificar que el pipeline funciona. No se pueden derivar afirmaciones científicas de ellas.  
> La validación PVU real requiere **N ≥ 10 casos del mundo real independientes** (ver PVU § 2.1).  
> Los 12 casos históricos reales en `datasets/real_cases/` satisfacen este requisito.
