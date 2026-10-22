"""The V1 engine (docs/03, docs/09 engine.py). Stage-blind: it reads only EffectiveParams."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Mapping, Sequence

import numpy as np

from .config import EffectiveParams, RunSpec, SimulationControls, resolve_params
from .graphs import Graph
from .records import RunLog, append_row
from .rng import BIT_GENERATOR, RNG_SCHEME, STREAM_CODE, DrawProvider, pick, weighted_pick

ACTIONS = ("S", "D", "C")


@dataclass(frozen=True)
class Packet:
    answer_id: str           # "h{h}-s{root}"; unique only within a run: key is (run_id, answer_id)
    root: int
    depth: int               # 0 at the root
    items: tuple[bool, ...]  # exact item outcomes, inherited unchanged by copies


@dataclass
class RoutingResult:
    received: dict[int, tuple[Packet, int, int]] = field(default_factory=dict)  # receiver -> (packet, sender, round)
    requests: list[tuple[int, int, int, bool]] = field(default_factory=list)    # (round, requester, target, had)
    incoming: dict[int, set[int]] = field(default_factory=dict)                 # target -> distinct requesters


def route(neighbors: Sequence[Sequence[int]], holders: Mapping[int, Packet],
          copiers: Sequence[int], U_routing: np.ndarray,
          neighbor_weights: Sequence[Sequence[float]] | None = None) -> RoutingResult:
    """Synchronous answer routing (docs/03 step 4), one round per row of U_routing.

    Each unresolved copier asks one not-yet-queried neighbour per round, chosen by mapping its
    uniform onto the sorted remaining candidates. A transfer happens iff the target held a packet
    at the START of the round; all transfers commit together at the end of the round. No knowledge
    state is available here (T5).
    """
    U = np.asarray(U_routing, dtype=float)
    if neighbor_weights is None:
        neighbor_weights = tuple((1.0,) * len(nb) for nb in neighbors)
    if len(neighbor_weights) != len(neighbors) or any(len(w) != len(nb) for w, nb in zip(neighbor_weights, neighbors)):
        raise ValueError("neighbor_weights must align with neighbors")
    weight_by_neighbor = [dict(zip(nb, weights)) for nb, weights in zip(neighbors, neighbor_weights)]
    possession: dict[int, Packet] = dict(holders)
    result = RoutingResult()
    queried: dict[int, set[int]] = {i: set() for i in copiers}
    unresolved = sorted(i for i in copiers if i not in possession)
    for rnd in range(1, U.shape[0] + 1):
        holding_at_start = set(possession)
        scheduled: list[tuple[int, int]] = []
        for i in unresolved:
            remaining = sorted(set(neighbors[i]) - queried[i])
            if not remaining:
                continue
            j = weighted_pick(remaining, [weight_by_neighbor[i][candidate] for candidate in remaining],
                              float(U[rnd - 1, i]))
            queried[i].add(j)
            had = j in holding_at_start
            result.requests.append((rnd, i, j, had))
            result.incoming.setdefault(j, set()).add(i)
            if had:
                scheduled.append((j, i))
        for j, i in scheduled:  # simultaneous commit: senders held at round start, so their packets are unchanged
            src = possession[j]
            packet = Packet(src.answer_id, src.root, src.depth + 1, src.items)
            possession[i] = packet
            result.received[i] = (packet, j, rnd)
        unresolved = [i for i in unresolved if i not in result.received]
    return result


# ---------------------------------------------------------------- simulate

def _clip01(x: float) -> float:
    return min(max(float(x), 0.0), 1.0)


def _answers(uniforms: np.ndarray, probability: float) -> tuple[bool, ...]:
    """Item q is correct iff its fixed uniform is below the success probability (docs/05)."""
    return tuple(bool(u < probability) for u in uniforms)


def _sample_actions(P: np.ndarray, U: np.ndarray, controls: SimulationControls) -> list[str]:
    """Inverse CDF of each student's uniform over the fixed order (S, D, C)."""
    if controls.force_action == "S":
        return ["S"] * len(P)
    actions = []
    for i, u in enumerate(np.asarray(U, dtype=float)):
        if u < P[i, 0]:
            actions.append("S")
        elif u < P[i, 0] + P[i, 1]:
            actions.append("D")
        else:
            actions.append("C")
    return actions


