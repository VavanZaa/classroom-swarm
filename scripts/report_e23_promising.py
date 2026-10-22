"""Report every frozen E23 condition, effects, uncertainty and mechanism evidence."""
from pathlib import Path
from collections import defaultdict
import json
import re
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).resolve().parent))
import e23_promising_mechanisms as e

def interval(r): return f"{r['effect']:+.3f} [{r['lo95']:+.3f}, {r['hi95']:+.3f}]"

def status(r):
    if r['target']=='near_zero':
        if r['lo95']>0: return 'Positive difference; paper little-change pattern conditional'
        if r['hi95']<0: return 'Negative difference; paper little-change pattern conditional'
        return 'Uncertain; not evidence of a human null'
    if r['target']=='context_dependent': return 'Partial composition probe'
    if r['target']=='positive': return 'Positive supported' if r['lo95']>0 else 'Opposite supported' if r['hi95']<0 else 'Uncertain'
    return 'Negative supported' if r['hi95']<0 else 'Opposite supported' if r['lo95']>0 else 'Uncertain'

def main():
    root=e.ROOT; lock=e.verify(root); files=[]; effects={}; metrics={}; totals=[]
    for phase in e.PHASES:
        dest=root/phase; complete=e.config.load_config(dest/'run-complete.json'); analysis=e.config.load_config(dest/'derived/analysis-manifest.json')
        assert analysis['execution_sha256']==e.config.sha256(dest/'run-complete.json') and analysis['design_sha256']==e.config.sha256(root/'design-lock.json')
        for name,digest in analysis['hashes'].items(): assert e.config.sha256(dest/'derived'/name)==digest,name
        effects[phase]=e.config.load_config(dest/'derived/effects.json'); metrics[phase]=e.config.load_config(dest/'derived/cohort-metrics.json'); totals.append(complete)
        files.extend([dest/'run-complete.json',dest/'class-metrics.json',dest/'raw-inventory.json',*sorted((dest/'derived').glob('*.json'))])
    testfile=e.REPO/'.tmp/A33-test-output.txt'; testmatch=re.search(r'(\d+) passed',testfile.read_text(encoding='utf-8'))
    assert testmatch; passed=int(testmatch[1]); files.append(testfile)
    headline=[r for r in effects['confirmation'] if r['metric']==r['headline_metric']]
    defaults=[r for r in headline if r['profile']=='default' and r['variant'] in ('A32','A33')]
    lookup={(r['case'],r['a'],r['b'],r['group'],r['metric'],r['variant']):r for r in defaults}
    report=e.REPO/'docs/experiments/E23-promising-mechanisms-results.md'
    if report.exists(): raise ValueError('Preserve an existing E23 report')
    count=sum(t['classrooms'] for t in totals); hashes=sum(t['file_hashes_verified'] for t in totals)
    lines=['---','type: experiment-results','updated: 2026-10-10','---','# E23 A33 promising mechanisms and study trends','',
        f'**Implemented the optional A33 curriculum, observed teacher forecasts, group preparation and shared reasoning; completed {count:,} classrooms with every live/reloaded raw audit passed, {hashes:,} saved-file hashes checked and {passed} tests passing.** All sources/settings, both development cohorts and sixteen fresh confirmation cohorts were frozen before outcomes. No parameters were fitted or changed between pools. Human calibration remains deferred.','',
        'A33 retains activity-linked effortful learning, scarce teacher/helper time and the exact A32 fallback. Initial domain means are preserved by the component projection. The new observed skill pretests, targeting and tagged measurement are additional assumptions; the combined comparison cannot identify one isolated mechanism. Numerical rates/costs are hypotheses, not field estimates.','',
        '## Fresh study comparisons','',
        'Treatment-minus-control differences are simulator percentage points with pointwise paired 95% intervals across sixteen whole schools/cohorts. They describe simulation randomness, not uncertainty about human realism. The last column preserves the paper-direction assessment; near-zero expectations are not proven by a nonsignificant result.','',
        '| Case / group / treatment minus control / outcome | A32 fresh reference | Full A33 | Assessment |','|---|---:|---:|---|']
    primary=[]
    for r in defaults:
        if r['variant']!='A33': continue
        a=lookup[r['case'],r['a'],r['b'],r['group'],r['metric'],'A32']; case=e.old.CASES[r['case']]
        lines.append(f"| [{case['paper']}]({case['url']}) / {r['group']} / {r['a']}−{r['b']} / {r['metric']} | {interval(a)} | {interval(r)} | {status(r)} |")
        if r['primary']: primary.append(r)
    lines+=['','## Family adjusted primary intervals','',
        'Bonferroni intervals cover the fourteen default A33 primary contrasts. Repeated practice, partial composition and the India-inspired probe are secondary. Do not pick a sensitivity as the primary result after seeing signs.','',
        '| Case / group / contrast / outcome | Family adjusted 95% interval |','|---|---:|']
    for r in primary: lines.append(f"| {r['case']} / {r['group']} / {r['a']}−{r['b']} / {r['metric']} | [{r['simultaneous_lo95']:+.3f}, {r['simultaneous_hi95']:+.3f}] |")
    lines+=['','## All prespecified variants and sensitivities','',
        '| Case / profile / variant / group / contrast / outcome | Fresh difference [95%] | Assessment |','|---|---:|---|']
    for r in headline: lines.append(f"| {r['case']} / {r['profile']} / {r['variant']} / {r['group']} / {r['a']}−{r['b']} / {r['metric']} | {interval(r)} | {status(r)} |")
    changes=e.config.load_config(root/'confirmation/derived/changes.json')
    lines+=['','## Paired changes to intervention effects','',
        'These subtract within-model study contrasts in the same cohorts. Differences versus A32 include changed information/content/measurement. Old-accuracy and no-reasoning controls isolate those stated switches; zero fixed-curriculum tracking is an encoded assignment control.','',
        '| Case / profile / group / outcome / reference variant | A33 contrast minus reference contrast [95%] |','|---|---:|']
    unique=set()
    for r in changes:
        if r['metric']!=r['headline_metric']: continue
        key=(r['case'],r['profile'],r['group'],r['metric'],r['reference_variant'],r['a'],r['b'])
        if key in unique: continue
        unique.add(key); lines.append(f"| {r['case']} / {r['profile']} / {r['group']} / {r['a']}−{r['b']} / {r['metric']} / {r['reference_variant']} | {interval(r)} |")
    grouped=defaultdict(list)
    for r in metrics['confirmation']: grouped[r['case'],r['profile'],r['arm'],r['group'],r['variant']].append(r)
    means=[]
    for key,rows in sorted(grouped.items()):
        mean={m:float(np.mean([r[m] for r in rows])) if all(r[m] is not None for r in rows) else None for m in rows[0] if m not in ('case','profile','arm','group','variant','replicate')}
        means.append(dict(case=key[0],profile=key[1],arm=key[2],group=key[3],variant=key[4],**mean))
    lines+=['','## Learning and observed activities','',
        'Knowledge gain is the mean over all components/domains. Teacher/helper gain credits in older metrics concern the active component and should not be compared as if already averaged across components. Teacher counts/time are per class/block; sessions are per student/block.','',
        '| Case / profile / arm / group / variant | Mean K gain | Peer sessions | Contract sessions | Guidance | Individual or group coaching | Group coaching | Followup | Teacher ticks | Advanced lessons share | Constructed items/student/block |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    for r in means:
        def fmt(v): return 'Unavailable' if v is None else f'{v:.3f}'
        lines.append('| '+' / '.join(r[k] for k in ('case','profile','arm','group','variant'))+' | '+' | '.join(fmt(r[k]) for k in ('knowledge_gain','peer_sessions','contract_sessions','guidance_count','coaching_count','group_coaching_count','followup_count','teacher_spent','advanced_lesson_share','constructed_items'))+' |')
    lines+=['','## Development cohort outcomes retained','',
        'Two development cohorts are too few for strong inference. These outcomes were not used for tuning or selection; fresh results use the same settings.','',
        '| Case / group / contrast / outcome | A33 development mean difference |','|---|---:|']
    for r in effects['development']:
        if r['variant']=='A33' and r['profile']=='default' and r['metric']==r['headline_metric']: lines.append(f"| {r['case']} / {r['group']} / {r['a']}−{r['b']} / {r['metric']} | {r['effect']:+.3f} |")
    lines+=['','## Interpretation boundaries','',
        'Tracking now changes the skill that is taught, not just the scalar difficulty. Inspect skill choices and prerequisite processing along with both starting groups. The three-level representation, threshold .7 and pretests are uncalibrated; matching a direction would support consistency under those assumptions, not identify human mechanisms.','',
        'Teacher forecasts use released outcomes and expected format exposure, not hidden competence or actual private attention. Group coaching pays delivery plus feedback time; no prep/feedback overhead becomes a learning dose. The planner is still greedy and can rationally favor followup when participation barriers dominate. The .35/from-knowledge profile tests a different baseline; it does not replace the .6/constant-confidence default. Unrelated potential-score restrictions under zero transfer remain encoded. Global access help can raise unrelated participation without teaching that topic.','',
        'Shared reasoning can construct valid answers from complementary fragments, but does not schedule more voluntary interactions or reproduce Sudoku/audio dialogue/public-rank incentives. Scheduled repeated blocks remain a benchmark. Component saturation limits helper gains on mastered material; any exact ceiling is an initialization identity, not an independently reproduced human null.','',
        'AI harm/mitigation and earlier peer results must be judged against the fresh paired A32 baseline. New component measurement and curriculum exposure can alter magnitudes; no extra AI penalty or learning-rate increase was introduced. Private student confidence/benefit beliefs remain pooled across skills, a limitation for adaptive self-study.','',
        'The [Indian incentive study](https://econweb.ucsd.edu/~kamurali/papers/Published%20Articles/Publisher%20Formatted%20Versions/Teacher%20Performance%20Pay%20%28JPE%202011%29.pdf) motivates a contrasting concept/transfer probe. Its shared-skill spillover coefficient .15 is declared, not estimated; positive unrelated improvement through that rule is not independent validation. The full field contract, multiple teachers and subject timetable remain outside this simplified probe.','',
        'The composition test is still only a fixed-low-focal peer-mean comparison, not the paper\'s full own-ability by peer-mean by spread design or dropout analysis. Static graph boundaries remain unchanged. A full cross-study replication claim is not justified solely by these comparisons.','']
    plot=[r for r in primary if r['target']!='near_zero']; fig=e.REPO/'docs/experiments/figures/E23-A32-A33-trends.png'; fig.parent.mkdir(exist_ok=True)
    f,ax=plt.subplots(figsize=(12,7)); y=np.arange(len(plot))
    for variant,offset,color in [('A32',-.13,'#b87832'),('A33',.13,'#256480')]:
        selected=[lookup[r['case'],r['a'],r['b'],r['group'],r['metric'],variant] for r in plot]
        ax.errorbar([r['effect'] for r in selected],y+offset,xerr=[[r['effect']-r['lo95'] for r in selected],[r['hi95']-r['effect'] for r in selected]],fmt='o',capsize=3,label=variant,color=color)
    ax.set_yticks(y,[f"{r['case']}: {r['a']}-{r['b']} ({r['group']}, {r['metric']})" for r in plot]); ax.invert_yaxis(); ax.axvline(0,color='gray',linewidth=1)
    ax.set_xlabel('Simulator percentage-point difference; paired pointwise 95% interval'); ax.set_title('Fresh matched cohorts; content, information and measurement change together'); ax.legend(); ax.grid(axis='x',alpha=.2); f.tight_layout(); f.savefig(fig,dpi=160); plt.close(f)
    lines+=['![Fresh A32 versus A33 intervention contrasts](figures/E23-A32-A33-trends.png)','',
        '## Reproducibility','',
        f'Design lock: `runs/E23-promising-mechanisms-r1/design-lock.json`. The development/confirmation folders contain all declared cohorts, raw classrooms, per-file hashes, effects, effect changes, unavailable contrasts and source manifests. Tests: {passed} passed. Every {count:,} live/reloaded reconstruction passed. No engine/source/setting was changed after the design lock. All frozen earlier sources/report evidence verified.','',
        'Done: implementation, functional acceptance, both frozen pools, raw audits and all-condition analysis. Waiting: no required input. Next: assess unresolved mechanisms with a separately declared design; preserve these successes and failures.','']
    report.write_text('\n'.join(lines),encoding='utf-8'); files+=[report,fig,root/'design-lock.json',Path(__file__),e.PLAN,e.REPO/'docs/25-v4-promising-mechanisms.md']
    summary=e.REPO/'docs/reports/A33-E23-summary-2026-10-10.json'
    e.config.save_json(summary,dict(classrooms=count,raw_file_hashes_verified=hashes,tests_passed=passed,primary=primary,condition_means=means,scope='Uncalibrated study-informed consistency, no fitting or external validation'))
    files.append(summary)
    e.config.save_json(report.with_suffix('.sources.json'),dict(classrooms=count,tests_passed=passed,raw_file_hashes_verified=hashes,sources={str(p.relative_to(e.REPO)).replace('\\','/'):e.config.sha256(p) for p in files}))
    print(report,flush=True)

if __name__=='__main__': main()
