"""Locked E8 universal-access AI policy comparison layered on frozen V3."""
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

from . import e5, e6, e7
from .experiment import _git_state
from .graphs import Graph, generate_graph
from .records import RunLog, append_row
from .rng import BIT_GENERATOR, FAMILY_CODE, RNG_SCHEME, STREAM_CODE, Draws, graph_seed, null_seed, pick, weighted_pick
from .storage import write_replicate
from .v3 import (
    V3Controls, V3Params, V3RunSpec, _answers, _clip01, _log_event, _log_state, _log_ties, _manifest,
    _utilities, expected_access, initial_traits, route_v3, seed_probabilities, simulate_v3, update_beliefs,
)

EXPERIMENT_ID = "E8"
PRIMARY_SEED = 930107
SURFACE_SEED = 930108
ROBUSTNESS_SEED = 930109
SMOKE_SEED = 930993
BOOT_SEED = 930700
BOOT_B = 10_000
PRIMARY_REPLICATES = tuple(range(1, 401))
SURFACE_REPLICATES = tuple(range(1, 201))
ROBUSTNESS_REPLICATES = tuple(range(1, 101))
SMOKE_REPLICATES = (1, 2)
PREREG = "docs/experiments/E8-preregistration.md"
LOCK = "docs/experiments/E8-lock.json"
MODEL_LOCK = "docs/V3-model-lock.json"
REPO = Path(__file__).resolve().parents[2]
E8_ACTIONS = ("S", "D", "C", "A")

DELTA = {
    "pA_early": 0.02, "pA_late": 0.02, "pS_early": 0.02, "pD_early": 0.02,
    "pC_early": 0.02, "pS_late": 0.02, "pD_late": 0.02, "pC_late": 0.02,
    "adopter_share": 0.02, "persistent_ai_share": 0.02, "abandonment_share": 0.02,
    "grade_late": 0.05, "reward_late": 0.05, "K_final": 0.01, "C_final": 0.05,
    "exam_final": 0.05, "grade_exam_gap": 0.05, "ai_learning_mean": 0.01,
    "ai_reward_mean": 0.05, "succ_late": 0.05, "source_top20": 0.05,
    "source_gini": 0.05, "source_resid_persist_strict": 0.10,
    "adoption_assortativity": 0.05, "community_adoption_gap": 0.05,
    "neighbor_lag": 0.05, "K_inequality": 0.01, "exam_inequality": 0.05,
}
SUMMARY_OUTCOMES = tuple(DELTA)
PRIMARY_OUTCOMES = (
    "pA_late", "pS_late", "pD_late", "pC_late", "grade_late", "K_final",
    "exam_final", "grade_exam_gap",
)


def _require(ok: bool, message: str) -> None:
    if not ok:
        raise ValueError(message)


@dataclass(frozen=True)
class E8Policy:
    enabled: bool = True
    kind: str = "controlled"
    universal_access: bool = True
    choice_rule: str = "argmax"
    temperature: float = 0.10
    unrestricted_accuracy: float = 1.0
    unrestricted_learning: float = 0.10
    tutor_learning: float = 1.0
    scaffold_strength: float = 0.25
    ai_cost: int = 1

    def validate(self) -> None:
        _require(isinstance(self.enabled, bool), "enabled must be bool")
        _require(self.kind in {"none", "unrestricted", "controlled"}, "invalid E8 policy kind")
        _require(self.enabled == (self.kind != "none"), "enabled must agree with policy kind")
        _require(self.universal_access is True, "E8 AI access must be universal")
        _require(self.choice_rule in {"argmax", "softmax"}, "invalid choice rule")
        _require(math.isfinite(self.temperature) and self.temperature > 0, "temperature must be positive")
        _require(0 <= self.unrestricted_accuracy <= 1, "unrestricted accuracy must be in [0,1]")
        _require(0 <= self.unrestricted_learning <= 1.5, "unrestricted learning must be in [0,1.5]")
        _require(0 <= self.tutor_learning <= 1.5, "tutor learning must be in [0,1.5]")
        _require(0 <= self.scaffold_strength <= 1, "scaffold strength must be in [0,1]")
        _require(self.ai_cost in {0, 1, 2}, "AI cost must be 0, 1 or 2")


