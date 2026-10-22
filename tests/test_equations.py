"""T17–T24: equation conformance with docs/03, checked against hand-computed values.

Each test runs simulate() as a black box on a tiny hand-built graph with a FixedDraws provider, so
every uniform is chosen explicitly. Student 2 is isolated in the 3-student scenarios (it can only
choose S and never interacts). Hand calculations are in the comments. Tolerance 1e-12.
"""
import pyarrow as pa
import pytest

from classroom_swarm.config import SimulationControls, Stage
from classroom_swarm.derive import cascades
from classroom_swarm.engine import simulate

from conftest import FixedDraws, event_index, graph_from_edges, make_spec, snapshots_by_event, table

S, D, C = FixedDraws.S, FixedDraws.D, FixedDraws.C
TOL = 1e-12
PAIR = [(0, 1)]  # 0 - 1, student 2 isolated


def _run(stage, edges, n, draws_kwargs, *, R=1, controls=None, test_tally=False, graph_weights=None, **params):
    base = dict(N=n, M_H=4, M_E=4, F_E=None, d_bar=2, K0=0.5)
    base.update(params)
    spec = make_spec(stage, R=R, family="ER", **base)
    draws = FixedDraws(n, base["M_H"], base["M_E"], R_max=R, **draws_kwargs)
    log = simulate(spec, graph_from_edges(n, edges, weights=graph_weights), draws,
                   controls=controls or SimulationControls(), test_tally=test_tally)
    return log


def _K(log, h, i, kind="homework", exam=None):
    return snapshots_by_event(log)[(kind, h, exam)][i]


def _decision(log, h, i):
    return next(d for d in table(log, "decisions") if d["homework_index"] == h and d["student_id"] == i)


def _items(log, h, i, event_type="homework"):
    events = event_index(log)
    got = [r for r in table(log, "item_outcomes")
           if r["student_id"] == i and events[r["event_id"]]["event_type"] == event_type
           and events[r["event_id"]]["homework_index"] == h]
    got.sort(key=lambda r: r["item"])
    return [r["correct"] for r in got], {r["mode"] for r in got}, got


# ---------------------------------------------------------------- T17 independent learning

def test_T17_independent_learning_uses_post_learning_K():
    # alpha 0.1, E 1: K+ = 0.5 + 0.1 * 0.5 = 0.55. Items thresholded at 0.55, not 0.5:
    # [0.52, 0.54, 0.56, 0.90] -> [T, T, F, F] -> grade 0.5 (at K = 0.5 it would be 0.0)
    log = _run(Stage.M0, PAIR, 3, dict(strategy={1: [S, S, S]}, item={1: {0: [0.52, 0.54, 0.56, 0.90]}}),
               alpha=0.1, H=1)
    assert _K(log, 1, 0)["K"] == pytest.approx(0.55, abs=TOL)
    assert _K(log, 1, 0)["E"] == 1.0
    correct, modes, _ = _items(log, 1, 0)
    assert correct == [True, True, False, False] and modes == {"S"}
    d = _decision(log, 1, 0)
    assert (d["action"], d["grade"], d["cost"]) == ("S", pytest.approx(0.5, abs=TOL), 1)


def test_T17_independent_learning_clips_at_one_and_uses_effort():
    # M5, forced S, alpha 0.9. h1: K = 0.5 + 0.9 * 0.5 = 0.95. Exam 1 all wrong (u = 0.99 > 0.95):
    # G_E = 0 -> E = 1 + 0.3 * 0.7 = 1.21. h2: 0.95 + 0.9 * 1.21 * 0.05 = 1.00445 -> clipped to 1.0
    log = _run(Stage.M5, PAIR, 3, dict(exam={1: {i: [0.99] * 4 for i in range(3)}}),
               controls=SimulationControls(force_action="S"), alpha=0.9, H=2, F_E=1)
    assert _K(log, 1, 0)["K"] == pytest.approx(0.95, abs=TOL)
    assert _K(log, 1, 0, kind="exam", exam=1)["E"] == pytest.approx(1.21, abs=TOL)
    assert _K(log, 2, 0)["K"] == 1.0


# ---------------------------------------------------------------- T18 discussion, T24 frozen pre-state

