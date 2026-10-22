---
type: spec
updated: 2026-09-20
status: FROZEN
tags:
  - spec
---
# 05 · RNG and reproducibility

## Principle (A7, A16)
Randomness is **semantic and pre-generated**, not consumed sequentially. Each random process has a named tensor indexed by what it means (homework, student, item, round), so matched runs (M0–M5, $R=1$ vs 3) threshold **the same latent draws** against different probabilities. Differences between paired runs are then caused by the mechanism, not by RNG bookkeeping.

## Stable stream codes
Seeds come from `numpy.random.SeedSequence(entropy=[master_seed, replicate, stream_code, ...])`. **Codes are fixed integers and never depend on the order of `spawn()` calls**, so adding a stream later can't shift any existing one.

| Code | Stream | Seed key | Tensor per key | Index |
|---|---|---|---|---|
| 1 | graph | [master, rep, 1, family_code] | one integer seed for NetworkX | — |
| 2 | strategy | [master, rep, 2, h] | $U^{strategy}$, shape $(N)$ | student |
| 3 | partner | [master, rep, 3, h] | $U^{partner}$, shape $(N)$ | student |
| 4 | item | [master, rep, 4, h] | $U^{item}$, shape $(M_H, N)$ | item, student |
| 5 | routing | [master, rep, 5, h] | $U^{routing}$, shape $(R_{max}, N)$; a run with $R$ uses rows $[:R]$ | round, student |
| 6 | exam | [master, rep, 6, e] | $U^{exam}$, shape $(M_E, N)$ | item, student |
| 7 | null | [master, rep, 7, family_code, ℓ] | one integer seed per rewiring ℓ | — |
| 8 | V3 exploration | [master, rep, 8, h] | $U^{explore}$, shape $(N)$ | student |
| 9 | V3 traits | [master, rep, 9] | three standard-normal rows | trait, student |
| 10 | V3 sharing | [master, rep, 10, h] | $U^{share}$, shape $(R_{max},N)$ | round, requester |

Family codes: ER = 1, WS = 2, SBM = 3. Streams 2–6 and 8–10 don't include the family, so every topology of a replicate shares them too. This is **intentional**: one `Draws` object per replicate serves all stages, $R$ values, families and the paired V3 controls ([[docs/09-engine-api]]). Don't split it per family.

**Why one seed per homework, with the variable-length dimension outermost:** NumPy fills arrays in row-major order. So $U^{routing}$ for $R=1$ is exactly the first row of the $R=3$ tensor for the same homework, and a shorter horizon $H$ reuses the same per-homework seeds. $R{=}1$ vs $R{=}3$ and short vs long horizons therefore stay paired. (Changing $N$ or $M_H$ is a different world and isn't paired.)

## Use rules
- $U^{item}_{h,i,q}$ is used for **every self-generated answer** (S, D and failed-copy fallback): item correct iff $U<p$. **Copied answers draw nothing.** They inherit the source packet's item outcomes exactly.
- Partner and routing choices: **sort the candidate student ids ascending first**, then map the existing uniform through the cumulative normalized fixed edge weights (A20). With uniform weights this is exactly index $\lfloor U\cdot|\text{candidates}|\rfloor$. NetworkX neighbour-iteration order is never relied on. Weights add no RNG stream.
- Strategy: inverse CDF of $U^{strategy}_{h,i}$ over the fixed order (S, D, C). The uniform is drawn for every student every homework, including isolates.
- Bit generator: NumPy's default (PCG64). Its name is recorded.

## What is saved (not the tensors)
Master seed, replicate, the stream-code table version (`rng_scheme = "v1"`), the bit-generator name, NumPy/NetworkX/Python versions and the git commit. Any tensor can be regenerated from these. See [[docs/07-output-schema]].

## Determinism
Students are iterated in index order, and no result depends on set or dict order. Identical seed, parameters, graph and code must give **identical outputs** (test T6).
