"""E17: existing-control robustness, protocol probes and raw-audited comparison."""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import csv
import json
import numpy as np
import pyarrow.parquet as pq
from classroom_swarm.tutoring_config import (
    REPO, resolve_config, preflight, run_experiment, load_config, save_json, sha256)
from classroom_swarm.v4 import V4Log
from classroom_swarm.v4_tutoring import validate_tutoring_log
import e16_tutoring_diagnostic as e16

VARIANTS = [
    ('reference', {}, {}),
    ('skill75', {}, {'teaching_skill': {'kind':'constant','value':.75}}),
    ('skill50', {}, {'teaching_skill': {'kind':'constant','value':.5}}),
    ('heterogeneous', {}, {'teaching_skill': {'kind':'uniform','low':.5,'high':1.}}),
    ('partial_checks', {'quality_check_probability':.25}, {}),
    ('no_checks', {'quality_check_probability':0.}, {}),
    ('frozen_quality', {'quality_learning_rate':0.}, {}),
    ('no_quality_target', {'quality_target_weight':0.}, {}),
    ('prior_low', {}, {'source_quality':{'kind':'constant','value':.2}}),
    ('prior_high', {}, {'source_quality':{'kind':'constant','value':.8}}),
    ('slow', {'guided_practice_ticks':5}, {}),
    ('voluntary', {'tutoring_activity':'joint_practice'}, {}),
    ('single_scheduled', {'H':1,'exam_every':1}, {}),
    ('single_voluntary', {'H':1,'exam_every':1,'tutoring_activity':'joint_practice'}, {}),
]
ARMS = ('mixed','tracked','solo')
PRIMARY_VARIANTS = {'reference','single_scheduled','single_voluntary'}


def declaration(stage):
    seed,reps = (10061701,20) if stage=='development' else (10061791,60)
    c=e16.base('E17_'+stage,seed,reps)
    c['notes']='E17: fixed tutoring robustness and protocol probes; not fitted to human data.'
    c['params'].update(N=8,distant_weight=0.,closeness_spread=0.)
    c['initial']['knowledge']={'kind':'values','values':[.35]*4+[.75]*4}
    edges={'mixed':e16.old.clique([[0,1,4,5],[2,3,6,7]]),
           'tracked':e16.old.clique([[0,1,2,3],[4,5,6,7]])}
    for variant,params,initial in VARIANTS:
        for arm in ARMS:
            patch=deepcopy(params)
            if arm=='solo':patch['allow_hint']=False
            c['conditions'].append(dict(name=f'{arm}_{variant}',params=patch,
                initial=deepcopy(initial),network={'family':'CUSTOM','edges':edges['mixed' if arm=='solo' else arm]}))
        for a,b in [('mixed','tracked'),('mixed','solo'),('tracked','solo')]:
            # Tracked–solo changes graph and hint access; components not separately identified.
            bundled=a=='tracked'
            e16.contrast(c,f'{a}_{variant}',f'{b}_{variant}',
                kind='bundled' if bundled else 'single_parameter',
                reason='Tracking and teaching access change together; use the other two contrasts to inspect components.' if bundled else None)
        if variant!='reference':
            baseline='single_scheduled' if variant=='single_voluntary' else 'reference'
            bundle=variant in {'heterogeneous','single_scheduled'}
            for arm in ARMS:
                e16.contrast(c,f'{arm}_{variant}',f'{arm}_{baseline}',
                    kind='bundled' if bundle else 'single_parameter',
                    reason='Distribution family/support or episode/exam schedule changes jointly; components cannot be separately identified.' if bundle else None)
            if variant=='single_voluntary':
                for arm in ARMS:
                    e16.contrast(c,f'{arm}_{variant}',f'{arm}_voluntary',kind='bundled',
                        reason='Episode count and exam frequency change jointly to measure the final single-block outcome.')
    c['stated_identities'] += [
        'Scheduled guided-session frequency is identical across mixed/tracked groups by construction.',
        'Equal scheduled base practice plus nonnegative bonuses partly encodes the teaching advantage.',
        'No checks or zero quality update rate means no quality-belief changes.']
    return c


