# Coupling matrix — how the state variables influence each other

This is the reference for *what drives what* in the multilayer engine, and the
place to look before changing `multilayer_engine.py`. The code is the source of
truth (`DEFAULT_COUPLING_GAINS` + `COUPLING_RATIONALE`), and
`tests/test_coupling_structure.py` enforces every property described here.

## The state vector

`K = 5`, one row per agent:

| idx | variable | range | meaning |
|---|---|---|---|
| 0 | `opinion` | [-1, 1] | ideological position |
| 1 | `cooperation` | [0, 1] | willingness to cooperate |
| 2 | `hierarchy` | [0, 1] | recognition of authority (0 rebel, 1 conformist) |
| 3 | `income` | [0, 1] | normalised income |
| 4 | `info_access` | [0, 1] | access to information |

Dynamics: `dx_i/dt = -∇U(x_i) + Σ_ℓ w_ℓ (A_ℓ · x)_i · σ + θ(a_i)·η_i`

## The declared matrix

Every cross-variable link is declared in `DEFAULT_COUPLING_GAINS` with a cited
mechanism in `COUPLING_RATIONALE`. Nothing outside that table couples two
variables.

| source → target | gain | mechanism | direction |
|---|---:|---|---|
| `opinion` → `cooperation` | +0.40 | social alignment: position fixes cooperation level | together |
| `hierarchy` → `cooperation` | +0.30 | conformity / legitimacy (Almond & Verba) | together |
| `hierarchy` → `income` | +0.40 | stratification: recognised hierarchy concentrates income | together |
| `cooperation` → `info_access` | +0.20 | civic engagement (Putnam, social capital) | together |
| `income` → `info_access` | +0.30 | digital divide (van Dijk, 2005) | together |
| `info_access` → `opinion` | +0.50 | selective exposure: more information widens the wells (Sunstein 2001, Prior 2007) | state-dependent — amplifies whichever side the agent is on |

**Density: 6 of 20 possible pairs (30%).** Sign convention: gain > 0 ⇒ both move
together; gain < 0 ⇒ they move in opposite directions. All six declared terms
happen to be non-negative; the *machinery* supports negative gains, and
`test_negative_gain_flips_the_relationship` proves it by inverting
`hierarchy → income`.

The graph closes a cycle: `opinion → cooperation → info_access → opinion`. That
matters — without a cycle the model is a feed-forward chain and 4 of the 5
variables influence nothing.

## Self-dynamics (not part of the matrix)

| variable | attractor |
|---|---|
| `opinion` | double well at `±well`, where `well = clip(0.7 + g·(info−0.5), 0.35, 0.85)` |
| `cooperation` | `0.4 + 0.4·opinion + 0.3·(hierarchy − 0.5)` |
| `hierarchy` | bistable at 0 (rebel) and 1 (conformist), unstable at 0.5 |
| `income` | `0.5 + 0.4·(hierarchy − 0.5)` |
| `info_access` | `0.5 + 0.2·cooperation + 0.3·(income − 0.5)` |

`info_access → opinion` shifts the **well position** rather than applying a linear
push. That is the correct reading of the filter-bubble effect on a bimodal
potential, and it is what gives the model a usable response range (wells between
±0.35 and ±0.85) instead of a 1 % nudge.

## Network influence

The social layers act on **all five** dimensions, with per-variable
susceptibility (`NETWORK_SUSCEPTIBILITY`):

| variable | susceptibility | why |
|---|---:|---|
| `opinion` | 1.00 | opinion is fully contagious |
| `cooperation` | 0.30 | conditional cooperation |
| `hierarchy` | 0.20 | authority recognition is partly social |
| `income` | 0.10 | income does not spread by social contact |
| `info_access` | 0.15 | some social diffusion of information |

Values stay below the amplification threshold: the network term contributes
`coupling · susceptibility`, which must stay well under each variable's relaxation
rate (0.3 for `info_access`, 2.0 for `cooperation`). At susceptibility 0.4 for
`info_access` with `coupling = 0.3` the ratio was 0.12/0.3 = 0.4, which biased
`info_access` until it saturated the clip.

One sparse matmul covers all `K` columns per layer — not `K` separate matvecs.

## Measured response surface

N=400, 400 steps, seed 42:

| configuration | polarization | cooperation | income sd | hierarchy sd | info |
|---|---:|---:|---:|---:|---:|
| baseline (6 terms, `coupling` 0.3) | 0.7696 | 0.4834 | **0.1985** | 0.4432 | **0.6773** |
| selective-exposure gain = 0.0 | 0.6909 | 0.4763 | 0.1985 | 0.4432 | 0.6767 |
| selective-exposure gain = 0.75 | 0.7820 | 0.4814 | 0.1985 | 0.4432 | 0.6769 |
| `coupling` = 0.0 | 0.7249 | 0.4282 | 0.2088 | 0.4511 | 0.5688 |
| `coupling` = 1.0 | 0.8408 | 0.6398 | 0.1324 | 0.2914 | 0.9108 |
| **all couplings ablated** | 0.6909 | 0.4202 | **0.0885** | 0.4432 | **0.5659** |

The last row is the regression witness: ablating the six terms reproduces the old
model's pathology exactly — `income` dies again (sd 0.1985 → 0.0885) and
`info_access` stops being coupled.

## Ablating a term

From Python:

```python
from multilayer_engine import DEFAULT_COUPLING_GAINS, MultilayerEngine

gains = dict(DEFAULT_COUPLING_GAINS)
gains.pop(("info_access", "opinion"))          # remove the feedback loop
engine = MultilayerEngine(N=400, coupling_gains=gains)
```

Over HTTP:

```bash
curl -X POST localhost:8000/v1/engine/multilayer \
  -H "X-API-Key: $MASSIVE_API_KEY" -H 'Content-Type: application/json' \
  -d '{"coupling_gains": {"info_access->opinion": 0.0}}'
```

Omitted keys get no coupling, so `{}` is the fully ablated model.

## Invariants the tests enforce

`tests/test_coupling_structure.py`:

1. every gain has a rationale, and no term names a non-existent variable;
2. density is not a feed-forward chain (≥ 6 cross-couplings) and a cycle exists;
3. **ablating any single term changes the outcome** — a term you can remove
   without consequence is decorative, and decorative terms are worse than absent
   ones;
4. `income` does not collapse to a constant, `hierarchy` stays bimodal *and*
   consequential;
5. the network force reaches ≥ 3 of the 4 non-opinion variables;
6. positive gains move together, and a negative gain genuinely inverts;
7. the model has a response surface (polarization spread > 0.05 across declared
   knobs) and does not saturate the clip.

## Changing the model

1. Add the term to `DEFAULT_COUPLING_GAINS` **and** `COUPLING_RATIONALE`.
2. Check the direction physically: the gradient must produce the sign you claim.
3. Confirm the amplification ratio `coupling · susceptibility / relaxation_rate`
   stays well below 1, or the variable will saturate its clip.
4. Run `pytest tests/test_coupling_structure.py` — the ablation test will tell you
   immediately whether the term is load-bearing.
5. Re-derive the calibration artefacts. `configs/calibrated/` and the
   pre-registration seals describe a specific potential; changing the matrix
   invalidates them as validation evidence.
