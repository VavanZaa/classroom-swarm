"""A21 V3 generative behaviour model (docs/10).

V3 is deliberately separate from engine.simulate so its new behavioural equations cannot alter the
V1/V2 reference path. It reuses Graph, Packet, DrawProvider and canonical raw logging.
"""
from __future__ import annotations

import math
import platform
from dataclasses import asdict, dataclass, field
from pathlib import Path
from statistics import NormalDist
from typing import Mapping, Sequence

import networkx
import numpy as np
import pyarrow

from .config import FAMILIES
from .engine import ACTIONS, Packet
from .graphs import Graph, generate_graph, with_edge_weights
from .records import RunLog, append_row
from .rng import BIT_GENERATOR, FAMILY_CODE, RNG_SCHEME, STREAM_CODE, DrawProvider, Draws, graph_seed, pick, weighted_pick
from .storage import write_replicate


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


def _finite(*values: float) -> bool:
    return all(isinstance(v, (int, float)) and math.isfinite(v) for v in values)


@dataclass(frozen=True)
class V3Params:
    # Environment and measurement
    N: int = 30
    H: int = 20
    F_E: int | None = 5
    M_H: int = 10
    M_E: int = 30
    # Mean traits and learning
    K0: float = 0.5
    alpha: float = 0.0584
    kappa: float = 0.15
    copy_success_cost: int = 0
    chi_C: float = 0.10
    eta_Q: float = 0.20
    eta_C: float = 0.20
    # A21 seed, exploration and directed reliability
    seed_fraction: float = 0.10
    epsilon: float = 0.06
    A0: float = 0.50
    eta_A: float = 0.20
    # A21 endogenous sharing
    share_p0: float = 0.80
    share_reciprocity: float = 2.0
    share_capacity: int = 2
    # A21 unassigned heterogeneity
    K0_sd: float = 0.10
    alpha_log_sd: float = 0.25
    kappa_log_sd: float = 0.25
    # Optional generic, action-symmetric social learning
    eta_social: float = 0.0
    # Frozen topology parameters (same generators as V1/V2)
    d_bar: int = 6
    omega: float = 0.1
    sbm_ratio: float = 5.0

    def validate(self) -> None:
        for name in ("N", "H", "M_H", "M_E", "d_bar", "share_capacity", "copy_success_cost"):
            value = getattr(self, name)
            _require(isinstance(value, int) and not isinstance(value, bool), f"{name} must be an integer")
        _require(self.N >= 1 and self.H >= 1 and self.M_H >= 1 and self.M_E >= 1, "sizes must be >= 1")
        _require(self.F_E is None or (isinstance(self.F_E, int) and self.F_E >= 1), "F_E must be None or >= 1")
        _require(self.share_capacity >= 1, "share_capacity must be >= 1")
        _require(self.copy_success_cost in (0, 1), "copy_success_cost must be 0 or 1")
        _require(self.d_bar >= 2 and self.d_bar % 2 == 0 and self.d_bar < self.N,
                 "d_bar must be even, >= 2 and < N")
        numeric = (self.K0, self.alpha, self.kappa, self.chi_C, self.eta_Q, self.eta_C,
                   self.seed_fraction, self.epsilon, self.A0, self.eta_A, self.share_p0,
                   self.share_reciprocity, self.K0_sd, self.alpha_log_sd, self.kappa_log_sd,
                   self.eta_social, self.omega, self.sbm_ratio)
        _require(_finite(*numeric), "V3 parameters must be finite")
        _require(0.0 <= self.K0 <= 1.0, "K0 must be in [0, 1]")
        _require(self.alpha > 0.0 and self.kappa >= 0.0, "alpha must be > 0 and kappa >= 0")
        for name in ("chi_C", "eta_Q", "eta_C", "seed_fraction", "epsilon", "eta_A", "share_p0",
                     "eta_social", "omega"):
            _require(0.0 <= getattr(self, name) <= 1.0, f"{name} must be in [0, 1]")
        _require(self.eta_A < 1.0, "eta_A must be < 1 so direct-tie beliefs stay strictly positive")
        _require(0.0 < self.A0 < 1.0, "A0 must be in (0, 1)")
        _require(self.K0_sd >= 0 and self.alpha_log_sd >= 0 and self.kappa_log_sd >= 0,
                 "trait spread parameters must be >= 0")
        _require(self.sbm_ratio > 0.0, "sbm_ratio must be > 0")


