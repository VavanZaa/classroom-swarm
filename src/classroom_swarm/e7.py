"""Locked E7 universal-answer-AI intervention layered on frozen V3."""
from __future__ import annotations

import hashlib
import json
import math
import platform
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, replace
from itertools import product
from pathlib import Path
from typing import Mapping, Sequence

import networkx as nx
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from . import e5, e6
from .experiment import _git_state
from .graphs import Graph, generate_graph
from .records import RunLog, append_row
from .rng import BIT_GENERATOR, FAMILY_CODE, RNG_SCHEME, STREAM_CODE, Draws, graph_seed, pick, weighted_pick
from .storage import write_replicate
from .v3 import (
    V3Controls, V3Params, V3RunSpec, _answers, _clip01, _log_event, _log_state, _log_ties, _manifest,
    _utilities, expected_access, initial_traits, route_v3, seed_probabilities, simulate_v3,
    update_beliefs,
)

EXPERIMENT_ID = "E7"
STRUCTURAL_SEED = 920107
FACTORIAL_SEED = 920108
SMOKE_SEED = 920993
BOOT_SEED = 920700
BOOT_B = 10_000
AI_ACCESS_STREAM_CODE = 701
STRUCTURAL_REPLICATES = tuple(range(1, 401))
FACTORIAL_REPLICATES = tuple(range(1, 101))
SMOKE_REPLICATES = (1, 2)
PREREG = "docs/experiments/E7-preregistration.md"
LOCK = "docs/experiments/E7-lock.json"
MODEL_LOCK = "docs/V3-model-lock.json"
REPO = Path(__file__).resolve().parents[2]
E7_ACTIONS = ("S", "D", "C", "A")
FACTOR_NAMES = ("ai_cost", "confidence_penalty", "access", "choice", "persistence", "ai_learning", "eta_social")
PRIMARY = ("pA_available_late", "pC_late", "grade_late", "K_final", "C_final", "exam_final")
DELTA = {
    "pA_available_late": 0.02, "pA_late": 0.02, "pS_late": 0.02, "pD_late": 0.02,
    "pC_late": 0.02, "adopter_share": 0.02, "persistent_ai_share": 0.02,
    "grade_late": 0.05, "reward_late": 0.05, "K_final": 0.01, "C_final": 0.05,
    "exam_final": 0.05, "grade_exam_gap": 0.05, "succ_late": 0.05,
    "source_top20": 0.05, "source_gini": 0.05, "source_resid_persist_strict": 0.10,
    "pA_prewithdraw": 0.02, "pA_postwithdraw": 0.02, "pS_postwithdraw": 0.02,
    "pD_postwithdraw": 0.02, "pC_postwithdraw": 0.02,
}
SUMMARY_OUTCOMES = tuple(DELTA)


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


@dataclass(frozen=True)
class E7Intervention:
    enabled: bool = True
    access_fraction: float = 1.0
    ai_cost: int = 0
    confidence_decrement: float = 0.02
    choice_rule: str = "argmax"
    temperature: float = 0.10
    withdraw_homework: int | None = None
    ai_learning_multiplier: float = 0.0

    def validate(self, H: int) -> None:
        _require(isinstance(self.enabled, bool), "enabled must be bool")
        _require(0.0 < self.access_fraction <= 1.0, "access_fraction must be in (0,1]")
        _require(self.ai_cost in (0, 1), "ai_cost must be 0 or 1")
        _require(0.0 <= self.confidence_decrement <= 1.0, "confidence_decrement must be in [0,1]")
        _require(self.choice_rule in {"argmax", "softmax"}, "choice_rule must be argmax or softmax")
        _require(math.isfinite(self.temperature) and self.temperature > 0, "temperature must be positive")
        _require(self.withdraw_homework is None or 2 < self.withdraw_homework <= H,
                 "withdraw_homework must be None or in [3,H]")
        _require(0.0 <= self.ai_learning_multiplier <= 1.0, "ai_learning_multiplier must be in [0,1]")


@dataclass(frozen=True)
class E7Condition:
    label: str
    params: V3Params = V3Params()
    intervention: E7Intervention = E7Intervention()


@dataclass
class E7Result:
    log: RunLog
    ai_access: list[dict]
    ai_decisions: list[dict]