@dataclass(frozen=True)
class E8Condition:
    label: str
    params: V3Params = V3Params()
    family: str = "SBM"
    trait_shuffle: bool = False
    policy: E8Policy = E8Policy()


@dataclass
class E8Result:
    log: RunLog
    ai_decisions: list[dict]


def no_ai_policy(choice_rule: str = "argmax", temperature: float = 0.10) -> E8Policy:
    return E8Policy(enabled=False, kind="none", choice_rule=choice_rule, temperature=temperature, ai_cost=0)


def unrestricted_policy(**changes) -> E8Policy:
    base = E8Policy(kind="unrestricted", ai_cost=0)
    return replace(base, **changes)


def controlled_policy(**changes) -> E8Policy:
    return replace(E8Policy(kind="controlled", ai_cost=1), **changes)


def primary_conditions() -> tuple[E8Condition, ...]:
    p = V3Params()
    return (
        E8Condition("E8-A-none", p, "SBM", False, no_ai_policy()),
        E8Condition("E8-A-unrestricted", p, "SBM", False, unrestricted_policy()),
        E8Condition("E8-A-controlled", p, "SBM", False, controlled_policy()),
    )


PRIMARY_LABELS = tuple(c.label for c in primary_conditions())


def _pct(value: float) -> str:
    return f"{round(100 * value):03d}"


def surface_conditions() -> tuple[E8Condition, ...]:
    p, out = V3Params(), [E8Condition("E8-B-none", V3Params(), "SBM", False, no_ai_policy())]
    for accuracy, learning, cost in product((0.80, 0.90, 1.00), (0.0, 0.10, 0.50), (0, 1)):
        label = f"E8-B-U-r{_pct(accuracy)}-m{_pct(learning)}-c{cost}"
        out.append(E8Condition(label, p, "SBM", False,
                               unrestricted_policy(unrestricted_accuracy=accuracy,
                                                   unrestricted_learning=learning, ai_cost=cost)))
    for learning, scaffold, cost in product((0.50, 1.00, 1.50), (0.0, 0.25, 0.50), (1, 2)):
        label = f"E8-B-T-m{_pct(learning)}-s{_pct(scaffold)}-c{cost}"
        out.append(E8Condition(label, p, "SBM", False,
                               controlled_policy(tutor_learning=learning,
                                                 scaffold_strength=scaffold, ai_cost=cost)))
    return tuple(out)


SURFACE_LABELS = tuple(c.label for c in surface_conditions())


def robustness_conditions() -> tuple[E8Condition, ...]:
    out = []
    for regime, social, choice, shuffle, er, h40 in product("NUT", (0, 1), (0, 1, 2), (0, 1), (0, 1), (0, 1)):
        choice_rule = "argmax" if choice == 0 else "softmax"
        temperature = 0.10 if choice in (0, 1) else 0.25
        if regime == "N":
            policy = no_ai_policy(choice_rule, temperature)
        elif regime == "U":
            policy = unrestricted_policy(choice_rule=choice_rule, temperature=temperature)
        else:
            policy = controlled_policy(choice_rule=choice_rule, temperature=temperature)
        p = replace(V3Params(), eta_social=0.10 if social else 0.0, H=40 if h40 else 20)
        digits = f"{social}{choice}{shuffle}{er}{h40}"
        out.append(E8Condition(f"E8-C-{regime}-{digits}", p, "ER" if er else "SBM",
                               bool(shuffle), policy))
    return tuple(out)


ROBUSTNESS_LABELS = tuple(c.label for c in robustness_conditions())