@dataclass(frozen=True)
class V3RunSpec:
    experiment_id: str
    replicate: int
    family: str
    R: int
    params: V3Params
    master_seed: int

    def __post_init__(self) -> None:
        _require(bool(self.experiment_id) and "/" not in self.experiment_id, "experiment_id must be non-empty, no '/'")
        _require(self.family in FAMILIES, f"family must be one of {FAMILIES}")
        _require(isinstance(self.replicate, int) and self.replicate >= 0, "replicate must be non-negative")
        _require(isinstance(self.R, int) and self.R >= 1, "R must be >= 1")
        _require(isinstance(self.master_seed, int) and self.master_seed >= 0, "master_seed must be non-negative")
        self.params.validate()

    @property
    def run_id(self) -> str:
        return f"{self.experiment_id}/rep{self.replicate:04d}/{self.family}/R{self.R}/V3"


@dataclass(frozen=True)
class V3Controls:
    """Testing and trait-null controls; defaults are used in scientific runs."""
    trait_permutation: tuple[int, ...] | None = None
    force_action: str | None = None

    def __post_init__(self) -> None:
        _require(self.force_action in (None, "S", "D", "C"), "force_action must be None, S, D or C")


@dataclass(frozen=True)
class TraitState:
    K0: np.ndarray
    alpha: np.ndarray
    kappa: np.ndarray


@dataclass
class V3RoutingResult:
    received: dict[int, tuple[Packet, int, int]] = field(default_factory=dict)
    requests: list[tuple[int, int, int, bool, bool]] = field(default_factory=list)
    incoming: dict[int, set[int]] = field(default_factory=dict)
    sharing_events: list[dict] = field(default_factory=list)
    belief_outcomes: list[tuple[int, int, bool]] = field(default_factory=list)


def initial_traits(p: V3Params, draws: DrawProvider,
                   controls: V3Controls = V3Controls()) -> TraitState:
    z = np.asarray(draws.traits(), dtype=float)
    if z.shape != (3, p.N):
        raise ValueError(f"traits draw must have shape (3, {p.N})")
    if p.K0_sd == 0.0:
        K0 = np.full(p.N, p.K0)
    else:
        normal = NormalDist()
        lo = normal.cdf((0.0 - p.K0) / p.K0_sd)
        hi = normal.cdf((1.0 - p.K0) / p.K0_sd)
        uniforms = np.array([normal.cdf(float(value)) for value in z[0]])
        lower, upper = np.nextafter(0.0, 1.0), np.nextafter(1.0, 0.0)
        probabilities = np.clip(lo + uniforms * (hi - lo), lower, upper)
        K0 = np.array([p.K0 + p.K0_sd * normal.inv_cdf(float(prob)) for prob in probabilities])
    alpha = p.alpha * np.exp(p.alpha_log_sd * z[1] - 0.5 * p.alpha_log_sd ** 2)
    kappa = p.kappa * np.exp(p.kappa_log_sd * z[2] - 0.5 * p.kappa_log_sd ** 2)
    if controls.trait_permutation is not None:
        perm = np.asarray(controls.trait_permutation, dtype=int)
        if perm.shape != (p.N,) or sorted(perm.tolist()) != list(range(p.N)):
            raise ValueError("trait_permutation must be a permutation of 0..N-1")
        K0, alpha, kappa = K0[perm], alpha[perm], kappa[perm]
    return TraitState(K0, alpha, kappa)


def seed_probabilities(feasible_social: np.ndarray, seed_fraction: float) -> np.ndarray:
    feasible = np.asarray(feasible_social, dtype=bool)
    _require(0.0 <= seed_fraction <= 1.0, "seed_fraction must be in [0, 1]")
    P = np.zeros((len(feasible), 3), float)
    P[feasible] = ((1.0 - seed_fraction) / 2.0, (1.0 - seed_fraction) / 2.0, seed_fraction)
    P[~feasible] = (1.0, 0.0, 0.0)
    return P


