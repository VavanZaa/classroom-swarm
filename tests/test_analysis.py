"""E1 analysis layer on constructed fixtures (docs/experiments/E1-preregistration.md §4-§8, §4b).

No simulation output is used here except in the broker-null determinism test. Every expected
value is computed by hand in the comments.
"""
import json
import math
from pathlib import Path

import numpy as np
import pyarrow as pa
import pytest

from classroom_swarm import e1
from classroom_swarm.analysis import (
    SCALARS, bootstrap_indices, boundary_precision_check, broker_scores, broker_share, classify, convergence,
    paired_contrast, parse_run_id, precision_check, proxy_check, run_summaries, spearman, tipping_threshold,
    tipping_threshold_ci,
)
from classroom_swarm.config import Params, RunSpec, Stage
from classroom_swarm.derive import brokerage, cascade_extremes, exam_gaps, homework_trajectories, route_concentration
from classroom_swarm.experiment import run_broker_null
from classroom_swarm.graphs import generate_graph
from classroom_swarm.records import COLUMNS
from classroom_swarm.rng import graph_seed
from classroom_swarm.storage import ARROW_SCHEMAS

RUN = "x/rep0001/SBM/R3/M1"
REPO = Path(__file__).resolve().parents[1]


def tbl(name, rows):
    return pa.table({c: [r.get(c) for r in rows] for c in COLUMNS[name]}, schema=ARROW_SCHEMAS[name])


def dec(h, i, action, grade, *, success=None, root=None, depth=0, run=RUN):
    root = i if root is None else root
    return dict(run_id=run, event_id=f"h{h}", homework_index=h, student_id=i, feasible_S=True,
                feasible_D=True, feasible_C=True, P_S=0.45, P_D=0.45, P_C=0.10, action=action,
                partner_id=None, grade=grade, reward=grade, cost=0 if success else 1,
                copy_success=success, answer_id=f"h{h}-s{root}", root_id=root, depth=depth)


def snap(event_id, i, K, run=RUN):
    return dict(run_id=run, event_id=event_id, student_id=i, K=K, C=0.5, E=1.0, Q_S=0.35, Q_D=0.35,
                Q_C=0.35, X=0.0)


def ev(event_id, seq, kind, h, e=None, run=RUN):
    exam = kind == "exam"
    return dict(run_id=run, event_id=event_id, seq=seq, event_type=kind, homework_index=h, exam_index=e,
                diagnostic_only=True if exam else None, exam_updates_confidence=False if exam else None,
                exam_updates_effort=False if exam else None)


def exam_items(event_id, i, pattern, run=RUN):
    return [dict(run_id=run, event_id=event_id, student_id=i, item=q, correct=bool(c), mode="exam",
                 answer_id=None, root_id=None) for q, c in enumerate(pattern)]


def rt(h, rnd, req, tgt, success, *, root=None, sender_depth=None, run=RUN):
    ok = dict(answer_id=f"h{h}-s{root}", root_id=root, sender_depth=sender_depth,
              receiver_depth=None if sender_depth is None else sender_depth + 1)
    none = dict(answer_id=None, root_id=None, sender_depth=None, receiver_depth=None)
    return dict(run_id=run, homework_index=h, round=rnd, requester_id=req, target_id=tgt,
                target_had_packet=success, transfer_success=success, **(ok if success else none))


def edges(pairs, run=RUN):
    return [dict(run_id=run, u=u, v=v, weight=1.0) for u, v in pairs]


# ---- fixture A: N = 3, H = 2, exam after h2 --------------------------------------------------
# h1: s0 S 0.8 ; s1 copies s0 (success, depth 1) 0.8 ; s2 C fails 0.4.   K_post = 0.60, 0.50, 0.50
# h2: s0 S 1.0 ; s1 S 0.6 ; s2 D 0.4.                                    K_post = 0.70, 0.60, 0.55
# exam e1 (after h2): s0 3/4, s1 2/4, s2 1/4. Edges 0-1, 1-2.
DEC_A = [dec(1, 0, "S", 0.8), dec(1, 1, "C", 0.8, success=True, root=0, depth=1), dec(1, 2, "C", 0.4, success=False),
         dec(2, 0, "S", 1.0), dec(2, 1, "S", 0.6), dec(2, 2, "D", 0.4)]
SNAP_A = [snap("h1", i, k) for i, k in enumerate((0.60, 0.50, 0.50))] + \
         [snap("h2", i, k) for i, k in enumerate((0.70, 0.60, 0.55))]
