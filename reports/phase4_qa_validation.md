# Phase 4 — Validation & QA Report (MASSIVE v2)

## Context
Validation of the Master Orchestrator workflow (4-agent team) executed against the MASSIVE repository. This Phase 4 report validates the **Phase 3 v2 fixes** applied to close the critical issues identified by the agent audit.

## Scope of changes (Phase 3 v2 — this session)

| # | Fix | File(s) | Lines | Finding ref |
|---|-----|---------|-------|-------------|
| 1 | Dispatcher: multilayer_engine → run_multilayer_simulation() | `services/llm_orchestrator.py` | 333-362 | CRIT-1 |
| 2 | Dispatcher: massive_engine → run_massive_sim() | `services/llm_orchestrator.py` | 364-399 | CRIT-1 |
| 3 | Dispatcher: factbook_validation explicit motor key | `services/llm_orchestrator.py` | 401-422 | CRIT-1 |
| 4 | micro_massive: stub redirect → real MicroOrchestrator API | `services/llm_orchestrator.py` | 479-505 | CRIT-2 |
| 5 | nginx: remove streamlit_backend + /ui/ location | `nginx.conf` | 26-28, 67-77 | CRIT-2 |
| 6 | supervisord.conf: remove [program:streamlit] | `supervisord.conf` | 27-39 | CRIT-2 |
| 7 | llm_contract.json: remove 'endpoint: Streamlit /ui/' | `configs/llm_contract/massive_llm_contract.json` | 386 | CRIT-2 |
| 8 | LLM_PROMPTS.md: micro_massive → POST /v1/simulate | `docs/LLM_PROMPTS.md` | 30 | CRIT-2 |
| 9 | PRODUCTION_ARCHITECTURE_SPEC.md: remove /ui/ route | `PRODUCTION_ARCHITECTURE_SPEC.md` | 340 | CRIT-2 |
| 10 | README: '50% direction error' → '~27% RMSE reduction' | `README.md` | 31 | Scientific honesty |
| 11 | Timeline compatibility for multilayer/massive history | `services/llm_orchestrator.py` | 353-361, 383-399 | CRIT-1 compat |
| 17 | CLI `scientific` + `forecast` subcommands | `massive/cli/main.py` | — | (Arquitecto) |
| 18 | Dead code: `micro_engine.py:94` income feature | `micro_engine.py` | 94 | (Científico) |
| 19 | Dead code: `energy_engine.py:376-377` | `energy_engine.py` | 379-381 | (Científico) |
| 20 | Dead code: `micro_engine.py:689` std_feats | `micro_engine.py` | 689-690 | (Científico) |

## Test results

```
PYTHONHASHSEED=42 .venv/bin/python -m pytest tests/ -p no:cacheprovider
592 passed, 20 skipped, 1 warning in 23.84s
```

### Component-level validation

| Component | Tests | Result |
|-----------|-------|--------|
| LLM endpoint dispatch (multilayer/massive/micro) | 23 | ✅ Pass |
| LLM orchestrator coverage | 6 | ✅ Pass |
| Full test suite | 592 | ✅ Pass (20 skipped) |

### Targeted functional verification

| Check | Method | Result |
|-------|--------|--------|
| MultilayerEngine dispatch | `_post(client, {"intent": "Simula la dinámica..."})` → `run_multilayer_simulation()` | ✅ Returns `multilayer_engine` + timeline |
| MassiveEngine dispatch | `run_llm_simulation(motor="massive_engine")` | ✅ Returns `massive_engine` + real trajectory |
| MicroOrchestrator dispatch | `run_llm_simulation(motor="micro_massive")` | ✅ Returns real `history`, no /ui/ redirect |
| Factbook dispatch | `factbook_validation` intent → `run_scalar_simulation` | ✅ Explicit motor key |
| Streamlit dead-end cleanup | `grep -rn 'Streamlit.*ui/' services/ configs/ docs/` | ✅ No active redirects remain |
| Scientific honesty | README vs calibration_log.md RMSE | ✅ 27% documented, not 50% |

## Devil's Advocate findings — resolution status

| Finding | Severity | Resolution |
|---------|----------|------------|
| F1: NaN propagation in JIT | 🔴 Critical | ✅ Fixed (NaN guard via `val != val` check) |
| F9: Event-driven deadlock | 🔴 Critical | ✅ Fixed (liveness guard, opt-in via `run()`) |
| F11: Dask seed bug | 🔴 High | ✅ Fixed (per-replica `run_cfg` with unique seed) |
| F14: JIT warm-up shape mismatch | 🔴 High | ✅ Fixed (2D `_xt` passed to both functions) |
| F16: Upload DoS (read before size check) | 🔴 Critical | ✅ Fixed (streaming chunk-read + Content-Length pre-check) |
| F22: `random_network` O(N²) = 8TB OOM | 🔴 Critical | ✅ Fixed (cap at 50K, error directs to MassiveEngine LOD) |
| F23: Unbounded `max_intentos` | 🔴 Critical | ✅ Fixed (clamped to max 10) |
| F19: API keys in logs | 🟢 Low | ⚠️ Deferred (no API keys in traceback paths in current code path) |
| F20: No X-Forwarded-For parsing | 🔴 High | ⚠️ Mitigation: nginx `set_real_ip_from` + `real_ip_header` (see nginx.conf) |
| F21: Full opinions in response | 🟠 Medium | ⚠️ Deferred — API contract depends on frontend types |

## Outstanding (Devil's Advocate findings not fixed this sprint)

| Finding | Reason deferred |
|---------|-----------------|
| F2: NaN survives uint8 quantization (`massive_engine.py:258`) | Requires `quantize_state` to detect/skip NaN — behavioral change risking bit-equality tests |
| F3: Negative eta → sqrt(NaN) | `energy_runner` already clips eta to [0.001, 0.1]; direct `step()` calls unguarded by design (caller responsibility) |
| F4: `_validar_params` ignores NaN/inf | Would require adding `math.isfinite` checks across all 13 rules — larger change |
| F5: std=0 division in `regla_umbral_heterogeneo` | Same root cause as F4; scheduled for FASE-5b param validation |
| F6: Replicator NaN payoff | Strategic layer disabled by default; validation in scientific runner |
| F7: Missing Factbook country silently defaults | Requires raising vs. falling back — BC concern |
| F8: HK total fragmentation | Algorithmic redesign of fallback; deferred to v0.3 |
| F10: Rate limiter memory leak | Needs periodic cleanup task; informational per spec |
| F12: Global circuit breaker | Per-provider isolation scheduled for v0.3 |
| F13: FileRateLimiter Windows race | Linux-only production deployment |
| F15: GPU noise unseeded (CuPy global RNG) | GPU not available in CI; tracked in benchmark suite |
| F17: LLM injection in social_architect | Requires JSON schema validation of LLM responses — larger project |
| F18: `_extraer_json` no schema validation | Same as F17 |
| F24: Dense Langevin O(N²) JIT kernel | Sparse path already exists; routing logic deferred |
| F25: `generate_hierarchical` O(hubs²) | Topology generator optimization deferred |
| F26-F30: UX issues (KeyError, swallowed errors, etc.) | Frontend is a stub; scheduled with Phase 3 UI work |

## Conclusion
The 5 CRÍTICOs (F16, F22, F23, F9, F11) from the Devil's Advocate audit — the "kill switches" — are **fixed and verified**. The architectural tensions (route mismatch, Streamlit Docker, nginx :80, JIT cold-start, MC event-loop blocking) are **resolved**. All 592 existing tests pass.