def _utilities(Q: np.ndarray, access: np.ndarray, kappa: np.ndarray, A0: float) -> np.ndarray:
    U = np.asarray(Q, dtype=float).copy()
    U[:, 2] += np.asarray(kappa, dtype=float) * (np.asarray(access, dtype=float) - A0)
    return U


def action_probabilities(Q: np.ndarray, expected_access: np.ndarray, kappa: np.ndarray,
                         feasible_social: np.ndarray, epsilon: float, A0: float) -> np.ndarray:
    """Marginal epsilon-greedy probabilities. Deliberately has no prevalence/X argument (T27)."""
    _require(0.0 <= epsilon <= 1.0, "epsilon must be in [0, 1]")
    U = _utilities(Q, expected_access, kappa, A0)
    feasible = np.asarray(feasible_social, dtype=bool)
    P = np.zeros_like(U)
    for i in range(len(P)):
        actions = (0, 1, 2) if feasible[i] else (0,)
        best = max(U[i, a] for a in actions)
        ties = [a for a in actions if U[i, a] == best]
        for a in actions:
            P[i, a] = epsilon / len(actions)
        for a in ties:
            P[i, a] += (1.0 - epsilon) / len(ties)
    return P


def expected_access(neighbors: Sequence[Sequence[int]], neighbor_weights: Sequence[Sequence[float]],
                    A: np.ndarray) -> np.ndarray:
    out = np.zeros(len(neighbors), float)
    for i, nb in enumerate(neighbors):
        if not nb:
            continue
        beliefs = np.array([A[i, j] for j in nb], float)
        scores = np.asarray(neighbor_weights[i], float) * beliefs
        out[i] = float(np.dot(scores / scores.sum(), beliefs))
    return out


def share_probability(base: float, reciprocity: float, reverse_belief: float, A0: float) -> float:
    if base <= 0.0:
        return 0.0
    if base >= 1.0:
        return 1.0
    logit = math.log(base / (1.0 - base)) + reciprocity * (reverse_belief - A0)
    return 1.0 / (1.0 + math.exp(-logit))


def update_beliefs(A: np.ndarray, outcomes: Sequence[tuple[int, int, bool]], eta_A: float) -> np.ndarray:
    if not 0.0 <= eta_A < 1.0:
        raise ValueError("eta_A must be in [0, 1)")
    updated = np.asarray(A, dtype=float).copy()
    for requester, target, success in outcomes:
        if not math.isfinite(float(updated[requester, target])):
            raise ValueError("belief update must address an existing directed social tie")
        updated[requester, target] += eta_A * (float(bool(success)) - updated[requester, target])
    return updated


def social_update(Q: np.ndarray, actions: Sequence[str], rewards: np.ndarray,
                  neighbors: Sequence[Sequence[int]], neighbor_weights: Sequence[Sequence[float]],
                  eta_social: float) -> np.ndarray:
    updated = np.asarray(Q, dtype=float).copy()
    if eta_social == 0.0:
        return updated
    for i, nb in enumerate(neighbors):
        for k, action in enumerate(ACTIONS):
            observed = [(j, w) for j, w in zip(nb, neighbor_weights[i]) if actions[j] == action]
            if not observed:
                continue
            total = sum(w for _, w in observed)
            target = sum(w * float(rewards[j]) for j, w in observed) / total
            updated[i, k] += eta_social * (target - updated[i, k])
    return updated


