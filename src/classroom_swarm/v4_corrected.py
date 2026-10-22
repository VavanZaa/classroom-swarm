"""A26 corrected controls: learnable tutor credit, honest hint deadlines, separable score terms.

Explicit source fork of A25 (docs/15). Every A22-A25 source stays byte-identical, and under the
legacy flags this engine must reproduce A25 on every shared raw table.
"""
from __future__ import annotations
import json
import math
from dataclasses import asdict, dataclass
import numpy as np
from .graphs import Graph
from .rng import weighted_pick
from .v3 import V3Params, initial_traits
from .v4 import V4Log, STREAMS, probabilities, feedback_update, validate_log
from .v4_grades import grade_update
from .v4_public_ai import PublicAIParams, PublicAIDraws, contact_matrix, target_options

BENEFIT_ACTIONS = ("attempt", "hint", "answer", "ai_answer", "ai_tutor")


@dataclass(frozen=True)
class CorrectedParams(PublicAIParams):
    tutor_credit_by_source: bool = True
    hint_deadline_guard: bool = True
    confidence_weight: float = .5
    wait_value: float = 0.
    attempt_ticks: int = 3

    def validate(self):
        super().validate()
        for name in ("tutor_credit_by_source", "hint_deadline_guard"):
            if not isinstance(getattr(self, name), bool):
                raise ValueError(f"{name} must be boolean")
        for name in ("confidence_weight", "wait_value"):
            v = getattr(self, name)
            if not math.isfinite(v) or not 0 <= v <= 1:
                raise ValueError(f"{name} must lie in [0,1]")
        if not isinstance(self.attempt_ticks, int) or isinstance(self.attempt_ticks, bool) or self.attempt_ticks < 1:
            raise ValueError("attempt_ticks must be a positive integer")
        if self.attempt_ticks > self.ticks:
            raise ValueError("attempt_ticks cannot exceed the homework deadline")


def blend(w, benefit, c, boost=0.):
    """Perceived grade of an own-work route: learned benefit shrunk toward self-assessment.

    At w=.5 this evaluates A25's literal expression, so legacy parity is bit-exact rather than
    within a rounding step; the general form only applies off the legacy value.
    """
    if w == .5:
        return .5 * (benefit + c + boost * (1 - c))
    return (1 - w) * benefit + w * (c + boost * (1 - c))


def corrected_scores(p, c, control, benefits, effort_cost, estimate, has_packet, has_hint, access,
                     can_hint, can_answer, remaining, *, shortfall=0., peer_prediction=None,
                     ai_available=False):
    """A25's score chain with the confidence weight and the waiting score made explicit.

    Policy receives private beliefs only: never latent knowledge, current item bits, another
    student's state, or the simulation's true AI capability.
    """
    w, a = p.confidence_weight, p.attempt_ticks
    peer_benefit = benefits[2] if peer_prediction is None else peer_prediction
    b_s = blend(w, benefits[0], c)
    b_d = blend(w, benefits[1], c, .25)
    if has_hint:
        b_s += .25 * (1 - b_s)
    learn = p.learning_value * control * (1 - c)
    scores = {"wait": p.wait_value}
    if remaining >= a:
        scores["attempt"] = b_s - estimate + learn - effort_cost * a / 12
    if can_hint and p.allow_hint and remaining >= 3 + a:
        scores["hint"] = access[0] * (b_d - estimate) + 1.5 * learn - effort_cost * (3 + a) / 12
    if can_answer and p.allow_answer and remaining >= 2:
        scores["answer"] = access[1] * (peer_benefit - estimate) - effort_cost * 2 / 12 + p.grade_response * shortfall
    if has_packet:
        scores["submit"] = 0.
    if ai_available and p.ai_mode == "answer" and remaining >= p.ai_answer_ticks:
        scores["ai_answer"] = (benefits[3] - estimate - effort_cost * p.ai_answer_ticks / 12
                               + p.grade_response * shortfall)
    if ai_available and p.ai_mode == "tutor" and remaining >= p.ai_tutor_ticks + a:
        # Perceived grade benefit, not the tutor's true generative effectiveness.
        predicted = benefits[4] if p.grade_effort_only else blend(w, benefits[4], c, .25)
        scores["ai_tutor"] = predicted - estimate + 1.5 * learn - effort_cost * (p.ai_tutor_ticks + a) / 12
    return scores