def structural_conditions() -> tuple[E7Condition, ...]:
    p, base = V3Params(), E7Intervention()
    return (
        E7Condition("E7-S-control", p, replace(base, enabled=False)),
        E7Condition("E7-S-base", p, base),
        E7Condition("E7-S-conf0", p, replace(base, confidence_decrement=0.0)),
        E7Condition("E7-S-conf05", p, replace(base, confidence_decrement=0.05)),
        E7Condition("E7-S-cost1", p, replace(base, ai_cost=1)),
        E7Condition("E7-S-softmax010", p, replace(base, choice_rule="softmax", temperature=0.10)),
        E7Condition("E7-S-softmax025", p, replace(base, choice_rule="softmax", temperature=0.25)),
        E7Condition("E7-S-withdraw", p, replace(base, withdraw_homework=11)),
        E7Condition("E7-S-learning", p, replace(base, ai_learning_multiplier=1.0)),
        E7Condition("E7-S-access25", p, replace(base, access_fraction=0.25)),
        E7Condition("E7-S-social010", replace(p, eta_social=0.10), base),
        E7Condition("E7-S-H40", replace(p, H=40), base),
    )


STRUCTURAL_LABELS = tuple(c.label for c in structural_conditions())


def factorial_conditions() -> tuple[E7Condition, ...]:
    p, out = V3Params(), []
    for bits in product((0, 1), repeat=7):
        intervention = E7Intervention(
            ai_cost=bits[0], confidence_decrement=0.04 if bits[1] else 0.0,
            access_fraction=1.0 if bits[2] else 0.25,
            choice_rule="softmax" if bits[3] else "argmax", temperature=0.10,
            withdraw_homework=None if bits[4] else 11,
            ai_learning_multiplier=float(bits[5]),
        )
        params = replace(p, eta_social=0.10 if bits[6] else 0.0)
        out.append(E7Condition("E7-F-" + "".join(map(str, bits)), params, intervention))
    return tuple(out)


FACTORIAL_LABELS = tuple(c.label for c in factorial_conditions())


def bits_from_label(label: str) -> tuple[int, ...]:
    prefix = "E7-F-"
    if not label.startswith(prefix) or len(label) != len(prefix) + 7 or set(label[len(prefix):]) - {"0", "1"}:
        raise ValueError(f"invalid E7 factorial label {label!r}")
    return tuple(int(bit) for bit in label[len(prefix):])


def verify_lock(repo: Path = REPO) -> str:
    repo = Path(repo)
    lock = json.loads((repo / LOCK).read_text(encoding="utf-8"))
    digest = hashlib.sha256((repo / PREREG).read_bytes()).hexdigest()
    if digest != lock["sha256"]:
        raise RuntimeError(f"E7 preregistration SHA-256 {digest} != lock {lock['sha256']}")
    e5.verify_lock(repo)
    return digest


def ai_access_mask(N: int, fraction: float, master_seed: int, replicate: int) -> np.ndarray:
    _require(N >= 1 and 0.0 < fraction <= 1.0, "invalid access-mask inputs")
    if fraction == 1.0:
        return np.ones(N, dtype=bool)
    rng = np.random.default_rng(np.random.SeedSequence([master_seed, replicate, AI_ACCESS_STREAM_CODE]))
    uniforms = rng.random(N)
    selected = np.argsort(uniforms, kind="stable")[:math.ceil(fraction * N)]
    mask = np.zeros(N, dtype=bool)
    mask[selected] = True
    return mask


def action_probabilities_e7(utilities: np.ndarray, feasible: Sequence[Sequence[int]], epsilon: float,
                            choice_rule: str, temperature: float) -> np.ndarray:
    U = np.asarray(utilities, float)
    P = np.zeros_like(U)
    for i, possible_seq in enumerate(feasible):
        possible = tuple(possible_seq)
        for k in possible:
            P[i, k] = epsilon / len(possible)
        if choice_rule == "argmax":
            best = max(U[i, k] for k in possible)
            ties = [k for k in possible if U[i, k] == best]
            for k in ties:
                P[i, k] += (1.0 - epsilon) / len(ties)
        else:
            shifted = np.array([(U[i, k] - max(U[i, j] for j in possible)) / temperature for k in possible])
            weights = np.exp(shifted)
            weights /= weights.sum()
            for k, weight in zip(possible, weights):
                P[i, k] += (1.0 - epsilon) * float(weight)
    return P