def route_v3(neighbors: Sequence[Sequence[int]], neighbor_weights: Sequence[Sequence[float]],
             A: np.ndarray, holders: Mapping[int, Packet], copiers: Sequence[int],
             U_routing: np.ndarray, U_sharing: np.ndarray, *, share_p0: float,
             share_reciprocity: float, A0: float, capacity: int) -> V3RoutingResult:
    """Synchronous A21 routing with learned targeting, willingness and per-homework capacity."""
    U_routing, U_sharing = np.asarray(U_routing, float), np.asarray(U_sharing, float)
    if U_routing.shape != U_sharing.shape:
        raise ValueError("routing and sharing tensors must have the same shape")
    N = len(neighbors)
    if A.shape != (N, N) or len(neighbor_weights) != N:
        raise ValueError("V3 routing inputs do not match N")
    weight_maps = [dict(zip(nb, ws)) for nb, ws in zip(neighbors, neighbor_weights)]
    possession: dict[int, Packet] = dict(holders)
    queried = {i: set() for i in copiers}
    unresolved = sorted(i for i in copiers if i not in possession)
    remaining_capacity = [capacity] * N
    result = V3RoutingResult()

    for rnd in range(1, U_routing.shape[0] + 1):
        holding_at_start = set(possession)
        attempts = []
        for i in unresolved:
            remaining = sorted(set(neighbors[i]) - queried[i])
            if not remaining:
                continue
            scores = [weight_maps[i][j] * float(A[i, j]) for j in remaining]
            j = weighted_pick(remaining, scores, float(U_routing[rnd - 1, i]))
            queried[i].add(j)
            had = j in holding_at_start
            result.incoming.setdefault(j, set()).add(i)
            if had:
                prob = share_probability(share_p0, share_reciprocity, float(A[j, i]), A0)
                draw = float(U_sharing[rnd - 1, i])
                willing = draw < prob
            else:
                prob, draw, willing = None, None, None
            attempts.append({"requester": i, "target": j, "had": had, "prob": prob,
                             "draw": draw, "willing": willing})

        granted: set[tuple[int, int]] = set()
        for target in sorted({a["target"] for a in attempts if a["had"] and a["willing"]}):
            eligible = [a for a in attempts if a["target"] == target and a["had"] and a["willing"]]
            eligible.sort(key=lambda a: (a["draw"], a["requester"]))
            for attempt in eligible[:remaining_capacity[target]]:
                granted.add((attempt["requester"], target))
            remaining_capacity[target] -= min(len(eligible), remaining_capacity[target])

        scheduled: list[tuple[int, int]] = []
        for attempt in attempts:
            i, j, had, willing = attempt["requester"], attempt["target"], attempt["had"], attempt["willing"]
            success = (i, j) in granted
            if not had:
                capacity_available = None
            elif willing:
                capacity_available = success
            else:
                capacity_available = remaining_capacity[j] > 0
            result.requests.append((rnd, i, j, had, success))
            result.belief_outcomes.append((i, j, success))
            result.sharing_events.append({
                "round": rnd, "requester_id": i, "target_id": j, "target_had_packet": had,
                "share_probability": attempt["prob"], "sharing_draw": attempt["draw"],
                "willing": willing, "capacity_available": capacity_available, "share_granted": success,
            })
            if success:
                scheduled.append((j, i))
        for j, i in scheduled:
            src = possession[j]
            packet = Packet(src.answer_id, src.root, src.depth + 1, src.items)
            possession[i] = packet
            result.received[i] = (packet, j, rnd)
        unresolved = [i for i in unresolved if i not in result.received]
    return result


def _answers(uniforms: np.ndarray, probability: float) -> tuple[bool, ...]:
    return tuple(bool(u < probability) for u in uniforms)


def _clip01(x: float) -> float:
    return min(max(float(x), 0.0), 1.0)


def _log_event(log: RunLog, event_id: str, seq: int, kind: str, h: int | None, exam: int | None = None) -> None:
    is_exam = kind == "exam"
    append_row(log.tables, "events", run_id=log.run_id, event_id=event_id, seq=seq, event_type=kind,
               homework_index=h, exam_index=exam, diagnostic_only=True if is_exam else None,
               exam_updates_confidence=False if is_exam else None,
               exam_updates_effort=False if is_exam else None)


def _log_state(log: RunLog, event_id: str, K, C, E, Q) -> None:
    for i in range(len(K)):
        append_row(log.tables, "state_snapshots", run_id=log.run_id, event_id=event_id, student_id=i,
                   K=float(K[i]), C=float(C[i]), E=float(E[i]), Q_S=float(Q[i, 0]),
                   Q_D=float(Q[i, 1]), Q_C=float(Q[i, 2]), X=0.0)