def parse_robustness_label(label: str) -> tuple[str, int, int, int, int, int]:
    parts = label.split("-")
    if len(parts) != 4 or parts[:2] != ["E8", "C"] or parts[2] not in "NUT":
        raise ValueError(f"invalid E8 robustness label {label!r}")
    digits = parts[3]
    if len(digits) != 5 or digits[0] not in "01" or digits[1] not in "012" or any(x not in "01" for x in digits[2:]):
        raise ValueError(f"invalid E8 robustness label {label!r}")
    return (parts[2], *(int(x) for x in digits))


def verify_lock(repo: Path = REPO) -> str:
    repo = Path(repo)
    lock = json.loads((repo / LOCK).read_text(encoding="utf-8"))
    digest = hashlib.sha256((repo / PREREG).read_bytes()).hexdigest()
    if digest != lock["sha256"]:
        raise RuntimeError(f"E8 preregistration SHA-256 {digest} != lock {lock['sha256']}")
    e5.verify_lock(repo)
    return digest


def action_probabilities_e8(utilities: np.ndarray, feasible: Sequence[Sequence[int]], epsilon: float,
                            choice_rule: str, temperature: float) -> np.ndarray:
    return e7.action_probabilities_e7(utilities, feasible, epsilon, choice_rule, temperature)


def _sample_probabilities(possible: Sequence[int], probabilities: np.ndarray, u: float) -> int:
    cumulative = 0.0
    for k in possible:
        cumulative += float(probabilities[k])
        if u < cumulative:
            return k
    return possible[-1]


def _static_rows(log: RunLog, spec: V3RunSpec, graph: Graph, traits) -> None:
    for i in range(spec.params.N):
        append_row(log.tables, "graph_nodes", run_id=spec.run_id, student_id=i,
                   community_id=None if graph.community is None else graph.community[i], degree=int(graph.degree[i]))
        append_row(log.tables, "agent_traits", run_id=spec.run_id, student_id=i,
                   K0=float(traits.K0[i]), alpha=float(traits.alpha[i]), kappa=float(traits.kappa[i]))
    for (u, v), weight in zip(graph.edges, graph.weights):
        append_row(log.tables, "graph_edges", run_id=spec.run_id, u=u, v=v, weight=float(weight))


