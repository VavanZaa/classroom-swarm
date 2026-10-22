---
type: experiment
id: E7
status: REPORTED
date: 2026-09-20
tags:
  - experiment
  - results
  - v3
  - ai-intervention
---
# E7 · Results: perfect-answer AI displaces human exchange and learning, but withdrawal permits recovery

Results of [[docs/experiments/E7-preregistration]] under the frozen V3 model. E7 completed **17,600
runs**: 4,800 structural runs and 12,800 full-factorial runs. The preregistration SHA-256 was
`9f1bbbd41e1d56ad9137877bd948467656ab907407f266222a32bd89f16ce8d3`; the clean run used commit
`507fceb`; and frozen V3 remained at commit `876556a`. Runtime was 22.3 minutes. There were **no
deviations** and no stderr. All **17,307** manifested files were independently rehashed with zero missing
files or mismatches, and all **216 tests** passed after the run.

## Main answer

Under the deliberately severe E7 scenario, AI adoption emerged from neutral exploration and personal
reinforcement without an AI-prevalence reward or assigned adopter types. In the baseline intervention,
late AI use was **31.83%** [30.95%, 32.72%]; 43.38% of students ever used AI, and 32.26% used it on at
least three of their last five available homeworks.

Students did not simply add AI on top of existing behavior. Relative to no-AI V3, late solving fell 6.49
points, discussion fell 7.97 points, and human copying fell **17.37 points**. Homework grades increased
4.74 points, while final knowledge fell **4.46 points**, unaided exam performance fell **4.41 points**,
and the homework-grade/unaided-exam gap widened **9.15 points**. Recorded confidence fell 18.97 points
under the imposed decrement scenario.

These are conditional simulation consequences—not estimated effects on real students. Perfect AI grades,
zero AI learning and the confidence decrement are inputs. Adoption, behavioral substitution, human-source
reorganization and recovery after withdrawal are outputs.

Seven of nine locked predictions passed:

| Prediction | Result | Evidence |
|---|---|---|
| P1 · AI adoption | pass | 0.318 [0.310, 0.327] > .20 |
| P2 · grade >+.10 and K <-.02 | **fail** | K fell .0446, but grade rose only .0474 [.0454, .0495] |
| P3 · unaided exam deficit | pass | -0.0441 [-0.0458, -0.0424] |
| P4 · confidence scenario | pass | -0.1897 [-0.1952, -0.1843] |
| P5 · human-copy displacement | pass | -0.1737 [-0.1833, -0.1645] |
| P6 · persistent withdrawal deficit | **fail** | final exam -0.0112 [-0.0127, -0.0096], smaller than locked -.03 |
| P7 · learning support | pass | K +0.0813 [0.0789, 0.0837] versus zero-learning AI |
| P8 · confidence behavioral negative control | pass | adoption difference exactly 0 [0, 0] |
| P9 · softmax adoption | pass | 0.812 and 0.557, both >.20 |

P2's combined prediction fails even though the performance–learning divergence is clear: average grades
rose less than the deliberately demanding ten-point boundary because only about one third of late actions
used the perfect-answer service.

## Baseline behavior

| Outcome | No AI | Baseline AI | Paired change |
|---|---:|---:|---:|
| late AI action | 0.000 | 0.318 | +0.318 |
| late solve | 0.250 | 0.185 | -0.065 |
| late discuss | 0.347 | 0.267 | -0.080 |
| late human copy | 0.403 | 0.229 | -0.174 |
| late homework grade | 0.827 | 0.874 | +0.047 |
| final knowledge | 0.750 | 0.705 | -0.045 |
| final unaided exam | 0.750 | 0.706 | -0.044 |
| final confidence | 0.801 | 0.611 | -0.190 |
| grade–exam gap | 0.077 | 0.168 | +0.092 |

The grade and exam result reproduces the qualitative concern motivating E7: visible assisted performance
can improve while unaided competence worsens. It should not be treated as a numerical reproduction of
Bastani et al.; E7 was not calibrated to that study.

Equal AI effort cost did little to prevent adoption: late use remained 30.05% [29.19%, 30.93%]. The
perfect grade keeps AI highly rewarding even when its nominal effort cost matches other actions.

Limiting access to 25% of students reduced population AI use to 8.32%. Because exactly 8/30 students had
access, adoption among the eligible population was roughly similar to universal access; access mainly
scaled how much of the classroom could enter the AI regime.

## Withdrawal and recovery

Students used AI on 28.72% of homeworks 6–10 before the locked withdrawal. After removal at homework 11,
AI use became zero and late behavior moved close to the no-AI control:

| Late outcome after withdrawal | Control | Withdrawal | Difference |
|---|---:|---:|---:|
| solve | 0.250 | 0.246 | -0.004 |
| discuss | 0.347 | 0.364 | +0.017 |
| human copy | 0.403 | 0.390 | -0.013 |
| knowledge | 0.750 | 0.738 | -0.011 |
| unaided exam | 0.750 | 0.739 | -0.011 |
| confidence | 0.801 | 0.775 | -0.026 |

The locked persistent-dependence prediction therefore failed. There was a measurable residual deficit,
but ten post-withdrawal homeworks allowed substantial behavioral and learning recovery. E7 supports
temporary displacement with partial recovery, not irreversible dependence.

Withdrawal did leave a network trace: strict human-source persistence was 0.388 after withdrawal versus
0.523 in control. The source structure reorganized even though aggregate action shares mostly recovered.

## Decision rules and social amplification

AI adoption is highly sensitive to the choice mechanism:

- baseline argmax: 31.83%;
- softmax tau=.10: **81.21%**;
- softmax tau=.25: **55.69%**;
- symmetric social learning eta=.10: **95.51%**.

At tau=.10, final knowledge and exam performance fell to approximately 0.631. Under symmetric social
learning, almost every student adopted AI, human copying fell to 1.41%, knowledge fell to 0.583 and the
grade–exam gap reached 0.399. Social learning was action-symmetric, but the AI's imposed perfect reward
made its observed outcome overwhelmingly attractive. This is not an AI-prevalence bonus, yet it creates
a powerful reward-transmission feedback.

This sensitivity repeats E6's warning: behavioral conclusions may generalize across decision rules in
direction, while their magnitude and network organization do not.

## Human source network

AI displaced most human copying, but the human copying that remained became more concentrated:

| Human source outcome | Control | Baseline AI |
|---|---:|---:|
| top 20% share of successful copied answers | 0.623 | 0.820 |
| source Gini | 0.646 | 0.773 |
| strict residual source persistence | 0.523 | 0.592 |

Thus AI did not simply “become the broker”—it was not in the student graph. Instead it reduced the human
exchange market and concentrated the remaining successful human sourcing among fewer students. The
strict-persistence increase was +0.069 [0.046, 0.093], precise but below the locked .10 practical delta.

Under softmax, strict human-source persistence instead fell to 0.150 and 0.074; under near-universal
socially learned AI adoption it was estimable in only 116/400 classrooms and averaged near zero. Human
source-role conclusions are therefore strongly regime-dependent.

## Learning-support counterfactual

Giving the AI an S-equivalent learning multiplier while retaining a perfect grade left adoption nearly
unchanged at 31.32%, but changed the educational result:

- final knowledge rose to 0.786, **+0.0813** versus zero-learning AI and +0.0367 versus no AI;
- final unaided exam rose to 0.787, **+0.0806** versus zero-learning AI;
- the grade–exam gap fell from 0.168 to 0.094.

The factorial learning-support main effect was +0.0748 on knowledge and +0.0743 on unaided exams. Its
interaction with persistent access was +0.0343 and +0.0339 respectively. In plain terms: longer access
is harmful when the AI substitutes for learning, but beneficial when the same high-performing service
also produces learning. Tool design is more consequential than the mere presence of an “AI” label.

This control is a mechanism counterfactual, not a calibrated representation of a particular tutor.

## Global sensitivity

Across the full $2^7$ endpoints, the largest main effects were:

| Outcome | Largest effects, ordered by absolute size |
|---|---|
| AI adoption while available | access +0.538; social learning +0.226; softmax choice +0.107; persistence +0.075; cost -0.041 |
| late human copying | persistence -0.269; access -0.208; social learning +0.073 |
| homework grade | persistence +0.101; access +0.069; AI learning +0.022 |
| final knowledge | AI learning +0.0748; social learning -0.0278; persistence -0.0079 |
| final confidence | persistence -0.180; access -0.132; imposed decrement -0.113; social learning -0.095 |
| unaided exam | AI learning +0.0743; social learning -0.0275; persistence -0.0079 |

The confidence decrement had exactly zero effect on adoption, other action shares, knowledge and exams
because confidence was deliberately measurement-only. It changed only confidence. This negative control
confirms that E7 behavior was not secretly caused by the imposed psychological penalty.

Important interactions prevent universal one-factor interpretations. Access × social learning added
0.194 AI adoption, while choice × social learning reduced the corresponding main-effect sum by 0.106.
Access × learning support added 0.050 to knowledge and exams. The targeted cost × choice interaction
reduced adoption by 0.0231; its other outcome effects were below their practical deltas.