def _manifest(spec: RunSpec, p: EffectiveParams, graph: Graph, draws: DrawProvider,
              controls: SimulationControls) -> dict:
    return {
        "run_id": spec.run_id, "experiment_id": spec.experiment_id, "replicate": spec.replicate,
        "family": spec.family, "R": spec.R, "stage": spec.stage.name, "master_seed": spec.master_seed,
        "rng_scheme": RNG_SCHEME, "bit_generator": BIT_GENERATOR, "stream_codes": dict(STREAM_CODE),
        "draws_provider": type(draws).__name__, "R_max": draws.R_max,
        "base_params": asdict(spec.params), "effective_params": asdict(p), "controls": asdict(controls),
        "q0_mode": "override" if spec.params.q0_override is not None else "derived",
        "graph": {"family": graph.family, "N": graph.N, "seed": graph.seed,
                   "generator_params": dict(graph.generator_params), "edge_hash": graph.edge_hash,
                  "weight_hash": graph.weight_hash,
                   **graph.summary()},
    }


def _log_event(log: RunLog, event_id: str, seq: int, event_type: str, homework_index: int | None,
               exam_index: int | None = None, flags: tuple[bool, bool, bool] | None = None) -> None:
    diagnostic, conf, effort = flags if flags is not None else (None, None, None)
    append_row(log.tables, "events", run_id=log.run_id, event_id=event_id, seq=seq, event_type=event_type,
               homework_index=homework_index, exam_index=exam_index, diagnostic_only=diagnostic,
               exam_updates_confidence=conf, exam_updates_effort=effort)


def _log_snapshot(log: RunLog, event_id: str, K, C, E, Q, X) -> None:
    for i in range(len(K)):
        append_row(log.tables, "state_snapshots", run_id=log.run_id, event_id=event_id, student_id=i,
                   K=float(K[i]), C=float(C[i]), E=float(E[i]),
                   Q_S=float(Q[i, 0]), Q_D=float(Q[i, 1]), Q_C=float(Q[i, 2]), X=float(X[i]))


