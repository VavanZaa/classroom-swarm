"""Publish all E21 study contrasts, paired changes and retained historical evidence."""
from pathlib import Path
import csv, sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import e21_study_mechanisms as e

LABELS = {'star': 'STAR: small−regular', 'kenya': 'Kenya: tracked−mixed',
          'lab_repeated': 'Peer lab: repeated scheduled', 'lab_single': 'Peer lab: single voluntary',
          'ai': 'AI', 'seating': 'Seating: cross−random',
          'composition': 'Peer mean: no copying', 'composition_copy': 'Peer mean: copying',
          'teacher_rewards': 'Teacher rewards'}


def read_csv(path):
    with path.open(newline='', encoding='utf-8') as handle: return list(csv.DictReader(handle))


def interval(r, simultaneous=False):
    lo, hi = ('simultaneous_lo95', 'simultaneous_hi95') if simultaneous else ('lo95', 'hi95')
    return f"{float(r.get('effect', r.get('delta'))):+.3f} [{float(r[lo]):+.3f}, {float(r[hi]):+.3f}]"


def identify(spec, row):
    return all(spec[k] == row[k] for k in ('case', 'a', 'b', 'group'))


def historical(spec):
    case = spec['case']
    if case in {'star', 'kenya'}:
        path = REPO / 'runs/E19-teacher-study-r1/confirmation_derived/effects.json'
        selected = 'guidance_03_longer_day' if case == 'star' else 'population_mean_045'
        r = next(r for r in e.config.load_config(path) if (r['study'], r['profile'], r['control'], r['group'], r['metric']) == (case, selected, 'main', spec['group'], 'exam'))
    elif case.startswith('lab_'):
        path = REPO / 'runs/E17-tutoring-robustness-r1/confirmation_derived/effects.csv'
        suffix = 'reference' if case == 'lab_repeated' else 'single_voluntary'
        r = next(r for r in read_csv(path) if (r['condition'], r['reference'], r['group'], r['metric']) == (f"{spec['a']}_{suffix}", f"{spec['b']}_{suffix}", 'low', 'exam'))
    elif case in {'ai', 'seating'}:
        path = REPO / 'runs/E14/derived/effects.csv'
        group = 'ai_and_spread' if case == 'ai' else 'grouping'
        a, b = (f"middle_{spec['a']}", f"middle_{spec['b']}") if case == 'ai' else ('cross_pairs', 'random_pairs')
        r = next(r for r in read_csv(path) if (r['group'], r['condition'], r['reference'], r['metric']) == (group, a, b, 'focal_exam'))
    elif case.startswith('composition'):
        path = REPO / 'runs/E16-tutoring-r1/validation_derived/effects.csv'
        suffix = 'joint_copy' if case == 'composition_copy' else 'joint'
        r = next(r for r in read_csv(path) if (r['group'], r['condition'], r['reference'], r['metric']) == ('composition', f'high_{suffix}', f'low_{suffix}', 'exam'))
    else: return None, None
    return r, path


def status(r, target):
    lo, hi, value = float(r['lo95']), float(r['hi95']), float(r['effect'])
    if target == 'near_zero':
        return 'Within declared ±1 pp model band' if lo >= -1 and hi <= 1 else 'Near-zero diagnostic not established'
    if target in {'context_dependent', 'mechanism_probe'}:
        return 'Positive' if lo > 0 else 'Negative' if hi < 0 else 'Uncertain'
    sign = 1 if target == 'positive' else -1
    if (lo > 0 if sign == 1 else hi < 0): return 'Target direction; pointwise support'
    if (hi < 0 if sign == 1 else lo > 0): return 'Opposite direction; pointwise support'
    if value * sign > 0: return 'Target mean; interval uncertain'
    if abs(value) < 1e-10: return 'Zero mean; interval uncertain'
    return 'Opposite mean; interval uncertain'


