"""Publish the preserved E18 failure and E19 setup fit with all fresh controls."""
from __future__ import annotations
import csv
import json
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'scripts'))
import e19_teacher_studies as e19
import e18_teacher_studies as e18
from classroom_swarm.teacher_config import preflight


def effect(rows,study,profile,group,metric='exam',control='main'):
    return next(r for r in rows if (r['study'],r['profile'],r['group'],r['metric'],r['control'])==(study,profile,group,metric,control))


def interval(r,simultaneous=False):
    keys=('simultaneous_lo95','simultaneous_hi95') if simultaneous else ('lo95','hi95')
    return f"{r['effect']:+.3f} [{r[keys[0]]:+.3f}, {r[keys[1]]:+.3f}]"


def examples(selection):
    paths=[]
    # New input seeds/cohorts, never executed by this report.
    for study,mean in [('star',.5),('kenya',e19.resolve_profile('kenya',selection['kenya']['profile'])['population'].get('mean',.5))]:
        jobs=[j for j in e19.jobs('confirmation',0,selection) if j['study']==study and j['control']=='main' and j['profile']==selection[study]['profile']]
        for j in jobs:
            n=j['resolved']['params']['N']
            poolseed=10062101 if study=='star' else 10062102
            pop=e19.cohort(study,poolseed,0,n=n,mean=mean)
            ids=pop['mixed'][0] if study=='star' else pop[j['arm']][j['section']]
            c=j['config']
            c['seed']=poolseed+1000+j['section']
            c['experiment_id']='E19_editable_'+study
            c['initial']['knowledge']={'kind':'values','values':[pop['knowledge'][i] for i in ids]}
            c['teacher']['observation_prior']=float(np.mean([pop['observed_baseline'][i] for i in ids]))
            c['notes']='Editable selected setup, fresh unused seeds. One class only; use full E19 school pipeline for comparison.'
            preflight(e19.resolve_config(c))
            path=REPO/'configs'/f"E19-{study}-{j['arm']}-s{j['section']}-example.json"
            if path.exists():raise ValueError('Preserve existing example')
            e19.save_json(path,c);paths.append(path)
    return paths


