# A26: corrected controls and identified contrasts (V4.3-C)

2026-09-25. A read-only audit of the V4 line ([[docs/experiments/V4-audit-2026-09-25|audit record]]) found two implementation defects, one bundled primary contrast, one selection-biased subgrouping and two undeclared score-function assumptions. A26 repairs what is repairable in an engine and re-runs the A25 questions under an identified design. It is an explicit source fork: `v4_corrected.py` and `e13.py` are new files, and every A22–A25 source, lock and result stays byte-identical. Earlier runs remain historical records.

A26 changes controls and reporting, not the substantive model. Under its legacy flags it must reproduce A25 exactly, and a parity test enforces that on every raw table.

## What the audit found and what A26 does about it

| # | Finding | Disposition |
|---|---|---|
| 1 | `tutor_ai0` credits `ai_tutor` only when the hint strength is positive, so the null-tutor control is unlearnable | fixed: `tutor_credit_by_source` |
| 2 | `B_check` is written and never read; it dilutes the benefits that do drive choice | not present in the A25/A26 line (no checking action); a regression test now forbids a write-only benefit channel; E9/E10 get errata |
| 3 | E11's copying increase and E12's grade–exam gap restate encoded rules | fixed in reporting: the preregistration names them as identities before the run |
| 4 | `public_no_ai − motivation_only` moves five parameters at once | fixed: a five-step ladder, one parameter per step |
| 5 | `motivation_only − legacy` bundles the learning bonus with the waiting bonus | fixed: `wait_value` separates them |
| 6 | Subgroup labels are taken from one arm of the contrast | fixed: contrasted subgroups use the exogenous `alpha` trait; behavioural groups stay descriptive and are never differenced |
| 7 | `attempt`/`hint` mix confidence into the benefit, the shortcut actions do not | not a defect; exposed as `confidence_weight` and tested at 0, .5 and 1 |
| 8 | `B` is anchored at `K0` and no A25 condition varies it | not a defect; `benefit_prior` arms added |
| 9 | ~8% of peer hints arrive with too little time left to use | fixed: `hint_deadline_guard`, mirroring the rule the AI tutor already applies |
| 10 | E12 has no topology arm | fixed: ER conditions |

## Interface

`CorrectedParams(PublicAIParams)` adds five fields. Defaults give the corrected model; the listed legacy values reproduce A25.

| Field | Default | Legacy | Meaning |
|---|---|---|---|
| `tutor_credit_by_source` | `True` | `False` | credit and label an AI-tutored attempt by the hint's **source**, not its strength |
| `hint_deadline_guard` | `True` | `False` | serve a peer hint only if a full attempt still fits before the deadline |
| `confidence_weight` | `.5` | `.5` | weight on self-assessment in the attempt/hint benefit; 0 uses the learned benefit alone |
| `wait_value` | `0.` | `.025` | the waiting score, now independent of `grade_effort_only` |
| `attempt_ticks` | `3` | `3` | the attempt duration the hint guard reserves; not a new behaviour |

All five must be finite and, where numeric, in [0,1]; the two flags must be booleans. `attempt_ticks` must be a positive integer not exceeding `ticks`. Every A25 validation rule still applies, including `allow_check=False` and the refusal of a hidden learning reward under `grade_effort_only`.

`simulate_corrected(params, graph, draws, condition=...) -> V4Log` keeps A25's tables and adds `hint_usable` to hint-receipt rows. `PublicAIDraws` and all semantic streams, including 106 closeness and 107 AI items, are reused unchanged; A26 introduces no new stream and cannot perturb historical randomness.

## The three engine changes

**Tutor credit.** An attempt whose consumed hint came from the AI is labelled `origin='ai_tutor_attempt'` whenever `hint_source=='ai'`, regardless of hint strength, and `corrected_grade_credit` tests that origin before it tests `assisted`. A zero-strength tutor therefore yields route `ai_guided`, credit `.5` attempt and `.5` ai_tutor, and a grade equal to an unaided attempt. The student can now learn that the tutor adds nothing. Under `tutor_credit_by_source=False` the A25 rule returns exactly, so the size of the old defect is measured rather than asserted.

