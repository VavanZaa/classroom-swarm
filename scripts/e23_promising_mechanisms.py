"""E23 frozen A32/A33 comparison, ablations, two pools; no outcome-driven fitting."""
from pathlib import Path
from copy import deepcopy
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor,as_completed
from datetime import datetime,timezone
import argparse
import json
import sys
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from classroom_swarm import promising_config as config
from classroom_swarm.promising_settings import resolve_promising
from classroom_swarm.promising_validation import validate_promising_log
from classroom_swarm.v4_promising import simulate_promising
from classroom_swarm.tutoring_settings import TutoringParams
from classroom_swarm.v4_public_ai import PublicAIDraws
from classroom_swarm.v4 import V4Log

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'scripts'))
import e22_a32_study_trends as old

ROOT=REPO/'runs/E23-promising-mechanisms-r1'
PHASES={'development':(2,30000),'confirmation':(16,31000)}
BOOTSTRAPS,BOOTSTRAP_SEED=20000,1001033299
PLAN=REPO/'docs/experiments/E23-promising-mechanisms-plan.md'

def design_for(job,variant):
    r=job['resolved']; case=job['case']; d={'curriculum':{},'teacher_forecast':{},'group_preparation':{},'shared_reasoning':{}}
    if variant=='A32': return resolve_promising(d)
    teacher=r['extensions']['teacher_work']['enabled']
    if variant in ('forecast_only','forecast_group'):
        d['teacher_forecast']['enabled']=teacher
        d['group_preparation']['enabled']=variant=='forecast_group'
    else:
        d['curriculum']['enabled']=True
        d['teacher_forecast']['enabled']=teacher and variant not in ('curriculum_only','old_accuracy','fixed_curriculum')
        d['group_preparation']['enabled']=teacher and case in ('teacher_rewards','india_probe') and variant=='A33'
        d['shared_reasoning']['enabled']=r['params']['allow_hint'] and variant not in ('no_reasoning','curriculum_only','old_accuracy','fixed_curriculum')
        if variant=='old_accuracy': d['curriculum']['independent_teacher_accuracy']=False
        if variant=='fixed_curriculum': d['curriculum'].update(adaptive=False,fixed_level=0)
        elif not teacher or case=='ai':
            d['curriculum'].update(adaptive=False,level_schedule=[h%3 for h in range(r['params']['H'])])
    return resolve_promising(d)

def build_jobs(phase,rep):
    draw_rep=PHASES[phase][1]+rep
    bases=[deepcopy(j) for j in old.build_jobs(draw_rep) if j['profile']=='default']
    for j in bases:
        if j['case']=='teacher_rewards': j['resolved']['extensions']['test_preparation']['participation_cost']=0.
    teacher=[deepcopy(j) for j in bases if j['case']=='teacher_rewards']
    for j in teacher:
        j['profile']='low_access'
        for e in j['resolved']['extensions']['test_preparation']['exams']: e['access_cost']=.35
        j['resolved']['initial']['confidence']={'kind':'from_knowledge'}
    bases+=teacher
    india=[]
    for transfer in (0.,.15):
        for j in [deepcopy(j) for j in teacher]:
            j['case']='india_probe'; j['profile']='zero_transfer' if transfer==0 else 'concept_transfer'
            r=j['resolved']; x=r['extensions']; x['test_preparation'].update(participation=False,coaching_concept_share=1.,coaching_format_share=0.)
            for e in x['test_preparation']['exams']: e['format_loading']=0.; e['access_cost']=0.
            r['mechanisms']['topics']['transfer']=[[1.,transfer],[transfer,1.]]
            x['teacher_work'].update(actions=['coaching','guidance'],contract={**x['teacher_work']['contract'],'strength':20. if j['arm']=='rewarded' else 0.})
            india.append(j)
    bases+=india
    jobs=[]
    for j in bases:
        variants=['A32','A33']
        if j['case']=='kenya': variants+=['curriculum_only','old_accuracy','fixed_curriculum']
        if j['case']=='teacher_rewards': variants+=['forecast_only','forecast_group']
        if j['case'] in ('lab_single','seating','composition'): variants+=['no_reasoning']
        for variant in variants:
            job=deepcopy(j); job.update(phase=phase,cohort=rep,variant=variant)
            job['condition']=f"{job['case']}_{job['profile']}_{job['arm']}_{variant}_s{job['section']}"
            job['resolved']['name']=job['condition']; job['resolved']['design']=__import__('dataclasses').asdict(design_for(job,variant))
            jobs.append(job)
    return jobs

