"""E25: shared bounded parameter search, independent selection, fresh multi-study tests."""
from pathlib import Path
from copy import deepcopy
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import gzip
import json
import sys
import numpy as np
from classroom_swarm import repaired_config as config
from classroom_swarm.v4_repaired import simulate_repaired
from classroom_swarm.repaired_validation import validate_repaired_log, deep_audit
from classroom_swarm.v4_public_ai import PublicAIDraws
from classroom_swarm.tutoring_settings import TutoringParams
from classroom_swarm.v4 import V4Log

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'scripts'))
import e23_promising_mechanisms as e23
import e24_existing_mechanism_audit as e24

ROOT=REPO/'runs/E25-plausible-fit-r1'
PLAN=REPO/'docs/experiments/E25-plausible-fit-plan.md'
MAIN=('star','kenya','ai','seating','teacher_rewards')
SECONDARY=('lab_single','lab_repeated','composition')
POOLS={'training':(2,51000),'selection':(4,52000),'fresh':(16,53000)}
POPULATION,GENERATIONS,OPT_SEED=8,2,88251010
# name, lower, upper, reference, logarithmic, destination, applicable cases
PARAMETERS=[
 ('observation_update',.5,1.,.5,False,'teacher.observation_learning_rate',('kenya',)),
 ('mastery_threshold',.6,.8,.7,False,'design.curriculum.mastery_threshold',('kenya',)),
 ('teacher_linear_cost',.0001,.002,.001,True,'extensions.teacher_work.effort_cost',MAIN+SECONDARY),
 ('teacher_convex_cost',.0005,.004,.002,True,'extensions.teacher_work.quadratic_cost',MAIN+SECONDARY),
 ('teacher_intrinsic',.1,1.,.2,True,'extensions.teacher_work.intrinsic_weight',MAIN+SECONDARY),
 ('teacher_gain_belief',.01,.04,.02,True,'extensions.teacher_work.belief_gain_rate',MAIN+SECONDARY),
 ('helper_intrinsic',.01,.04,.02,True,'extensions.helper_contract.helper_intrinsic_value',MAIN+SECONDARY),
 ('helper_cost',.75,1.5,1.,False,'extensions.helper_contract.helper_cost_multiplier',MAIN+SECONDARY),
 ('exam_access_cost',.25,.4,.35,False,'exam_access_cost',('teacher_rewards',)),
 ('material_quality',.6,1.,.8,False,'extensions.learning_process.material_quality',MAIN+SECONDARY),
]

def target(case,a,b,group,metric,direction,margin=.1):
    return dict(case=case,a=a,b=b,group=group,metric=metric,direction=direction,margin=margin)

TARGETS=[
 target('star','small','regular','all','core_potential','positive'),
 target('kenya','tracked','mixed','low','core_potential','positive'),
 target('kenya','tracked','mixed','high','core_potential','positive'),
 target('ai','answer','none','all','core_potential','negative'),
 target('ai','tutor','answer','all','core_potential','positive'),
 target('ai','tutor','none','all','core_potential','near_zero',.2),
 target('ai','answer','none','all','homework','positive'),
 target('ai','tutor','none','all','homework','positive'),
 target('seating','cross','random','low','core_potential','near_zero',.2),
 target('seating','reward','cross','low','core_potential','positive'),
 target('seating','reward','cross','high','core_potential','near_zero',.2),
 target('teacher_rewards','rewarded','unrewarded','all','familiar_potential','positive'),
 target('teacher_rewards','rewarded','unrewarded','all','familiar_participation','positive',1.),
 target('teacher_rewards','rewarded','unrewarded','all','novel_potential','near_zero',.5),
 target('teacher_rewards','rewarded','unrewarded','all','knowledge_gain','near_zero',.5),
]
SECONDARY_TARGETS=[target(case,'mixed',b,'low','core_potential','positive') for case in ('lab_single','lab_repeated') for b in ('tracked','solo')]

def transform(vector):
    assert len(vector)==len(PARAMETERS) and np.all(np.isfinite(vector)) and np.all((np.asarray(vector)>=0)&(np.asarray(vector)<=1)), 'outside normalized bounds'
    return {name:float(np.exp(np.log(lo)+v*(np.log(hi)-np.log(lo)))) if log else float(lo+v*(hi-lo))
        for v,(name,lo,hi,ref,log,path,cases) in zip(vector,PARAMETERS)}

