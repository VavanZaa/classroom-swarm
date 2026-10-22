"""E27 keeps the fitted teacher's productivity expectation below the physical ceiling."""
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
from collections import defaultdict
from datetime import datetime,timezone
import argparse
import numpy as np
import e26_protocol_parameter_fit as fit
from classroom_swarm import repaired_config as config

REPO=fit.REPO; ROOT=REPO/'runs/E27-teacher-belief-check-r1'
CASES=('star','teacher_rewards')
CAP=.0584/3.
PLAN=REPO/'docs/experiments/E27-teacher-belief-check-plan.md'

def encode(values):
    return [(np.log(values[name])-np.log(lo))/(np.log(hi)-np.log(lo)) if log else (values[name]-lo)/(hi-lo)
        for name,lo,hi,ref,log,path,cases in fit.PARAMETERS]

def candidates():
    values=config.load_config(fit.ROOT/'search-complete.json')['parameters']; ratio=CAP/values['teacher_gain_belief']
    capped={**values,'teacher_gain_belief':CAP}
    scaled={**capped,'teacher_linear_cost':max(.0001,values['teacher_linear_cost']*ratio),
        'teacher_convex_cost':max(.0005,values['teacher_convex_cost']*ratio)}
    return {name:encode(v) for name,v in [('cap_only',capped),('cap_scaled_costs',scaled),
        ('cap_scaled_intrinsic09',{**scaled,'teacher_intrinsic':.9}),
        ('cap_minimum_costs',{**capped,'teacher_linear_cost':.0001,'teacher_convex_cost':.0005}),
        ('cap_minimum_intrinsic1',{**capped,'teacher_linear_cost':.0001,'teacher_convex_cost':.0005,'teacher_intrinsic':1.})]}

def verify():
    lock=config.load_config(ROOT/'design-lock.json'); fit.verify()
    for name,digest in lock['sources'].items(): assert config.sha256(REPO/name)==digest,name
    for name,digest in lock['declarations'].items(): assert config.sha256(ROOT/name)==digest,name
    assert config.sha256(fit.ROOT/'search-complete.json')==lock['e26_selection_sha256']
    return lock

def prepare():
    fit.verify(); assert not ROOT.exists(); assert not (fit.ROOT/'fresh').exists(), 'declare before E26 fresh outcomes'
    ROOT.mkdir(parents=True); config.save_json(ROOT/'candidates.json',candidates())
    for cohort in list(range(3000,3004))+list(range(4000,4004)):
        config.save_json(ROOT/f'cohort{cohort}.json',fit.jobs('training',cohort,'unfitted',cases=CASES))
    sources=[Path(__file__),PLAN,REPO/'tests/test_e27_teacher_belief_check.py',REPO/'scripts/e26_protocol_parameter_fit.py',REPO/'src/classroom_swarm/effort_runtime.py']
    config.save_json(ROOT/'design-lock.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
        sources={str(p.relative_to(REPO)).replace('\\','/'):config.sha256(p) for p in sources},
        declarations={p.name:config.sha256(p) for p in ROOT.glob('*.json')},e26_selection_sha256=config.sha256(fit.ROOT/'search-complete.json'),
        physical_ceiling=CAP,other_boundaries='unchanged E26 bounds; no physical-learning change',
        selection='five fixed development candidates on four cohorts; best two feasible plus cap_only on four further cohorts; freeze before fresh',
        fresh='sixteen E26 untouched cohorts, STAR and teacher incentives only; no E26 fresh outcome used for selection',
        identities='Other E26 cases have no discretionary teacher actions; these three subjective/cost preferences cannot change their student trajectories. No new interaction.'))
    print('E27 physically coherent belief probes locked before E26/E27 fresh outcomes.',flush=True)

def evaluate(stage,labels,vectors,cohorts,workers):
    rows=defaultdict(list)
    tasks=[(str(ROOT),'training',rep,label,vectors[label],CASES) for label in labels for rep in cohorts]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for future in as_completed([pool.submit(fit.worker,t) for t in tasks]):
            _,label,rep,r=future.result(); rows[label]+=r; print(f'{stage}/{label}/{rep} audited.',flush=True)
    result={label:fit.assess(rows[label],vectors[label]) for label in labels}
    config.save_json(ROOT/(stage+'-results.json'),result)
    return result

def select(workers):
    verify(); assert not (ROOT/'selection-lock.json').exists()
    vectors=config.load_config(ROOT/'candidates.json')
    development=evaluate('development',list(vectors),vectors,range(3000,3004),workers)
    feasible=sorted([name for name in vectors if development[name]['feasible']],key=lambda n:(development[n]['objective'],n))
    shortlist=feasible[:2]
    if 'cap_only' not in shortlist: shortlist.append('cap_only')
    selection=evaluate('selection',shortlist,vectors,range(4000,4004),workers)
    eligible=[n for n in shortlist if selection[n]['feasible']]
    chosen=min(eligible,key=lambda n:(selection[n]['objective'],n)) if eligible else 'cap_only'
    config.save_json(ROOT/'selection-lock.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),candidate=chosen,
        vector=vectors[chosen],parameters=fit.transform(vectors[chosen]),feasible=bool(eligible),shortlist=shortlist,
        selection_sha256=config.sha256(ROOT/'selection-results.json'),development_sha256=config.sha256(ROOT/'development-results.json'),
        source_lock_sha256=config.sha256(ROOT/'design-lock.json'),status='frozen before any fresh outcome'))
    print(f'E27 selected {chosen}, feasible={bool(eligible)}.',flush=True)

def fresh(workers):
    verify(); selected=config.load_config(ROOT/'selection-lock.json'); assert not (ROOT/'fresh-complete.json').exists()
    tasks=[(str(ROOT),'fresh',rep,'physical_belief',selected['vector'],CASES) for rep in range(16)]; rows=[]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        for future in as_completed([pool.submit(fit.worker,t) for t in tasks]):
            _,label,rep,r=future.result(); rows+=r; print(f'E27 fresh/{rep} audited.',flush=True)
    config.save_json(ROOT/'fresh-effects.json',fit.effects(rows)); config.save_json(ROOT/'fresh-metrics.json',rows)
    config.save_json(ROOT/'fresh-assessment.json',fit.assess(rows,selected['vector']))
    inventories=[config.load_config(p) for p in ROOT.glob('*/*/cohort*/run-complete.json')]
    config.save_json(ROOT/'fresh-complete.json',dict(classrooms=sum(r['classrooms'] for r in inventories),
        raw_hashes_verified=sum(r['hashes_verified'] for r in inventories),selection_sha256=config.sha256(ROOT/'selection-lock.json'),
        independent_checks={k:sum(r['independent_checks'][k] for r in inventories) for k in ('readiness','choices','pretests')}))
    for r in fit.effects(rows): print(r['case'],r['metric'],f"{r['effect']:+.4f} [{r['lo95']:+.4f},{r['hi95']:+.4f}]",flush=True)

def main():
    p=argparse.ArgumentParser(); p.add_argument('command',choices=['prepare','select','fresh','verify']); p.add_argument('--workers',type=int,default=12); a=p.parse_args()
    if a.command=='prepare': prepare()
    elif a.command=='select': select(a.workers)
    elif a.command=='fresh': fresh(a.workers)
    else: verify(); print('E27/E26/E25 and historical source locks passed.')

if __name__=='__main__': main()
