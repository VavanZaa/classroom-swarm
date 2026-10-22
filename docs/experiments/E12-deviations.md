# E12 storage correction and complete rerun

2026-09-24. The initial `runs/E12` attempt failed when the AI-use table changed from answer mode to tutor mode. Schema inference gave the unused numeric field a null-only type, which was incompatible with the other mode's numeric values. This was a data-writer defect, not a simulation or parameter change.

All 100 replicate directories were incomplete; none had `complete.json`. No aggregate E12 outcomes were inspected, and no parameters were tuned in response. The partial outputs and original lock remain in `runs/E12`; every originally locked source is archived byte-for-byte under `runs/E12/frozen-source` and was verified against the original hashes before correction.

The correction declares an explicit shared AI-use schema with nullable float fields for answer accuracy and tutor hint strength. A regression test writes both modes to one file and checks exact restoration. `v4_public_ai.py`, all conditions, seeds, equations, metrics and planned contrasts are unchanged. The runner and test source change only for this schema correction and this provenance record.

The complete 2,600-run experiment is restarted with a new lock at `runs/E12r1`. No partial shards are reused. E9r1, E10 and E11 locked sources remain unchanged. Scientific E12 claims must use E12r1 and its manifests, never the partial initial attempt.