def corrected_grade_credit(packet, used):
    """Credit the route actually submitted. An AI-tutored attempt is credited by hint source."""
    if packet is None:
        total = sum(used)
        return np.asarray(used, float) / total if total else np.zeros(5), "missing"
    credit = np.zeros(5)
    if packet["via"] == "ai":
        credit[3] = 1; route = "ai_answer"
    elif packet["via"] == "peer":
        credit[2] = 1; route = "answer"
    elif packet["origin"] == "ai_tutor_attempt":
        credit[0] = credit[4] = .5; route = "ai_guided"
    elif packet["assisted"]:
        credit[0] = credit[1] = .5; route = "guided"
    else:
        credit[0] = 1; route = "attempt"
    return credit, route


def simulate_corrected(p: CorrectedParams, graph: Graph, draws: PublicAIDraws,
                       condition="corrected") -> V4Log:
    p.validate()
    if graph.N != p.N or draws.N != p.N or draws.M_H != p.items or draws.legacy.M_E != p.exam_items:
        raise ValueError("graph/draw dimensions do not match V4 parameters")
    n = p.N
    traits = initial_traits(V3Params(N=n, alpha=p.alpha, kappa=p.kappa), draws.legacy)
    K, C = traits.K0.copy(), traits.K0.copy()
    control = np.full(n, .5)
    B = np.repeat(traits.K0[:, None], 5, axis=1)
    if p.benefit_prior is not None:
        B[:] = p.benefit_prior
    A = np.full((n, n, 2), .5)
    contacts = contact_matrix(p, graph, draws)
    public_grades = np.full(n, np.nan)
    log = V4Log({"model": "A26-v4.3-corrected", "condition": condition, "params": asdict(p),
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
    log.tables["ai_uses"] = []
    log.tables["hint_receipts"] = []
    log.tables["contacts"] = [dict(u=i, v=j, closeness=float(contacts[i, j]), friend=graph.has_edge(i, j))
                              for i in range(n) for j in range(i + 1, n) if contacts[i, j] > 0]

    def return_grades(h):
        for row in [x for x in grade_queue if x["release"] == h]:
            i = row["student"]
            public_grades[i] = row["grade"]
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
        hint_sources = ["none"] * n
        ai_used = np.zeros(n, dtype=bool)
        submitted = np.zeros(n, dtype=bool)
        busy = np.zeros(n, dtype=int)
        jobs, pending = [], {}
        sequences = [[] for _ in range(n)]
        activity_counts = np.zeros((n, 5), dtype=int)
        helpful = np.zeros(n, dtype=int)
        helper_ticks = np.zeros(n, dtype=int)
        arrays = {name: draws.tensor(name, h) for name in STREAMS}
        arrays["ai_items"] = draws.tensor("ai_items", h)

        def event(i, action, start, end, before=None, after=None, occupied=True, packet=None,
                  provider=-1, extra=""):
            log.tables["events"].append(dict(homework=h, student=i, action=action, start=int(start),
                end=int(end), occupied=bool(occupied), K_before=float(K[i] if before is None else before),
                K_after=float(K[i] if after is None else after), C=float(C[i]), control=float(control[i]),
                estimate=float(estimates[i]), packet_id="" if packet is None else packet["id"],
                root=-1 if packet is None else packet["root"], depth=0 if packet is None else packet["depth"],
                provider=int(provider), detail=extra))

        def receive_hint(i, provider, strength, source, tick):
            hints[i], hint_sources[i] = strength, source
            log.tables["hint_receipts"].append(dict(homework=h, student=i, provider=int(provider),
                tick=int(tick), strength=float(strength), source=source,
                remaining=int(p.ticks - tick), usable=bool(p.ticks - tick >= p.attempt_ticks)))

        def resolve(req, finish, success, reason):
            i, j, mode = req["i"], req["j"], req["mode"]
            m = int(mode == "answer")
            before = float(A[i, j, m])
            A[i, j, m] += p.eta_access * (int(success) - A[i, j, m])
            log.tables["requests"].append(dict(homework=h, requester=i, provider=j, mode=mode,
                start=req["start"], finish=int(finish), success=bool(success), reason=reason,
                blocked_busy=req["blocked_busy"], declined=req["declined"],
                no_packet=req["no_packet"], A_before=before, A_after=float(A[i, j, m]),
                observed="delivered" if success else "unavailable",
                requester_public_grade=req["own_grade"], provider_public_grade=req["source_grade"],
                closeness=req["closeness"], research_requester_K=req["own_K"], research_provider_K=req["source_K"]))

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
                    # A26: credit the tutor by the hint's source, so a zero-strength tutor is learnable.
                    ai_guided = job["hint_source"] == "ai" and (p.tutor_credit_by_source or hint > 0)
                    prob = float(K[i] + hint * (1 - K[i]))
                    bits = arrays["items"][start, i] < prob
                    packet = dict(id=f"h{h}-i{i}-t{start}", root=i, depth=0,
                                  bits=bits, assisted=hint > 0, copied=False, via="attempt",
                                  origin="ai_tutor_attempt" if ai_guided else "student")
                    parent = "" if packets[i] is None else packets[i]["id"]
                    packets[i] = packet
                    estimates[i] = min(1., C[i] + (.25 * (1 - C[i]) if hint > 0 else 0))
                    log.tables["packets"].append(dict(homework=h, student=i, tick=t, packet_id=packet["id"],
                        parent_id=parent, root=i, probability=prob, assisted=bool(hint > 0),
                        item_bits="".join("1" if x else "0" for x in bits), origin=packet["origin"],
                        hint_source=job["hint_source"]))
                    event(i, "attempt", start, t, before[i], K[i], packet=packet)
                elif kind in {"ai_answer", "ai_tutor"}:
                    packet = None
                    if kind == "ai_answer":
                        bits = arrays["ai_items"][start, i] < p.ai_accuracy
                        packet = dict(id=f"ai-h{h}-i{i}-t{start}", root=-1, depth=0, bits=bits,
                                      assisted=True, copied=True, origin="ai_answer", via="ai")
                        parent = "" if packets[i] is None else packets[i]["id"]
                        packets[i] = packet
                        estimates[i] = float(B[i, 3])
                        log.tables["packets"].append(dict(homework=h, student=i, tick=t, packet_id=packet["id"],
                            parent_id=parent, root=-1, probability=p.ai_accuracy, assisted=True,
                            item_bits="".join("1" if x else "0" for x in bits), origin="ai_answer", hint_source="none"))
                    else:
                        receive_hint(i, -1, p.ai_hint_strength, "ai", t)
                    log.tables["ai_uses"].append(dict(homework=h, student=i, mode=kind, start=start, end=t,
                        K_before=float(before[i]), K_after=float(K[i]),
                        packet_id="" if packet is None else packet["id"],
                        accuracy=p.ai_accuracy if kind == "ai_answer" else None,
                        hint_strength=p.ai_hint_strength if kind == "ai_tutor" else None))
                    event(i, kind + "_receive", start, t, before[i], K[i], packet=packet)
                elif kind in {"hint", "answer"}:
                    j = job["j"]
                    if kind == "hint":
                        receive_hint(i, j, job["strength"], "peer", t)
                        event(i, "hint_receive", start, t, before[i], K[i], provider=j)
                    else:
                        src = job["source"]
                        packets[i] = dict(src, depth=src["depth"] + 1, assisted=True, copied=True, via="peer")
                        estimates[i] = job["request"]["expected_grade"]
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
                # A26: a hint is only served if a full attempt still fits, as the AI tutor already requires.
                tail = p.attempt_ticks if mode == "hint" and p.hint_deadline_guard else 0
                eligible = busy[j] <= t and j not in pending and j not in used_helpers
                reason = "busy"
                if not eligible:
                    req["blocked_busy"] += 1
                elif mode == "answer" and packets[j] is None:
                    req["no_packet"] += 1
                    reason = "no_packet"
                    eligible = False
                if eligible and t + duration + tail <= p.ticks:
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
                pools, target_weights, access = [], [], []
                for mode in ("hint", "answer"):
                    ids, ws = target_options(i, mode, contacts, A, public_grades, p)
                    pools.append(ids); target_weights.append(ws)
                    m = int(mode == "answer")
                    access.append(float(np.dot(ws, [A[i, j, m] for j in ids]) / sum(ws)) if ws else 0.)
                peer_prediction = float(B[i, 2])
                if pools[1] and np.isfinite(public_grades[i]):
                    observed = float(np.dot(target_weights[1], public_grades[pools[1]]) / sum(target_weights[1]))
                    peer_prediction = (1 - p.public_signal) * peer_prediction + p.public_signal * observed
                scores = corrected_scores(p, C[i], control[i], B[i], traits.kappa[i], estimates[i],
                    packets[i] is not None, hints[i] > 0, access, bool(pools[0]), bool(pools[1]), p.ticks - t,
                    shortfall=float(shortfall[i]), peer_prediction=peer_prediction,
                    ai_available=h >= p.ai_start and not ai_used[i])
                names, prob = probabilities(scores, p)
                index = min(len(names) - 1, int(np.searchsorted(np.cumsum(prob), arrays["choice"][t, i], side="right")))
                action = names[index]
                event(i, "choose_" + action, t, t, occupied=False,
                      extra=json.dumps({"scores": {k: float(v) for k, v in scores.items()},
                                        "probabilities": dict(zip(names, map(float, prob))),
                                        "grade_shortfall": float(shortfall[i]),
                                        "answer_pressure_bonus": float(p.grade_response * shortfall[i]) if "answer" in scores else 0.,
                                        "ai_answer_pressure_bonus": float(p.grade_response * shortfall[i]) if "ai_answer" in scores else 0.,
                                        "eligible_answer_sources": pools[1]}, sort_keys=True))
                sequences[i].append(action)
                if action in BENEFIT_ACTIONS:
                    activity_counts[i, BENEFIT_ACTIONS.index(action)] += 1
                if action in {"hint", "answer"}:
                    mode = int(action == "answer")
                    target = weighted_pick(pools[mode], target_weights[mode], float(arrays["target"][t, i]))
                    pending[i] = dict(i=i, j=target, mode=action, start=t,
                                      blocked_busy=0, declined=0, no_packet=0,
                                      own_grade=float(public_grades[i]) if np.isfinite(public_grades[i]) else None,
                                      source_grade=float(public_grades[target]) if np.isfinite(public_grades[target]) else None,
                                      closeness=float(contacts[i, target]), own_K=float(K[i]), source_K=float(K[target]),
                                      expected_grade=float((1 - p.public_signal) * B[i, 2] + p.public_signal * public_grades[target])
                                                     if np.isfinite(public_grades[target]) else float(B[i, 2]))
                    busy[i] = t + 1
                    event(i, "request_" + action, t, t + 1, provider=target)
                else:
                    duration = {"attempt": p.attempt_ticks, "wait": 1, "submit": 1,
                                "ai_answer": p.ai_answer_ticks, "ai_tutor": p.ai_tutor_ticks}[action]
                    if action in {"ai_answer", "ai_tutor"}:
                        ai_used[i] = True
                    jobs.append(dict(i=i, kind=action, start=t, end=t + duration, hint=float(hints[i]),
                                     hint_source=hint_sources[i]))
                    if action == "attempt":
                        hints[i], hint_sources[i] = 0, "none"
                    busy[i] = t + duration
        complete(p.ticks)
        assert not jobs and not pending
        for i in range(n):
            packet = packets[i]
            grade = 0. if packet is None else float(np.mean(packet["bits"]))
            used = activity_counts[i]
            credit, route = corrected_grade_credit(packet, used)
            grade_queue.append(dict(homework=h, release=h + 1, student=i, grade=grade,
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
                B_attempt=float(B[i, 0]), B_hint=float(B[i, 1]), B_answer=float(B[i, 2]), B_check=0.,
                grade_shortfall=float(shortfall[i]), grade_satisfaction=float(satisfaction[i]),
                B_ai_answer=float(B[i, 3]), B_ai_tutor=float(B[i, 4]),
                ai_answer=int(used[3]), ai_tutor=int(used[4]), final_route=route,
                peer_copied=bool(packet and packet["via"] == "peer"),
                direct_ai_answer=bool(packet and packet["via"] == "ai"),
                ai_answer_origin=bool(packet and packet["origin"] == "ai_answer")))
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


def validate_corrected_log(log):
    """A25's audit plus the two A26 guarantees."""
    validate_log(log)
    p = CorrectedParams(**log.manifest["params"])
    rows = log.tables["homework_feedback"]
    by = {(r["homework"], r["student"]): r for r in log.tables["students"]}
    assert len(rows) == p.N * p.H
    assert len({(r["source_homework"], r["student"]) for r in rows}) == p.N * p.H
    for row in rows:
        source = by[row["source_homework"], row["student"]]
        assert row["homework"] == row["source_homework"] + 1
        assert row["grade"] == source["grade"] and row["K_before"] == row["K_after"] == source["K"]
        expected = grade_update(np.array(json.loads(row["B_before"])), row["C_before"], row["grade"],
                                json.loads(row["credit"]), row["assisted"], source["complete"], p)
        np.testing.assert_allclose(json.loads(row["B_after"]), expected[0], rtol=0, atol=1e-14)
        assert abs(row["C_after"] - expected[1]) < 1e-14
        assert row["shortfall_after"] == expected[2]
    for req in log.tables["requests"]:
        h = req["homework"]
        if h > 1:
            assert req["requester_public_grade"] == by[h - 1, req["requester"]]["grade"]
            assert req["provider_public_grade"] == by[h - 1, req["provider"]]["grade"]
        else:
            assert req["requester_public_grade"] is None and req["provider_public_grade"] is None
        if req["mode"] == "answer" and p.peer_rule == "higher":
            assert h > 1 and req["provider_public_grade"] > req["requester_public_grade"]
    ai = log.tables["ai_uses"]
    assert len({(r["homework"], r["student"]) for r in ai}) == len(ai)
    assert all(r["homework"] >= p.ai_start and r["K_before"] == r["K_after"] for r in ai)
    assert p.ai_mode != "none" or not ai
    assert all(e["action"] not in {"check", "choose_check"} for e in log.tables["events"])
    # A26: no peer hint arrives too late to use while the guard is on.
    peer = [r for r in log.tables["hint_receipts"] if r["source"] == "peer"]
    assert len(peer) == sum(e["action"] == "hint_receive" for e in log.tables["events"])
    if p.hint_deadline_guard:
        assert all(r["usable"] for r in peer)
    assert all(r["usable"] for r in log.tables["hint_receipts"] if r["source"] == "ai")
    # A26: a consulted tutor is always credited, whatever its strength.
    tutored = {(r["homework"], r["student"]) for r in log.tables["packets"] if r["hint_source"] == "ai"}
    if p.tutor_credit_by_source:
        assert tutored == {(r["homework"], r["student"]) for r in log.tables["packets"]
                           if r["origin"] == "ai_tutor_attempt"}