def _sample_probabilities(possible: Sequence[int], probabilities: np.ndarray, u: float) -> int:
    cumulative = 0.0
    for k in possible:
        cumulative += float(probabilities[k])
        if u < cumulative:
            return k
    return possible[-1]


def _social_update_four(Q: np.ndarray, actions: Sequence[str], rewards: np.ndarray,
                        neighbors: Sequence[Sequence[int]], neighbor_weights: Sequence[Sequence[float]],
                        eta: float) -> np.ndarray:
    updated = np.asarray(Q, float).copy()
    if eta == 0.0:
        return updated
    for i, nb in enumerate(neighbors):
        for k, action in enumerate(E7_ACTIONS):
            observed = [(j, w) for j, w in zip(nb, neighbor_weights[i]) if actions[j] == action]
            if observed:
                total = sum(w for _, w in observed)
                target = sum(w * float(rewards[j]) for j, w in observed) / total
                updated[i, k] += eta * (target - updated[i, k])
    return updated


def _static_rows(log: RunLog, spec: V3RunSpec, graph: Graph, traits) -> None:
    for i in range(spec.params.N):
        append_row(log.tables, "graph_nodes", run_id=spec.run_id, student_id=i,
                   community_id=None if graph.community is None else graph.community[i], degree=int(graph.degree[i]))
        append_row(log.tables, "agent_traits", run_id=spec.run_id, student_id=i,
                   K0=float(traits.K0[i]), alpha=float(traits.alpha[i]), kappa=float(traits.kappa[i]))
    for (u, v), weight in zip(graph.edges, graph.weights):
        append_row(log.tables, "graph_edges", run_id=spec.run_id, u=u, v=v, weight=float(weight))