def reference_vector():
    return np.array([(np.log(ref)-np.log(lo))/(np.log(hi)-np.log(lo)) if log else (ref-lo)/(hi-lo)
        for name,lo,hi,ref,log,path,cases in PARAMETERS])

def jobs(pool,cohort,profile,vector=None,cases=MAIN):
    draw=POOLS[pool][1]+cohort
    values=transform(vector) if vector is not None else None
    result=[]
    for original in e23.build_jobs('confirmation',draw-e23.PHASES['confirmation'][1]):
        if original['variant']!='A33' or original['profile']!='default' or original['case'] not in cases: continue
        j=deepcopy(original); r=j['resolved']; j.update(pool=pool,cohort=cohort,profile=profile)
        j['condition']=f"{j['case']}_{profile}_{j['arm']}_s{j['section']}"; r['name']=j['condition']
        if values is not None:
            # Predeclared plausible reference: heterogeneous initial test confidence;
            # costs remain utility units, not a guessed monetary or attendance rate.
            if j['case']=='teacher_rewards': r['initial']['confidence']={'kind':'from_knowledge'}
            for name,lo,hi,ref,log,path,applicable in PARAMETERS:
                if j['case'] not in applicable: continue
                value=values[name]
                if path=='exam_access_cost':
                    for exam in r['extensions']['test_preparation']['exams']: exam['access_cost']=value
                else:
                    keys=path.split('.'); branch=r
                    for key in keys[:-1]: branch=branch[key]
                    branch[keys[-1]]=value
        j['repairs_enabled']=profile!='legacy'; result.append(j)
    return result

def native(x):
    if isinstance(x,np.generic): return x.item()
    if isinstance(x,np.ndarray): return x.tolist()
    raise TypeError(type(x).__name__)

def read_raw(folder):
    complete=config.load_config(folder/'complete.json')
    for path,digest in complete['hashes'].items(): assert config.sha256(folder/path)==digest, str(folder/path)
    with gzip.open(folder/'raw.json.gz','rt',encoding='utf-8') as handle: data=json.load(handle)
    log=V4Log(data['manifest']); log.tables=data['tables']; validate_repaired_log(log)
    counts=deep_audit(log)
    return log,len(complete['hashes']),counts

def worker(task):
    root_string,pool,cohort,profile,vector,cases=task; root=Path(root_string)
    declaration=jobs(pool,cohort,profile,vector,cases); dest=root/pool/profile/f'cohort{cohort:04d}'
    rows=[]; inventory=[]
    for j in declaration:
        r=j['resolved']; folder=dest/'raw'/j['condition']
        if not (folder/'complete.json').exists():
            assert not folder.exists(), 'preserve partial failure; choose a new execution identity'
            p=TutoringParams(**r['params'])
            log=simulate_repaired(p,config.make_graph(r['network'],p.N,j['seed'],j['replicate']),
                PublicAIDraws(j['seed'],j['replicate'],p.N,p.items,p.exam_items),r['name'],r['initial'],
                r['teacher'],r['mechanisms'],r['extensions'],r['design'],j['repairs_enabled'])
            validate_repaired_log(log,p)
            folder.mkdir(parents=True); config.save_json(folder/'declared-job.json',j)
            with gzip.open(folder/'raw.json.gz','wt',encoding='utf-8',compresslevel=3) as handle:
                json.dump(dict(manifest=log.manifest,tables=log.tables),handle,allow_nan=False,default=native,separators=(',',':'))
            config.save_json(folder/'complete.json',dict(hashes={f.name:config.sha256(f) for f in folder.iterdir()}))
        log,hashes,counts=read_raw(folder)
        inventory.append(dict(condition=j['condition'],hashes=hashes,checks=counts,path=str(folder.relative_to(root))))
        for group,ids in j['groups'].items():
            if ids:
                row=dict(case=j['case'],arm=j['arm'],section=j['section'],group=group,cohort=cohort,profile=profile,**e23.metrics(log,ids))
                h=r['params']['H']; doses=[d for d in log.tables['learning_doses'] if d['student'] in ids]
                row['foundation_share']=float(np.mean([v['level']==0 for v in log.tables.get('curriculum_choices',[])])) if log.tables.get('curriculum_choices') else None
                row['mean_effort']=float(np.mean([d['effort'] for d in doses])) if doses else 0.
                row['productive_ticks']=sum(d['dose'] for d in doses)/len(ids)/h
                rows.append(row)
    config.save_json(dest/'class-metrics.json',rows); config.save_json(dest/'raw-inventory.json',inventory)
    config.save_json(dest/'run-complete.json',dict(classrooms=len(inventory),hashes_verified=sum(r['hashes'] for r in inventory),
        independent_checks={name:sum(r['checks'][name] for r in inventory) for name in ('readiness','choices','pretests')},
        hashes={name:config.sha256(dest/name) for name in ('class-metrics.json','raw-inventory.json')}))
    return pool,profile,cohort,rows

