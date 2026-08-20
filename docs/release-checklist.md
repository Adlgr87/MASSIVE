# Checklist de release — MASSIVE

> Ejecutar completamente antes de publicar una versión. Revisado 2026-08-20.

## Pre-condiciones

- [ ] `main` verde: los 12 workflows de CI en success (`gh run list --branch main`).
- [ ] Suite completa local: `python -m pytest tests/ -q` → 0 failed, 0 errores de colección.
- [ ] `ruff check .` y `black --check .` → limpios.
- [ ] `python scripts/typecheck_slice.py` → 0 errores.
- [ ] `cd frontend && npm ci && npm run build` → exitoso.
- [ ] Docker: `docker compose -f docker-compose.single.yml up -d --build` + `/health` 200 + `/ready` 200 (con claves configuradas).
- [ ] `pip-audit -r requirements.txt` → sin vulnerabilidades críticas/altas (o aceptación de riesgo documentada en `docs/production-readiness-audit.md`).
- [ ] gitleaks/secret scan verde; sin secretos nuevos.
- [ ] CHANGELOG.md actualizado (Keep a Changelog).
- [ ] Versiones bumpadas: `pyproject.toml` (+ frontend si cambia contrato).

## Contrato y compatibilidad

- [ ] Si cambian DTOs `/v1`: regenerar `frontend/src/types/api.generated.ts` (`python scripts/gen_ts_types.py`) y verificar workflow `validate_ts_types`.
- [ ] Si cambia `configs/llm_contract/*.json`: bump de versión del contrato + nota en CHANGELOG.
- [ ] Tests de caracterización de motores verdes (sin deriva numérica fuera de tolerancia).

## Publicación

- [ ] Tag semver anotado: `git tag -a vX.Y.Z -m "..." && git push origin vX.Y.Z`.
- [ ] GitHub Release con notas (= sección de CHANGELOG).
- [ ] Verificar workflows de publish (PyPI/Docker Hub) — requieren secrets del owner.
- [ ] Desplegar a staging y repetir smoke antes de producción.

## Rollback

- [ ] Procedimiento validado: `docs/runbooks/operations.md` §5 (stateless; revert de tag + rebuild).

## Post-release

- [ ] Monitorear logs 30 min (`WARNING`/`ERROR` inesperados).
- [ ] Cerrar hallazgos del audit asociados; actualizar matriz en `docs/production-readiness-audit.md`.
