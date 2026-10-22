---
type: experiment
id: E6
status: REPORTED
date: 2026-09-20
tags:
  - experiment
  - results
  - v3
  - robustness
---
# E6 · Results: copying is structurally robust; role persistence and parameter rankings are conditional

Results of [[docs/experiments/E6-preregistration]] under the frozen
[[docs/10-v3-generative-model|V3 model]]. E6 completed **31,200 runs**: 5,600 structural runs and
25,600 full-factorial runs. The preregistration SHA-256 was
`f6aa7ac964c3ba276ff572721960e98694cfe7dd6fd7e9e9772c8ad5848d3800`; the final isolated-worker
implementation was commit `1dd1705`; and the frozen V3 model was commit `876556a`.

Two technical deviations occurred. The first process stopped at structural replicate 143 with a
`MemoryError`; a memory-releasing resume stopped at replicate 290. No scientific outcome was inspected
after either interruption. The final implementation isolated each replicate in a subprocess, retained
all complete raw outputs without overwriting them, and preserved every locked seed, condition, outcome,
threshold and analysis rule. See [[docs/experiments/E6-deviations]]. The completed run had no stderr.
All **24,908** manifested files were independently rehashed with zero missing files or mismatches, and
all **209 tests** passed after the run.

## Main answer

The narrow emergence claim is supported **inside V3**: copying remains substantial without a
copying-prevalence term or assigned behavioral types, and it survives all 14 preregistered structural
conditions. Baseline late copying was **39.65%** (95% CI [38.89%, 40.42%]). Even the lowest condition,
reward without an effort-cost penalty, retained **16.06%** [15.47%, 16.66%], well above the locked 4%
boundary.

This is conditional emergence, not creation from nothing and not proof of real classroom behavior. The
model explicitly makes copying an available action, introduces it through a declared seed or neutral
exploration, and encodes reward, effort, sharing, routing and answer-transfer mechanisms. What emerges
is the population pattern and source organization without a direct prevalence bonus or assigned role
labels. The possibility of copying and its generic incentives are designed into the model.

Four of the five pass/fail predictions passed. The sixth preregistered item was a report-only interaction
with no directional prediction.

| Prediction | Result | Evidence |
|---|---|---|
| P1 · Baseline copying persists | pass | 0.3965 [0.3889, 0.4042] > 0.04 |
| P2 · Strict baseline source roles persist | pass | mean residual rho 0.501 [0.483, 0.520]; significant-classroom share 0.853 [0.818, 0.888] |
| P3 · Equal-cost copying persists | pass | 0.2709 [0.2642, 0.2774] > 0.04 |
| P4 · Both softmax variants retain copying | pass | 0.5838 [0.5790, 0.5885] and 0.4449 [0.4408, 0.4492] |
| P5 · Predicted four largest pC factors | **fail** | sharing replaced `eta_Q`; `eta_Q` ranked sixth |
| P6 · cost × `eta_Q` × exploration | reported | negligible for all five outcomes; no direction was predicted |

## Structural robustness of copying

Every condition independently passed the preregistered lower-CI > 0.04 rule.

| Structural condition | Late copying | 95% CI | Difference from baseline |
|---|---:|---:|---:|
| baseline | 0.3965 | [0.3889, 0.4042] | — |
| homogeneous traits | 0.4632 | [0.4553, 0.4710] | +0.0667 |
| softmax, tau=0.10 | 0.5838 | [0.5790, 0.5885] | +0.1872 |
| softmax, tau=0.25 | 0.4449 | [0.4408, 0.4492] | +0.0484 |
| knowledge reward | 0.1833 | [0.1768, 0.1899] | -0.2133 |
| no effort-cost reward penalty | 0.1606 | [0.1547, 0.1666] | -0.2360 |
| no reliability access utility | 0.3973 | [0.3896, 0.4049] | +0.0008, negligible |
| equal successful-copy cost | 0.2709 | [0.2642, 0.2774] | -0.1256 |
| N=15 | 0.4110 | [0.4001, 0.4223] | +0.0145, boundary-inadequate |
| N=120 | 0.4004 | [0.3966, 0.4042] | +0.0039, negligible |
| H=10 | 0.3823 | [0.3748, 0.3899] | -0.0143, below practical delta |
| H=80 | 0.4018 | [0.3943, 0.4095] | +0.0053, below practical delta |
| mean degree 2 | 0.3122 | [0.3055, 0.3190] | -0.0843 |
| mean degree 10 | 0.4050 | [0.3972, 0.4126] | +0.0085, below practical delta |