def _log_ties(log: RunLog, event_id: str, neighbors, A) -> None:
    for i, nb in enumerate(neighbors):
        for j in nb:
            append_row(log.tables, "tie_snapshots", run_id=log.run_id, event_id=event_id,
                       observer_id=i, target_id=j, A=float(A[i, j]))


def _manifest(spec: V3RunSpec, graph: Graph, draws: DrawProvider, controls: V3Controls) -> dict:
    return {
        "run_id": spec.run_id, "experiment_id": spec.experiment_id, "replicate": spec.replicate,
        "family": spec.family, "R": spec.R, "stage": "V3", "model_version": "V3",
        "master_seed": spec.master_seed, "rng_scheme": RNG_SCHEME, "bit_generator": BIT_GENERATOR,
        "stream_codes": dict(STREAM_CODE), "draws_provider": type(draws).__name__, "R_max": draws.R_max,
        "base_params": asdict(spec.params), "effective_params": asdict(spec.params),
        "controls": asdict(controls), "q0_mode": "individual_K0_minus_kappa",
        "graph": {"family": graph.family, "N": graph.N, "seed": graph.seed,
                  "generator_params": dict(graph.generator_params), "edge_hash": graph.edge_hash,
                  "weight_hash": graph.weight_hash, **graph.summary()},
    }