EV_A = [ev("init", 0, "init", None), ev("h1", 1, "homework", 1), ev("h2", 2, "homework", 2), ev("e1", 3, "exam", 2, 1)]
ITEMS_A = (exam_items("e1", 0, [True, True, True, False]) + exam_items("e1", 1, [True, True, False, False])
           + exam_items("e1", 2, [True, False, False, False]))
ROUTE_A = [rt(1, 1, 1, 0, True, root=0, sender_depth=0), rt(1, 1, 2, 1, False)]
TABLES_A = {"decisions": tbl("decisions", DEC_A), "state_snapshots": tbl("state_snapshots", SNAP_A),
            "events": tbl("events", EV_A), "item_outcomes": tbl("item_outcomes", ITEMS_A),
            "routing_events": tbl("routing_events", ROUTE_A), "graph_edges": tbl("graph_edges", edges([(0, 1), (1, 2)]))}


def test_homework_trajectories():
    t = homework_trajectories(TABLES_A["decisions"], TABLES_A["state_snapshots"])
    h1, h2 = t[(RUN, 1)], t[(RUN, 2)]
    # h1: pC 2/3, succ 1/2, reach 1/3, K mean 1.6/3, pop var 0.0066667/3, dHK mean(0.2, 0.3, -0.1)
    assert (h1["N"], h1["n_C"], h1["n_succ"]) == (3, 2, 1)
    assert h1["pC"] == pytest.approx(2 / 3) and h1["succ"] == pytest.approx(0.5) and h1["reach"] == pytest.approx(1 / 3)
    assert h1["K_mean"] == pytest.approx(1.6 / 3) and h1["K_var"] == pytest.approx(0.0066667 / 3, abs=1e-7)
    assert h1["dHK"] == pytest.approx(0.4 / 3)
    # h2: no copying -> succ NA; K mean 1.85/3; pop var 0.0116667/3; dHK mean(0.3, 0.0, -0.15)
    assert h2["pC"] == 0.0 and h2["succ"] is None and h2["reach"] == 0.0
    assert h2["K_mean"] == pytest.approx(1.85 / 3) and h2["K_var"] == pytest.approx(0.0116667 / 3, abs=1e-7)
    assert h2["dHK"] == pytest.approx(0.05)


def test_exam_gaps_last_and_block():
    # N = 2, H = 4, exams after h2 (e1) and h4 (e2).
    # G_H s0: .5 .7 .6 .9 ; s1: .3 .5 .4 .4.  Exams: e1 s0 .5, s1 .25 ; e2 s0 .75, s1 .5
    run = "y/rep0001/ER/R1/M0"
    grades = {0: (0.5, 0.7, 0.6, 0.9), 1: (0.3, 0.5, 0.4, 0.4)}
    decisions = tbl("decisions", [dec(h, i, "S", g[h - 1], run=run) for i, g in grades.items() for h in range(1, 5)])
    events = tbl("events", [ev("init", 0, "init", None, run=run), ev("h1", 1, "homework", 1, run=run),
                            ev("h2", 2, "homework", 2, run=run), ev("e1", 3, "exam", 2, 1, run=run),
                            ev("h3", 4, "homework", 3, run=run), ev("h4", 5, "homework", 4, run=run),
                            ev("e2", 6, "exam", 4, 2, run=run)])
    items = tbl("item_outcomes", exam_items("e1", 0, [1, 1, 0, 0], run) + exam_items("e1", 1, [1, 0, 0, 0], run)
                + exam_items("e2", 0, [1, 1, 1, 0], run) + exam_items("e2", 1, [1, 1, 0, 0], run))
    g = exam_gaps(decisions, items, events)
    # last:  e1 mean(.7-.5, .5-.25) = .225 ; e2 mean(.9-.75, .4-.5) = .025
    # block: e1 mean(.6-.5, .4-.25) = .125 ; e2 mean(.75-.75, .4-.5) = -.05
    assert g[(run, 1)]["h_e"] == 2 and g[(run, 2)]["h_e"] == 4
    assert g[(run, 1)]["dGK_last"] == pytest.approx(0.225) and g[(run, 2)]["dGK_last"] == pytest.approx(0.025)
    assert g[(run, 1)]["dGK_block"] == pytest.approx(0.125) and g[(run, 2)]["dGK_block"] == pytest.approx(-0.05)