def prepare(root):
    configs={stage:declaration(stage) for stage in ('development','confirmation')}
    for c in configs.values():preflight(resolve_config(c))
    root.mkdir(parents=True,exist_ok=False)
    for stage,c in configs.items():save_json(root/f'{stage}.json',c)
    sources=sorted((REPO/'src/classroom_swarm').glob('*.py'))+[
        Path(__file__),REPO/'scripts/e16_tutoring_diagnostic.py',
        REPO/'scripts/e14_classroom_trends.py',REPO/'scripts/resume_tutoring_experiment.py',
        REPO/'tests/test_e17_robustness.py',REPO/'docs/experiments/E17-preregistration.md']
    save_json(root/'design-lock.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
        configs={stage:sha256(root/f'{stage}.json') for stage in configs},
        sources={str(p.relative_to(REPO)).replace('\\','/'):sha256(p) for p in sources},
        total_runs=sum(c['replicates']*len(c['conditions']) for c in configs.values()),
        primary_family_size=9,bootstrap_resamples=3000,bootstrap_seed=10061799,
        interpretation='Monte Carlo robustness, not human empirical validation.'))
    print('Prepared 42 conditions per stage; 840 development + 2520 confirmation runs.',flush=True)


def verify(root):
    lock=load_config(root/'design-lock.json')
    for name,digest in lock['sources'].items():
        if sha256(REPO/name)!=digest:raise ValueError('Changed locked source: '+name)
    for stage,digest in lock['configs'].items():
        if sha256(root/f'{stage}.json')!=digest:raise ValueError('Changed locked config: '+stage)
    historical=load_config(REPO/'runs/E16-tutoring-r1/diagnostic-lock.json')
    for name,digest in historical['sources'].items():
        if sha256(REPO/name)!=digest:raise ValueError('Changed E16 source: '+name)
    return lock


def execute(root,stage):
    verify(root)
    if stage=='confirmation' and not (root/'development-review.md').is_file():
        raise ValueError('Write development-review.md before opening confirmation.')
    output=root/stage
    if (output/'complete.json').is_file():
        raise ValueError('Stage already complete; audit/analyze instead.')
    if output.exists():
        from resume_tutoring_experiment import resume
        resume(output)
    else:run_experiment(load_config(root/f'{stage}.json'),output)


def summarize(log,ids):
    result=e16.summarize(log,ids)
    ids=set(ids);h=log.manifest['params']['H']
    content=[r for r in log.tables['tutoring_content'] if r['requester'] in ids]
    feedback=[r for r in log.tables['quality_feedback'] if r['requester'] in ids]
    events=[r for r in log.tables['events'] if r['student'] in ids]
    result.update(
        helping_events_per_episode=sum(r['provider'] in ids for r in log.tables['tutoring_content'])/(len(ids)*h),
        checked_fraction=sum(r['checked_items'] for r in feedback)/(len(feedback)*log.manifest['params']['items']) if feedback else 0.,
        quality_update_fraction=sum(abs(r['Q_after']-r['Q_before'])>1e-14 for r in feedback)/len(feedback) if feedback else 0.,
        quality_belief_change=sum(r['Q_after']-r['Q_before'] for r in feedback)/len(feedback) if feedback else 0.,
        guided_ticks_per_episode=sum(r['end']-r['start'] for r in events if r['action']=='guided_practice')/(len(ids)*h),
        own_practice_ticks_per_episode=sum(r['end']-r['start'] for r in events if r['action'] in {'attempt','guided_practice','scheduled_practice'})/(len(ids)*h))
    return result


def units(metric):
    if metric.endswith('_per_episode'):return 1.,'count or ticks per student per episode'
    return 100.,'percentage points'


def paired_effect(a,b,metric,rng,alpha=.05):
    scale,unit=units(metric)
    delta=scale*(np.asarray(a,float)-np.asarray(b,float))
    boot=delta[rng.integers(0,len(delta),(3000,len(delta)))].mean(axis=1)
    return dict(effect=float(delta.mean()),lo95=float(np.quantile(boot,alpha/2)),
        hi95=float(np.quantile(boot,1-alpha/2)),unit=unit)