def simulate_e8(spec: V3RunSpec, graph: Graph, draws: Draws, policy: E8Policy,
                controls: V3Controls = V3Controls()) -> E8Result:
    """Pure E8 simulation; exact argmax no-AI controls are dispatched to frozen V3 elsewhere."""
    p, N = spec.params, spec.params.N
    p.validate()
    policy.validate()
    _require(graph.N == N and graph.family == spec.family, "graph does not match E8 run spec")
    traits = initial_traits(p, draws, controls)
    nbrs, nbr_weights = graph.neighbors, graph.neighbor_weights
    social_feasible = np.asarray(graph.degree) > 0
    K, C, E = traits.K0.copy(), traits.K0.copy(), np.ones(N)
    Q = np.column_stack([traits.K0 - traits.kappa] * 4)
    A = np.full((N, N), np.nan)
    for u, v in graph.edges:
        A[u, v] = A[v, u] = p.A0

    manifest = _manifest(spec, graph, draws, controls)
    manifest.update(stage="V3-E8", model_version="V3/E8-AI-policy", policy=asdict(policy))
    log = RunLog(spec.run_id, manifest)
    _static_rows(log, spec, graph, traits)
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
        ai_available = np.full(N, policy.enabled and h >= 2, dtype=bool)
        utilities = np.column_stack((_utilities(Q0[:, :3], human_access, traits.kappa, p.A0), Q0[:, 3]))
        feasible_actions = [tuple([0] + ([1, 2] if social_feasible[i] else []) + ([3] if ai_available[i] else []))
                            for i in range(N)]
        modes: list[str] = []
        if h == 1:
            P = np.column_stack((seed_probabilities(social_feasible, p.seed_fraction), np.zeros(N)))
            actions = []
            for i, u in enumerate(U_strategy):
                k = _sample_probabilities(feasible_actions[i], P[i], float(u))
                actions.append(E8_ACTIONS[k])
                modes.append("seed" if k == 2 else "initial_honest")
        else:
            P = action_probabilities_e8(utilities, feasible_actions, p.epsilon,
                                        policy.choice_rule, policy.temperature)
            U_explore = np.asarray(draws.exploration(h), float)
            actions = []
            for i, possible in enumerate(feasible_actions):
                explored[i] = U_explore[i] < p.epsilon
                if explored[i]:
                    k = pick(possible, float(U_strategy[i]))
                    modes.append("explore")
                elif policy.choice_rule == "argmax":
                    best = max(utilities[i, j] for j in possible)
                    tied = [j for j in possible if utilities[i, j] == best]
                    k = pick(tied, float(U_strategy[i]))
                    modes.append("exploit")
                else:
                    exploit = action_probabilities_e8(utilities[i:i + 1], [possible], 0.0,
                                                       "softmax", policy.temperature)[0]
                    k = _sample_probabilities(possible, exploit, float(U_strategy[i]))
                    modes.append("softmax")
                actions.append(E8_ACTIONS[k])

        U_item, U_partner = np.asarray(draws.item(h), float), np.asarray(draws.partner(h), float)
        K_next = K0.copy()
        own = {}
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
        ai_probability = np.full(N, np.nan)
        learning_increment = np.zeros(N)
        for i, action in enumerate(actions):
            if action in {"S", "D"}:
                final.append((own[i], action, 1, None))
            elif action == "A":
                multiplier = (policy.unrestricted_learning if policy.kind == "unrestricted"
                              else policy.tutor_learning)
                K_next[i] = _clip01(K0[i] + multiplier * traits.alpha[i] * (1.0 - K0[i]))
                learning_increment[i] = K_next[i] - K0[i]
                if policy.kind == "unrestricted":
                    probability = policy.unrestricted_accuracy
                    mode = "ai_unrestricted"
                else:
                    probability = K_next[i] + policy.scaffold_strength * (1.0 - K_next[i])
                    mode = "ai_controlled"
                ai_probability[i] = probability
                packet = Packet(f"h{h}-ai", -1, 0, _answers(U_item[:, i], probability))
                final.append((packet, mode, policy.ai_cost, None))
            elif i in routed.received:
                K_next[i] = _clip01(K0[i] + p.chi_C * traits.alpha[i] * (1.0 - K0[i]))
                final.append((routed.received[i][0], "copied", p.copy_success_cost, True))
            else:
                packet = Packet(f"h{h}-s{i}", i, 0, _answers(U_item[:, i], K0[i]))
                final.append((packet, "fallback", 1, False))

        grade = np.asarray([sum(packet.items) / p.M_H for packet, _, _, _ in final])
        cost = np.asarray([c for _, _, c, _ in final], int)
        reward = grade - traits.kappa * cost
        C_next = np.clip(C0 + p.eta_C * (grade - C0), 0.0, 1.0)
        Q_next = Q0.copy()
        for i, action in enumerate(actions):
            k = E8_ACTIONS.index(action)
            Q_next[i, k] += p.eta_Q * (reward[i] - Q_next[i, k])
        Q_next = e7._social_update_four(Q_next, actions, reward, nbrs, nbr_weights, p.eta_social)
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
                "policy_kind": policy.kind, "accessible": bool(policy.enabled),
                "available": bool(ai_available[i]), "feasible_A": bool(ai_available[i]),
                "used_A": action == "A", "P_A": float(P[i, 3]),
                "Q_A_before": float(Q0[i, 3]), "Q_A_after": float(Q[i, 3]),
                "K_before": float(K0[i]), "K_after": float(K[i]),
                "confidence_before": float(C0[i]), "confidence_after": float(C[i]),
                "correct_probability": None if math.isnan(ai_probability[i]) else float(ai_probability[i]),
                "learning_increment": float(learning_increment[i]), "ai_cost": policy.ai_cost,
                "unrestricted_accuracy": policy.unrestricted_accuracy,
                "unrestricted_learning": policy.unrestricted_learning,
                "tutor_learning": policy.tutor_learning, "scaffold_strength": policy.scaffold_strength,
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
    return E8Result(log, ai_rows)


