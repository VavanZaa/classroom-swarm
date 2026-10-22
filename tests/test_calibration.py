"""T10: under forced-S with E = 1, K follows K_T = 1 - (1 - K0)(1 - alpha)^T exactly. docs/02 §31, docs/09."""
import pytest

from classroom_swarm.config import SimulationControls, Stage, alpha_from_trajectory

from conftest import make_spec, run, snapshots_by_event, table

FORCED_S = SimulationControls(force_action="S")


@pytest.mark.parametrize("alpha", [0.0584, alpha_from_trajectory(0.5, 0.85, 20)])
def test_T10_knowledge_trajectory_is_exact(alpha):
    spec = make_spec(Stage.M1, alpha=alpha)
    log, _ = run(spec, controls=FORCED_S)
    snaps = snapshots_by_event(log)
    assert all(d["action"] == "S" for d in table(log, "decisions"))
    for h in range(1, spec.params.H + 1):
        expected = 1 - (1 - spec.params.K0) * (1 - alpha) ** h
        for s in snaps[("homework", h, None)].values():
            assert s["K"] == pytest.approx(expected, abs=1e-12)
            assert s["E"] == 1.0


def test_T10_reaches_the_target_when_alpha_is_derived():
    alpha = alpha_from_trajectory(0.5, 0.85, 20)
    log, _ = run(make_spec(Stage.M1, alpha=alpha), controls=FORCED_S)
    final = snapshots_by_event(log)[("homework", 20, None)]
    assert all(s["K"] == pytest.approx(0.85, abs=1e-12) for s in final.values())


def test_forced_S_is_recorded_and_logs_model_probabilities():
    spec = make_spec(Stage.M1, p_C0=0.10)
    log, graph = run(spec, controls=FORCED_S)
    assert log.manifest["controls"]["force_action"] == "S"
    for d in table(log, "decisions"):
        if d["homework_index"] == 1 and graph.degree[d["student_id"]] > 0:
            assert d["P_C"] == pytest.approx(0.10, abs=1e-12)  # model's probability, not the forced action

    normal, _ = run(spec)
    assert normal.manifest["controls"]["force_action"] is None
