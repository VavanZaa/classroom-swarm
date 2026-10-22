---
type: experiment
id: E8
status: LOCKED
date: 2026-09-20
tags:
  - experiment
  - preregistration
  - v3
  - ai-policy
  - guardrails
---
# E8 · Preregistration: universal voluntary AI under unrestricted and controlled tutoring policies

Locked on 2026-09-20 before any E8 simulation output existed. The approved rationale is in
[[docs/experiments/E8-design]]. E8 is a separate intervention engine layered on frozen V3 and does not
modify `v3.py`, its model lock, or E5–E7 evidence.

## 1. Question and evidence boundary

Every student has access to AI in both AI regimes, but no student is forced to use it. E8 compares:

1. exact frozen V3 with no AI;
2. unrestricted answer AI that supplies a complete answer with little effort;
3. controlled tutor AI that withholds the complete answer, supplies accurate stepwise help, and requires
   a student attempt.

This follows the treatment distinction in Bastani et al. (2025), *PNAS*, DOI
[10.1073/pnas.2422633122](https://doi.org/10.1073/pnas.2422633122), and the scaffolded tutor design in
Kestin et al. (2025), *Scientific Reports*, DOI
[10.1038/s41598-025-97652-6](https://doi.org/10.1038/s41598-025-97652-6). Step-level tutoring is also
consistent with VanLehn (2011), DOI [10.1080/00461520.2011.611369](https://doi.org/10.1080/00461520.2011.611369).
The evidence motivates mechanisms, not numerical calibration. Controlled-tutor effectiveness is swept
because published effects vary by system, subject, duration and comparator.

E8 estimates conditional model consequences and policy boundaries. It does not estimate a real school's
adoption rate or treatment effect. Calibration is omitted because no empirical dataset is available.

## 2. Causal and network boundary

- AI is an external service, never a student-graph node. Universal access does not change graph degree,
  betweenness, paths, routing or human source-role definitions.
- From homework 2, one fourth action A is feasible for every student in both AI regimes. Feasible-action
  count and neutral exploration are identical across those regimes.
- No adopter, cheater, responsible-user or resistant type is assigned. There is no AI-prevalence utility.
- Optional social learning observes actions and rewards and updates S, D, C and A symmetrically.
- Confidence follows the frozen grade-tracking measurement equation. There is no AI-specific confidence
  penalty and confidence remains outside choice.
- Diagnostic exams are unaided and state-inert.
- AI policy changes the service response, not student preferences or graph position.

## 3. Common voluntary choice rule

Initialize the fourth value identically to other actions,

$$Q_i^A(0)=K_{0i}-\kappa_i,\qquad U_i^A=Q_i^A.$$

Frozen V3 action-neutral exploration applies over feasible actions. Exploitation is either frozen argmax
or the declared softmax robustness rule

$$P_i(a)=\epsilon/4+(1-\epsilon)
\frac{\exp((U_i^a-\max_bU_i^b)/\tau)}{\sum_b\exp((U_i^b-\max_cU_i^c)/\tau)}.$$

The same semantic strategy draw is reused across paired worlds. Personal and optional social Q updates
are the frozen V3 equations. Universal access therefore does not imply universal use.

## 4. AI mechanisms

### 4.1 Unrestricted answer AI

For each homework item the supplied complete answer is correct with probability $r_U$, using the existing
semantic item uniform. Incidental knowledge is

$$K_i'=K_i+m_U\alpha_i(1-K_i).$$

The reference is $r_U=1$, $m_U=.10$ and cost $c_U=0$. Unlike E7's severe zero-learning reference, `.10`
equals frozen human-copy incidental learning. The response surface uses
$r_U\in\{.80,.90,1.00\}$, $m_U\in\{0,.10,.50\}$ and $c_U\in\{0,1\}$.

### 4.2 Controlled tutor AI

The tutor has a verified solution and common-error guidance, reveals only steps or hints, and requires an
attempt. After a tutored attempt,

$$K_i'=K_i+m_T\alpha_i(1-K_i),$$

and submitted-item correctness has probability

$$p_i^T=K_i'+s_T(1-K_i').$$

The reference is $m_T=1$, $s_T=.25$, and $c_T=1$. The response surface uses
$m_T\in\{.50,1.00,1.50\}$, $s_T\in\{0,.25,.50\}$ and $c_T\in\{1,2\}$. The two parameters separately
represent durable learning and immediate task scaffolding. The reference gives S-equivalent learning,
not an automatic knowledge advantage.

For either service, realized reward remains

$$R_i=G_i^H-\kappa_i c_A.$$

There is no tutor bonus. A controlled interface may be rejected if partial assistance does not compensate
for effort.

## 5. Blocks, seeds and stopping

- Block A seed **930107**, 400 replicates, 3 conditions = **1,200 runs**.
- Block B seed **930108**, 200 replicates, 37 conditions = **7,400 runs**.
- Block C seed **930109**, 100 replicates, 144 conditions = **14,400 runs**.
- Bootstrap seed **930700**, 10,000 paired resamples.
- Smoke seed **930993**, two replicate worlds per block; smoke output is deleted.
- Total full E8: **23,000 runs**. No optional stopping, condition removal or outcome-driven tuning.

All compatible conditions use common graph, trait and semantic draws. Accuracy and scaffold differences
reuse item uniforms. E8 starts only from a clean committed tree and refuses to overwrite a full run.

## 6. Block A · Primary three-regime trends

All use N=30, H=20, SBM, R=3, frozen V3 defaults, argmax and personal learning only.

| Label | Policy |
|---|---|
| `E8-A-none` | exact frozen V3 |
| `E8-A-unrestricted` | universal A; $r_U=1$, $m_U=.10$, $c_U=0$ |
| `E8-A-controlled` | universal A; $m_T=1$, $s_T=.25$, $c_T=1$ |

Trajectories are reported for every homework, with early homeworks 2–6 and late homeworks 16–20 declared
summary windows.

## 7. Block B · Mechanism response surface

All use N=30, H=20, SBM, R=3, argmax and personal learning only.

- one exact no-AI control: `E8-B-none`;
- 18 unrestricted cells from $3\times3\times2$: labels
  `E8-B-U-r<080|090|100>-m<000|010|050>-c<0|1>`;
- 18 controlled cells from $3\times3\times2$: labels
  `E8-B-T-m<050|100|150>-s<000|025|050>-c<1|2>`.

Report every cell versus no AI and every matched unrestricted/controlled reference contrast. The policy
map is based on intervals, not point estimates.

## 8. Block C · Spread and robustness

Cross all levels of:

| Factor | Levels |
|---|---|
| regime | N=no AI; U=unrestricted reference; T=controlled reference |
| social learning | 0; $\eta_{social}=.10$ |
| decision rule | argmax; softmax $\tau=.10$; softmax $\tau=.25$ |
| trait assignment | original; one complete-bundle shuffle independent of graph position |
| topology | SBM; ER |
| horizon | H=20; H=40 with a matched no-AI control |

This is $3\times2\times3\times2\times2\times2=144$ cells. Labels are
`E8-C-<N|U|T>-<social><choice><shuffle><topology><horizon>`. Choice is `0` for argmax, `1` for softmax
`.10`, and `2` for softmax `.25`; social, shuffle, topology and horizon are binary (`1` means social
learning, shuffled traits, ER and H40 respectively).

Because access never varies, the social contrast tests peer-outcome observation, not access diffusion.
“Spread” means changing voluntary adoption and clustering across the friendship graph.

## 9. Outcomes

Per run and, where stated, per homework reconstruct from raw logs:

- `pA_early`, `pA_late`, S/D/C early and late shares;
- ever adopter share, persistent AI share, first-use homework and abandonment after first use;
- late grade and reward, final K and confidence, final unaided exam, grade–exam gap;
- mean learning increment and reward on AI-use rows;
- human-copy success, source top-20 share, source Gini and strict source persistence;
- AI adoption assortativity, within-minus-between-community adoption difference, and neighbour-lag
  association;
- K and exam outcomes by initial-K quintile and top-minus-bottom inequality;
- fraction of replicate classrooms where each AI regime exceeds no AI.

The primary outcomes are late AI, S, D and C shares, late grade, final K, final exam, grade–exam gap,
discussion displacement and human-copy displacement. Network associations are descriptive unless they
come from the paired social-learning contrast.

## 10. Practical deltas and intervals

Use paired 95% percentile bootstrap intervals. Reuse E7's precision scale, chosen before E8 outcomes:

- action/adoption shares: `.02`;
- grade, exam, reward, grade–exam gap and copy success: `.05`;
- K and K inequality: `.01`;
- confidence and source concentration/Gini: `.05`;
- strict source persistence: `.10`.

Report all contrasts, including boundary-inadequate intervals. Do not equate statistical exclusion of zero
with practical importance.

## 11. Locked predictions

1. **P1 voluntary use:** lower CI of late A share exceeds `.05` in both Block-A AI regimes.
2. **P2 adoption advantage:** unrestricted minus controlled lower CI for early and late A share exceeds
   `.05`.
3. **P3 performance illusion:** unrestricted minus no AI has grade–exam gap lower CI above `.05`.
4. **P4 controlled protection:** controlled minus unrestricted has final K and exam lower CIs above `.02`.
5. **P5 unrestricted displacement:** unrestricted minus controlled has upper CIs below `-.02` for both
   late D and late C shares.
6. **P6 controlled versus no AI:** direction is deliberately open; classify final K and exam using the
   `.01` K and `.05` exam practical deltas.
7. **P7 effort sensitivity:** within the Block-B controlled surface, cost two minus cost one has late A
   share upper CI below `-.02`.
8. **P8 tutor-learning sensitivity:** the controlled $m_T=1.50$ versus `.50` marginal contrast has final K
   lower CI above `.02`.
9. **P9 decision robustness:** both AI regimes have late-A lower CI above `.05` under argmax and each
   softmax rule in Block C's baseline SBM/H20/unshuffled/no-social slice.
10. **P10 decision-rule sensitivity:** at least one softmax-minus-argmax late-A contrast in that slice has
    an absolute interval entirely beyond `.02`; no direction is prespecified.

## 12. Locked school-facing classifications

For each Block-B cell relative to paired no AI:

- **safe:** lower 95% bounds for both final-K and final-exam differences exceed `-.01`;
- **useful:** safe and lower bounds for both exceed `+.01`;
- **performance illusion:** late-grade lower bound exceeds `+.05`, final-exam upper bound is below `-.01`,
  and grade–exam-gap lower bound exceeds `+.05`;
- **social displacement:** either late-D or late-C upper bound is below `-.05`;
- **viable controlled policy:** safe, controlled late-A lower bound exceeds `.05`, and the matching
  Block-C reference has late-A lower bound above `.05` under argmax and at least one softmax rule.

Cells may have multiple warnings. The final traffic-light map is green for useful controlled cells without
performance illusion, amber for safe but not useful controlled cells or cells with social displacement,
and red for unsafe or performance-illusion cells. Rules are scenario classifications, not school forecasts.

## 13. Raw data, integrity and claims

Canonical schema v3 remains unchanged. A is stored in `decisions.action`. An `ai_decisions.parquet`
sidecar records policy, feasibility, P_A, Q_A, AI parameters, K before/after, immediate correctness
probability, learning increment and effort. AI is absent from graph tables.

The runner must verify this hash and the frozen V3 lock, require a clean tree, prove exact no-AI parity,
run a deleting smoke, isolate full-run replicate workers, hash all outputs, and report every failed run or
deviation. E8 may support conditional comparisons among declared AI policies. It may not claim calibrated
real-world adoption, causal effects at a school, or that all controlled tutors are effective.
