"""Fixed A32 functional controls. No outcome-driven tuning or field-sign gate."""
from pathlib import Path
import argparse
import csv
import json
import hashlib
from copy import deepcopy
import numpy as np
import pyarrow.parquet as pq
from classroom_swarm.effort_config import template, resolve_config, preflight, run_experiment, save_json, sha256
from classroom_swarm.effort_validation import validate_effort_log
from classroom_swarm.v4 import V4Log

REPO=Path(__file__).resolve().parents[1]
OUTPUT=REPO/'runs/A32-functional-r1'
PLAN=REPO/'docs/experiments/A32-functional-plan.md'
REPORT=REPO/'docs/experiments/A32-functional-results.md'


def constant(value): return {'kind':'constant','value':value}


def design():
    c=template(); c.update(experiment_id='A32_functional_r1',seed=100773241,replicates=6)
    c['params'].update(N=8,H=5,ticks=12,items=20,exam_items=30,exam_every=1,feedback_delay=0,
        allow_hint=False,allow_answer=False,distant_weight=0,closeness_spread=0.)
    c['network'].update(family='CUSTOM',edges=[])
    c['teacher'].update(enabled=True,time_budget=3,actions=['instruction'])
    c['mechanisms']['topics'].update(enabled=True,schedule=[0]*5)
    c['initial']['knowledge']={'kind':'truncated_normal','mean':.45,'std':.15,'low':0.,'high':1.}
    c['extensions']['learning_process']['enabled']=True
    cases=[]
    def add(name, **settings): cases.append(dict(name=name,**settings))
    add('process_reference')
    add('A31_reference',extensions={'learning_process':{'enabled':False}})
    add('zero_effort',extensions={'learning_process':{'effort_grid':[0.]}})
    add('zero_attention',extensions={'learning_process':{'attention':constant(0.),'attention_effort_weight':0.}})
    add('no_self_material',extensions={'learning_process':{'material_access':False,'self_reasoning_quality':0.}})
    add('no_teacher',teacher={'enabled':False})
    add('answer_AI',params={'ai_mode':'answer'})
    add('tutor_AI',params={'ai_mode':'tutor'})
    add('teacher_work',extensions={'teacher_work':{'enabled':True}})
    for name,bonus in [('prep_tax_only',0.),('prep_product',.5)]:
        add(name,teacher={'teaching_skill':.2},extensions={'teacher_work':{'enabled':True,'total_budget':4,
            'actions':[],'preparation_quality_bonus':bonus}})
    add('partial_instruction',extensions={'teacher_work':{'enabled':True,'total_budget':2,
        'allow_instruction_crowdout':True,'actions':[]}})
    helper_initial={'knowledge':{'kind':'values','values':[.8,.75,.7,.65,.2,.25,.3,.35]}}
    for name,extra in [('helper_zero',{'prize':0.}),('helper_reward',{'prize':100.}),
                       ('helper_placebo',{'prize':100.,'placebo_payment':True}),
                       ('helper_high_cost',{'prize':100.,'helper_cost_multiplier':10000.}),
                       ('helper_refused',{'prize':100.,'recipient_acceptance':0.}),
                       ('helper_fractional',{'prize':100.,'top_fraction':.1})]:
        contract={'enabled':True,'pairs':[[0,4],[1,5],[2,6],[3,7]],'belief_progress_rate':.3,
                  'top_fraction':.5,'helper_intrinsic_value':0.,'payment_delay':0,**extra}
        add(name,teacher={'enabled':False},initial=helper_initial,extensions={'helper_contract':contract,
            'learning_process':{'future_test_value':constant(20.)}})
    add('helper_disengaged',teacher={'enabled':False},initial=helper_initial,extensions={
        'helper_contract':{'enabled':True,'pairs':[[0,4],[1,5],[2,6],[3,7]],'prize':100.,'belief_progress_rate':.3},
        'learning_process':{'attention':constant(0.),'attention_effort_weight':0.}})
    add('format_only',teacher={'enabled':False},extensions={'learning_process':{'future_test_value':constant(100.),
        'effort_grid':[1.]},'test_preparation':{'enabled':True,'concept_share':0.,'format_share':1.}})
    for name,strength in [('coaching_zero_reward',0.),('coaching_linked_reward',20.)]:
        add(name,extensions={'learning_process':{'material_access':False,'self_reasoning_quality':0.},
            'teacher_work':{'enabled':True,'protected_instruction_ticks':0,'preparation_ticks':0,'actions':['coaching'],
                'intrinsic_weight':0.,'contract':{'strength':strength,'forms':['familiar']}},
            'test_preparation':{'enabled':True,'coaching_concept_share':0.,'coaching_format_share':1.}})
    for name,strength in [('participation_zero_reward',0.),('participation_linked_reward',20.)]:
        add(name,extensions={'learning_process':{'material_access':False,'self_reasoning_quality':0.},
            'teacher_work':{'enabled':True,'protected_instruction_ticks':0,'preparation_ticks':0,'actions':['followup'],
                'intrinsic_weight':0.,'contract':{'strength':strength,'forms':['familiar']}},
            'test_preparation':{'enabled':True,'participation':True,'participation_cost':.6}})
    add('combined',initial=helper_initial,extensions={'learning_process':{'future_test_value':constant(5.)},
        'teacher_work':{'enabled':True,'actions':['guidance','coaching','followup']},
        'helper_contract':{'enabled':True,'pairs':[[0,4],[1,5],[2,6],[3,7]],'prize':100.,'belief_progress_rate':.3},
        'test_preparation':{'enabled':True,'participation':True,'participation_cost':.3}})
    c['conditions']=cases
    c['contrasts']=[dict(condition=a,reference=b,kind='single_parameter',identity='not_identity') for a,b in [
        ('prep_product','prep_tax_only'),('helper_reward','helper_zero'),('helper_placebo','helper_reward'),
        ('helper_high_cost','helper_reward'),('helper_refused','helper_reward'),
        ('coaching_linked_reward','coaching_zero_reward'),('participation_linked_reward','participation_zero_reward')]]
    c['notes']='Uncalibrated functional stress controls, fixed before outcomes. Prize/stakes 100 exercise decision branches; no field effect target.'
    return c


