"""Validate the precision adequacy rule on synthetic data BEFORE it is used in a preregistration.

Rule under test: a paired contrast is adequately precise iff its 95% bootstrap CI half-width <= delta/4.
It runs through the real code path (analysis.paired_contrast + analysis.precision_check) on iid paired
differences ~ N(0.01, sigma), delta = 0.02. Theory: half-width ~ 1.96 sigma / sqrt(n), so the rule should
pass for sigma <= 0.25 delta sqrt(n) / 1.96 (n=200: sigma <= 1.80 delta; n=800: sigma <= 3.61 delta), and
a failing case must turn into a passing one when n grows. The E1 rule failed that last property.

    .venv\\Scripts\\python.exe scripts/validate_precision_rule.py
"""
import numpy as np

from classroom_swarm.analysis import bootstrap_indices, paired_contrast, precision_check

DELTA = 0.02
rng = np.random.default_rng(20260918)
results = {}
for n in (200, 800):
    boot = bootstrap_indices(n, B=2000, seed=7)
    for sigma_in_delta in (1.0, 1.5, 2.0, 3.0):
        passes = 0
        for _ in range(100):
            diffs = rng.normal(0.01, sigma_in_delta * DELTA, n)
            rows = [{"replicate": r + 1, "stage": s, "R": 3, "family": "SBM", "x": v}
                    for r, d in enumerate(diffs) for s, v in (("A", float(d)), ("B", 0.0))]
            c = paired_contrast(rows, "x", ("A", 3, "SBM"), ("B", 3, "SBM"), boot)
            passes += precision_check(c, DELTA)["adequate"]
        results[(n, sigma_in_delta)] = passes
        theory = "pass" if sigma_in_delta <= 0.25 * np.sqrt(n) / 1.96 else "fail"
        print(f"n={n:4d}  sigma={sigma_in_delta:.1f} delta  theory {theory}: rule passed {passes}/100")

ok = (results[(200, 1.0)] >= 95 and results[(200, 3.0)] <= 5 and results[(800, 3.0)] >= 95
      and results[(200, 2.0)] <= 5 and results[(800, 2.0)] >= 95)
print("VALID: passes when precise, fails when not, and responds to n" if ok else "INVALID")
raise SystemExit(0 if ok else 1)