def verify_previous():
    old.verify(old.ROOT)
    paths=['runs/E22b-teacher-access-r1/design-lock.json','docs/reports/A32-paper-trend-assessment-2026-10-07.sources.json','docs/24-proposed-content-teacher-peer-mechanisms.sources.json']
    count=0
    for name in paths:
        document=config.load_config(REPO/name)
        for path,digest in document['sources'].items(): assert config.sha256(REPO/path)==digest,path; count+=1
        if 'declarations' in document:
            for path,digest in document['declarations'].items(): assert config.sha256((REPO/name).parent/path)==digest,path; count+=1
    return count

def comparisons():
    rows=[deepcopy(c) for c in old.comparisons() if c['a'] not in ('placebo','high_cost')]
    for r in rows:
        r['profiles']=['default','low_access'] if r['case']=='teacher_rewards' else ['default']
        if r['case']=='composition': r['primary']=False
    for metric in ('familiar_potential','unrelated_potential','knowledge_gain'):
        rows.append(dict(case='india_probe',a='rewarded',b='unrewarded',group='all',metric=metric,target='positive',primary=False,profiles=['zero_transfer','concept_transfer']))
    return rows

def prepare(root):
    if root.exists(): raise ValueError('Use a new E23 identity')
    previous=verify_previous(); alljobs={}
    for phase,(n,_) in PHASES.items():
        for rep in range(n):
            jobs=build_jobs(phase,rep)
            for j in jobs:
                c=config.template(); c.update(seed=j['seed'],replicates=1,conditions=[j['resolved']])
                config.preflight(config.resolve_config(c))
            alljobs[phase,rep]=jobs
    root.mkdir(parents=True)
    for (phase,rep),jobs in alljobs.items():
        (root/phase).mkdir(exist_ok=True); config.save_json(root/phase/f'cohort{rep:04d}.json',jobs)
    config.save_json(root/'comparisons.json',comparisons())
    sources=sorted((REPO/'src/classroom_swarm').glob('*.py'))+[Path(__file__),PLAN,REPO/'docs/25-v4-promising-mechanisms.md',REPO/'scripts/report_e23_promising.py',REPO/'tests/test_v4_promising.py',REPO/'tests/test_e23_promising.py']
    config.save_json(root/'design-lock.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),sources={str(p.relative_to(REPO)).replace('\\','/'):config.sha256(p) for p in sources},declarations={str(p.relative_to(root)).replace('\\','/'):config.sha256(p) for p in sorted(root.rglob('*.json'))},phases=PHASES,classrooms={phase:sum(len(j) for (s,r),j in alljobs.items() if s==phase) for phase in PHASES},primary_family_size=sum(r['primary'] for r in comparisons()),bootstrap_resamples=BOOTSTRAPS,bootstrap_seed=BOOTSTRAP_SEED,previous_entries_verified=previous,identities=['No direct knowledge from payment/copying/exams/time.','Zero domain transfer blocks direct unrelated concept gains.','Fixed curriculum/no peer assignment contrast is an identity.','Some single-block high starters have mastered foundation skills.'],status='all sources, both pools and all variants locked before outcomes'))
    print(f"Locked {sum(map(len,alljobs.values()))} classrooms in both pools.",flush=True)

def verify(root):
    lock=config.load_config(root/'design-lock.json')
    for name,digest in lock['sources'].items(): assert config.sha256(REPO/name)==digest,name
    for name,digest in lock['declarations'].items(): assert config.sha256(root/name)==digest,name
    verify_previous(); return lock

def metrics(log,ids):
    result=old.metrics(log,ids); ids=set(ids); h=log.manifest['params']['H']; t=log.tables
    result['group_coaching_count']=sum(r.get('scope')=='group' for r in t['teacher_actions'])/h
    for source in ('teacher','coaching','guided','helper'):
        rows=[r for r in t['learning_doses'] if r['student'] in ids and r['source']==source]
        result[source+'_processing']=float(np.mean([r['processing_probability'] for r in rows])) if rows else None
    choices=t.get('curriculum_choices',[])
    result['advanced_lesson_share']=float(np.mean([r['level']==2 for r in choices])) if choices else None
    result['constructed_items']=sum(r['constructed'] for r in t.get('shared_reasoning',[]) if r['requester'] in ids)/(len(ids)*h)
    signals=t.get('participation_forecast_evidence',[])
    result['participation_brier']=float(np.mean([(r['predicted_probability']-int(r['participated']))**2 for r in signals if r['student'] in ids])) if signals else None
    return result

def read(folder):
    complete=config.load_config(folder/'complete.json')
    for name,digest in complete['hashes'].items(): assert config.sha256(folder/name)==digest,name
    log=V4Log(config.load_config(folder/'manifest.json')); log.tables={name[:-8]:pq.read_table(folder/name).to_pylist() for name in complete['hashes'] if name.endswith('.parquet')}
    validate_promising_log(log); return log,len(complete['hashes'])

def worker(root_string,phase,rep):
    root=Path(root_string); rows=[]; inventory=[]
    for j in config.load_config(root/phase/f'cohort{rep:04d}.json'):
        folder=root/phase/'raw'/f'cohort{rep:04d}'/j['condition']; r=j['resolved']; p=TutoringParams(**r['params'])
        if not (folder/'complete.json').exists():
            if folder.exists():
                target=folder.with_name(folder.name+'-partial-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
                assert folder.resolve().is_relative_to(root.resolve()) and target.resolve().is_relative_to(root.resolve()); folder.rename(target)
            graph=config.make_graph(r['network'],p.N,j['seed'],j['replicate'])
            log=simulate_promising(p,graph,PublicAIDraws(j['seed'],j['replicate'],p.N,p.items,p.exam_items),j['condition'],r['initial'],r['teacher'],r['mechanisms'],r['extensions'],r['design'])
            log.manifest.update(network=r['network'],declared_job=j); validate_promising_log(log,p)
            folder.mkdir(parents=True); config.save_json(folder/'manifest.json',log.manifest)
            for name,values in log.tables.items(): pq.write_table(pa.Table.from_pylist(values),folder/f'{name}.parquet',compression='zstd')
            config.save_json(folder/'complete.json',dict(hashes={p.name:config.sha256(p) for p in sorted(folder.iterdir())}))
        log,count=read(folder); assert log.manifest['declared_job']==j
        for group,ids in j['groups'].items():
            if ids: rows.append(dict(case=j['case'],profile=j['profile'],arm=j['arm'],group=group,section=j['section'],replicate=rep,variant=j['variant'],**metrics(log,ids)))
        inventory.append(dict(condition=j['condition'],replicate=rep,hashes=count,complete_sha256=config.sha256(folder/'complete.json')))
    return rows,inventory

def run(root,phase,workers):
    lock=verify(root); dest=root/phase
    if (dest/'run-complete.json').exists(): raise ValueError('Phase complete; use saved evidence')
    rows=[]; inventory=[]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(worker,str(root),phase,rep):rep for rep in range(PHASES[phase][0])}
        for f in as_completed(futures):
            r,i=f.result(); rows+=r; inventory+=i
            print(f"{phase}: audited cohort {futures[f]+1}/{PHASES[phase][0]}, {len(inventory)}/{lock['classrooms'][phase]} classrooms",flush=True)
    assert len(inventory)==lock['classrooms'][phase]
    config.save_json(dest/'class-metrics.json',rows); config.save_json(dest/'raw-inventory.json',inventory)
    config.save_json(dest/'run-complete.json',dict(classrooms=len(inventory),file_hashes_verified=sum(r['hashes'] for r in inventory),design_sha256=config.sha256(root/'design-lock.json'),hashes={name:config.sha256(dest/name) for name in ('class-metrics.json','raw-inventory.json')},raw_audits='all passed'))
    verify(root)

def paired(values,alpha=.05):
    v=np.asarray(values,float); v[np.abs(v)<1e-10]=0
    indices=np.random.default_rng(BOOTSTRAP_SEED).integers(0,len(v),(BOOTSTRAPS,len(v)))
    lo,hi=np.quantile(v[indices].mean(axis=1),[alpha/2,1-alpha/2])
    return dict(effect=float(v.mean()),lo95=float(lo),hi95=float(hi))

def analyze(root,phase):
    lock=verify(root); dest=root/phase; complete=config.load_config(dest/'run-complete.json')
    assert complete['design_sha256']==config.sha256(root/'design-lock.json')
    for name,digest in complete['hashes'].items(): assert config.sha256(dest/name)==digest,name
    for r in config.load_config(dest/'raw-inventory.json'): assert config.sha256(dest/'raw'/f"cohort{r['replicate']:04d}"/r['condition']/'complete.json')==r['complete_sha256']
    collected=defaultdict(list)
    for r in config.load_config(dest/'class-metrics.json'): collected[r['case'],r['profile'],r['arm'],r['group'],r['variant'],r['replicate']].append(r)
    by={}
    ignored={'case','profile','arm','group','variant','replicate','section','students'}
    for key,parts in collected.items():
        n=sum(r['students'] for r in parts)
        by[key]={'students':n,**{metric:sum(r[metric]*r['students'] for r in parts)/n if all(r[metric] is not None for r in parts) else None for metric in parts[0] if metric not in ignored}}
    effects=[]; unavailable=[]; n=PHASES[phase][0]
    for spec in comparisons():
        for profile in spec['profiles']:
            variants=sorted({k[4] for k in by if k[0]==spec['case'] and k[1]==profile})
            for variant in variants:
                if (spec['case'],profile,spec['a'],spec['group'],variant,0) not in by: continue
                metrics_list=[m for m in next(v for k,v in by.items() if k[0]==spec['case']) if m!='students']
                for metric in metrics_list:
                    a=[by[spec['case'],profile,spec['a'],spec['group'],variant,rep][metric] for rep in range(n)]
                    b=[by[spec['case'],profile,spec['b'],spec['group'],variant,rep][metric] for rep in range(n)]
                    identity={k:v for k,v in spec.items() if k not in ('profiles','metric')}
                    if any(v is None for v in a+b):
                        unavailable.append(dict(**identity,profile=profile,variant=variant,metric=metric)); continue
                    primary=spec['primary'] and profile=='default' and variant=='A33' and metric==spec['metric']
                    simultaneous=paired(np.asarray(a)-b,.05/lock['primary_family_size']) if primary else {}
                    effects.append(dict(**identity,profile=profile,variant=variant,metric=metric,headline_metric=spec['metric'],**paired(np.asarray(a)-b),simultaneous_lo95=simultaneous.get('lo95'),simultaneous_hi95=simultaneous.get('hi95'),cohort_differences=(np.asarray(a)-b).tolist()))
    changes=[]
    indexed={(r['case'],r['profile'],r['a'],r['b'],r['group'],r['variant'],r['metric']):r for r in effects}
    for r in effects:
        if r['variant']!='A33': continue
        for variant in ('A32','curriculum_only','old_accuracy','fixed_curriculum','forecast_only','forecast_group','no_reasoning'):
            other=indexed.get((r['case'],r['profile'],r['a'],r['b'],r['group'],variant,r['metric']))
            if other: changes.append({k:v for k,v in r.items() if k not in ('effect','lo95','hi95','cohort_differences','simultaneous_lo95','simultaneous_hi95')}|dict(reference_variant=variant,**paired(np.asarray(r['cohort_differences'])-other['cohort_differences'])))
    out=dest/'derived'
    if out.exists(): raise ValueError('Preserve existing phase analysis')
    out.mkdir(); config.save_json(out/'effects.json',effects); config.save_json(out/'changes.json',changes); config.save_json(out/'unavailable.json',unavailable)
    config.save_json(out/'cohort-metrics.json',[dict(case=k[0],profile=k[1],arm=k[2],group=k[3],variant=k[4],replicate=k[5],**v) for k,v in sorted(by.items())])
    config.save_json(out/'analysis-manifest.json',dict(design_sha256=config.sha256(root/'design-lock.json'),execution_sha256=config.sha256(dest/'run-complete.json'),hashes={p.name:config.sha256(p) for p in sorted(out.iterdir())}))
    for r in effects:
        if r['variant']=='A33' and r['profile']=='default' and r['metric']==r['headline_metric']: print(f"{r['case']}/{r['group']}/{r['a']}-{r['b']}: {r['effect']:+.3f} [{r['lo95']:+.3f},{r['hi95']:+.3f}]",flush=True)

def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('command',choices=['prepare','run','analyze','verify']); parser.add_argument('--root',type=Path,default=ROOT); parser.add_argument('--phase',choices=PHASES,default='development'); parser.add_argument('--workers',type=int,default=4); a=parser.parse_args()
    if a.command=='prepare': prepare(a.root)
    elif a.command=='run': run(a.root,a.phase,a.workers)
    elif a.command=='analyze': analyze(a.root,a.phase)
    else: verify(a.root); print('E23 and previous frozen evidence verified.')

if __name__=='__main__': main()
