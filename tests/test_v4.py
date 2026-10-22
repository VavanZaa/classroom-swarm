"""A22 equation, information, timing and reconstruction checks."""
from dataclasses import replace

import numpy as np
import pytest

from classroom_swarm.graphs import _from_edges, generate_er
from classroom_swarm.rng import Draws
from classroom_swarm.v3 import V3Params, V3RunSpec, simulate_v3
from classroom_swarm.v4 import (
    V4Params, V4Draws, activity_scores, feedback_update, simulate_v4, simulate_legacy,
    summarize, validate_log,
)


def setup_run(**changes):
    p = replace(V4Params(N=6, H=7, ticks=12), **changes)
    graph = generate_er(6, 3, 71)
    return p, graph, V4Draws(82, 0, 6, p.items, p.exam_items)


def test_v4_semantic_draws_reproducible_and_independent():
    a, b = V4Draws(9, 1, 4, 10, 30), V4Draws(9, 1, 4, 10, 30)
    b.tensor("target", 4)
    np.testing.assert_array_equal(a.tensor("choice", 2), b.tensor("choice", 2))
    assert not np.array_equal(a.tensor("choice", 2), a.tensor("target", 2))
    np.testing.assert_array_equal(a.legacy.traits(), Draws(9, 1, 4, 10, 30, 3).traits())


def test_v4_feedback_equations():
    p = V4Params(feedback_mode="recalibrate")
    c, r = feedback_update(.8, .5, .2, .8, p)
    assert c == pytest.approx(.5) and r == .5
    _, constructive = feedback_update(.8, .5, .2, .8, replace(p, feedback_mode="constructive"))
    _, withdrawal = feedback_update(.8, .5, .2, .8, replace(p, feedback_mode="withdrawal"))
    assert constructive > .5 > withdrawal
    assert feedback_update(.2, .2, .8, .2, replace(p, feedback_mode="withdrawal"))[1] > .2


def test_v4_choice_uses_only_private_inputs_and_masks():
    scores = activity_scores(V4Params(), .5, .5, np.full(4, .5), .15, 0., False,
                             False, (.5, .5), False, 12)
    assert set(scores) == {"attempt", "wait"}
    late = activity_scores(V4Params(), .5, .5, np.full(4, .5), .15, .7, True,
                          False, (.5, .5), True, 1)
    assert set(late) == {"wait", "submit"}


def test_v4_reproducibility_and_raw_integrity():
    p, g, d = setup_run()
    a, b = simulate_v4(p, g, d), simulate_v4(p, g, V4Draws(82, 0, 6, 10, 30))
    assert a.tables == b.tables
    validate_log(a)
    assert summarize(a)["K_final"] == pytest.approx(np.mean([
        r["K"] for r in a.tables["students"] if r["homework"] == p.H]))


def test_v4_no_feedback_effect_before_release():
    p, g, d = setup_run(feedback_mode="none")
    a = simulate_v4(p, g, d)
    b = simulate_v4(replace(p, feedback_mode="recalibrate", feedback_delay=1), g, d)
    assert [r for r in a.tables["students"] if r["homework"] <= 6] == [
        r for r in b.tables["students"] if r["homework"] <= 6]
    assert all(r["homework"] == 7 for r in b.tables["feedback"])
    assert all(r["K_before"] == r["K_after"] for r in b.tables["feedback"])


def test_v4_feedback_beyond_horizon_never_released():
    p, g, d = setup_run(H=6, feedback_delay=4)
    assert simulate_v4(p, g, d).tables["feedback"] == []


def test_v41_fixed_confidence_and_control():
    p, g, d = setup_run(self_assessment=False, feedback_mode="none")
    log = simulate_v4(p, g, d)
    initial = {r["student"]: r["K0"] for r in log.tables["traits"]}
    assert all(r["C"] == initial[r["student"]] and r["control"] == .5
               for r in log.tables["students"])


def test_v4_isolates_and_no_social_events():
    p, _, d = setup_run()
    g = _from_edges("ER", 6, {}, 0, [])
    log = simulate_v4(p, g, d)
    assert not log.tables["requests"]
    assert all(r["action"] not in {"hint", "answer", "help_hint", "help_answer"}
               for r in log.tables["events"])
    validate_log(log)


