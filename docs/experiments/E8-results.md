---
type: experiment
id: E8
status: REPORTED
date: 2026-09-20
tags:
  - experiment
  - results
  - v3
  - ai-policy
  - guardrails
---
# E8 · Results: controlled tutoring reverses unrestricted-AI learning loss, but still displaces peers

Results of [[docs/experiments/E8-preregistration]] under frozen V3. E8 completed **23,000 runs**:
1,200 primary, 7,400 mechanism-surface and 14,400 robustness runs. The preregistration SHA-256 was
`0dab017184c6b5e17859ff3053a6d2304aba168a37374bb24405b5105a2a9ba2`; the clean run used commit
`49d00e8`; and frozen V3 remained at `876556a`. Runtime was 38.4 minutes. There were no deviations or
stderr. An independent audit rehashed **32,615 files** with zero missing, mismatched or extra files, and
all **222 tests** passed after the run.

## Main answer

Universal access did not produce universal use. With personal reinforcement and no AI-prevalence term,
late use stabilized at **31.37%** [30.52%, 32.22%] for unrestricted answer AI and **22.17%** [21.43%,
22.94%] for the controlled tutor. About 43% of students tried either service at least once, but controlled
use was less persistent: 35.9% of controlled-AI adopters had abandoned it by the late window versus 15.2%
of unrestricted-AI adopters.

The educational directions diverged. Relative to no AI:

- unrestricted AI raised late homework grades 4.82 points, reduced knowledge **3.30 points**, reduced the
  unaided exam **3.36 points**, and widened the grade–exam gap **8.17 points**;
- controlled AI raised grades only 0.97 points, increased knowledge **2.86 points**, increased the unaided
  exam **2.86 points**, and narrowed the grade–exam gap **1.90 points**.

Controlled tutoring therefore beat unrestricted AI by 6.16 points in knowledge and 6.22 points on the
unaided exam. The result was directionally stable under argmax and both softmax decision rules, and at
20- and 40-homework horizons.

These are conditional model consequences. The tutor's S-equivalent learning increment, verified feedback
and answer withholding are imposed treatment mechanisms. Voluntary uptake, persistence, population-level
effects, substitution away from human behavior and social amplification are outputs.

![[figures/E8-primary-trends.png]]

## Primary comparison

| Outcome | No AI | Unrestricted | Controlled | U − no AI | T − no AI |
|---|---:|---:|---:|---:|---:|
| late AI use | 0 | 0.314 | 0.222 | +0.314 | +0.222 |
| ever adopted | 0 | 0.430 | 0.428 | +0.430 | +0.428 |
| persistent use | 0 | 0.319 | 0.220 | +0.319 | +0.220 |
| late solve | 0.256 | 0.194 | 0.219 | -0.063 | -0.037 |
| late discuss | 0.344 | 0.262 | 0.292 | -0.081 | -0.052 |
| late human copy | 0.400 | 0.230 | 0.267 | -0.170 | -0.133 |
| late homework grade | 0.826 | 0.874 | 0.836 | +0.048 | +0.010 |
| final knowledge | 0.751 | 0.718 | 0.779 | -0.033 | +0.029 |
| final unaided exam | 0.751 | 0.717 | 0.779 | -0.034 | +0.029 |
| grade–exam gap | 0.075 | 0.157 | 0.056 | +0.082 | -0.019 |
| recorded confidence | 0.800 | 0.853 | 0.811 | +0.053 | +0.010 |

Confidence followed homework grades and did not affect decisions. Unlike E7's imposed decrement scenario,
E8 predicts higher measured confidence under unrestricted AI because visible performance is high. Neither
result estimates real psychological confidence; together they demonstrate why an assumed confidence
penalty should not be treated as an emergent finding.

## Locked predictions

Eight of nine directional predictions passed; the tenth item was deliberately an open-direction
classification.

| Prediction | Result | Evidence |
|---|---|---|
| P1 · voluntary use | pass | late U 0.314 and T 0.222; both lower bounds >.05 |
| P2 · unrestricted adoption advantage >.05 early and late | **fail** | early +.032 [.030, .034], late +.092 [.087, .097] |
| P3 · unrestricted performance illusion | pass | grade–exam gap +.0817 [.0792, .0842] |
| P4 · controlled protection | pass | T−U K +.0616 [.0597, .0635], exam +.0622 [.0601, .0643] |
| P5 · unrestricted human displacement | pass | U−T discussion -.0294, human copy -.0370 |
| P6 · controlled versus no AI | open | K +.0286; exam +.0286; positive but exam below locked .05 practical delta |
| P7 · controlled effort sensitivity | pass | cost 2−1 adoption -.1052 [-.1102, -.1004] |
| P8 · tutor-learning sensitivity | pass | $m_T=1.5-.5$ K +.0317 [.0304, .0331] |
| P9 · decision-robust use | pass | both interfaces used above .05 under all three rules |
| P10 · decision-rule sensitivity | pass | every softmax/argmax adoption contrast exceeded .02 |

