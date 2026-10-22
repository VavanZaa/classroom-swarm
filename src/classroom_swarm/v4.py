"""A22: bounded-time activities and delayed private assessment feedback.

The historical engines are deliberately not modified. See docs/11 for equations.
All scientific summaries below are reconstructed from raw event/state records.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field

import numpy as np

from .graphs import Graph
from .rng import Draws, weighted_pick
from .v3 import V3Params, initial_traits, simulate_v3

STREAMS = {"choice": 101, "target": 102, "accept": 103, "priority": 104, "items": 105}
BENEFIT_ACTIONS = ("attempt", "hint", "answer", "check")
MAX_TICKS = 32


@dataclass(frozen=True)
class V4Params:
    N: int = 30
    H: int = 20
    ticks: int = 12
    items: int = 10
    exam_items: int = 30
    exam_every: int = 5
    self_assessment: bool = True
    feedback_mode: str = "recalibrate"
    feedback_delay: int = 1
    choice_rule: str = "softmax"
    temperature: float = .10
    epsilon: float = .06
    alpha: float = .0584
    kappa: float = .15
    eta_benefit: float = .20
    eta_access: float = .20
    eta_confidence: float = .10
    eta_exam: float = .50
    eta_control: float = .40
    exam_target: float = .70
    learning_value: float = .25
    misattribution: float = .20
    willingness: float = .80
    reciprocity: float = 2.
    urgency_cost: float = .80
    helper_time: bool = True
    allow_hint: bool = True
    allow_answer: bool = True
    allow_check: bool = True
    benefit_prior: float | None = None

    def validate(self):
        for key in ("N", "H", "ticks", "items", "exam_items", "exam_every"):
            v = getattr(self, key)
            if not isinstance(v, int) or isinstance(v, bool) or v < 1:
                raise ValueError(f"{key} must be a positive integer")
        if self.ticks > MAX_TICKS:
            raise ValueError("ticks exceeds semantic tensor extent")
        if not isinstance(self.feedback_delay, int) or self.feedback_delay < 0:
            raise ValueError("feedback_delay must be a nonnegative integer")
        if self.feedback_mode not in {"none", "recalibrate", "constructive", "withdrawal"}:
            raise ValueError("unknown feedback mode")
        if not self.self_assessment and self.feedback_mode != "none":
            raise ValueError("exam feedback requires self_assessment")
        if self.choice_rule not in {"softmax", "argmax"}:
            raise ValueError("unknown choice rule")
        for name in ("epsilon", "eta_benefit", "eta_access", "eta_confidence", "eta_exam",
                     "eta_control", "exam_target", "misattribution", "willingness"):
            v = getattr(self, name)
            if not math.isfinite(v) or not 0 <= v <= 1:
                raise ValueError(f"{name} must lie in [0,1]")
        if self.eta_access >= 1:
            raise ValueError("eta_access must keep private tie beliefs positive")
        for name in ("temperature", "alpha"):
            if not math.isfinite(getattr(self, name)) or getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        for name in ("kappa", "learning_value", "reciprocity", "urgency_cost"):
            if not math.isfinite(getattr(self, name)) or getattr(self, name) < 0:
                raise ValueError(f"{name} must be nonnegative")
        if self.benefit_prior is not None and not 0 <= self.benefit_prior <= 1:
            raise ValueError("benefit_prior must lie in [0,1]")


class V4Draws:
    def __init__(self, seed: int, replicate: int, N: int, M_H: int, M_E: int):
        self.seed, self.replicate, self.N, self.M_H = seed, replicate, N, M_H
        self.legacy = Draws(seed, replicate, N, M_H, M_E, 3)
        self.cache = {}

    def tensor(self, name: str, h: int):
        key = (name, h)
        if key not in self.cache:
            shape = (MAX_TICKS, self.N, self.M_H) if name == "items" else (MAX_TICKS, self.N)
            a = np.random.default_rng(np.random.SeedSequence(
                [self.seed, self.replicate, STREAMS[name], h])).random(shape)
            a.setflags(write=False)
            self.cache[key] = a
        return self.cache[key]


def activity_scores(p, c, control, benefits, effort_cost, estimate, has_packet,
                    has_hint, access, social, remaining, checked=False):
    """Policy receives private beliefs only, never latent knowledge or other students' state."""
    b_s = .5 * (benefits[0] + c)
    b_d = .5 * (benefits[1] + c + .25 * (1 - c))
    if has_hint:
        b_s += .25 * (1 - b_s)
    learn = p.learning_value * control * (1 - c)
    scores = {"wait": .025}
    if remaining >= 3:
        scores["attempt"] = b_s - estimate + learn - effort_cost * 3 / 12
    if social and p.allow_hint and remaining >= 6:
        scores["hint"] = access[0] * (b_d - estimate) + 1.5 * learn - effort_cost * 6 / 12
    if social and p.allow_answer and remaining >= 2:
        scores["answer"] = access[1] * (benefits[2] - estimate) - effort_cost * 2 / 12
    if has_packet:
        scores["submit"] = 0.
        if p.allow_check and not checked and remaining >= 2:
            scores["check"] = .5 * (1 - estimate) + .5 * learn - effort_cost * 2 / 12
    return scores