def simulate_v3(spec: V3RunSpec, graph: Graph, draws: DrawProvider, *,
                controls: V3Controls = V3Controls()) -> RunLog:
    """Run one A21 V3 classroom. Pure: all random inputs come from `draws`."""
    p, N = spec.params, spec.params.N
    if graph.N != N or graph.family != spec.family:
        raise ValueError("graph does not match V3RunSpec")
    if spec.R > draws.R_max:
        raise ValueError("R exceeds draws.R_max")
    traits = initial_traits(p, draws, controls)
    nbrs, nbr_weights = graph.neighbors, graph.neighbor_weights
    feasible = np.array(graph.degree) > 0

    K, C, E = traits.K0.copy(), traits.K0.copy(), np.ones(N)
    Q = np.column_stack([traits.K0 - traits.kappa] * 3)
    A = np.full((N, N), np.nan)
    for u, v in graph.edges:
        A[u, v] = A[v, u] = p.A0

    log = RunLog(spec.run_id, _manifest(spec, graph, draws, controls))
    for i in range(N):
        append_row(log.tables, "graph_nodes", run_id=spec.run_id, student_id=i,
                   community_id=None if graph.community is None else graph.community[i], degree=int(graph.degree[i]))
        append_row(log.tables, "agent_traits", run_id=spec.run_id, student_id=i, K0=float(traits.K0[i]),
                   alpha=float(traits.alpha[i]), kappa=float(traits.kappa[i]))
    for (u, v), weight in zip(graph.edges, graph.weights):
        append_row(log.tables, "graph_edges", run_id=spec.run_id, u=u, v=v, weight=float(weight))
    seq, exam_index = 0, 0
    _log_event(log, "init", seq, "init", None)
    _log_state(log, "init", K, C, E, Q)
    _log_ties(log, "init", nbrs, A)

    for h in range(1, p.H + 1):
        K0, C0, Q0, A0_matrix = K.copy(), C.copy(), Q.copy(), A.copy()
        access = expected_access(nbrs, nbr_weights, A0_matrix)
        U_strategy = np.asarray(draws.strategy(h), float)
        explored = np.zeros(N, dtype=bool)
        modes: list[str] = []
        if h == 1:
            P = seed_probabilities(feasible, p.seed_fraction)
            actions = []
            for i, u in enumerate(U_strategy):
                if controls.force_action is not None:
                    a = controls.force_action if (controls.force_action == "S" or feasible[i]) else "S"
                elif u < P[i, 0]:
                    a = "S"
                elif u < P[i, 0] + P[i, 1]:
                    a = "D"
                else:
                    a = "C"
                actions.append(a)
                modes.append("forced" if controls.force_action else ("seed" if a == "C" else "initial_honest"))
        else:
            P = action_probabilities(Q0, access, traits.kappa, feasible, p.epsilon, p.A0)
            U = _utilities(Q0, access, traits.kappa, p.A0)
            U_explore = np.asarray(draws.exploration(h), float)
            actions = []
            for i in range(N):
                possible = [0, 1, 2] if feasible[i] else [0]
                explored[i] = U_explore[i] < p.epsilon
                if controls.force_action is not None:
                    a = controls.force_action if (controls.force_action == "S" or feasible[i]) else "S"
                    modes.append("forced")
                elif explored[i]:
                    a = ACTIONS[pick(possible, float(U_strategy[i]))]
                    modes.append("explore")
                else:
                    best = max(U[i, k] for k in possible)
                    ties = [k for k in possible if U[i, k] == best]
                    a = ACTIONS[pick(ties, float(U_strategy[i]))]
                    modes.append("exploit")
                actions.append(a)

        U_item, U_partner = np.asarray(draws.item(h), float), np.asarray(draws.partner(h), float)
        K_next = K0.copy()
        own: dict[int, Packet] = {}
        partners: list[int | None] = [None] * N
        for i, action in enumerate(actions):
            if action == "S":
                K_next[i] = _clip01(K0[i] + traits.alpha[i] * (1.0 - K0[i]))
                probability = K_next[i]
            elif action == "D":
                j = weighted_pick(nbrs[i], nbr_weights[i], float(U_partner[i]))
                partners[i] = j
                gain = 1.0 + max(K0[j] - K0[i], 0.0)
                K_next[i] = _clip01(K0[i] + traits.alpha[i] * (1.0 - K0[i]) * gain)
                probability = max(K_next[i], K0[j])
            else:
                continue
            own[i] = Packet(f"h{h}-s{i}", i, 0, _answers(U_item[:, i], probability))

        copiers = [i for i, action in enumerate(actions) if action == "C"]
        routed = route_v3(nbrs, nbr_weights, A0_matrix, own, copiers,
                          np.asarray(draws.routing(h), float)[:spec.R],
                          np.asarray(draws.sharing(h), float)[:spec.R], share_p0=p.share_p0,
                          share_reciprocity=p.share_reciprocity, A0=p.A0, capacity=p.share_capacity)
        final: list[tuple[Packet, str, int, bool | None]] = []
        for i, action in enumerate(actions):
            if action != "C":
                final.append((own[i], action, 1, None))
            elif i in routed.received:
                K_next[i] = _clip01(K0[i] + p.chi_C * traits.alpha[i] * (1.0 - K0[i]))
                final.append((routed.received[i][0], "copied", p.copy_success_cost, True))
            else:
                packet = Packet(f"h{h}-s{i}", i, 0, _answers(U_item[:, i], K0[i]))
                final.append((packet, "fallback", 1, False))
        grade = np.array([sum(packet.items) / p.M_H for packet, _, _, _ in final])
        cost = np.array([c for _, _, c, _ in final], int)
        reward = grade - traits.kappa * cost
        C_next = np.clip(C0 + p.eta_C * (grade - C0), 0.0, 1.0)
        Q_next = Q0.copy()
        for i, action in enumerate(actions):
            k = ACTIONS.index(action)
            Q_next[i, k] += p.eta_Q * (reward[i] - Q_next[i, k])
        Q_next = social_update(Q_next, actions, reward, nbrs, nbr_weights, p.eta_social)
        A_next = update_beliefs(A0_matrix, routed.belief_outcomes, p.eta_A)
        K, C, Q, A = K_next, C_next, Q_next, A_next

        seq += 1
        event_id = f"h{h}"
        _log_event(log, event_id, seq, "homework", h)
        for i, action in enumerate(actions):
            packet, mode, c, success = final[i]
            append_row(log.tables, "decisions", run_id=spec.run_id, event_id=event_id, homework_index=h,
                       student_id=i, feasible_S=True, feasible_D=bool(feasible[i]), feasible_C=bool(feasible[i]),
                       P_S=float(P[i, 0]), P_D=float(P[i, 1]), P_C=float(P[i, 2]), action=action,
                       partner_id=partners[i], grade=float(grade[i]), reward=float(reward[i]), cost=int(c),
                       copy_success=success, answer_id=packet.answer_id, root_id=packet.root, depth=packet.depth)
            append_row(log.tables, "v3_decisions", run_id=spec.run_id, event_id=event_id, homework_index=h,
                       student_id=i, decision_mode=modes[i], seeded=bool(h == 1 and action == "C"),
                       explored=bool(explored[i]), expected_access=float(access[i]))
            for q, correct in enumerate(packet.items):
                append_row(log.tables, "item_outcomes", run_id=spec.run_id, event_id=event_id, student_id=i,
                           item=q, correct=correct, mode=mode, answer_id=packet.answer_id, root_id=packet.root)
        for rnd, requester, target, had, success in routed.requests:
            if success:
                packet, sender, got_round = routed.received[requester]
                assert sender == target and got_round == rnd
                ids = dict(answer_id=packet.answer_id, root_id=packet.root,
                           sender_depth=packet.depth - 1, receiver_depth=packet.depth)
            else:
                ids = dict(answer_id=None, root_id=None, sender_depth=None, receiver_depth=None)
            append_row(log.tables, "routing_events", run_id=spec.run_id, homework_index=h, round=rnd,
                       requester_id=requester, target_id=target, target_had_packet=had,
                       transfer_success=success, **ids)
        for row in routed.sharing_events:
            append_row(log.tables, "sharing_events", run_id=spec.run_id, homework_index=h, **row)
        _log_state(log, event_id, K, C, E, Q)
        _log_ties(log, event_id, nbrs, A)

        if p.F_E is not None and h % p.F_E == 0:
            exam_index += 1
            correct = np.asarray(draws.exam(exam_index), float) < K[None, :]
            seq += 1
            exam_event = f"e{exam_index}"
            _log_event(log, exam_event, seq, "exam", h, exam_index)
            for i in range(N):
                for q in range(p.M_E):
                    append_row(log.tables, "item_outcomes", run_id=spec.run_id, event_id=exam_event,
                               student_id=i, item=q, correct=bool(correct[q, i]), mode="exam",
                               answer_id=None, root_id=None)
            _log_state(log, exam_event, K, C, E, Q)
            _log_ties(log, exam_event, nbrs, A)
    return log


