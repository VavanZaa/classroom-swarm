---
type: blueprint
version: V1.0
received: 2026-09-18
status: SOURCE (amended; see table)
tags:
  - spec
---
# Classroom Swarm V1.0: original blueprint

> [!important] Read this first
> Below is the blueprint as Vavan sent it on 2026-09-18, **verbatim**. Amendments A1–A21 **override** it. The current specification is docs 01–10. Where they differ from this text, they win. Never implement a section listed in the "Overrides" column from this file.

| # | Amendment (approval date stated when later than 2026-09-18) | Overrides | Current spec |
|---|---|---|---|
| A1 | In M0–M3, an exam every $F_E$ homeworks is a **diagnostic probe**: it measures $G^E$ (so $\Delta_{GK}$ exists from the start) but changes no state ($C, E, Q$ unchanged). | §24–26, §28 step 11, §36 | [[docs/01-model-hierarchy]], [[docs/03-event-schedule]] |
| A2 | New ladder: M0 fixed tendencies → M1 +personal reinforcement → M2 +peer exposure → M3 +confidence affects decisions → M4 +exam feedback updates confidence → M5 +exam feedback changes effort. | §36, §47 | [[docs/01-model-hierarchy]] |
| A3 | $R$ is **not** a model stage. It is a crossed experimental factor, $R\in\{1,3\}$ (reference 3). The null for any comparison is M0 **at the same $R$**. $M_k(R{=}3)-M_k(R{=}1)$ measures multi-hop. | §36, §38, §40 | [[docs/01-model-hierarchy]], [[docs/06-validation-and-ablations]] |
| A4 | One new graph per Monte Carlo replicate, reused by every model variant in that replicate. Disconnected graphs and isolates are **kept** (never redrawn). SBM = 3 communities × 10, $p_{in}=6/13$, $p_{out}=6/65$. Generators come from NetworkX. | §30 | [[docs/04-network-generation]] |
| A5 | $C$ updates from homework grades in **every** model ($M_i$ always measurable) but is causally inert until M3 ($\beta_C=0$). $X$ is always measured and inert until M2 ($\beta_P=0$). | §36, §47 | [[docs/01-model-hierarchy]], [[docs/02-state-and-parameters]] |
| A6 | $Q_i^a(0)=q_0$ for all actions. Reference $q_0=K_0-\kappa=0.35$. **Mandatory** robustness axis $q_0\in\{0,\,K_0-\kappa,\,K_0\}$ (fixes the early-choice lock-in artefact). | §4.5, §28 init, §31 | [[docs/02-state-and-parameters]] |
| A7 | Separate named RNG streams derived from one master replicate seed. Common random numbers across model variants (same graph, initial students, question and exam draws). | §44 | [[docs/05-rng-and-reproducibility]] |
| A8 | Broker null: a degree-preserving double-edge-swap ensemble ($L=200$ dev, 500–1000 final) with student identities and attributes fixed. Report $Z_i^B=(B_i-\mu_i^{null})/\sigma_i^{null}$. | §39 | [[docs/06-validation-and-ablations]] |
| A9 | **No LLM anywhere in V1.** Core package renamed away from "AI student". | — | `AGENTS.md` |
| A10 | Canonical outputs are machine-readable (CSV/Parquet/JSON/GraphML). Obsidian and 3D visualisation come later and stay outside the core. | — | [[docs/07-output-schema]], [[docs/08-visualization]] |
| A11 | **Isolated students ($\deg=0$) can't choose D or C:** $U^D=U^C=-\infty$ before softmax, so $P(S)=1$. $p_C^0$ means the copying tendency *when copying is feasible*. Feasibility is logged. | §11 isolate branch, §28 step 3 | [[docs/03-event-schedule]] |
| A12 | $q_0$ is **derived**, $q_0=K_0-\kappa$, whenever $K_0$ or $\kappa$ changes, and never clipped. Only the explicit $q_0$ robustness run overrides it. $b_C$ alone sets the initial copy bias. | §31 | [[docs/02-state-and-parameters]] |
| A13 | SBM = **3 near-equal communities at every $N$** (7/7/6, 10/10/10, 14/13/13). $p_{out}=\bar d/(rw+b)$ with $w=\frac1N\sum_g n_g(n_g-1)$ and $b=N-1-w$. | §30 | [[docs/04-network-generation]] |
| A14 | Watts–Strogatz only with even $k=\bar d\in\{4,6,8,10\}$ (reference 6); invariant $k<N$. | §30 | [[docs/04-network-generation]] |
| A15 | Broker reporting: $Z^B$ (`NA` when $\sigma^{null}=0$, case kept), $B^{excess}=B-\mu^{null}$, and permutation $p=(1+\#\{B^{null}\ge B^{obs}\})/(L+1)$. First scope: M0, M1, M2 at $R=3$, SBM, reference parameters, $L=200$. A block-preserving null is added before any community-bridge claim. | §39 | [[docs/06-validation-and-ablations]] |
| A16 | Common random numbers are **semantic, pre-generated tensors** ($U^{strategy}$, $U^{partner}$, $U^{item}$, $U^{routing}$, $U^{exam}$), shared by matched M0–M5 runs, seeded as `SeedSequence([master, replicate, stream_code, …])` with **stable integer stream codes** (never spawn order). | §44 | [[docs/05-rng-and-reproducibility]] |
| A17 | Output interface: raw event tables only, with `answer_id` provenance (no stored path strings) and committed post-event state snapshots (event 0 = initial). $H^{cum}$, cascades, brokers and $\Delta_{GK}$ live under `derived/`, computed from the raw logs. | §37 | [[docs/07-output-schema]] |
| A18 | Python package `src/classroom_swarm/`. The outer folder isn't renamed for now. | — | `AGENTS.md` |
| A19 | **V2 peer exposure (approved by Vavan 2026-09-18, after E1/E2).** New structural parameter `exposure`: `"requests"` = §7/§23 as written (V1, default, reference) or `"copying"` = $X_i(h{+}1)=\lvert\{j\in N_i: a_j(h)=C\}\rvert/\deg(i)$, the share of neighbours who **chose C** in the previous homework, whatever its success or target; 0 if $\deg(i)=0$; own action never counts. Still local, still a one-homework measurement, not a norm state; $\beta_P$ and the stage ladder are unchanged. It matches §2's "local exposure to peer copying" more closely than §7's definition. | §7, §23 (only when `exposure="copying"`) | [[docs/02-state-and-parameters]], [[docs/03-event-schedule]] |
| A20 | **Frozen weighted contact graph (approved by Vavan 2026-09-20).** Every social edge may carry a positive finite symmetric weight $w_{ij}=w_{ji}$ representing exogenous contact opportunity. The weights are fixed for the whole run, default to 1 (exact V1/V2 behaviour), affect only discussion-partner and copying-request target selection, and never enter strategy utility or peer exposure. They are not updated from copying, success, knowledge, reputation or the derived cheating-flow graph. The existing semantic partner/routing uniform is mapped to the cumulative normalized weights of sorted candidates, so no RNG stream changes. A weight-shuffle null preserves topology and the global weight multiset but not node strengths; weighted-broker claims additionally require a strength-aware null. | §5, §11, §28 steps 3–4, §33 | [[docs/03-event-schedule]], [[docs/04-network-generation]], [[docs/05-rng-and-reproducibility]], [[docs/06-validation-and-ablations]], [[docs/07-output-schema]] |
| A21 | **V3 generative behaviour model (approved by Vavan 2026-09-20).** V3 is implemented beside V1/V2 and never changes their equations or results. It removes the peer-prevalence term ($\beta_P=0$, $X$ causally inert); uses a declared homework-1 seed followed by action-neutral exploration; gives each directed social tie a private reliability belief $A_{ij}$ learned only from $i$'s own requests; selects copy targets from frozen contact weight $w_{ij}$ times learned reliability; makes sharing probabilistic, reciprocal and capacity-limited; samples unassigned student heterogeneity independently of graph position; and optionally updates all action values symmetrically from neighbours' observed action/reward. No role labels, copying propensities or dynamic cheating-edge weights exist. Defaults are provisional mechanisms, not fitted educational values; no scientific V3 claim precedes a separate preregistration. | V1/V2 do not change; V3 is a new model | [[docs/10-v3-generative-model]], [[docs/05-rng-and-reproducibility]], [[docs/06-validation-and-ablations]], [[docs/07-output-schema]] |

---

# Classroom Swarm V1.0

## 1. Purpose

The purpose of V1 is to study whether repeated local interactions among students can spontaneously produce:

$$
\text{copying cascades},
$$

$$
\text{multi-hop answer paths},
$$

$$
\text{broker/source roles},
$$

$$
\text{persistent behavioral regimes},
$$

and

$$
\text{decoupling between homework grades and actual knowledge}.
$$

The model deliberately does **not** encode these phenomena directly.

This follows the logic of the ODD framework for agent-based models: adaptive agent behavior should be distinguished from patterns that are imposed by rules versus patterns expected to emerge from interaction.

The central causal architecture is

$$
\boxed{
\text{knowledge}
\rightarrow
\text{local decisions}
\rightarrow
\text{social interaction}
\rightarrow
\text{observable reward}
\rightarrow
\text{strategy adaptation}
}
$$

while the network creates constraints on which interactions are possible.

---

# 2. Emergence contract

V1 explicitly imposes only microscopic mechanisms.

It imposes:

$$
\text{students can learn},
$$

$$
\text{students choose strategies stochastically},
$$

$$
\text{students learn strategy values from their own outcomes},
$$

$$
\text{answers can be passed only through adjacent social contacts},
$$

and optionally

$$
\text{local exposure to peer copying can influence later decisions}.
$$

V1 does **not** impose:

$$
\text{cheating hubs},
$$

$$
\text{preferred cheating routes},
$$

$$
\text{cheating communities},
$$

$$
\text{cascade thresholds},
$$

$$
\text{global peer pressure},
$$

or

$$
\text{a requirement that copying increase over time}.
$$

The cheating network is therefore an **output**, not a state variable.

---

# 3. Entities

There are three entity classes.

| Entity                | Meaning                                                   |
| --------------------- | --------------------------------------------------------- |
| Student \(i\)         | Adaptive autonomous agent                                 |
| Social graph \(A\)    | Static communication/access structure                     |
| Answer packet \(\Pi\) | Temporary information object existing during one homework |

The model runs in discrete homework/exam events.

---

# 4. Persistent student state

Student \(i\) has

$$
\boxed{
S_i(t)=
\left[
K_i,\,
C_i,\,
E_i,\,
\alpha_i,\,
Q_i^S,\,
Q_i^D,\,
Q_i^C
\right].
}
$$

There are only seven persistent numerical states.

## 4.1 Knowledge

$$
K_i\in[0,1].
$$

Interpretation:

$$
\boxed{
K_i=P(\text{independently answering a standardized course item correctly}).
}
$$

This avoids introducing a separate arbitrary mapping between latent knowledge and performance.

---

## 4.2 Confidence

$$
C_i\in[0,1].
$$

Interpretation:

$$
C_i=
\text{student's subjective expectation of their own academic performance}.
$$

Initially,

$$
C_i(0)=K_i(0).
$$

Therefore everyone begins calibrated.

An important emergent observable is

$$
\boxed{
M_i=C_i-K_i.
}
$$

Positive \(M_i\) means overconfidence and negative \(M_i\) underconfidence.

Research supports links between academic performance and subsequent self-efficacy, although the causal relationship varies by population. A longitudinal meta-analysis found performance→self-efficacy effects larger than the reverse direction, with especially weak evidence for self-efficacy→performance among children.

For that reason, V1 lets grades update confidence but gives confidence only a modest and switchable effect on strategy choice.

---

## 4.3 Effort

Effort is a multiplicative learning modifier:

$$
E_i\ge1.
$$

Baseline:

$$
E_i(0)=1.
$$

This normalization deliberately eliminates the previous \(\alpha E_0\) scale redundancy.

---

## 4.4 Learning efficiency

$$
\alpha_i>0.
$$

This controls how rapidly genuine cognitive work converts remaining learning potential into knowledge.

V1-Core begins with

$$
\alpha_i=\alpha
$$

for every student.

Heterogeneous \(\alpha_i\) is a later robustness experiment rather than a baseline assumption.

---

## 4.5 Strategy values

Students maintain learned values

$$
\mathbf Q_i=
\left[
Q_i^S,Q_i^D,Q_i^C
\right]
$$

for:

$$
S=\text{independent solution},
$$

$$
D=\text{discussion/help},
$$

$$
C=\text{seek an answer through the network}.
$$

These are **learned expected rewards**, not probabilities.

Initially:

$$
Q_i^S=Q_i^D=Q_i^C=0.
$$

---

# 5. Social graph

The social network is

$$
\boxed{
G=(V,A)
}
$$

where

$$
A_{ij}\in\{0,1\}.
$$

An edge means that \(i\) and \(j\) have sufficient social access that asking/discussing/sharing is possible.

In V1:

$$
A_{ij}=A_{ji}
$$

and

$$
A(t)=A(0).
$$

The friendship experiment by Potipiti and Kingsuwankul found peer effects particularly for copying, which requires cooperation, giving some empirical justification for using social relationships as constraints on copying opportunities.

But V1 does **not** assume that having a friendship edge directly changes behavior.

It creates opportunity only.

---

# 6. No persistent cheating network

There is no

$$
F_{ij}
$$

or dynamic "cheating relationship strength."

Instead, for homework \(h\), record

$$
H_{ij}^{(h)}
=
\text{number of actual answer transmissions }i\rightarrow j.
$$

This is generated by the simulation.

The cumulative flow network is reconstructed afterward:

$$
\boxed{
H_{ij}^{\mathrm{cum}}(T)
=
\sum_{h=1}^{T}H_{ij}^{(h)}.
}
$$

Consequently,

$$
\text{brokerage},
\quad
\text{source dominance},
\quad
\text{persistent routes}
$$

have to appear in \(H\); they cannot influence the agents directly.

---

# 7. Previous-peer exposure

The only social-behavior signal is derived from the previous homework.

Define

$$
X_i(h)=
\frac{
\left|
\left\{
j\in N_i:
j\text{ asked }i\text{ for an answer during }h-1
\right\}
\right|
}{
|N_i|
}.
$$

If \(\deg(i)=0\),

$$
X_i=0.
$$

Crucially, \(X_i\) is not a learned norm state.

It is simply a measurement of the immediately preceding interaction.

The peer-cheating literature provides justification for testing this mechanism: a 2022 meta-analysis of 38 studies and 24,181 participants found an association of approximately

$$
r=0.37
$$

between perceived peer cheating and one's own cheating. The evidence does not establish our exact causal function, so the peer coefficient must remain optional and its zero condition is mandatory.

---

# 8. Initial strategy preference

Let

$$
p_C^0
$$

denote the initial probability of choosing copying before any experience.

The remaining probability is divided equally:

$$
p_S^0=p_D^0=
\frac{1-p_C^0}{2}.
$$

Instead of forcing \(Q_C\) negative, introduce a fixed baseline copying bias

$$
\boxed{
b_C
=
\ln
\left(
\frac{2p_C^0}{1-p_C^0}
\right).
}
$$

Set

$$
b_S=b_D=0.
$$

Then with

$$
Q=0,\qquad
C=0.5,\qquad
X=0,
$$

softmax produces exactly \(p_C^0\).

This keeps the learned \(Q\)-values on the same reward scale rather than using them simultaneously as initialization logits and reinforcement estimates.

---

# 9. Strategy utilities

For homework \(h\):

$$
U_i^S
=
Q_i^S
+
\beta_C(C_i-0.5),
$$

$$
U_i^D
=
Q_i^D,
$$

$$
\boxed{
U_i^C
=
b_C+
Q_i^C+
\beta_P X_i.
}
$$

Strategy probabilities are

$$
\boxed{
P_i(a)
=
\frac{\exp(U_i^a)}
{
\exp(U_i^S)+
\exp(U_i^D)+
\exp(U_i^C)
}.
}
$$

There is no softmax temperature.

The reward scale already establishes the utility scale; adding \(T\) would create an unnecessary scaling degree of freedom.

A strategy is sampled once per homework.

---

# 10. Independent strategy \(S\)

Use the pre-homework knowledge \(K_i\).

Learning is

$$
\boxed{
\Delta K_i^S
=
\alpha_iE_i(1-K_i).
}
$$

Then

$$
K_i^{S+}
=
\operatorname{clip}
\left(
K_i+\Delta K_i^S,
0,1
\right).
$$

For a homework containing \(M_H\) items:

$$
y_{iq}
\sim
\operatorname{Bernoulli}(K_i^{S+}).
$$

The answer packet is

$$
\Pi_i=
\left[
\mathbf y_i,\,
root=i,\,
path=[i]
\right].
$$

The grade is

$$
G_i^H
=
\frac{1}{M_H}
\sum_qy_{iq}.
$$

---

# 11. Discussion strategy \(D\)

Student \(i\) chooses one direct neighbor

$$
j\sim\operatorname{Uniform}(N_i).
$$

The partner is selected using topology only.

The agent does not inspect \(K_j\).

Learning is

$$
\boxed{
\Delta K_i^D
=
\alpha_iE_i(1-K_i)
\left[
1+(K_j-K_i)_+
\right].
}
$$

where

$$
(x)_+=\max(x,0).
$$

Thus discussion with an equally or less knowledgeable student has approximately ordinary learning effectiveness, while discussion with a more knowledgeable student may accelerate learning.

This is inspired by the "more knowledgeable other" mechanism used in Flat Peer Learning, but the exact functional form remains a V1 structural hypothesis rather than an empirical law. Flat Peer Learning itself demonstrates how stochastic independent and peer-learning processes on static networks can generate nontrivial group-level learning dynamics.

Set

$$
K_i^{D+}
=
\operatorname{clip}
(
K_i+\Delta K_i^D,
0,1
).
$$

The probability of producing a correct homework item is

$$
p_i^D=
\max(K_i^{D+},K_j).
$$

Then

$$
y_{iq}
\sim
\operatorname{Bernoulli}(p_i^D).
$$

The generated answer belongs to \(i\):

$$
\Pi_i=
[
\mathbf y_i,
root=i,
path=[i]
].
$$

This discussion submodel is intentionally minimal because peer tutoring is not the primary V1 research target.

---

# 12. Copying strategy \(C\)

Choosing \(C\) means:

$$
\boxed{
\text{attempt to obtain an answer through local contacts}.
}
$$

It does not mean:

$$
\text{choose the student who has the best answer}.
$$

Initially:

$$
\Pi_i=\varnothing.
$$

Each copy-seeking student also has a temporary set

$$
\mathcal Q_i=\varnothing
$$

containing neighbors already queried during this homework.

---

# 13. Routing micro-rounds

Each homework contains

$$
R
$$

social-interaction micro-rounds.

At round \(r\), every unresolved copier \(i\):

selects one neighbor

$$
j\in N_i\setminus\mathcal Q_i
$$

uniformly and adds

$$
j
$$

to \(\mathcal Q_i\).

The request

$$
i\rightarrow j
$$

is recorded.

If \(j\) possessed an answer packet **at the beginning of round \(r\)**, then \(j\) can transmit it to \(i\).

The new packet is

$$
\Pi_i=
[
\mathbf y_j,\,
root(\Pi_j),\,
path(\Pi_j)\Vert i
].
$$

All transfers are committed simultaneously at the end of the round.

Therefore:

$$
A\rightarrow B\rightarrow C
$$

requires at least two micro-rounds.

No answer can travel through arbitrarily many students inside one computer iteration.

---

# 14. Path emergence

Suppose student \(A\) originally solves the homework.

Round 1:

$$
A\rightarrow B.
$$

Round 2:

$$
B\rightarrow C.
$$

Round 3:

$$
C\rightarrow D.
$$

The final packet contains

$$
path=[A,B,C,D].
$$

None of these paths are calculated by a routing algorithm.

No student sees the global graph.

No shortest-path search occurs.

Therefore multi-hop routing arises entirely from repeated local possession and requests.

---

# 15. Answer sharing

Baseline V1 assumes:

$$
\boxed{
\text{an answer holder shares when directly asked by an adjacent student}.
}
$$

There is no sharing-probability parameter.

This deliberately interprets the social edge as a relationship through which answer sharing is possible.

Adding a separate sharing probability would be strongly confounded with \(R\), because both reduce or increase the probability that a packet reaches its destination.

Sharing probability becomes a robustness extension, not a V1 parameter.

---

# 16. Copying success

If student \(i\) receives a packet,

$$
G_i^H
=
\frac1{M_H}
\sum_q y_{iq}^{packet}.
$$

The copied answer is exact in V1.

Therefore errors propagate as well as correct answers.

For example:

$$
A:
\mathbf y=(1,1,0,1,0,\ldots)
$$

can lead to

$$
A\rightarrow B\rightarrow C\rightarrow D
$$

all submitting the same error pattern.

This allows correlated error cascades to emerge without explicitly programming them.

---

# 17. Learning while copying

Successful copying may still teach something.

Define

$$
\boxed{
\Delta K_i^C
=
\chi_C
\alpha_iE_i(1-K_i).
}
$$

Then

$$
K_i^{C+}
=
K_i+
\Delta K_i^C.
$$

Here

$$
\chi_C=0
$$

means copying provides no learning and

$$
\chi_C=1
$$

means copying is educationally equivalent to independent work.

The MIT homework-copying study found copying increased through the semester and toward assignment deadlines, and frequent copying was associated with weaker later performance on similar exam problems. This supports testing \(\chi_C<1\), but it does not justify setting \(\chi_C=0\) or give us a precise coefficient.

Therefore \(\chi_C\) must be swept broadly.

---

# 18. Failed copying

If after \(R\) rounds

$$
\Pi_i=\varnothing,
$$

student \(i\) attempts the assignment with their existing knowledge:

$$
y_{iq}
\sim
\operatorname{Bernoulli}(K_i).
$$

Thus

$$
G_i^H
=
\frac1{M_H}\sum_q y_{iq}.
$$

But

$$
\Delta K_i=0.
$$

Interpretation:

the student spent the available learning period seeking an answer and only attempted the work at the deadline.

This is a structural assumption and must be tested later against a fallback-independent variant.

---

# 19. Homework effort cost

Normalize cognitive/time cost as

$$
c_S=1,
$$

$$
c_D=1,
$$

and

$$
c_C=
\begin{cases}
0,&\text{successful copying}\\
1,&\text{failed copying}.
\end{cases}
$$

Thus copying is only "easy" if the network actually delivers an answer.

There is no separate cost parameter per strategy.

---

# 20. Homework subjective reward

The student observes grade and effort cost:

$$
\boxed{
R_i^H
=
G_i^H-\kappa c_i.
}
$$

The student does **not** directly observe

$$
\Delta K_i.
$$

That distinction is fundamental.

The model therefore contains two objective functions:

student behavior reacts to

$$
R_i^H,
$$

while the investigator cares about

$$
K_i.
$$

---

# 21. Strategy reinforcement

Only the strategy selected during that homework is updated:

$$
\boxed{
Q_i^{a_i}(h+1)
=
Q_i^{a_i}(h)
+
\eta_Q
\left[
R_i^H-Q_i^{a_i}(h)
\right].
}
$$

Unchosen strategies retain their previous values.

No exam directly modifies \(Q\).

This is deliberately a minimal reinforcement-learning approximation rather than a claim that actual students literally perform Q-learning.

---

# 22. Confidence update

Following any graded event:

$$
\boxed{
C_i'
=
C_i+
\eta_C(G_i-C_i).
}
$$

Therefore copied homework can produce

$$
G_i^H>K_i
$$

and hence

$$
C_i\uparrow
$$

without equivalent knowledge growth.

This allows confidence miscalibration to arise endogenously.

---

# 23. Peer exposure update

After homework \(h\):

$$
\boxed{
X_i(h+1)
=
\frac{
\#\text{ distinct neighbors that requested an answer from }i
}{
\deg(i)
}.
}
$$

Only **incoming requests from other students** count.

A student's own copying request does not contribute to \(X_i\).

This prevents personal copying experience from being counted twice:

$$
Q_i^C
=
\text{personal reinforcement},
$$

whereas

$$
X_i
=
\text{peer exposure}.
$$

---

# 24. Examination

Every \(F_E\) homeworks, students take an exam.

No social interaction occurs.

For \(M_E\) exam items,

$$
Y_i^E
\sim
\operatorname{Binomial}(M_E,K_i).
$$

Hence

$$
\boxed{
G_i^E
=
\frac{Y_i^E}{M_E}.
}
$$

The exam is therefore a noisy observation of actual mastery rather than simply setting

$$
G=K.
$$

---

# 25. Exam effect on confidence

Apply the same performance-feedback equation:

$$
C_i'
=
C_i+\eta_C(G_i^E-C_i).
$$

This can correct homework-induced confidence miscalibration.

---

# 26. Exam effect on effort

Following the user's original hypothesis, a disappointing exam increases subsequent study effort.

Define target performance

$$
\tau_E.
$$

Then:

$$
\boxed{
E_i'
=
1+
\eta_E
(\tau_E-G_i^E)_+.
}
$$

Thus a sufficiently good exam resets effort to baseline:

$$
E_i=1.
$$

A poor exam produces:

$$
E_i>1.
$$

Unlike the previous model, effort does not accumulate indefinitely and no decay parameter is required.

This is an explicit V1 hypothesis, not a claim that every real student responds to failure by working harder.

---

# 27. Exact simulation schedule

For homework \(h\):

$$
\text{snapshot}
\rightarrow
\text{strategy selection}
\rightarrow
\text{honest learning}
\rightarrow
\text{answer creation}
\rightarrow
\text{network routing}
\rightarrow
\text{grades}
\rightarrow
\text{copy learning}
\rightarrow
\text{confidence}
\rightarrow
Q\text{-update}
\rightarrow
X\text{-update}
\rightarrow
\text{commit}.
$$

All students make their strategy decision from the same pre-homework state.

Network packet updates are synchronous inside each routing round.

---

# 28. Reference pseudocode

```text
INITIALIZE
    generate or load static graph A

    for each student i:
        K[i] = K0
        C[i] = K0
        E[i] = 1
        alpha[i] = alpha

        Q[i,S] = 0
        Q[i,D] = 0
        Q[i,C] = 0

        X[i] = 0

    bC = log(2 * pC0 / (1 - pC0))

FOR homework h = 1 ... H:

    --------------------------------------------------
    1. SNAPSHOT
    --------------------------------------------------

    K0_step = copy(K)
    C0_step = copy(C)
    E0_step = copy(E)
    Q0_step = copy(Q)
    X0_step = copy(X)

    packet[i] = NONE
    queried[i] = empty set
    incoming_requesters[i] = empty set
    action[i] = NONE

    --------------------------------------------------
    2. CHOOSE STRATEGY
    --------------------------------------------------

    for each student i:

        U_S = Q0_step[i,S]
              + beta_C * (C0_step[i] - 0.5)

        U_D = Q0_step[i,D]

        U_C = bC
              + Q0_step[i,C]
              + beta_P * X0_step[i]

        P = softmax(U_S, U_D, U_C)

        action[i] = categorical_sample(P)

    --------------------------------------------------
    3. INDEPENDENT / DISCUSSION LEARNING
    --------------------------------------------------

    K_buffer = copy(K0_step)

    for each student i:

        if action[i] == S:

            deltaK =
                alpha[i]
                * E0_step[i]
                * (1 - K0_step[i])

            K_buffer[i] =
                clip(K0_step[i] + deltaK, 0, 1)

            answers =
                BernoulliVector(M_H, K_buffer[i])

            packet[i] =
                Packet(
                    answers = answers,
                    root = i,
                    path = [i]
                )

        else if action[i] == D:

            if degree(i) > 0:
                j = random_neighbor(i)

                multiplier =
                    1 + max(K0_step[j] - K0_step[i], 0)

                deltaK =
                    alpha[i]
                    * E0_step[i]
                    * (1 - K0_step[i])
                    * multiplier

                K_buffer[i] =
                    clip(K0_step[i] + deltaK, 0, 1)

                p_answer =
                    max(K_buffer[i], K0_step[j])

            else:
                deltaK =
                    alpha[i]
                    * E0_step[i]
                    * (1 - K0_step[i])

                K_buffer[i] =
                    clip(K0_step[i] + deltaK, 0, 1)

                p_answer = K_buffer[i]

            answers =
                BernoulliVector(M_H, p_answer)

            packet[i] =
                Packet(
                    answers = answers,
                    root = i,
                    path = [i]
                )

        else if action[i] == C:

            packet[i] = NONE


    --------------------------------------------------
    4. NETWORK ROUTING
    --------------------------------------------------

    initialize homework transmission log H_flow

    for round r = 1 ... R:

        holders_at_start =
            set of students with packet != NONE

        scheduled_transfers = empty

        for each student i where:
            action[i] == C
            AND packet[i] == NONE:

            candidates =
                neighbors(i) minus queried[i]

            if candidates is empty:
                continue

            j = random_choice(candidates)

            queried[i].add(j)
            incoming_requesters[j].add(i)

            if j in holders_at_start:

                scheduled_transfers.add(
                    source = j,
                    receiver = i,
                    packet = packet[j]
                )

        # simultaneous commit

        for each transfer (j -> i):

            packet[i] =
                copy(packet[j])

            packet[i].path =
                packet[j].path + [i]

            H_flow[j,i] += 1


    --------------------------------------------------
    5. CALCULATE HOMEWORK OUTCOME
    --------------------------------------------------

    for each student i:

        if action[i] in {S,D}:

            G_H[i] =
                mean(packet[i].answers)

        else if action[i] == C
                AND packet[i] != NONE:

            G_H[i] =
                mean(packet[i].answers)

            deltaK =
                chi_C
                * alpha[i]
                * E0_step[i]
                * (1 - K0_step[i])

            K_buffer[i] =
                clip(K0_step[i] + deltaK, 0, 1)

        else:
            # failed copy attempt

            fallback =
                BernoulliVector(M_H, K0_step[i])

            G_H[i] = mean(fallback)

            K_buffer[i] = K0_step[i]


    --------------------------------------------------
    6. CONFIDENCE UPDATE
    --------------------------------------------------

    for each student i:

        C_new[i] =
            clip(
                C0_step[i]
                + eta_C * (G_H[i] - C0_step[i]),
                0, 1
            )


    --------------------------------------------------
    7. SUBJECTIVE REWARD
    --------------------------------------------------

    for each student i:

        if action[i] in {S,D}:
            cost = 1

        else if action[i] == C
                AND packet[i] != NONE:
            cost = 0

        else:
            cost = 1

        reward =
            G_H[i] - kappa * cost


    --------------------------------------------------
    8. STRATEGY LEARNING
    --------------------------------------------------

        a = action[i]

        Q_new[i,a] =
            Q0_step[i,a]
            + eta_Q * (
                reward - Q0_step[i,a]
            )

        other Q values remain unchanged


    --------------------------------------------------
    9. PEER EXPOSURE FOR NEXT HOMEWORK
    --------------------------------------------------

    for each student i:

        if degree(i) > 0:

            X_new[i] =
                number_of_distinct(
                    incoming_requesters[i]
                ) / degree(i)

        else:
            X_new[i] = 0


    --------------------------------------------------
    10. COMMIT
    --------------------------------------------------

    K = K_buffer
    C = C_new
    Q = Q_new
    X = X_new

    save:
        actions
        grades
        K
        C
        E
        Q
        X
        all packet paths
        roots
        H_flow


    --------------------------------------------------
    11. EXAM IF SCHEDULED
    --------------------------------------------------

    if h mod F_E == 0:

        for each student i:

            correct =
                Binomial(M_E, K[i])

            G_E[i] =
                correct / M_E

            C[i] =
                clip(
                    C[i]
                    + eta_C * (G_E[i] - C[i]),
                    0, 1
                )

            E[i] =
                1
                + eta_E
                * max(tau_E - G_E[i], 0)

        save exam state
```

---

# 29. Parameter registry: environmental parameters

The ranges below are **initial experimental ranges**, not claims that empirical studies established these exact values.

| Parameter | Meaning                 | Reference | Initial range | Calibration basis                      | Mandatory ablation / robustness                         |
| --------- | ----------------------- | --------: | ------------: | -------------------------------------- | ------------------------------------------------------- |
| \(N\)     | Students                |        30 |         20–40 | Classroom-scale scenario, not fitted   | \(20,30,40\)                                            |
| \(H\)     | Homework count          |        20 |         12–30 | Simulation horizon                     | Short and long horizons                                 |
| \(F_E\)   | Homework between exams  |         5 |          2–10 | Curriculum scenario                    | \(F_E=2\), \(5\), \(10\), and no exams                  |
| \(R\)     | Routing rounds/homework |         3 |           1–5 | Structural information-flow assumption | **\(R=1\)** is mandatory; removes multi-hop propagation |
| \(M_H\)   | Homework items          |        10 |          5–20 | Measurement granularity                | \(M_H\rightarrow1000\) to approximate noiseless grade   |
| \(M_E\)   | Exam items              |        30 |         10–50 | Measurement granularity                | \(M_E\rightarrow1000\)                                  |

The MIT copying study provides useful external temporal patterns—copying rose during semesters and near deadlines—but it does not identify our routing-round parameter \(R\).

---

# 30. Social-network registry

The graph should be treated primarily as an **input condition**, not something fitted together with behavioral coefficients.

Reference synthetic tests should hold

$$
N
$$

and approximately

$$
\bar d
$$

constant while changing topology.

| Input                                    |         Reference | Test range / variants        | Purpose                                 | Required comparison          |
| ---------------------------------------- | ----------------: | ---------------------------- | --------------------------------------- | ---------------------------- |
| Mean degree \(\bar d\)                   |                 6 | 4–10                         | Overall social accessibility            | Matched topology comparisons |
| Network family                           | community network | ER / small-world / community | Structural hypothesis                   | All three                    |
| WS rewiring \(\omega\)                   |               0.1 | 0.05–0.3                     | Only when generating small-world graphs | Degree-matched ER            |
| SBM community ratio \(r=p_{in}/p_{out}\) |                 5 | 2–10                         | Only for synthetic community graphs     | Degree-preserving shuffle    |

These are **experimental network generators**, not psychological parameters.

For ER graphs:

$$
p_{edge}
=
\frac{\bar d}{N-1}.
$$

For SBM graphs, \(p_{in}\) and \(p_{out}\) should be solved from the desired

$$
\bar d
$$

and chosen ratio \(r\), rather than independently fitted.

This avoids making density and modularity unconstrained simultaneously.

Flat Peer Learning is useful precedent for treating network topology itself as an experimental condition and showing that local peer-learning dynamics can change substantially across graph structures.

---

# 31. Learning and initialization registry

| Parameter  | Meaning                            | Reference |                  Range | Calibration source                              | Required ablation                        |
| ---------- | ---------------------------------- | --------: | ---------------------: | ----------------------------------------------- | ---------------------------------------- |
| \(K_0\)    | Initial knowledge                  |      0.50 |              0.30–0.70 | User-defined conceptual starting level          | Repeat at 0.4 and 0.6                    |
| \(C_0\)    | Initial confidence                 |   \(K_0\) |                derived | Calibration assumption                          | Start with \(C_0-K_0=\pm0.2\) robustness |
| \(E_0\)    | Baseline effort multiplier         |         1 |                  fixed | Normalization                                   | none; fixes scale                        |
| \(\alpha\) | Learning efficiency                |    0.0584 |    approx. 0.045–0.077 | Derived from desired honest-learning trajectory | Recalibrate when horizon changes         |
| \(p_C^0\)  | Initial copying choice probability |      0.10 |              0.01–0.20 | Scenario/seed prevalence; not empirical fit     | Rare seed \(0.01\), high seed \(0.20\)   |
| \(Q_a(0)\) | Learned action values              |         0 |                  fixed | Neutral prior                                   | none                                     |
| \(b_C\)    | Initial copy bias                  |   derived | derived from \(p_C^0\) | Algebraic                                       | varies only through \(p_C^0\)            |

For an independent student with \(E=1\):

$$
K_{t+1}
=
K_t+\alpha(1-K_t).
$$

Hence

$$
K_T
=
1-(1-K_0)(1-\alpha)^T.
$$

Solving:

$$
\boxed{
\alpha
=
1-
\left(
\frac{1-K_T}{1-K_0}
\right)^{1/T}.
}
$$

For

$$
K_0=0.5,
\qquad
K_{20}=0.85,
$$

we obtain

$$
\boxed{
\alpha\approx0.0584.
}
$$

Targeting

$$
K_{20}=0.80-0.90
$$

gives approximately

$$
\alpha=0.045-0.077.
$$

These values therefore come directly from **your desired learning trajectory**, not external educational data.

That fact should always be reported.

---

# 32. Behavioral parameter registry

| Parameter   | Mechanism                             |                              Reference | Plausible sweep | Evidence/calibration status                                                       | Mandatory ablation |
| ----------- | ------------------------------------- | -------------------------------------: | --------------: | --------------------------------------------------------------------------------- | ------------------ |
| \(\eta_Q\)  | Strategy adaptation rate              |                                   0.20 |       0.05–0.40 | Modeling timescale; not empirically estimated                                     | **0**              |
| \(\kappa\)  | Aversion to costly work               |                                   0.15 |          0–0.40 | Hypothesis parameter                                                              | **0**              |
| \(\beta_C\) | Confidence → independent-work utility |                                    0.5 |           0–1.5 | Sign plausible; magnitude uncalibrated                                            | **0**              |
| \(\beta_P\) | Peer exposure → copying utility       | reference core = 0; social model = 0.5 |           0–1.5 | Peer effect empirically supported; mapping unknown                                | **0 mandatory**    |
| \(\chi_C\)  | Relative learning from copying        |                                   0.10 |             0–1 | Unknown; copying literature suggests it can be lower than genuine problem solving | **0, 0.5, 1**      |
| \(\eta_C\)  | Performance → confidence update       |                                   0.20 |       0.10–0.40 | Direction supported; timescale not calibrated                                     | **0**              |
| \(\eta_E\)  | Poor exam → extra effort              |                                   0.30 |          0–0.60 | User hypothesis; not universal empirical law                                      | **0**              |
| \(\tau_E\)  | Exam performance target               |                                   0.70 |       0.60–0.80 | Institutional/scenario threshold                                                  | 0.6 and 0.8        |

The confidence mechanism is deliberately conservative because reviews show performance and academic self-efficacy are related, but causal pathways are heterogeneous and performance→self-efficacy often appears stronger.

The positive sign of \(\beta_P\) is motivated by peer-cheating research, including the \(r\approx0.37\) meta-analytic association and experimental evidence that friendship can facilitate cooperative copying. It should **not** be calibrated numerically from that correlation because an observed correlation does not translate directly into a softmax utility coefficient.

---

# 33. Fixed structural constants

These are deliberately **not** tunable in V1.

| Constant                        |  Value | Reason                                                   |
| ------------------------------- | -----: | -------------------------------------------------------- |
| Softmax temperature             |  \(1\) | Avoid utility-scale non-identifiability                  |
| \(c_S\)                         |      1 | Normalized genuine-work cost                             |
| \(c_D\)                         |      1 | Discussion treated as genuine cognitive work             |
| \(c_C\), success                |      0 | Successful shortcut                                      |
| \(c_C\), failure                |      1 | Failed search consumes available work period             |
| Share probability along an edge |      1 | Avoid confounding sharing with routing opportunities     |
| Transmission error              |      0 | Exact copied answer; error comes from source             |
| Friendship dynamics             |    off | Prevent network coevolution from obscuring V1 mechanism  |
| Forgetting                      |    off | Not required over initial short horizon                  |
| Exam → direct \(Q\) update      |    off | Avoid hard-coding exam suppression of copying            |
| Dynamic cheating-edge strength  | absent | Persistent pathways must emerge                          |
| Reputation                      | absent | Sources/brokers must emerge from actual information flow |

---

# 34. Why these removed parameters really were redundant or dangerous

### Dynamic cheating-edge strength \(F_{ij}\)

Removed because

$$
\text{success}
\rightarrow
F_{ij}\uparrow
\rightarrow
\text{future path probability}\uparrow
$$

would nearly guarantee path persistence.

We want to see whether persistence appears **without path memory**.

---

### Persistent social norm \(N_i\)

Removed because immediate peer exposure

$$
X_i
$$

already represents social information.

A separate slowly changing norm state creates another timescale and makes

$$
\beta_P,\eta_N
$$

partly non-identifiable.

---

### Detection belief

Removed because detection policy is a separate research question.

It can be added when studying institutional interventions.

---

### Reputation

Removed because if high-performing students become sources, we want that to arise because they actually possess better answer packets—not because agents are told whom to target.

---

### Eligibility traces

Removed because

$$
\text{poor exam}
\rightarrow
Q_C\downarrow
$$

would encode a direct mechanism making exams suppress copying.

Without it, whether exams indirectly alter behavior through confidence and effort becomes a genuine system result.

---

### Softmax temperature

Removed because changing \(T\) and rescaling every utility coefficient can produce equivalent probabilities.

Reward grade already establishes a meaningful utility scale.

---

### Separate sharing probability

Removed because a lower sharing probability and additional routing rounds can generate similar reachability.

That is exactly the sort of parameter confounding that makes ABMs difficult to interpret.

Sensitivity analysis is explicitly useful for identifying parameters that can be fixed or removed when they add little distinguishable behavior.

---

# 35. Parameters that are still partially confounded

## \(\eta_Q\) versus \(\kappa\)

They are not redundant.

$$
\eta_Q
$$

controls how rapidly experience is learned.

$$
\kappa
$$

changes which strategy ultimately provides the highest subjective reward.

But final copying prevalence alone cannot distinguish them well.

Therefore analyze the full

$$
P(C,t)
$$

trajectory.

---

## \(\beta_P\) versus network density

Both can increase copying.

But their mechanisms differ.

Higher degree changes:

$$
\text{answer reachability},
$$

$$
\text{path length},
$$

and

$$
\text{cascade size}.
$$

Higher \(\beta_P\) changes:

$$
P(C\mid X).
$$

These can be distinguished only if we save both behavioral and network outputs.

---

## \(\chi_C\) versus \(\alpha\)

For copiers,

$$
\Delta K_C=
\chi_C\alpha E(1-K).
$$

So these are confounded if only copiers are observed.

But independent students identify the baseline effect

$$
\alpha E(1-K),
$$

allowing \(\chi_C\) to be interpreted relatively.

Therefore \(\alpha\) must be calibrated first using the all-independent control.

---

## \(\eta_C\) versus \(\beta_C\)

$$
\eta_C
$$

sets confidence-update speed.

$$
\beta_C
$$

sets behavioral sensitivity to confidence.

They can compensate to some extent.

I therefore recommend fixing

$$
\eta_C=0.20
$$

for the first experiments and varying

$$
\beta_C.
$$

Only later should \(\eta_C\) be swept broadly.

---

## \(\eta_E\) versus exam frequency

Frequent weak remediation and rare strong remediation can create similar average effort.

Therefore report both:

$$
E(t)
$$

and exam timing.

Do not infer \(\eta_E\) from final knowledge alone.

---

# 36. Required structural ablation hierarchy

This is more important than numerical parameter sensitivity.

| Model  | Active mechanism                                       | Question                                                            |
| ------ | ------------------------------------------------------ | ------------------------------------------------------------------- |
| **M0** | Static graph + fixed stochastic strategy probabilities | What network-flow structure appears without behavioral learning?    |
| **M1** | M0 + \(Q\)-reinforcement                               | Can individual success alone make copying expand?                   |
| **M2** | M1 + multi-hop \(R>1\)                                 | Does path propagation qualitatively change behavior?                |
| **M3** | M2 + \(\beta_P>0\)                                     | What additional effect comes from peer exposure?                    |
| **M4** | M3 + confidence                                        | Does performance-belief feedback alter strategy ecology?            |
| **M5** | M4 + exams/effort feedback                             | How does assessment feedback alter long-run knowledge and behavior? |

The strongest emergence test is:

$$
\boxed{
M1/M2\text{ with }\beta_P=0.
}
$$

If copying expands there, then no direct peer-imitation mechanism was required.

The mechanism is simply:

$$
\text{local access}
\rightarrow
\text{successful shortcut}
\rightarrow
\text{personal reinforcement}
\rightarrow
\text{more requests}
\rightarrow
\text{more answer availability}.
$$

That is a much more convincing emergent result.

---

# 37. Required outputs

Individual level:

$$
K_i(t),
$$

$$
C_i(t),
$$

$$
C_i(t)-K_i(t),
$$

$$
Q_i^S,Q_i^D,Q_i^C,
$$

$$
P_i(S),P_i(D),P_i(C),
$$

$$
G_i^H,G_i^E.
$$

Network-flow level:

$$
\text{source/root},
$$

$$
\text{complete provenance path},
$$

$$
\text{path depth},
$$

$$
\text{cascade size},
$$

$$
H_{ij}^{(h)},
$$

$$
\text{cumulative edge flow},
$$

$$
\text{node flow-through count}.
$$

Classroom level:

$$
\bar K(t),
$$

$$
\operatorname{Var}(K(t)),
$$

$$
P(C,t),
$$

$$
P(C\text{ succeeds},t),
$$

and

$$
\boxed{
\Delta_{GK}
=
\overline{G_H}-\overline{G_E}.
}
$$

\(\Delta_{GK}\) is our main **grade–knowledge decoupling indicator**.

---

# 38. Defining an answer cascade

For a given homework and root source \(s\),

$$
\mathcal C_s
=
\{
i:
root(\Pi_i)=s
\}.
$$

Cascade size:

$$
\boxed{
S_s=|\mathcal C_s|.
}
$$

Maximum cascade depth:

$$
\boxed{
L_s
=
\max_{i\in\mathcal C_s}
|path(\Pi_i)|-1.
}
$$

A large

$$
S_s
$$

is not automatically evidence of behavioral contagion.

It can arise from topology alone.

Therefore cascade statistics must always be compared against M0.

---

# 39. Defining an emergent broker

Do **not** call a high-degree student an emergent broker simply because many paths pass through them.

Define raw brokerage:

$$
B_i
=
\sum_h
\#\{
\text{answer paths in homework }h
\text{ where }i
\text{ is internal}
\}.
$$

Then compare \(B_i\) against a degree-matched null.

For example:

$$
\boxed{
B_i^{excess}
=
B_i-
E[B_i\mid\deg(i)].
}
$$

A student with unusually high

$$
B_i^{excess}
$$

is a stronger candidate for an emergent broker than merely a high-degree node.

This distinction is essential.

Otherwise we risk calling a trivial consequence of topology "emergence."

---

# 40. Defining persistent routes

Cumulative edge flow:

$$
F_{ij}^{obs}
=
\sum_hH_{ij}^{(h)}.
$$

Then compute concentration, for example:

$$
\boxed{
C_F=
\frac{
\sum_{(i,j)\in\text{top }20\%\text{ edges}}
F_{ij}^{obs}
}{
\sum_{ij}F_{ij}^{obs}
}.
}
$$

Compare \(C_F\) against simulations with:

$$
\eta_Q=0
$$

and degree-preserving graph randomization.

If concentrated "information highways" persist only when reinforcement is active, that is much more interesting than concentration caused purely by graph structure.

---

# 41. Calibration order

Calibration must be sequential.

First calibrate the non-social learning model.

Set:

$$
P(S)=1,
$$

$$
\eta_E=0.
$$

Choose \(\alpha\) to reproduce the desired baseline trajectory.

Second verify measurement noise using \(M_H,M_E\).

Third introduce discussion.

Fourth introduce copying but freeze adaptation:

$$
\eta_Q=0,
\quad
\beta_P=0.
$$

Fifth introduce reinforcement.

Sixth add peer exposure.

Finally add confidence and examination feedback.

Do not calibrate all parameters simultaneously.

Pattern-oriented modeling recommends constraining models against several independent patterns rather than fitting a single aggregate output, and parameter-space sampling is preferable to finding one apparently optimal combination.

---

# 42. Sensitivity-analysis sequence

After structural ablation, perform one-factor screening.

Parameters with negligible effect on every important output should be fixed or removed.

Then perform global sensitivity on the surviving parameters using a design such as Latin Hypercube sampling followed by PRCC where monotonicity is reasonable, or Sobol indices for strongly nonlinear interactions.

Sensitivity analysis is especially valuable in ABMs because it reveals which represented mechanisms actually control the output and whether model conclusions survive parameter uncertainty.

The first global sensitivity vector should probably be

$$
\boxed{
[
\eta_Q,
\kappa,
\beta_P,
\beta_C,
\chi_C,
\eta_E
].
}
$$

I would initially keep

$$
\eta_C,\tau_E,\alpha
$$

fixed after calibration.

---

# 43. Monte Carlo replication

A single simulation is meaningless for this model.

For each parameter condition use independent random seeds.

Start with approximately

$$
n=200
$$

runs during development.

For final experiments, increase repetitions until major output estimates stabilize.

For each condition monitor convergence of at least:

$$
E[P(C,T)],
$$

$$
E[\bar K(T)],
$$

median maximum cascade size,

and upper-tail cascade statistics.

The required number of repetitions should be chosen from convergence, not an arbitrary round number.

---

# 44. Logical invariants for code verification

Every simulation step must satisfy:

$$
0\le K_i\le1,
$$

$$
0\le C_i\le1,
$$

$$
E_i\ge1,
$$

$$
0\le G_i\le1.
$$

Every transmitted packet must have:

$$
path[0]=root.
$$

Every adjacent pair in a path must satisfy:

$$
A_{uv}=1.
$$

A packet received during round \(r\) cannot be retransmitted until

$$
r+1.
$$

Every flow edge

$$
H_{ij}^{(h)}>0
$$

must correspond to an actual logged transmission.

Students must never use hidden values such as another student's \(K_j\) to choose whom to copy from.

Only the simulator uses \(K_j\) to calculate the consequences of discussion.

With identical seed, parameters, graph and implementation:

$$
\text{output must reproduce exactly}.
$$

These checks should be automated unit/integration tests before scientific experiments.

---

# 45. Failure criteria for V1

V1 should be rejected or simplified further if:

the main qualitative result appears only within an extremely narrow parameter range;

removing one arbitrary parameter reverses essentially every conclusion;

network topology has no measurable effect despite the research question being path-based;

\(Q\)-reinforcement adds nothing beyond fixed random behavior;

confidence adds no observable behavior beyond what \(Q\) already explains;

the same macro-output can be generated by widely different parameter combinations while no additional observable distinguishes them;

or the "emergent" phenomenon can be derived trivially from a single imposed equation.

In any of those cases, the correct response is model reduction—not adding another variable.

---

# 46. External patterns useful for later validation

Several empirical patterns provide useful targets without being directly programmed.

The MIT homework study observed copying increasing through the semester and toward weekly deadlines.

Peer-cheating research finds a sizeable association between perceived peer cheating and own dishonesty.

Experimental work found friendship effects specifically on cooperative copying.

Another study found closer friendship increased cheating particularly among lower-performing students.

V1 should **not** hard-code these four patterns.

Instead, later we can ask whether one parameter region reproduces several of them simultaneously.

That is substantially stronger validation.

---

# 47. Reference V1 configuration

The first reference run should use:

$$
N=30,
$$

$$
K_0=C_0=0.5,
$$

$$
E_0=1,
$$

$$
H=20,
$$

$$
\alpha=0.0584,
$$

$$
M_H=10,
$$

$$
M_E=30,
$$

$$
F_E=5,
$$

$$
R=3,
$$

$$
p_C^0=0.10,
$$

$$
\eta_Q=0.20,
$$

$$
\kappa=0.15,
$$

$$
\chi_C=0.10,
$$

$$
\eta_C=0.20,
$$

$$
\eta_E=0.30,
$$

$$
\tau_E=0.70.
$$

But critically, the first behavioral experiment should set

$$
\boxed{
\beta_P=0.
}
$$

Use

$$
\beta_C=0
$$

initially as well.

So the first serious test is almost minimal:

$$
\boxed{
\text{static graph}
+
\text{multi-hop answer flow}
+
\text{personal reinforcement}.
}
$$

If that already produces growing copying, stable flow concentration, brokers, cascades, or knowledge/grade separation, we have a genuinely interesting emergent result.

Then add

$$
\beta_P>0
$$

to measure what explicit peer influence contributes.

Then add confidence.

Then add exams/effort feedback.

---

# 48. Final V1 causal diagram

The minimal core is

$$
\boxed{
\begin{array}{ccccc}
K_i
&\rightarrow&
\text{answer quality}
&\rightarrow&
G_i
\\[4pt]
&&&&\downarrow
\\
A
&\rightarrow&
\text{answer accessibility}
&\rightarrow&
R_i
\\
&&\downarrow&&\downarrow
\\
&&\text{paths/cascades}
&&Q_i
\\
&&&&\downarrow
\\
&&&&P_i(S,D,C)
\end{array}
}
$$

with optional extensions

$$
G_i\rightarrow C_i\rightarrow P_i(S)
$$

and

$$
\text{peer requests}
\rightarrow
X_i
\rightarrow
P_i(C).
$$

The social graph itself never learns.

The cheating graph itself never exists as causal state.

Therefore the interesting mesoscale structures have to be generated repeatedly from local decisions.

---

# 49. What V1 can legitimately claim

If V1 produces a copying cascade, we can say:

> Under these specified local mechanisms and network conditions, copying cascades emerged.

We cannot say:

> Real classrooms necessarily behave this way.

If a high-betweenness copying broker appears, we can say:

> The model generated a broker role without explicitly assigning one.

We must still test whether this exceeds what node degree alone predicts.

If copying prevalence rises under

$$
\beta_P=0,
$$

that is especially interesting because:

$$
\boxed{
\text{behavior spread without an explicit peer-imitation rule}.
}
$$

If copying only spreads when

$$
\beta_P>0,
$$

then the correct conclusion is different:

> Explicit socially mediated behavioral influence was necessary for copying diffusion under the tested assumptions.

Both outcomes are scientifically informative.

The purpose of V1 is not to make the desired behavior happen.

It is to determine **which minimal mechanisms are actually sufficient to make it happen**.
