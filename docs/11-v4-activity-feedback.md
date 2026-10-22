# A22 — V4.1 activity and V4.2 feedback model

Implementation specification, 2026-09-24. Authorized by the user's request to implement V4.1/V4.2 and run analyses. V1–V3 and E8 remain unchanged. This amendment applies only to the separate V4 engine. It permits within-homework activities and feedback-dependent behavior; the contact graph and contact weights remain fixed. No AI, forgetting, evolving friendship, norm, fatigue or retrieval-induced exam learning is included. No LLM agents are used.

## Scope and interpretation

This is a one-skill, discrete-time model with a packet of ten binary item answers per homework. Activities can change during a homework. All defaults are declared mechanistic scenarios, not measured student parameters. The inherited alpha=0.0584 originates in the V1 target trajectory, not educational data. One V4 attempt uses alpha/3; checking or explaining uses alpha/6. These are explicit rates, not a claim that the full V4 learning trajectory matches V3.

The literature basis is the reviewed `v4-evidence-based-plan.md` delivered in the planning task: instrumental vs expedient help, perception vs learning, conditional failure response, active peer discussion, and time constraints. Literature supports candidate mechanisms, not these equations. New experiment comparisons are internal causal contrasts between declared rules.

## API and persistent state

`V4Params`, `V4Draws(seed, replicate, N, M_H, M_E)`, `simulate_v4(params, graph, draws, condition=...) -> V4Log`. `simulate_legacy` delegates unchanged to V3. Separate V4 raw schemas; no changes to historical record schemas.

State per student: K (latent competence), C (predicted unaided success), B[attempt,hint,answer,check] (learned grade benefit), R (perceived controllability), and private directed access A[observer,target,help mode]. Traits use the exact V3 trait stream and transform, independently of graph position. Initially C=K0, R=.5, B=K0 and A=.5 on edges. Unlike V3 Q, B contains benefit before effort cost; the K0 prior is therefore deliberate, with .25/.75 prior controls. Effort is charged once in choice.

At homework start packets, hints, pending requests and jobs clear. K,C,B,R,A persist. V4.1 holds C and R fixed at initialization; V4.2 enables observation-based C updates and optionally exam feedback. B and A learn in both versions. R changes only under the declared exam response rule. No student chooses by reading latent K (own or peer), global graph properties or derived flows.

## Activities and time

Default horizon H=20, N=30, T=12 ticks/homework. Attempt costs 3 ticks; check 2; requesting 1 followed by waiting/service; explanation service 2 for both participants; answer service 1 for both; wait and submit 1. At most one occupied interval per student at a time. Submitting closes own work but leaves the student available to help. At the deadline the current packet is submitted automatically; no packet receives grade 0 and is separately marked incomplete.

Requests choose a sorted neighbor weighted by frozen contact opportunity times private access A for that help mode. Only one pending request per requester, no resampling until it resolves. It becomes eligible next tick and times out after 2 waiting ticks. Pending requests are ordered by independent semantic priority. Busy providers cannot accept. Idle providers voluntarily accept with probability logistic(logit(.8)+2*(reverse A-.5)-.8*urgency), where urgency=(1-t/T) subtracted from 1 when provider has not submitted (i.e. t/T); submitted providers have zero urgency. A requested answer also requires a packet at service start. Explanation needs no existing correct packet. Provider identity is selected before these hidden availability checks. Private access changes only on a completed direct request: A += .2*(success-A). Outcome means delivered service, not answer correctness. Timeouts remain generic unavailability to the requester; true blocking causes are researcher logs only. No normative dislike update exists.

Matched participants cannot do other work during service. No same-tick forwarding: packets available at tick start are the only packets eligible to be captured for service; completions from prior intervals are now available. Ticks represent declared opportunity units, not calibrated minutes. Pair capacity is limited by time, not a second fixed transfer cap. A resource-ablation control allows helpers to serve without losing their own work time; this deliberately unrealistic counterfactual is labeled as such.

## Choice, outcomes and learning

Let v be the current privately estimated packet grade, or 0 without a packet. Let c=C when self-assessment is causal, otherwise initial C. Set bS=(B_S+c)/2, bD=(B_D+c+.25*(1-c))/2, bA=B_A. Expected access aD/aA is the A-weighted contact mean. L = learning_value * R * (1-c), with learning_value=.25.