def test_T18_T24_discussion_with_a_stronger_partner_uses_pre_homework_K():
    # alpha 0.3, chi_C 0. Student 0 does S every homework: 0.5 -> 0.65 -> 0.755 -> 0.8285.
    # Student 1 copies from 0 at h1, h2 (chi_C 0, stays 0.5), then discusses with 0 at h3.
    # h3 uses 0's PRE-homework K = 0.755 (not 0.8285):
    #   K1+ = 0.5 + 0.3 * 0.5 * (1 + 0.255) = 0.68825 ; p = max(0.68825, 0.755) = 0.755
    #   items [0.70, 0.75, 0.76, 0.99] -> [T, T, F, F] -> grade 0.5
    #   (partner's post K would give 0.75; K1+ alone would give 0.0)
    log = _run(Stage.M0, PAIR, 3,
               dict(strategy={1: [S, C, S], 2: [S, C, S], 3: [S, D, S]},
                    item={3: {1: [0.70, 0.75, 0.76, 0.99]}}),
               alpha=0.3, chi_C=0.0, H=3)
    assert [_K(log, h, 0)["K"] for h in (1, 2, 3)] == pytest.approx([0.65, 0.755, 0.8285], abs=TOL)
    assert [_K(log, h, 1)["K"] for h in (1, 2)] == pytest.approx([0.5, 0.5], abs=TOL)
    assert _K(log, 3, 1)["K"] == pytest.approx(0.68825, abs=TOL)
    d = _decision(log, 3, 1)
    assert (d["action"], d["partner_id"]) == ("D", 0)
    assert d["grade"] == pytest.approx(0.5, abs=TOL)
    correct, modes, _ = _items(log, 3, 1)
    assert correct == [True, True, False, False] and modes == {"D"}


def test_T18_discussion_with_a_weaker_partner_has_multiplier_one():
    # h1: 0 does S (0.65), 1 copies (chi_C 0, stays 0.5). h2: 0 discusses with weaker 1:
    #   K0+ = 0.65 + 0.3 * 0.35 * 1 = 0.755 ; p = max(0.755, 0.5) = 0.755
    #   items [0.75, 0.76, 0.10, 0.99] -> [T, F, T, F]
    log = _run(Stage.M0, PAIR, 3,
               dict(strategy={1: [S, C, S], 2: [D, C, S]}, item={2: {0: [0.75, 0.76, 0.10, 0.99]}}),
               alpha=0.3, chi_C=0.0, H=2)
    assert _K(log, 2, 0)["K"] == pytest.approx(0.755, abs=TOL)
    assert _decision(log, 2, 0)["partner_id"] == 1
    assert _items(log, 2, 0)[0] == [True, False, True, False]


def test_T18_discussion_clips_at_one():
    # alpha 0.9: h1 0 -> 0.95, 1 stays 0.5. h2: 1 discusses with 0:
    #   0.5 + 0.9 * 0.5 * (1 + 0.45) = 1.1525 -> clipped to 1.0
    log = _run(Stage.M0, PAIR, 3, dict(strategy={1: [S, C, S], 2: [S, D, S]}), alpha=0.9, chi_C=0.0, H=2)
    assert _K(log, 2, 1)["K"] == 1.0


def test_T26_weighted_discussion_partner_uses_contact_weight_not_hidden_state():
    # Student 0 has sorted neighbours [1, 2]. u=.5 selects 2 under uniform weights, but 1 under 9:1 weights.
    edges = [(0, 1), (0, 2)]
    draws = dict(strategy={1: [D, S, S]}, partner={1: [0.5, 0.0, 0.0]})
    uniform = _run(Stage.M0, edges, 3, draws, H=1)
    weighted = _run(Stage.M0, edges, 3, draws, H=1, graph_weights=(9.0, 1.0))
    assert _decision(uniform, 1, 0)["partner_id"] == 2
    assert _decision(weighted, 1, 0)["partner_id"] == 1


# ---------------------------------------------------------------- T19 successful copy

def test_T19_successful_copy():
    # 0 does S (K+ 0.55): items [0.1, 0.9, 0.2, 0.8] -> [T, F, T, F]. 1 copies from 0 in round 1.
    # 1's own uniforms (opposite pattern) must be ignored. K1+ = 0.5 + 0.2 * 0.1 * 1 * 0.5 = 0.51
    log = _run(Stage.M0, PAIR, 3,
               dict(strategy={1: [S, C, S]},
                    item={1: {0: [0.1, 0.9, 0.2, 0.8], 1: [0.9, 0.1, 0.9, 0.1]}}),
               alpha=0.1, chi_C=0.2, H=1)
    assert _K(log, 1, 1)["K"] == pytest.approx(0.51, abs=TOL)
    d = _decision(log, 1, 1)
    assert (d["action"], d["copy_success"], d["cost"]) == ("C", True, 0)
    assert (d["answer_id"], d["root_id"], d["depth"]) == ("h1-s0", 0, 1)
    assert d["grade"] == pytest.approx(0.5, abs=TOL) and d["reward"] == pytest.approx(0.5, abs=TOL)
    correct, modes, rows = _items(log, 1, 1)
    assert correct == [True, False, True, False] and modes == {"copied"}
    assert all((r["answer_id"], r["root_id"]) == ("h1-s0", 0) for r in rows)


