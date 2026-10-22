"""E3 plan against its locked preregistration."""
import json
from pathlib import Path

from classroom_swarm import e3
from classroom_swarm.config import Params, Stage

REPO = Path(__file__).resolve().parents[1]


def test_constants_match_the_lock_record():
    lock = json.loads((REPO / e3.LOCK).read_text("utf-8"))
    assert (e3.MASTER_SEED, e3.SMOKE_SEED, e3.BOOT_SEED) == (lock["master_seed"], lock["smoke_master_seed"],
                                                             lock["bootstrap_seed"])
    assert len(e3.CONDITIONS) == lock["conditions"] == 11 and len(e3.REPLICATES) == lock["replicates"] == 400
    assert e3.verify_lock(REPO / e3.PREREG, REPO / e3.LOCK) == lock["sha256"]


def test_conditions_vary_only_exposure_and_beta():
    conds = e3.conditions()
    assert len(conds) == 11 and all(stage == Stage.M2 for _, stage, _ in conds)
    for label, _, params in conds:
        params.validate()
        changed = {k for k, v in vars(params).items() if v != getattr(Params(), k)}
        assert changed <= {"exposure", "beta_P"}
    assert e3.CONDITIONS["E3-v2-b0"] == {"exposure": "copying", "beta_P": 0.0}
    assert e3.CONDITIONS["E3-v1-b4.5"] == {"exposure": "requests", "beta_P": 4.5}
    assert e3.CONDITIONS["E3-v2-b6"] == {"exposure": "copying", "beta_P": 6.0}


def test_contrast_plan():
    plan = e3.contrasts()
    assert len(plan) == 15
    assert [c["a"][0] for c in plan if c["name"].startswith("A")] == [f"E3-v2-b{b:g}" for b in e3.BETAS]
    assert all(c["b"] == ("E3-v2-b0",) for c in plan if c["name"][0] in "BC")
    assert {c["name"] for c in plan if not c["stress"]} == {"A: V2-V1 b0.5", "A: V2-V1 b1.5", "B: V2 b0.5-b0",
                                                            "B: V2 b1.5-b0", "C: V1 b0.5-b0", "C: V1 b1.5-b0"}
