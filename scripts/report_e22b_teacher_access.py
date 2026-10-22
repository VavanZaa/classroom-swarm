"""Report the separately declared teacher-access correction and paired changes."""
from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parent))
import e22_teacher_access_correction as c
from report_e22_a32_study_trends import interval,status
e=c.e


def checked(root):
    e.verify(root); complete=e.config.load_config(root/'run-complete.json')
    analysis=e.config.load_config(root/'derived/analysis-manifest.json')
    assert analysis['execution_sha256']==e.config.sha256(root/'run-complete.json')
    for name,digest in complete['hashes'].items(): assert e.config.sha256(root/name)==digest
    for name,digest in analysis['hashes'].items(): assert e.config.sha256(root/'derived'/name)==digest
    return complete,e.config.load_config(root/'derived/effects.json'),e.config.load_config(root/'derived/cohort-metrics.json')


def main():
    before,old,oldmetrics=checked(e.ROOT); complete,effects,metrics=checked(c.ROOT)
    report=e.REPO/'docs/experiments/E22b-teacher-access-results.md'
    if report.exists(): raise ValueError('Preserve existing correction report')
    lines=['---','type: experiment-results','updated: 2026-10-07','---','# E22b — Teacher study protocol correction','',
        f'**Completed all {complete["classrooms"]} corrected classrooms with {complete["file_hashes_verified"]:,} saved-file hashes verified; every raw audit passed.** E22\'s original {before["classrooms"]:,} classrooms are preserved. Source review identified the duplicated exam cost before aggregate outcomes were inspected. Only the general .6 cost was removed: the per-exam .6 access cost remains. E22 total cost 1.2 is retained as the high-cost control. Same students, seeds and semantic draws permit paired comparison. No engine changed.','',
        'The corrected protocol is separately documented, not retrospectively presented as the original E22 design. Reward utility and participation thresholds remain assumed. The paper reports higher reward-linked scores, increased preparation/participation, and little unrelated-test improvement ([Glewwe, Ilias and Kremer](https://www.aeaweb.org/articles?id=10.1257/app.2.3.205)).','',
        '| Profile / outcome | Corrected effect [pointwise 95%] | Simultaneous 95% (three primary outcomes) | Assessment | Original high-cost effect |','|---|---:|---:|---|---:|']
    headlines=[r for r in effects if r['metric']==r['headline_metric']]
    for r in headlines:
        match=next(x for x in old if all(x[k]==r[k] for k in ('case','profile','a','b','group','metric','headline_metric')))
        primary=r['profile']=='default'
        lines.append(f'| {r["profile"]} / {r["metric"]} | {interval(r)} | {interval(r,True) if primary else "Sensitivity"} | {status(r,r["target"],primary)} | {interval(match)} |')
    lines+=['','## All assessment outcomes','',
        'Potential: unaided performance if all enrolled students take the exam. Participants: observed takers only. Cohort: absent students contribute zero. Participation: percent taking the test. Improvements in cohort contribution alone do not demonstrate conceptual learning. Followup applies to every exam form, so it can also raise unrelated-test participation.','',
        '| Profile / outcome | Rewarded−unrewarded [pointwise 95%] |','|---|---:|']
    seen=set()
    for r in effects:
        key=(r['profile'],r['metric'])
        if key in seen: continue
        seen.add(key)
        if r['metric'].startswith(('familiar_','novel_','unrelated_','core_')) or r['metric'] in ('knowledge_gain','coaching_count','guidance_count','followup_count','teacher_gain','teacher_spent'):
            lines.append(f'| {r["profile"]} / {r["metric"]} | {interval(r)} |')
    lines+=['','## Single-setting cost effects on the treatment contrast','',
        'These paired differences compare corrected reward effects with the same reward effects at cost 1.2, under identical opportunity draws. All profiles/outcomes are reported in the saved JSON; intervals below are pointwise sensitivity diagnostics. Unchanged nonparticipation profiles must be exact null controls.','',
        '| Profile / outcome | Corrected effect − original effect [paired 95%] |','|---|---:|']
    by=lambda rows:{(r['profile'],r['arm'],r['replicate']):r for r in rows if r['group']=='all' and r['case']=='teacher_rewards'}
    a,b=by(metrics),by(oldmetrics); changes=[]
    for profile in e.CASES['teacher_rewards']['profiles']:
        for metric in e.metrics_keys(next(iter(a.values()))):
            values=[]
            for rep in range(e.REPLICATES):
                terms=[a[profile,'rewarded',rep][metric],a[profile,'unrewarded',rep][metric],b[profile,'rewarded',rep][metric],b[profile,'unrewarded',rep][metric]]
                if any(x is None for x in terms): break
                values.append(terms[0]-terms[1]-terms[2]+terms[3])
            if len(values)!=e.REPLICATES: continue
            change=dict(profile=profile,metric=metric,**e.paired(values)); changes.append(change)
            if profile in ('format_without_participation','concept_only'): assert abs(change['effect'])<1e-10 and abs(change['lo95'])<1e-10 and abs(change['hi95'])<1e-10
            if metric in ('familiar_potential','unrelated_potential','familiar_participation','knowledge_gain'):
                lines.append(f'| {profile} / {metric} | {interval(change)} |')
    parity=[]
    for rep in range(e.REPLICATES):
        for job in c.corrected_jobs(rep):
            if job['profile'] not in ('format_without_participation','concept_only'): continue
            rel=Path('raw')/f'rep{rep:04d}'/job['condition']/'complete.json'
            assert e.config.load_config(e.ROOT/rel)['hashes']==e.config.load_config(c.ROOT/rel)['hashes']
            parity.append(str(rel).replace('\\','/'))
    assert len(parity)==96
    e.config.save_json(c.ROOT/'unchanged-profile-parity.json',dict(classrooms=len(parity),complete_files=parity,result='Every recorded file hash identical'))
    lines+=['','## Reading these results','',
        'The unrelated potential-score null follows from the taught-topic-only schedule and zero topic transfer: it is an encoded restriction in this design, not independent validation of human test specificity. Participation and enrolled-cohort effects remain separate from learning. Default reward 1 and sensitivity reward 20 are both retained; stronger utility cannot replace an uncertain default result. Individual coaching/time limits and the absence of classwide test-preparation organization remain important correspondence gaps. All 96 unchanged nonparticipation-profile classrooms match every original recorded file hash exactly.','',
        f'Correction plan: [E22b protocol](E22b-teacher-access-plan.md). Full E22 comparison: [E22 results](E22-A32-study-trends-results.md). Every corrected raw log was reloaded and audited; total saved-hash checks across both designs: {before["file_hashes_verified"]+complete["file_hashes_verified"]:,}.','']
    report.write_text('\n'.join(lines),encoding='utf-8')
    e.config.save_json(c.ROOT/'derived/cost-correction-changes.json',changes)
    sources=[report,c.PLAN,Path(__file__),e.REPO/'scripts/e22_teacher_access_correction.py',
        c.ROOT/'design-lock.json',c.ROOT/'run-complete.json',c.ROOT/'raw-inventory.json',
        c.ROOT/'derived/analysis-manifest.json',c.ROOT/'derived/effects.json',c.ROOT/'derived/cohort-metrics.json',
        c.ROOT/'derived/cost-correction-changes.json',c.ROOT/'unchanged-profile-parity.json',e.ROOT/'derived/effects.json',e.ROOT/'derived/cohort-metrics.json']
    e.config.save_json(report.with_suffix('.sources.json'),dict(sources={str(p.relative_to(e.REPO)).replace('\\','/'):e.config.sha256(p) for p in sources}))
    print(report)


if __name__=='__main__': main()