def aggregate(rows):
    collected=defaultdict(list)
    for r in rows: collected[r['case'],r['arm'],r['group'],r['cohort']].append(r)
    out={}
    for key,parts in collected.items():
        n=sum(p['students'] for p in parts); value={'students':n}
        for name in parts[0]:
            if name in ('case','arm','section','group','cohort','profile','students'): continue
            available=[p for p in parts if p[name] is not None]
            value[name]=sum(p[name]*p['students'] for p in available)/sum(p['students'] for p in available) if available else None
        out[key]=value
    return out

def paired(values,alpha=.05):
    a=np.array(values,float); rng=np.random.default_rng(882525)
    means=a[rng.integers(0,len(a),size=(20000,len(a)))].mean(axis=1)
    lo,hi=np.quantile(means,[alpha/2,1-alpha/2])
    return dict(effect=float(a.mean()),lo95=float(lo),hi95=float(hi),deltas=a.tolist(),positive_cohorts=int(sum(a>0)),negative_cohorts=int(sum(a<0)))

def effects(rows,specs=TARGETS):
    by=aggregate(rows); results=[]; reps=sorted(set(r['cohort'] for r in rows))
    for s in specs:
        if not any(k[0]==s['case'] for k in by): continue
        delta=[by[s['case'],s['a'],s['group'],rep][s['metric']]-by[s['case'],s['b'],s['group'],rep][s['metric']] for rep in reps]
        r=dict(s,**paired(delta)); sim=paired(delta,.05/len(TARGETS))
        r.update(family_lo95=sim['lo95'],family_hi95=sim['hi95'])
        if s['direction']=='positive': r['direction_match']=r['effect']>0; r['robust_match']=r['family_lo95']>0
        elif s['direction']=='negative': r['direction_match']=r['effect']<0; r['robust_match']=r['family_hi95']<0
        else: r['direction_match']=abs(r['effect'])<=s['margin']; r['robust_match']=r['family_lo95']>=-s['margin'] and r['family_hi95']<=s['margin']
        results.append(r)
    return results

def assess(rows,vector):
    e=effects(rows); by=aggregate(rows); problems=[]
    for k,v in by.items():
        if k[2]!='all': continue
        if v['productive_fraction']<.2: problems.append(f'{k}: fewer than 20% productive dose events')
        if k[0]=='teacher_rewards' and k[1]=='unrewarded' and v['familiar_participation']<60:
            problems.append(f'{k}: baseline enrolled exam participation below 60%')
    star=[v for k,v in by.items() if k[0]=='star' and k[2]=='all']
    if star and np.mean([v['guidance_count'] for v in star])<=0: problems.append('class-size explanation has no guidance channel in use')
    teacher=[v for k,v in by.items() if k[0]=='teacher_rewards' and k[1]=='rewarded' and k[2]=='all']
    if teacher and np.mean([v['coaching_count'] for v in teacher])<=0: problems.append('teacher incentive explanation has no test preparation in use')
    losses=defaultdict(list)
    for r in e:
        scale=r['margin']; v=r['effect']; d=r['direction']
        gap=max(0,scale-v) if d=='positive' else max(0,scale+v) if d=='negative' else max(0,abs(v)-scale)
        losses[r['case']].append((gap/scale)**2)
    trend=float(np.mean([np.mean(v) for v in losses.values()]))
    prior=.02*float(np.mean((np.array(vector)-reference_vector())**2))
    return dict(feasible=not problems,problems=problems,trend_loss=trend,prior_penalty=prior,
        objective=trend+prior+(1000 if problems else 0),effects=e,parameters=transform(vector),
        activity=[dict(case=k[0],arm=k[1],group=k[2],cohort=k[3],**v) for k,v in sorted(by.items()) if k[2]=='all'])

def verify(root=ROOT):
    lock=config.load_config(root/'design-lock.json')
    for name,digest in lock['sources'].items(): assert config.sha256(REPO/name)==digest,name
    for name,digest in lock['declarations'].items(): assert config.sha256(root/name)==digest,name
    e24.verify()
    return lock