def zip_rows(columns: Mapping[str, Sequence]) -> list[dict]:
    names = tuple(columns)
    return [dict(zip(names, values)) for values in zip(*(columns[name] for name in names))]


def _control_sidecar(log: RunLog) -> list[dict]:
    traits = {r["student_id"]: r for r in zip_rows(log.tables["agent_traits"])}
    states = {(r["event_id"], r["student_id"]): r for r in zip_rows(log.tables["state_snapshots"])}
    rows = []
    for d in zip_rows(log.tables["decisions"]):
        h, i = d["homework_index"], d["student_id"]
        before = states[("init" if h == 1 else f"h{h - 1}", i)]
        after = states[(f"h{h}", i)]
        q0 = traits[i]["K0"] - traits[i]["kappa"]
        rows.append({
            "run_id": log.run_id, "homework_index": h, "student_id": i, "policy_kind": "none",
            "accessible": False, "available": False, "feasible_A": False, "used_A": False,
            "P_A": 0.0, "Q_A_before": q0, "Q_A_after": q0,
            "K_before": before["K"], "K_after": after["K"],
            "confidence_before": before["C"], "confidence_after": after["C"],
            "correct_probability": None, "learning_increment": 0.0, "ai_cost": 0,
            "unrestricted_accuracy": 0.0, "unrestricted_learning": 0.0,
            "tutor_learning": 0.0, "scaffold_strength": 0.0,
        })
    return rows


AI_DECISION_SCHEMA = pa.schema([
    ("run_id", pa.string()), ("homework_index", pa.int64()), ("student_id", pa.int64()),
    ("policy_kind", pa.string()), ("accessible", pa.bool_()), ("available", pa.bool_()),
    ("feasible_A", pa.bool_()), ("used_A", pa.bool_()), ("P_A", pa.float64()),
    ("Q_A_before", pa.float64()), ("Q_A_after", pa.float64()), ("K_before", pa.float64()),
    ("K_after", pa.float64()), ("confidence_before", pa.float64()), ("confidence_after", pa.float64()),
    ("correct_probability", pa.float64()), ("learning_increment", pa.float64()), ("ai_cost", pa.int64()),
    ("unrestricted_accuracy", pa.float64()), ("unrestricted_learning", pa.float64()),
    ("tutor_learning", pa.float64()), ("scaffold_strength", pa.float64()),
])


def write_e8_replicate(rep_dir: Path, results: Sequence[E8Result], shared_manifest: dict) -> Path:
    rep_dir = Path(rep_dir)
    write_replicate(rep_dir, [r.log for r in results], shared_manifest)
    rows = [row for result in results for row in result.ai_decisions]
    pq.write_table(pa.Table.from_pylist(rows, schema=AI_DECISION_SCHEMA), rep_dir / "ai_decisions.parquet")
    return rep_dir


def read_ai_table(rep_dir: Path) -> pa.Table:
    return pq.read_table(Path(rep_dir) / "ai_decisions.parquet", schema=AI_DECISION_SCHEMA)


def _controls(condition: E8Condition, replicate: int, master_seed: int) -> V3Controls:
    if not condition.trait_shuffle:
        return V3Controls()
    seed = null_seed(master_seed, replicate, condition.family, 502)
    perm = tuple(int(x) for x in np.random.default_rng(seed).permutation(condition.params.N))
    return V3Controls(trait_permutation=perm)


def _shared(block: str, replicate: int, master_seed: int, plan: Sequence[E8Condition]) -> dict:
    return {
        "experiment_id": EXPERIMENT_ID, "block": block, "model_version": "V3/E8-AI-policy",
        "replicate": replicate, "master_seed": master_seed, "rng_scheme": RNG_SCHEME,
        "bit_generator": BIT_GENERATOR, "stream_codes": dict(STREAM_CODE), "family_codes": dict(FAMILY_CODE),
        "R_max": 3, "preregistration_sha256": hashlib.sha256((REPO / PREREG).read_bytes()).hexdigest(),
        "v3_model_commit": json.loads((REPO / MODEL_LOCK).read_text(encoding="utf-8"))["git_commit"],
        "conditions": [{"label": c.label, "params": asdict(c.params), "family": c.family,
                        "trait_shuffle": c.trait_shuffle, "policy": asdict(c.policy)} for c in plan],
        "versions": {"python": platform.python_version(), "numpy": np.__version__,
                     "networkx": nx.__version__, "pyarrow": pa.__version__}, **_git_state(),
    }


