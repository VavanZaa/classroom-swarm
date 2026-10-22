---
type: experiment-deviation
id: E6-D1
date: 2026-09-20
status: RECORDED BEFORE RESUME
---
# E6 deviation D1 · Technical memory interruption and non-overwriting resume

The first full E6 process stopped with `MemoryError` while constructing structural replicate 143.
Structural replicates 1–142 had already been fully written; all 12 canonical files plus each manifest
were present. Replicate 143 was not written. The factorial block and all derived analysis had not begun,
and no scientific outcome was inspected.

The resume implementation preserves and reads complete replicate directories without overwriting them,
starts simulation at the first missing replicate, and explicitly releases Python and Arrow memory after
each replicate/shard. It retains every locked condition, seed, replicate count, outcome, bootstrap,
threshold and analysis rule. Manifests preserve the clean code commit that generated each raw file; the
final report records D1 and the resume commit.

This is a technical execution deviation only. Any incomplete directory would block resume rather than
being silently accepted.

## D2 · Second cumulative-memory interruption

The first resume reached structural replicate 289, then stopped while converting a large Arrow item
table during summary reconstruction. Again, the failed replicate was not written, the factorial and
derived analyses had not begun, and no outcome was inspected. Memory release within one long process
was insufficient.

The second resume uses an isolated subprocess for each replicate. Each worker either reads an existing
complete raw replicate or generates the first missing one, writes only a small checkpoint summary, and
then exits so all memory is returned to the operating system. Factorial workers similarly isolate one
replicate's 16 shards. Scientific design, raw schema, seeds and analysis remain unchanged; existing raw
directories are never overwritten.