def test_cascade_extremes_including_empty_homework():
    # h1: root 0 holds + s1 copied (size 2, depth 1); s2 failed (no cascade). h2: three size-1 cascades.
    # h3: everyone copies and fails -> no cascade -> (0, 0) (§4b.1)
    rows = DEC_A + [dec(3, i, "C", 0.5, success=False) for i in range(3)]
    ex = cascade_extremes(tbl("decisions", rows))
    assert ex[(RUN, 1)] == (2, 1) and ex[(RUN, 2)] == (1, 0) and ex[(RUN, 3)] == (0, 0)


def test_route_concentration_eligible_edges_and_na():
    # 5 edges -> 10 directed eligible -> k = 2. Flows 0->1 x3, 1->2 x1, 4->0 x2: top 2 = 5 of 6.
    ring = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 4)]
    flows = [rt(h, 1, 1, 0, True, root=0, sender_depth=0) for h in (1, 2, 3)] + \
            [rt(4, 1, 2, 1, True, root=1, sender_depth=0)] + [rt(h, 1, 0, 4, True, root=4, sender_depth=0) for h in (5, 6)]
    runs = {"a/rep0001/SBM/R3/M1": (ring, flows), "b/rep0001/SBM/R3/M1": (ring, [rt(1, 1, 1, 0, False)]),
            "c/rep0001/SBM/R3/M1": ([], [])}
    ev_rows, e_rows = [], []
    for run, (es, fs) in runs.items():
        e_rows += edges(es, run)
        ev_rows += [{**f, "run_id": run} for f in fs]
    cf = route_concentration(tbl("routing_events", ev_rows), tbl("graph_edges", e_rows))
    assert cf["a/rep0001/SBM/R3/M1"] == pytest.approx(5 / 6)
    assert cf["b/rep0001/SBM/R3/M1"] is None     # no flow -> NA
    assert cf.get("c/rep0001/SBM/R3/M1") is None  # no edges and no flow: no rows at all -> absent = NA


def test_route_concentration_top_k_on_a_larger_graph():
    # 15 edges -> 30 directed -> k = ceil(0.2 * 30) = 6. (Checked: for every even count below 400 the float
    # ceil(0.2 * n) equals the exact integer ceiling, so this isn't a float edge case, just a k > 1 case.)
    # Flows: seven distinct directed edges with flows 7,6,5,4,3,2,1 -> top 6 = 27 of 28.
    path = [(i, i + 1) for i in range(15)]
    flows = []
    for n, (u, v) in enumerate(path[:7]):
        flows += [rt(h, 1, v, u, True, root=u, sender_depth=0) for h in range(1, 8 - n)]
    cf = route_concentration(tbl("routing_events", flows), tbl("graph_edges", edges(path)))
    assert cf[RUN] == pytest.approx(27 / 28)


def test_brokerage_counts_internal_positions_of_every_path():
    # chain h1: 0 S -> 1 (r1) -> 2 (r2) -> 3 (r3); 4 fails. Paths [0,1], [0,1,2], [0,1,2,3]:
    # B1 = 2 (internal in two paths), B2 = 1, others 0 (§4b.6)
    decisions = tbl("decisions", [dec(1, 0, "S", 0.8), dec(1, 1, "C", 0.8, success=True, root=0, depth=1),
                                  dec(1, 2, "C", 0.8, success=True, root=0, depth=2),
                                  dec(1, 3, "C", 0.8, success=True, root=0, depth=3),
                                  dec(1, 4, "C", 0.2, success=False)])
    routes = tbl("routing_events", [rt(1, 1, 1, 0, True, root=0, sender_depth=0), rt(1, 2, 2, 1, True, root=0, sender_depth=1),
                                    rt(1, 3, 3, 2, True, root=0, sender_depth=2), rt(1, 1, 4, 3, False)])
    assert brokerage(routes, decisions) == {(RUN, 0): 0, (RUN, 1): 2, (RUN, 2): 1, (RUN, 3): 0, (RUN, 4): 0}


def test_parse_run_id():
    assert parse_run_id("E1/rep0042/WS/R1/M3") == {"experiment_id": "E1", "replicate": 42, "family": "WS",
                                                  "R": 1, "stage": "M3"}


