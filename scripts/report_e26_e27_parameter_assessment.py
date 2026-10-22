"""Read-only final assessment, raw private-input audit, plots and editable declarations."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
from collections import Counter,defaultdict
from copy import deepcopy
from datetime import datetime,timezone
import gzip
import json
import argparse
import numpy as np
from classroom_swarm import repaired_config as config
from classroom_swarm.v4 import V4Log
import e25_plausible_parameter_fit as e25
import e26_protocol_parameter_fit as fit
import e27_teacher_belief_check as physical
from audit_e26_private_inputs import audit_private_inputs

REPO=fit.REPO; ROOTS=[e25.ROOT,fit.ROOT,physical.ROOT]
REPORT=REPO/'docs/reports/Plausible-parameter-study-assessment-2026-10-10.md'
SUMMARY=REPORT.with_name('E26-E27-summary-2026-10-10.json')
CACHE=REPO/'.tmp/E26-private-audit-cache.json'
FIGURE=REPO/'docs/experiments/figures/E26-E27-study-trends.png'

def audit_one(name):
    folder=Path(name); complete=config.load_config(folder/'complete.json')
    for path,digest in complete['hashes'].items(): assert config.sha256(folder/path)==digest,str(folder/path)
    with gzip.open(folder/'raw.json.gz','rt',encoding='utf-8') as handle: raw=json.load(handle)
    log=V4Log(raw['manifest']); log.tables=raw['tables']
    return str(folder.relative_to(REPO)),dict(complete_sha256=config.sha256(folder/'complete.json'),raw_hashes=len(complete['hashes']),**audit_private_inputs(log))

def audit(workers):
    folders=[p.parent for root in ROOTS for p in root.glob('*/*/cohort*/raw/*/complete.json')]
    cached=config.load_config(CACHE) if CACHE.exists() else {}
    pending=[p for p in folders if str(p.relative_to(REPO)) not in cached or cached[str(p.relative_to(REPO))]['complete_sha256']!=config.sha256(p/'complete.json')]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for index,future in enumerate(as_completed([pool.submit(audit_one,str(p)) for p in pending])):
            name,result=future.result(); cached[name]=result
            if (index+1)%100==0: config.save_json(CACHE,cached); print(f'Private inputs audited: {index+1}/{len(pending)} additional classrooms.',flush=True)
    config.save_json(CACHE,cached)
    print(f'{len(cached)} saved classrooms now have independently reconstructed private inputs.',flush=True)

def signature(r): return r['case'],r['a'],r['b'],r['group'],r['metric']
def fmt(v): return f'{v:+.3f}'
def ci(r): return f"{fmt(r['effect'])} [{fmt(r['lo95'])}, {fmt(r['hi95'])}]"

def figure(profiles):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    panels=[('STAR: small − regular',[('star','all','core_potential','small','regular')]),
        ('Tracking: tracked − mixed',[('kenya','low','core_potential','tracked','mixed'),('kenya','high','core_potential','tracked','mixed')]),
        ('AI: unaided exam',[('ai','all','core_potential','answer','none'),('ai','all','core_potential','tutor','answer'),('ai','all','core_potential','tutor','none')]),
        ('Seating and helper rewards',[('seating','low','core_potential','cross','random'),('seating','low','core_potential','reward','cross'),('seating','high','core_potential','reward','cross')]),
        ('Teacher incentives',[('teacher_rewards','all','familiar_potential','rewarded','unrewarded'),('teacher_rewards','all','familiar_participation','rewarded','unrewarded'),('teacher_rewards','all','novel_potential','rewarded','unrewarded')])]
    fig,axes=plt.subplots(3,2,figsize=(13,10)); colors=['#9ca3af','#0f766e','#7c3aed']
    for ax,(title,keys) in zip(axes.flat,panels):
        labels=[]
        for index,key in enumerate(keys):
            for offset,(name,rows) in enumerate(profiles.items()):
                matches=[r for r in rows if (r['case'],r['group'],r['metric'],r['a'],r['b'])==key]
                if not matches: continue
                r=matches[0]; y=index+(offset-1)*.18
                ax.errorbar(r['effect'],y,xerr=[[r['effect']-r['lo95']],[r['hi95']-r['effect']]],fmt='o',capsize=3,color=colors[offset],label=name if index==0 else None)
            labels.append(key[1]+' / '+key[2].replace('_potential','').replace('_participation',' participation')+' / '+key[3]+'−'+key[4])
        ax.set_yticks(range(len(keys)),labels); ax.axvline(0,color='#6b7280',linewidth=.8); ax.set_title(title,loc='left'); ax.set_xlabel('Model percentage-point difference (95% paired interval)'); ax.invert_yaxis(); ax.grid(axis='x',alpha=.2)
    axes.flat[-1].axis('off'); handles,labels=axes.flat[0].get_legend_handles_labels(); axes.flat[-1].legend(handles,labels,loc='upper left',frameon=False)
    axes.flat[-1].text(0,.65,'16 untouched paired cohorts\nFinal teacher parameters use a physical productivity cap.\nPublished study directions informed fitting.\nThese intervals describe simulation variability.',transform=axes.flat[-1].transAxes,va='top',fontsize=11)
    fig.suptitle('Audited policy and protocol corrections: conditional study trends',fontsize=15); fig.tight_layout(rect=(0,0,1,.96)); fig.savefig(FIGURE,dpi=180); plt.close(fig)

def generate():
    fit.verify(); physical.verify(); assert (fit.ROOT/'fresh-complete.json').exists() and (physical.ROOT/'fresh-complete.json').exists()
    assert not REPORT.exists(), 'preserve existing assessment'
    cached=config.load_config(CACHE); folders=[p.parent for root in ROOTS for p in root.glob('*/*/cohort*/raw/*/complete.json')]
    assert len(cached)==len(folders), 'audit every completed classroom before reporting'
    for folder in folders: assert cached[str(folder.relative_to(REPO))]['complete_sha256']==config.sha256(folder/'complete.json')
    legacy=config.load_config(fit.ROOT/'fresh/legacy/effects.json'); protocol=config.load_config(fit.ROOT/'fresh/protocol/effects.json')
    selected=config.load_config(fit.ROOT/'fresh/selected/effects.json'); capped=config.load_config(physical.ROOT/'fresh-effects.json')
    final=[r for r in selected if r['case'] not in physical.CASES]+capped
    final.sort(key=lambda r:next((i for i,s in enumerate(fit.TARGETS+fit.SECONDARY_TARGETS) if signature(r)==signature(s)),100))
    params=config.load_config(physical.ROOT/'selection-lock.json')['parameters']; vector=config.load_config(physical.ROOT/'selection-lock.json')['vector']
    profiles={'A33 legacy':legacy,'A34 protocol defaults':protocol,'Final bounded settings':final}; figure(profiles)
    primary=[r for r in final if signature(r) in {signature(s) for s in fit.TARGETS}]
    results={name:config.load_config(root/'fresh-complete.json') for name,root in [('E26',fit.ROOT),('E27',physical.ROOT)]}
    counts={k:sum(v[k] for v in cached.values()) for k in ('benefit_inputs','service_inputs','request_costs','raw_hashes')}
    activity={}
    for label,root in [('protocol',fit.ROOT),('selected',fit.ROOT)]:
        by=fit.aggregate(config.load_config(root/f'fresh/{label}/all-class-metrics.json'))
        activity[label]=by
    activity['capped']=fit.aggregate(config.load_config(physical.ROOT/'fresh-metrics.json'))
    def avg(label,case,arm,key,group='all'):
        values=[v[key] for k,v in activity[label].items() if k[:3]==(case,arm,group) and v[key] is not None]
        return float(np.mean(values)) if values else None
    comparisons=[]
    for r in primary:
        a=next(s for s in legacy if signature(s)==signature(r)); b=next(s for s in protocol if signature(s)==signature(r))
        comparisons.append(dict(spec=signature(r),legacy=a,protocol=b,final=r))
    summary=dict(created_utc=datetime.now(timezone.utc).isoformat(),parameters=params,
        primary=primary,secondary=[r for r in final if r not in primary],profiles=profiles,
        pattern_matches=sum(r['direction_match'] for r in primary),simultaneous_matches=sum(r['robust_match'] for r in primary),
        independent_private_checks=counts,classrooms=len(cached),runs=results,
        teacher_activity={f'{case}/{arm}/{key}':avg('capped',case,arm,key) for case in physical.CASES for arm in (('small','regular') if case=='star' else ('unrewarded','rewarded')) for key in ('teacher_spent','guidance_count','explanation_count','coaching_count','group_coaching_count','followup_count','familiar_participation')},
        peer_activity={f'{arm}/{key}':avg('selected','seating',arm,key) for arm in ('cross','reward') for key in ('contract_sessions','peer_sessions','helper_gain','productive_fraction')},
        design_limits=['after-class elective teacher coaching absent','full lab task/rank/teachback protocol absent','full composition protocol absent','human units/preferences/initial mastery uncalibrated','threshold changes teaching criterion and physical readiness','AI tutor assisted-practice gain remains smaller than answer-AI gain, contrary to paper ordering'])
    config.save_json(SUMMARY,summary)
    lines=['# Plausible parameters and multi-study trend assessment','',
        'Date: 2026-10-10. A34 policy correction; E25 exploratory search, E26 protocol correction and E27 physical teacher-belief check. All earlier engines and results remain preserved.','',
        f"**Result:** {summary['pattern_matches']}/{len(primary)} selected primary model patterns satisfy the declared directional or near-zero mean criteria on sixteen untouched cohorts; {summary['simultaneous_matches']}/{len(primary)} satisfy the stricter simultaneous interval criteria. These are conditional checks of a target subset after fitting to published directions, not complete paper reproductions, independent external validation or estimates of human parameters.",'',
        '## What changed and why','',
        'A34 reconnects returned-grade attempt/hint beliefs and expected hint-service availability to effort/activity choice. It charges the request’s operational cost consistently, initializes dependent beliefs from effective component knowledge, and rejects missing or inconsistent curriculum/policy evidence. Explicit independent priors remain explicit. No new AI penalty, background learning or treatment-specific learning multiplier is introduced.','',
        'E25 found a further setup problem: unpaid-study templates inherited teacher reward strength 1. Its complete 24-vector search and independent selection are retained, but its fresh pool was left unrun and its fitted recipe is not treated as a valid field comparison. E26 explicitly disables pay contracts outside the incentive study and permits the existing individualized explanation in STAR. It requires delivered teacher support, test preparation and rewarded helping, rather than score signs alone. The STAR protocol change is bundled; it cannot identify reward removal separately from explanation availability. Its additional policy-only arm isolates A34’s repair against A33 on the original STAR setup.','',
        'E26 selected a teacher gain belief of 0.04, exceeding the ordinary-teaching physical ceiling. E27 capped it at 0.0584/3 = 0.0194667 per productive reference dose before fresh outcomes. Independent selection chose cap-only; changing costs or intrinsic concern further was unnecessary. Actor optimism is possible, but this final recipe does not rely on optimism above the simulator’s conditional maximum. Engagement, usefulness and prerequisites can reduce actual uptake further.','',
        '## Parameter design: coherent does not mean empirically established','',
        'Knowledge, content quality, confidence and probabilities lie on 0–1 scales. Ticks are abstract schedule units; three ticks define one reference dose. They are not calibrated classroom minutes. Teacher/helper costs and rewards are actor utility values, not salary amounts. The 0.0584 physical alpha is a prior trajectory assumption. Initial latent knowledge distributions are not measured human exam-score distributions. Study class sizes and assignments are fixed protocol controls.','',
        '| Final parameter | Value | Interpretation and assessment |','|---|---:|---|']
    descriptions={
        'observation_update':'Fraction of a released observation used in tracking updates; bounded 0.5–1. Plausible partial updating, unmeasured.',
        'mastery_threshold':'Prerequisite criterion; bounded 0.6–0.8. Also changes physical readiness, so its contribution is bundled.',
        'teacher_linear_cost':'Utility per work tick; bounded 0.0001–0.002. Positive and shared across studies; no human cost estimate.',
        'teacher_convex_cost':'Existing resulting-work-fraction penalty coefficient; bounded 0.0005–0.004. Not the marginal difference of total work disutility.',
        'teacher_intrinsic':'Utility weight on projected average conceptual gain; bounded 0.1–1. Shared between paid/unpaid arms; not calibrated.',
        'teacher_gain_belief':'Expected headroom gain per productive reference dose. Capped to the model’s maximum; actual expectation may be lower.',
        'helper_intrinsic':'Small intrinsic utility for effortful helping; bounded 0.01–0.04, applies to ordinary and rewarded helping.',
        'helper_cost':'Effort cost relative to ordinary work; bounded 0.75–1.5. Positive, shared across peer treatments.',
        'exam_access_cost':'Utility barrier for the Kenyan incentive exam; bounded 0.25–0.4. With heterogeneous confidence, gives partial participation; not observed attendance data.',
        'material_quality':'Usable corrective content probability; bounded 0.6–1, common to all AI and control arms.'}
    for name,value in params.items(): lines.append(f'| {name} | {value:.7g} | {descriptions[name]} |')
    lines+=['','Protocol values never optimized: student counts (STAR 15/24), exogenous assignments and ability cohorts, physical alpha, time budgets, teacher skill, reward strength/prize, AI use capacity, transfer matrices, test design and experiment length. Other parameters remain the inherited explicitly declared hypotheses. Initial incentive-study confidence equals effective latent mean knowledge: this produces heterogeneity but assumes perfect initial alignment, which is not established for the human sample. No interpretation of these values as measured human preferences is justified. High concern/low work costs remain weakly identified; the finite search does not uniquely identify them.','',
        'The search uses ten bounds, shared teacher/helper preferences and a small prior-distance penalty. It fits directions and declared model-resolution bands, rather than exact published coefficients with incompatible units. Hard screens reject dormant interventions, fewer than 20% productive dose events or below 60% baseline enrolled exam participation. Those screens are declared plausibility checks, not paper-estimated cutoffs. Every failed candidate remains saved.','',
        '## Fresh study comparisons','',
        'All numbers below are model percentage points. Brackets are paired 95% intervals across the sixteen simulated cohorts. They are not uncertainty intervals for the papers’ effects. Simultaneous support uses the declared fifteen-target family. Near-zero support requires its simultaneous interval to fit entirely inside the declared band; nonsignificance alone is insufficient.','',
        '| Study / outcome / contrast | A33 default | A34 protocol default | Final bounded settings | Mean / simultaneous criterion |','|---|---:|---:|---:|---|']
    for r in primary:
        c=next(c for c in comparisons if c['spec']==signature(r)); label=f"{r['case']}, {r['group']}, {r['metric']}, {r['a']} − {r['b']}"
        lines.append(f"| {label} | {fmt(c['legacy']['effect'])} | {fmt(c['protocol']['effect'])} | {ci(r)} | {'pass' if r['direction_match'] else 'miss'} / {'pass' if r['robust_match'] else 'uncertain or miss'} |")
    lines+=['','![Fresh paired study contrasts](../experiments/figures/E26-E27-study-trends.png)','',
        'The [STAR paper](https://www.nber.org/papers/w6051) supports a small-class achievement advantage. Here that requires a finite teacher support channel and appropriate work preferences; no class-size learning bonus is encoded. [Tracking in Kenya](https://www.aeaweb.org/articles?id=10.1257/aer.101.5.1739) motivates instructional adaptation. Both starter groups matter, and the fitted observer/threshold choices change lesson selection as well as readiness. The ability distribution was held fixed.','',
        'The [AI trial](https://www.pnas.org/doi/10.1073/pnas.2422633122) motivates separate assisted homework and unaided exams. The fit retains answer-AI harm and tutor mitigation through changed practice/content, without a direct AI penalty. The [seating/reward study](https://www.aeaweb.org/content/file?id=15848) motivates actual incentivized helping and lower/upper comparisons. A small upper effect may satisfy our engineering band even if statistically distinguishable from zero; that is not proof of a human null.','',
        'A further unfitted AI check still disagrees with the paper: the human tutor arm had the larger assisted-practice improvement, whereas this model gives answer AI the larger homework improvement. Declared answer accuracy is 0.9 and hint strength is 0.25; these were not estimated from the field tools or optimized here. This is a tool-content/usage parameter and protocol gap, not a reason to add a direct AI outcome bonus. The selected unaided-exam directions do not establish full AI-study reproduction.','',
        'The [Kenyan incentive trial](https://www.aeaweb.org/articles?id=10.1257/app.2.3.205) motivates linked-test preparation and participation. Familiar-test and enrollment-denominator participation outputs are both checked, alongside novel concept scores. Zero-transfer unrelated scores and invariant compulsory instruction/teacher attendance are structural identities here, not recovered field findings. Preparation is scheduled in reserved class time, whereas the field’s additional sessions occurred outside normal class hours; this remains a protocol gap.','',
        '## Activity evidence and effects on earlier conclusions','',
        '| Final teacher context | Support/preparation per block | Teacher work per block |','|---|---|---:|']
    for case,arms in [('star',('small','regular')),('teacher_rewards',('unrewarded','rewarded'))]:
        for arm in arms:
            lines.append(f"| {case}/{arm} | guidance {avg('capped',case,arm,'guidance_count'):.3f}; explanation {avg('capped',case,arm,'explanation_count'):.3f}; coaching {avg('capped',case,arm,'coaching_count'):.3f}; followup {avg('capped',case,arm,'followup_count'):.3f} | {avg('capped',case,arm,'teacher_spent'):.3f} / 8 |")
    lines+=['',f"Rewarded helper sessions: {avg('selected','seating','reward','contract_sessions'):.4f} per student/block; cross-rank control: {avg('selected','seating','cross','contract_sessions'):.4f}. These are delivered sessions with actual student effort/time, not payments credited as learning.",'',
        'The paired legacy/protocol/final table preserves earlier reversals. Primary changes are decomposed in `fresh-changes.json`; STAR’s separate policy-only comparison is also saved. Changes from protocol default to fitted setup are bundled parameter interventions. They cannot identify which fitted coefficient caused an effect. Frozen E23/E24 results remain unchanged and should still be cited when describing the historical model.','',
        '| Secondary check | Final effect [95% interval] |','|---|---:|']
    for r in summary['secondary']: lines.append(f"| {r['case']}, {r['group']}, {r['a']} − {r['b']} | {ci(r)} |")
    lines+=['','The single-lab protocol still omits observed ranks, richer task structure and optional teachback; the repeated-practice probe is not that experiment. Some high starters have mastered the tested foundation component, making an upper null partly an identity. Composition remains a partial ability-mean probe without the full dropout/placement protocol. These probes cannot establish replication of those papers.','',
        '## Design problems versus parameter problems','',
        'Confirmed implementation/configuration problems were repaired: disconnected practice beliefs, ignored service probability, initial-state dependencies, missing-ledger acceptance and unintended teacher rewards. Restricting STAR to preference nudges excluded an already implemented instructional interaction; E26 enables it under the same capacity limit. No additional software tool or treatment-specific outcome multiplier was needed.','',
        'Within the corrected engine, lesson adaptation, helping incentives and work preferences explain parameter sensitivity. The bounded fit and physical ceiling are evidence that a coherent conditional configuration exists for supported patterns. They do not show these are the true human settings or that the tested design is uniquely correct. Missed/uncertain patterns in the limited search are not proof of a missing interaction. Known after-class, laboratory and composition gaps are protocol omissions and should be addressed in separately specified studies before stronger claims.','',
        '## Backpropagation and evidence limits','',
        'The NumPy agent simulator has discrete actions/effort, argmax decisions, random gates and changing schedules. Direct pathwise backpropagation is unsuitable without replacing/relaxing those mechanisms. The bounded evolutionary search follows the gradient-free population approach described in [official SciPy documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.differential_evolution.html), using existing NumPy dependencies. A differentiable surrogate would need its own fidelity check; it was not added.','',
        f"{len(cached):,} new saved classrooms across E25/E26/E27 passed live/reloaded engine audits; {counts['raw_hashes']:,} raw-file hashes were independently rechecked. The post-run audit reconstructs {counts['benefit_inputs']:,} private benefit inputs, {counts['service_inputs']:,} weighted service inputs and {counts['request_costs']:,} charged hint requests from released history. All source locks are preserved. Tests: see the frozen final test output and source manifest.",'',
        'Development and selection used separate cohorts; both final selections were locked before fresh data. The papers’ directions informed fitting, so fresh simulated seeds test internal robustness rather than independent external validation. Further evidence requires measured initial skill distributions, attendance/work/activity data and a study not used to select the setup. Shared preferences and physiological constraints improve discipline, but cannot replace that evidence.','',
        '## Reproduce and inspect','',
        '- Model: [A34 specification](../26-v4-policy-repair.md).','- Search protocols: [E25](../experiments/E25-plausible-fit-plan.md), [E26](../experiments/E26-protocol-fit-plan.md), [E27](../experiments/E27-teacher-belief-check-plan.md).',
        '- Full raw/declarations/rejections: `runs/E25-plausible-fit-r1`, `runs/E26-protocol-fit-r1`, `runs/E27-teacher-belief-check-r1`.','- Machine-readable final assessment: `E26-E27-summary-2026-10-10.json`; manifest freezes the report, evidence, raw completion digests and new source files.','- Editable A34 case configurations are separate from scientific locks, with fresh example seeds. They are conditional fitted hypotheses, not human calibrated defaults.','',
        'Completed: audited corrections, protocol repair, bounded joint fitting, physical-belief check and fresh multi-study comparison. Waiting: no required user decision. Remaining scientific work: independent human calibration/validation and explicitly specified after-class/lab/composition protocols.']
    REPORT.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    examples=[]
    for index,case in enumerate(fit.MAIN):
        c=config.template(); c.update(seed=982600+index,replicates=1,experiment_id='A34_fitted_hypothesis_'+case)
        c['extensions']['learning_process']['enabled']=True
        c['conditions']=[deepcopy(j['resolved']) for j in fit.jobs('fresh',0,'illustration',vector,cases=(case,))]
        config.preflight(config.resolve_config(c)); path=REPO/f'configs/A34-fitted-{case}.json'; assert not path.exists(); config.save_json(path,c); examples.append(path)
    private_path=REPORT.with_name('E26-E27-private-input-audit-2026-10-10.json'); config.save_json(private_path,cached)
    files=[REPORT,SUMMARY,FIGURE,private_path,Path(__file__),REPO/'scripts/audit_e26_private_inputs.py',REPO/'tests/test_e26_private_inputs.py',REPO/'.tmp/E26-final-test-output.txt']
    files += [root/name for root in ROOTS for name in ('design-lock.json','search-complete.json','selection-lock.json','fresh-complete.json','fresh-effects.json','fresh-assessment.json','fresh-metrics.json','fresh-changes.json','development-results.json','selection-results.json') if (root/name).exists()]
    files += [p for root in ROOTS for p in root.glob('generation*-results.json')]
    files += [p for root in ROOTS for p in root.glob('fresh/*/*.json')]
    files += [p for root in ROOTS for p in root.glob('*/*/cohort*/run-complete.json')]
    files += [p for root in ROOTS for p in root.glob('*/*/cohort*/class-metrics.json')]
    files += [p for root in ROOTS for p in root.glob('*/*/cohort*/raw-inventory.json')]
    manifest=dict(created_utc=datetime.now(timezone.utc).isoformat(),sources={str(p.relative_to(REPO)).replace('\\','/'):config.sha256(p) for p in files},
        editable_example_snapshots={str(p.relative_to(REPO)):config.sha256(p) for p in examples},
        raw_completion_digests={name+'/complete.json':r['complete_sha256'] for name,r in cached.items()},
        status='final selections frozen before fresh; post-run private-input audit read-only; parameter hypotheses uncalibrated')
    config.save_json(REPORT.with_suffix('.sources.json'),manifest)
    print(f'Report saved: {summary["pattern_matches"]}/{len(primary)} mean criteria, {summary["simultaneous_matches"]} simultaneous; {len(cached)} audited classrooms.',flush=True)

def main():
    p=argparse.ArgumentParser(); p.add_argument('command',choices=['audit','generate']); p.add_argument('--workers',type=int,default=8); a=p.parse_args()
    if a.command=='audit': audit(a.workers)
    else: generate()

if __name__=='__main__': main()