def simulate_e7(spec: V3RunSpec, graph: Graph, draws: Draws, intervention: E7Intervention,
                access_mask: np.ndarray) -> E7Result:
    """Pure E7 intervention simulation. Frozen V3 is called separately for controls."""
    p, N = spec.params, spec.params.N
    p.validate()
    intervention.validate(p.H)
    _require(intervention.enabled, "simulate_e7 requires an enabled intervention")
    _require(graph.N == N and graph.family == spec.family, "graph does not match E7 run spec")
    _require(np.asarray(access_mask).shape == (N,), "access mask must have shape N")
    traits = initial_traits(p, draws)
    nbrs, nbr_weights = graph.neighbors, graph.neighbor_weights
    social_feasible = np.array(graph.degree) > 0
    K, C, E = traits.K0.copy(), traits.K0.copy(), np.ones(N)
    Q = np.column_stack([traits.K0 - traits.kappa] * 4)
    A = np.full((N, N), np.nan)
    for u, v in graph.edges:
        A[u, v] = A[v, u] = p.A0

    manifest = _manifest(spec, graph, draws, controls=V3Controls())
    manifest.update(stage="V3-E7", model_version="V3/E7-AI", intervention=asdict(intervention),
                    ai_access_stream_code=AI_ACCESS_STREAM_CODE)
    log = RunLog(spec.run_id, manifest)
    _static_rows(log, spec, graph, traits)
    ai_access = [{"run_id": spec.run_id, "student_id": i, "accessible": bool(access_mask[i])}
                 for i in range(N)]
    ai_rows: list[dict] = []
    seq, exam_index = 0, 0
    _log_event(log, "init", seq, "init", None)
    _log_state(log, "init", K, C, E, Q[:, :3])
    _log_ties(log, "init", nbrs, A)

    for h in range(1, p.H + 1):
        K0, C0, Q0, A0_matrix = K.copy(), C.copy(), Q.copy(), A.copy()
        human_access = expected_access(nbrs, nbr_weights, A0_matrix)
        U_strategy = np.asarray(draws.strategy(h), float)
        explored = np.zeros(N, dtype=bool)
        active = h >= 2 and (intervention.withdraw_homework is None or h < intervention.withdraw_homework)
        ai_available = np.asarray(access_mask, bool) & active
        utilities = np.column_stack((_utilities(Q0[:, :3], human_access, traits.kappa, p.A0), Q0[:, 3]))
        feasible_actions = [tuple([0] + ([1, 2] if social_feasible[i] else []) + ([3] if ai_available[i] else []))
                            for i in range(N)]
        modes: list[str] = []
        if h == 1:
            P = np.column_stack((seed_probabilities(social_feasible, p.seed_fraction), np.zeros(N)))
            actions = []
            for i, u in enumerate(U_strategy):
                k = _sample_probabilities(feasible_actions[i], P[i], float(u))
                actions.append(E7_ACTIONS[k])
                modes.append("seed" if k == 2 else "initial_honest")
        else:
            P = action_probabilities_e7(utilities, feasible_actions, p.epsilon,
                                        intervention.choice_rule, intervention.temperature)
            U_explore = np.asarray(draws.exploration(h), float)
            actions = []
            for i, possible in enumerate(feasible_actions):
                explored[i] = U_explore[i] < p.epsilon
                if explored[i]:
                    k = pick(possible, float(U_strategy[i]))
                    modes.append("explore")
                elif intervention.choice_rule == "argmax":
                    best = max(utilities[i, j] for j in possible)
                    ties = [j for j in possible if utilities[i, j] == best]
                    k = pick(ties, float(U_strategy[i]))
                    modes.append("exploit")
                else:
                    exploit = action_probabilities_e7(utilities[i:i + 1], [possible], 0.0,
                                                       "softmax", intervention.temperature)[0]
                    k = _sample_probabilities(possible, exploit, float(U_strategy[i]))
                    modes.append("softmax")
                actions.append(E7_ACTIONS[k])

        U_item, U_partner = np.asarray(draws.item(h), float), np.asarray(draws.partner(h), float)
        K_next = K0.copy()
        own: dict[int, object] = {}
        partners: list[int | None] = [None] * N
        from .engine import Packet
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
        final = []
        for i, action in enumerate(actions):
            if action in {"S", "D"}:
                final.append((own[i], action, 1, None))
            elif action == "A":
                K_next[i] = _clip01(K0[i] + intervention.ai_learning_multiplier
                                    * traits.alpha[i] * (1.0 - K0[i]))
                packet = Packet(f"h{h}-ai", -1, 0, tuple([True] * p.M_H))
                final.append((packet, "ai", intervention.ai_cost, None))
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
        for i, action in enumerate(actions):
            if action == "A":
                C_next[i] = max(0.0, C0[i] - intervention.confidence_decrement)
        Q_next = Q0.copy()
        for i, action in enumerate(actions):
            k = E7_ACTIONS.index(action)
            Q_next[i, k] += p.eta_Q * (reward[i] - Q_next[i, k])
        Q_next = _social_update_four(Q_next, actions, reward, nbrs, nbr_weights, p.eta_social)
        A_next = update_beliefs(A0_matrix, routed.belief_outcomes, p.eta_A)
        K, C, Q, A = K_next, C_next, Q_next, A_next

        seq += 1
        event_id = f"h{h}"
        _log_event(log, event_id, seq, "homework", h)
        for i, action in enumerate(actions):
            packet, mode, c, success = final[i]
            append_row(log.tables, "decisions", run_id=spec.run_id, event_id=event_id, homework_index=h,
                       student_id=i, feasible_S=True, feasible_D=bool(social_feasible[i]),
                       feasible_C=bool(social_feasible[i]), P_S=float(P[i, 0]), P_D=float(P[i, 1]),
                       P_C=float(P[i, 2]), action=action, partner_id=partners[i], grade=float(grade[i]),
                       reward=float(reward[i]), cost=int(c), copy_success=success,
                       answer_id=packet.answer_id, root_id=packet.root, depth=packet.depth)
            append_row(log.tables, "v3_decisions", run_id=spec.run_id, event_id=event_id, homework_index=h,
                       student_id=i, decision_mode=modes[i], seeded=bool(h == 1 and action == "C"),
                       explored=bool(explored[i]), expected_access=float(human_access[i]))
            ai_rows.append({
                "run_id": spec.run_id, "homework_index": h, "student_id": i,
                "accessible": bool(access_mask[i]), "available": bool(ai_available[i]),
                "feasible_A": bool(ai_available[i]), "P_A": float(P[i, 3]),
                "Q_A_before": float(Q0[i, 3]), "Q_A_after": float(Q[i, 3]),
                "confidence_before": float(C0[i]), "confidence_after": float(C[i]),
                "ai_cost": intervention.ai_cost,
                "ai_learning_multiplier": intervention.ai_learning_multiplier,
                "confidence_decrement": intervention.confidence_decrement,
            })
            for q, correct in enumerate(packet.items):
                append_row(log.tables, "item_outcomes", run_id=spec.run_id, event_id=event_id,
                           student_id=i, item=q, correct=correct, mode=mode,
                           answer_id=packet.answer_id, root_id=packet.root)
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
        _log_state(log, event_id, K, C, E, Q[:, :3])
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
            _log_state(log, exam_event, K, C, E, Q[:, :3])
            _log_ties(log, exam_event, nbrs, A)
    return E7Result(log, ai_access, ai_rows)


