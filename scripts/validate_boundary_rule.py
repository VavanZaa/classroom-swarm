"""Validate the boundary precision rule on synthetic data BEFORE any preregistration uses it.

Rule under test (analysis.boundary_precision_check): a paired contrast is adequate iff its 95% bootstrap
CI contains neither +delta nor -delta. Real code path: analysis.paired_contrast -> the rule. delta = 0.02,
paired differences iid N(mu, sigma), 100 datasets per case.

Pass criteria, fixed before the first run:
  (a) far beyond delta but noisy (mu = 5 delta, sigma = 4 delta, n = 200): new rule passes >= 95/100,
      the old half-width rule passes <= 5/100 (the E3 failure mode).
  (b) true effect exactly at delta (mu = delta, sigma = delta, n = 200): passes <= 10/100 (undecidable).
  (c) near the boundary, responds to n (mu = 1.3 delta, sigma = 3 delta): n = 200 passes < 50/100,
      n = 3200 passes >= 95/100.
  (d) null effect (mu = 0, sigma = delta, n = 200): passes >= 95/100 (a precise "negligible").

    .venv\\Scripts\\python.exe scripts/validate_boundary_rule.py
"""
import numpy as np

from classroom_swarm.analysis import boundary_precision_check, bootstrap_indices, paired_contrast, precision_check

DELTA = 0.02
rng = np.random.default_rng(20260919)
boots = {}


def rate(mu, sigma, n, rule):
    boot = boots.setdefault(n, bootstrap_indices(n, B=2000, seed=11))
    passes = 0
    for _ in range(100):
        diffs = rng.normal(mu, sigma, n)
        rows = [{"replicate": r + 1, "stage": s, "R": 3, "family": "SBM", "x": v}
                for r, d in enumerate(diffs) for s, v in (("A", float(d)), ("B", 0.0))]
        c = paired_contrast(rows, "x", ("A", 3, "SBM"), ("B", 3, "SBM"), boot)
        passes += (boundary_precision_check(c, DELTA) if rule == "boundary" else precision_check(c, DELTA))["adequate"]
    return passes


a_new, a_old = rate(5 * DELTA, 4 * DELTA, 200, "boundary"), rate(5 * DELTA, 4 * DELTA, 200, "halfwidth")
b = rate(DELTA, DELTA, 200, "boundary")
c200, c3200 = rate(1.3 * DELTA, 3 * DELTA, 200, "boundary"), rate(1.3 * DELTA, 3 * DELTA, 3200, "boundary")
d = rate(0.0, DELTA, 200, "boundary")
print(f"(a) far beyond delta, noisy:  boundary rule {a_new}/100, half-width rule {a_old}/100")
print(f"(b) effect exactly at delta:  {b}/100")
print(f"(c) near boundary:            n=200 {c200}/100, n=3200 {c3200}/100")
print(f"(d) null effect:              {d}/100")
ok = a_new >= 95 and a_old <= 5 and b <= 10 and c200 < 50 and c3200 >= 95 and d >= 95
print("VALID: all four criteria met" if ok else "INVALID: at least one criterion failed")
raise SystemExit(0 if ok else 1)
