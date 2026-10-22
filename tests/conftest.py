"""Shared helpers for the V1 test suite (docs/06 T1–T16, API in docs/09).

Engine imports happen inside the helpers, so that before the engine exists each test
module fails on its own import instead of the whole session failing here.
"""
from __future__ import annotations

MASTER_SEED = 20260918
EXPERIMENT = "test"


def make_spec(stage=None, *, R=3, family="SBM", replicate=1, master_seed=MASTER_SEED, **param_overrides):
    from classroom_swarm.config import Params, RunSpec, Stage

    return RunSpec(
        experiment_id=EXPERIMENT,
        replicate=replicate,
        family=family,
        R=R,
        stage=Stage.M1 if stage is None else stage,
        params=Params(**param_overrides),
        master_seed=master_seed,
    )


def make_graph(spec):
    from classroom_swarm.graphs import generate_graph
    from classroom_swarm.rng import graph_seed

    return generate_graph(spec.family, spec.params, graph_seed(spec.master_seed, spec.replicate, spec.family))


def make_draws(spec, R_max=3):
    from classroom_swarm.rng import Draws

    p = spec.params
    return Draws(spec.master_seed, spec.replicate, p.N, p.M_H, p.M_E, R_max=R_max)


def run(spec, *, graph=None, R_max=3, controls=None, test_tally=False):
    """simulate() with the replicate's graph and shared draws. Returns (log, graph)."""
    from classroom_swarm.config import SimulationControls
    from classroom_swarm.engine import simulate

    graph = make_graph(spec) if graph is None else graph
    log = simulate(spec, graph, make_draws(spec, R_max), controls=controls or SimulationControls(),
                   test_tally=test_tally)
    return log, graph


def graph_from_edges(N, edges, family="ER", weights=None):
    """Hand-built Graph (docs/09 fields) for isolate and routing tests."""
    from classroom_swarm.graphs import Graph

    canon = tuple(sorted({(min(u, v), max(u, v)) for u, v in edges}))
    nbrs = [set() for _ in range(N)]
    for u, v in canon:
        nbrs[u].add(v)
        nbrs[v].add(u)
    return Graph(family=family, N=N, generator_params={}, seed=0, edges=canon,
                 neighbors=tuple(tuple(sorted(s)) for s in nbrs), community=None,
                 weights=None if weights is None else tuple(weights))


class FixedDraws:
    """DrawProvider (docs/09) with explicitly chosen uniforms, for the T17–T24 equation tests.

    strategy / partner: {h: [u per student]}. item: {h: {student: [u per item]}}.
    routing: {h: [[u per student] per round]}. exam: {e: {student: [u per item]}}.
    Unset values use the defaults below. In M0, and at h = 1 in any stage, the strategy uniforms
    map onto actions as u < 0.45 -> S, u < 0.90 -> D, otherwise C (P = 0.45 / 0.45 / 0.10).
    """
    S, D, C = 0.2, 0.6, 0.95

    def __init__(self, N, M_H, M_E, R_max, *, strategy=None, partner=None, item=None, routing=None,
                 exam=None, exploration=None, sharing=None, traits=None,
                 default_item=0.5, default_exam=0.5):
        self.N, self.M_H, self.M_E, self.R_max = N, M_H, M_E, R_max
        self._strategy, self._partner = strategy or {}, partner or {}
        self._item, self._routing, self._exam = item or {}, routing or {}, exam or {}
        self._exploration, self._sharing = exploration or {}, sharing or {}
        self._traits = traits
        self._default_item, self._default_exam = default_item, default_exam

    def strategy(self, h):
        import numpy as np
        return np.array(self._strategy.get(h, [self.S] * self.N), dtype=float)

    def partner(self, h):
        import numpy as np
        return np.array(self._partner.get(h, [0.0] * self.N), dtype=float)

    def item(self, h):
        import numpy as np
        arr = np.full((self.M_H, self.N), self._default_item)
        for i, vals in self._item.get(h, {}).items():
            arr[:, i] = vals
        return arr

    def routing(self, h):
        import numpy as np
        return np.array(self._routing.get(h, [[0.0] * self.N] * self.R_max), dtype=float)

    def exam(self, e):
        import numpy as np
        arr = np.full((self.M_E, self.N), self._default_exam)
        for i, vals in self._exam.get(e, {}).items():
            arr[:, i] = vals
        return arr

    def exploration(self, h):
        import numpy as np
        return np.array(self._exploration.get(h, [0.5] * self.N), dtype=float)

    def traits(self):
        import numpy as np
        return np.zeros((3, self.N)) if self._traits is None else np.array(self._traits, dtype=float)

    def sharing(self, h):
        import numpy as np
        return np.array(self._sharing.get(h, [[0.0] * self.N] * self.R_max), dtype=float)