def _control_sidecars(log: RunLog) -> tuple[list[dict], list[dict]]:
    traits = {r["student_id"]: r for r in zip_rows(log.tables["agent_traits"])}
    states = {(r["event_id"], r["student_id"]): r for r in zip_rows(log.tables["state_snapshots"])}
    access = [{"run_id": log.run_id, "student_id": i, "accessible": False} for i in sorted(traits)]
    rows = []
    for d in zip_rows(log.tables["decisions"]):
        h, i = d["homework_index"], d["student_id"]
        before_event = "init" if h == 1 else f"h{h - 1}"
        q0 = traits[i]["K0"] - traits[i]["kappa"]
        rows.append({"run_id": log.run_id, "homework_index": h, "student_id": i,
                     "accessible": False, "available": False, "feasible_A": False, "P_A": 0.0,
                     "Q_A_before": q0, "Q_A_after": q0,
                     "confidence_before": states[(before_event, i)]["C"],
                     "confidence_after": states[(f"h{h}", i)]["C"], "ai_cost": 0,
                     "ai_learning_multiplier": 0.0, "confidence_decrement": 0.0})
    return access, rows


def zip_rows(columns: Mapping[str, Sequence]) -> list[dict]:
    names = tuple(columns)
    return [dict(zip(names, values)) for values in zip(*(columns[name] for name in names))]


AI_ACCESS_SCHEMA = pa.schema([("run_id", pa.string()), ("student_id", pa.int64()), ("accessible", pa.bool_())])
AI_DECISION_SCHEMA = pa.schema([
    ("run_id", pa.string()), ("homework_index", pa.int64()), ("student_id", pa.int64()),
    ("accessible", pa.bool_()), ("available", pa.bool_()), ("feasible_A", pa.bool_()),
    ("P_A", pa.float64()), ("Q_A_before", pa.float64()), ("Q_A_after", pa.float64()),
    ("confidence_before", pa.float64()), ("confidence_after", pa.float64()), ("ai_cost", pa.int64()),
    ("ai_learning_multiplier", pa.float64()), ("confidence_decrement", pa.float64()),
])


def write_e7_replicate(rep_dir: Path, results: Sequence[E7Result], shared_manifest: dict) -> Path:
    rep_dir = Path(rep_dir)
    write_replicate(rep_dir, [r.log for r in results], shared_manifest)
    for name, schema, rows in (
        ("ai_access", AI_ACCESS_SCHEMA, [row for result in results for row in result.ai_access]),
        ("ai_decisions", AI_DECISION_SCHEMA, [row for result in results for row in result.ai_decisions]),
    ):
        pq.write_table(pa.Table.from_pylist(rows, schema=schema), rep_dir / f"{name}.parquet")
    return rep_dir


def read_ai_table(rep_dir: Path, name: str) -> pa.Table:
    schemas = {"ai_access": AI_ACCESS_SCHEMA, "ai_decisions": AI_DECISION_SCHEMA}
    if name not in schemas:
        raise ValueError(f"unknown E7 sidecar {name!r}")
    return pq.read_table(Path(rep_dir) / f"{name}.parquet", schema=schemas[name])


