# E9 execution deviation: roundoff correction

2026-09-24. The initial locked execution at `runs/E9` failed its exact nondecreasing-knowledge invariant in replicates 29, 62 and 65; 97 other replicate shards completed while the worker pool drained. No aggregate behavioral or treatment results had been analyzed or inspected.

Diagnostic reproduction of replicate 29/no_check found K decreases of -5.551115123125783e-17 for inactive students at homework 1. The mathematically equivalent update `1 - (1 - K) * residual` recomputed inactive values and introduced a one-ULP decrease. It was replaced by `K + (1 - K) * (1 - residual)`, which preserves inactive values exactly and only adds nonnegative increments. No parameter, policy, experiment condition, seed, analysis outcome or sample size changed.

A regression test reproduces that seed and verifies both monotonicity and exact preservation for students with no learning activities. The original lock and partial raw logs are preserved. The entire 2,600-run study is rerun into `runs/E9r1` with a new source lock; no old/new shards are mixed. The preregistration remains unchanged. Report results only from E9r1, with this deviation disclosed.