**Hint deadline.** A pending peer-hint request is served only if `t + 2 + attempt_ticks <= ticks`. Otherwise the reason is `deadline`, as it already is past the service window. The AI tutor already required `remaining >= ai_tutor_ticks + attempt_ticks`; peer hints now use the same rule, so "limited hint uptake" is a choice rather than an arrival accident. `hint_usable` is logged on every hint receipt so the residual can be audited; with the guard on it must always be true.

**Score generalisation.** The attempt and hint benefits become `(1-w)*B + w*c` and `(1-w)*B_hint + w*(c + .25*(1-c))` with `w = confidence_weight`, and the waiting score becomes `wait_value`. At `w=.5` with `wait_value=.025` under `grade_effort_only=False`, and at `w=.5` with `wait_value=0` under `grade_effort_only=True`, the score dictionary equals A25's to the last bit. No other coefficient moves.

A26 adds no mechanism, no new belief, no new action and no new information channel. It does not touch learning, grades, exams, copying, closeness, AI capability or any rate.

## Identification

E12's single step from `motivation_only` to `public_no_ai` moved `peer_rule`, `distant_weight`, `closeness_spread`, `grade_bias` and `public_signal` together, so no contribution was separable; and `public_signal` is not neutral, because under the strict higher-grade rule the eligible pool's mean grade always exceeds the requester's, which biases the perceived value of copying upward. E13 replaces that step with a ladder that adds one thing at a time, each paired on the same graph and the same semantic draws:

`legacy` → `drop_learning_bonus` / `drop_wait_bonus` → `motivation_only` → `acquaintances` (contact set) → `plus_grade_filter` (eligibility) → `plus_grade_weighting` (source weighting) → `public_no_ai` (benefit blending).

Each rung is a preregistered primary contrast against the rung below it. The ladder is additive by construction; it does not claim the effects are additive, and interactions between rungs are not estimated.

## Subgroups

Contrasted subgroups are the top and bottom thirds of each classroom by the exogenous learning trait `alpha`, which is drawn before any behaviour, is identical in every condition of a replicate and cannot be selected on an arm's own noise. Behavioural early-attempt groups are retained as a within-condition description under a `desc_` prefix and are **excluded from the paired-effect table in code**, because a group defined by one arm's realised behaviour cannot be differenced against another arm without importing a regression-to-the-mean term.

## Stated identities, fixed before the run

These are consequences of the encoded rules. E13 reports them for magnitude and audit, never as findings.

- Answer AI emits packets at `ai_accuracy` and grants no knowledge, while grades come only from packet bits and knowledge only from attempts. Any positive uptake must therefore raise homework grades and widen the homework–exam gap. **The scientific content is the uptake, the substitution away from attempts, and the peer propagation of AI answers, not the gap.**
- `grade_response * grade_shortfall` is added to the answer and AI-answer scores, so removing it must reduce copying.
- `B` moves toward an observed grade at receipt, so an above-expectation grade must raise the credited action's benefit.

## Tests

Beyond A25's suite: A25 parity on every raw table under legacy flags; score-dictionary parity at `w=.5` for both `grade_effort_only` settings; an AI-tutored attempt at zero hint strength credits `ai_tutor` and produces route `ai_guided`; the A25 rule returns under `tutor_credit_by_source=False`; no hint is received with fewer than `attempt_ticks` remaining while the guard is on, and some are without it; **no benefit index is write-only** — perturbing any one of the five benefits must change the score dictionary; `confidence_weight=0` removes self-assessment from the attempt score only; `wait_value` is independent of `grade_effort_only`; stream independence and unchanged historical locks.

## Limits

A26 corrects controls, identification and reporting. It does not calibrate anything, does not add forgetting, sanctions, detection, correlated AI errors or multiple concepts, and does not make any earlier result wrong in its own terms. Rates and coefficients remain assumptions from chosen trajectories. A cleaner contrast ladder identifies which encoded rule moved an outcome; it still cannot turn an encoded rule into an empirical finding.
