---
type: spec
updated: 2026-09-20
status: FROZEN
tags:
  - spec
  - v3
---
# 10 · V3 generative behaviour model

V3 is a separate model approved in A21. It asks whether copying levels, routes, source roles and brokerage can arise from local experience and constrained exchange without a copying-prevalence term. V1 and V2 remain historical reference models and their equations are untouched.

## 1. Emergence boundary

- There is no $\beta_P X$ term. Neighbour copying prevalence is neither state nor input to choice.
- No student is assigned a cheater, source, broker or good-student role.
- Frozen $w_{ij}=w_{ji}>0$ means exogenous contact opportunity only (A20).
- Directed $A_{ij}(h)\in(0,1)$ is student $i$'s private estimate that neighbour $j$ can and will supply an answer. It is learned only when $i$ requests from $j$.
- The cheating-flow graph remains derived output and never updates $w$, $A$, utilities or sharing.
- All numerical defaults below are provisional mechanistic choices approved for implementation, not calibrated educational estimates.

## 2. V3 parameters

Reference environment, learning and measurement values stay $N=30$, $H=20$, $M_H=10$, $M_E=30$, $F_E=5$, $K_0=0.5$, $\alpha=0.0584$, $\kappa=0.15$, $\chi_C=0.10$, $\eta_Q=0.20$, $\eta_C=0.20$ and $R=3$.

| Parameter | Default | Meaning |
|---|---:|---|
| $s_0$ | 0.10 | copying seed probability on homework 1 only |
| $\epsilon$ | 0.06 | action-neutral exploration probability from homework 2 |
| $A_0$ | 0.50 | initial directed source-reliability belief |
| $\eta_A$ | 0.20 | reliability learning rate after a direct request |
| $p_{share}^0$ | 0.80 | baseline willingness to share |
| $\beta_R$ | 2.0 | reciprocity effect on sharing log odds |
| $L$ | 2 | maximum answers supplied by one holder per homework |
| $\sigma_K$ | 0.10 | SD of initial-knowledge normal distribution |
| $\sigma_{\log\alpha}$ | 0.25 | log-SD of learning efficiency |
| $\sigma_{\log\kappa}$ | 0.25 | log-SD of effort cost |
| $\eta_{social}$ | 0 | optional symmetric social-learning rate; off in baseline |
| $c_C^{success}$ | 0 | successful-copy effort cost; fixed to 1 only in the preregistered equal-cost control |

## 3. Unassigned traits

Three independent standard-normal draws per student are generated independently of graph family and position:

For knowledge, transform the standard-normal draw through the inverse CDF of
$\mathcal N(K_0,\sigma_K^2)$ truncated to $[0,1]$ (and use $K_0$ exactly when $\sigma_K=0$). Denoting
this deterministic transform by $T_{[0,1]}$:

$$K_{0i}=T_{[0,1]}(K_0,\sigma_K,Z^K_i),$$
$$\alpha_i=\alpha\exp(\sigma_{\log\alpha}Z^\alpha_i-\tfrac12\sigma_{\log\alpha}^2),$$
$$\kappa_i=\kappa\exp(\sigma_{\log\kappa}Z^\kappa_i-\tfrac12\sigma_{\log\kappa}^2).$$

The lognormal correction preserves the untruncated mean. A trait-shuffle control applies one explicit permutation to complete $(K_{0i},\alpha_i,\kappa_i)$ bundles, preserving the joint sample while breaking its node assignment. Initially $C_i=K_{0i}$, $E_i=1$, and $Q_i^S=Q_i^D=Q_i^C=K_{0i}-\kappa_i$.

## 4. Choice without prevalence

Isolates can only choose S. For feasible students on homework 1:

$$P(C)=s_0,\qquad P(S)=P(D)=\frac{1-s_0}{2}.$$

Choosing C on homework 1 is the declared seed. The seed is absent from every later homework.

For $h\ge2$, define target-selection probabilities and expected access from the frozen pre-homework beliefs:

$$\pi_{ij}=\frac{w_{ij}A_{ij}}{\sum_{k\in N_i}w_{ik}A_{ik}},\qquad
\widehat A_i=\sum_{j\in N_i}\pi_{ij}A_{ij}.$$

Utilities are

$$U_i^S=Q_i^S,\qquad U_i^D=Q_i^D,\qquad
U_i^C=Q_i^C+\kappa_i(\widehat A_i-A_0).$$

There is no prevalence input. With probability $\epsilon$, choose uniformly among feasible actions. Otherwise choose uniformly among actions tied for maximum utility. Exploration uses its own semantic uniform and is action-neutral.

## 5. Production and target selection

S and D use the existing frozen-state learning and answer equations, replacing common $\alpha,\kappa$ with $\alpha_i,\kappa_i$. Discussion partner selection uses only $w_{ij}$.

Each unresolved copier selects among not-yet-requested neighbours with probability proportional to $w_{ij}A_{ij}$, using frozen pre-homework $A$. Routing remains synchronous and one hop per round.

## 6. Endogenous sharing and capacity

If requester $i$ asks holder $j$, the holder's willingness is

$$p_{j\rightarrow i}=\operatorname{logistic}\left(
\operatorname{logit}(p_{share}^0)+\beta_R(A_{ji}-A_0)\right).$$

$A_{ji}$ makes reciprocity local: $j$ is more willing to help $i$ only when $j$'s own prior requests to $i$ were successful. A new semantic sharing uniform determines willingness. Each holder can complete at most $L$ transfers per homework. Within one round, willing simultaneous requests compete by ascending sharing uniform, then requester id; earlier rounds consume capacity first. Packets still commit synchronously at round end.

Every direct request updates only the requester's belief after the homework:

$$A_{ij}'=A_{ij}+\eta_A(Y_{ij}-A_{ij}),$$

where $Y_{ij}=1$ only if a transfer actually succeeded. No observation or third-party event updates $A_{ij}$.

## 7. Outcomes, personal learning and optional social learning

Copy learning, fallback answers and item generation retain the V1 equations, using individual $\alpha_i$. Individual realised reward is

$$R_i=G_i^H-\kappa_i c_i.$$

The baseline cost is 1 for S, D and failed-copy fallback, and 0 for a successful copy. Because this
payoff difference can itself make copying attractive, a scientific emergence test must include the
equal-cost control $c_C^{success}=1$ and may not describe a baseline effect as cost-independent unless
it survives that control.

The chosen action value receives the personal update

$$Q_i^{a_i}\leftarrow Q_i^{a_i}+\eta_Q(R_i-Q_i^{a_i}).$$

If $\eta_{social}>0$, student $i$ observes each neighbour's action and reward. For every action $a$ represented among neighbours, compute the contact-weighted mean $\bar R_{i,a}$ and apply symmetrically:

$$Q_i^a\leftarrow Q_i^a+\eta_{social}(\bar R_{i,a}-Q_i^a).$$

The rule is identical for S, D and C. The baseline has $\eta_{social}=0$.

Confidence continues to track homework grades for measurement, $C_i'=C_i+\eta_C(G_i^H-C_i)$, but does not enter V3 choice. Exams are diagnostic and change no state in the first V3 implementation. Effort remains 1.

## 8. Required controls and claims

Before a V3 scientific run, preregister at least:

1. seed-off persistence and sensitivity to $s_0$;
2. $\epsilon=0$ and $\eta_A=0$ ablations;
3. unity weights, shuffled weights and trait-shuffled controls;
4. unlimited sharing and $p_{share}^0=1$ controls;
5. $\eta_{social}=0$ baseline and a positive symmetric-social-learning condition;
6. degree/strength-aware broker null before a weighted-broker claim;
7. horizon and class-size robustness.
8. successful-copy cost set to 1, isolating behavior that does not depend on the baseline effort-cost advantage.

Implementation tests establish equations and reproducibility only. They do not establish that V3 produces emergence.