def test_run_summaries_on_fixture_A():
    (s,) = run_summaries(TABLES_A, early=(1, 1), late=(2, 2))
    assert set(SCALARS) <= set(s)
    assert (s["run_id"], s["replicate"], s["family"], s["R"], s["stage"]) == (RUN, 1, "SBM", 3, "M1")
    expected = {
        "pC_late": 0.0, "pC_change": -2 / 3, "succ_late": None, "K_final": 1.85 / 3,
        "VarK_final": 0.0116667 / 3, "dHK_late": 0.05, "dHK_mean": (0.4 / 3 + 0.05) / 2,
        # exam after h2: last = mean(1.0-.75, .6-.5, .4-.25); block over h1-h2 = mean(.9-.75, .7-.5, .4-.25)
        "dGK_last": 0.5 / 3, "dGK_block": 0.5 / 3,
        "Smax_mean": 1.5, "Lmax_mean": 0.5, "reach": 1 / 6,
        "CF": 1.0,  # 2 edges -> 4 directed -> k = 1; single flow 0->1
        "P_C_last": 0.0,
        "tipped": 0.0,  # pC_late 0 is not above 0.5
    }
    for key, value in expected.items():
        if value is None:
            assert s[key] is None, key
        else:
            assert s[key] == pytest.approx(value, abs=1e-7), key


def _summaries(values_a, values_b, a=("M1", 3, "SBM"), b=("M0", 3, "SBM"), outcome="x"):
    rows = []
    for rep, (va, vb) in enumerate(zip(values_a, values_b), start=1):
        for (stage, R, fam), v in ((a, va), (b, vb)):
            rows.append({"replicate": rep, "stage": stage, "R": R, "family": fam, outcome: v})
    return rows


def test_paired_contrast_drops_na_and_uses_shared_resamples():
    # diffs [1, 2, 2, NA] -> estimate 5/3, n 3. Resample rows -> nanmeans [5/3, 1, 2, NaN(all NA, excluded)]
    rows = _summaries([1.0, 2.0, 3.0, None], [0.0, 0.0, 1.0, 1.0])
    boot = np.array([[0, 1, 2, 3], [0, 0, 0, 0], [1, 1, 2, 2], [3, 3, 3, 3]])
    c = paired_contrast(rows, "x", ("M1", 3, "SBM"), ("M0", 3, "SBM"), boot)
    lo, hi = np.percentile([5 / 3, 1.0, 2.0], [2.5, 97.5])
    assert (c["n"], c["estimate"]) == (3, pytest.approx(5 / 3))
    assert (c["lo"], c["hi"]) == (pytest.approx(lo), pytest.approx(hi))
    with pytest.raises(ValueError):
        paired_contrast(rows, "x", ("M1", 3, "SBM"), ("M0", 3, "SBM"), boot[:, :3])  # replicate count mismatch


def test_paired_contrast_can_key_conditions_by_other_fields():
    # E2 conditions share stage/R/family and differ by experiment_id (the condition label)
    rows = [{"replicate": r, "experiment_id": label, "x": v}
            for r, (va, vb) in enumerate([(3.0, 1.0), (5.0, 2.0)], start=1)
            for label, v in (("E2-kappa0.40", va), ("E2-ref", vb))]
    boot = np.array([[0, 1], [1, 1]])
    c = paired_contrast(rows, "x", ("E2-kappa0.40",), ("E2-ref",), boot, key=("experiment_id",))
    assert (c["n"], c["estimate"]) == (2, pytest.approx(2.5))


@pytest.mark.parametrize("lo,hi,delta,adequate", [
    (0.00, 0.01, 0.02, True),     # half-width 0.005 = delta/4 exactly -> adequate
    (0.00, 0.0102, 0.02, False),  # half-width 0.0051 > 0.005
    (float("nan"), float("nan"), 0.02, False),
])
def test_precision_check(lo, hi, delta, adequate):
    out = precision_check({"lo": lo, "hi": hi}, delta)
    assert out["adequate"] is adequate and out["limit"] == pytest.approx(delta / 4)


@pytest.mark.parametrize("lo,hi,adequate", [
    (0.43, 0.45, True),     # far beyond +delta: wide or not, the reading can't change
    (-0.01, 0.015, True),   # inside +-delta (negligible)
    (0.005, 0.015, True),   # inside, excludes 0 (detected below delta)
    (0.01, 0.03, False),    # contains +delta
    (-0.03, -0.01, False),  # contains -delta
    (-0.05, 0.05, False),   # contains both
    (0.02, 0.03, True),     # endpoint exactly at delta does not count as crossing
    (float("nan"), 0.1, False),
])
def test_boundary_precision_check(lo, hi, adequate):
    assert boundary_precision_check({"lo": lo, "hi": hi}, 0.02)["adequate"] is adequate