def prepare(root):
    assert not root.exists(), 'use a new experiment identity'; e24.verify()
    for vector in (np.zeros(len(PARAMETERS)),np.ones(len(PARAMETERS))):
        for job in jobs('training',0,'preflight',vector):
            c=config.template(); c.update(seed=job['seed'],replicates=1,conditions=[job['resolved']])
            config.preflight(config.resolve_config(c))
    root.mkdir(parents=True)
    config.save_json(root/'parameter-space.json',[dict(name=n,lower=l,upper=u,reference=r,logarithmic=g,path=p,cases=c) for n,l,u,r,g,p,c in PARAMETERS])
    config.save_json(root/'targets.json',dict(primary=TARGETS,secondary=SECONDARY_TARGETS))
    # Freeze all cohorts before any outcomes; subsequent candidates follow the locked algorithm.
    for pool,(n,offset) in POOLS.items():
        for rep in range(n): config.save_json(root/f'{pool}-cohort{rep:04d}.json',jobs(pool,rep,'default',cases=MAIN+SECONDARY))
    sources=list(sorted((REPO/'src/classroom_swarm').glob('*.py')))+[Path(__file__),PLAN,REPO/'docs/26-v4-policy-repair.md',REPO/'tests/test_v4_repaired.py',REPO/'tests/test_e25_parameter_fit.py']
    config.save_json(root/'design-lock.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
        sources={str(p.relative_to(REPO)).replace('\\','/'):config.sha256(p) for p in sources},
        declarations={p.name:config.sha256(p) for p in root.glob('*.json')},pools=POOLS,
        algorithm=dict(name='bounded rand/1/bin differential evolution',population=POPULATION,generations=GENERATIONS,mutation=.7,crossover=.8,seed=OPT_SEED,regularization=.02),
        selection='best three feasible candidates plus reference; independent four cohorts; choose smallest objective; freeze before fresh',
        identities=['No competence from copying, payments, elapsed time or assessment.','Unrelated zero-transfer effects are structural, excluded from fitting.','High starters may start at mastered foundation; single-lab upper null is not an empirical recovery.'],
        storage='lossless gzipped JSON of all raw tables, reloaded and audited; no raw candidate discarded',
        status='search protocol and untouched cohort definitions locked before outcomes'))
    print('E25 sources, bounds, targets, optimizer and all cohorts locked.',flush=True)

def evaluate(pool,vectors,workers,root):
    tasks=[(str(root),pool,rep,label,list(v),MAIN) for label,v in vectors for rep in range(POOLS[pool][0])]
    allrows=defaultdict(list)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        futures={executor.submit(worker,t):t for t in tasks}
        for future in as_completed(futures):
            pool,label,cohort,rows=future.result(); allrows[label]+=rows
            print(f'{pool}/{label}/cohort{cohort}: {len(rows)} group records audited.',flush=True)
    out={}
    for label,v in vectors:
        out[label]=assess(allrows[label],v)
        config.save_json(root/pool/label/'assessment.json',out[label])
    return out

def search(root,workers):
    verify(root); assert not (root/'search-complete.json').exists(), 'preserve completed search'
    rng=np.random.default_rng(OPT_SEED); pop=rng.random((POPULATION,len(PARAMETERS))); pop[0]=reference_vector()
    history=[]; allvectors={}; incumbents=[]
    for generation in range(GENERATIONS+1):
        if generation==0: trial=pop.copy()
        else:
            trial=[]
            for i in range(POPULATION):
                a,b,c=rng.choice([j for j in range(POPULATION) if j!=i],3,replace=False)
                mutant=np.clip(pop[a]+.7*(pop[b]-pop[c]),0,1); mask=rng.random(len(PARAMETERS))<.8; mask[rng.integers(len(PARAMETERS))]=True
                trial.append(np.where(mask,mutant,pop[i]))
            trial=np.array(trial)
        vectors=[(f'g{generation:02d}c{i:02d}',v) for i,v in enumerate(trial)]
        for label,v in vectors: allvectors[label]=v.tolist()
        config.save_json(root/f'generation{generation:02d}-declared.json',{label:v.tolist() for label,v in vectors})
        out=evaluate('training',vectors,workers,root)
        for i,(label,v) in enumerate(vectors):
            history.append(dict(candidate=label,vector=v.tolist(),**out[label]))
            if generation==0: incumbents.append(label)
            elif out[label]['objective']<next(h['objective'] for h in history if h['candidate']==incumbents[i]): pop[i]=v; incumbents[i]=label
        config.save_json(root/f'generation{generation:02d}-results.json',history[-POPULATION:])
        print(f'Generation {generation}: best objective {min(h["objective"] for h in history):.6f}',flush=True)
    feasible=sorted([h for h in history if h['feasible']],key=lambda h:(h['objective'],h['candidate']))
    shortlist=[h['candidate'] for h in feasible[:3]]
    if 'g00c00' not in shortlist: shortlist.append('g00c00')
    selected=evaluate('selection',[(s,allvectors[s]) for s in shortlist],workers,root)
    eligible=[s for s in shortlist if selected[s]['feasible']]
    best=min(eligible,key=lambda s:(selected[s]['objective'],s)) if eligible else 'g00c00'
    result=dict(candidate=best,vector=allvectors[best],parameters=transform(allvectors[best]),
        shortlist=shortlist,selection=selected[best],all_training=history,
        feasible_selection_candidates=eligible,status='selection frozen before fresh outcomes; finite search does not prove optimality or design impossibility',
        source_lock_sha256=config.sha256(root/'design-lock.json'))
    config.save_json(root/'search-complete.json',result)
    config.save_json(root/'selection-lock.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
        search_sha256=config.sha256(root/'search-complete.json'),sources=verify(root)['sources']))
    print(f'Selected {best}; feasible={bool(eligible)}; untouched fresh pool remains unrun.',flush=True)