def _simulate_plan(plan: Sequence[E8Condition], replicate: int, master_seed: int) -> list[E8Result]:
    graphs: dict[tuple, Graph] = {}
    draws: dict[tuple[int, int, int], Draws] = {}
    results = []
    for condition in plan:
        p = condition.params
        p.validate()
        condition.policy.validate()
        graph_key = (condition.family, p.N, p.d_bar, p.omega, p.sbm_ratio)
        if graph_key not in graphs:
            graphs[graph_key] = generate_graph(condition.family, p,
                                                graph_seed(master_seed, replicate, condition.family))
        draw_key = (p.N, p.M_H, p.M_E)
        if draw_key not in draws:
            draws[draw_key] = Draws(master_seed, replicate, p.N, p.M_H, p.M_E, R_max=3)
        graph, source = graphs[graph_key], draws[draw_key]
        controls = _controls(condition, replicate, master_seed)
        spec = V3RunSpec(condition.label, replicate, condition.family, 3, p, master_seed)
        if not condition.policy.enabled and condition.policy.choice_rule == "argmax":
            log = simulate_v3(spec, graph, source, controls=controls)
            results.append(E8Result(log, _control_sidecar(log)))
        else:
            results.append(simulate_e8(spec, graph, source, condition.policy, controls))
    return results


def run_block_replicate(block: str, replicate: int, master_seed: int, out_root: Path,
                        plan: Sequence[E8Condition]) -> Path:
    plan = tuple(plan)
    _require(len({c.label for c in plan}) == len(plan), "E8 condition labels must be unique")
    return write_e8_replicate(Path(out_root) / f"rep{replicate:04d}",
                              _simulate_plan(plan, replicate, master_seed),
                              _shared(block, replicate, master_seed, plan))


def run_sharded_replicate(block: str, replicate: int, master_seed: int, out_root: Path,
                          plan: Sequence[E8Condition], shard_size: int, *, resume: bool = False) -> list[Path]:
    plan = tuple(plan)
    _require(shard_size >= 1, "shard size must be positive")
    paths = []
    for start in range(0, len(plan), shard_size):
        shard = plan[start:start + shard_size]
        shard_dir = Path(out_root) / f"rep{replicate:04d}" / f"shard{start // shard_size:02d}"
        if shard_dir.exists():
            if not resume:
                raise FileExistsError(f"refusing to overwrite E8 shard {shard_dir}")
            paths.append(shard_dir)
            continue
        write_e8_replicate(shard_dir, _simulate_plan(shard, replicate, master_seed),
                           _shared(block, replicate, master_seed, shard))
        paths.append(shard_dir)
    return paths


def _mean(values) -> float | None:
    finite = [float(v) for v in values if v is not None and math.isfinite(float(v))]
    return sum(finite) / len(finite) if finite else None


def _share(rows: Sequence[Mapping], action: str) -> float | None:
    return sum(r["action"] == action for r in rows) / len(rows) if rows else None


def _gini(values: Sequence[float]) -> float | None:
    x = np.asarray(values, float)
    if x.sum() == 0:
        return None
    return float(np.abs(x[:, None] - x[None, :]).sum() / (2 * len(x) * x.sum()))


def _binary_edge_assortativity(edges: Sequence[tuple[int, int]], adopted: set[int]) -> float | None:
    if not edges:
        return None
    x = np.asarray([int(u in adopted) for u, v in edges] + [int(v in adopted) for u, v in edges], float)
    y = np.asarray([int(v in adopted) for u, v in edges] + [int(u in adopted) for u, v in edges], float)
    if x.std() == 0 or y.std() == 0:
        return None
    return float(np.corrcoef(x, y)[0, 1])