The result is therefore not an artifact of assigned heterogeneity, deterministic argmax choice, one
specific personal reward, the reliability term in copying utility, one class size, one horizon or the
baseline density. Its **magnitude** is nevertheless mechanism-sensitive: changing the reward definition
roughly halves copying, equal cost removes 12.6 percentage points, and sparse degree removes 8.4 points.

## Source roles: strong baseline evidence, limited generality

The stronger source-role test controls degree, betweenness, SBM community, initial knowledge, learning
efficiency, effort cost and each half-semester's opportunity to originate an answer. Baseline residual
source persistence averaged **rho=0.501** [0.483, 0.520], above the 0.20 criterion. In **85.25%** of
classrooms [81.75%, 88.75%], the one-sided 999-permutation test had p<=.05, above the 50% criterion.
This supports persistent source positions beyond the named observables, not innate psychological roles.

The result also survives removal of trait heterogeneity: the homogeneous condition's mean was 0.514.
However, it is **not robust to probabilistic choice**. Mean strict persistence fell to 0.190 under
softmax tau=0.10 and 0.096 under tau=0.25. Thus the baseline argmax/reinforcement dynamics help create
stable source identities. The defensible claim is “strict roles emerge in baseline and homogeneous V3,”
not “source roles emerge under every reasonable decision rule.”

Baseline source traffic was concentrated—the most-used 20% supplied 62.61% of successful copied
answers and source Gini was 0.648. Multi-hop routing appeared in 60.2% of late homeworks, but the
five-copier cascade rate was only **0.55%**. E6 therefore confirms E5's distinction: persistent sources
and multi-hop routes occur, while large baseline cascades do not.

## Which parameters matter most

Importance below is conditional on the deliberately broad frozen endpoints. It is not a universal
sensitivity ranking and does not say these endpoints are realistic.

For late copying, the ranked main effects were:

| Rank | Factor change | Effect on late copying | 95% CI |
|---:|---|---:|---:|
| 1 | successful-copy cost 0 -> 1 | -0.2102 | [-0.2142, -0.2062] |
| 2 | sharing probability 0.60 -> 1.00 | +0.1366 | [0.1331, 0.1401] |
| 3 | routing depth 1 -> 3 | +0.1288 | [0.1253, 0.1324] |
| 4 | symmetric social learning 0 -> 0.10 | +0.0625 | [0.0561, 0.0693] |
| 5 | exploration 0 -> 0.12 | +0.0277 | [0.0229, 0.0325] |
| 6 | action reinforcement 0 -> 0.40 | -0.0275 | [-0.0344, -0.0212] |
| 7 | source-belief learning 0 -> 0.40 | +0.0079 | [0.0051, 0.0107] |
| 8 | seed fraction 0 -> 0.20 | -0.0037 | [-0.0071, -0.0004] |

The failed P5 prediction matters. Sharing opportunity is a stronger global driver of copying than
expected-value learning over these endpoints, while the one-time seed is the weakest. Copying is mainly
controlled by whether it is cheap, whether answers are shared, and whether paths can reach a holder—not
by a copying-prevalence reward.

The top effects differ by outcome:

| Outcome | Largest main effects, ordered by absolute size |
|---|---|
| copying | copy cost -0.210; sharing +0.137; routing +0.129; social learning +0.063 |
| copy success | routing +0.258; sharing +0.175; copy cost +0.155; social learning -0.125 |
| final knowledge | copy cost +0.0479; sharing -0.0261; routing -0.0256; social learning -0.0134 |
| strict source persistence | reinforcement +0.173; belief learning +0.106; social learning -0.096; sharing +0.073 |
| multi-hop rate | routing +0.557; copy cost -0.161; social learning +0.103; sharing +0.097 |

Routing's multi-hop effect is partly definitional because the factor directly changes allowed request
depth. High copying is also not automatically desirable: mechanisms that raise copying often reduce
final knowledge or copy success.

Main effects are context-dependent. The three largest pC interactions were copy cost × social learning
**-0.151**, social learning × routing **+0.086**, and sharing × belief learning **+0.063**. The targeted
cost × reinforcement × exploration effect was negligible for copying (-0.0012 [-0.0035, 0.0010]) and
for all other primary outcomes. The complete file contains all 185 locked effects.

## Assumption verdicts

| Assumption or claim | Verdict from E5/E6 |
|---|---|
| A copying-prevalence utility is necessary | **False inside V3.** Copying persists with beta_P=0. |
| Fixed “copier,” “good student” or “broker” types are necessary | **False inside V3.** Homogeneous traits still produce copying and strict role persistence. |
| Copying is generated from literally no possibility | **False framing.** The action and incentives exist; seed/exploration supplies entry. |
| Cost advantage is necessary | **False**, but it is the largest tested pC factor. Equal cost still yields 27.1% copying. |
| Local reliability utility causes copying prevalence | **Unsupported.** Removing it changes pC by only +0.08 points. |
| Learned targeting is a major copying driver | **Not supported.** `eta_A` changes pC by only +0.79 points and did not meet E5's material success criterion. |
| Endogenous sharing is unimportant | **False over the E6 endpoints.** Sharing is the second-largest pC factor, with strong interactions. |
| Generic social learning is necessary | **False.** Baseline emergence occurs without it; when enabled it amplifies copying and harms success/knowledge. |
| Stable source roles are decision-rule invariant | **False.** Strict persistence weakens sharply under softmax choice. |
| Large copying cascades emerge at baseline | **False.** The baseline cascade-five rate is 0.55%. |
| Weighted edges are needed | **No evidence of need.** E5's independent frozen weights were negligible for pC; E6 did not retest weights. |
| The model is empirically realistic | **Unknown.** No calibration or held-out classroom validation exists. |

## Harsh defensibility assessment

V3 is defensible as a **transparent generative proof of possibility**: a preregistered, frozen,
reproducible mechanism can create substantial copying and persistent source organization without a
prevalence bonus or assigned roles. E6 greatly reduces the chance that this narrow result is a single
parameter, class-size, horizon, density, reward or deterministic-choice artifact.

It is **not yet defensible as a descriptive, predictive or policy model of students**. There is no
evidence that its parameter ranges, utility structure, learning rates, sharing decisions, network or
outcome mapping match real classrooms. The full factorial identifies sensitivity over chosen endpoints,
not empirically likely causes. Strong interactions make single-parameter rankings portable only within
the tested design. The strict role regression controls measured simulation variables but cannot rule out
unmeasured real traits or prove a psychological “broker” identity. Multiple mechanisms are deliberately
simple, and the rare-cascade failure shows the model does not reproduce every intuitively expected
collective pattern.

Confidence should therefore be separated by claim:

| Claim | Confidence | Reason |
|---|---|---|
| computational integrity and reproducibility | very high | locked hashes, no outcome-driven changes, 24,908 verified files, 209 passing tests |
| copying can emerge in this model without prevalence or assigned types | high | preregistered replication plus 14/14 structural passes |
| baseline strict source roles are not explained by named covariates | high within model | both locked residual/permutation criteria pass |
| source roles generalize across choice rules | low | both softmax variants sharply weaken persistence |
| factor ranking within the E6 endpoints | moderate-high | full 2^8 design, but large interactions and broad artificial endpoints |
| real-classroom prevalence, causality or forecasting | unknown/low | calibration and external validation were explicitly omitted |

