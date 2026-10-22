"""Execution-only parallel transport for the frozen E19 confirmation jobs."""
from __future__ import annotations
import argparse
from concurrent.futures import ProcessPoolExecutor
from collections import defaultdict
from dataclasses import asdict
from datetime import datetime,timezone
from pathlib import Path
import sys

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'scripts'))
import e19_teacher_studies as e19


def execute(args):
    job,out=args
    folder=out/'raw'/f"rep{job['replicate']:04d}"/job['name']
    reused=(folder/'complete.json').exists()
    if reused:
        log=e19.load_raw(folder)
        e19.check_identity(log,job)
    else:
        if folder.exists():
            target=folder.with_name(folder.name+'-partial-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
            if not folder.resolve().is_relative_to(out.resolve()) or not target.resolve().is_relative_to(out.resolve()):
                raise ValueError('Partial preservation path escapes stage')
            folder.rename(target)
        r=job['resolved'];p=e19.TutoringParams(**r['params'])
        graph=e19.make_graph(r['network'],p.N,job['seed'],job['replicate'])
        log=e19.simulate_teacher(p,graph,e19.PublicAIDraws(job['seed'],job['replicate'],p.N,p.items,p.exam_items),
            condition=job['name'],initial=r['initial'],teacher=r['teacher'])
        log.manifest.update(cohort_global_ids=job['global_ids'],
            cohort_baseline_scores=[job['cohort']['observed_baseline'][i] for i in job['global_ids']],
            study=job['study'],profile=job['profile'],control=job['control'],assignment=job['arm'],
            section=job['section'],network=r['network'])
        e19.validate_teacher_log(log)
        folder.mkdir(parents=True)
        e19.save_json(folder/'declared_class.json',dict(config=job['config'],resolved=r))
        e19.save_json(folder/'manifest.json',log.manifest)
        for name,rows in log.tables.items():
            e19.pq.write_table(e19.pa.Table.from_pylist(rows),folder/f'{name}.parquet',compression='zstd')
        e19.save_json(folder/'complete.json',{'hashes':{p.name:e19.sha256(p) for p in sorted(folder.iterdir())}})
    record=dict(replicate=job['replicate'],condition=job['name'],study=job['study'],profile=job['profile'],
        control=job['control'],arm=job['arm'],section=job['section'],path=str(folder.relative_to(out)),
        complete_sha256=e19.sha256(folder/'complete.json'))
    return record,reused


def audit_job(args):
    job,out=args
    folder=out/'raw'/f"rep{job['replicate']:04d}"/job['name']
    log=e19.load_raw(folder);e19.check_identity(log,job)
    pop=job['cohort'];parts=[]
    for group in ('all','low','high'):
        ids=set(pop['student_ids'] if group=='all' else pop[group])
        local=[i for i,g in enumerate(job['global_ids']) if g in ids]
        if local:
            key=(job['study'],job['label'],job['control'],job['arm'],group,job['replicate'])
            parts.append((key,e19.metrics(log,local)))
    return parts,dict(condition=job['name'],replicate=job['replicate'],complete_sha256=e19.sha256(folder/'complete.json'))


def analyze_confirmation(root,workers):
    """Same aggregation/statistics as E19; only per-class audits are parallel."""
    e19.verify(root);selection=e19.selected(root);out=root/'confirmation'
    completion=e19.load_config(out/'complete.json')
    for name,digest in completion['hashes'].items():assert e19.sha256(out/name)==digest
    execution=e19.load_config(root/'confirmation-execution-lock.json')
    for name,digest in execution['sources'].items():assert e19.sha256(REPO/name)==digest
    gate=e19.sha256(root/'selection.json')
    assert e19.load_config(out/'stage-lock.json')['selection_sha256']==gate
    derived=root/'confirmation_derived'
    if derived.exists():raise ValueError('Derived stage already exists; preserve it')
    jobs=[j for rep in range(e19.REPLICATES['confirmation']) for j in e19.jobs('confirmation',rep,selection)]
    grouped=defaultdict(list);inventory=[]
    with ProcessPoolExecutor(max_workers=workers) as executor:
        for number,(parts,record) in enumerate(executor.map(audit_job,[(j,out) for j in jobs],chunksize=1),1):
            for key,value in parts:grouped[key].append(value)
            inventory.append(record)
            if number%100==0 or number==len(jobs):print(f'Audited confirmation: {number}/{len(jobs)} classrooms',flush=True)
    assert len(inventory)==completion['classrooms']
    rows=[];by={}
    for key,parts in sorted(grouped.items()):
        study,label,control,arm,group,rep=key;value=e19.aggregate_class_metrics(parts)
        rows.append(dict(study=study,profile=label,control=control,arm=arm,group=group,replicate=rep,**value));by[key]=value
    effects=[]
    for spec in e19.specifications('confirmation',selection):
        study,label,control=spec['study'],spec['label'],spec['control']
        a,b=('small','regular') if study=='star' else ('tracked','mixed')
        for group in ('all','low','high'):
            for metric in [key for key in next(iter(by.values())) if key!='students']:
                delta=[by[study,label,control,a,group,r][metric]-by[study,label,control,b,group,r][metric] for r in range(e19.REPLICATES['confirmation'])]
                primary=control=='main' and label==selection[study]['profile'] and metric=='exam' and (group=='all' if study=='star' else group in {'low','high'})
                result=e19.paired(delta);simultaneous=e19.paired(delta,alpha=.05/3) if primary else None
                effects.append(dict(study=study,profile=label,control=control,group=group,metric=metric,
                    condition=a,reference=b,primary=primary,**result,
                    simultaneous_lo95=simultaneous['lo95'] if simultaneous else '',
                    simultaneous_hi95=simultaneous['hi95'] if simultaneous else ''))
    derived.mkdir();e19.write_csv(derived/'run_metrics.csv',rows);e19.write_csv(derived/'effects.csv',effects)
    e19.save_json(derived/'effects.json',effects)
    e19.save_json(derived/'analysis_manifest.json',dict(classrooms=len(inventory),raw_audits='all passed',
        design_lock_sha256=e19.sha256(root/'design-lock.json'),stage_completion_sha256=e19.sha256(out/'complete.json'),
        selection_sha256=gate,historical_entries_verified=e19.historical(),inventory=inventory,
        execution_lock_sha256=e19.sha256(root/'confirmation-execution-lock.json'),
        hashes={p.name:e19.sha256(p) for p in sorted(derived.iterdir())},
        interpretation='Paired Monte Carlo uncertainty, not human-study sampling uncertainty.'))
    for r in effects:
        if r['primary']:print(f"{r['study']}/{r['group']}: {r['effect']:+.3f} [{r['lo95']:+.3f}, {r['hi95']:+.3f}]",flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=REPO/'runs/E19-teacher-study-r1')
    parser.add_argument('--workers',type=int,default=8)
    parser.add_argument('--analyze',action='store_true')
    args=parser.parse_args()
    if not 1<=args.workers<=8:raise ValueError('Use 1–8 workers')
    root=args.root;out=root/'confirmation'
    if args.analyze:
        analyze_confirmation(root,args.workers);return
    e19.verify(root);selection=e19.selected(root)
    if (out/'complete.json').exists():raise ValueError('Stage is complete')
    sources={str(p.relative_to(REPO)).replace('\\','/'):e19.sha256(p) for p in [Path(__file__),
        REPO/'tests/test_e19_parallel_confirmation.py',REPO/'docs/experiments/E19-execution-addendum.md']}
    driver_lock=root/'confirmation-execution-lock.json'
    if driver_lock.exists():
        locked=e19.load_config(driver_lock)
        assert locked['sources']==sources and locked['workers']==args.workers
        assert locked['selection_sha256']==e19.sha256(root/'selection.json')
    else:
        e19.save_json(driver_lock,dict(created_utc=datetime.now(timezone.utc).isoformat(),sources=sources,
            workers=args.workers,design_lock_sha256=e19.sha256(root/'design-lock.json'),
            selection_sha256=e19.sha256(root/'selection.json'),
            interpretation='Execution transport only; E19 jobs, sources, seeds, settings and analysis unchanged.'))
    out.mkdir(exist_ok=True)
    e19.save_json(out/'stage-lock.json',dict(design_lock_sha256=e19.sha256(root/'design-lock.json'),
        selection_sha256=e19.sha256(root/'selection.json'),stage='confirmation',
        seed=e19.SEEDS['confirmation'],replicates=e19.REPLICATES['confirmation'],
        specifications=e19.specifications('confirmation',selection),
        execution_lock_sha256=e19.sha256(driver_lock)))
    jobs=[j for rep in range(e19.REPLICATES['confirmation']) for j in e19.jobs('confirmation',rep,selection)]
    inventory=[];used=0
    with ProcessPoolExecutor(max_workers=args.workers) as executor:
        for number,(record,reused) in enumerate(executor.map(execute,[(j,out) for j in jobs],chunksize=1),1):
            inventory.append(record);used+=reused
            if number%100==0 or number==len(jobs):
                print(f'Confirmation: {number}/{len(jobs)} classrooms complete ({used} reused)',flush=True)
    e19.save_json(out/'inventory.json',inventory)
    e19.save_json(out/'execution-lock.json',e19.load_config(driver_lock))
    for name,digest in sources.items():assert e19.sha256(REPO/name)==digest
    e19.save_json(out/'complete.json',dict(classrooms=len(inventory),
        hashes={p:e19.sha256(out/p) for p in ('stage-lock.json','inventory.json','execution-lock.json')}))
    e19.verify(root)


if __name__=='__main__':main()