def run_outputs(tables: Mapping[str, pa.Table], ai_decisions: pa.Table) -> tuple[list[dict], list[dict]]:
    decisions: dict[str, list[dict]] = defaultdict(list)
    states: dict[str, list[dict]] = defaultdict(list)
    ai_rows: dict[str, list[dict]] = defaultdict(list)
    for row in tables["decisions"].to_pylist(): decisions[row["run_id"]].append(row)
    for row in tables["state_snapshots"].to_pylist(): states[row["run_id"]].append(row)
    for row in ai_decisions.to_pylist(): ai_rows[row["run_id"]].append(row)
    events = {(r["run_id"], r["event_id"]): r for r in tables["events"].to_pylist()}
    exams: dict[tuple[str, str, int], list[bool]] = defaultdict(list)
    for row in tables["item_outcomes"].to_pylist():
        if row["mode"] == "exam": exams[(row["run_id"], row["event_id"], row["student_id"])].append(row["correct"])
    traits: dict[str, dict[int, dict]] = defaultdict(dict)
    for row in tables["agent_traits"].to_pylist(): traits[row["run_id"]][row["student_id"]] = row
    nodes: dict[str, dict[int, dict]] = defaultdict(dict)
    for row in tables["graph_nodes"].to_pylist(): nodes[row["run_id"]][row["student_id"]] = row
    edges: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for row in tables["graph_edges"].to_pylist(): edges[row["run_id"]].append((row["u"], row["v"]))

    summaries, trajectories = [], []
    for run_id in sorted(decisions):
        drows, N = decisions[run_id], len(nodes[run_id])
        H = max(r["homework_index"] for r in drows)
        early = [r for r in drows if 2 <= r["homework_index"] <= min(6, H)]
        late = [r for r in drows if H - 4 <= r["homework_index"] <= H]
        adopted = {r["student_id"] for r in drows if r["action"] == "A"}
        late_adopted = {r["student_id"] for r in late if r["action"] == "A"}
        persistent = sum(sum(r["action"] == "A" and r["student_id"] == i for r in late) >= 3
                         for i in range(N)) / N
        abandonment = ((len(adopted - late_adopted) / len(adopted)) if adopted else None)
        final_state = [r for r in states[run_id] if r["event_id"] == f"h{H}"]
        final_by_student = {r["student_id"]: r for r in final_state}
        exam_events = sorted((e for (rid, _), e in events.items() if rid == run_id and e["event_type"] == "exam"),
                             key=lambda e: e["exam_index"])
        final_exam_event = exam_events[-1]["event_id"] if exam_events else None
        exam_student = {i: _mean(exams[(run_id, final_exam_event, i)]) for i in range(N)} if final_exam_event else {}
        exam_final = _mean(exam_student.values())
        late_copies = [r for r in late if r["action"] == "C"]
        successful = [r for r in late_copies if r["copy_success"]]
        root_counts = Counter(r["root_id"] for r in successful)
        counts = np.asarray([root_counts[i] for i in range(N)], float)
        top_k = math.ceil(0.2 * N)
        strict, _, _ = e6._strict_details(tables, run_id)
        used_ai = [r for r in ai_rows[run_id] if r["used_A"]]

        communities = nodes[run_id]
        within, between = [], []
        if all(row["community_id"] is not None for row in communities.values()):
            for u, v in edges[run_id]:
                value = int(u in adopted and v in adopted)
                (within if communities[u]["community_id"] == communities[v]["community_id"] else between).append(value)
        community_gap = (_mean(within) - _mean(between)) if within and between else None

        by_h = {(r["homework_index"], r["student_id"]): r["action"] for r in drows}
        exposed, unexposed = [], []
        adjacency = defaultdict(list)
        for u, v in edges[run_id]: adjacency[u].append(v); adjacency[v].append(u)
        for h in range(3, H + 1):
            for i in range(N):
                prior = any(by_h.get((h - 1, j)) == "A" for j in adjacency[i])
                (exposed if prior else unexposed).append(int(by_h[(h, i)] == "A"))
        neighbor_lag = (_mean(exposed) - _mean(unexposed)) if exposed and unexposed else None

        order = sorted(range(N), key=lambda i: (traits[run_id][i]["K0"], i))
        quintiles = np.array_split(order, 5)
        bottom, top = quintiles[0].tolist(), quintiles[-1].tolist()
        K_inequality = _mean(final_by_student[i]["K"] for i in top) - _mean(final_by_student[i]["K"] for i in bottom)
        exam_inequality = (_mean(exam_student[i] for i in top) - _mean(exam_student[i] for i in bottom)
                           if exam_student else None)

        identity = run_id.split("/")
        grade_late = _mean(r["grade"] for r in late)
        first_ai = {i: min(r["homework_index"] for r in drows if r["student_id"] == i and r["action"] == "A")
                    for i in adopted}
        summaries.append({
            "run_id": run_id, "experiment_id": identity[0], "replicate": int(identity[1][3:]),
            "family": identity[2], "R": int(identity[3][1:]), "N": N, "H": H,
            **{f"p{a}_early": _share(early, a) for a in E8_ACTIONS},
            **{f"p{a}_late": _share(late, a) for a in E8_ACTIONS},
            "adopter_share": len(adopted) / N, "persistent_ai_share": persistent,
            "abandonment_share": abandonment, "first_ai_mean": _mean(first_ai.values()),
            "grade_late": grade_late, "reward_late": _mean(r["reward"] for r in late),
            "K_final": _mean(r["K"] for r in final_state), "C_final": _mean(r["C"] for r in final_state),
            "exam_final": exam_final,
            "grade_exam_gap": None if grade_late is None or exam_final is None else grade_late - exam_final,
            "ai_learning_mean": _mean(r["learning_increment"] for r in used_ai),
            "ai_reward_mean": _mean(r["reward"] for r in drows if r["action"] == "A"),
            "succ_late": len(successful) / len(late_copies) if late_copies else None,
            "source_top20": sum(sorted(counts, reverse=True)[:top_k]) / counts.sum() if counts.sum() else None,
            "source_gini": _gini(counts), "source_resid_persist_strict": strict,
            "adoption_assortativity": _binary_edge_assortativity(edges[run_id], adopted),
            "community_adoption_gap": community_gap, "neighbor_lag": neighbor_lag,
            "K_inequality": K_inequality, "exam_inequality": exam_inequality,
        })
        state_by_event = defaultdict(list)
        for row in states[run_id]: state_by_event[row["event_id"]].append(row)
        for h in range(1, H + 1):
            rows_h = [r for r in drows if r["homework_index"] == h]
            state_h = state_by_event[f"h{h}"]
            trajectories.append({
                "run_id": run_id, "experiment_id": identity[0], "replicate": int(identity[1][3:]),
                "homework_index": h, **{f"p{a}": _share(rows_h, a) for a in E8_ACTIONS},
                "grade": _mean(r["grade"] for r in rows_h), "reward": _mean(r["reward"] for r in rows_h),
                "K": _mean(r["K"] for r in state_h), "C": _mean(r["C"] for r in state_h),
            })
    return summaries, trajectories


def surface_policy(label: str) -> tuple[str, float, float, int]:
    if label == "E8-B-none":
        return "N", 0.0, 0.0, 0
    parts = label.split("-")
    if len(parts) != 6 or parts[:2] != ["E8", "B"]:
        raise ValueError(f"invalid E8 surface label {label!r}")
    if parts[2] == "U":
        return "U", int(parts[3][1:]) / 100, int(parts[4][1:]) / 100, int(parts[5][1:])
    if parts[2] == "T":
        return "T", int(parts[3][1:]) / 100, int(parts[4][1:]) / 100, int(parts[5][1:])
    raise ValueError(f"invalid E8 surface label {label!r}")
