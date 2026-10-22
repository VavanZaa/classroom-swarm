"""Quantities rebuilt from the canonical raw tables (docs/07 derived/, docs/09 derive.py).

Inputs are `pyarrow.Table`s. Answers are joined only on the composite key (run_id, answer_id).
Definitions of the E1 quantities: docs/experiments/E1-preregistration.md §4, §4b, §7.
"""
from __future__ import annotations

from collections import Counter, defaultdict

import pyarrow as pa


def _homework_of(event_id: str) -> int | None:
    """event_id convention (docs/07): 'init', 'h<homework>', 'e<exam>'."""
    return int(event_id[1:]) if event_id.startswith("h") else None


def _successful_transfers(routing_events: pa.Table) -> dict[tuple[str, int, int], int]:
    """(run_id, h, receiver) -> sender. A copier accepts only its first packet, so this is unique."""
    parent: dict[tuple[str, int, int], int] = {}
    for r in routing_events.to_pylist():
        if r["transfer_success"]:
            key = (r["run_id"], r["homework_index"], r["requester_id"])
            if key in parent:
                raise ValueError(f"two successful transfers to the same copier: {key}")
            parent[key] = r["target_id"]
    return parent


def provenance_paths(routing_events: pa.Table, decisions: pa.Table) -> dict[tuple[str, int, int], tuple[int, ...]]:
    """(run_id, h, student) -> (root, ..., student), rebuilt from routing parent links."""
    parent = _successful_transfers(routing_events)
    paths: dict[tuple[str, int, int], tuple[int, ...]] = {}
    for d in decisions.to_pylist():
        run_id, h, student = d["run_id"], d["homework_index"], d["student_id"]
        chain = [student]
        while (run_id, h, chain[-1]) in parent:
            chain.append(parent[(run_id, h, chain[-1])])
            if len(chain) > len(parent) + 1:
                raise ValueError(f"cycle in provenance for {(run_id, h, student)}")
        paths[(run_id, h, student)] = tuple(reversed(chain))
    return paths


def flow_counts(routing_events: pa.Table) -> dict[tuple[str, int, int, int], int]:
    """H^(h): (run_id, h, source, receiver) -> number of transmissions."""
    counts: dict[tuple[str, int, int, int], int] = defaultdict(int)
    for r in routing_events.to_pylist():
        if r["transfer_success"]:
            counts[(r["run_id"], r["homework_index"], r["target_id"], r["requester_id"])] += 1
    return dict(counts)


def cascades(decisions: pa.Table) -> list[dict]:
    """Answer cascades (§38): per (run_id, h, root), size = root + every holder of its packet.

    A failed copier's fallback answer holds no packet and belongs to no cascade (docs/09 convention 8).
    """
    groups: dict[tuple[str, int, int], list[int]] = {}
    for d in decisions.to_pylist():
        if d["action"] == "C" and not d["copy_success"]:
            continue
        groups.setdefault((d["run_id"], d["homework_index"], d["root_id"]), []).append(d["depth"])
    return [{"run_id": run_id, "h": h, "root": root, "size": len(depths), "max_depth": max(depths)}
            for (run_id, h, root), depths in sorted(groups.items())]


def homework_trajectories(decisions: pa.Table, state_snapshots: pa.Table) -> dict[tuple[str, int], dict]:
    """Per (run_id, h): N, n_C, n_succ, pC, succ (None without C-choices), reach, K_mean, K_var
    (population variance of K_post), dHK = mean(G_H - K_post). E1 §4 O1-O4."""
    K_post: dict[tuple[str, int, int], float] = {}
    for s in state_snapshots.to_pylist():
        h = _homework_of(s["event_id"])
        if h is not None:
            K_post[(s["run_id"], h, s["student_id"])] = s["K"]
    groups: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for d in decisions.to_pylist():
        groups[(d["run_id"], d["homework_index"])].append(d)
    out = {}
    for (run_id, h), rows in groups.items():
        n = len(rows)
        n_c = sum(1 for d in rows if d["action"] == "C")
        n_succ = sum(1 for d in rows if d["action"] == "C" and d["copy_success"])
        ks = [K_post[(run_id, h, d["student_id"])] for d in rows]
        k_mean = sum(ks) / n
        out[(run_id, h)] = {
            "N": n, "n_C": n_c, "n_succ": n_succ, "pC": n_c / n,
            "succ": n_succ / n_c if n_c else None, "reach": n_succ / n,
            "K_mean": k_mean, "K_var": sum((k - k_mean) ** 2 for k in ks) / n,
            "dHK": sum(d["grade"] - k for d, k in zip(rows, ks)) / n,
        }
    return out


