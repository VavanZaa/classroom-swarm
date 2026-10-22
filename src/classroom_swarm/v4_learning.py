"""A23 explicit simulation fork: score inspection versus active learning.

Historical A22 is immutable; see docs/12 for the two intentional equation changes.
The fraction=1 control must reproduce every A22 raw table exactly.
"""
from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
import numpy as np

from .graphs import Graph
from .rng import weighted_pick
from .v3 import V3Params, initial_traits
from .v4 import (V4Params, V4Draws, V4Log, STREAMS, BENEFIT_ACTIONS,
                 activity_scores, probabilities, feedback_update)


@dataclass(frozen=True)
class LearningParams(V4Params):
    check_learning_fraction: float = 0.0
    align_check_value: bool = True

    def validate(self):
        super().validate()
        if not math.isfinite(self.check_learning_fraction) or not 0 <= self.check_learning_fraction <= 1:
            raise ValueError("check_learning_fraction must lie in [0,1]")
        if not isinstance(self.align_check_value, bool):
            raise ValueError("align_check_value must be boolean")


def learning_activity_scores(p, c, control, benefits, effort_cost, estimate, has_packet,
                             has_hint, access, social, remaining, checked=False):
    scores = activity_scores(p, c, control, benefits, effort_cost, estimate, has_packet,
                             has_hint, access, social, remaining, checked)
    if p.align_check_value and p.check_learning_fraction != 1 and "check" in scores:
        scores["check"] -= (1 - p.check_learning_fraction) * .5 * p.learning_value * control * (1 - c)
    return scores


def simulate_learning(p: LearningParams, graph: Graph, draws: V4Draws, condition="v4_learning") -> V4Log:
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
    log = V4Log({"model": "A23-v4.2-learning", "condition": condition, "params": asdict(p),
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
                    residual[i] *= 1 - min(1., p.check_learning_fraction * traits.alpha[i] / 6)
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
                scores = learning_activity_scores(p, C[i], control[i], B[i], traits.kappa[i], estimates[i],
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