def rows(table_columns: dict) -> list[dict]:
    """Columnar {column: [values]} -> list of row dicts."""
    if not table_columns:
        return []
    n = len(next(iter(table_columns.values())))
    return [{c: vals[k] for c, vals in table_columns.items()} for k in range(n)]


def table(log, name) -> list[dict]:
    return rows(log.tables[name])


def event_index(log) -> dict:
    """event_id -> event row (event_id is treated as opaque)."""
    return {e["event_id"]: e for e in table(log, "events")}


def snapshots_by_event(log) -> dict:
    """(event_type, homework_index, exam_index) -> {student_id: snapshot row}."""
    events = event_index(log)
    out: dict = {}
    for s in table(log, "state_snapshots"):
        e = events[s["event_id"]]
        out.setdefault((e["event_type"], e["homework_index"], e["exam_index"]), {})[s["student_id"]] = s
    return out


def ordered_snapshots(log) -> list[tuple[dict, dict]]:
    """[(event row, {student_id: snapshot row})] in event sequence order."""
    events = sorted(table(log, "events"), key=lambda e: e["seq"])
    by_event: dict = {}
    for s in table(log, "state_snapshots"):
        by_event.setdefault(s["event_id"], {})[s["student_id"]] = s
    return [(e, by_event[e["event_id"]]) for e in events]




# Portfolio source-only asset profile
# Original assertions remain intact. Enable only after restoring the matching
# research artifacts with --run-research-assets.
import pytest as _portfolio_pytest

@_portfolio_pytest.hookimpl(specname="pytest_addoption")
def pytest_portfolio_asset_options(parser):
    parser.addoption("--run-research-assets", action="store_true", default=False,
                     help="Run checks requiring excluded local research archives/indexes")

@_portfolio_pytest.hookimpl(specname="pytest_collection_modifyitems")
def pytest_portfolio_asset_collection(config, items):
    if config.getoption("--run-research-assets"):
        return
    requires_assets = {'tests/test_e21_study_mechanisms.py::test_teacher_resources_do_not_change_with_class_size_or_assignment', 'tests/test_e21_study_mechanisms.py::test_profiles_preserve_assignment_students_and_semantic_draws', 'tests/test_e27_teacher_belief_check.py::test_cap_does_not_change_physical_alpha_or_rewards', 'tests/test_e21_study_mechanisms.py::test_single_session_and_ai_measurement_scopes_are_declared', 'tests/test_declared_experiments.py::test_historical_sources_still_match_e13_lock', 'tests/test_e27_teacher_belief_check.py::test_all_candidates_below_conditional_physical_learning_ceiling', 'tests/test_e19_teacher_studies.py::test_preserved_historical_engines_and_e18_report_match_hashes', 'tests/test_e27_teacher_belief_check.py::test_candidates_stay_inside_previous_bounds', 'tests/test_e21_study_mechanisms.py::test_focal_composition_states_remain_fixed_and_reward_probe_keeps_intrinsic', 'tests/test_e21_study_mechanisms.py::test_fixed_design_covers_previous_cases_and_eleven_primary_contrasts', 'tests/test_e21_study_mechanisms.py::test_protocol_bridge_is_separate_from_new_features'}
    for item in items:
        if item.nodeid in requires_assets:
            item.add_marker(_portfolio_pytest.mark.skip(reason='requires the excluded historical campaign locks/run archives; use --run-research-assets after restoring them'))
