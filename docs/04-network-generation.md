---
type: spec
updated: 2026-09-20
status: FROZEN
tags:
  - spec
---
# 04 · Network generation

The graph is an **input condition**, never fitted and never changed during a run (§5, §30). Our wrappers (`generate_er`, `generate_ws`, `generate_sbm`) call NetworkX and are responsible for parameters, reproducibility and validation. They don't reimplement the algorithms.

## Frozen edge weights (A20)

Each undirected social edge $(i,j)$ may carry a positive finite symmetric weight $w_{ij}=w_{ji}$. It means **exogenous contact opportunity or relationship strength**, not trust, answer quality, copying history, knowledge or reputation. Weights are fixed for the complete run.

- Generated V1/V2 graphs use $w_{ij}=1$ on every edge, preserving all historical behaviour exactly.
- A weighted condition must supply its weights explicitly and preregister their source or construction. There is no reference synthetic weight distribution.
- Weights affect only conditional selection of a discussion partner or copying-request target. They never enter $U^S,U^D,U^C$, peer exposure $X$, learning, reward or sharing.
- The global cheating-flow graph remains derived output and never updates these weights.
- Candidate ids are sorted, then the existing semantic uniform is mapped through cumulative normalized candidate weights. Multiplying every candidate weight for one chooser by the same positive constant changes nothing.

This is deliberately a single frozen friendship/contact layer. A future directed learned reliability state $A_{ij}(t)$ must be a separate model amendment; it must not overwrite $w_{ij}$.

## Generators

| Family | NetworkX call | Parameters |
|---|---|---|
| ER | `gnp_random_graph(N, p, seed)` | $p=\bar d/(N-1)$ (reference $6/29\approx0.2069$) |
| Small-world | `watts_strogatz_graph(N, k, p, seed)` | $k=\bar d\in\{4,6,8,10\}$ (even only, A14), $p=\omega$ (reference 0.1). Invariant: $k<N$. |
| Community (reference) | `stochastic_block_model(sizes, P, seed)` | 3 near-equal communities at every $N$ (A13) |

**SBM (A13).** Sizes $n_g = \lfloor N/3\rfloor + [g < N \bmod 3]$, which gives 7/7/6, 10/10/10 and 14/13/13 for $N=20,30,40$. Keeping 3 communities means changing $N$ changes only class size, not mesoscopic topology. To hit the target mean degree $\bar d$ and ratio $r=p_{in}/p_{out}$:
$$w=\frac1N\sum_g n_g(n_g-1),\qquad b=N-1-w,\qquad p_{out}=\frac{\bar d}{r\,w+b},\qquad p_{in}=r\,p_{out}.$$
Checked 2026-09-18, with expected mean degree exactly 6.000 in all three cases:

| $N$ | sizes | $p_{in}$ | $p_{out}$ |
|---|---|---|---|
| 20 | 7/7/6 | 0.7177 | 0.1435 |
| 30 | 10/10/10 | 0.4615 | 0.0923 |
| 40 | 14/13/13 | 0.3394 | 0.0679 |

The wrapper rejects any combination with $p_{in}>1$. Community membership is saved with every graph.

## Replicate pairing (A4)
- One graph per **replicate × topology**, reused by every model × $R$ run in that replicate.
- **Never redraw.** Disconnected graphs and isolates are kept; we sample the stated graph model, not $P(G\mid\text{connected})$. A "connected classroom" condition would be a separate, explicit experiment.
- Isolates can only choose S (A11; [[docs/03-event-schedule]]).

## Saved with every graph
Family and parameters, $N$, replicate, the seed derivation ([[docs/05-rng-and-reproducibility]]), the canonical edge list (sorted pairs $u<v$), its aligned edge weights, separate SHA-256 hashes of topology and weighted edges, realised mean degree, realised mean node strength, number of isolates, number of components, and SBM community membership. Tables: [[docs/07-output-schema]].

## Null ensembles
- **Degree-preserving (A8, primary):** `double_edge_swap(G_copy, nswap=10·|E|, max_tries=100·nswap, seed)`. Degrees are kept; connectivity is **not** imposed. Student identities and all attributes stay on the same node ids. $L=200$ during development, 500–1000 for final claims. Failed or partial swap sets are recorded, never dropped silently.
- **Weight-shuffle (A20):** keep the topology fixed and randomly permute the observed weight multiset over its edges. This tests whether weight placement matters beyond topology and the marginal weight distribution. It does **not** preserve node strengths.
- **Strength-aware weighted null (required before weighted-broker claims):** preserve at least node degree and strength, and preferably block structure when making community claims. This is not supplied by the first A20 implementation; absence of this null blocks a confirmatory weighted-broker claim, not descriptive analysis.
- **Degree- and block-preserving (later, A15):** required before any claim about *community bridges*, because global rewiring destroys community structure. Not built in the first phase.
