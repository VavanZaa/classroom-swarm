"""E20 frozen functional diagnostics; no human calibration or outcome-driven tuning."""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
import sys,json,csv
import numpy as np
import pyarrow.parquet as pq
REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'src'));sys.path.insert(0,str(REPO/'scripts'))
from classroom_swarm import mechanism_config as config
from classroom_swarm.v4 import V4Log
from classroom_swarm.v4_mechanisms import validate_mechanism_log
import e19_teacher_studies as e19

SEEDS={'development':10062011,'confirmation':10062012}
REPLICATES={'development':6,'confirmation':18}


def profiles():
    return [dict(name='reference',parent=None),
        dict(name='linear_reward',parent='reference',mechanisms={'incentives':{'enabled':True,'intrinsic_weight':0.}}),
        dict(name='no_reward',parent='linear_reward',mechanisms={'incentives':{'reward_strength':0.}}),
        dict(name='concave_reward',parent='linear_reward',mechanisms={'incentives':{'reward_power':.5}}),
        dict(name='convex_reward',parent='linear_reward',mechanisms={'incentives':{'reward_power':2.}}),
        dict(name='cheap_effort',parent='linear_reward',mechanisms={'incentives':{'effort_cost':.0001}}),
        dict(name='admin_bursts',parent='reference',mechanisms={'workload':{'enabled':True,'admin_bursts':[6,0,4,0,6,0],'fatigue_per_tick':0.}}),
        dict(name='costly_grading',parent='admin_bursts',teacher={'grading_ticks_per_student':1}),
        dict(name='automated_grading',parent='costly_grading',teacher={'grading_automation':1.}),
        dict(name='fatigue',parent='reference',mechanisms={'workload':{'enabled':True,'fatigue_per_tick':.04,'quality_loss':.7,'recovery':.2}}),
        dict(name='fatigue_off',parent='fatigue',mechanisms={'workload':{'fatigue_per_tick':0.}}),
        dict(name='topics_isolated',parent='reference',mechanisms={'topics':{'enabled':True}}),
        dict(name='topics_transfer',parent='topics_isolated',mechanisms={'topics':{'transfer':[[1.,.2],[.2,1.]]}}),
        dict(name='topic_preparation',parent='topics_isolated',mechanisms={'workload':{'enabled':True,'preparation_ticks':1,'topic_switch_ticks':2,'fatigue_per_tick':0.}}),
        dict(name='helper_consolidation',parent='topics_isolated',mechanisms={'topics':{'helper_consolidation_rate':.2}}),
        dict(name='peer_reference',parent='reference',mechanisms={'peer_observation':{'enabled':True,'topic_specific':False}}),
        dict(name='peer_noise',parent='peer_reference',mechanisms={'peer_observation':{'sensitivity':.7,'specificity':.7}}),
        dict(name='peer_delay',parent='peer_reference',mechanisms={'peer_observation':{'delay_ticks':14}}),
        dict(name='peer_absent',parent='peer_reference',mechanisms={'peer_observation':{'coverage':0.}}),
        dict(name='combined',parent='reference',mechanisms={
            'incentives':{'enabled':True,'intrinsic_weight':0.},
            'workload':{'enabled':True,'preparation_ticks':1,'topic_switch_ticks':2,'fatigue_per_tick':.04,'quality_loss':.7,'recovery':.2},
            'topics':{'enabled':True,'transfer':[[1.,.2],[.2,1.]],'helper_consolidation_rate':.2},
            'peer_observation':{'enabled':True,'sensitivity':.7,'specificity':.7,'delay_ticks':4}}),
        *[dict(name='combined_without_'+b,parent='combined',mechanisms={b:{'enabled':False}}) for b in ('incentives','workload','topics','peer_observation')]]


def recipe(stage):
    c=config.template();c.update(experiment_id='E20_'+stage,seed=SEEDS[stage],replicates=REPLICATES[stage])
    c['params'].update(N=8,H=6,ticks=16,items=12,exam_items=30,exam_every=1,feedback_delay=0,
        allow_answer=False,ai_mode='none',tutoring_activity='shared_practice',distant_weight=0.,closeness_spread=0.)
    c['network'].update(family='ER',d_bar=4)
    c['teacher'].update(enabled=True,time_budget=8,allocation='round_robin',curriculum='adaptive',observation_sources=['exam'])
    c['initial']['learning_efficiency']={'kind':'constant','value':.0584}
    c['initial']['effort_aversion']={'kind':'constant','value':.15}
    by={}
    for p in profiles():
        parent=deepcopy(by[p['parent']]) if p['parent'] else dict(params={},initial={},network={},teacher={},mechanisms=deepcopy(c['mechanisms']))
        parent['name']=p['name'];parent['teacher'].update(p.get('teacher',{}))
        for b,patch in p.get('mechanisms',{}).items():parent['mechanisms'][b].update(patch)
        by[p['name']]=parent
    c['conditions']=list(by.values());c['contrasts']=[]
    resolved=config.resolve_config(c);settings={p['name']:p for p in resolved['conditions']}
    for p in profiles():
        if not p['parent']:continue
        diff=config.differences({k:v for k,v in settings[p['name']].items() if k!='name'},
                                {k:v for k,v in settings[p['parent']].items() if k!='name'})
        c['contrasts'].append(dict(condition=p['name'],reference=p['parent'],kind='single_parameter' if len(diff)==1 else 'bundled',
            reason='This declared feature/protocol bundle cannot identify its individual parts.' if len(diff)>1 else '',
            identity='not_identity'))
    c['stated_identities'] += ['Transfers and helper consolidation are nonnegative direct gains by rule.',
        'Reward payouts are arithmetic, not learning.', 'Fatigue lowers declared skill; net classroom outcomes are not guaranteed.',
        'Unreleased peer evidence cannot update private beliefs.','Dividing exposure among skills changes competence measurement; scalar and topic outcomes are not human-equivalent scales.']
    c['notes']='E20 functional controls, not study fitting. All candidates retained; no human calibration; no selection or tuning between pools.'
    return c


