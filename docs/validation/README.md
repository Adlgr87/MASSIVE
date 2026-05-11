# Validation — PVU-BS / Validación

> **EN:** This folder contains the MASSIVE Protocol of Validated Use (PVU-BS) in both languages, plus pre-registration and report templates.  
> **ES:** Esta carpeta contiene el Protocolo de Uso Validado de MASSIVE (PVU-BS) en ambos idiomas, junto con plantillas de pre-registro y reporte.

---

## Documents / Documentos

| Document / Documento | English | Español |
|----------------------|---------|---------|
| PVU Protocol | [PVU_BeyondSight_EN.md](PVU_BeyondSight_EN.md) | [PVU_BeyondSight_ES.md](PVU_BeyondSight_ES.md) |
| Pre-registration template | [preregistration_template_EN.md](preregistration_template_EN.md) | [preregistration_template_ES.md](preregistration_template_ES.md) |
| Validation report template | [validation_report_template_EN.md](validation_report_template_EN.md) | [validation_report_template_ES.md](validation_report_template_ES.md) |

---

## Quick Start / Inicio Rápido

```bash
# Run the offline benchmark (no API key needed):
PYTHONHASHSEED=42 python -m benchmarks.runner \
    --cases datasets/pvu_cases \
    --offline \
    --out reports/validation/ci \
    --seed 42
```

Results are saved to `reports/validation/ci/`:
- `metrics.json` — per-case metrics
- `report.md`    — human-readable summary

---

## Sample vs Real Validation / Casos de Muestra vs Validación Real

> ⚠️ **EN:** The `datasets/pvu_cases/sample_case_*` folders contain **synthetic** data.  
> They are provided only to verify the pipeline works. No scientific claims may be drawn from them.  
> Real PVU validation requires **N ≥ 10 independent real-world cases** (see PVU § 2.1).

> ⚠️ **ES:** Las carpetas `datasets/pvu_cases/sample_case_*` contienen datos **sintéticos**.  
> Existen solo para verificar que el pipeline funciona. No se pueden derivar afirmaciones científicas de ellas.  
> La validación PVU real requiere **N ≥ 10 casos del mundo real independientes** (ver PVU § 2.1).