def _shared(block: str, replicate: int, master_seed: int, plan: Sequence[E7Condition]) -> dict:
    return {
        "experiment_id": EXPERIMENT_ID, "block": block, "model_version": "V3/E7-AI",
        "replicate": replicate, "master_seed": master_seed, "rng_scheme": RNG_SCHEME,
        "bit_generator": BIT_GENERATOR, "stream_codes": dict(STREAM_CODE), "family_codes": dict(FAMILY_CODE),
        "R_max": 3, "ai_access_stream_code": AI_ACCESS_STREAM_CODE,
        "preregistration_sha256": hashlib.sha256((REPO / PREREG).read_bytes()).hexdigest(),
        "v3_model_commit": json.loads((REPO / MODEL_LOCK).read_text(encoding="utf-8"))["git_commit"],
        "conditions": [{"label": c.label, "params": asdict(c.params),
                        "intervention": asdict(c.intervention)} for c in plan],
        "versions": {"python": platform.python_version(), "numpy": np.__version__,
                     "networkx": nx.__version__, "pyarrow": pa.__version__}, **_git_state(),
    }


def _simulate_plan(plan: Sequence[E7Condition], replicate: int, master_seed: int) -> list[E7Result]:
    graphs: dict[tuple, Graph] = {}
    draws: dict[tuple[int, int, int], Draws] = {}
    results = []
    for condition in plan:
        p = condition.params
        p.validate()
        condition.intervention.validate(p.H)
        graph_key = (p.N, p.d_bar, p.omega, p.sbm_ratio)
        if graph_key not in graphs:
            graphs[graph_key] = generate_graph("SBM", p, graph_seed(master_seed, replicate, "SBM"))
        draw_key = (p.N, p.M_H, p.M_E)
        if draw_key not in draws:
            draws[draw_key] = Draws(master_seed, replicate, p.N, p.M_H, p.M_E, R_max=3)
        graph, source = graphs[graph_key], draws[draw_key]
        spec = V3RunSpec(condition.label, replicate, "SBM", 3, p, master_seed)
        if condition.intervention.enabled:
            mask = ai_access_mask(p.N, condition.intervention.access_fraction, master_seed, replicate)
            results.append(simulate_e7(spec, graph, source, condition.intervention, mask))
        else:
            log = simulate_v3(spec, graph, source)
            access, ai_rows = _control_sidecars(log)
            results.append(E7Result(log, access, ai_rows))
    return results


def run_structural_replicate(replicate: int, master_seed: int, out_root: Path,
                             plan: Sequence[E7Condition] | None = None) -> Path:
    plan = tuple(structural_conditions() if plan is None else plan)
    return write_e7_replicate(Path(out_root) / f"rep{replicate:04d}",
                              _simulate_plan(plan, replicate, master_seed),
                              _shared("structural", replicate, master_seed, plan))


def run_factorial_replicate(replicate: int, master_seed: int, out_root: Path,
                            shard_size: int = 16, *, resume: bool = False) -> list[Path]:
    plan = factorial_conditions()
    _require(shard_size >= 1 and 128 % shard_size == 0, "shard_size must divide 128")
    paths = []
    for start in range(0, len(plan), shard_size):
        shard = plan[start:start + shard_size]
        shard_dir = Path(out_root) / f"rep{replicate:04d}" / f"shard{start // shard_size:02d}"
        if shard_dir.exists():
            if not resume:
                raise FileExistsError(f"refusing to overwrite existing factorial shard {shard_dir}")
            paths.append(shard_dir)
            continue
        write_e7_replicate(shard_dir, _simulate_plan(shard, replicate, master_seed),
                           _shared("factorial", replicate, master_seed, shard))
        paths.append(shard_dir)
    return paths


def _mean(values) -> float | None:
    finite = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return sum(finite) / len(finite) if finite else None


def _gini(values: Sequence[float]) -> float | None:
    x = np.asarray(values, float)
    if x.sum() == 0:
        return None
    return float(np.abs(x[:, None] - x[None, :]).sum() / (2 * len(x) * x.sum()))


