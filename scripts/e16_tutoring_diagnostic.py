"""E16: declared tutoring mechanisms, protocol diagnostics and untouched-seed validation."""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime,timezone
import csv,json
from pathlib import Path
import numpy as np
import pyarrow.parquet as pq
from classroom_swarm.tutoring_config import (REPO,template,resolve_config,preflight,run_experiment,load_config,save_json,sha256)
from classroom_swarm.v4 import V4Log
from classroom_swarm.v4_tutoring import validate_tutoring_log
import e14_classroom_trends as old


def base(name,seed,reps):
    c=template();c.update(experiment_id=name,seed=seed,replicates=reps,conditions=[],contrasts=[],
        notes='E16 uncalibrated exploratory mechanism/protocol probe. All conditions retained; held-out seeds predeclared.')
    c['params'].update(H=20,exam_every=5,allow_answer=False,tutoring_activity='shared_practice')
    c['initial']['confidence']={'kind':'constant','value':.5}
    for key in c['initial']:
        if key.startswith('benefit_'):c['initial'][key]={'kind':'constant','value':.5}
    c['stated_identities'] += ['Wrong or inaccessible explanations grant no direct content bonus.',
        'Shared practice reserves equal base practice in teaching/solo arms; nonnegative content/helper additions partly encode a practice benefit.',
        'Source quality updates use personally observed checked content, not true knowledge or gain.',
        'Changing peers with all communication disabled gives exact focal-student nulls.']
    return c


def contrast(c,a,b,kind='single_parameter',reason=None):
    row=dict(condition=a,reference=b,kind=kind,identity='not_identity')
    if reason:row['reason']=reason
    c['contrasts'].append(row)


def declarations(stage):
    seed,reps=(10011601,30) if stage=='development' else (10011691,100)
    lab=base('E16_'+stage+'_lab',seed,reps)
    lab['params'].update(N=8,distant_weight=0.,closeness_spread=0.)
    lab['initial']['knowledge']={'kind':'values','values':[.35]*4+[.75]*4}
    edges={'mixed':old.clique([[0,1,4,5],[2,3,6,7]]),
           'tracked':old.clique([[0,1,2,3],[4,5,6,7]])}
    variants=[('reference',{},{}),('solo',{'allow_hint':False},{}),
        ('no_helper',{'helper_content_learning':False},{}),
        ('incorrect',{}, {'teaching_skill':{'kind':'constant','value':0.}}),
        ('slow',{'guided_practice_ticks':5},{}),
        ('hard',{}, {'task_difficulty':{'kind':'constant','value':.95}}),
        ('legacy',{'tutoring_activity':'legacy_hint'},{}),
        ('voluntary',{'tutoring_activity':'joint_practice'}, {})]
    for label,params,initial in variants:
        for group in edges:
            lab['conditions'].append(dict(name=group+'_'+label,params=params,initial=initial,
                network={'family':'CUSTOM','edges':edges[group]}))
        contrast(lab,'mixed_'+label,'tracked_'+label)
        if label!='reference':
            for group in edges:
                if label=='hard':
                    contrast(lab,group+'_'+label,group+'_reference',kind='bundled',
                        reason='Changing task-difficulty distribution changes its family and support; these components cannot be identified separately.')
                else:contrast(lab,group+'_'+label,group+'_reference')
    comp=base('E16_'+stage+'_composition',seed+1,reps)
    comp['network'].update(family='ER',d_bar=6)
    comp['params'].update(N=30,distant_weight=.1,tutoring_activity='joint_practice')
    for label,params in [('joint',{}),('joint_copy',{'allow_answer':True}),
        ('legacy',{'tutoring_activity':'legacy_hint'}),
        ('legacy_copy',{'tutoring_activity':'legacy_hint','allow_answer':True})]:
        for level,value in [('low',.35),('high',.75)]:
            comp['conditions'].append(dict(name=level+'_'+label,params=params,
                initial={'knowledge':{'kind':'values','values':[.35]*15+[value]*15}}))
        contrast(comp,'high_'+label,'low_'+label)
    for level in ['low','high']:
        contrast(comp,level+'_joint',level+'_legacy')
        contrast(comp,level+'_joint_copy',level+'_legacy_copy')
        contrast(comp,level+'_joint_copy',level+'_joint')
    return {'lab':lab,'composition':comp}


def prepare(root):
    root.mkdir(parents=True,exist_ok=False)
    configs={}
    for stage in ['development','validation']:
        for group,c in declarations(stage).items():
            resolved=resolve_config(c);preflight(resolved)
            name=stage+'_'+group
            save_json(root/(name+'.json'),c)
            configs[name]=sha256(root/(name+'.json'))
    sources=sorted((REPO/'src/classroom_swarm').glob('*.py'))+[
        Path(__file__), REPO/'scripts/e14_classroom_trends.py', REPO/'tests/test_v4_tutoring.py',
        REPO/'docs/18-v4-tutoring-content.md',REPO/'docs/experiments/E16-diagnostic-plan.md']
    save_json(root/'diagnostic-lock.json',dict(timestamp=datetime.now(timezone.utc).isoformat(),configs=configs,
        sources={str(p.relative_to(REPO)).replace('\\','/'):sha256(p) for p in sources},
        primary=['lab:mixed_reference-tracked_reference','lab:mixed_reference-mixed_solo'],
        criterion='Both held-out exam means and latent knowledge-gain means positive; uncertainty reported. No tuning to sign.',
        interpretation='Exploratory directional correspondence in the specified protocol, not human calibration.'))


