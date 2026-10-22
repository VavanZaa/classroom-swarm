"""E2b plan against its locked preregistration."""
import json
from pathlib import Path

from classroom_swarm import e2, e2b

REPO = Path(__file__).resolve().parents[1]


def test_constants_match_the_lock_record():
    lock = json.loads((REPO / e2b.LOCK).read_text("utf-8"))
    assert (e2b.MASTER_SEED, e2b.SMOKE_SEED, e2b.BOOT_SEED) == (lock["master_seed"], lock["smoke_master_seed"],
                                                               lock["bootstrap_seed"])
    assert len(e2b.REPLICATES) == lock["replicates"] == 400
    assert len(e2b.CONDITIONS) * len(e2b.REPLICATES) == lock["runs"]
    assert e2b.verify_lock(REPO / e2b.PREREG, REPO / e2b.LOCK) == lock["sha256"]


def test_conditions_repeat_e2_plausible_max_exactly():
    assert e2b.CONDITIONS["E2b-plausible-max"] == e2.CONDITIONS["E2-plausible-max"]
    assert e2b.CONDITIONS["E2b-ref"] == {}
    plan = e2b.contrasts()
    assert [(c["a"], c["b"]) for c in plan] == [(("E2b-plausible-max",), ("E2b-ref",))]
    assert e2b.MASTER_SEED not in (e2.MASTER_SEED, 918001)  # new data, not a reuse of E1/E2 seeds
