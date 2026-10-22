"""A24: automatic previous-homework grades and grade-driven copying.

Corrects the user's intended meaning of checking. Historical A22/A23 stay frozen.
"""
from __future__ import annotations
import json
import math
from dataclasses import asdict, dataclass
import numpy as np
from .graphs import Graph
from .rng import weighted_pick
from .v3 import V3Params, initial_traits
from .v4 import V4Params, V4Draws, V4Log, STREAMS, activity_scores, probabilities, feedback_update, validate_log

BENEFIT_ACTIONS = ("attempt", "hint", "answer")


@dataclass(frozen=True)
class GradeParams(V4Params):
    allow_check: bool = False
    grade_target: float = .75
    grade_response: float = .4

    def validate(self):
        super().validate()
        if self.allow_check:
            raise ValueError("A24 grades are universal feedback, not an optional checking action")
        for name in ("grade_target", "grade_response"):
            v = getattr(self, name)
            if not math.isfinite(v) or not 0 <= v <= 1:
                raise ValueError(f"{name} must lie in [0,1]")


def grade_credit(packet, used):
    if packet is None:
        total = sum(used)
        return np.asarray(used, float) / total if total else np.zeros(3), "missing"
    if packet["copied"]:
        return np.array([0., 0., 1.]), "answer"
    if packet["assisted"]:
        return np.array([.5, .5, 0.]), "guided"
    return np.array([1., 0., 0.]), "attempt"


def grade_update(benefits, c, grade, credit, assisted, complete, p):
    updated = benefits + p.eta_benefit * np.asarray(credit) * (grade-benefits)
    if p.self_assessment and complete:
        c += p.eta_confidence * (p.misattribution if assisted else 1.) * (grade-c)
    return updated, float(c), max(p.grade_target-grade, 0.), grade-p.grade_target


def grade_activity_scores(p, c, control, benefits, effort_cost, estimate, has_packet,
                          has_hint, access, social, remaining, *, shortfall=0.):
    scores = activity_scores(p, c, control, benefits, effort_cost, estimate, has_packet,
                             has_hint, access, social, remaining)
    # Private returned grade only: no latent K or future/current actual grade is read.
    if "answer" in scores:
        scores["answer"] += p.grade_response * shortfall
    return scores


