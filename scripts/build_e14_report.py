"""Format already-frozen E14 analysis outputs; does not refit or reclassify findings."""
import csv
import hashlib
from pathlib import Path
import shutil

ROOT=Path(__file__).resolve().parents[1]
DERIVED=ROOT/'runs/E14/derived'


def load(name):
    with (DERIVED/name).open(encoding='utf-8',newline='') as handle:
        return list(csv.DictReader(handle))


def main():
    estimates=load('condition_estimates.csv')
    effects=load('effects.csv')
    verdicts=load('literature_comparison.csv')
    index={(r['group'],r['condition'],r['metric']):float(r['mean']) for r in estimates}
    def value(group,condition,metric): return index[group,condition,metric]
    def table(headers,rows):
        return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
                         ['| '+' | '.join(map(str,row))+' |' for row in rows])
    def conditions(group):
        return list(dict.fromkeys(r['condition'] for r in estimates if r['group']==group))
    matched=sum(r['verdict']=='same direction' for r in verdicts)
    opposite=sum(r['verdict']=='opposite direction' for r in verdicts)
    inconclusive=sum(r['verdict']=='inconclusive' for r in verdicts)
    equivalent=sum(r['verdict']=='within declared equivalence band' for r in verdicts)
    not_equivalent=sum(r['verdict']=='not established as equivalent' for r in verdicts)
    sections=[f'''# E14: classroom setup and literature trends

Completed 2026-10-01: **3,300 simulations, 33 conditions, 100 classroom replicates per condition**. All raw-output audits, file/source hash checks and both exact social-channel controls passed. No parameter fitting or tuning was performed. The ten frozen primary comparisons yielded {matched} matching directions, {opposite} opposite direction, {inconclusive} inconclusive directions, {equivalent} within the predeclared simulation equivalence band, and {not_equivalent} outside that classification. Read each comparison below; they test overlapping mechanisms and are not ten independent study replications.

This tests whether the current model can produce literature-compatible directions under declared assumptions. Scores below are synthetic normalized quantities. Agreement does not validate those assumptions or reproduce published human effect sizes.

## Published evidence used

| Study | Classroom setup and empirical result | Boundary of this comparison |
|---|---|---|
| [Krueger / Project STAR](https://www.nber.org/papers/w6051), NBER 1997 / QJE 1999 | Small classes of 13–17 versus regular 22–25; small classes improved standardized test ranks, about four percentile points initially. | Simulate 15 versus 24; teacher attention is absent. Published percentile-rank changes are not our score percentage points. |
| [Kimbrough, McGee and Shigeoka](https://docs.iza.org/dp10783.pdf), 2017 working paper / JHR 2022 | Four-person laboratory groups solving logic problems. Peer teaching benefited low performers; homogeneous ability grouping offset the benefit. | Compare fixed low starters in mixed versus homogeneous four-person groups, and teaching versus solo. Numerical hints abstract from discussion. |
| [Duflo, Dupas and Kremer](https://www.povertyactionlab.org/sites/default/files/research-paper/39%20Peer%20Effects%2C%20Teacher%20Incentives%2C%20and%20the%20Impact%20of%20Tracking%20Project.pdf), AER 2011 | Randomized tracking in 121 Kenyan primary schools; students across ability levels benefited, including through teachers adapting instruction. | The adaptive-instruction channel is absent. Our grouping result cannot reproduce the full intervention. |
| [Wu, Zhang and Wang](https://www.aeaweb.org/content/file?id=15848), AEJ Economic Policy 2023 | Mixed seating alone had no detectable effect; pairing plus helper rewards improved low students' mathematics by about 0.24 SD. | Compare seating alone. No rewards or friendship formation in this model. A nondetection is not proof of an exact human zero. |
| [Bastani et al.](https://www.pnas.org/doi/10.1073/pnas.2422633122), PNAS 2025 | Nearly 1,000 high-school students; four sessions. Base AI improved practice but reduced unaided exam performance; tutor guardrails removed the detectable harm without a detectable exam gain. | Compare answer/tutor/no AI over four numerical episodes. No calibrated time scale, actual GPT conversations or human-data fitting. The published affiliation correction does not change these findings. |

Additional distribution evidence was found after the E14 design was frozen, and is **background, not an added primary comparison**: [Booij, Leuven and Oosterbeek, author manuscript](https://leuven.economists.nl/pdf/ability_final.pdf), Review of Economic Studies 2017, experimentally varied mean and spread of prior ability in university tutorial groups of about 40. Peer effects depended on both moments and own ability. Their regression-based assignment calculations favored three-way tracking for low/middle students; surveys found more positive interactions, without evidence of teacher adjustment. This cautions against assuming that higher peer means or wider distributions have one universal effect. Our spread sensitivity changes students' own starting knowledge too, so it does not isolate that paper's contextual peer-SD effect.

## Frozen primary comparisons

Outcome: final unaided exam, treatment minus reference, in normalized score percentage points (pp). Focal students are all students for size/AI and fixed low starters for peer composition/grouping. Intervals are replicate-level percentile-bootstrap Monte Carlo intervals, adjusted across ten comparisons; nominal simultaneous coverage is 95%, approximate. Human empirical uncertainty is not included. For nondetection targets, the separately chosen equivalence band is ±1 pp.
''']
    sections.append(table(['Comparison','Expected direction','Exam difference (pp)','Adjusted interval (pp)','Verdict'],[
        [r['label']+(' (friends only)' if r['condition']=='small_friends' else ' (weak acquaintance access)' if r['condition']=='small_acquaintances' else ''),r['expected'],f"{float(r['delta']):+.2f}",
         f"[{float(r['simultaneous_lo']):+.2f}, {float(r['simultaneous_hi']):+.2f}]",r['verdict']]
        for r in verdicts]))
    sections.append('''## What the runs show

The model reproduced the peer-teaching benefit over solo work (+1.53 pp) and the answer-AI tradeoff: middle-population homework increased 22.11 pp while unaided exams fell 2.16 pp. Tutor AI exceeded answer AI by 2.42 exam pp. Tutor versus no AI was a small positive +0.26 pp, with its interval excluding zero; it qualifies under our ±1 pp simulation equivalence criterion, but does **not** reproduce the human study's statistical nondetection literally.

Two important expected patterns did not appear clearly: smaller classes and mixed versus homogeneous teaching groups. Teaching still benefited homogeneous low groups (+1.43 exam pp, exploratory pointwise interval [1.11,1.78]); tracking did not remove the teaching benefit as it did in the laboratory study. The model therefore captures a teaching benefit but misses that study's composition interaction.

Stronger peers under the current hint/copy rules improved low starters' homework by 9.01 pp, increased their final copied share by 15.53 pp, reduced attempts by 0.124 per episode, and lowered exams by 2.01 pp. This is consistent with copied answers displacing practice. With copying disabled, stronger peers produced nearly no exam change (−0.06 pp, inconclusive). It is not evidence that stronger peers generally harm real students. Likewise, cross-ability desk pairing produced −1.90 exam pp while raising homework 3.58 pp and copying 11.13 pp; that does not recover the published seating-only nondetection.

The exploratory wider initial distribution lowered four-episode knowledge gain by 0.25 pp and exam scores by 0.71 pp, while raising homework by 4.91 pp. Its realized mean also differed by chance; those effects include changes in students' own traits and interactions, so they cannot be read as an isolated peer-spread effect. High-starting populations had higher score levels but less knowledge gain, partly reflecting the encoded remaining-knowledge headroom.

These discrepancies identify limits worth testing in a future separately declared experiment: the effect of provider ability on teaching needs an isolated sensitivity test, and teacher attention or instruction would provide additional classroom-size mechanisms. Adaptive teaching, helper incentives and ability-dependent engagement require explicit mechanisms before testing the corresponding field results. Do not adjust the present coefficients until an apparent match emerges.
''')
    sections.append('''## Shared numerical assumptions

Class-size, peer-composition and grouping scenarios run 20 homework episodes; AI/spread scenarios run four. Each episode has 12 ticks and ten homework items; exams have 30 items, every five episodes in the 20-episode setups and every episode in the AI setups. Learning-efficiency and effort-aversion distributions are lognormal with arithmetic means 0.0584 and 0.15, respectively, and log SD 0.25. The learning coefficient comes from the existing chosen model trajectory, not empirical estimation. Confidence and all five benefit priors start at 0.5, grade target is 0.75, and the existing recalibration feedback rule is retained. Every remaining numerical assumption is recorded explicitly in the four resolved locks.
''')
    sections.append('''## Class size

ER graphs have expected friend degree six across sizes. Acquaintance weight is zero or 0.1. Thus size does not dilute teacher time, and larger classes can change weak-contact opportunities. N=45 is exploratory and outside STAR's main regular-class range. The size-change pairing preserves stream identities, not identical classroom-sized random tensors.
''')
    sections.append(table(['Condition','N','Initial K (%)','Final K (%)','Final exam (%)','Final homework (%)'],[
        [c,15 if c.startswith('small') else 24 if c.startswith('regular') else 45]+
        [f'{100*value("class_size",c,"all_"+m):.2f}' for m in ('initial_knowledge','final_knowledge','exam','homework')]
        for c in conditions('class_size')]))
    sections.append('''## Knowledge of peers

The first 15 students always start at 0.35; only the other 15 students change. Confidence and benefit priors remain fixed at 0.5. Higher-peer-knowledge comparisons are mechanism probes motivated by peer-teaching evidence. Successful hints are measured as deliveries per focal student per episode; copying is the share of final homework packets marked copied.
''')
    sections.append(table(['Condition','Focal final K (%)','Focal exam (%)','Focal homework (%)','Final copied (%)','Hints/student/episode'],[
        [c]+[f'{100*value("peer_composition",c,"focal_"+m):.2f}' for m in ('final_knowledge','exam','homework','copied')]+
        [f'{value("peer_composition",c,"focal_hint_deliveries_per_episode"):.3f}']
        for c in conditions('peer_composition')]))
    sections.append('''## Ability grouping and seating

The four-person conditions share the same eight students and alter only allowed contacts. Copying is disabled. The paired-deskmate conditions have 32 students and permit both hints and copying. These are different mechanisms; comparisons are within each setup. The random seating graph was drawn once before outcomes, so the seating contrast is conditional on that declared graph.
''')
    sections.append(table(['Condition','Low starters final K (%)','Low starters exam (%)','Low starters homework (%)','Hints/student/episode'],[
        [c]+[f'{100*value("grouping",c,"focal_"+m):.2f}' for m in ('final_knowledge','exam','homework')]+
        [f'{value("grouping",c,"focal_hint_deliveries_per_episode"):.3f}']
        for c in conditions('grouping')]))
    sections.append('''## AI, population mean and spread

Means/SD parameters describe an underlying normal truncated to [0,1]. The table reports realized initial means and within-class SD averaged across replicates, plus final within-class SD. Narrow/wide rows change the underlying SD from the middle baseline 0.10 to 0.05/0.20. This changes own traits and peers jointly; a mean-zero distribution change is not a fixed-student peer-only effect.

Default answer AI accuracy is 0.90 per item. The `answer51` sensitivity changes both availability and accuracy versus no AI and is declared bundled. The paper's 51% whole-problem correctness is not a calibrated per-item probability. Tutor learning follows the model's assumed hint-learning rule; gains are not independent evidence that real tutoring necessarily improves knowledge.
''')
    sections.append(table(['Condition','Initial K (%)','Initial SD','K gained (pp)','Final SD','Exam (%)','Homework (%)','AI uses/student/episode'],[
        [c,f'{100*value("ai_and_spread",c,"all_initial_knowledge"):.2f}',
         f'{value("ai_and_spread",c,"all_initial_sd"):.3f}',
         f'{100*value("ai_and_spread",c,"all_knowledge_gain"):.2f}',
         f'{value("ai_and_spread",c,"all_final_sd"):.3f}',
         f'{100*value("ai_and_spread",c,"all_exam"):.2f}',
         f'{100*value("ai_and_spread",c,"all_homework"):.2f}',
         f'{value("ai_and_spread",c,"all_ai_uses_per_episode"):.3f}']
        for c in conditions('ai_and_spread')]))
    sections.append('''## Audit and reproducibility

- All 3,300 runs completed; every raw table was reloaded, checked against its SHA-256 file hash, and passed `validate_declared_log`.
- Both disabled-social-channel controls passed exact equality of focal final knowledge, final exam and final homework in all 100 paired replicates.
- Source/configuration hashes still match the E14 preregistration. All 58 source entries across the E9r1/E10/E11/E12r1/E13 historical locks were checked with zero mismatches.
- 112 targeted configuration, engine and measurement tests passed, including reference raw-table parity and the E14 measurement tests. No engine change was made for E14.
- Inherited identities include zero direct knowledge from copied answers, nonnegative practice gain and knowledge headroom. They are not discoveries. Conditional uptake and displaced practice determine intervention outcomes.

Artifacts: [preregistered design](E14-preregistration.md); `runs/E14/preregistration-lock.json`; four complete JSON declarations and runtime locks; `runs/E14/derived/analysis_manifest.json`; all-replicate metrics, condition estimates, effect intervals, comparison verdicts and raw inventory CSVs in `runs/E14/derived/`. Raw student/action/initial-state tables remain under each group's `raw/` directory. The analysis manifest hashes all derived artifacts. In the effect CSV, the `simultaneous_lo/hi` fields apply simultaneous adjustment only where `primary=True`; other rows repeat exploratory pointwise intervals.

To reproduce into a fresh root: run `scripts/e14_classroom_trends.py prepare --root runs/E14_new`, execute the four generated files with `python -m classroom_swarm.experiment_config run ... --output ...`, then run `scripts/e14_classroom_trends.py analyze --root runs/E14_new`. A frozen root cannot be reused or overwritten.

![E14 classroom trends](figures/E14-classroom-trends.png)

The two line panels and AI gain panel display averages for the declared scenarios, not fitted response curves. The class-size vertical axis magnifies small differences that are inconclusive in the primary comparisons. The grouping panel shows the adjusted primary intervals. Secondary metrics and contrasts are exploratory; their pointwise intervals are available in the CSVs.
''')
    dest=ROOT/'docs/experiments/figures/E14-classroom-trends.png'
    dest.parent.mkdir(parents=True,exist_ok=True)
    shutil.copyfile(DERIVED/'classroom_trends.png',dest)
    assert hashlib.sha256(dest.read_bytes()).digest()==hashlib.sha256((DERIVED/'classroom_trends.png').read_bytes()).digest()
    (ROOT/'docs/experiments/E14-results.md').write_text('\n\n'.join(sections)+'\n',encoding='utf-8')
    print('Wrote E14-results.md and verified figure copy')


if __name__=='__main__': main()
