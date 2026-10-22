"""T9 and the alpha reference check: parameter resolution and initial choice probabilities.

docs/02 (derived constants), docs/01 (stage ladder), docs/09 (resolve_params, SimulationControls).
"""
import dataclasses
import math

import numpy as np
import pytest

from classroom_swarm.config import (
    EffectiveParams, Params, RunSpec, SimulationControls, Stage, alpha_from_trajectory, resolve_params,
)
from classroom_swarm.engine import strategy_probabilities


def test_alpha_formula_is_exact():
    assert alpha_from_trajectory(0.5, 0.85, 20) == pytest.approx(0.0584225201, abs=1e-10)


def test_alpha_reference_literal_matches_derivation():
    assert abs(Params().alpha - alpha_from_trajectory(0.5, 0.85, 20)) < 1e-4


def test_alpha_is_never_recomputed_from_K0_or_H():
    # a fixed-alpha robustness run must keep alpha as given (docs/09 decision 3)
    assert resolve_params(Stage.M1, Params(K0=0.4, H=30)).alpha == Params().alpha


LADDER = {  # stage: (eta_Q, beta_P, beta_C, exam->C, exam->E, eta_E) with reference magnitudes
    Stage.M0: (0.0, 0.0, 0.0, False, False, 0.0),
    Stage.M1: (0.2, 0.0, 0.0, False, False, 0.0),
    Stage.M2: (0.2, 0.5, 0.0, False, False, 0.0),
    Stage.M3: (0.2, 0.5, 0.5, False, False, 0.0),
    Stage.M4: (0.2, 0.5, 0.5, True, False, 0.0),
    Stage.M5: (0.2, 0.5, 0.5, True, True, 0.3),
}


@pytest.mark.parametrize("stage", list(Stage))
def test_stage_ladder_resolves_effective_values(stage):
    ep = resolve_params(stage, Params())
    assert isinstance(ep, EffectiveParams)
    got = (ep.eta_Q, ep.beta_P, ep.beta_C, ep.exam_updates_confidence, ep.exam_updates_effort, ep.eta_E)
    assert got == pytest.approx(LADDER[stage])


def test_stage_and_controls_are_not_scientific_parameters():
    names = {f.name for f in dataclasses.fields(Params)}
    assert "stage" not in names and "force_action" not in names
    assert "stage" in {f.name for f in dataclasses.fields(RunSpec)}
    assert "stage" not in {f.name for f in dataclasses.fields(EffectiveParams)}
    assert SimulationControls().force_action is None


def test_run_id_format():
    spec = RunSpec(experiment_id="dev01", replicate=1, family="SBM", R=3, stage=Stage.M1,
                   params=Params(), master_seed=1)
    assert spec.run_id == "dev01/rep0001/SBM/R3/M1"


def test_q0_is_derived_and_unclipped():
    assert resolve_params(Stage.M1, Params()).q0 == pytest.approx(0.35)
    assert resolve_params(Stage.M1, Params(K0=0.1, kappa=0.4)).q0 == pytest.approx(-0.3)


def test_q0_override_wins():
    assert resolve_params(Stage.M1, Params(q0_override=0.0, K0=0.6)).q0 == 0.0


def test_b_C_and_C0():
    ep = resolve_params(Stage.M1, Params(p_C0=0.10, K0=0.5, C0_offset=0.2))
    assert ep.b_C == pytest.approx(math.log(2 * 0.10 / 0.90))
    assert ep.C0 == pytest.approx(0.7)


def test_exposure_mode_is_validated_and_passed_through():
    assert resolve_params(Stage.M2, Params()).exposure == "requests"
    assert resolve_params(Stage.M2, Params(exposure="copying")).exposure == "copying"
    with pytest.raises(ValueError):
        Params(exposure="friends").validate()


def test_params_validate_rejects_odd_mean_degree():
    Params().validate()
    with pytest.raises(ValueError):
        Params(d_bar=5).validate()


def _probs(p_C0, stage, Q_value, n=5, feasible=None):
    ep = resolve_params(stage, Params(p_C0=p_C0))
    Q = np.full((n, 3), Q_value)
    C = np.full(n, 0.5)
    X = np.zeros(n)
    feas = np.ones(n, dtype=bool) if feasible is None else feasible
    return strategy_probabilities(Q, C, X, feas, ep)


@pytest.mark.parametrize("p_C0", [0.01, 0.10, 0.20])
@pytest.mark.parametrize("stage", [Stage.M1, Stage.M3])  # M3: beta_C active, still exact at C = 0.5
def test_initial_copy_probability_is_exactly_pC0(p_C0, stage):
    P = _probs(p_C0, stage, Q_value=0.35)
    np.testing.assert_allclose(P[:, 2], p_C0, rtol=0, atol=1e-12)
    np.testing.assert_allclose(P[:, 0], (1 - p_C0) / 2, rtol=0, atol=1e-12)
    np.testing.assert_allclose(P[:, 1], (1 - p_C0) / 2, rtol=0, atol=1e-12)


def test_uniform_q0_shift_leaves_probabilities_unchanged():
    np.testing.assert_allclose(_probs(0.1, Stage.M1, 0.0), _probs(0.1, Stage.M1, 0.7), rtol=0, atol=1e-12)


def test_infeasible_rows_are_exactly_S():
    ep = resolve_params(Stage.M2, Params())
    Q = np.array([[0.0, 5.0, 50.0], [0.0, 5.0, 50.0]])
    P = strategy_probabilities(Q, np.full(2, 0.5), np.ones(2), np.array([False, True]), ep)
    assert tuple(P[0]) == (1.0, 0.0, 0.0)
    assert P[1, 2] > 0.99
    np.testing.assert_allclose(P.sum(axis=1), 1.0, rtol=0, atol=1e-12)