Unpenalized activity scores: attempt bS-v+L; explanation aD*(bD-v)+1.5L; answer aA*(bA-v); check .5*(1-v)+.5L; wait .025; submit 0. Subtract kappa*nominal_duration/12 from attempt, explanation, answer and check only. Nominal explanation duration includes request+service+follow-up attempt; answer includes request+service. If a hint is available, predicted attempt correctness is bS+.25*(1-bS). Check requires a packet; social requests require a neighbor; submit requires a packet; an activity must fit before the deadline. Pending work cannot be submitted until completed. No future exact grade or true knowledge enters these scores.

Choose softmax(score/.10) mixed with .06 uniform exploration. Required comparator: argmax with the same exploration. Scores use a common semantic choice draw at each student/homework/tick. Isolates have no social activities; waiting, checking, submission and individual work are the V4 equivalents of the legacy solo feasible set.

An attempt produces a new answer id and latent K increment (alpha_i/3)*(1-K), multiplied by 1+hint when a delivered hint is consumed. Independent probability is post-attempt K; guided probability adds hint*(1-K). Delivered hint strength is .15+.35*K_provider at service start (a generative outcome rule, never target-choice information). A learner receives no knowledge merely for requesting/receiving a hint. The explaining provider practices at alpha_i/6. Checking practices at alpha_i/6 and returns the current packet's actual fraction correct through an assumed reliable checking rubric, not a solution. This feedback affordance is an explicit model assumption. Checking does not automatically repair a packet. Answer delivery preserves exact item bits, root and answer id and increases route depth; it grants no direct knowledge. A later attempt/check can produce learning. No action decreases K in this scope.

At final grading, each benefit B for an enacted attempt/hint/answer/check is updated toward the homework grade, weighted by its fraction of those activities; unsuccessful requests count as experience. This is coarse episode credit assignment, not omniscient attribution. Feedback never directly penalizes the answer action. Check observations can update C when enabled. Final grades update C at eta_C=.1, weighted 1 for unaided packets or misattribution=.2 for assisted packets. Missing work is not evidence of wrong knowledge and does not update C. A guided packet remains assisted until replaced by an independent attempt. Every generated packet stores assistance status separately from provenance.

Checking is feasible once per currently held answer id; it becomes feasible again after a new attempt or a different received packet. The helper-time-free counterfactual permits concurrent own work and help, still limits a provider to one new service match per tick, and retains explanation-practice gains. It changes available work capacity and its downstream learning opportunities; it is deliberately not a realistic classroom.

## V4.2 exam response

Exams occur every 5 homeworks using the historical semantic exam stream, 30 items, P(correct)=K. They never change K in V4.1/4.2. Prediction at assessment is recorded separately from subsequent C. With feedback enabled, release occurs at the start of homework exam_h+delay+1; delay counts full intervening homeworks (default 1). Feedback past the simulation horizon is not delivered early.

On release C += .5*(score-C). Recalibration leaves R unchanged. Constructive response: R = clip(R+.4*(.7-score)*(1-R)). Withdrawal-capable response: R = clip(R+.4*(score-prediction_at_exam)); positive surprises permit recovery. These response equations encode individual reactions; their population consequences are experimental outputs, not new psychological discoveries.

## RNG, logs and experimental boundaries

New stream codes 101 choice, 102 target, 103 acceptance, 104 priority, 105 attempt items. Pre-generate full per-homework tensors indexed by tick/student (item uniforms have a trailing item dimension); shape uses a fixed maximum tick extent 32, preserving prefixes across deadline conditions. Existing codes 9 traits and 6 exams remain untouched. Changing condition names never affects draws. Endogenous histories can diverge under common inputs.

Raw tables: events (activity start/end, K before/after, selection probabilities/scores, observable packet estimates), requests (start/finish, target, mode, outcome, researcher blocking causes, access before/after), packets (id, parent, root, depth, item bits, assistance), students (per-homework pre/post state, grade, completion and activity counts), exams (score, predicted score, release), feedback (pre/post C and R), graph and traits. Scalar states and all four B values are logged. Source roles, switching, success, congestion and copying shares are derived from raw data; summary tables are never causal state.

Tests cover semantic pairing, local-only choice, no overlapping intervals, exact copies, hint learning only through attempts, direct-request updates, delayed feedback, no effect before release, unchanged K at exam/feedback, response equations, bounds, deadline feasibility, isolates, raw reconstruction, and exact V3 delegation. Interpretation distinguishes mixed sequences from V3's mutually exclusive homework actions.