def probabilities(scores, p):
    names = sorted(scores)
    u = np.array([scores[n] for n in names])
    if p.choice_rule == "argmax":
        prob = (u == u.max()).astype(float)
        prob /= prob.sum()
    else:
        prob = np.exp((u - u.max()) / p.temperature)
        prob /= prob.sum()
    return names, (1 - p.epsilon) * prob + p.epsilon / len(names)


def feedback_update(c, control, score, prediction, p):
    if p.feedback_mode == "none":
        return c, control
    c += p.eta_exam * (score - c)
    if p.feedback_mode == "constructive":
        control += p.eta_control * (p.exam_target - score) * (1 - control)
    elif p.feedback_mode == "withdrawal":
        control += p.eta_control * (score - prediction)
    return float(np.clip(c, 0, 1)), float(np.clip(control, 0, 1))


@dataclass
class V4Log:
    manifest: dict
    tables: dict = field(default_factory=lambda: {name: [] for name in (
        "events", "requests", "packets", "students", "exams", "feedback", "graph", "traits")})


def simulate_legacy(spec, graph, draws):
    return simulate_v3(spec, graph, draws)


def simulate_v4(p: V4Params, graph: Graph, draws: V4Draws, condition="v4") -> V4Log:
    p.validate()
    if graph.N != p.N or draws.N != p.N or draws.M_H != p.items or draws.legacy.M_E != p.exam_items:
        raise ValueError("graph/draw dimensions do not match V4 parameters")
    n = p.N
    traits = initial_traits(V3Params(N=n, alpha=p.alpha, kappa=p.kappa), draws.legacy)
    K, C = traits.K0.copy(), traits.K0.copy()
    control = np.full(n, .5)
    B = np.repeat(traits.K0[:, None], 4, axis=1)
    if p.benefit_prior is not None:
        B[:] = p.benefit_prior
    A = np.full((n, n, 2), .5)
    nb, weights = graph.neighbors, graph.neighbor_weights
    log = V4Log({"model": "A22-v4", "condition": condition, "params": asdict(p),
                 "seed": draws.seed, "replicate": draws.replicate, "graph_hash": graph.edge_hash,
                 "weight_hash": graph.weight_hash, "family": graph.family})
    for i in range(n):
        log.tables["traits"].append(dict(student=i, K0=float(K[i]), alpha=float(traits.alpha[i]),
                                         kappa=float(traits.kappa[i]), degree=graph.degree[i]))
    for (i, j), w in zip(graph.edges, graph.weights):
        log.tables["graph"].append(dict(u=i, v=j, weight=w))
    feedback_queue = []

    for h in range(1, p.H + 1):
        for fb in [x for x in feedback_queue if x["release"] == h]:
            i = fb["student"]
            cb, rb = float(C[i]), float(control[i])
            C[i], control[i] = feedback_update(cb, rb, fb["score"], fb["prediction"], p)
            log.tables["feedback"].append(dict(homework=h, student=i, exam_homework=fb["homework"],
                score=fb["score"], prediction=fb["prediction"], C_before=cb, C_after=float(C[i]),
                control_before=rb, control_after=float(control[i]), K_before=float(K[i]), K_after=float(K[i])))
        K_start, C_start = K.copy(), C.copy()
        packets = [None] * n
        estimates = np.zeros(n)
        hints = np.zeros(n)
        checked = [None] * n
        submitted = np.zeros(n, dtype=bool)
        busy = np.zeros(n, dtype=int)
        jobs, pending = [], {}
        sequences = [[] for _ in range(n)]
        activity_counts = np.zeros((n, 4), dtype=int)
        helpful = np.zeros(n, dtype=int)
        helper_ticks = np.zeros(n, dtype=int)
        arrays = {name: draws.tensor(name, h) for name in STREAMS}

        def event(i, action, start, end, before=None, after=None, occupied=True, packet=None,
                  provider=-1, extra=""):
            log.tables["events"].append(dict(homework=h, student=i, action=action, start=int(start),
                end=int(end), occupied=bool(occupied), K_before=float(K[i] if before is None else before),
                K_after=float(K[i] if after is None else after), C=float(C[i]), control=float(control[i]),
                estimate=float(estimates[i]), packet_id="" if packet is None else packet["id"],
                root=-1 if packet is None else packet["root"], depth=0 if packet is None else packet["depth"],
                provider=int(provider), detail=extra))

        def resolve(req, finish, success, reason):
            i, j, mode = req["i"], req["j"], req["mode"]
            m = int(mode == "answer")
            before = float(A[i, j, m])
            A[i, j, m] += p.eta_access * (int(success) - A[i, j, m])
            log.tables["requests"].append(dict(homework=h, requester=i, provider=j, mode=mode,
                start=req["start"], finish=int(finish), success=bool(success), reason=reason,
                blocked_busy=req["blocked_busy"], declined=req["declined"],
                no_packet=req["no_packet"], A_before=before, A_after=float(A[i, j, m]),
                observed="delivered" if success else "unavailable"))

        def complete(t):
            finishing = [job for job in jobs if job["end"] == t]
            if not finishing:
                return
            # Aggregate gains from the same frozen state, including the helper-time-free control.
            before = K.copy()
            residual = np.ones(n)
            for job in finishing:
                i, kind = job["i"], job["kind"]
                if kind == "attempt":
                    residual[i] *= 1 - min(1., traits.alpha[i] / 3 * (1 + job["hint"]))
                elif kind == "check":
                    residual[i] *= 1 - min(1., traits.alpha[i] / 6)
                elif kind == "hint":
                    j = job["j"]
                    residual[j] *= 1 - min(1., traits.alpha[j] / 6)
            # Add a nonnegative increment; recomputing 1-(1-K) perturbs inactive K by one ULP.
            K[:] = before + (1 - before) * (1 - residual)
            for job in finishing:
                i, kind, start = job["i"], job["kind"], job["start"]
                if kind == "attempt":
                    hint = job["hint"]
                    prob = float(K[i] + hint * (1 - K[i]))
                    bits = arrays["items"][start, i] < prob
                    packet = dict(id=f"h{h}-i{i}-t{start}", root=i, depth=0,
                                  bits=bits, assisted=hint > 0, copied=False)
                    parent = "" if packets[i] is None else packets[i]["id"]
                    packets[i] = packet
                    estimates[i] = min(1., C[i] + (.25 * (1 - C[i]) if hint > 0 else 0))
                    log.tables["packets"].append(dict(homework=h, student=i, tick=t, packet_id=packet["id"],
                        parent_id=parent, root=i, probability=prob, assisted=bool(hint > 0),
                        item_bits="".join("1" if x else "0" for x in bits)))
                    event(i, "attempt", start, t, before[i], K[i], packet=packet)
                elif kind == "check":
                    packet = packets[i]
                    estimates[i] = float(np.mean(packet["bits"]))
                    checked[i] = packet["id"]
                    if p.self_assessment:
                        weight = p.misattribution if packet["assisted"] else 1.
                        C[i] += p.eta_confidence * weight * (estimates[i] - C[i])
                    event(i, "check", start, t, before[i], K[i], packet=packet)
                elif kind in {"hint", "answer"}:
                    j = job["j"]
                    if kind == "hint":
                        hints[i] = job["strength"]
                        event(i, "hint_receive", start, t, before[i], K[i], provider=j)
                    else:
                        src = job["source"]
                        packets[i] = dict(src, depth=src["depth"] + 1, assisted=True, copied=True)
                        estimates[i] = float(B[i, 2])
                        event(i, "answer_receive", start, t, before[i], K[i], packet=packets[i], provider=j)
                    event(j, "help_" + kind, start, t, before[j], K[j], occupied=p.helper_time,
                          packet=job.get("source"), provider=i)
                    helpful[j] += 1
                    helper_ticks[j] += t - start
                    resolve(job["request"], t, True, "delivered")
                elif kind == "submit":
                    submitted[i] = True
                    event(i, "submit", start, t, before[i], K[i], packet=packets[i])
                else:
                    event(i, "wait", start, t, before[i], K[i])
            jobs[:] = [job for job in jobs if job["end"] != t]

        for t in range(p.ticks):
            complete(t)
            used_helpers = set()
            # Requests created in a previous tick compete for currently free partners.
            for i in sorted(list(pending), key=lambda x: (arrays["priority"][t, x], x)):
                req = pending[i]
                j, mode = req["j"], req["mode"]
                duration = 2 if mode == "hint" else 1
                eligible = busy[j] <= t and j not in pending and j not in used_helpers
                reason = "busy"
                if not eligible:
                    req["blocked_busy"] += 1
                elif mode == "answer" and packets[j] is None:
                    req["no_packet"] += 1
                    reason = "no_packet"
                    eligible = False
                if eligible and t + duration <= p.ticks:
                    base = p.willingness
                    if base in (0., 1.):
                        willingness = base
                    else:
                        urgency = 0. if submitted[j] else t / p.ticks
                        z = math.log(base / (1 - base)) + p.reciprocity * (A[j, i, int(mode == "answer")] - .5)
                        willingness = 1 / (1 + math.exp(-z + p.urgency_cost * urgency))
                    if arrays["accept"][t, i] < willingness:
                        job = dict(i=i, j=j, kind=mode, start=t, end=t + duration, request=req,
                                   strength=float(.15 + .35 * K[j]))
                        if mode == "answer":
                            job["source"] = dict(packets[j])
                        jobs.append(job)
                        busy[i] = t + duration
                        if p.helper_time:
                            busy[j] = t + duration
                        used_helpers.add(j)
                        del pending[i]
                        continue
                    req["declined"] += 1
                    reason = "declined"
                elif eligible:
                    reason = "deadline"
                event(i, "waiting", t, t + 1)
                busy[i] = t + 1
                if t - req["start"] >= 2 or t == p.ticks - 1:
                    resolve(req, t + 1, False, reason)
                    del pending[i]

            for i in range(n):
                if busy[i] > t or i in pending or submitted[i]:
                    continue
                access = []
                for mode in range(2):
                    values = np.array([A[i, j, mode] for j in nb[i]])
                    w = np.array(weights[i]) * values
                    access.append(float(np.dot(w, values) / w.sum()) if len(w) else 0.)
                scores = activity_scores(p, C[i], control[i], B[i], traits.kappa[i], estimates[i],
                    packets[i] is not None, hints[i] > 0, access, bool(nb[i]), p.ticks - t,
                    packets[i] is not None and checked[i] == packets[i]["id"])
                names, prob = probabilities(scores, p)
                index = min(len(names) - 1, int(np.searchsorted(np.cumsum(prob), arrays["choice"][t, i], side="right")))
                action = names[index]
                event(i, "choose_" + action, t, t, occupied=False,
                      extra=json.dumps({"scores": {k: float(v) for k, v in scores.items()},
                                        "probabilities": dict(zip(names, map(float, prob)))}, sort_keys=True))
                sequences[i].append(action)
                if action in BENEFIT_ACTIONS:
                    activity_counts[i, BENEFIT_ACTIONS.index(action)] += 1
                if action in {"hint", "answer"}:
                    mode = int(action == "answer")
                    target = weighted_pick(nb[i], [w * A[i, j, mode] for j, w in zip(nb[i], weights[i])],
                                           float(arrays["target"][t, i]))
                    pending[i] = dict(i=i, j=target, mode=action, start=t,
                                      blocked_busy=0, declined=0, no_packet=0)
                    busy[i] = t + 1
                    event(i, "request_" + action, t, t + 1, provider=target)
                else:
                    duration = {"attempt": 3, "check": 2, "wait": 1, "submit": 1}[action]
                    jobs.append(dict(i=i, kind=action, start=t, end=t + duration, hint=float(hints[i])))
                    if action == "attempt":
                        hints[i] = 0
                    busy[i] = t + duration
        complete(p.ticks)
        assert not jobs and not pending
        for i in range(n):
            packet = packets[i]
            grade = 0. if packet is None else float(np.mean(packet["bits"]))
            used = activity_counts[i]
            total = int(used.sum())
            if total:
                B[i] += p.eta_benefit * used / total * (grade - B[i])
            if p.self_assessment and packet is not None:
                weight = p.misattribution if packet["assisted"] else 1.
                C[i] += p.eta_confidence * weight * (grade - C[i])
            log.tables["students"].append(dict(homework=h, student=i, K_before=float(K_start[i]),
                K=float(K[i]), C_before=float(C_start[i]), C=float(C[i]), control=float(control[i]),
                grade=grade, complete=packet is not None, copied=bool(packet and packet["copied"]),
                assisted=bool(packet and packet["assisted"]), packet_id="" if packet is None else packet["id"],
                root=-1 if packet is None else packet["root"], depth=0 if packet is None else packet["depth"],
                attempt=int(used[0]), hint=int(used[1]), answer=int(used[2]), check=int(used[3]),
                help_count=int(helpful[i]), helper_ticks=int(helper_ticks[i]),
                mixed=bool(np.count_nonzero(used) >= 2), sequence=">".join(sequences[i]),
                B_attempt=float(B[i, 0]), B_hint=float(B[i, 1]), B_answer=float(B[i, 2]), B_check=float(B[i, 3])))
        if h % p.exam_every == 0:
            grades = (draws.legacy.exam(h // p.exam_every) < K[None, :]).mean(axis=0)
            for i in range(n):
                row = dict(homework=h, student=i, score=float(grades[i]), prediction=float(C[i]),
                           K=float(K[i]), release=h + p.feedback_delay + 1)
                log.tables["exams"].append(row)
                if p.feedback_mode != "none":
                    feedback_queue.append(row)
    return log


def validate_log(log):
    """Audit raw identities, timing, bounds and disjoint occupied intervals."""
    p = log.manifest["params"]
    intervals = {}
    for e in log.tables["events"]:
        assert 0 <= e["start"] <= e["end"] <= p["ticks"]
        if e["occupied"]:
            intervals.setdefault((e["homework"], e["student"]), []).append((e["start"], e["end"]))
    for seq in intervals.values():
        seq.sort()
        assert all(a[1] <= b[0] for a, b in zip(seq, seq[1:])), seq
    packets = {r["packet_id"]: r for r in log.tables["packets"]}
    assert len(packets) == len(log.tables["packets"])
    assert len(log.tables["students"]) == p["N"] * p["H"]
    for r in log.tables["students"]:
        assert 0 <= r["K_before"] <= r["K"] <= 1
        assert 0 <= r["C"] <= 1 and 0 <= r["control"] <= 1
        if r["complete"]:
            packet = packets[r["packet_id"]]
            assert r["grade"] == sum(x == "1" for x in packet["item_bits"]) / p["items"]
            assert r["root"] == packet["root"]
        else:
            assert r["grade"] == 0 and not r["packet_id"]
    for r in log.tables["requests"]:
        expected = r["A_before"] + p["eta_access"] * (int(r["success"]) - r["A_before"])
        assert abs(expected - r["A_after"]) < 1e-12
        assert r["finish"] > r["start"]
    for f in log.tables["feedback"]:
        assert f["homework"] == f["exam_homework"] + p["feedback_delay"] + 1
        assert f["K_before"] == f["K_after"]


def _mean(rows, key):
    return float(np.mean([r[key] for r in rows])) if rows else float("nan")


def gini(values):
    v = np.sort(np.asarray(values, float))
    return float((2 * np.dot(np.arange(1, len(v) + 1), v) / v.sum() - len(v) - 1) / len(v)) if v.sum() else 0.


def summarize(log):
    p = log.manifest["params"]
    rows = log.tables["students"]
    late = [r for r in rows if r["homework"] > p["H"] - 5]
    final = [r for r in rows if r["homework"] == p["H"]]
    exams = log.tables["exams"]
    last_exam = max((r["homework"] for r in exams), default=-1)
    req = [r for r in log.tables["requests"] if r["homework"] > p["H"] - 5]
    successful = [r for r in req if r["success"]]
    providers = np.bincount([r["provider"] for r in successful], minlength=p["N"])
    out = {"K_final": _mean(final, "K"), "exam_final": _mean([r for r in exams if r["homework"] == last_exam], "score"),
           "grade_late": _mean(late, "grade"), "copy_late": _mean(late, "copied"),
           "assisted_late": _mean(late, "assisted"), "incomplete_late": 1 - _mean(late, "complete"),
           "calibration_late": float(np.mean([abs(r["C"] - r["K"]) for r in late])),
           "confidence_bias_late": float(np.mean([r["C"] - r["K"] for r in late])),
           "mixed_late": _mean(late, "mixed"), "control_late": _mean(late, "control"),
           "help_success": len(successful) / len(req) if req else float("nan"),
           "busy_request_share": float(np.mean([r["blocked_busy"] > 0 for r in req])) if req else float("nan"),
           "request_latency": float(np.mean([r["finish"] - r["start"] for r in req])) if req else float("nan"),
           "source_gini": gini(providers),
           "source_top20": float(np.sort(providers)[-max(1, math.ceil(p["N"] * .2)):].sum() / providers.sum()) if providers.sum() else float("nan"),
           "multihop_late": float(np.mean([r["depth"] >= 2 for r in late])),
           "hint_then_attempt": float(np.mean(["hint" in r["sequence"] and "attempt" in r["sequence"].split("hint", 1)[1] for r in late])),
           "answer_then_check": float(np.mean(["answer" in r["sequence"] and "check" in r["sequence"].split("answer", 1)[1] for r in late])),
           "K_sd_final": float(np.std([r["K"] for r in final])),
           "early_copy": _mean([r for r in rows if r["homework"] <= 5], "copied")}
    out["grade_knowledge_gap"] = out["grade_late"] - _mean(late, "K")
    out["grade_exam_gap"] = out["grade_late"] - out["exam_final"]
    for key in ("attempt", "hint", "answer", "check", "help_count", "helper_ticks"):
        out[key + "_late"] = _mean(late, key)
    halves = []
    for first in (True, False):
        rr = [r for r in log.tables["requests"] if r["success"] and ((r["homework"] <= p["H"] // 2) == first)]
        halves.append(np.bincount([r["provider"] for r in rr], minlength=p["N"]).astype(float))
    # Descriptive degree-adjusted persistence, NOT a strict causal role test.
    x = np.column_stack([np.ones(p["N"]), [r["degree"] for r in log.tables["traits"]]])
    residuals = [v - x @ np.linalg.lstsq(x, v, rcond=None)[0] for v in halves]
    out["source_persistence"] = float(np.corrcoef(*residuals)[0, 1]) if all(np.std(v) > 1e-10 for v in residuals) else float("nan")
    by = {(r["homework"], r["student"]): r for r in rows}
    prev_copy, recovered = 0, 0
    for r in late:
        prev = by.get((r["homework"] - 1, r["student"]))
        if prev and prev["copied"]:
            prev_copy += 1
            recovered += int(r["complete"] and not r["assisted"])
    out["copy_to_unaided"] = recovered / prev_copy if prev_copy else float("nan")
    return out


def trajectories(log):
    rows = log.tables["students"]
    result = []
    for h in range(1, log.manifest["params"]["H"] + 1):
        rr = [r for r in rows if r["homework"] == h]
        row = {"homework": h}
        for k in ("K", "C", "grade", "copied", "assisted", "complete", "mixed", "control",
                  "attempt", "hint", "answer", "check", "helper_ticks"):
            row[k] = _mean(rr, k)
        row["calibration"] = float(np.mean([abs(r["C"] - r["K"]) for r in rr]))
        result.append(row)
    return result