## What is supported and what is imposed

| Statement | E7 verdict |
|---|---|
| Students can discover and adopt AI without an AI-prevalence reward | supported inside E7 |
| AI necessarily gives perfect answers | imposed, not tested |
| AI necessarily gives zero learning | imposed focal scenario; contradicted by the learning-support control as a universal claim |
| AI use necessarily lowers confidence | imposed and measurement-only; confidence evidence in the literature is mixed |
| AI adoption necessarily becomes universal | false in baseline; 31.8% late, but near-universal with symmetric social learning |
| AI primarily replaces human copying | partly: copying fell most, but solving and discussion also fell |
| AI makes human source roles disappear | false in baseline; remaining human exchange became more concentrated |
| AI withdrawal causes irreversible dependence | not supported; substantial recovery occurred |
| Guardrails/learning support can change the sign of the educational effect | strongly supported inside E7 |

## Scientific defensibility

E7 is defensible as a transparent **scenario experiment**. It cleanly separates the AI access layer from
the social graph, uses no adopter types or prevalence reward, preserves frozen V3 as an exact control,
tests alternative decision rules and includes negative and learning-support controls. The no-AI control
has exact table parity with frozen V3.

E7 is not an empirical forecast. It contains no hallucinations, detection risk, teacher intervention,
AI scarcity, prompt quality, subject differences, social norms or confidence-to-choice feedback. Its
perfect-score/zero-learning combination is intentionally severe. The confidence magnitude cannot be
interpreted causally because it was specified. The 40-homework condition lacks a matched H=40 no-AI
control, so its stable 32.3% late adoption is informative, but its absolute knowledge difference must not
be interpreted as a horizon-specific AI effect.

The peer-reviewed evidence supports concern about performance–learning separation, but also shows that
guardrails and instructional design can mitigate or reverse harm. E7 reflects that uncertainty rather
than treating “AI reduces learning and confidence” as a universal law.

## Precision record

Of 242 structural contrasts, 222 were adequate. Eleven inadequate rows were the intentionally undefined
`pA_available_late` contrast against a control in which AI was never available. Nine estimable contrasts
crossed practical-delta boundaries:

| Condition | Outcome | Estimate | 95% CI |
|---|---|---:|---:|
| softmax tau=.25 | late grade | +0.0507 | [0.0485, 0.0529] |
| withdrawal | late discussion | +0.0170 | [0.0107, 0.0231] |
| withdrawal | final K | -0.0112 | [-0.0127, -0.0098] |
| withdrawal | post-withdraw discussion | +0.0183 | [0.0122, 0.0242] |
| withdrawal | post-withdraw human copy | -0.0237 | [-0.0305, -0.0168] |
| access 25% | late discussion | -0.0189 | [-0.0218, -0.0161] |
| access 25% | final confidence | -0.0503 | [-0.0530, -0.0477] |
| access 25% | post-period discussion | -0.0188 | [-0.0216, -0.0159] |
| H=40 | human-copy success | -0.0457 | [-0.0530, -0.0384] |

Of 168 factorial effects, 166 were adequate. The two boundary-inadequate effects were cost × access on
adoption (-0.0194 [-0.0210, -0.0178]) and access × learning support on unaided exam (+0.0496
[0.0485, 0.0507]).

## Evidence files

- `runs/E7/derived/structural_summaries.parquet` — SHA-256 `8619cc08ce0d89ba...`
- `runs/E7/derived/structural_contrasts.parquet` — SHA-256 `ab83f3ec5fb40648...`
- `runs/E7/derived/factorial_effects.parquet` — SHA-256 `cab96596a74878ed...`
- `runs/E7/derived/predictions.parquet` — SHA-256 `3cb36ffe357ed01e...`
- `runs/E7/derived/report.json` — SHA-256 `7a9578d0d5c868f4...`
- `runs/E7/derived/hashes.json` records all 17,307 manifested hashes and independently hashes to
  `be47d6d07d483054...`.

## Conclusion

In E7's severe substitution scenario, a universally accessible perfect-answer AI becomes a major fourth
action, displaces all three human behaviors, raises visible grades, lowers knowledge and unaided
performance, widens the performance–competence gap and concentrates the remaining human source network.
Those harms are not inevitable properties of AI: withdrawal permits substantial recovery, and a
learning-support mechanism reverses the knowledge effect without reducing adoption. The scientifically
defensible conclusion is about **AI design and substitution**, not “AI always harms students.”
