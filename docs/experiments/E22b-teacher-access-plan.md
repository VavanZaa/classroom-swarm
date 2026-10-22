---
type: experiment-preregistration-deviation
updated: 2026-10-07
---
# E22b — Correct duplicated exam-access cost in teacher study setup

During E22 execution, before aggregate outcomes were inspected, a source review found that the intended .6 exam access cost had been entered both in each exam design and in the general participation cost. A32 correctly adds these fields, so E22's total cost is 1.2. This is a study setup error, not an engine defect. E22's locked source, declarations and every result are retained and completed. Its teacher-reward default describes a high-access-cost stress case, not the intended .6 setup. See `effort_runtime.py` assessment access-cost calculation.

E22b is separately frozen before its first simulation: only the eight teacher-incentive conditions are repeated across the same 24 paired cohorts (192 classrooms), same global IDs, seeds, opportunities, parameters and assumptions as E22. Only the duplicated general `test_preparation.participation_cost` changes .6 → 0 where participation is enabled; each exam's `access_cost=.6` remains. The two nonparticipation profiles are exact unchanged controls. The correction and test are included in the source lock. No choice depends on a realized effect.

All three teacher-paper headline estimands are retained: reward-linked potential score, unrelated potential score and reward-linked participation. Pointwise paired 95% intervals and Bonferroni simultaneous intervals over these three outcomes are reported. Comparison with E22 uses whole-cohort paired changes because the same semantic draws are preserved; it identifies this one cost correction only. Field units and participation threshold remain uncalibrated; the corrected cost cannot be called empirically validated.

Every raw file is hash-verified, reloaded and numerically audited. Full sensitivity profiles (reward 1 and 20; reward-20 format without participation; conceptual-only) stay visible, with no engine/source edits. Use this corrected protocol for interpreting the intended teacher-study comparison and show the E22 high-cost result as a retained limitation/control. E22b was declared after E22 began, so it is a documented protocol correction, not an original independent preregistration or a new blind external validation.
