# A27: configurable initial knowledge

2026-10-01. The user requested control over the initial knowledge distribution's mean and standard deviation, for example to model a classroom with high starting knowledge. `v4_population.py` is an explicit fork of A26; historical engines, locks and results remain unchanged. It adds no action or decision rule.

## Controls

`PopulationParams` exposes all corrected-model settings plus:

| Parameter | Default | Meaning |
|---|---|---|
| `K0` | `0.50` | Mean of the underlying normal distribution, from 0 to 1 |
| `K0_sd` | `0.10` | Standard deviation of the underlying normal distribution; finite and nonnegative |

Initial knowledge is sampled from that normal distribution **truncated to [0, 1]**, using the existing semantic trait draws. These parameters describe the underlying normal: truncation changes its actual mean and standard deviation near either boundary. A finite classroom also has sampling variation. Positive spread does not guarantee that every student exceeds a particular knowledge threshold. With `K0_sd=0`, every student starts at exactly `K0`, including at 0 or 1.

Illustrative settings, not calibrated student populations:

| Classroom | `K0` | `K0_sd` |
|---|---:|---:|
| Existing reference | 0.50 | 0.10 |
| High starting knowledge, narrow spread | 0.85 | 0.05 |
| Mixed starting knowledge | 0.50 | 0.20 |
| Identical high starting knowledge | 0.85 | 0.00 |

Knowledge measures unaided item correctness probability, not intelligence. Learning efficiency and effort aversion retain their separate distributions. Confidence starts at each student's sampled knowledge; the five benefit beliefs do too unless `benefit_prior` is explicitly supplied. Consequently changing initial knowledge also changes initial confidence and, by default, benefit priors. A contrast must disclose this coupling; use a common `benefit_prior` to hold those priors constant across populations. Future scientific claims require a separate preregistration and run lock.

## Example

```python
from classroom_swarm.graphs import generate_er
from classroom_swarm.v4_public_ai import PublicAIDraws
from classroom_swarm.v4_population import (
    PopulationParams, simulate_population, validate_population_log,
)

p = PopulationParams(K0=0.85, K0_sd=0.05, ai_mode="answer")
graph = generate_er(p.N, 6, 71)
draws = PublicAIDraws(82, 0, p.N, p.items, p.exam_items)
log = simulate_population(p, graph, draws, condition="high_start_answer_ai")
validate_population_log(log)
```

This is a Python configuration interface; no interactive settings panel is introduced. Both requested settings are saved in the run manifest, and the realized values remain in the `traits` table. Default settings must reproduce A26 on every raw table. Tests also check zero spread, high/low populations under paired draws, unchanged other traits, bounded samples, invalid inputs and reproducibility.
