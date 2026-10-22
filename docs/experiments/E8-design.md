---
type: experiment-design
id: E8
status: APPROVED
date: 2026-09-20
tags:
  - experiment
  - design
  - v3
  - ai-policy
  - guardrails
---
# E8 · Draft design: no AI, unrestricted answer AI, and controlled tutor AI

Approved on 2026-09-20. This design is preserved as the rationale for the exact locked preregistration;
the preregistration, not this document, controls the E8 run.

## 1. School-policy question

Every student has access to AI in both AI conditions, but using it is voluntary. E8 asks how classroom
behavior and learning develop under three school environments:

1. **No AI:** frozen V3 actions S, D and C only.
2. **Unrestricted AI:** every student may select AI and receive a complete answer with little effort.
3. **Controlled tutor AI:** every student may select AI, but the interface gives accurate, stepwise hints,
   requires an attempt, and does not reveal the complete answer.

The treatment is the AI affordance, not an assigned student type. E8 does not label students as cheaters,
responsible users, adopters or resisters. Adoption and persistence must arise from neutral exploration,
personal reinforcement and, only in declared conditions, action-symmetric observation of peers.

The intended output is a policy envelope for schools: when does a controlled tutor protect or improve
learning, when is it rejected because it requires effort, and when does unrestricted AI produce a widening
gap between assisted grades and unaided competence?

## 2. Peer-reviewed basis