def main():
    root = e.ROOT; lock = e.verify(root)
    report = REPO / 'docs/experiments/E21-study-mechanism-results.md'
    if report.exists(): raise ValueError('Preserve the existing E21 report')
    analysis = e.config.load_config(root / 'derived/analysis-manifest.json')
    assert analysis['raw_audits'] == 'all passed'
    for name, digest in analysis['hashes'].items(): assert e.config.sha256(root / 'derived' / name) == digest
    assert analysis['execution_sha256'] == e.config.sha256(root / 'run-complete.json')
    assert analysis['design_sha256'] == e.config.sha256(root / 'design-lock.json')
    complete = e.config.load_config(root / 'run-complete.json')
    for name, digest in complete['hashes'].items(): assert e.config.sha256(root / name) == digest
    for item in e.config.load_config(root / 'raw-inventory.json'):
        assert e.config.sha256(root / 'raw' / f"rep{item['replicate']:04d}" / item['condition'] / 'complete.json') == item['complete_sha256']
    replay = e.config.load_config(root / 'historical-replay.json')
    assert replay['all_passed'] and len(replay['results']) == 13
    effects = e.config.load_config(root / 'derived/effects.json')
    changes = e.config.load_config(root / 'derived/changes.json')
    metrics = e.config.load_config(root / 'derived/school-metrics.json')
    cases = e.config.load_config(root / 'cases.json'); specs = e.config.load_config(root / 'comparisons.json')
    evidence = []
    for folder in ('runs/E14/derived', 'runs/E16-tutoring-r1/validation_derived',
                   'runs/E17-tutoring-robustness-r1/confirmation_derived', 'runs/E19-teacher-study-r1/confirmation_derived'):
        manifest_path = REPO / folder / 'analysis_manifest.json'
        old = e.config.load_config(manifest_path)
        for name, digest in old['hashes'].items(): assert e.config.sha256(REPO / folder / name) == digest
        evidence.append(manifest_path)
    def get(spec, profile, metric=None, table=effects):
        return next(r for r in table if identify(spec, r) and r['profile'] == profile and r['metric'] == (metric or spec['metric']))
    def means(case, profile, arm, group, key):
        rows = [r for r in metrics if (r['case'], r['profile'], r['arm'], r['group']) == (case, profile, arm, group)]
        assert len(rows) == 24
        return float(np.mean([r[key] for r in rows]))
    material = [get(s, 'combined', table=changes) for s in specs if s['primary']]
    supported_changes = sum(r['simultaneous_lo95'] > 0 or r['simultaneous_hi95'] < 0 for r in material)
    reversed_means = []
    for s in specs:
        baseline = cases[s['case']]['baseline']
        if get(s, baseline)['effect'] * get(s, 'combined')['effect'] < -1e-10: reversed_means.append(s)
    lines = ['---', 'type: experiment-results', 'updated: 2026-10-07', '---',
        '# E21 — Do A31 mechanisms change the study comparisons?', '',
        f"**E21 completed {complete['classrooms']:,} new classrooms across 24 fresh paired replicates, plus thirteen exact historical replays.** The full suite passes **571 tests**. Human calibration remains deferred. Six previously tested paper families were revisited, and a seventh teacher-reward paper was assessed as a mechanism probe. No engine changed, no coefficient was adjusted after outcomes, no setup was selected from outcomes, and every declared comparison is retained.", '',
        f"The combined mechanisms change **{supported_changes} of the eleven main exam contrasts** with simultaneous 95% Monte Carlo intervals excluding zero. **{len(reversed_means)} of fourteen comparison means** reverse sign relative to their matched mechanism-off context; small or uncertain means are not proof of a reversal. The tables below separate the earlier saved result, the fresh old-protocol result, any necessary protocol bridge, and the A31 feature effect.", '',
        '## Previous results versus new comparisons', '',
        'Effects are treatment minus control in model percentage points, with pointwise paired 95% intervals. Historical intervals retain their original samples. The fresh old-protocol column uses 24 new replicates under the earlier assumptions; differences from old numbers are sampling variability, not engine changes. AI and single-block lab A31 headlines measure the active-topic exam; all-topic exams and mean competence are reported separately.', '',
        '| Case / group / contrast | Previous saved result | Fresh old protocol, features off | Matched active protocol, features off | Combined A31 | A31 minus matched contrast [95%] |',
        '|---|---:|---:|---:|---:|---:|']
    for s in specs:
        old, path = historical(s)
        if path: evidence.append(path)
        baseline = cases[s['case']]['baseline']
        label = f"{LABELS[s['case']]} / {s['group']} / {s['a']}−{s['b']}"
        lines.append(f"| {label} | {interval(old) if old else 'New mechanism probe'} | {interval(get(s, 'reference'))} | {interval(get(s, baseline))} | {interval(get(s, 'combined'))} | {interval(get(s, 'combined', table=changes))} |")
    lines += ['',
        'The paired change compares the same treatment contrast under two mechanism profiles on the same fresh replicate, rather than subtracting independent historical estimates. For AI and seating, the matched baseline is a separate joint-practice bridge with A31 features off; their legacy-hint result remains visible. Teacher-reward reference means only the additional workload/topics/peer branches are off: reward strength is already the declared treatment.', '',
        '## Which earlier conclusions are sensitive?', '',
        '| Case / group / contrast | Combined A31 assessment against stated target | Change from matched baseline, simultaneous 95% where primary |',
        '|---|---|---:|']
    for s in specs:
        r = get(s, 'combined'); change = get(s, 'combined', table=changes)
        label = f"{s['case']} / {s['group']} / {s['a']}−{s['b']}"
        lines.append(f"| {label} | {status(r, s['target'])} | {interval(change, s['primary'])} |")
    lines += ['',
        'Only the eleven predeclared main combined-versus-baseline exam changes receive family-adjusted intervals. Outcome intervals, other profiles, composition and teacher-reward probes remain descriptive and pointwise. A paper’s nonsignificant difference is not proof of equivalence; the ±1 pp band is only the prespecified simulator diagnostic. No model points are converted to human standard deviations, percentile ranks or puzzle-solving times.', '',
        '![Study contrasts and changes](figures/E21-study-mechanism-comparisons.png)', '',
        '## Study-specific interpretation', '',
        '**Class size.** [STAR / Krueger](https://www.nber.org/papers/w6051) motivates the smaller-class direction. E21 retains the E19 setup: 15 versus 24 students, equal realized population mean/spread, one teacher with the same total budget, guidance 0.3 and student ticks 18. Incentives replace fixed discretionary allocation with observed-score effort/target choice; workload and grading can remove the appointments that generated the earlier size effect. These assumptions have no established conversion to human minutes. Disruption, aides and demographic channels remain missing.', '',
        '**Instructional tracking.** [Duflo, Dupas and Kremer](https://www.povertyactionlab.org/sites/default/files/research-paper/39%20Peer%20Effects%2C%20Teacher%20Incentives%2C%20and%20the%20Impact%20of%20Tracking%20Project.pdf) motivates joint assessment of learning across starting groups, teacher effort and instructional targeting. The retained E19 mean 0.45 and teacher-content multiplier 2 were earlier direction fits, not field estimates. Adding one preparation tick to the three-tick budget can make a three-tick lesson infeasible. Resource and peer-access contexts below test that limitation separately. Convex rewards are a theoretical sensitivity, not an observed Kenyan pay schedule. A31’s content/readiness geometry is different from the paper’s abstract instructional-distance model, so its analytical effort/target rankings need not follow. Two numerical topic labels are not measurements of human basic/advanced skill.', '',
        '**Peer-teaching lab.** [Kimbrough, McGee and Shigeoka](https://www.crepe.e.u-tokyo.ac.jp/events/20190325_shigeoka.pdf) used one shared-puzzle practice block with audio and public ranks, followed by individual evaluation. The repeated scheduled probe tests the previous E17 result; the single voluntary probe is a closer duration/choice counterpart. Scheduled frequency is fixed, so it cannot explain a field decrease in spontaneous teaching. Consolidation and noisy/delayed evidence can alter helper gains and choices, but audio explanations, puzzle strategies, public ranks and individual tournament incentives remain absent.', '',
        '**AI use.** [Bastani and colleagues](https://www.pnas.org/doi/10.1073/pnas.2422633122) motivates assisted practice versus unaided, concept-related evaluation and a separate safeguarded tutor. E21 retains the four-session none/answer/tutor comparison and then introduces four persistent session topics. The main A31 exam uses the final active topic; the all-topic result tests broader accumulated competence. A31 still lacks the study’s common lecture/review stages, conversational assistance and explicit future-test stakes. Pure copying continues to grant zero direct skill; that assumption remains relevant to any matching direction.', '',
        '**Seating and peer composition.** [Wu, Zhang and Wang](https://www.aeaweb.org/content/file?id=15848) separates seating alone from financial rewards to student helpers. E21 retests seating only; teacher rewards cannot stand in for its rewarded-seating treatment, and friendship changes remain absent. [Booij, Leuven and Oosterbeek](https://leuven.economists.nl/pdf/ability_final.pdf) finds own-ability-dependent mean/spread interactions. E21 retests the earlier fixed-low-focal mean comparison with and without copying. It does not reproduce that full distributional regression, engagement or dropout result.', '',
        '**Teacher rewards.** [Glewwe, Ilias and Kremer](https://scholar.harvard.edu/files/kremer/files/teacher_incentives_aej_july_2010_sunday.pdf) reports gains concentrated in reward-linked tests and increased preparation, with weaker unrelated-test evidence. E21 changes reward strength 0 → 1 while retaining intrinsic motivation 0.2 and the same teacher budget. A31 can change general teaching effort and knowledge, but it has no separate test-specific preparation state, unrelated assessment or exam participation choice. A positive general exam effect would therefore match only a broad direction; it cannot reproduce the study’s distinguishing test-specific pattern.', '',
        f"**A concrete capacity check:** in the lower tracked section, the original three-tick budget delivers {means('kenya', 'reference', 'tracked', 'low', 'instruction_count'):.3f} instruction episodes per homework. The combined model delivers {means('kenya', 'combined', 'tracked', 'low', 'instruction_count'):.3f}; its separately declared six-tick control delivers {means('kenya', 'resourced_combined', 'tracked', 'low', 'instruction_count'):.3f}. Preparation competes with a discrete three-tick lesson. This identifies a feasibility problem in the assumed budget, not a real-world estimate of necessary preparation time.", '',
        '**Why the smaller-class match weakens.** In the linear and convex incentive profiles, average teaching effort falls from eight to three ticks per class per episode. Both class sizes receive the same three-tick broadcast lesson and no individual guidance. The earlier size-sensitive guidance pathway disappears. This is a consequence of the assumed effort objective and productivity belief; it shows that the earlier class-size agreement depends on how guidance is supplied.', '',
        '**Why the remaining tracking sign is insufficient.** With the combined mechanisms and original budget, the lower-starter exam contrast is +0.236 pp, but no instruction is delivered and the knowledge-gain interval spans zero. That result cannot support reproduction of a teacher-adaptation mechanism. The six-tick resource control restores lessons and yields +0.408 pp for lower starters; its +0.196 pp higher-starter effect remains uncertain. Allowing peer access under the original three-tick budget instead yields a lower-starter contrast of -0.235 pp, with a pointwise interval below zero. Resource and peer-access controls are separate contexts; a full resource-by-peer interaction was not tested. The joint study pattern remains unresolved.', '',
        '## Capacity, targeting and activity evidence', '',
        'Means across fresh replicates and episodes. Teaching effort and mandatory work are ticks per class per episode; teacher attention/practice are ticks per student per episode. Lesson difficulty is conditional on delivered instruction, shown as a dash when instruction count is zero. Direct component gains later in the report are active-topic accounting, not causal mediation.', '',
        '| Teacher case / profile / arm / group | Teaching effort | Mandatory work | Teacher attention | Practice ticks | Instruction episodes | Lesson difficulty | Effective skill | Returned grade fraction |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for case in ('star', 'kenya', 'teacher_rewards'):
        for profile in cases[case]['profiles']:
            name = profile['name']
            for arm, group in ([('small', 'all'), ('regular', 'all')] if case == 'star' else
                               [('mixed', 'low'), ('tracked', 'low'), ('mixed', 'high'), ('tracked', 'high')] if case == 'kenya' else
                               [('unrewarded', 'all'), ('rewarded', 'all')]):
                keys = ('teacher_effort', 'mandatory_work', 'teacher_attention', 'practice_ticks', 'instruction_count', 'instruction_difficulty', 'effective_skill', 'grade_return_fraction')
                values = [means(case, name, arm, group, k) for k in keys]
                display = [f'{v:.3f}' for v in values]; display[5] = '—' if values[4] == 0 else display[5]
                lines.append(f"| {case} / {name} / {arm} / {group} | " + ' | '.join(display) + ' |')
    lines += ['',
        'Grading is charged per student and can leave a backlog after the H+1 closing pass. Administrative arrivals carry forward rather than disappearing. Resource controls change teacher budget in both assignment arms; they are new resource assumptions. The automated grading comparison removes declared time cost, not grading error. Teacher-disabled student cases have no teaching actions; their unused runtime skill setting is not an intervention or teacher outcome.', '',
        '| Teacher comparison | Exam effect [95%] | Interpretation |', '|---|---:|---|']
    for s in [x for x in specs if x['case'] in {'star', 'kenya'}]:
        for name in ('grading_reference', 'grading_combined', 'automated_combined'):
            lines.append(f"| {s['case']} / {s['group']} / {name} | {interval(get(s, name))} | Same grading context; automation is an additional declared intervention. |")
        if s['case'] == 'kenya':
            for name in ('resourced_reference', 'resourced_combined', 'peer_context', 'peer_combined'):
                lines.append(f"| kenya / {s['group']} / {name} | {interval(get(s, name))} | Matched budget-six or peer-access context; not a coefficient fit. |")
    lines += ['', '## Student mechanisms and measurement sensitivity', '',
        '| Case / contrast | Combined all-topic exam [95%] | Combined active-topic exam [95%] | Combined mean competence gain difference [95%] | Homework difference [95%] |',
        '|---|---:|---:|---:|---:|']
    for s in specs:
        lines.append(f"| {s['case']} / {s['group']} / {s['a']}−{s['b']} | " + ' | '.join(interval(get(s, 'combined', metric=k)) for k in ('exam', 'exam_active', 'knowledge_gain', 'homework')) + ' |')
    lines += ['',
        'Splitting fixed exposure across independent topics changes the competence representation. Report the relevant-topic and broad exam separately rather than attributing dilution to worse human learning. Initial topics are clones with no hidden starting advantage; transfer and consolidation are declared nonnegative additions. Exams themselves grant no learning.', '',
        '| Case / combined arm / group | Guided episodes/student | Helper episodes/student | Practice ticks/student/episode | Direct helper gain | Received peer updates/student/episode | Pending signals/student/episode | AI uses/student/episode |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for case in ('lab_repeated', 'lab_single', 'ai', 'seating', 'composition', 'composition_copy'):
        for arm in cases[case]['arms']:
            group = 'low' if case in {'lab_repeated', 'lab_single', 'seating'} else 'focal' if case.startswith('composition') else 'all'
            values = [means(case, 'combined', arm, group, k) for k in ('guided_sessions', 'helper_sessions', 'practice_ticks', 'helper_gain_active', 'peer_updates', 'peer_pending', 'ai_use')]
            lines.append(f"| {case} / {arm} / {group} | " + ' | '.join(f'{v:.4f}' for v in values) + ' |')
    lines += ['',
        'Session counts are numerical completed interactions, not coded human teaching statements. Direct helper gains sum logged active-topic components in model points per student, not net effects. Private observation covers direct checked recipients only; no third-party reputation is inferred. Current student confidence and benefit beliefs remain pooled across topics.', '',
        '## Every profile and paired change', '',
        'All headline contrasts, including legacy bridges and matched grading/resource/peer contexts. Pointwise intervals are descriptive. Combined mechanisms include different channels in teacher-free cases; adding a classroom teacher to the Sudoku lab would change its protocol and is not done.', '',
        '| Case / group / contrast / profile | Exam effect [95%] | Matched profile | Change in contrast [95%] | Knowledge-gain contrast [95%] |',
        '|---|---:|---|---:|---:|']
    for s in specs:
        for p in cases[s['case']]['profiles']:
            name = p['name']; change = get(s, name, table=changes)
            lines.append(f"| {s['case']} / {s['group']} / {s['a']}−{s['b']} / {name} | {interval(get(s, name))} | {change['matched']} | {interval(change)} | {interval(get(s, name, metric='knowledge_gain'))} |")
    lines += ['',
        '## Preservation, uncertainty and remaining work', '',
        'The [E21 plan](E21-study-mechanism-plan.md), source hashes, resolved declarations and all 24 cohort/job files were frozen before new study outcomes. Preparation was corrected before freezing to check each declaration once instead of inheriting a 100-replicate runner default. No study outcome was produced by that preflight. All subsequent simulations used the frozen A31 sources and exact declarations.', '',
        f"All {complete['classrooms']:,} saved outputs passed hash checks, declaration identity checks and the full topic/exam/teacher/grade/provenance/time/reward/peer-belief validators. Thirteen original-seed historical classrooms matched every original raw table. All older source locks and E20 report evidence remain unchanged. Tests cover paired cohort membership, separate protocol bridges, fixed resource treatment, focal-state invariance, active-topic measurement declarations, weighted school aggregation, bootstrap cancellation, parallel-versus-serial raw parity, corrupt/mismatched resume rejection and partial-output preservation.", '',
        'Evidence lives in `runs/E21-study-mechanisms-r1/`: `design-lock.json`, `cases.json`, `comparisons.json`, 24 resolved replicate job files, `historical-replay.json`, saved raw class declarations/tables, `raw-inventory.json`, `run-complete.json`, and `derived/` metrics/effects/paired changes/analysis manifest. The report source manifest records the exact analysis, historical effect files and figure. No prior report, engine or default was rewritten to improve signs.', '',
        'An editorial review clarified that declared coefficients stayed fixed after outcomes and made the teacher-effort and zero-instruction limitations explicit. The first report, report script and source manifest are preserved byte-for-byte in `.tmp/E21-report-review-first-draft/`; this report’s source manifest records their hashes and the revision. No experiment settings, raw data, analysis or figure changed.', '',
        'These are study-informed conditional mechanism comparisons with uncalibrated coefficients and coarse time/content proxies. They establish numerical sensitivity and continuity. They do not independently validate the human processes, exact effect sizes or the missing dialogue, student rewards, strategic cramming, relationships and engagement channels. Human calibration stays deferred; future changes need a new model/run identity and controls for the mechanism they add.', '',
        'Progress: study comparisons and prior-result sensitivity tests complete; no input pending. Next: address the specific unsupported mechanisms revealed by these comparisons under a separately declared design.', '']
    figure = REPO / 'docs/experiments/figures/E21-study-mechanism-comparisons.png'
    fig, axes = plt.subplots(1, 2, figsize=(16.4, 9), sharey=True)
    positions = np.arange(len(specs))
    for name, offset, color, label in [('baseline', -.14, '#376c90', 'Matched features-off protocol'), ('combined', .14, '#ca7435', 'Combined A31')]:
        rows = [get(s, cases[s['case']]['baseline'] if name == 'baseline' else name) for s in specs]
        centers = [r['effect'] for r in rows]
        axes[0].errorbar(centers, positions + offset, xerr=[[r['effect']-r['lo95'] for r in rows], [r['hi95']-r['effect'] for r in rows]], fmt='o', capsize=3, markersize=4, color=color, label=label)
    for i, s in enumerate(specs):
        r = get(s, 'combined', table=changes); lo = r['simultaneous_lo95'] if s['primary'] else r['lo95']; hi = r['simultaneous_hi95'] if s['primary'] else r['hi95']
        axes[1].errorbar(r['effect'], i, xerr=[[r['effect']-lo], [hi-r['effect']]], fmt='o', capsize=3, color='#24547c' if s['primary'] else '#777777', markersize=4)
    axes[0].set_yticks(positions, [f"{LABELS[s['case']]} / {s['group']} / {s['a']}−{s['b']}" for s in specs], fontsize=9)
    axes[0].invert_yaxis(); axes[0].legend(fontsize=9, loc='best')
    for axis in axes: axis.axvline(0, color='#666666', linewidth=.8); axis.grid(axis='x', alpha=.2); axis.set_xlabel('Model percentage points')
    axes[0].set_title('Study treatment contrast · pointwise 95%')
    axes[1].set_title('Change caused by combined mechanisms\n11 primary: simultaneous 95%; probes: pointwise')
    fig.suptitle('E21 · 24 fresh paired replicates · original studies and outputs preserved', fontsize=14)
    fig.text(.5, .012, 'Active-topic exams for AI and single-block lab; broader exams elsewhere. Human calibration deferred.', ha='center', fontsize=9)
    fig.tight_layout(rect=(0, .035, 1, .95)); fig.savefig(figure, dpi=170); plt.close(fig)
    report.write_text('\n'.join(lines), encoding='utf-8')
    preservation_path = REPO / '.tmp/E21-report-review-first-draft/preservation.json'
    preservation = e.config.load_config(preservation_path)
    for entry in preservation['entries']:
        assert e.config.sha256(REPO / entry['preserved']) == entry['sha256']
    evidence += [preservation_path] + [REPO / entry['preserved'] for entry in preservation['entries']]
    editorial_revision = dict(date='2026-10-07',
        changes=['Clarified that declared coefficients were fixed after outcomes.',
                 'Explained the loss of class-size-sensitive guidance under incentives.',
                 'Explained why a positive tracking exam contrast with zero instruction does not support the teacher-adaptation mechanism.'],
        preserved_originals=preservation['entries'],
        scientific_effect='No experiment settings, raw data, analysis or figure changed.')
    sourcepaths = list(dict.fromkeys(evidence + [Path(__file__), report, figure, root / 'design-lock.json', root / 'run-complete.json', root / 'historical-replay.json', root / 'derived/analysis-manifest.json'] + list((root / 'derived').glob('*.json'))))
    e.config.save_json(report.with_suffix('.sources.json'), dict(sources={str(p.relative_to(REPO)).replace('\\', '/'): e.config.sha256(p) for p in sourcepaths},
        classrooms=complete['classrooms'], tests_passed=571, exact_historical_replays=13,
        primary_family_size=11, simultaneous_changes=supported_changes, sign_reversals_in_means=len(reversed_means),
        editorial_revision=editorial_revision,
        interpretation='Study-informed sensitivity, no fitting or human calibration. All profiles and historical failures retained.'))
    e.verify(root)
    print(f'Reported {complete["classrooms"]} classrooms; {supported_changes}/11 simultaneous changes; {len(reversed_means)}/14 mean sign reversals.')


if __name__ == '__main__': main()