Adding a more agentic or LLM-driven layer now would not repair this evidence gap. It would add opaque
priors, extra degrees of freedom and harder causal attribution. The scientific gate is passed for
continuing V3 as a theory/synthetic-laboratory model, but **not** for presenting a more agentic version as
a realistic classroom simulator. If empirical data later become available, measurement design,
calibration, parameter recovery and held-out prediction should precede agentic complexity.

Weighted graphs should likewise remain optional. Frozen exogenous weights are reasonable only for a
specific tie-strength question; E5 found no need for them in the main emergence claim. Learned or dynamic
weights would add a new feedback mechanism and could manufacture concentration unless independently
motivated and preregistered.

## Boundary-inadequate results

The locked boundary rule classified 234/247 structural contrasts and 182/185 factorial effects as
adequate. The following intervals crossed a practical-delta boundary and are not classified as clearly
below or above it:

| Block | Condition/effect | Outcome | Estimate | 95% CI |
|---|---|---|---:|---:|
| S | homogeneous | pC_change | +0.0194 | [0.0145, 0.0243] |
| S | softmax tau=.10 | dGK_last | -0.0195 | [-0.0220, -0.0171] |
| S | softmax tau=.10 | capacity denial | +0.0481 | [0.0436, 0.0527] |
| S | softmax tau=.25 | pC_postseed | +0.0224 | [0.0148, 0.0302] |
| S | softmax tau=.25 | success | -0.0466 | [-0.0527, -0.0404] |
| S | knowledge reward | source Gini | +0.0493 | [0.0410, 0.0575] |
| S | equal cost | CF | +0.0521 | [0.0486, 0.0556] |
| S | N=15 | pC_late | +0.0145 | [0.0031, 0.0261] |
| S | N=15 | Lmax_mean | -0.2334 | [-0.2621, -0.2040] |
| S | N=120 | strict source persistence | +0.1010 | [0.0808, 0.1211] |
| S | H=10 | CF | +0.0483 | [0.0451, 0.0515] |
| S | degree 2 | dGK_last | -0.0204 | [-0.0224, -0.0185] |
| S | degree 10 | multihop rate | +0.0560 | [0.0235, 0.0880] |
| F | `eta_Q` | final knowledge | +0.0096 | [0.0079, 0.0113] |
| F | `eta_A` | strict source persistence | +0.1058 | [0.0936, 0.1177] |
| F | `eta_social` | strict source persistence | -0.0962 | [-0.1090, -0.0839] |

## Evidence files

- `runs/E6/derived/structural_absolute.parquet` — SHA-256 `b640ad3c127ea2d4...`
- `runs/E6/derived/structural_contrasts.parquet` — SHA-256 `eb3cfaff09bbb171...`
- `runs/E6/derived/factorial_effects.parquet` — SHA-256 `e98cf52a330f5111...`
- `runs/E6/derived/source_null.parquet` — SHA-256 `80552a19c69cc717...`
- `runs/E6/derived/predictions.parquet` — SHA-256 `3455c35b8e34db26...`
- `runs/E6/derived/report.json` — SHA-256 `f414b186482688d0...`
- `runs/E6/derived/hashes.json` records all 24,908 manifested hashes and itself independently hashes to
  `a216ad9c2f44306d...`.

## Conclusion

E6 strengthens the narrow scientific conclusion: prevalence-free, role-unassigned copying is a robust
emergent macro-pattern of V3. The strongest tested controls are copying cost, sharing and routing depth.
It simultaneously narrows the claim: source-role persistence depends on the decision rule, large
cascades remain absent, the predicted top-four parameter set failed, and there is no empirical evidence
that V3 represents real students. Further complexity should not be described as increased realism until
data can test that proposition.