def execute():
    c=design(); r=resolve_config(c); preflight(r)
    evidence=REPO/'docs/reports/A32-functional-design-lock.json'
    if evidence.exists() or OUTPUT.exists(): raise ValueError('A32 functional identity already exists')
    sources=([Path(__file__),PLAN,REPO/'docs/23-v4-effort-learning.md']+sorted((REPO/'src/classroom_swarm').glob('*.py'))+
        sorted((REPO/'tests').glob('test*effort*.py')))
    save_json(evidence,{'status':'frozen before simulation','resolved':r,
        'sources':{str(p.relative_to(REPO)).replace('\\','/'):sha256(p) for p in sources}})
    run_experiment(c,OUTPUT)


def mean(values):
    values=list(values); return float(np.mean(values)) if values else None


def report():
    lock=json.loads((REPO/'docs/reports/A32-functional-design-lock.json').read_text())
    for source,expected in lock['sources'].items():
        assert sha256(REPO/source)==expected,source
    inventory=list(csv.DictReader((OUTPUT/'runs.csv').open()))
    assert len(inventory)==len(lock['resolved']['conditions'])*lock['resolved']['replicates']
    summaries=[]; audited_files=0; checks={name:[] for name in ('zero_effort','zero_attention','self_content','teacher_budget','coaching_core','helper_delay')}
    raw={}
    for row in inventory:
        folder=OUTPUT/row['path']; complete=json.loads((folder/'complete.json').read_text())
        for name,expected in complete['hashes'].items(): assert sha256(folder/name)==expected; audited_files+=1
        log=V4Log(json.loads((folder/'manifest.json').read_text())); log.tables={p.stem:pq.read_table(p).to_pylist() for p in folder.glob('*.parquet')}
        validate_effort_log(log)
        t=log.tables; name=row['condition']; rep=int(row['replicate']); raw[name,rep]=log
        final=[r for r in t['students'] if r['homework']==5]
        doses=t.get('learning_doses',[]); resources=t.get('teacher_resources',[])
        assessments=t.get('assessment_scores',[])
        values=dict(condition=name,replicate=rep,knowledge=100*mean(r['K'] for r in final),
            gain=100*mean(r['K']-next(s['K0'] for s in t['traits'] if s['student']==r['student']) for r in final),
            student_cost=sum(r['cost'] for r in t.get('student_costs',[]))/8,
            productive_fraction=mean(r['dose']>0 for r in doses),dose=sum(r['dose'] for r in doses),
            helper_sessions=len(t.get('helper_sessions',[])),helper_time=sum(r['end']-r['start'] for r in t.get('helper_sessions',[])),
            teacher_spent=mean(r['spent'] for r in resources),format_final=mean(r['familiarity'] for r in t.get('format_states',[]) if r['form']=='familiar'),
            teacher_payments=sum(r['amount'] for r in t.get('contract_payments',[])),helper_payments=sum(r['amount'] for r in t.get('helper_payments',[])))
        for form in ('familiar','novel','unrelated','core'):
            scores=[r for r in assessments if r['homework']==5 and r['form']==form]
            values[form+'_cohort']=100*mean(r['cohort_contribution'] for r in scores) if scores else None
            values[form+'_participants']=100*mean(r['score'] for r in scores if r['score'] is not None) if any(r['score'] is not None for r in scores) else None
            values[form+'_participation']=mean(r['participated'] for r in scores)
        summaries.append(values)
        if name in ('zero_effort','zero_attention'):
            checks[name].append(not t.get('topic_learning') and bool(t.get('student_costs')))
        if name=='no_self_material': checks['self_content'].append(all(r['fraction']==0 for r in doses if r['source']=='attempt'))
        if resources: checks['teacher_budget'].append(all(r['spent']<=r['total_budget'] and r['spent']+r['unused']==r['total_budget'] for r in resources))
        if name.startswith('helper_'):
            checks['helper_delay'].append(all(r['homework']>r['source_homework'] for r in t.get('helper_payments',[])))
    for rep in range(6):
        a=raw['coaching_linked_reward',rep]; b=raw['coaching_zero_reward',rep]
        checks['coaching_core'].append(a.tables['topic_states']==b.tables['topic_states'] and
            [r['potential_correct'] for r in a.tables['assessment_items'] if r['form']=='core']==
            [r['potential_correct'] for r in b.tables['assessment_items'] if r['form']=='core'])
    assert all(values and all(values) for values in checks.values()),checks
    metric_keys=[key for key in summaries[0] if key not in ('condition','replicate')]
    grouped={name:{key:mean(r[key] for r in summaries if r['condition']==name and r[key] is not None) for key in metric_keys}
        for name in sorted({r['condition'] for r in summaries})}
    evidence=REPO/'docs/reports/A32-functional-results.json'
    save_json(evidence,dict(runs=len(inventory),audited_files=audited_files,checks={k:len(v) for k,v in checks.items()},classes=summaries,means=grouped))
    def fmt(x): return '—' if x is None else f'{x:.3f}'
    lines=['---','type: functional-report','updated: 2026-10-07','---','# A32 implementation and functional checks','',
        f'Completed {len(inventory)} fixed classroom runs: {len(grouped)} conditions × six paired replicates. All raw audits passed, and {audited_files:,} saved file hashes matched. The design, engine, tests, specification and this runner were frozen before outcomes.', '',
        'These are uncalibrated mechanism checks. No study coefficient was fitted, no candidate was selected from these outcomes, and no field-study replication is claimed. Large declared prize/test-utility controls exercise offers and format choice; their sizes have no human-unit interpretation.', '',
        'The earlier 571 tests remain passing; the implementation adds 60 acceptance/configuration tests. Historical A31 compatibility is tested on every raw table and manifest with all new branches off. A separate historical source audit is recorded alongside this report.', '',
        '| Condition | Final K (%) | Gain (pp) | Positive-dose fraction | Paid cost/student | Helper sessions/class | Teacher ticks/day | Familiarity |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for name,m in grouped.items():
        lines.append('| '+name+' | '+' | '.join(fmt(m[k]) for k in ('knowledge','gain','productive_fraction','student_cost','helper_sessions','teacher_spent','format_final'))+' |')
    lines+=['', 'Zero-effort and zero-attention classrooms paid activity costs but had no conceptual gains. Removing useful self materials and self-generated reasoning eliminated direct self-practice gains; teacher opportunities remained separate. Every teacher work schedule conserved the declared total and retained ordinary protected instruction. Tax-only and productive preparation spent the same resource schedule.', '',
        'Helper rewards, zero prizes, placebo payments, refusal, high cost, fractional quotas and failed engagement all have separate records. Helping reserves both students; payments use released observed partner progress and do not directly change knowledge. Differences in conceptual outcomes include displaced own study, explanation quality and recipient uptake, so a positive net effect is not assumed.', '',
        '| Teacher protocol | Familiar cohort score (%) | Familiar participation | Novel cohort score (%) | Core cohort score (%) | K (%) |',
        '|---|---:|---:|---:|---:|---:|']
    for name in ('coaching_zero_reward','coaching_linked_reward','participation_zero_reward','participation_linked_reward','combined'):
        m=grouped[name]; lines.append('| '+name+' | '+' | '.join(fmt(m[k]) for k in ('familiar_cohort','familiar_participation','novel_cohort','core_cohort','knowledge'))+' |')
    lines+=['', 'Pure-format coaching left conceptual states and core potential item outcomes exactly equal to its zero-reward control. This is an encoded separation, not empirical evidence for a field mechanism. Participation changes observed/cohort scores without changing the underlying potential test; missing observations remain missing. Participant-only means, full-cohort contributions and participation are separate in the saved report data.', '',
        'Limits: teacher planning uses declared productivity/uptake priors and observed score proxies; it is not a calibrated model of human engagement. Mixed-topic/form scores can bias those proxies. One teacher does not represent a school tournament. Dialogue, friendship/personality effects, multiple-teacher coordination and human-unit mapping remain absent. The next scientific step is new frozen study protocols, retaining the contrary E21 cases and separating infrastructure, resources, participation and learning.', '',
        'Evidence: `runs/A32-functional-r1/lock.json`, `docs/reports/A32-functional-design-lock.json`, `docs/reports/A32-functional-results.json`; specification: `docs/23-v4-effort-learning.md`.', '',
        'Done: approved mechanisms implemented and functional controls completed. Waiting: none. Next: separately declared study comparisons; human calibration remains deferred.', '']
    REPORT.write_text('\n'.join(lines),encoding='utf-8')
    save_json(REPORT.with_suffix('.sources.json'),{'sources':{str(p.relative_to(REPO)).replace('\\','/'):sha256(p) for p in
        [REPORT,evidence,Path(__file__),PLAN,REPO/'docs/reports/A32-functional-design-lock.json',OUTPUT/'lock.json',OUTPUT/'complete.json',OUTPUT/'runs.csv']}})
    print(json.dumps({'runs':len(inventory),'audited_files':audited_files,'checks':{k:len(v) for k,v in checks.items()}},indent=2))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('command',choices=['run','report'])
    args=parser.parse_args(); execute() if args.command=='run' else report()
