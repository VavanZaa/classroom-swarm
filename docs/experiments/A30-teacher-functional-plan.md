---
type: diagnostic-plan
updated: 2026-10-06
---
# A30 teacher functional diagnostics

This plan is declared before diagnostic outcomes. It tests the new role's causal paths, resource accounting and information timing. It is not a paper replication, calibration or validation against human data. No coefficient will be changed to obtain a desired sign. Implementation defects require a separately identified rerun and an explanation of the correction.

Use `configs/A30-teacher-diagnostic.json`: seed 10063001, eight paired replicates, six students, six homeworks, twelve ticks per homework, twelve homework items and one hundred exam items. Exams occur at homeworks 2, 4 and 6. Initial student knowledge is uniform [0.2,0.7], confidence and benefit priors are constant 0.5, and alpha is constant 0.0584 (an assumed trajectory rate, not an estimated human parameter). The student graph is complete and static. Peer joint practice is permitted, copied answers are disabled, and student AI is disabled. All remaining settings and distributions are declared in JSON.

The reference teacher has eight ticks per homework, one admin tick, one tick per graded student submission, a three-tick whole-class lesson and one-tick individual guidance appointments, in that order. Fixed lesson difficulty is 0.4, teacher competence 0.95 and teaching skill one. Observations use returned homework and released exams, no added delay/noise, coverage one, prior 0.5 and learning rate 0.5; assisted homework has zero weight. Guidance strength is 0.1 and confidence blend rate 0.2. These values specify proxies, not calibration.

| Condition | Change from reference |
|---|---|
| no_teacher | Disable the complete teacher intervention; A29 parity comparator. |
| fixed_manual | Reference teacher. |
| fixed_automated | Fully automate grading. |
| adaptive_automated | Fully automated grading and instruction adapted to observed assessments. |
| incorrect_automated | Fully automated grading with zero teaching skill. |
| guidance_only | Fully automated grading, guidance only, strength 0.3, confidence blend zero. |
| guidance_time_only | Same guidance schedule with strength zero. |
| overloaded_manual | Reduce the reference teacher's budget to four ticks. |
| unobserved_adaptive | Adaptive/automated teacher with observation coverage zero. |

All contrasts and their differences are resolved in the lock. Enabling the teacher adds a bundle of workload, instruction and guidance, so the whole-role comparison cannot identify their separate contributions. Other specified contrasts change one numerical setting or action list. Automation reducing grading cost, zero skill eliminating correct teacher content, and absent observations preserving the prior are encoded consequences; they are functional checks, not empirical findings.

Save each raw table and hashes. Re-read every output, verify hashes and run raw audits. Report the mean final unaided exam and competence, teacher appointments/guidance, teacher content gain, required grading time, and unfinished grading at the end of homework 6 and after the closing day. Report all nine conditions, including adverse or inconclusive directions. Describe resource transfer separately from net student outcomes. Preserve historical source hashes and freeze this plan, JSON, engine, tests and diagnostic script before execution. A subsequent study comparison needs a study-matched protocol and a separate design.
