"""Generate E22 tables without selecting setups or suppressing contrary results."""
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
sys.path.insert(0,str(Path(__file__).resolve().parent))
import e22_a32_study_trends as e


def interval(r,simultaneous=False):
    a,b=('simultaneous_lo95','simultaneous_hi95') if simultaneous else ('lo95','hi95')
    return f'{r["effect"]:+.3f} [{r[a]:+.3f}, {r[b]:+.3f}]'


def status(r,target,simultaneous=False):
    lo,hi=(r['simultaneous_lo95'],r['simultaneous_hi95']) if simultaneous else (r['lo95'],r['hi95'])
    if target=='near_zero': return 'Within model ±1 pp band' if lo>=-1 and hi<=1 else 'Near-zero not established'
    if target=='context_dependent': return 'Positive' if lo>0 else 'Negative' if hi<0 else 'Uncertain'
    if (lo>0 if target=='positive' else hi<0): return 'Paper direction supported'
    if (hi<0 if target=='positive' else lo>0): return 'Opposite direction supported'
    return 'Uncertain direction'


def main():
    root=e.ROOT; lock=e.verify(root); complete=e.config.load_config(root/'run-complete.json')
    analysis=e.config.load_config(root/'derived/analysis-manifest.json')
    assert complete['raw_audits']==analysis['raw_audits']=='all passed'
    assert analysis['execution_sha256']==e.config.sha256(root/'run-complete.json')
    assert analysis['design_sha256']==e.config.sha256(root/'design-lock.json')
    for name,digest in complete['hashes'].items(): assert e.config.sha256(root/name)==digest
    for name,digest in analysis['hashes'].items(): assert e.config.sha256(root/'derived'/name)==digest
    effects=e.config.load_config(root/'derived/effects.json'); metrics=e.config.load_config(root/'derived/cohort-metrics.json')
    headlines=[r for r in effects if r['metric']==r['headline_metric']]
    report=e.REPO/'docs/experiments/E22-A32-study-trends-results.md'
    if report.exists(): raise ValueError('Preserve existing E22 report')
    primary=[r for r in headlines if r['profile']=='default' and r['primary']]
    counts={s:sum(status(r,r['target'],True)==s for r in primary) for s in
        ('Paper direction supported','Opposite direction supported','Uncertain direction','Within model ±1 pp band','Near-zero not established')}
    lines=['---','type: experiment-results','updated: 2026-10-07','---','# E22 — Does A32 support the published trends?','',
        f'**Completed {complete["classrooms"]:,} new classrooms across {e.REPLICATES} paired school/cohort replicates. Every raw audit passed and {complete["file_hashes_verified"]:,} saved-file hashes were verified.** The engine and all settings were frozen before outcomes; no parameters were adjusted after results. Human calibration remains deferred. Historical locked sources and reports passed their preservation checks.','',
        f'Across fourteen default primary contrasts, simultaneous intervals classify: {counts}. Near-zero bands are model diagnostics, not replication of a human null. Repeated teaching and peer composition are additional probes. Study-direction agreement remains conditional on the declared assumptions, not proof that the causal model is correct.','',
        '## Paper comparisons under the default setup','',
        'Effects are treatment minus control in simulator percentage points. Intervals resample whole paired schools/cohorts. Pointwise and family-adjusted intervals measure simulation randomness under fixed assumptions; they exclude structural/model uncertainty. Potential scores are unaided performance with everybody evaluated; actual participation and enrolled-cohort scores are separate.','',
        '| Study / group / contrast / outcome | Effect [pointwise 95%] | Simultaneous 95% | Assessment |','|---|---:|---:|---|']
    for r in [x for x in headlines if x['profile']=='default']:
        case=e.CASES[r['case']]; label=f'[{case["paper"]}]({case["url"]}) / {r["group"]} / {r["a"]}−{r["b"]} / {r["metric"]}'
        lines.append(f'| {label} | {interval(r)} | {interval(r,True) if r["primary"] else "Secondary"} | {status(r,r["target"],r["primary"])} |')
    lines+=['','## All predeclared setups','',
        'Sensitivity results never replace the default primary result. The larger reward/future-stakes and lower teacher-cost values are utility assumptions, not measured currency/time equivalents. A supported alternative profile establishes conditional agreement only.','',
        '| Case / profile / group / contrast / outcome | Effect [pointwise 95%] | Assessment |','|---|---:|---|']
    for r in headlines:
        lines.append(f'| {r["case"]} / {r["profile"]} / {r["group"]} / {r["a"]}−{r["b"]} / {r["metric"]} | {interval(r)} | {status(r,r["target"])} |')
    lines+=['','## Recorded learning, effort and teacher activity','',
        'Means below are per student per block for costs and sessions; teacher actions/resources are per classroom per block. Knowledge/gain are final model points. These activity measurements can rule out a proposed explanation, but do not identify human mediation.','',
        '| Case / profile / arm / group | K gain | Productive doses % | Cost | Peer sessions | Contract sessions | Teacher instruction ticks | Guidance | Coaching | Followup | Teacher spent |','|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|']
    grouped={}
    for r in metrics: grouped.setdefault((r['case'],r['profile'],r['arm'],r['group']),[]).append(r)
    for key,rows in sorted(grouped.items()):
        def m(k): return float(np.mean([r[k] for r in rows]))
        lines.append('| '+' / '.join(key)+' | '+' | '.join(f'{m(k)*(100 if k=="productive_fraction" else 1):.3f}' for k in
            ('knowledge_gain','productive_fraction','cost','peer_sessions','contract_sessions','instruction_ticks','guidance_count','coaching_count','followup_count','teacher_spent'))+' |')
    lines+=['','## Teacher rewards: performance versus participation','',
        'A missing exam contributes zero to the enrolled-cohort formula. Potential, participant-only and cohort effects therefore answer different questions. Followup reduces access costs globally, so an unrelated-cohort-score gain can occur without unrelated learning. Zero cross-topic transfer is an explicit restriction, not evidence of human test specificity.','',
        '| Profile / contrast / outcome | Effect [pointwise 95%] |','|---|---:|']
    seen=set()
    for r in effects:
        if r['case']=='teacher_rewards' and r['metric'].startswith(('familiar_','novel_','unrelated_','core_')):
            key=(r['profile'],r['metric'])
            if key in seen: continue
            seen.add(key)
            lines.append(f'| {r["profile"]} / rewarded−unrewarded / {r["metric"]} | {interval(r)} |')
    lines+=['','## What the assumptions can and cannot support','',
        '**Class size:** finite individual guidance is a plausible channel for smaller classes. A32 must actually select guidance and students must use it; higher teacher knowledge alone is insufficient. The lower-cost profile checks a decision threshold, not a calibrated correction. The fixed 120-student school improves pairing over earlier separately generated classrooms.','',
        '**Tracking:** instructional adaptation can be plausible when students differ in readiness. Budget six funds the declared lesson after preparation; budget three explicitly shortens it. The multiplier two and population mean .45 came from earlier setup fitting. The fixed-curriculum control tests whether adaptive-targeting is needed, but uncertainty and new effort/quality gates can still prevent the paper direction.','',
        '**AI:** assisted scores and unaided learning are distinct. Copying competes with costly practice, while protected lecture makes some learning common to all arms; larger AI effects are therefore not guaranteed. Study effort, access and future stakes can change uptake. The zero direct-learning rule for answer receipt is encoded; a net harmful total contrast is not predetermined because subsequent activities can compensate. Language tutoring and the paper\'s common review stage remain missing.','',
        '**Peer-teaching lab:** one voluntary block with future evaluation is closer than twenty scheduled blocks. Helpful content, helper learning and time costs are plausible; numerical knowledge probabilities do not represent puzzle solving. Audio, communicated strategies, public ranks and explicit tournament pay are absent. Repeated opportunity frequency is encoded and cannot establish spontaneous-teaching-frequency agreement.','',
        '**Rewarded seating:** rewards tied to observed partner improvement, baseline-defined pairs and real opportunity cost are plausible. A32 may generate helper gains absent in the paper; that mismatch must remain. Reward utilities, prize expectation and recipient willingness are not empirically calibrated. Placebo/high-cost controls test incentives rather than direct reward-to-knowledge credit.','',
        '**Teacher incentives:** the paper reports reward-linked gains, greater test preparation and participation, little unrelated-test improvement and unchanged attendance/homework assignment. A32 can now separate these outcomes, but an unrelated-topic null is partly imposed by zero transfer, and individual coaching is narrower than classroom test preparation. A larger reward alone cannot validate the full pattern. Student practice also reacts to the added available activities.','',
        '**Peer composition:** own ability, peer mean and spread interact in the paper; its tracking and dropout findings are not tested by the fixed-low-focal mean probe. Treat these results as a conditional mechanism stress test, never full study reproduction.','',
        '## Earlier results retained','',
        'E21 already audited 3,864 classrooms and replayed thirteen historical cases exactly. Its preserved combined-profile contrasts are reproduced below as descriptive references. E22 changes learning, resource feasibility and several protocols together; subtracting these numbers cannot identify the effect of any single new mechanism.','',
        '| Earlier E21 case / group / contrast | Effect [original pointwise 95%] |','|---|---:|']
    oldpath=e.REPO/'runs/E21-study-mechanisms-r1/derived/effects.json'
    for r in e.config.load_config(oldpath):
        if r['profile']=='combined' and r['metric']==r['headline_metric']:
            lines.append(f'| {r["case"]} / {r["group"]} / {r["a"]}−{r["b"]} | {interval(r)} |')
    fig=e.REPO/'docs/experiments/figures/E22-A32-paper-trends.png'; fig.parent.mkdir(exist_ok=True)
    plot=[r for r in primary if r['target']!='near_zero']; labels=[f'{r["case"]}: {r["a"]}−{r["b"]} ({r["group"]}, {r["metric"]})' for r in plot]
    f,ax=plt.subplots(figsize=(11,6)); y=np.arange(len(plot)); vals=np.array([r['effect'] for r in plot])
    ax.errorbar(vals,y,xerr=np.array([[r['effect']-r['lo95'] for r in plot],[r['hi95']-r['effect'] for r in plot]]),fmt='o',color='#234b68',capsize=3)
    ax.set_yticks(y,labels); ax.invert_yaxis(); ax.axvline(0,color='gray',linewidth=1); ax.set_xlabel('Simulator percentage-point difference; pointwise paired 95% interval')
    ax.set_title('Frozen A32 default setups — published nonzero-direction probes'); ax.grid(axis='x',alpha=.2); f.tight_layout(); f.savefig(fig,dpi=160); plt.close(f)
    lines+=['','![A32 paper-direction contrasts](figures/E22-A32-paper-trends.png)','',
        '## Reproducibility','',
        f'Design: `runs/E22-A32-study-trends-r1/design-lock.json`. Every resolved classroom is in the frozen replicate declarations; raw classroom tables and per-file hashes are under `raw/`. Analysis: `derived/effects.json`, `derived/cohort-metrics.json` and `derived/analysis-manifest.json`. Source preservation checks verified {lock["historical_entries_verified"]} A32/E21 source/report entries in addition to E21\'s recursive older-source checks. All {complete["classrooms"]:,} runs passed both live and reloaded raw validation. No after-outcome tuning, model change or rejected profile removal occurred.','',
        'A defensible claim is: “Under the explicitly declared assumptions, the simulation supports selected paper-consistent directional patterns; other patterns remain uncertain, contrary or untested.” A blanket claim that it reproduces all studies is unsupported.','']
    report.write_text('\n'.join(lines),encoding='utf-8')
    e.config.save_json(e.REPO/'docs/reports/E22-A32-study-trends-summary.json',dict(counts=counts,primary=primary,classrooms=complete['classrooms']))
    sources=[report,fig,e.PLAN,Path(__file__),e.REPO/'scripts/e22_a32_study_trends.py',
        root/'design-lock.json',root/'run-complete.json',root/'raw-inventory.json',root/'class-metrics.json',
        root/'derived/analysis-manifest.json',root/'derived/effects.json',root/'derived/cohort-metrics.json',oldpath,
        e.REPO/'docs/reports/E22-A32-study-trends-summary.json']
    e.config.save_json(report.with_suffix('.sources.json'),dict(sources={str(p.relative_to(e.REPO)).replace('\\','/'):e.config.sha256(p) for p in sources}))
    print(report); print(counts)


if __name__=='__main__': main()
