"""E2 plan against its locked preregistration, and the one-factor condition runner."""
import json
from pathlib import Path

import pyarrow.compute as pc
import pytest

from classroom_swarm import e2
from classroom_swarm.config import Params, Stage
from classroom_swarm.experiment import run_conditions
from classroom_swarm.storage import read_table

REPO = Path(__file__).resolve().parents[1]


def test_constants_match_the_lock_record():
    lock = json.loads((REPO / "docs/experiments/E2-lock.json").read_text("utf-8"))
    assert (e2.MASTER_SEED, e2.SMOKE_SEED, e2.BOOT_SEED) == (lock["master_seed"], lock["smoke_master_seed"],
                                                             lock["bootstrap_seed"])
    assert len(e2.CONDITIONS) == lock["conditions"] and len(e2.REPLICATES) * len(e2.CONDITIONS) == lock["runs"]
    assert e2.verify_lock(REPO / lock["preregistration"], REPO / "docs/experiments/E2-lock.json") == lock["sha256"]


def test_conditions_are_single_changes_except_plausible_max():
    conds = e2.conditions()
    assert [label for label, _, _ in conds][0] == "E2-ref" and len(conds) == 14
    assert all(stage == Stage.M2 and "/" not in label for label, stage, _ in conds)
    for label, _, params in conds:
        params.validate()
        changed = {k for k, v in vars(params).items() if v != getattr(Params(), k)}
        assert changed == set(e2.CONDITIONS[label])
        if label not in ("E2-ref", "E2-plausible-max"):
            assert len(changed) == 1
    assert e2.CONDITIONS["E2-plausible-max"] == {"beta_P": 1.5, "kappa": 0.40, "eta_Q": 0.40, "p_C0": 0.20}


def test_contrast_plan():
    plan = e2.contrasts()
    assert len(plan) == 13 and all(c["b"] == ("E2-ref",) for c in plan)
    assert {c["name"] for c in plan if c["stress"]} == {"E2-betaP3", "E2-betaP6"}


def test_run_conditions_shares_graph_and_draws(tmp_path):
    base = Params(H=3)
    conds = [("t-ref", Stage.M2, base), ("t-eta", Stage.M2, Params(H=3, eta_Q=0.4))]
    rep = run_conditions(conds, 1, 11, tmp_path)
    edges = read_table(rep, "graph_edges")
    per_run = {r: {(e["u"], e["v"]) for e in edges.filter(pc.equal(edges["run_id"], r)).to_pylist()}
               for r in ("t-ref/rep0001/SBM/R3/M2", "t-eta/rep0001/SBM/R3/M2")}
    assert per_run["t-ref/rep0001/SBM/R3/M2"] == per_run["t-eta/rep0001/SBM/R3/M2"]
    dec = [d for d in read_table(rep, "decisions").to_pylist() if d["homework_index"] == 1]
    acts = {(d["run_id"].split("/")[0], d["student_id"]): d["action"] for d in dec}
    assert all(acts[("t-ref", i)] == acts[("t-eta", i)] for i in range(30))  # h1 differs only after learning
    with pytest.raises(ValueError):
        run_conditions([("a", Stage.M2, base), ("a", Stage.M2, base)], 1, 11, tmp_path / "x")
    with pytest.raises(ValueError):  # R above R_max
        run_conditions([("a", Stage.M2, base, "SBM", 5)], 1, 11, tmp_path / "z")


def test_run_conditions_per_condition_family_and_R(tmp_path):
    base = Params(H=3)
    conds = [("s3", Stage.M2, base, "SBM", 3), ("s1", Stage.M2, base, "SBM", 1), ("er", Stage.M2, base, "ER", 3)]
    rep = run_conditions(conds, 1, 11, tmp_path)
    runs = sorted({r["run_id"] for r in read_table(rep, "decisions").to_pylist()})
    assert runs == ["er/rep0001/ER/R3/M2", "s1/rep0001/SBM/R1/M2", "s3/rep0001/SBM/R3/M2"]
    edges = read_table(rep, "graph_edges").to_pylist()
    by_run = {}
    for e in edges:
        by_run.setdefault(e["run_id"], set()).add((e["u"], e["v"]))
    assert by_run["s3/rep0001/SBM/R3/M2"] == by_run["s1/rep0001/SBM/R1/M2"] != by_run["er/rep0001/ER/R3/M2"]
    rounds = {r["round"] for r in read_table(rep, "routing_events").to_pylist() if r["run_id"].startswith("s1/")}
    assert rounds <= {1}
    with pytest.raises(ValueError):
        run_conditions([("a", Stage.M2, base), ("b", Stage.M2, Params(H=3, N=20))], 1, 11, tmp_path / "y")