def main():
    root=REPO/'runs/E19-teacher-study-r1'
    lock=e19.verify(root);selection=e19.selected(root)
    sourcepaths=[]
    for stage in ('development','confirmation'):
        derived=root/f'{stage}_derived'
        manifest=e19.load_config(derived/'analysis_manifest.json')
        assert manifest['raw_audits']=='all passed'
        for name,digest in manifest['hashes'].items():assert e19.sha256(derived/name)==digest
        for item in manifest['inventory']:
            assert e19.sha256(root/stage/'raw'/f"rep{item['replicate']:04d}"/item['condition']/'complete.json')==item['complete_sha256']
        sourcepaths.extend([derived/'analysis_manifest.json',derived/'effects.json'])
    execution=e19.load_config(root/'confirmation-execution-lock.json')
    for name,digest in execution['sources'].items():assert e19.sha256(REPO/name)==digest
    development=e19.load_config(root/'development_derived/effects.json')
    confirmation=e19.load_config(root/'confirmation_derived/effects.json')
    old=e18.load_config(REPO/'runs/E18-teacher-study-r1/confirmation_derived/effects.json')
    oldnames={s:r['profile'] for s,r in e18.selected(REPO/'runs/E18-teacher-study-r1').items()}
    names={s:r['profile'] for s,r in selection.items()}
    with (root/'confirmation_derived/run_metrics.csv').open(newline='',encoding='utf-8') as h:
        metrics=list(csv.DictReader(h))
    def armvalues(study,profile,control,arm,group,key):
        rows=sorted([r for r in metrics if (r['study'],r['profile'],r['control'],r['arm'],r['group'])==(study,profile,control,arm,group)],key=lambda r:int(r['replicate']))
        assert len(rows)==80
        return np.asarray([float(r[key]) for r in rows])
    def mean(study,profile,control,arm,group,key):return float(armvalues(study,profile,control,arm,group,key).mean())
    def contribution(study,group,profile,control):
        a,b=('small','regular') if study=='star' else ('tracked','mixed')
        selected=armvalues(study,names[study],'main',a,group,'exam')-armvalues(study,names[study],'main',b,group,'exam')
        comparator=armvalues(study,profile,control,a,group,'exam')-armvalues(study,profile,control,b,group,'exam')
        return e19.paired(selected-comparator)
    primary=[effect(confirmation,'star',names['star'],'all'),effect(confirmation,'kenya',names['kenya'],'low'),effect(confirmation,'kenya',names['kenya'],'high')]
    allmeans=all(r['effect']>0 and effect(confirmation,r['study'],r['profile'],r['group'],'knowledge_gain')['effect']>0 for r in primary)
    pointwise=sum(r['lo95']>0 for r in primary);simultaneous=sum(r['simultaneous_lo95']>0 for r in primary)
    classrooms=sum(e19.load_config(root/stage/'complete.json')['classrooms'] for stage in ('development','confirmation'))
    report=REPO/'docs/experiments/E19-teacher-study-results.md'
    if report.exists():raise ValueError('Report already exists; preserve historical report')
    status='All three selected exam and knowledge mean directions match the target studies.' if allmeans else 'The selected setups still do not reproduce every target exam and knowledge direction.'
    lines=['---','type: experiment-results','updated: 2026-10-06','---',
        '# Teacher study comparisons — setup adjustments and fresh checks','',
        f"**{status}** In E19, **{pointwise}/3** target exam contrasts have pointwise 95% intervals above zero; **{simultaneous}/3** have simultaneous intervals above zero. This is conditional agreement after fitting to known study directions, not independent human validation.",'',
        f"E19 completed **{classrooms:,} classroom runs**, after the preserved **1,848 E18 runs**. Its development panel used 20 paired replicates; confirmation used 80 fresh replicates per comparison. All raw outputs were re-read, hash-checked and audited. **521 tests pass**, including deterministic raw-table parity for the confirmation transport. **{lock['historical_entries_verified']} historical source entries** matched. The A30 teacher engine and every previous experiment remain unchanged.",'',
        '## Human comparisons and model counterparts','',
        '| Study | Reported direction | Model comparison | What is missing |','|---|---|---|---|',
        '| [Project STAR / Krueger](https://www.nber.org/papers/w6051) | Smaller classes improve test outcomes | 15 versus 24 students, one teacher with the same total budget, equal realized initial knowledge mean 0.45 and SD 0.10 | Disruption, aides, demographic mechanisms, measured teacher workload and human time scale |',
        '| [Duflo, Dupas and Kremer: Kenyan tracking](https://www.povertyactionlab.org/sites/default/files/research-paper/39%20Peer%20Effects%2C%20Teacher%20Incentives%2C%20and%20the%20Impact%20of%20Tracking%20Project.pdf) | Tracking benefits students across initial achievement levels | Same 84 students in two mixed or two baseline-test tracks of 42; teachers adapt to observed scores; equal school resources | Full teacher incentives/effort mechanism, topics, measured peer behavior and demographic calibration |','',
        'Lower/higher groups are defined by noisy baseline-assessment ranks before assignment. Teachers use recorded baseline priors and released assessment signals, without access to current hidden competence. Mean-based instructional adaptation is an inferred mechanism proxy. These model percentage points are not the papers’ standardized effects or percentile ranks.','',
        '## What the first attempt showed','',
        'The [E18 report](E18-teacher-study-results.md) is preserved with every tested setup. Its selection preferred the fewest changed settings among positive development means. That selected a nearly null STAR reference and a tracking teacher-content multiplier of two. Fresh seeds did not confirm the complete pattern. E19 was declared after seeing this limitation, so the entire second round is exploratory, including its new seed pool.','',
        '| Target | E18 fresh exam effect | E19 fresh exam effect | E19 fresh knowledge/gain effect | E19 simultaneous exam interval |',
        '|---|---:|---:|---:|---:|']
    for label,r in zip(['Small class: overall','Tracking: lower starting half','Tracking: higher starting half'],primary):
        previous=effect(old,r['study'],oldnames[r['study']],r['group'])
        knowledge=effect(confirmation,r['study'],r['profile'],r['group'],'knowledge_gain')
        lines.append(f'| {label} | {interval(previous)} | {interval(r)} | {interval(knowledge)} | {interval(r,True)} |')
    lines+=['','Brackets are paired Monte Carlo intervals. Simultaneous intervals cover the three selected exam contrasts only. Knowledge, controls and development intervals are pointwise descriptive checks. Fresh seeds evaluate simulator repeatability after selection; they do not supply held-out human evidence.','',
        '![Fresh comparisons and controls](figures/E19-teacher-study-comparisons.png)','',
        '## Selected setup changes','',
        'The [E19 plan](E19-teacher-study-plan.md) froze eight class-size and ten tracking candidates before its outcomes. Selection required all relevant knowledge and exam lower bounds above zero and exam means at least +0.15 model points; it then preferred fewer changes. A failed development gate remains explicitly marked. Confirmation did not reselect.','',
        '| Study | Selected profile | Development gate met | Exact changes from E19 reference |','|---|---|---|---|']
    for study in ('star','kenya'):
        patch=e19.resolve_profile(study,names[study]);changes={k:patch[k] for k in ('teacher','params','population') if patch[k]}
        lines.append(f"| {study} | {names[study]} | {selection[study]['development_target_met']} | `{json.dumps(changes,sort_keys=True)}` |")
    if names['star']=='guidance_03_longer_day':
        lines+=['','The selected class-size setup changes guidance strength **0.10 → 0.30** and the student session **12 → 18 model ticks** in both class sizes. The teacher budget stays **8 ticks** in both. There is no established conversion from these ticks to classroom minutes; this is an opportunity/productivity hypothesis, not a claim that STAR lengthened the smaller class’s day.']
    if names['kenya']=='population_mean_045':
        lines+=['','The selected tracking population changes mean initial knowledge **0.50 → 0.45**, keeping the same **0.60 span** and realized SD (about **0.175**). The range becomes **0.15–0.75** rather than 0.20–0.80. Both assignment arms use exactly the same shifted students. The lower starting level shifts observed instructional targets and remaining learning capacity while preserving heterogeneity. In this engine, lower difficulty can improve teacher-content correctness; novelty depends on the difficulty–student-knowledge gap, so shifting both does not automatically make lessons more novel. The study does not identify this scalar mean.']
    if not selection['kenya']['development_target_met']:
        lines+=['','**Tracking missed the declared development confidence gate.** The rule selected the best tentative candidate by its minimum exam lower bound. Fresh outcomes are reported without changing that status; a positive fresh result cannot retroactively turn the development gate into a pass.']
    lines+=['','E19’s STAR reference is the original instruction/guidance setup. Its Kenyan reference already includes E18’s teacher-content multiplier **2**, compared with the original A30 default **1**. A selected multiplier **4**, if present above, is therefore 2 → 4 within E19 and 1 → 4 against the original default. This coefficient scales completed usable teacher content; it does not multiply all learning or bypass attendance, time, correctness, novelty or readiness.','',
        'Population mean shifts, wider readiness, stronger guidance and shorter/more productive explanations are hypotheses selected using known target directions. They are exposed in the configuration and not established properties of either human sample. Action-list/duration/productivity bundles cannot attribute their effect to one component. Scalar knowledge and alpha 0.0584 remain assumed numerical trajectories, not human estimates.','',
        '## Mechanism and protocol controls','',
        '| Comparison | Exam effect, pointwise 95% | Interpretation |','|---|---:|---|']
    controls=[('STAR: selected','star',names['star'],'all','main','Same total teacher resources across sizes.'),
        ('STAR: reference','star','reference','all','main','Original observed instruction/guidance protocol.'),
        ('STAR: selected teacher disabled','star','no_teacher','all','disabled','Same student setup and day length; teacher removed.'),
        ('STAR: selected calendar with zero support','star','zero_support','all','zero_support','Same durations/calendar, all teacher benefit channels zero.'),
        ('STAR: equal guidance time per student','star','scaled_guidance','all','scaled','Different guidance-only protocol; appointment fragmentation remains.')]
    for group in ('low','high'):
        controls += [(f'Kenya {group}: reference','kenya','reference',group,'main','Multiplier 2, original readiness band.'),
            (f'Kenya {group}: fixed curriculum','kenya','fixed_curriculum',group,'fixed','Selected settings; difficulty fixed at 0.5.'),
            (f'Kenya {group}: peer access','kenya','with_peers',group,'peers','Selected settings plus voluntary static-network peer practice.')]
    for label,study,profile,group,control,meaning in controls:
        lines.append(f'| {label} | {interval(effect(confirmation,study,profile,group,control=control))} | {meaning} |')
    lines+=['','A nonzero control can arise from finite samples, slot-specific draws, population composition or scheduling. Equal average guidance time does not guarantee equal usable practice opportunities. The zero-support calendar can reduce practice without teaching anything. Positive selected effects should therefore be read alongside teacher-induced contrasts, rather than credited to class size alone.','',
        '| Paired difference between treatment contrasts | Exam difference, pointwise 95% |','|---|---:|---:|',
        f"| STAR selected minus corresponding teacher-disabled size contrast | {interval(contribution('star','all','no_teacher','disabled'))} |",
        f"| STAR selected minus corresponding zero-support size contrast | {interval(contribution('star','all','zero_support','zero_support'))} |",
        f"| Kenya lower: adaptive minus fixed-curriculum tracking contrast | {interval(contribution('kenya','low','fixed_curriculum','fixed'))} |",
        f"| Kenya higher: adaptive minus fixed-curriculum tracking contrast | {interval(contribution('kenya','high','fixed_curriculum','fixed'))} |",'',
        'These differences are conditional intervention diagnostics. Fixed 0.5 is one comparator, not the field study’s untreated instruction. Peer sensitivity changes an additional interaction channel and must be reported even if it reverses a match.','',
        '## Time and learning evidence','',
        'Cumulative means per student across 12 episodes. Content gain is the recorded teacher component, not net treatment gain. Practice time excludes teacher appointments.','',
        '| Selected arm/group | Exam | Knowledge gained | Practice ticks | Teacher ticks | Guidance appointments | Teacher content gain | Lesson difficulty | Usable content fraction |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for study,arms,groups in [('star',['small','regular'],['all']),('kenya',['mixed','tracked'],['low','high'])]:
        for group in groups:
            for arm in arms:
                values=[mean(study,names[study],'main',arm,group,key) for key in ['exam','knowledge_gain','practice_ticks','teacher_ticks','guidance_count','teacher_gain','teacher_difficulty','teacher_usable']]
                lines.append(f'| {study}/{arm}/{group} | '+' | '.join(f'{v:.3f}' for v in values)+' |')
    lines+=['','Tracking holds broadcast duration and student membership fixed. Observed curriculum targets, content usefulness and subsequent practice choices can vary. Smaller classes change per-student appointments under a fixed total teacher budget; appointment costs can cancel learning gains. Neither positive net sign is guaranteed by the engine.','',
        '## Every E19 development candidate','',
        'Intervals below cover 20 exploratory replicates. They were used for selection, have search multiplicity and are not independent support. All failed and opposite candidates are retained. Exact parent patches are in the locked script/design.','',
        '| STAR candidate | Changes from reference | Exam difference | Knowledge/gain difference |','|---|---|---:|---:|']
    for p in e19.profiles()['star']:
        patch=e19.resolve_profile('star',p['name']);changes={k:patch[k] for k in ('teacher','params','population') if patch[k]}
        lines.append(f"| {p['name']} | `{json.dumps(changes,sort_keys=True)}` | {interval(effect(development,'star',p['name'],'all'))} | {interval(effect(development,'star',p['name'],'all','knowledge_gain'))} |")
    lines+=['','| Kenya candidate | Changes from reference | Lower exam | Higher exam | Lower knowledge/gain | Higher knowledge/gain |','|---|---|---:|---:|---:|---:|']
    for p in e19.profiles()['kenya']:
        patch=e19.resolve_profile('kenya',p['name']);changes={k:patch[k] for k in ('teacher','params','population') if patch[k]}
        values=[interval(effect(development,'kenya',p['name'],g,m)) for m in ('exam','knowledge_gain') for g in ('low','high')]
        lines.append(f"| {p['name']} | `{json.dumps(changes,sort_keys=True)}` | "+' | '.join(values)+' |')
    lines+=['','## Are the fitted assumptions sensible?','',
        '| Assumption | Assessment and practical limit |','|---|---|',
        '| One teacher with a finite class budget | Plausible resource constraint; workload/tick quantities need field measurements. It creates more potential attention in smaller classes, not a guaranteed outcome gain. |',
        '| More effective brief individual explanation | Individual diagnosis and explanation can plausibly improve productivity. A multiplier or two-tick lesson selected for the sign is not evidence of that real productivity or duration. |',
        '| Stronger guidance | Plausible support for voluntary practice; its utility scale/decay are numerical assumptions and require behavior data. |',
        '| Wider readiness band | Can represent scaffolding or curriculum accessibility. It must be assessed against observed gains from above-level material, not accepted because tracking becomes positive. |',
        '| Adaptive observed-score curriculum | Respects teacher information limits and represents targeting. Mean-based targets omit the paper’s incentive/effort model and topic-specific instruction. |',
        '| Population mean/spread | Initial heterogeneity is relevant, but these scalar moments lack a study-test mapping. A mean shift can be illustrative; it is not empirical calibration. |',
        '| High skill, full attendance and frequent assessment | Optimistic controlled settings. Real attendance, observation noise/coverage and teacher workload may change the signs. |',
        '| Scalar monotone knowledge | Omits forgetting, misconceptions, topic transfer and rich dialogue. Agreement of two final signs cannot identify these missing mechanisms. |',
        '| Fresh confirmation and control contrasts | Useful numerical checks after fitting. Independent participant data or a held-out human protocol is needed for external validation. |','',
        ('A defensible claim is: “Under explicitly stated, study-informed setup assumptions, the simulation shows similar mean directions to both selected studies; uncertainty and mechanism controls are reported.”' if allmeans else
         'A defensible claim is: “The simulation partially agrees with the selected studies under explicitly stated, study-informed setup assumptions; the remaining mismatches and uncertainty are reported.”')+' Avoid claiming an empirically validated classroom model or reproduction of the papers’ numerical effect sizes.','',
        '## Saved settings and reproducibility','',
        'Raw data and class JSON declarations are in `runs/E19-teacher-study-r1/development` and `confirmation`; paired run metrics/effects, source-linked audit manifests, selection review and both cohort pools are retained alongside them. E18’s earlier null/incomplete results remain available. The [execution addendum](E19-execution-addendum.md) records equivalent parallel confirmation execution; its source lock was written before confirmation outcomes.','',
        'The following editable examples have fresh unused seeds and passed configuration validation. Each file is a single class; it does not alone reproduce the paired school comparison.']
    samplepaths=examples(selection)
    for p in samplepaths:lines.append(f"- [{p.name}](../../configs/{p.name})")
    lines+=['','The full comparison is reproducible with `scripts/e19_teacher_studies.py` (`prepare`, `run`, `analyze`, `select`, `verify`) against a new output root; confirmation may use the parallel driver. Preserve existing roots and source locks.','',
        'Progress: study comparisons, bounded setup adjustments, fresh checks and assumption assessment completed; no input pending. Next: independent human calibration and remaining teacher-incentive, workload, topic and peer-observation mechanisms.']
    report.write_text('\n'.join(lines)+'\n',encoding='utf-8')
    fig,axes=plt.subplots(1,3,figsize=(14,6),layout='constrained')
    panels=[('STAR: small − regular','star','all',[(names['star'],'main','Selected'),('reference','main','Reference'),('no_teacher','disabled','Teacher disabled'),('zero_support','zero_support','Zero support'),('scaled_guidance','scaled','Equal guidance time')]),
        ('Kenya: lower starting half','kenya','low',[(names['kenya'],'main','Selected'),('reference','main','Reference'),('fixed_curriculum','fixed','Fixed curriculum'),('with_peers','peers','Peer access')]),
        ('Kenya: higher starting half','kenya','high',[(names['kenya'],'main','Selected'),('reference','main','Reference'),('fixed_curriculum','fixed','Fixed curriculum'),('with_peers','peers','Peer access')])]
    for ax,(title,study,group,entries) in zip(axes,panels):
        for y,(profile,control,label) in enumerate(entries):
            r=effect(confirmation,study,profile,group,control=control)
            color='#116b8b' if y==0 else '#69788c'
            ax.errorbar(r['effect'],y,xerr=[[max(0,r['effect']-r['lo95'])],[max(0,r['hi95']-r['effect'])]],fmt='o',color=color,capsize=4)
        ax.set_yticks(range(len(entries)),[e[2] for e in entries]);ax.invert_yaxis()
        ax.axvline(0,color='#9ba5b1',linestyle='--',linewidth=1)
        ax.set_title(title,fontsize=11);ax.set_xlabel('Unaided exam difference (model pp)');ax.grid(axis='x',alpha=.15)
    fig.suptitle('E19: fresh checks after declared setup fitting',fontsize=14)
    figure=REPO/'docs/experiments/figures/E19-teacher-study-comparisons.png'
    fig.savefig(figure,dpi=160);plt.close(fig)
    sourcepaths+=[report,figure,Path(__file__),root/'design-lock.json',root/'selection.json',root/'development-review.md',
        root/'confirmation-execution-lock.json',REPO/'docs/experiments/E18-teacher-study-results.sources.json']
    e19.save_json(report.with_suffix('.sources.json'),dict(sources={str(p.relative_to(REPO)).replace('\\','/'):e19.sha256(p) for p in sourcepaths},
        target_mean_directions_met=allmeans,primary_pointwise_supported=pointwise,primary_simultaneous_supported=simultaneous,
        classrooms=classrooms,earlier_classrooms=1848,historical_source_entries_verified=lock['historical_entries_verified'],
        interpretation='Known-direction exploratory setup fitting; fresh seeds check simulator repeatability, not independent human validation.'))
    print(report)
    print('All target mean directions:',allmeans,'; pointwise:',pointwise,'/3; simultaneous:',simultaneous,'/3')


if __name__=='__main__':main()