def run_summaries(tables: Mapping[str, pa.Table], ai_decisions: pa.Table) -> list[dict]:
    decisions: dict[str, list[dict]] = defaultdict(list)
    for row in tables["decisions"].to_pylist():
        decisions[row["run_id"]].append(row)
    states: dict[str, list[dict]] = defaultdict(list)
    for row in tables["state_snapshots"].to_pylist():
        states[row["run_id"]].append(row)
    events = {(r["run_id"], r["event_id"]): r for r in tables["events"].to_pylist()}
    exam_scores: dict[tuple[str, str], list[bool]] = defaultdict(list)
    for row in tables["item_outcomes"].to_pylist():
        if row["mode"] == "exam":
            exam_scores[(row["run_id"], row["event_id"])].append(row["correct"])
    ai_rows: dict[str, list[dict]] = defaultdict(list)
    for row in ai_decisions.to_pylist():
        ai_rows[row["run_id"]].append(row)
    nodes: dict[str, int] = Counter(r["run_id"] for r in tables["graph_nodes"].to_pylist())
    out = []
    for run_id in sorted(decisions):
        drows, N = decisions[run_id], nodes[run_id]
        H = max(r["homework_index"] for r in drows)
        late = [r for r in drows if H - 4 <= r["homework_index"] <= H]
        by_student_ai = Counter(r["student_id"] for r in drows if r["action"] == "A")
        first_ai = {}
        for row in drows:
            if row["action"] == "A":
                first_ai.setdefault(row["student_id"], row["homework_index"])
        available_h = sorted({r["homework_index"] for r in ai_rows[run_id] if r["available"]})
        last_available = set(available_h[-5:])
        available_window = [r for r in drows if r["homework_index"] in last_available]
        persistent = sum(sum(r["action"] == "A" for r in available_window if r["student_id"] == i) >= 3
                         for i in range(N)) / N
        final_state = [r for r in states[run_id] if r["event_id"] == f"h{H}"]
        exam_events = sorted((e for (rid, _), e in events.items() if rid == run_id and e["event_type"] == "exam"),
                             key=lambda e: e["exam_index"])
        exam_final = (_mean(exam_scores[(run_id, exam_events[-1]["event_id"])]) if exam_events else None)
        late_copies = [r for r in late if r["action"] == "C"]
        successful = [r for r in late_copies if r["copy_success"]]
        root_counts = Counter(r["root_id"] for r in successful)
        counts = np.array([root_counts[i] for i in range(N)], float)
        top_k = math.ceil(0.2 * N)
        strict, _, _ = e6._strict_details(tables, run_id)

        def share(rows: Sequence[Mapping], action: str) -> float | None:
            return sum(r["action"] == action for r in rows) / len(rows) if rows else None

        pre = [r for r in drows if 6 <= r["homework_index"] <= 10]
        post = [r for r in drows if 11 <= r["homework_index"] <= 15]
        identity = run_id.split("/")
        grade_late = _mean(r["grade"] for r in late)
        out.append({
            "run_id": run_id, "experiment_id": identity[0], "replicate": int(identity[1][3:]),
            "family": identity[2], "R": int(identity[3][1:]), "stage": identity[4], "N": N, "H": H,
            "pA_available_late": share(available_window, "A"), "pA_late": share(late, "A"),
            "pS_late": share(late, "S"), "pD_late": share(late, "D"), "pC_late": share(late, "C"),
            "adopter_share": len(by_student_ai) / N, "persistent_ai_share": persistent,
            "first_ai_mean": _mean(first_ai.values()), "grade_late": grade_late,
            "reward_late": _mean(r["reward"] for r in late), "K_final": _mean(r["K"] for r in final_state),
            "C_final": _mean(r["C"] for r in final_state), "exam_final": exam_final,
            "grade_exam_gap": None if grade_late is None or exam_final is None else grade_late - exam_final,
            "succ_late": (len(successful) / len(late_copies) if late_copies else None),
            "source_top20": (sum(sorted(counts, reverse=True)[:top_k]) / counts.sum() if counts.sum() else None),
            "source_gini": _gini(counts), "source_resid_persist_strict": strict,
            "pA_prewithdraw": share(pre, "A"), "pA_postwithdraw": share(post, "A"),
            "pS_postwithdraw": share(post, "S"), "pD_postwithdraw": share(post, "D"),
            "pC_postwithdraw": share(post, "C"),
        })
    return out


def factorial_effects(summaries: Sequence[Mapping], outcome: str, order: Sequence[int]) -> list[float]:
    by_rep: dict[int, list[Mapping]] = defaultdict(list)
    for row in summaries:
        by_rep[row["replicate"]].append(row)
    effects = []
    for replicate in sorted(by_rep):
        positive, negative = [], []
        for row in by_rep[replicate]:
            sign = math.prod(1 if bits_from_label(row["experiment_id"])[index] else -1 for index in order)
            value = row.get(outcome)
            if value is not None:
                (positive if sign > 0 else negative).append(float(value))
        effects.append(float(np.mean(positive) - np.mean(negative)) if positive and negative else float("nan"))
    return effects
