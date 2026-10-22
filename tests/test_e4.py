"""E4 plan against its locked preregistration."""
import json
from collections import Counter
from pathlib import Path

from classroom_swarm import e4
from classroom_swarm.config import Params, Stage

REPO = Path(__file__).resolve().parents[1]


def test_constants_match_the_lock_record():
    lock = json.loads((REPO / e4.LOCK).read_text("utf-8"))
    assert (e4.MASTER_SEED, e4.SMOKE_SEED, e4.BOOT_SEED) == (lock["master_seed"], lock["smoke_master_seed"],
                                                             lock["bootstrap_seed"])
    assert len(e4.CONDITIONS) == lock["conditions"] == 40 and len(e4.contrasts()) == lock["contrasts"] == 58
    assert len(e4.REPLICATES) * len(e4.CONDITIONS) == lock["runs"]
    assert e4.PRECISION_RULE == lock["precision_rule"] == "boundary"
    assert e4.DELTA["tipped"] == 0.10 and "tipped" in e4.CONFIRMATORY
    assert e4.verify_lock(REPO / e4.PREREG, REPO / e4.LOCK) == lock["sha256"]


def test_conditions_cover_the_three_blocks_without_duplicates():
    conds = e4.conditions()
    assert len({c[0] for c in conds}) == 40
    assert all(p.exposure == "copying" and set(k for k, v in vars(p).items() if v != getattr(Params(), k))
               <= {"exposure", "beta_P"} for _, _, p, _, _ in conds)
    cells = Counter((stage, fam, r) for _, stage, _, fam, r in conds)
    assert cells[(Stage.M2, "SBM", 3)] == 8          # block F (also T's SBM R3 cell and S's M2 row)
    assert all(cells[(Stage.M2, f, r)] == 4 for f in ("ER", "WS") for r in (1, 3))
    assert cells[(Stage.M2, "SBM", 1)] == 4
    assert all(cells[(s, "SBM", 3)] == 4 for s in (Stage.M3, Stage.M4, Stage.M5))


def test_contrast_plan_blocks():
    plan = e4.contrasts()
    assert Counter(c["block"] for c in plan) == {"F": 7, "T": 39, "S": 12}
    labels = set(e4.CONDITIONS)
    assert all(c["a"][0] in labels and c["b"][0] in labels for c in plan)
    assert {c["b"][0] for c in plan if c["block"] == "F"} == {"E4-F-b0"}
