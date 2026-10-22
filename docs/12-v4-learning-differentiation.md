# A23: activity-specific learning, V4.2-L

Requested 2026-09-24: make knowledge differences between students' learning activities more apparent. This is a separately identified exploratory extension, not a correction to locked A22/E9 results. Never select parameters because they produce the desired gap.

## Mechanism and interface

The A22 `check` activity reveals a packet's score through a reliable rubric, without reconstructing an answer or explaining a solution. Nevertheless, A22 awards it half an independent attempt's learning rate. A23 separates this informational benefit from competence acquisition.

`LearningParams(V4Params)` adds `check_learning_fraction: float = 0.0` in [0,1] and `align_check_value: bool = True`. A completed check has rate `fraction * alpha_i / 6`. At zero, it still takes two ticks, reveals the score, updates private confidence, and can change subsequent choices, but does not directly increase K. An actual subsequent attempt still learns. The check score's intrinsic-learning term `.5 * learning_value * control * (1-C)` is multiplied by the same fraction when alignment is enabled; its information-value term is unchanged. The unaligned condition isolates the state-update change.

All other A22 equations, traits, attempt and explanation rates, guided-attempt bonus, fixed graph, timings, semantic streams and local-information boundaries are preserved. No additional copying penalty, student type or knowledge-gap target is introduced. `simulate_learning` is an explicit source fork of the A22 simulation function, importing unchanged helpers from `v4.py`; parity at fraction=1 is tested on every raw table. This preserves the locked source without a runtime monkey patch.

The zero default means **score inspection only**, not that all real-world checking is educationally useless. An effortful correction or self-explanation would need its own operational action. Positive fractions are sensitivity assumptions, not empirically estimated rates. Alpha remains chosen from a trajectory, not calibrated to educational data.

## Evidence boundary

Karpicke & Blunt (2011), https://pubmed.ncbi.nlm.nih.gov/21252317/, experimentally compared retrieval and elaborative study and found advantages on conceptual tests. This motivates distinguishing reconstructive activity from receiving information; it does not estimate these simulation rates or show that every attempt beats every form of checking.

Smith et al. (2009), https://pubmed.ncbi.nlm.nih.gov/19119232/, found improved performance on related questions after peer discussion. We retain learning from explaining and from attempting after a hint. Neither paper validates a particular simulated classroom gap.

## E10 exploratory design, fixed before execution

100 fresh replicate seeds (master 924101), 30 students, 20 homeworks, common random numbers within each replicate. Ten conditions: A22 parity reference; fractions .25, .10, 0 with aligned values; zero with unchanged choice values; checks disabled; reference/zero at 40 homeworks; reference/zero on ER instead of SBM. The full sensitivity grid is reported. No parameter search follows results.

Primary descriptive outcomes: class mean K, within-class K P90-P10 and SD, and learning gained since initialization. These separate a lower class average from a wider student gap. Activity counts use **completed events**, not choices or failed requests. Exact event gains must reconstruct each student's total K change.

For student-level behavioral comparisons, rank each reference classroom's students by completed attempts in homeworks 1-5 (ties by student ID), fixing lower/upper thirds of ten students across all paired conditions in that graph family. Report their initial K, final K, total gain, gain after homework 5, and full-trajectory attempts/checks/copy receipts. These are early low/high attempt groups, not assigned types. They are observational and confounded by initial traits and subsequent choices; no causal effect of choosing a behavior is claimed. Ties and behavior persistence are reported. Each replicate is the uncertainty unit, not each student.

Report means and paired differences with 2,000 bootstrap resamples of whole classrooms (seed 924102), pointwise 95% intervals. No multiplicity-adjusted claim of significance or real-world calibration. Lock model, tests, analysis and design before runs; save raw Parquet, manifests and hashes. Full historical suite plus parity, no-free-learning, retained information updates, bounds and time-accounting tests must pass first.

Even a wider gap can be a direct consequence of the encoded learning rule. Only changes in activity allocation and feedback trajectories beyond that rule can be described as emergent; no novelty claim follows from a larger number alone.