def analyze(root,stage):
    lock=verify(root);folder=root/stage
    done=load_config(folder/'complete.json')
    for name,digest in done['hashes'].items():
        if sha256(folder/name)!=digest:raise ValueError('Changed stage artifact: '+name)
    c=resolve_config(load_config(root/f'{stage}.json'))
    runtime=load_config(folder/'lock.json')
    if runtime['conditions']!=c['conditions']:raise ValueError('Runtime conditions differ')
    rows=[];inventory=[];by={}
    for condition in c['conditions']:
        name=condition['name']
        for group in ('low','high','all'):by[name,group]=[]
        for rep in range(c['replicates']):
            path=folder/'raw'/f'rep{rep:04d}'/name
            hashes=load_config(path/'complete.json')['hashes']
            for file,digest in hashes.items():
                if sha256(path/file)!=digest:raise ValueError(f'Changed raw output: {path/file}')
            manifest=load_config(path/'manifest.json')
            if (manifest['seed'],manifest['replicate'],manifest['condition'])!=(c['seed'],rep,name):
                raise ValueError('Run identity differs')
            # Params are checked by A29 audit and initial settings compared with declaration.
            if manifest['initial']!=condition['initial']:raise ValueError('Initial settings differ')
            log=V4Log(manifest)
            for file in hashes:
                if file.endswith('.parquet'):log.tables[file[:-8]]=pq.read_table(path/file).to_pylist()
            validate_tutoring_log(log)
            for group,ids in [('low',range(4)),('high',range(4,8)),('all',range(8))]:
                result=summarize(log,ids);by[name,group].append(result)
                rows.append(dict(condition=name,replicate=rep,group=group,**result))
            inventory.append(dict(condition=name,replicate=rep,completion_sha256=sha256(path/'complete.json')))
        print('Audited '+stage+'/'+name,flush=True)
    effects=[];rng=np.random.default_rng(lock['bootstrap_seed'])
    for contrast in c['contrasts']:
        a,b=contrast['condition'],contrast['reference']
        for group in ('low','high','all'):
            for metric in by[a,group][0]:
                av=[r[metric] for r in by[a,group]];bv=[r[metric] for r in by[b,group]]
                primary=(group=='low' and metric=='exam' and
                    any((a,b)==(f'{x}_{v}',f'{y}_{v}') for v in PRIMARY_VARIANTS
                        for x,y in [('mixed','tracked'),('mixed','solo'),('tracked','solo')]))
                result=paired_effect(av,bv,metric,rng)
                family=paired_effect(av,bv,metric,rng,alpha=.05/9) if primary else None
                effects.append(dict(condition=a,reference=b,group=group,metric=metric,
                    **result,kind=contrast['kind'],primary=primary,
                    simultaneous_lo95=family['lo95'] if family else '',
                    simultaneous_hi95=family['hi95'] if family else ''))
        # Effect heterogeneity, paired within each replicate, using fixed own-ability groups.
        if any((a,b)==(f'mixed_{v}',f'{x}_{v}') for v,_,_ in VARIANTS for x in ('tracked','solo')):
            for metric in ('exam','knowledge_gain'):
                av=[hi[metric]-lo[metric] for hi,lo in zip(by[a,'high'],by[a,'low'])]
                bv=[hi[metric]-lo[metric] for hi,lo in zip(by[b,'high'],by[b,'low'])]
                effects.append(dict(condition=a,reference=b,group='high_minus_low',metric=metric,
                    **paired_effect(av,bv,metric,rng),kind=contrast['kind'],primary=False,
                    simultaneous_lo95='',simultaneous_hi95=''))
    out=root/f'{stage}_derived';out.mkdir(exist_ok=False)
    e16.write_csv(out/'run_metrics.csv',rows);e16.write_csv(out/'effects.csv',effects)
    e16.write_csv(out/'raw_inventory.csv',inventory)
    save_json(out/'analysis_manifest.json',dict(total_runs=len(inventory),raw_audits='all passed',
        design_lock_sha256=sha256(root/'design-lock.json'),
        uncertainty='Paired pointwise 95% MC bootstrap; nine primary exams also simultaneous Bonferroni 95%.',
        hashes={p.name:sha256(p) for p in sorted(out.iterdir())}))
    for r in effects:
        if r['group']=='low' and r['metric']=='exam' and r['condition'].startswith('mixed_'):
            print(f"{r['condition']} - {r['reference']}: {r['effect']:+.3f} [{r['lo95']:+.3f},{r['hi95']:+.3f}]",flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','run','analyze','verify'])
    parser.add_argument('--root',type=Path,default=REPO/'runs/E17-tutoring-robustness-r1')
    parser.add_argument('--stage',choices=['development','confirmation'],default='development')
    args=parser.parse_args()
    if args.command=='prepare':prepare(args.root)
    elif args.command=='run':execute(args.root,args.stage)
    elif args.command=='analyze':analyze(args.root,args.stage)
    else:verify(args.root);print('Design and E16 source hashes verified.')


if __name__=='__main__':main()
