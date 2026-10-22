"""E6-only structural variants around the frozen V3 engine.

This module does not modify `v3.py`. The locked E6 baseline calls `simulate_v3`; this implementation
exists only for the preregistered softmax, reward and access-utility variants.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np

from .engine import ACTIONS, Packet
from .graphs import Graph
from .records import RunLog, append_row
from .rng import DrawProvider, pick, weighted_pick
from .v3 import (
    V3Controls, V3RunSpec, _answers, _clip01, _log_event, _log_state, _log_ties, _manifest,
    expected_access, initial_traits, route_v3, seed_probabilities, social_update, update_beliefs,
)


@dataclass(frozen=True)
class E6Variant:
    choice_rule: str = "argmax"
    temperature: float | None = None
    reward_rule: str = "grade_cost"
    access_utility: bool = True

    def validate(self) -> None:
        if self.choice_rule not in {"argmax", "softmax"}:
            raise ValueError("choice_rule must be argmax or softmax")
        if self.choice_rule == "softmax":
            if self.temperature is None or not math.isfinite(self.temperature) or self.temperature <= 0:
                raise ValueError("softmax temperature must be positive and finite")
        elif self.temperature is not None:
            raise ValueError("argmax choice has no temperature")
        if self.reward_rule not in {"grade_cost", "knowledge_cost", "grade_no_cost"}:
            raise ValueError("unknown E6 reward rule")


def _utilities(Q: np.ndarray, access: np.ndarray, kappa: np.ndarray, A0: float,
               access_utility: bool) -> np.ndarray:
    U = np.asarray(Q, float).copy()
    if access_utility:
        U[:, 2] += np.asarray(kappa, float) * (np.asarray(access, float) - A0)
    return U


def _choice_probabilities(U: np.ndarray, feasible: np.ndarray, epsilon: float,
                          variant: E6Variant) -> np.ndarray:
    P = np.zeros_like(U, dtype=float)
    for i in range(len(U)):
        possible = [0, 1, 2] if feasible[i] else [0]
        if variant.choice_rule == "argmax":
            best = max(U[i, k] for k in possible)
            exploit = [k for k in possible if U[i, k] == best]
            for k in possible:
                P[i, k] = epsilon / len(possible) + ((1.0 - epsilon) / len(exploit) if k in exploit else 0.0)
        else:
            values = np.array([U[i, k] for k in possible], float)
            weights = np.exp((values - values.max()) / variant.temperature)
            soft = weights / weights.sum()
            for position, k in enumerate(possible):
                P[i, k] = epsilon / len(possible) + (1.0 - epsilon) * soft[position]
    return P


def _sample_later_actions(U: np.ndarray, feasible: np.ndarray, strategy: np.ndarray,
                          exploration: np.ndarray, epsilon: float, variant: E6Variant,
                          controls: V3Controls) -> tuple[list[str], np.ndarray, list[str]]:
    actions, modes = [], []
    explored = np.asarray(exploration, float) < epsilon
    for i in range(len(U)):
        possible = [0, 1, 2] if feasible[i] else [0]
        if controls.force_action is not None:
            action = controls.force_action if (controls.force_action == "S" or feasible[i]) else "S"
            mode = "forced"
        elif explored[i]:
            action, mode = ACTIONS[pick(possible, float(strategy[i]))], "explore"
        elif variant.choice_rule == "argmax":
            best = max(U[i, k] for k in possible)
            ties = [k for k in possible if U[i, k] == best]
            action, mode = ACTIONS[pick(ties, float(strategy[i]))], "exploit"
        else:
            values = np.array([U[i, k] for k in possible], float)
            weights = np.exp((values - values.max()) / variant.temperature)
            cumulative, target, selected = 0.0, float(strategy[i]) * float(weights.sum()), possible[-1]
            for k, weight in zip(possible, weights):
                cumulative += float(weight)
                if target < cumulative:
                    selected = k
                    break
            action, mode = ACTIONS[selected], "softmax"
        actions.append(action)
        modes.append(mode)
    return actions, explored, modes


def simulate_variant(spec: V3RunSpec, graph: Graph, draws: DrawProvider, variant: E6Variant, *,
                     controls: V3Controls = V3Controls()) -> RunLog:
    """Run one preregistered E6 structural variant with frozen V3 mechanics elsewhere."""
    variant.validate()
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

    manifest = _manifest(spec, graph, draws, controls)
    manifest["e6_variant"] = asdict(variant)
    log = RunLog(spec.run_id, manifest)
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
            for i, uniform in enumerate(U_strategy):
                if controls.force_action is not None:
                    action = controls.force_action if (controls.force_action == "S" or feasible[i]) else "S"
                elif uniform < P[i, 0]:
                    action = "S"
                elif uniform < P[i, 0] + P[i, 1]:
                    action = "D"
                else:
                    action = "C"
                actions.append(action)
                modes.append("forced" if controls.force_action else ("seed" if action == "C" else "initial_honest"))
        else:
            U = _utilities(Q0, access, traits.kappa, p.A0, variant.access_utility)
            P = _choice_probabilities(U, feasible, p.epsilon, variant)
            actions, explored, modes = _sample_later_actions(
                U, feasible, U_strategy, np.asarray(draws.exploration(h), float), p.epsilon, variant, controls)

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
        cost = np.array([value for _, _, value, _ in final], int)
        if variant.reward_rule == "knowledge_cost":
            reward = K_next - traits.kappa * cost
        elif variant.reward_rule == "grade_no_cost":
            reward = grade.copy()
        else:
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
            packet, mode, value, success = final[i]
            append_row(log.tables, "decisions", run_id=spec.run_id, event_id=event_id, homework_index=h,
                       student_id=i, feasible_S=True, feasible_D=bool(feasible[i]), feasible_C=bool(feasible[i]),
                       P_S=float(P[i, 0]), P_D=float(P[i, 1]), P_C=float(P[i, 2]), action=action,
                       partner_id=partners[i], grade=float(grade[i]), reward=float(reward[i]), cost=int(value),
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