def simulate(spec: RunSpec, graph: Graph, draws: DrawProvider, *,
             controls: SimulationControls = SimulationControls(),
             test_tally: bool = False) -> RunLog:
    """One run of docs/03. Pure: no I/O, no global state, all randomness from `draws`."""
    p = resolve_params(spec.stage, spec.params)
    if graph.N != p.N:
        raise ValueError(f"graph has N = {graph.N}, params say N = {p.N}")
    if graph.family != spec.family:
        raise ValueError(f"graph family {graph.family} != spec family {spec.family}")
    if spec.R > draws.R_max:
        raise ValueError(f"spec.R = {spec.R} exceeds draws.R_max = {draws.R_max}")
    if not isinstance(controls, SimulationControls):
        raise ValueError("controls must be a SimulationControls")

    N, run_id, nbrs = p.N, spec.run_id, graph.neighbors
    nbr_weights = graph.neighbor_weights
    degree = np.array(graph.degree, dtype=int)
    feasible = degree > 0  # D and C need at least one neighbour (A11)

    K = np.full(N, p.K0)
    C = np.full(N, p.C0)
    E = np.ones(N)
    Q = np.full((N, 3), p.q0)
    X = np.zeros(N)

    log = RunLog(run_id=run_id, manifest=_manifest(spec, p, graph, draws, controls))
    tally = {"H": {}, "grades": {}} if test_tally else None
    for i in range(N):
        append_row(log.tables, "graph_nodes", run_id=run_id, student_id=i,
                   community_id=None if graph.community is None else graph.community[i], degree=int(degree[i]))
    for (u, v), weight in zip(graph.edges, graph.weights):
        append_row(log.tables, "graph_edges", run_id=run_id, u=u, v=v, weight=float(weight))
    seq = 0
    _log_event(log, "init", seq, "init", None)
    _log_snapshot(log, "init", K, C, E, Q, X)

    exam_index = 0
    for h in range(1, p.H + 1):
        # 1. snapshot: every step below reads only the frozen pre-homework state
        K0, C0, E0, Q0, X0 = K.copy(), C.copy(), E.copy(), Q.copy(), X.copy()
        K_next = K0.copy()

        # 2. strategy choice
        P = strategy_probabilities(Q0, C0, X0, feasible, p)
        actions = _sample_actions(P, draws.strategy(h), controls)

        # 3. independent / discussion learning and answer creation
        U_item = np.asarray(draws.item(h), dtype=float)
        U_partner = np.asarray(draws.partner(h), dtype=float)
        own: dict[int, Packet] = {}
        partner: list[int | None] = [None] * N
        for i, a in enumerate(actions):
            if a == "S":
                K_next[i] = _clip01(K0[i] + p.alpha * E0[i] * (1.0 - K0[i]))
                prob = K_next[i]
            elif a == "D":
                j = weighted_pick(nbrs[i], nbr_weights[i], float(U_partner[i]))  # contact weights, never K
                partner[i] = j
                gain = 1.0 + max(K0[j] - K0[i], 0.0)
                K_next[i] = _clip01(K0[i] + p.alpha * E0[i] * (1.0 - K0[i]) * gain)
                prob = max(K_next[i], K0[j])
            else:
                continue
            own[i] = Packet(f"h{h}-s{i}", i, 0, _answers(U_item[:, i], prob))

        # 4. routing
        copiers = [i for i, a in enumerate(actions) if a == "C"]
        routing = route(nbrs, own, copiers, np.asarray(draws.routing(h), dtype=float)[:spec.R], nbr_weights)

        # 5. grades, copy learning, fallback
        final: list[tuple[Packet, str, int, bool | None]] = []
        for i, a in enumerate(actions):
            if a != "C":
                final.append((own[i], a, 1, None))
            elif i in routing.received:
                K_next[i] = _clip01(K0[i] + p.chi_C * p.alpha * E0[i] * (1.0 - K0[i]))
                final.append((routing.received[i][0], "copied", 0, True))
            else:  # failed copy: attempt at the deadline with pre-homework K, no learning
                fallback = Packet(f"h{h}-s{i}", i, 0, _answers(U_item[:, i], K0[i]))
                final.append((fallback, "fallback", 1, False))
        grade = np.array([sum(packet.items) / p.M_H for packet, _, _, _ in final])
        cost = np.array([c for _, _, c, _ in final], dtype=int)

        # 6. confidence, 7. reward, 8. Q (chosen action only), 9. peer exposure
        C_next = np.clip(C0 + p.eta_C * (grade - C0), 0.0, 1.0)
        reward = grade - p.kappa * cost
        Q_next = Q0.copy()
        for i, a in enumerate(actions):
            k = ACTIONS.index(a)
            Q_next[i, k] = Q0[i, k] + p.eta_Q * (reward[i] - Q0[i, k])
        if p.exposure == "copying":  # V2 (A19): share of neighbours who chose C this homework
            chose_c = [a == "C" for a in actions]
            X_next = np.array([sum(chose_c[j] for j in nbrs[i]) / degree[i] if degree[i] > 0 else 0.0
                               for i in range(N)])
        else:  # V1 (§7, §23): share of neighbours who asked me
            X_next = np.array([len(routing.incoming.get(i, ())) / degree[i] if degree[i] > 0 else 0.0
                               for i in range(N)])

        # 10. commit
        K, C, Q, X = K_next, C_next, Q_next, X_next

        seq += 1
        event_id = f"h{h}"
        _log_event(log, event_id, seq, "homework", h)
        for i, a in enumerate(actions):
            packet, mode, c, success = final[i]
            append_row(log.tables, "decisions", run_id=run_id, event_id=event_id, homework_index=h, student_id=i,
                       feasible_S=True, feasible_D=bool(feasible[i]), feasible_C=bool(feasible[i]),
                       P_S=float(P[i, 0]), P_D=float(P[i, 1]), P_C=float(P[i, 2]), action=a,
                       partner_id=partner[i], grade=float(grade[i]), reward=float(reward[i]), cost=int(c),
                       copy_success=success, answer_id=packet.answer_id, root_id=packet.root, depth=packet.depth)
            for q, correct in enumerate(packet.items):
                append_row(log.tables, "item_outcomes", run_id=run_id, event_id=event_id, student_id=i, item=q,
                           correct=correct, mode=mode, answer_id=packet.answer_id, root_id=packet.root)
        for rnd, requester, target, had in routing.requests:
            if had:
                packet, sender, got_round = routing.received[requester]
                assert sender == target and got_round == rnd
                ids = dict(answer_id=packet.answer_id, root_id=packet.root,
                           sender_depth=packet.depth - 1, receiver_depth=packet.depth)
            else:
                ids = dict(answer_id=None, root_id=None, sender_depth=None, receiver_depth=None)
            append_row(log.tables, "routing_events", run_id=run_id, homework_index=h, round=rnd,
                       requester_id=requester, target_id=target, target_had_packet=had, transfer_success=had, **ids)
        _log_snapshot(log, event_id, K, C, E, Q, X)
        if tally is not None:
            for receiver, (_, sender, _) in routing.received.items():
                tally["H"][(h, sender, receiver)] = tally["H"].get((h, sender, receiver), 0) + 1
            for i in range(N):
                tally["grades"][(h, i)] = float(grade[i])

        # exam after homework h (docs/03): probe in M0-M3, causal in M4-M5
        if p.F_E is not None and h % p.F_E == 0:
            exam_index += 1
            correct = np.asarray(draws.exam(exam_index), dtype=float) < K[None, :]  # (M_E, N)
            G_E = correct.sum(axis=0) / p.M_E
            if p.exam_updates_confidence:
                C = np.clip(C + p.eta_C * (G_E - C), 0.0, 1.0)
            if p.exam_updates_effort:
                E = 1.0 + p.eta_E * np.maximum(p.tau_E - G_E, 0.0)
            seq += 1
            exam_event = f"e{exam_index}"
            diagnostic = not (p.exam_updates_confidence or p.exam_updates_effort)
            _log_event(log, exam_event, seq, "exam", h, exam_index,
                       (diagnostic, p.exam_updates_confidence, p.exam_updates_effort))
            for i in range(N):
                for q in range(p.M_E):
                    append_row(log.tables, "item_outcomes", run_id=run_id, event_id=exam_event, student_id=i,
                               item=q, correct=bool(correct[q, i]), mode="exam", answer_id=None, root_id=None)
            _log_snapshot(log, exam_event, K, C, E, Q, X)

    log.test_tally = tally
    return log


def strategy_probabilities(Q: np.ndarray, C: np.ndarray, X: np.ndarray,
                           feasible_social: np.ndarray, p: EffectiveParams) -> np.ndarray:
    """Softmax over (S, D, C), temperature 1 (§9). Infeasible rows are exactly (1, 0, 0) (A11)."""
    Q = np.asarray(Q, dtype=float)
    U = np.empty_like(Q)
    U[:, 0] = Q[:, 0] + p.beta_C * (np.asarray(C, dtype=float) - 0.5)
    U[:, 1] = Q[:, 1]
    U[:, 2] = p.b_C + Q[:, 2] + p.beta_P * np.asarray(X, dtype=float)
    expU = np.exp(U - U.max(axis=1, keepdims=True))
    P = expU / expU.sum(axis=1, keepdims=True)
    P[~np.asarray(feasible_social, dtype=bool)] = (1.0, 0.0, 0.0)  # U^D = U^C = -inf
    return P