def fresh(root,workers):
    verify(root); lock=config.load_config(root/'selection-lock.json')
    assert config.sha256(root/'search-complete.json')==lock['search_sha256']
    assert not (root/'fresh-complete.json').exists(), 'preserve fresh outcome'
    chosen=config.load_config(root/'search-complete.json'); vectors=[('legacy',None),('default',None),('selected',chosen['vector'])]
    tasks=[(str(root),'fresh',rep,label,v,MAIN+SECONDARY) for label,v in vectors for rep in range(POOLS['fresh'][0])]
    rows=defaultdict(list)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        for future in as_completed([executor.submit(worker,t) for t in tasks]):
            pool,label,rep,r=future.result(); rows[label]+=r; print(f'Fresh/{label}/cohort{rep} complete and audited.',flush=True)
    for label,v in vectors:
        config.save_json(root/'fresh'/label/'effects.json',effects(rows[label],TARGETS+SECONDARY_TARGETS))
        config.save_json(root/'fresh'/label/'assessment.json',assess(rows[label],v or reference_vector().tolist()))
        config.save_json(root/'fresh'/label/'all-class-metrics.json',rows[label])
    changes=[]
    for label,reference in [('default','legacy'),('selected','default')]:
        a=aggregate(rows[label]); b=aggregate(rows[reference])
        for case,arm,group,rep in sorted(a):
            if rep!=0: continue
            for metric in ('core_potential','knowledge_gain','homework','familiar_potential','novel_potential','familiar_participation','teacher_spent','guidance_count','coaching_count','followup_count','helper_gain','productive_fraction'):
                if a[case,arm,group,0].get(metric) is None: continue
                values=[a[case,arm,group,r][metric]-b[case,arm,group,r][metric] for r in range(POOLS['fresh'][0])]
                changes.append(dict(profile=label,reference=reference,case=case,arm=arm,group=group,metric=metric,**paired(values)))
    config.save_json(root/'fresh-changes.json',changes)
    inventory=[config.load_config(p) for p in root.glob('*/*/cohort*/run-complete.json')]
    config.save_json(root/'fresh-complete.json',dict(classrooms=sum(r['classrooms'] for r in inventory),raw_hashes_verified=sum(r['hashes_verified'] for r in inventory),
        independent_checks={k:sum(r['independent_checks'][k] for r in inventory) for k in ('readiness','choices','pretests')},
        selection_sha256=config.sha256(root/'selection-lock.json'),fresh_profiles=[s for s,v in vectors],fresh_replicates=POOLS['fresh'][0]))
    for label in rows:
        print(label+': '+', '.join(f"{r['case']}/{r['group']}/{r['metric']}={r['effect']:+.3f}" for r in effects(rows[label])),flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('command',choices=['prepare','search','fresh','verify']); p.add_argument('--root',type=Path,default=ROOT); p.add_argument('--workers',type=int,default=8); a=p.parse_args()
    if a.command=='prepare': prepare(a.root)
    elif a.command=='search': search(a.root,a.workers)
    elif a.command=='fresh': fresh(a.root,a.workers)
    else: verify(a.root); print('E25 and historical source locks pass.')

if __name__=='__main__': main()