def exam_gaps(decisions: pa.Table, item_outcomes: pa.Table, events: pa.Table) -> dict[tuple[str, int], dict]:
    """Per (run_id, e): h_e, dGK_last = mean_i(G_H[i, h_e] - G_E[i, e]) and dGK_block = mean_i(mean of
    G_H over the homeworks since the previous exam - G_E[i, e]). E1 §4 O5 and secondary."""
    exam_of_event: dict[tuple[str, str], tuple[int, int]] = {}
    for e in events.to_pylist():
        if e["event_type"] == "exam":
            exam_of_event[(e["run_id"], e["event_id"])] = (e["exam_index"], e["homework_index"])
    correct: dict[tuple[str, int, int], list[int]] = defaultdict(lambda: [0, 0])
    for r in item_outcomes.to_pylist():
        if r["mode"] == "exam":
            e_idx, _ = exam_of_event[(r["run_id"], r["event_id"])]
            acc = correct[(r["run_id"], e_idx, r["student_id"])]
            acc[0] += int(r["correct"])
            acc[1] += 1
    G_H = {(d["run_id"], d["homework_index"], d["student_id"]): d["grade"] for d in decisions.to_pylist()}
    exams_by_run: dict[str, list[tuple[int, int]]] = defaultdict(list)
    for (run_id, _), (e_idx, h_e) in exam_of_event.items():
        exams_by_run[run_id].append((e_idx, h_e))
    out = {}
    for run_id, exams in exams_by_run.items():
        previous_h = 0
        for e_idx, h_e in sorted(exams):
            block = range(previous_h + 1, h_e + 1)
            students = sorted(i for (r, e, i) in correct if r == run_id and e == e_idx)
            last, blk = [], []
            for i in students:
                n_correct, n_items = correct[(run_id, e_idx, i)]
                g_e = n_correct / n_items
                last.append(G_H[(run_id, h_e, i)] - g_e)
                blk.append(sum(G_H[(run_id, h, i)] for h in block) / len(block) - g_e)
            out[(run_id, e_idx)] = {"h_e": h_e, "dGK_last": sum(last) / len(last), "dGK_block": sum(blk) / len(blk)}
            previous_h = h_e
    return out


def cascade_extremes(decisions: pa.Table) -> dict[tuple[str, int], tuple[int, int]]:
    """Per (run_id, h): (S_max, L_max). A homework with no cascade gives (0, 0) (E1 §4b.1)."""
    homeworks = {(d["run_id"], d["homework_index"]) for d in decisions.to_pylist()}
    out = {key: (0, 0) for key in homeworks}
    for c in cascades(decisions):
        key = (c["run_id"], c["h"])
        size, depth = out[key]
        out[key] = (max(size, c["size"]), max(depth, c["max_depth"]))
    return out


def route_concentration(routing_events: pa.Table, graph_edges: pa.Table, top_percent: int = 20) -> dict[str, float | None]:
    """C_F per run (E1 §4 O7): flow on the top ceil(top_percent% of 2|E|) directed eligible edges divided by
    total flow over the run. None if the run has no flow or no edges. Runs with neither have no entry."""
    n_edges: Counter = Counter(e["run_id"] for e in graph_edges.to_pylist())
    flows: dict[str, Counter] = defaultdict(Counter)
    for r in routing_events.to_pylist():
        if r["transfer_success"]:
            flows[r["run_id"]][(r["target_id"], r["requester_id"])] += 1
    out: dict[str, float | None] = {}
    for run_id in set(n_edges) | set(flows):
        eligible = 2 * n_edges[run_id]
        total = sum(flows[run_id].values())
        if eligible == 0 or total == 0:
            out[run_id] = None
            continue
        k = -(-eligible * top_percent // 100)  # exact integer ceiling
        ranked = sorted(flows[run_id].values(), reverse=True)
        out[run_id] = sum(ranked[:k]) / total
    return out


def brokerage(routing_events: pa.Table, decisions: pa.Table) -> dict[tuple[str, int], int]:
    """B_i per (run_id, student): number of copied-answer paths in which i is internal (E1 §7, §4b.6)."""
    paths = provenance_paths(routing_events, decisions)
    rows = decisions.to_pylist()
    B = {(d["run_id"], d["student_id"]): 0 for d in rows}
    for d in rows:
        if d["action"] == "C" and d["copy_success"]:
            for node in paths[(d["run_id"], d["homework_index"], d["student_id"])][1:-1]:
                B[(d["run_id"], node)] += 1
    return B


def grades_from_items(item_outcomes: pa.Table) -> dict[tuple[str, int, int], float]:
    """Homework grade = mean of that student's item outcomes: (run_id, h, student) -> grade."""
    totals: dict[tuple[str, int, int], list[int]] = defaultdict(lambda: [0, 0])
    for r in item_outcomes.to_pylist():
        h = _homework_of(r["event_id"])
        if h is None or r["mode"] == "exam":
            continue
        acc = totals[(r["run_id"], h, r["student_id"])]
        acc[0] += int(r["correct"])
        acc[1] += 1
    return {key: correct / n for key, (correct, n) in totals.items()}