def run_v3_replicate(experiment_id: str, replicate: int, master_seed: int, params: V3Params,
                     out_root: Path, *, families: Sequence[str] = ("ER", "WS", "SBM"), R: int = 3,
                     edge_weights: Mapping[str, Mapping[tuple[int, int], float] | Sequence[float]] | None = None,
                     controls: V3Controls = V3Controls()) -> Path:
    """Small transparent V3 runner. It performs no analysis and never tunes or interprets outcomes."""
    params.validate()
    if not families or any(family not in FAMILIES for family in families):
        raise ValueError("families must be a non-empty sequence of known graph families")
    if not isinstance(R, int) or R < 1:
        raise ValueError("R must be an integer >= 1")
    draws = Draws(master_seed, replicate, params.N, params.M_H, params.M_E, R_max=R)
    logs = []
    supplied = edge_weights or {}
    if set(supplied) - set(families):
        raise ValueError("edge_weights contains a family not included in this run")
    for family in families:
        graph = generate_graph(family, params, graph_seed(master_seed, replicate, family))
        if family in supplied:
            graph = with_edge_weights(graph, supplied[family])
        spec = V3RunSpec(experiment_id, replicate, family, R, params, master_seed)
        logs.append(simulate_v3(spec, graph, draws, controls=controls))
    shared = {
        "experiment_id": experiment_id, "model_version": "V3", "replicate": replicate,
        "master_seed": master_seed, "rng_scheme": RNG_SCHEME, "bit_generator": BIT_GENERATOR,
        "stream_codes": dict(STREAM_CODE), "family_codes": dict(FAMILY_CODE), "R_max": R,
        "versions": {"python": platform.python_version(), "numpy": np.__version__,
                     "networkx": networkx.__version__, "pyarrow": pyarrow.__version__},
    }
    from .experiment import _git_state
    shared.update(_git_state())
    rep_dir = Path(out_root) / f"rep{replicate:04d}"
    write_replicate(rep_dir, logs, shared)
    return rep_dir