P2 failed only because the early adoption difference was 3.2 rather than more than five points. The late
difference exceeded the threshold.

## Unrestricted versus controlled trends

The unrestricted reference supplied perfect answers, copy-equivalent incidental learning and zero effort.
Its use continued rising across the semester. Controlled use plateaued near 22% because partial help and
required effort produced less immediate reward. Nearly identical ever-adopter shares but different late
shares show that the policy primarily changed persistence after trial, not initial exposure.

The unrestricted result reproduces the qualitative performance–learning separation in Bastani et al.
(2025), [DOI 10.1073/pnas.2422633122](https://doi.org/10.1073/pnas.2422633122). The positive controlled
direction is consistent with scaffolded-tutor evidence from the same study and Kestin et al. (2025),
[DOI 10.1038/s41598-025-97652-6](https://doi.org/10.1038/s41598-025-97652-6). E8 was not calibrated to
either study and does not numerically reproduce their effects.

Unrestricted harm was not universal across mechanisms. All six unrestricted cells with the largest
incidental-learning multiplier, $m_U=.50$, met the locked noninferiority rule; the other 12 did not. No
unrestricted cell met the stronger useful criterion. Thus the model attributes harm to answer substitution
with insufficient learning, not to an AI label.

## Controlled-tutor policy surface

All 18 controlled cells were educationally safe under the locked rule. Eleven were useful, 15 retained
viable voluntary use, and none met the strict three-part performance-illusion rule. However, 14 produced
practically important discussion or human-copy displacement.

| Classification | Controlled cells |
|---|---:|
| safe | 18/18 |
| useful | 11/18 |
| viable voluntary uptake | 15/18 |
| social displacement | 14/18 |
| green | 1/18 |
| amber | 17/18 |
| red | 0/18 |

The only green cell combined strong learning support ($m_T=1.5$), no immediate correctness scaffold and
cost 2. It improved the exam 1.77 points and did not practically displace discussion or copying, but late
use was only 4.21% [3.84%, 4.61%], below the viability threshold. Therefore **no controlled cell was both
green and viable**.

A more attractive strong tutor ($m_T=1.5$, $s_T=.25$, cost 1) reached 22.78% late use and improved the
exam 4.55 points, but reduced discussion 4.86 points and human copying 13.76 points. At $s_T=.50$, cost 1,
late use reached 26.35% and the exam improved 5.07 points, while discussion and copying fell 5.90 and
15.50 points. Stronger scaffolding therefore increased both educational benefit and displacement.

![[figures/E8-controlled-policy-map.png]]

The strict surface-level performance-illusion flag required a grade increase above five points, an exam
decrease beyond one point and a gap increase above five points simultaneously. No cell crossed all three;
the unrestricted reference nevertheless passed preregistered P3 because its gap widened 8.17 points. This
difference between the two locked rules is retained rather than harmonized after seeing results.

## What “spread” means with universal access

Because everyone had access, baseline adoption was not diffusion of access. With personal learning only,
ever-adopter assortativity was slightly negative (approximately -.03) and neighbour-lag associations were
also slightly negative. E8 therefore provides no evidence of peer contagion in the baseline policy arms;
adoption mainly arose from neutral trials followed by personal reinforcement.

When the preregistered action-symmetric social-learning mechanism was activated, averaged across the other
robustness factors:

| Social-learning effect | Unrestricted | Controlled |
|---|---:|---:|
| late AI use | +0.259 | +0.129 |
| late discussion | -0.098 | -0.054 |
| late human copying | -0.087 | -0.010 |
| final knowledge | -0.055 | +0.0045 |
| final unaided exam | -0.055 | +0.0044 |
| grade–exam gap | +0.085 | -0.020 |

The rule did not favor AI by name. It transmitted observed rewards for every action. Perfect unrestricted
answers were more rewarding, so peer observation amplified unrestricted use and harm much more strongly.
The same generic mechanism changed no-AI behavior too: it increased copying and reduced knowledge by about
1.9 points. These are model mechanism effects, not evidence that real students copy classmates' AI use at
these rates.

## Robustness

Decision rules changed magnitudes but not the central educational direction. Each contrast below uses its
matched no-AI decision-rule control:

| Rule | U use | U exam change | T use | T exam change |
|---|---:|---:|---:|---:|
| argmax | 0.309 | -0.0322 | 0.221 | +0.0291 |
| softmax $\tau=.10$ | 0.812 | -0.0791 | 0.279 | +0.0410 |
| softmax $\tau=.25$ | 0.564 | -0.0650 | 0.266 | +0.0279 |

At H=40, the matched argmax unrestricted deficit was -4.03 exam points and the controlled advantage was
+3.85 points. Late use remained 31.73% and 22.30% respectively. The contrast therefore persisted rather
than being a short-horizon transient.

Changing SBM to ER or shuffling complete trait bundles across graph positions had near-zero marginal
effects on adoption, knowledge and exams. This is expected under universal access: the graph does not
mediate availability. It still mediates human help and optional peer observation.

## Human sociograph consequences

Both interfaces displaced every human action, especially copying. Remaining successful human sourcing
became more concentrated:

| Source metric | No AI | Unrestricted | Controlled |
|---|---:|---:|---:|
| top-20% source share | 0.625 | 0.818 | 0.756 |
| source Gini | 0.647 | 0.772 | 0.736 |
| strict source persistence | 0.520 | 0.591 | 0.586 |

Controlled tutoring preserved more human interaction than unrestricted AI but did not preserve the no-AI
social system. A school optimizing only knowledge would miss this tradeoff.

Initial-K inequality changes were negligible or inconclusive in the primary comparison. E8 does not show
a robust equity improvement or harm from either reference interface.

## School-facing interpretation

Within E8, the most defensible school policy is not “allow AI” versus “ban AI.” It is:

1. make the permitted interface tutor-like: verified content, hints, steps and required attempts;
2. ensure AI activity creates at least solving-equivalent learning rather than answer transfer;
3. retain regular unaided assessments, because assisted grades do not identify knowledge;
4. protect peer discussion explicitly—controlled AI can improve learning while hollowing out human help;
5. monitor use and abandonment, because overly effortful guardrails can be educationally sound but ignored;
6. report a policy range rather than one predicted adoption rate.

This model does **not** establish that a real tutor has $m_T=1$, `.25` scaffold strength or the observed
adoption rate. Those are scenario coordinates. Without school data, the useful claim is the qualitative
crossover: sufficient learning-oriented support reverses the sign of the educational effect, while
immediate reward and effort govern voluntary uptake.

## Defensibility and confidence

- **Computational integrity:** high. Locked design, exact V3 parity, semantic common random numbers,
  complete run, independent hashes and 222 passing tests.
- **Internal causal comparison:** moderately high for these equations. Policy is assigned at the world
  level and paired worlds share exogenous draws.
- **Qualitative uncontrolled-versus-controlled direction:** moderate. It agrees with relevant randomized
  studies and persists across declared decision rules and horizons.
- **Exact magnitudes and adoption rates:** low. Choice rules moved unrestricted adoption from 31% to 81%.
- **Real school recommendation:** low-to-moderate as a scenario guide, low as a forecast. There is no
  calibration, bypass behavior, AI error dialogue, teacher adaptation, subject variation or longitudinal
  field validation.

The largest remaining conceptual limitation is that tutor learning is represented numerically after a
single action. E8 does not simulate dialogue, explanation quality, student prompting or attempts to defeat
guardrails. A more agentic system should be used only to test whether it reproduces this transparent
mechanism envelope, not to replace it.

## Precision and evidence files

Of 112 primary contrasts, 100 passed the locked boundary-precision rule; ten were structurally
non-estimable comparisons against no-AI adoption-network outcomes, one was inconclusive and one straddled
a practical boundary. Of 1,008 surface contrasts, 742 were adequate; 180 were structurally non-estimable
and 86 crossed practical boundaries. All remain in the derived tables.

- `runs/E8/derived/primary_summaries.parquet` — SHA-256 `6161922eeb852c22...`
- `runs/E8/derived/primary_trajectories.parquet` — SHA-256 `2cb95e721bc62585...`
- `runs/E8/derived/primary_contrasts.parquet` — SHA-256 `046ac87bae6a8f7c...`
- `runs/E8/derived/surface_contrasts.parquet` — SHA-256 `df4e493519af2b7a...`
- `runs/E8/derived/robustness_summaries.parquet` — SHA-256 `2ffcee8476b3dd2b...`
- `runs/E8/derived/policy_map.parquet` — SHA-256 `64181051f39f4ee2...`
- `runs/E8/derived/predictions.parquet` — SHA-256 `5c8b6255b129ce1d...`
- `runs/E8/derived/report.json` — SHA-256 `95963e9d19b05d0a...`

## Conclusion

Under universal access, students voluntarily used both AI interfaces. Unrestricted complete answers
produced higher and more persistent use, better visible grades, lower knowledge and a wider grade–exam
gap. Controlled tutoring produced less use but higher knowledge and unaided performance than both
unrestricted AI and no AI. That educational gain did not automatically protect the classroom social
system: nearly every viable controlled policy still displaced human help. Schools should therefore treat
AI guardrails, unaided assessment and protected peer learning as a joint teaching design problem.