def historical():
    old=e19.verify(REPO/'runs/E19-teacher-study-r1');count=old['historical_entries_verified']+len(old['sources'])
    for rel in ['runs/E19-teacher-study-r1/confirmation-execution-lock.json','docs/experiments/E19-teacher-study-results.sources.json']:
        for name,digest in config.load_config(REPO/rel)['sources'].items():assert config.sha256(REPO/name)==digest,name;count+=1
    return count


def prepare(root):
    if root.exists():raise ValueError('Choose a new E20 root')
    for stage in SEEDS:config.preflight(config.resolve_config(recipe(stage)))
    sources=sorted((REPO/'src/classroom_swarm').glob('*.py'))+[Path(__file__),REPO/'tests/test_v4_mechanisms.py',
        REPO/'docs/21-v4-classroom-mechanisms.md',REPO/'docs/experiments/E20-mechanism-plan.md']
    root.mkdir(parents=True)
    for stage in SEEDS:config.save_json(root/f'{stage}.json',recipe(stage))
    config.save_json(root/'design-lock.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
        sources={str(p.relative_to(REPO)).replace('\\','/'):config.sha256(p) for p in sources},
        configs={s:config.sha256(root/f'{s}.json') for s in SEEDS},seeds=SEEDS,replicates=REPLICATES,
        historical_entries_verified=historical(),interpretation='Functional paired diagnostics; all profiles in both pools; no outcome-driven selection or human calibration.'))


def verify(root):
    lock=config.load_config(root/'design-lock.json')
    for name,digest in lock['sources'].items():assert config.sha256(REPO/name)==digest,name
    for stage,digest in lock['configs'].items():assert config.sha256(root/f'{stage}.json')==digest
    historical();return lock


def run(root,stage):
    verify(root);config.run_experiment(config.load_config(root/f'{stage}.json'),root/stage);verify(root)


def audit(root,stage):
    verify(root);out=root/stage;resolved=config.load_config(out/'lock.json');metrics=[]
    for rep in range(REPLICATES[stage]):
        for c in resolved['conditions']:
            folder=out/'raw'/f'rep{rep:04d}'/c['name']
            hashes=config.load_config(folder/'complete.json')
            # The existing declaration runner writes hashes directly.
            hashes=hashes.get('hashes',hashes)
            for name,digest in hashes.items():assert config.sha256(folder/name)==digest,name
            log=V4Log(config.load_config(folder/'manifest.json'))
            for file in folder.glob('*.parquet'):log.tables[file.stem]=pq.read_table(file).to_pylist()
            validate_mechanism_log(log)
            final=[r for r in log.tables['students'] if r['homework']==6]
            exams=[r for r in log.tables['exams'] if r['homework']==6]
            actions=[r for r in log.tables.get('teacher_actions',[]) if r['homework']<=6]
            observations=log.tables.get('quality_feedback',[])
            metrics.append(dict(stage=stage,replicate=rep,condition=c['name'],exam=100*float(np.mean([r['score'] for r in exams])),
                knowledge=100*float(np.mean([r['K'] for r in final])),teacher_ticks=sum(r['cost'] for r in actions),
                returned_grades=len(log.tables['homework_feedback']),peer_updates=len(observations),
                peer_backlog=len(log.tables.get('peer_signal_backlog',[])),
                topic_count=log.manifest.get('topic_count',1),
                final_fatigue=log.tables.get('teacher_fatigue',[{'after':0}])[-1]['after'],
                rewards=sum(r['amount'] for r in log.tables.get('teacher_rewards',[]))))
        print(f'Audited {stage}: {rep+1}/{REPLICATES[stage]}',flush=True)
    path=root/f'{stage}-metrics.json'
    if path.exists():raise ValueError('Metrics already exist')
    config.save_json(path,metrics)
    config.save_json(root/f'{stage}-audit.json',dict(raw_audits='all passed',classrooms=len(metrics),metrics_sha256=config.sha256(path),
        design_sha256=config.sha256(root/'design-lock.json'),historical_entries_verified=historical()))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','run','audit','verify'])
    parser.add_argument('--stage',choices=list(SEEDS),default='development')
    parser.add_argument('--root',type=Path,default=REPO/'runs/E20-mechanisms-r1')
    args=parser.parse_args()
    if args.command=='prepare':prepare(args.root)
    elif args.command=='run':run(args.root,args.stage)
    elif args.command=='audit':audit(args.root,args.stage)
    else:print(verify(args.root))


if __name__=='__main__':main()