def test_tipping_threshold_interpolates_first_crossing():
    # shares cross 0.5 between 3.5 (0.2) and 4.0 (0.6): 3.5 + 0.3/0.4 * 0.5 = 3.875
    assert tipping_threshold([3.0, 3.5, 4.0, 4.5], [0.0, 0.2, 0.6, 1.0]) == (pytest.approx(3.875), "interpolated")
    assert tipping_threshold([3.0, 3.5], [0.7, 0.9]) == (3.0, "below_grid")
    assert tipping_threshold([3.0, 3.5], [0.1, 0.2]) == (None, "above_grid")
    assert tipping_threshold([3.0, 3.5, 4.0], [0.0, 0.5, 1.0]) == (pytest.approx(3.5), "interpolated")


def test_tipping_threshold_ci_uses_shared_resamples():
    # 4 replicates; tipped at beta 3 / 4 / 5: rep1 0/0/1, rep2 0/1/1, rep3 0/1/1, rep4 0/0/1
    # shares 0, 0.5, 1 -> threshold exactly 4.0
    tipped = {3.0: [0, 0, 0, 0], 4.0: [0, 1, 1, 0], 5.0: [1, 1, 1, 1]}
    rows = [{"replicate": r + 1, "experiment_id": f"b{b:g}", "tipped": float(v)}
            for b, vals in tipped.items() for r, v in enumerate(vals)]
    labels = [(b, f"b{b:g}") for b in tipped]
    boot = np.array([[0, 1, 2, 3], [1, 1, 2, 2], [0, 0, 3, 3]])  # shares at 4.0: 0.5, 1.0, 0.0
    out = tipping_threshold_ci(rows, labels, boot)
    assert out["threshold"] == pytest.approx(4.0) and out["status"] == "interpolated"
    # resample thresholds: 4.0; 3.5 (0 at 3, 1.0 at 4 -> 3 + 0.5); 4.5 (0 at 4, 1 at 5 -> 4.5)
    lo, hi = np.percentile([4.0, 3.5, 4.5], [2.5, 97.5])
    assert (out["lo"], out["hi"]) == (pytest.approx(lo), pytest.approx(hi))
    assert out["shares"] == {3.0: 0.0, 4.0: 0.5, 5.0: 1.0}


def test_bootstrap_indices_are_seeded_and_shaped():
    a, b = bootstrap_indices(7, B=50, seed=918100), bootstrap_indices(7, B=50, seed=918100)
    assert a.shape == (50, 7) and np.array_equal(a, b) and a.min() >= 0 and a.max() <= 6


@pytest.mark.parametrize("lo,hi,label,magnitude", [
    (0.03, 0.05, "detected", "above_delta"),
    (-0.05, -0.03, "detected", "above_delta"),
    (0.005, 0.015, "detected", "below_delta"),
    (0.01, 0.03, "detected", "straddles_delta"),
    (-0.01, 0.015, "negligible", None),
    (-0.01, 0.05, "inconclusive", None),
    (float("nan"), float("nan"), "not_estimable", None),
])
def test_classify(lo, hi, label, magnitude):
    assert classify(lo, hi, 0.02) == (label, magnitude)


def test_spearman_with_ties():
    assert spearman([1, 2, 3, 4], [10, 20, 30, 40]) == pytest.approx(1.0)
    assert spearman([1, 2, 3, 4], [40, 30, 20, 10]) == pytest.approx(-1.0)
    # ranks x [1, 2.5, 2.5, 4], y [1, 2, 3, 4] -> 4.5 / sqrt(4.5 * 5)
    assert spearman([1, 2, 2, 3], [1, 2, 3, 4]) == pytest.approx(4.5 / math.sqrt(22.5))


def test_proxy_check_uses_condition_means():
    rows = []
    for rep in (1, 2):
        for k, stage in enumerate(("M0", "M1", "M2")):
            rows.append({"replicate": rep, "stage": stage, "R": 3, "family": "SBM",
                         "dGK_last": 0.1 * k + 0.01 * rep, "dHK_late": 0.2 * k})
    out = proxy_check(rows, threshold=0.8)
    assert out["n_conditions"] == 3 and out["rho"] == pytest.approx(1.0) and out["adequate"] is True