def verify(root):
    lock=load_config(root/'diagnostic-lock.json')
    for name,digest in lock['sources'].items():assert sha256(REPO/name)==digest,name
    for name,digest in lock['configs'].items():assert sha256(root/(name+'.json'))==digest,name
    return lock


def execute(root,name):
    verify(root)
    run_experiment(load_config(root/(name+'.json')),root/name)


def write_csv(path,rows):
    with path.open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def summarize(log,ids):
    result=old.metrics(log,ids)
    ids=set(ids);p=log.manifest['params']
    content=[r for r in log.tables.get('tutoring_content',[]) if r['requester'] in ids]
    components=[r for r in log.tables.get('learning_components',[]) if r['student'] in ids]
    for key in ['correct_fraction','usable_fraction','helper_fraction']:
        result[key]=float(np.mean([r[key] for r in content])) if content else 0.
    result['guided_sessions_per_episode']=len(content)/(len(ids)*p['H'])
    for key in ['practice_gain','content_gain','helper_gain']:
        result[key]=sum(r[key] for r in components)/len(ids)
    return result


def analyze(root,stage):
    lock=verify(root);by={};rows=[];inventory=[];total=0
    for group in ['lab','composition']:
        name=stage+'_'+group;folder=root/name
        done=load_config(folder/'complete.json')
        for file,digest in done['hashes'].items():assert sha256(folder/file)==digest
        config=resolve_config(load_config(root/(name+'.json')))
        assert load_config(folder/'lock.json')['conditions']==config['conditions']
        for c in config['conditions']:
            by[group,c['name']]=[]
            for rep in range(config['replicates']):
                path=folder/'raw'/f'rep{rep:04d}'/c['name']
                hashes=load_config(path/'complete.json')['hashes']
                for file,digest in hashes.items():assert sha256(path/file)==digest
                log=V4Log(load_config(path/'manifest.json'))
                for file in hashes:
                    if file.endswith('.parquet'):log.tables[file[:-8]]=pq.read_table(path/file).to_pylist()
                validate_tutoring_log(log)
                focal=range(4) if group=='lab' else range(15)
                result=summarize(log,focal)
                by[group,c['name']].append(result)
                rows.append(dict(group=group,condition=c['name'],replicate=rep,**result))
                inventory.append(dict(group=group,condition=c['name'],replicate=rep,
                    completion_sha256=sha256(path/'complete.json')));total+=1
            print('Audited '+name+'/'+c['name'],flush=True)
    effects=[];rng=np.random.default_rng(10011699)
    for group in ['lab','composition']:
        config=resolve_config(load_config(root/(stage+'_'+group+'.json')))
        for c in config['contrasts']:
            a,b=c['condition'],c['reference']
            for metric in list(by[group,a][0]):
                delta=100*np.array([x[metric]-y[metric] for x,y in zip(by[group,a],by[group,b])])
                boot=delta[rng.integers(0,len(delta),(3000,len(delta)))].mean(axis=1)
                effects.append(dict(group=group,condition=a,reference=b,metric=metric,effect=float(delta.mean()),
                    lo95=float(np.quantile(boot,.025)),hi95=float(np.quantile(boot,.975)),
                    kind=c['kind'],unit='percentage points; counts are per 100 episodes'))
    out=root/(stage+'_derived');out.mkdir(exist_ok=False)
    write_csv(out/'run_metrics.csv',rows);write_csv(out/'effects.csv',effects);write_csv(out/'raw_inventory.csv',inventory)
    save_json(out/'analysis_manifest.json',dict(total_runs=total,raw_audits='all passed',
        diagnostic_lock_sha256=sha256(root/'diagnostic-lock.json'),
        uncertainty='Paired pointwise 95% bootstrap Monte Carlo intervals, 3000 resamples. Exploratory, no multiplicity correction.',
        hashes={p.name:sha256(p) for p in sorted(out.iterdir())}))
    for r in effects:
        if r['metric']=='exam':print(f"{r['group']} {r['condition']} - {r['reference']}: {r['effect']:+.3f} [{r['lo95']:+.3f},{r['hi95']:+.3f}]")


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('command',choices=['prepare','run','analyze'])
    parser.add_argument('--root',type=Path,default=REPO/'runs/E16-tutoring-r1');parser.add_argument('--name')
    parser.add_argument('--stage',choices=['development','validation'],default='development')
    args=parser.parse_args()
    if args.command=='prepare':prepare(args.root)
    elif args.command=='run':execute(args.root,args.name)
    else:analyze(args.root,args.stage)


if __name__=='__main__':main()