# ---------------------------------------------------------------- T20 failed copy

def test_T20_failed_copy():
    # 0 and 1 both copy; nobody they can reach holds a packet (2 is isolated). R = 3, but each has one
    # neighbour, so one request each. Fallback at the PRE-homework K = 0.5, no learning:
    #   0: [0.49, 0.51, 0.30, 0.70] -> [T, F, T, F] -> 0.5, reward 0.5 - 0.15 = 0.35
    #   1: [0.10, 0.20, 0.30, 0.40] -> all T -> 1.0, reward 0.85
    log = _run(Stage.M0, PAIR, 3,
               dict(strategy={1: [C, C, S]},
                    item={1: {0: [0.49, 0.51, 0.30, 0.70], 1: [0.10, 0.20, 0.30, 0.40]}}),
               R=3, H=1, test_tally=True)
    for i, grade in ((0, 0.5), (1, 1.0)):
        d = _decision(log, 1, i)
        assert _K(log, 1, i)["K"] == 0.5
        assert (d["copy_success"], d["cost"]) == (False, 1)
        assert (d["answer_id"], d["root_id"], d["depth"]) == (f"h1-s{i}", i, 0)
        assert d["grade"] == pytest.approx(grade, abs=TOL)
        assert d["reward"] == pytest.approx(grade - 0.15, abs=TOL)
        assert _items(log, 1, i)[1] == {"fallback"}
    assert _items(log, 1, 0)[0] == [True, False, True, False]
    requests = sorted((r["round"], r["requester_id"], r["target_id"], r["target_had_packet"], r["transfer_success"])
                      for r in table(log, "routing_events"))
    assert requests == [(1, 0, 1, False, False), (1, 1, 0, False, False)]
    assert log.test_tally["H"] == {}
    roots = {c["root"] for c in cascades(pa.table(log.tables["decisions"]))}
    assert roots == {2}  # only the isolated S student's own answer; fallback work is in no cascade


# ---------------------------------------------------------------- T21 reward and Q, T22 confidence

def test_T21_T22_reward_Q_and_confidence():
    # M1 (eta_Q 0.2), path 0 - 1 - 2, q0 = 0.35, C0 = 0.5, eta_C 0.2, kappa 0.15.
    # 0 S: K+ 0.55, items all 0.1 -> grade 1.0, cost 1 -> R = 0.85 -> Q_S = 0.35 + 0.2 * 0.50 = 0.45
    # 1 D with 0 (equal K): K+ 0.55, p 0.55, items [0.1, 0.6, 0.7, 0.8] -> 0.25 -> R = 0.10
    #   -> Q_D = 0.35 + 0.2 * (-0.25) = 0.30
    # 2 C copies from 1 -> 0.25, cost 0 -> R = 0.25 -> Q_C = 0.35 + 0.2 * (-0.10) = 0.33
    # C' = 0.5 + 0.2 * (G - 0.5) -> 0.60, 0.45, 0.45
    log = _run(Stage.M1, [(0, 1), (1, 2)], 3,
               dict(strategy={1: [S, D, C]}, item={1: {0: [0.1] * 4, 1: [0.1, 0.6, 0.7, 0.8]}}),
               alpha=0.1, H=1)
    expected = {
        0: dict(action="S", reward=0.85, Q=(0.45, 0.35, 0.35), C=0.60),
        1: dict(action="D", reward=0.10, Q=(0.35, 0.30, 0.35), C=0.45),
        2: dict(action="C", reward=0.25, Q=(0.35, 0.35, 0.33), C=0.45),
    }
    for i, e in expected.items():
        d = _decision(log, 1, i)
        s = _K(log, 1, i)
        assert d["action"] == e["action"]
        assert d["reward"] == pytest.approx(e["reward"], abs=TOL)
        assert (s["Q_S"], s["Q_D"], s["Q_C"]) == pytest.approx(e["Q"], abs=TOL)
        assert s["C"] == pytest.approx(e["C"], abs=TOL)
    assert _decision(log, 1, 1)["partner_id"] == 0


def test_T22_exposure_counts_distinct_incoming_requesters_only():
    # Edges 0-1, 0-2, 0-3, 1-2; everyone copies, nobody holds; R = 1, all routing u = 0 (first candidate):
    #   0 -> 1, 1 -> 0, 2 -> 0, 3 -> 0
    #   X0 = |{1, 2, 3}| / 3 = 1.0 ; X1 = |{0}| / 2 = 0.5 ; X2 = 0 / 2 = 0.0 ; X3 = 0 / 1 = 0.0
    # (2 and 3 made requests themselves; outgoing requests must not count)
    log = _run(Stage.M0, [(0, 1), (0, 2), (0, 3), (1, 2)], 4, dict(strategy={1: [C, C, C, C]}), H=1)
    X = {i: _K(log, 1, i)["X"] for i in range(4)}
    assert X == pytest.approx({0: 1.0, 1: 0.5, 2: 0.0, 3: 0.0}, abs=TOL)