def test_convergence_rule():
    boot = np.array([[0, 1, 2, 3, 4, 5], [5, 5, 5, 5, 5, 5], [0, 0, 0, 0, 0, 0]])
    stable = convergence([1.0] * 6, boot, statistic="mean", tail=2)
    assert stable["passed"] is True and stable["movement"] == 0.0
    # running means at n = 5, 6: 0 and 1 -> movement 1; boot means [1, 6, 0]
    moving = convergence([0, 0, 0, 0, 0, 6], boot, statistic="mean", tail=2)
    lo, hi = np.percentile([1.0, 6.0, 0.0], [2.5, 97.5])
    assert moving["movement"] == pytest.approx(1.0) and moving["half_width"] == pytest.approx((hi - lo) / 2)
    assert moving["passed"] is False  # 1.0 is not below 0.1 x 2.85 = 0.285
    med = convergence([1, 2, 3, 4, 5, 6], boot, statistic="median", tail=2)
    assert med["final"] == pytest.approx(3.5)


def test_broker_scores_and_share():
    # s0: null [1,2,3,2] mean 2, sample sd sqrt(2/3): Z = 1/sqrt(2/3), p = (1 + 1)/5
    # s1: null all 0, obs 0 -> Z NA, p = 5/5 ; s2: null all 0, obs 5 -> Z NA, excess 5, p = 1/5
    nulls = [{0: 1, 1: 0, 2: 0}, {0: 2, 1: 0, 2: 0}, {0: 3, 1: 0, 2: 0}, {0: 2, 1: 0, 2: 0}]
    s = broker_scores({0: 3, 1: 0, 2: 5}, nulls)
    assert s[0]["Z"] == pytest.approx(1 / math.sqrt(2 / 3)) and s[0]["p"] == pytest.approx(0.4)
    assert s[1]["Z"] is None and s[1]["p"] == pytest.approx(1.0) and s[1]["excess"] == 0
    assert s[2]["Z"] is None and s[2]["excess"] == 5 and s[2]["p"] == pytest.approx(0.2)
    assert broker_share(s) == 0.0
    # L = 19 all-zero nulls: an observed broker gets p = 1/20 = 0.05 <= 0.05
    s19 = broker_scores({0: 4, 1: 0, 2: 0}, [{0: 0, 1: 0, 2: 0}] * 19)
    assert s19[0]["p"] == pytest.approx(0.05) and broker_share(s19) == pytest.approx(1 / 3)


def test_e1_constants_match_the_lock_record():
    lock = json.loads((REPO / "docs/experiments/E1-lock.json").read_text("utf-8"))
    assert (e1.MASTER_SEED, e1.SMOKE_SEED, e1.BOOT_SEED) == (lock["master_seed"], lock["smoke_master_seed"], lock["bootstrap_seed"])
    assert len(e1.REPLICATES) == lock["replicates"] and len(e1.REPLICATES) * 36 == lock["runs"]
    assert (e1.EARLY, e1.LATE, e1.L_NULL) == ((1, 5), (16, 20), 200)
    assert set(e1.CONFIRMATORY) | set(e1.SECONDARY) <= set(e1.DELTA) | {"VarK_final"}


def test_e1_contrast_plan():
    plan = e1.contrasts()
    primary = [c for c in plan if c["tier"] == "primary"]
    assert [(c["name"], c["a"], c["b"]) for c in primary] == [
        ("P1", ("M1", 3, "SBM"), ("M0", 3, "SBM")),
        ("P2", ("M1", 3, "SBM"), ("M1", 1, "SBM")),
        ("P3", ("M2", 3, "SBM"), ("M1", 3, "SBM"))]
    assert len([c for c in plan if c["tier"] == "secondary"]) == 30 + 18 + 24


def test_verify_lock(tmp_path):
    prereg, lock = REPO / "docs/experiments/E1-preregistration.md", REPO / "docs/experiments/E1-lock.json"
    assert e1.verify_lock(prereg, lock) == json.loads(lock.read_text("utf-8"))["sha256"]
    tampered = tmp_path / "prereg.md"
    tampered.write_bytes(prereg.read_bytes() + b"\nedited\n")
    with pytest.raises(RuntimeError):
        e1.verify_lock(tampered, lock)


def test_broker_null_runner_is_deterministic():
    base = Params(H=3)
    graph = generate_graph("SBM", base, graph_seed(5, 1, "SBM"))
    specs = [RunSpec("t", 1, "SBM", 3, stage, base, 5) for stage in (Stage.M0, Stage.M1)]
    a = run_broker_null(specs, graph, L=2, master_seed=5)
    b = run_broker_null(specs, graph, L=2, master_seed=5)
    assert a == b and set(a) == {"M0", "M1"}
    assert all(len(member) == 30 and all(isinstance(v, int) and v >= 0 for v in member.values())
               for members in a.values() for member in members)
    assert all(len(members) == 2 for members in a.values())