def test_v4_exact_packet_transfer_and_no_copy_learning():
    p, g, d = setup_run(H=20)
    log = simulate_v4(p, g, d)
    packets = {r["packet_id"]: r for r in log.tables["packets"]}
    copies = [r for r in log.tables["events"] if r["action"] == "answer_receive"]
    assert copies
    for row in copies:
        assert row["K_before"] == row["K_after"]
        assert row["packet_id"] in packets
    hints = [r for r in log.tables["events"] if r["action"] == "hint_receive"]
    assert hints and all(r["K_before"] == r["K_after"] for r in hints)


def test_v4_exam_probes_do_not_modify_trajectories_without_feedback():
    p, g, d = setup_run(feedback_mode="none")
    a, b = simulate_v4(p, g, d), simulate_v4(replace(p, exam_every=100), g, d)
    assert a.tables["students"] == b.tables["students"]


def test_v4_helper_time_control_still_valid():
    p, g, d = setup_run(helper_time=False)
    validate_log(simulate_v4(p, g, d))


def test_v4_frozen_beliefs_and_disabled_actions():
    p, g, d = setup_run(eta_access=0, allow_hint=False, allow_answer=False, allow_check=False)
    log = simulate_v4(p, g, d)
    assert not log.tables["requests"]
    assert all(r["action"] not in {"hint", "answer", "check"} for r in log.tables["events"])


def test_v4_private_access_disabled_with_real_requests():
    p, g, d = setup_run(H=20, eta_access=0)
    log = simulate_v4(p, g, d)
    assert log.tables["requests"]
    assert all(r["A_before"] == r["A_after"] == .5 for r in log.tables["requests"])


def test_v4_no_packet_available_before_creation():
    p, g, d = setup_run(H=20)
    log = simulate_v4(p, g, d)
    packets = {r["packet_id"]: r for r in log.tables["packets"]}
    for event in log.tables["events"]:
        if event["action"] == "answer_receive":
            assert packets[event["packet_id"]]["tick"] <= event["start"] < event["end"]
    for h in range(1, p.H + 1):
        successes = [r for r in log.tables["requests"] if r["homework"] == h and r["success"]]
        received = [r for r in log.tables["events"] if r["homework"] == h and r["action"] in {"hint_receive", "answer_receive"}]
        assert len(successes) == len(received)


def test_v4_all_experiment_conditions_are_declared_and_valid():
    from classroom_swarm.e9 import conditions
    plan = conditions()
    assert len(plan) == len({n for n, _, _ in plan}) == 26
    for _, _, p in plan:
        if p is not None:
            p.validate()


def test_v4_no_learning_preserves_knowledge_exactly_regression():
    from classroom_swarm.graphs import generate_graph
    from classroom_swarm.rng import graph_seed
    p = V4Params(allow_check=False)
    graph = generate_graph("SBM", V3Params(), graph_seed(924041, 29, "SBM"))
    log = simulate_v4(p, graph, V4Draws(924041, 29, 30, 10, 30))
    validate_log(log)
    for row in log.tables["students"]:
        if row["attempt"] == 0 and row["help_count"] == 0:
            assert row["K"] == row["K_before"]


def test_v4_legacy_delegates_exactly():
    p = V3Params(N=6, H=2, d_bar=2)
    spec = V3RunSpec("test", 0, "ER", 3, p, 3)
    g = generate_er(6, 2, 5)
    d = Draws(3, 0, 6, 10, 30, 3)
    assert simulate_legacy(spec, g, d).tables == simulate_v3(spec, g, d).tables


@pytest.mark.parametrize("changes", [{"ticks":33}, {"N":0}, {"misattribution":-1},
    {"temperature":0}, {"feedback_mode":"invented"}, {"feedback_delay":-1}])
def test_v4_rejects_invalid_parameters(changes):
    with pytest.raises(ValueError):
        replace(V4Params(), **changes).validate()