# ---------------------------------------------------------------- T25 V2 peer exposure (A19)

STAR_PLUS = [(0, 1), (0, 2), (0, 3), (1, 2)]


@pytest.mark.parametrize("exposure,expected", [
    # actions: 0 C, 1 C, 2 S, 3 C. R = 1, routing u = 0 -> 0 asks 1, 1 asks 0, 3 asks 0 (2 is S, asks nobody)
    # V1 "requests": X = distinct incoming requesters / degree -> 0: {1,3}/3, 1: {0}/2, 2: 0/2, 3: 0/1
    ("requests", {0: 2 / 3, 1: 0.5, 2: 0.0, 3: 0.0}),
    # V2 "copying": X = neighbours who chose C / degree -> 0: {1,3}/3, 1: {0}/2, 2: {0,1}/2, 3: {0}/1
    # (student 2 chose S itself: own action never counts; 3 and 2 were asked by nobody but see copying friends)
    ("copying", {0: 2 / 3, 1: 0.5, 2: 1.0, 3: 1.0}),
])
def test_T25_peer_exposure_definition(exposure, expected):
    log = _run(Stage.M0, STAR_PLUS, 4, dict(strategy={1: [C, C, S, C]}), H=1, exposure=exposure)
    X = {i: _K(log, 1, i)["X"] for i in range(4)}
    assert X == pytest.approx(expected, abs=TOL)


def test_T25_v2_exposure_is_zero_for_isolates_and_default_is_v1():
    log = _run(Stage.M0, PAIR, 3, dict(strategy={1: [C, C, S]}), H=1, exposure="copying")
    # 0 and 1 copy and see each other copying; 2 is isolated -> 0
    assert {i: _K(log, 1, i)["X"] for i in range(3)} == pytest.approx({0: 1.0, 1: 1.0, 2: 0.0}, abs=TOL)
    from classroom_swarm.config import Params
    assert Params().exposure == "requests"


# ---------------------------------------------------------------- T23 exams by stage

@pytest.mark.parametrize("stage", list(Stage))
def test_T23_exam_effects_by_stage(stage):
    # Forced S, alpha 0.1, F_E 1. h1: K 0.55, homework all correct (u 0.0) -> C = 0.5 + 0.2 * 0.5 = 0.6.
    # Exam 1 [0.1, 0.2, 0.6, 0.9] at K 0.55 -> 2/4 -> G_E = 0.5.
    #   M0-M3: nothing changes. M4: C = 0.6 + 0.2 * (0.5 - 0.6) = 0.58. M5: also E = 1 + 0.3 * 0.2 = 1.06.
    # h2 learning uses E: K = 0.55 + 0.1 * E * 0.45 -> 0.595 (E 1) or 0.5977 (E 1.06).
    # Exam 2 all correct (u 0.0) -> G_E = 1 -> M5 resets E to 1.
    log = _run(stage, PAIR, 3,
               dict(item={1: {i: [0.0] * 4 for i in range(3)}},
                    exam={1: {i: [0.1, 0.2, 0.6, 0.9] for i in range(3)}, 2: {i: [0.0] * 4 for i in range(3)}}),
               controls=SimulationControls(force_action="S"), alpha=0.1, H=2, F_E=1)
    hw1, ex1 = _K(log, 1, 0), _K(log, 1, 0, kind="exam", exam=1)
    assert hw1["C"] == pytest.approx(0.6, abs=TOL)
    exam_correct, modes, _ = _items(log, 1, 0, event_type="exam")
    assert sum(exam_correct) == 2 and modes == {"exam"}
    if stage <= Stage.M3:
        assert {k: ex1[k] for k in ("K", "C", "E", "Q_S", "Q_D", "Q_C", "X")} == \
               {k: hw1[k] for k in ("K", "C", "E", "Q_S", "Q_D", "Q_C", "X")}
        expected_E = 1.0
    elif stage == Stage.M4:
        assert (ex1["C"], ex1["E"]) == (pytest.approx(0.58, abs=TOL), 1.0)
        expected_E = 1.0
    else:
        assert (ex1["C"], ex1["E"]) == (pytest.approx(0.58, abs=TOL), pytest.approx(1.06, abs=TOL))
        expected_E = 1.06
    assert _K(log, 2, 0)["K"] == pytest.approx(0.55 + 0.1 * expected_E * 0.45, abs=TOL)
    assert _K(log, 2, 0, kind="exam", exam=2)["E"] == 1.0