The closest direct precedent is Bastani et al. (2025), *Proceedings of the National Academy of Sciences*,
DOI [10.1073/pnas.2422633122](https://doi.org/10.1073/pnas.2422633122). Nearly 1,000 high-school
mathematics students were assigned by classroom to conventional resources, a GPT-4-like unrestricted
interface, or a guardrailed GPT tutor. The unrestricted interface improved assisted practice performance
but reduced later unassisted examination performance. The tutor was supplied with the correct solution
and common mistakes, instructed not to disclose the complete solution, and guided students step by step;
it improved assisted practice without the same examination penalty.

Kestin et al. (2025), *Scientific Reports*, DOI
[10.1038/s41598-025-97652-6](https://doi.org/10.1038/s41598-025-97652-6), randomized 194 university
physics students in a crossover design. Their carefully prompted and scaffolded AI tutor produced larger
short-term learning gains in less time than an active-learning class. The tutor used active learning,
cognitive-load management, scaffolding, targeted feedback and self-pacing. The comparison was not an
unrestricted-chatbot arm and did not establish that every guardrailed tutor will work.

The broader intelligent-tutoring literature also supports representing tutoring as step-level feedback
rather than answer delivery. VanLehn (2011), *Educational Psychologist*, DOI
[10.1080/00461520.2011.611369](https://doi.org/10.1080/00461520.2011.611369), reviewed experiments
comparing human, computer and no tutoring and reported that step-based intelligent tutors could approach
the effectiveness of human tutoring. A 2025 K-12 systematic review found generally positive but
heterogeneous results and weaker advantages against other tutoring systems: Létourneau et al., *npj
Science of Learning*, DOI [10.1038/s41539-025-00320-7](https://doi.org/10.1038/s41539-025-00320-7).

These studies justify the **mechanisms** used in E8—answer withholding, guided steps, required attempts,
accurate feedback and unaided measurement. They do not identify transportable V3 parameter values.
Consequently E8 must not calibrate its numerical effects to a reported percentage and must sweep tutor
effectiveness.

## 3. Causal boundary

- Frozen `v3.py` remains untouched. E8 is a separate intervention layer and exact no-AI control.
- AI remains an external service, not a graph node. Universal access must not create an artificial star or
  mechanically change degree, centrality, routing or human source-role measures.
- Both AI regimes make one fourth top-level action, A, feasible for every student from homework 2 onward.
  The feasible-action count and neutral exploration probability are therefore identical across the two AI
  regimes.
- There is no AI-prevalence utility. Personal Q-learning uses only the student's realized reward.
- Optional peer observation updates S, D, C and A symmetrically. It is a declared social-learning
  treatment, not an AI-specific contagion bonus.
- Confidence remains measurement-only and receives no AI-specific penalty. E8 is about use, learning and
  social reorganization, not an uncalibrated confidence claim.
- Diagnostic exams remain unaided and state-inert.

## 4. Common voluntary adoption rule

Let the feasible actions be S, D, C and A. Initialize

$$Q_i^A(0)=K_{0i}-\kappa_i,$$

identically to the three human actions. AI utility is

$$U_i^A=Q_i^A.$$

The frozen V3 action-neutral exploration and argmax rule apply over all feasible actions. A softmax
robustness condition is mandatory because E6 and E7 found large decision-rule sensitivity. The same
semantic strategy draw is reused across paired no-AI, unrestricted and controlled worlds.

Every observed adoption pattern is therefore a response to experienced outcomes under the choice model.
Universal access does not imply universal use.

## 5. AI outcome mechanisms

### 5.1 Unrestricted answer AI

Selecting A returns a complete proposed answer with correctness $r_U$. The reference condition uses
$r_U=1$ to retain the severe E7 boundary; robustness uses $r_U\in\{.80,.90,1.00\}$. For each homework
item, correctness is generated from the existing semantic item uniform so paired accuracy conditions use
common random numbers.

Incidental learning is

$$K_i'=K_i+m_U\alpha_i(1-K_i),$$

with $m_U\in\{0,.10,.50\}$. Zero retains E7; `.10` is the frozen human-copy learning fraction; `.50`
tests meaningful learning even from unrestricted use. Reference effort cost is zero, with an equal-cost
robustness condition of one.

### 5.2 Controlled tutor AI

The tutor knows a verified solution and common errors but does not reveal the final answer. It gives one
step or hint at a time and requires the student to attempt the work. The model represents the resulting
active engagement, not language generation itself.

Knowledge after a tutored attempt is

$$K_i'=K_i+m_T\alpha_i(1-K_i),$$

where $m_T\in\{.50,1.00,1.50\}$. The middle value equals the learning increment of independent solving;
the range allows controlled AI to be worse than, equal to, or better than ordinary solving rather than
assuming a benefit.

The probability of a correct submitted item is

$$p_i^T=K_i'+s_T(1-K_i'),$$

where scaffold strength $s_T\in\{0,.25,.50\}$. Thus a tutor can improve assisted performance but cannot
guarantee a correct answer. Correctness uses the same semantic item uniform as paired S and unrestricted
conditions. The required attempt has effort cost one. A cost-two robustness condition represents a
frustrating or time-consuming interface.

These are deliberately separable dimensions: $m_T$ governs durable learning and $s_T$ governs immediate
task support. This prevents an improved homework score from being silently counted as knowledge.

### 5.3 Reward and learning

For either AI interface,

$$R_i=G_i^H-\kappa_i c_A,$$

and the chosen Q-value receives the same personal update as every V3 action. The controlled tutor is not
given a prosocial utility bonus. If its learning benefit does not produce enough immediate reward to
offset effort, students may avoid it; that is a policy-relevant outcome rather than a model failure.

## 6. Experimental blocks

### Block A · Primary three-regime trends

Use matched graph, trait and semantic draws with N=30, H=20, SBM, R=3 and frozen V3 defaults. Run at least
400 paired replicate worlds per condition.

| Condition | Universal access | AI mechanism |
|---|---:|---|
| `E8-A-none` | no | exact frozen V3 |
| `E8-A-unrestricted` | yes | $r_U=1$, $m_U=.10$, cost 0 |
| `E8-A-controlled` | yes | $m_T=1$, $s_T=.25$, cost 1 |

The unrestricted reference uses copy-equivalent incidental learning rather than E7's zero-learning
extreme. E7 remains the declared $m_U=0$ boundary.

### Block B · Mechanism response surface

Estimate where the conclusion changes rather than select a favorable controlled-AI point:

- unrestricted: $r_U\in\{.80,.90,1.00\}$ by $m_U\in\{0,.10,.50\}$ by cost $\in\{0,1\}$;
- controlled: $m_T\in\{.50,1.00,1.50\}$ by $s_T\in\{0,.25,.50\}$ by cost $\in\{1,2\}$;
- matched no-AI control.

Report the region in which each interface improves or harms final unaided performance versus no AI, and
the region in which controlled AI dominates unrestricted AI on learning while retaining nontrivial
voluntary adoption.

### Block C · Spread and robustness

Universal access is constant. Cross the three primary regimes with:

- personal learning only versus action-symmetric social learning $\eta_{social}=.10$;
- frozen argmax versus softmax $\tau\in\{.10,.25\}$;
- random trait-to-node assignment versus the frozen trait-shuffle null;
- SBM versus ER topology;
- H=20 versus a matched H=40 control set.

Because access never varies, the social-learning contrast identifies outcome observation, not access
diffusion. Describe “spread” as changing voluntary adoption across the friendship network, never as the AI
traveling from one student to another.

## 7. Outcomes and trend plots

Report trajectories by homework, not only final averages:

- AI action share, first use, ever-use share, persistent-use share and abandonment after first use;
- S, D and C shares and which behavior A displaces;
- assisted homework grade, final knowledge, unaided exam and grade–exam gap;
- learning per AI use and reward per AI use;
- human-copy success, source concentration and persistent human source roles;
- adoption assortativity, within/between-community clustering and neighbour-lag association;
- distributional effects by initial-knowledge quintile, without turning quintiles into agent types;
- fraction of classrooms in which each AI regime beats no AI, not only the mean effect.

Neighbour-lag association is descriptive. The paired $\eta_{social}=0$ versus `.10` contrast is the causal
simulation test of peer-outcome observation.

## 8. Proposed hypotheses to lock before running

These directions should be reviewed and assigned practical thresholds only after a smoke-based variance
calculation that does not inspect treatment effects.

1. Both AI interfaces will receive voluntary use without an AI-prevalence term.
2. Unrestricted AI will have higher early adoption and homework grades than controlled AI because it
   combines high correctness with lower effort.
3. Unrestricted AI will produce a larger grade–exam gap than both controlled AI and no AI.
4. Controlled AI with $m_T\ge1$ will produce greater knowledge and unaided performance than unrestricted
   reference AI; whether it beats no AI is an empirical simulation question, not assumed.
5. Unrestricted AI will displace more human copying and discussion than controlled AI.
6. Symmetric peer-outcome learning will amplify whichever AI interface has the more attractive realized
   reward; no direction between interfaces is prespecified across the whole response surface.
7. Controlled-AI adoption will be more sensitive to effort cost, while its learning result will be most
   sensitive to $m_T$.
8. Exact adoption levels and source-network organization will remain decision-rule sensitive.

## 9. School-facing decision rules

E8 should not recommend a policy from statistical significance alone. Before running, lock school-facing
criteria such as:

- **educationally safe:** unaided exam and final knowledge are not practically below no AI;
- **useful:** at least one unaided learning outcome is practically above no AI;
- **performance illusion:** homework grade rises while unaided exam falls and the gap exceeds a locked
  threshold;
- **social displacement:** discussion or human help falls beyond a locked threshold;
- **viable controlled policy:** controlled AI is educationally safe and retains a locked minimum voluntary
  adoption rate across both argmax and at least one softmax rule.

The final school output should be a traffic-light policy map over tutor learning support, immediate
scaffolding and effort cost. It must show assumption ranges and failure regions, not a single forecast.

## 10. Interpretation limits

E8 can estimate consequences inside a declared behavioral model. Without school data it cannot estimate
real adoption rates, the true effectiveness of a tutor, how often students bypass guardrails, or the size
of effects at a particular school. “Controlled” means the interface prevents full-answer substitution;
it does not mean students become intrinsically diligent.

The controlled reference is intentionally modest: S-equivalent learning, partial immediate support and
ordinary effort. The response surface—not that reference point—is the main scientific result. A later
empirical study could narrow the parameter ranges using observed AI-use traces, homework, delayed unaided
tests and student-network surveys.
