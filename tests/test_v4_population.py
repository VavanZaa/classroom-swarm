"""A27: configurable populations with A26 default parity and paired trait draws."""
from dataclasses import replace

import numpy as np
import pytest

from classroom_swarm.graphs import generate_er
from classroom_swarm.v4_corrected import CorrectedParams, simulate_corrected
from classroom_swarm.v4_public_ai import PublicAIDraws
from classroom_swarm.v4_population import (
    PopulationParams, simulate_population, validate_population_log,
)


def run(p):
    return simulate_population(
        p, generate_er(p.N, 3, 71),
        PublicAIDraws(82, 0, p.N, p.items, p.exam_items),
    )


@pytest.mark.parametrize("mode", ["none", "answer", "tutor"])
def test_default_population_reproduces_a26_on_every_raw_table(mode):
    old = CorrectedParams(N=8, H=8, ai_mode=mode)
    new = PopulationParams(N=8, H=8, ai_mode=mode)
    graph = generate_er(8, 3, 71)
    reference = simulate_corrected(old, graph, PublicAIDraws(82, 0, 8, 10, 30))
    log = run(new)
    assert log.tables == reference.tables
    validate_population_log(log)


@pytest.mark.parametrize("level", [0.0, 0.85, 1.0])
def test_zero_spread_sets_every_students_initial_knowledge_and_confidence(level):
    log = run(PopulationParams(N=8, H=1, K0=level, K0_sd=0.0))
    assert all(row["K0"] == level for row in log.tables["traits"])
    assert all(row["K_before"] == row["C_before"] == level
               for row in log.tables["students"])
    validate_population_log(log)


def test_mean_and_spread_change_knowledge_without_changing_other_traits():
    base = PopulationParams(N=30, H=1, K0=0.5, K0_sd=0.05)
    low, high = run(replace(base, K0=0.15)), run(replace(base, K0=0.85))
    narrow, wide = run(base), run(replace(base, K0_sd=0.20))
    for first, second in ((low, high), (narrow, wide)):
        for a, b in zip(first.tables["traits"], second.tables["traits"]):
            assert (a["alpha"], a["kappa"], a["degree"]) == (
                b["alpha"], b["kappa"], b["degree"])
        assert first.tables["graph"] == second.tables["graph"]
        assert first.tables["contacts"] == second.tables["contacts"]
    assert all(a["K0"] < b["K0"] for a, b in
               zip(low.tables["traits"], high.tables["traits"]))
    assert np.std([r["K0"] for r in wide.tables["traits"]]) > np.std(
        [r["K0"] for r in narrow.tables["traits"]])


@pytest.mark.parametrize("mean,spread", [(0.0, 0.1), (1.0, 0.1), (0.85, 0.05)])
def test_bounded_samples_manifest_and_reproducibility(mean, spread):
    p = PopulationParams(N=8, H=3, K0=mean, K0_sd=spread)
    log = run(p)
    assert all(0 <= r["K0"] <= 1 for r in log.tables["traits"])
    assert log.manifest["params"]["K0"] == mean
    assert log.manifest["params"]["K0_sd"] == spread
    assert log.manifest["model"] == "A27-v4.3-population"
    assert log.tables == run(p).tables
    validate_population_log(log)


@pytest.mark.parametrize("field,value", [
    ("K0", -0.1), ("K0", 1.1), ("K0", float("nan")),
    ("K0", float("inf")), ("K0", True), ("K0", "0.8"),
    ("K0_sd", -0.1), ("K0_sd", float("nan")),
    ("K0_sd", float("inf")), ("K0_sd", True), ("K0_sd", "0.1"),
])
def test_invalid_population_parameters_rejected(field, value):
    with pytest.raises(ValueError, match=field):
        run(PopulationParams(**{field: value}))