def simulate_grades(p: GradeParams, graph: Graph, draws: V4Draws, condition="v4_grades") -> V4Log:
    p.validate()
    if graph.N != p.N or draws.N != p.N or draws.M_H != p.items or draws.legacy.M_E != p.exam_items:
        raise ValueError("graph/draw dimensions do not match V4 parameters")
    n = p.N
    traits = initial_traits(V3Params(N=n, alpha=p.alpha, kappa=p.kappa), draws.legacy)
    K, C = traits.K0.copy(), traits.K0.copy()
    control = np.full(n, .5)
    B = np.repeat(traits.K0[:, None], 3, axis=1)
    if p.benefit_prior is not None:
        B[:] = p.benefit_prior
    A = np.full((n, n, 2), .5)
    nb, weights = graph.neighbors, graph.neighbor_weights
    log = V4Log({"model": "A24-v4.2-grades", "condition": condition, "params": asdict(p),
                 "seed": draws.seed, "replicate": draws.replicate, "graph_hash": graph.edge_hash,
                 "weight_hash": graph.weight_hash, "family": graph.family})
    for i in range(n):
        log.tables["traits"].append(dict(student=i, K0=float(K[i]), alpha=float(traits.alpha[i]),
                                         kappa=float(traits.kappa[i]), degree=graph.degree[i]))
    for (i, j), w in zip(graph.edges, graph.weights):
        log.tables["graph"].append(dict(u=i, v=j, weight=w))
    feedback_queue = []
    grade_queue = []
    shortfall, satisfaction = np.zeros(n), np.zeros(n)
    log.tables["homework_feedback"] = []

    def return_grades(h):
        for row in [x for x in grade_queue if x["release"] == h]:
            i = row["student"]
            result = grade_update(B[i], C[i], row["grade"], row["credit"],
                                  row["assisted"], row["complete"], p)
            new_b, new_c, pressure, feeling = result
            log.tables["homework_feedback"].append(dict(
                homework=h, source_homework=row["homework"], student=i,
                grade=row["grade"], route=row["route"], assisted=row["assisted"],
                credit=json.dumps(row["credit"]), B_before=json.dumps(B[i].tolist()),
                B_after=json.dumps(new_b.tolist()), C_before=float(C[i]), C_after=new_c,
                shortfall_before=float(shortfall[i]), shortfall_after=pressure,
                satisfaction=feeling, K_before=float(K[i]), K_after=float(K[i])))
            B[i], C[i], shortfall[i], satisfaction[i] = new_b, new_c, pressure, feeling


    for h in range(1, p.H + 1):
        return_grades(h)
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
        submitted = np.zeros(n, dtype=bool)
        busy = np.zeros(n, dtype=int)
        jobs, pending = [], {}
        sequences = [[] for _ in range(n)]
        activity_counts = np.zeros((n, 3), dtype=int)
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
                scores = grade_activity_scores(p, C[i], control[i], B[i], traits.kappa[i], estimates[i],
                    packets[i] is not None, hints[i] > 0, access, bool(nb[i]), p.ticks - t,
                    shortfall=float(shortfall[i]))
                names, prob = probabilities(scores, p)
                index = min(len(names) - 1, int(np.searchsorted(np.cumsum(prob), arrays["choice"][t, i], side="right")))
                action = names[index]
                event(i, "choose_" + action, t, t, occupied=False,
                      extra=json.dumps({"scores": {k: float(v) for k, v in scores.items()},
                                        "probabilities": dict(zip(names, map(float, prob))),
                                        "grade_shortfall": float(shortfall[i]),
                                        "answer_pressure_bonus": float(p.grade_response * shortfall[i]) if "answer" in scores else 0.}, sort_keys=True))
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
                    duration = {"attempt": 3, "wait": 1, "submit": 1}[action]
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
            credit, route = grade_credit(packet, used)
            grade_queue.append(dict(homework=h, release=h+1, student=i, grade=grade,
                credit=credit.tolist(), route=route, complete=packet is not None,
                assisted=bool(packet and packet["assisted"])))
            log.tables["students"].append(dict(homework=h, student=i, K_before=float(K_start[i]),
                K=float(K[i]), C_before=float(C_start[i]), C=float(C[i]), control=float(control[i]),
                grade=grade, complete=packet is not None, copied=bool(packet and packet["copied"]),
                assisted=bool(packet and packet["assisted"]), packet_id="" if packet is None else packet["id"],
                root=-1 if packet is None else packet["root"], depth=0 if packet is None else packet["depth"],
                attempt=int(used[0]), hint=int(used[1]), answer=int(used[2]), check=0,
                help_count=int(helpful[i]), helper_ticks=int(helper_ticks[i]),
                mixed=bool(np.count_nonzero(used) >= 2), sequence=">".join(sequences[i]),
                B_attempt=float(B[i, 0]), B_hint=float(B[i, 1]), B_answer=float(B[i, 2]), B_check=0., grade_shortfall=float(shortfall[i]),
                grade_satisfaction=float(satisfaction[i])))
        if h % p.exam_every == 0:
            grades = (draws.legacy.exam(h // p.exam_every) < K[None, :]).mean(axis=0)
            for i in range(n):
                row = dict(homework=h, student=i, score=float(grades[i]), prediction=float(C[i]),
                           K=float(K[i]), release=h + p.feedback_delay + 1)
                log.tables["exams"].append(row)
                if p.feedback_mode != "none":
                    feedback_queue.append(row)
    return_grades(p.H + 1)
    return log


def validate_grade_log(log):
    validate_log(log)
    p = GradeParams(**log.manifest['params'])
    records = log.tables['homework_feedback']
    assert len(records) == p.N*p.H
    assert {(r['source_homework'],r['student']) for r in records} == {
        (h,i) for h in range(1,p.H+1) for i in range(p.N)}
    by = {(r['homework'],r['student']):r for r in log.tables['students']}
    for row in records:
        source = by[row['source_homework'],row['student']]
        assert row['homework'] == row['source_homework']+1
        assert row['grade'] == source['grade']
        assert row['K_before'] == row['K_after'] == source['K']
        assert row['shortfall_after'] == max(p.grade_target-source['grade'],0)
        expected = grade_update(np.array(json.loads(row['B_before'])),row['C_before'],
            row['grade'],json.loads(row['credit']),row['assisted'],source['complete'],p)
        np.testing.assert_allclose(json.loads(row['B_after']),expected[0],rtol=0,atol=1e-14)
        assert abs(row['C_after']-expected[1])<1e-14
    assert all(e['action'] not in {'check','choose_check'} for e in log.tables['events'])
    assert all(r['check']==0 for r in log.tables['students'])

