# MASSIVE Calibration — Data Sourcing Plan (G0-ter)

## Objective

Reach **Tier 2** (≥ 500 observations) from verifiable, citable, license-compatible
sources before attempting per-segment or neural-network calibration. The current
corpus has 169 observations across 12 cases (Tier 1).

## Current State

| Metric | Value |
|---|---|
| Total observations | 169 |
| Cases | 12 |
| Tier | 1 (baselines + aggregate params with strong priors only) |
| `scripts/validate_dataset.py` status | ✅ Passes (exit 0) — all 12 cases declare target_variable |

## Source Plan

| # | Fuente | Tipo | Volumen estimado | Licencia | Coste | Notas |
|---|---|---|---|---|---|---|
| 1 | **Latinobarómetro** (2020, 2022) | Encuesta, 19 países, serie 2016-2023 | ~480 obs | CC BY-NC 4.0 | 0 € | Ideal para pooling; Pew Research replica con 19 países latinoamericanos y europeanos. Series trimestrales de polarización y confianza institucional. |
| 2 | **Eurobarómetro** (75.3, 76.1-76.3, 77.1-77.3) | Encuesta UE | ~120 obs | CC BY 4.0 | 0 € | Series de 1996-2023; pregunta QB7/Q41 sobre polarización. |
| 3 | **Pew Research Global Attitudes** (2016-2023) | Encuesta global | ~90 obs | CC BY 4.0 | 0 € | Series de polarización entre 2016-2023 en 19 países. |
| 4 | **ANES** (2016, 2020, 2024 time-series) | Encuesta electoral | ~60 obs | GPL 3.0 | 0 € | Preguntas de polarización afectiva (feeling thermometers). |
| 5 | **CSES** (Module 1-5) | Encuesta electoral | ~110 obs | CC BY 4.0 | 0 € | Series de 40+ países con preguntas de confianza institucional. |
| 6 | **V-Dem** (v13) | Base de datos de democracia | ~30 obs | CC BY 4.0 | 0 € | Índice de polarización (v2smpol) para 200+ países anualmente. |
| 7 | **World Bank WDI** | Indicadores macro | ~25 obs | CC BY 4.0 | 0 € | Gini, PIB per cápita, desigualdad para contexto sociodemográfico. |
| 8 | **ACLED** (2016-2024) | Datos de protestas/conflictos | ~200 obs | CC BY-NC 4.0 | 0 € | Eventos de protesta con timestamps; mapear a participación. |
| 9 | **GDELT** (GKG 2.0) | Índice masivo de noticias | ~500 obs (submuestreados) | MIT License | 0 € | Variables de emoción y temas para validación de narrativas. |
| 10 | **Kaggle: Reddit / Twitter opinion datasets** | Texto + sentiment | ~200 obs | Varia | 0 € | Datasets académicos anonimizados (verificar cada licencia). |

## Cost and Feasibility Summary

| Fuente | Coste | Esfuerzo (horas) | Observaciones |
|---|---|---|---|
| Latinobarómetro | 0 € | 3 | Registro gratuito, CSV descargable |
| Eurobarómetro | 0 € | 2 | Registro gratuito, código R disponible |
| Pew Research | 0 € | 2 | Registro gratuito, SPSS/Stata |
| ANES | 0 € | 3 | Registro requerido, grandes archivos |
| CSES | 0 € | 2 | Registro gratuito, formato estandarizado |
| V-Dem | 0 € | 1 | API directa o CSV |
| World Bank | 0 € | 1 | API directa |
| ACLED | 0 € | 4 | Registro gratuito, API con rate limits |
| GDELT | 0 € | 2 | Descarga directa, archivos grandes |
| Kaggle datasets | 0 € | 3 | Verificar licencia caso por caso |

## Capacity Progression Plan

| Tier | Observaciones mínimas | Permite | Status |
|---|---|---|---|
| Tier 1 | < 500 | Baselines + aggregate params (σ, ε, λ) with strong priors | ✅ Current (169 obs) |
| Tier 2 | 500-2000 | Per-scenario params + simple ensemble | ⏳ Target (plan: +480 from Latinobarómetro) |
| Tier 3 | 2000+ | Per-segment calibration + neural correctors | 🔒 Blocked until Tier 2 |

## Path to Tier 2

1. **Latinobarómetro 2022** — ~600 respuestas con preguntas de polarización. Adding 480 observations would reach Tier 2.
2. **Eurobarómetro 77.1** — ~27,000 respuestas con índice de polarización QB7. Subsample to 200 observations for representation diversity.
3. **ACLED** — 200 eventos de protesta con timestamps. Mapped to participation rate via binomial sampling.

Total target: 500+ new observations from 4 verifiable sources → Tier 2.

## References

- Latinobarómetro: https://www.latinobarometro.org/ (CC BY-NC 4.0)
- Eurobarómetro: https://ec.europa.eu/commfrontoffice/publicdataserver (CC BY 4.0)
- Pew Research: https://www.pewresearch.org/global/ (CC BY 4.0)
- ANES: https://electionstudies.org/ (GPL 3.0)
- CSES: https://www.cses.org/ (CC BY 4.0)
- V-Dem: https://www.v-dem.net/ (CC BY 4.0)
- World Bank: https://datatopics.worldbank.org/ (CC BY 4.0)
- ACLED: https://acleddata.com/ (CC BY-NC 4.0)
- GDELT: https://www.gdeltproject.org/ (MIT License)
