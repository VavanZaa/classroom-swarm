"""Frozen A32 paper-direction probes; every setup retained, no sign-driven fitting."""
from pathlib import Path
from copy import deepcopy
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
import argparse
import json
import sys
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from classroom_swarm import effort_config as config
from classroom_swarm.tutoring_settings import TutoringParams
from classroom_swarm.v4_public_ai import PublicAIDraws
from classroom_swarm.v4_effort_learning import simulate_effort
from classroom_swarm.effort_validation import validate_effort_log
from classroom_swarm.v4 import V4Log

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import e19_teacher_studies as e19
import e21_study_mechanisms as e21

ROOT = REPO / 'runs/E22-A32-study-trends-r1'
REPLICATES, SEED, BOOTSTRAPS, BOOTSTRAP_SEED = 24, 100772201, 20000, 100772299
PLAN = REPO / 'docs/experiments/E22-A32-study-trends-plan.md'


def constant(v): return dict(kind='constant', value=v)


def base(n=30, h=12, ticks=12, teacher=False):
    c = config.template()
    c.update(experiment_id='E22_A32_study_trends_r1', replicates=1)
    c['params'].update(N=n, H=h, ticks=ticks, items=12, exam_items=60,
        exam_every=max(1, h // 4), feedback_delay=0, tutoring_activity='joint_practice',
        allow_hint=False, allow_answer=False, ai_mode='none', distant_weight=0., closeness_spread=0.)
    c['network'].update(family='CUSTOM', edges=[])
    c['initial']['knowledge'] = dict(kind='truncated_normal', mean=.45, std=.1, low=0., high=1.)
    for k in ('confidence','control','benefit_attempt','benefit_hint','benefit_answer','benefit_ai_answer','benefit_ai_tutor'):
        c['initial'][k] = constant(.5)
    c['initial']['learning_efficiency'] = constant(.0584)
    c['initial']['effort_aversion'] = constant(.15)
    c['teacher'].update(enabled=teacher, actions=['instruction'], admin_ticks=0,
        grading_ticks_per_student=0, curriculum='adaptive', observation_sources=['exam'], allocation='round_robin')
    c['extensions']['learning_process']['enabled'] = True
    c['extensions']['teacher_work'].update(enabled=teacher, total_budget=4, actions=[])
    c['conditions'] = [dict(name='reference')]
    c['contrasts'] = []
    return c


def exams(c, participation=False):
    c['mechanisms']['topics'].update(enabled=True, names=['taught','unrelated'],
        schedule=[0]*c['params']['H'], transfer=[[1.,0.],[0.,1.]])
    c['extensions']['test_preparation'].update(enabled=True, participation=participation,
        participation_cost=.6 if participation else 0., exams=[
        dict(name=f, form=f, topic_weights=w, difficulty=.5, format_loading=loading,
             stakes=1., access_cost=.6 if participation else 0.)
        for f,w,loading in [('familiar',[1.,0.],1.), ('novel',[1.,0.],0.),
                            ('unrelated',[0.,1.],0.), ('core',[.5,.5],0.)]])


def clique(groups):
    return [[a,b] for g in groups for a in g for b in g if a<b]


def build_jobs(rep):
    jobs=[]
    def add(case, profile, arm, c, groups=None, ids=None, baseline=None, section=0):
        c=deepcopy(c); ids=list(range(c['params']['N'])) if ids is None else ids
        c['seed']=SEED + list(CASES).index(case)*100
        c['extensions']['student_ids']=ids
        name=f'{case}_{profile}_{arm}_s{section}'
        c['conditions']=[dict(name=name)]
        r=config.resolve_config(c)['conditions'][0]
        jobs.append(dict(case=case,profile=profile,arm=arm,section=section,condition=name,
            seed=c['seed'],replicate=rep,resolved=r,global_ids=ids,baseline_scores=baseline or [],
            groups=groups or {'all':list(range(len(ids)))}))
    # One fixed school in both class-size arms. Teacher resources are per section.
    pop=e19.cohort('star',SEED,rep,n=120)
    for profile,cost in [('default',.001),('lower_teacher_cost',.0001)]:
        for arm,n in [('small',15),('regular',24)]:
            for section,start in enumerate(range(0,120,n)):
                ids=list(range(start,start+n)); c=base(n,ticks=18,teacher=True)
                c['initial']['knowledge']=dict(kind='values',values=[pop['knowledge'][i] for i in ids])
                c['teacher'].update(guidance_strength=.3, identity=f'star-{section}',
                    observation_prior=float(np.mean([pop['observed_baseline'][i] for i in ids])))
                c['extensions']['teacher_work'].update(total_budget=8,actions=['guidance'],effort_cost=cost)
                add('star',profile,arm,c,ids=ids,baseline=[pop['observed_baseline'][i] for i in ids],section=section)
    pop=e19.cohort('kenya',SEED+100,rep,mean=.45)
    for profile in ('default','fixed_curriculum','crowdout_budget'):
        for arm in ('mixed','tracked'):
            for section,ids in enumerate(pop[arm]):
                c=base(42,teacher=True)
                c['initial']['knowledge']=dict(kind='values',values=[pop['knowledge'][i] for i in ids])
                c['teacher'].update(learning_multiplier=2.,identity=f'kenya-{section}',
                    observation_prior=float(np.mean([pop['observed_baseline'][i] for i in ids])),
                    curriculum='fixed' if profile=='fixed_curriculum' else 'adaptive')
                c['extensions']['teacher_work'].update(total_budget=3 if profile=='crowdout_budget' else 6,
                    allow_instruction_crowdout=profile=='crowdout_budget')
                groups={'all':list(range(42)),**{g:[j for j,i in enumerate(ids) if i in pop[g]] for g in ('low','high')}}
                add('kenya',profile,arm,c,groups,ids,[pop['observed_baseline'][i] for i in ids],section)
    for profile in ('default','future_stakes','more_AI_uses'):
        for arm in ('none','answer','tutor'):
            c=base(h=4,teacher=True); c['params'].update(ai_mode=arm,ai_start=1,max_ai_uses=3 if profile=='more_AI_uses' else 1)
            c['initial']['knowledge']=dict(kind='truncated_normal',mean=.5,std=.1,low=0.,high=1.)
            if profile=='future_stakes': c['extensions']['learning_process']['future_test_value']=constant(20.)
            add('ai',profile,arm,c)
    for case in ('lab_single','lab_repeated'):
        for profile in (('default','no_future_stakes') if case=='lab_single' else ('default',)):
            for arm in ('mixed','tracked','solo'):
                c=base(8,h=1 if case=='lab_single' else 20)
                c['params'].update(tutoring_activity='joint_practice' if case=='lab_single' else 'shared_practice',allow_hint=arm!='solo')
                c['initial']['knowledge']=dict(kind='values',values=[.35]*4+[.75]*4)
                c['network']['edges']=clique([[0,1,2,3],[4,5,6,7]] if arm=='tracked' else [[0,1,4,5],[2,3,6,7]])
                c['extensions']['learning_process'].update(material_access=False,
                    future_test_value=constant(0. if profile=='no_future_stakes' else 20.))
                add(case,profile,arm,c,{'all':list(range(8)),'low':list(range(4)),'high':list(range(4,8))})
    pop=e19.cohort('star',SEED+500,rep,n=32)
    # Bimodal ability and independent, observed 100-item baseline; lower/upper by observed rank.
    rng=np.random.default_rng(np.random.SeedSequence([SEED+500,rep,133]))
    k=rng.permutation([.35]*16+[.75]*16).tolist()
    u=np.random.default_rng(np.random.SeedSequence([SEED+500,rep,131])).random((100,32))
    scores=(u<np.array(k)).mean(axis=0).tolist(); ranks=sorted(range(32),key=lambda i:(scores[i],i))
    low,high=ranks[:16],ranks[16:]; cross=[[a,b] for a,b in zip(high,low)]
    order=rng.permutation(32).tolist(); random=[[order[j],order[j+1]] for j in range(0,32,2)]
    for profile,prize in [('default',1.),('stronger_reward',5.)]:
        for arm in (('random','cross','reward') if profile=='default' else ('random','cross','reward','placebo','high_cost')):
            c=base(32,h=20,teacher=True); c['params']['allow_hint']=True
            c['initial']['knowledge']=dict(kind='values',values=k)
            c['network']['edges']=random if arm=='random' else cross
            c['extensions']['helper_contract'].update(enabled=arm in ('reward','placebo','high_cost'),pairs=cross,
                baseline_scores=scores,checkpoints=[10,20],offer_ticks=[6],prize=prize,
                placebo_payment=arm=='placebo',helper_cost_multiplier=5. if arm=='high_cost' else 1.)
            add('seating',profile,arm,c,{'all':list(range(32)),'low':low,'high':high},baseline=scores)
    for profile in ('default','stronger_reward','format_without_participation','concept_only'):
        for arm in ('unrewarded','rewarded'):
            c=base(ticks=18,teacher=True); exams(c,participation=profile in ('default','stronger_reward'))
            strength=1. if profile=='default' else 20.
            c['extensions']['teacher_work'].update(total_budget=8,
                actions=['guidance','explanation'] if profile=='concept_only' else
                    (['coaching','guidance','followup'] if profile in ('default','stronger_reward') else ['coaching','guidance']),
                contract=dict(strength=strength if arm=='rewarded' else 0.,forms=['familiar']))
            add('teacher_rewards',profile,arm,c)
    for profile in ('default','copying'):
        for arm in ('low','high'):
            c=base(h=20); c['params'].update(allow_hint=True,allow_answer=profile=='copying')
            c['initial']['knowledge']=dict(kind='values',values=[.35]*15+[.35 if arm=='low' else .75]*15)
            c['network'].update(family='ER',d_bar=6,edges=None)
            add('composition',profile,arm,c,{'focal':list(range(15))})
    return jobs


CASES={
 'star':dict(paper='Krueger / STAR',url='https://www.nber.org/papers/w6051',profiles=['default','lower_teacher_cost']),
 'kenya':dict(paper='Duflo, Dupas and Kremer',url='https://www.aeaweb.org/articles?id=10.1257/aer.101.5.1739',profiles=['default','fixed_curriculum','crowdout_budget']),
 'ai':dict(paper='Bastani and colleagues',url='https://www.pnas.org/doi/10.1073/pnas.2422633122',profiles=['default','future_stakes','more_AI_uses']),
 'lab_single':dict(paper='Kimbrough, McGee and Shigeoka',url='https://www.crepe.e.u-tokyo.ac.jp/events/20190325_shigeoka.pdf',profiles=['default','no_future_stakes']),
 'lab_repeated':dict(paper='Earlier repeated-practice probe',url='https://www.crepe.e.u-tokyo.ac.jp/events/20190325_shigeoka.pdf',profiles=['default']),
 'seating':dict(paper='Wu, Zhang and Wang',url='https://www.aeaweb.org/content/file?id=15848',profiles=['default','stronger_reward']),
 'teacher_rewards':dict(paper='Glewwe, Ilias and Kremer',url='https://www.aeaweb.org/articles?id=10.1257/app.2.3.205',profiles=['default','stronger_reward','format_without_participation','concept_only']),
 'composition':dict(paper='Booij, Leuven and Oosterbeek — partial probe',url='https://leuven.economists.nl/pdf/ability_final.pdf',profiles=['default','copying'])}


def comparisons():
    rows=[]
    def add(case,a,b,g='all',metric='core_potential',target='positive',primary=True,profiles=None):
        rows.append(dict(case=case,a=a,b=b,group=g,metric=metric,target=target,primary=primary,
            profiles=profiles or CASES[case]['profiles']))
    add('star','small','regular')
    for g in ('low','high'): add('kenya','tracked','mixed',g)
    for a,b,t in [('answer','none','negative'),('tutor','answer','positive'),('tutor','none','near_zero')]: add('ai',a,b,target=t)
    for case in ('lab_single','lab_repeated'):
        for b in ('tracked','solo'): add(case,'mixed',b,'low',primary=case=='lab_single')
    add('seating','cross','random','low',target='near_zero')
    add('seating','reward','cross','low')
    add('seating','reward','cross','high',target='near_zero')
    for a in ('placebo','high_cost'): add('seating',a,'reward','low',target='negative',primary=False,profiles=['stronger_reward'])
    for metric,target in [('familiar_potential','positive'),('unrelated_potential','near_zero'),('familiar_participation','positive')]:
        add('teacher_rewards','rewarded','unrewarded',metric=metric,target=target)
    add('composition','high','low','focal',target='context_dependent',primary=False)
    return rows


def historical():
    e21.verify(REPO/'runs/E21-study-mechanisms-r1')
    count=0
    for name in ('docs/reports/A32-functional-design-lock.json','docs/experiments/A32-functional-results.sources.json',
                 'docs/experiments/E21-study-mechanism-results.sources.json'):
        for path,digest in config.load_config(REPO/name)['sources'].items():
            assert config.sha256(REPO/path)==digest,path; count+=1
    return count


def prepare(root):
    if root.exists(): raise ValueError('Use a new E22 run identity')
    historical(); jobs=[build_jobs(rep) for rep in range(REPLICATES)]
    for group in jobs:
        for job in group:
            r=job['resolved']; c=config.template(); c.update(seed=job['seed'],replicates=1,conditions=[r])
            config.preflight(config.resolve_config(c))
    root.mkdir(parents=True)
    config.save_json(root/'cases.json',CASES); config.save_json(root/'comparisons.json',comparisons())
    for rep,group in enumerate(jobs): config.save_json(root/f'rep{rep:04d}.json',group)
    sources=sorted((REPO/'src/classroom_swarm').glob('*.py'))+[Path(__file__),PLAN,
        REPO/'scripts/report_e22_a32_study_trends.py',REPO/'tests/test_e22_a32_study_trends.py',
        REPO/'scripts/e19_teacher_studies.py',REPO/'scripts/e21_study_mechanisms.py',REPO/'docs/23-v4-effort-learning.md']
    config.save_json(root/'design-lock.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
        sources={str(p.relative_to(REPO)).replace('\\','/'):config.sha256(p) for p in sources},
        declarations={p.name:config.sha256(p) for p in sorted(root.glob('*.json'))},
        classrooms=sum(map(len,jobs)),replicates=REPLICATES,seed=SEED,bootstrap_resamples=BOOTSTRAPS,
        bootstrap_seed=BOOTSTRAP_SEED,primary_family_size=sum(s['primary'] for s in comparisons()),
        historical_entries_verified=historical(),status='locked before all outcomes',
        identities=['Answer receipt/payments/exams add no direct knowledge.',
         'Zero topic/form transfer blocks direct cross-topic/form effects.',
         'Protected instruction is a scheduled opportunity, not proof of learning.',
         'Shared-practice opportunity frequency is scheduled.',
         'Missing exam scores contribute zero to eligible-cohort scores.'],
        interpretation='Study-informed known-direction probes. Default primary; all sensitivities retained; no field calibration or outcome-driven adjustment.'))
    print(f'Frozen {sum(map(len,jobs))} classrooms across {REPLICATES} paired schools/cohorts.',flush=True)


def verify(root):
    lock=config.load_config(root/'design-lock.json')
    for name,digest in lock['sources'].items(): assert config.sha256(REPO/name)==digest,name
    for name,digest in lock['declarations'].items(): assert config.sha256(root/name)==digest,name
    historical(); return lock


def read_raw(folder):
    complete=config.load_config(folder/'complete.json')
    for name,digest in complete['hashes'].items(): assert config.sha256(folder/name)==digest,name
    log=V4Log(config.load_config(folder/'manifest.json'))
    log.tables={name[:-8]:pq.read_table(folder/name).to_pylist() for name in complete['hashes'] if name.endswith('.parquet')}
    return log,len(complete['hashes'])


def metrics(log,ids):
    t=log.tables; h=log.manifest['params']['H']; ids=set(ids); n=len(ids)
    final=[r for r in t['students'] if r['homework']==h and r['student'] in ids]
    initial={r['student']:r['K0'] for r in t['traits']}
    result=dict(students=n,knowledge=100*float(np.mean([r['K'] for r in final])),
        knowledge_gain=100*float(np.mean([r['K']-initial[r['student']] for r in final])),
        homework=100*float(np.mean([r['grade'] for r in final])),
        cost=sum(r['cost'] for r in t['student_costs'] if r['student'] in ids)/(n*h),
        ai_use=sum(r['student'] in ids for r in t['ai_uses'])/(n*h),
        peer_sessions=sum(r['requester'] in ids for r in t['tutoring_content'])/(n*h),
        contract_sessions=sum(r['recipient'] in ids for r in t['helper_sessions'])/(n*h),
        instruction_ticks=sum(r['cost'] for r in t['teacher_actions'] if r['action']=='instruction')/h,
        guidance_count=sum(r['action']=='guidance' for r in t['teacher_actions'])/h,
        coaching_count=sum(r['action']=='coaching' for r in t['teacher_actions'])/h,
        followup_count=sum(r['action']=='followup' for r in t['teacher_actions'])/h,
        teacher_spent=sum(r['spent'] for r in t['teacher_resources'])/h,
        teacher_gain=100*sum(r.get('teacher_gain',0.) for r in t['learning_components'] if r['student'] in ids)/n,
        helper_gain=100*sum(r.get('helper_gain',0.) for r in t['learning_components'] if r['student'] in ids)/n,
        productive_fraction=float(np.mean([r['dose']>0 for r in t['learning_doses'] if r['student'] in ids]))
            if any(r['student'] in ids for r in t['learning_doses']) else 0.)
    for form in ('familiar','novel','unrelated','core'):
        scores=[r for r in t['assessment_scores'] if r['homework']==h and r['form']==form and r['student'] in ids]
        # Every headline design contains core. Non-present forms are unavailable, never zero.
        for suffix,key in [('potential','potential_score'),('cohort','cohort_contribution'),('participation','participated')]:
            result[form+'_'+suffix]=100*float(np.mean([r[key] for r in scores])) if scores else None
        observed=[r['score'] for r in scores if r['score'] is not None]
        result[form+'_participants']=100*float(np.mean(observed)) if observed else None
    return result


def worker(root_string,rep):
    root=Path(root_string); rows=[]; inventory=[]; new=reused=0
    for job in config.load_config(root/f'rep{rep:04d}.json'):
        folder=root/'raw'/f'rep{rep:04d}'/job['condition']; r=job['resolved']; p=TutoringParams(**r['params'])
        if (folder/'complete.json').exists(): reused+=1
        else:
            if folder.exists():
                target=folder.with_name(folder.name+'-partial-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
                assert folder.resolve().is_relative_to(root.resolve()) and target.resolve().is_relative_to(root.resolve())
                folder.rename(target)
            graph=config.make_graph(r['network'],p.N,job['seed'],rep)
            log=simulate_effort(p,graph,PublicAIDraws(job['seed'],rep,p.N,p.items,p.exam_items),job['condition'],
                r['initial'],r['teacher'],r['mechanisms'],r['extensions'])
            log.manifest.update(network=r['network'],declared_job=job)
            validate_effort_log(log,p); folder.mkdir(parents=True)
            config.save_json(folder/'manifest.json',log.manifest)
            for name,values in log.tables.items(): pq.write_table(pa.Table.from_pylist(values),folder/f'{name}.parquet',compression='zstd')
            config.save_json(folder/'complete.json',dict(hashes={f.name:config.sha256(f) for f in sorted(folder.iterdir())})); new+=1
        log,hashes=read_raw(folder); assert log.manifest['declared_job']==job
        assert log.manifest['extensions']==r['extensions']
        validate_effort_log(log,p)
        for group,ids in job['groups'].items():
            if ids: rows.append(dict(case=job['case'],profile=job['profile'],arm=job['arm'],group=group,
                section=job['section'],replicate=rep,**metrics(log,ids)))
        inventory.append(dict(replicate=rep,condition=job['condition'],hashes=hashes,
            complete_sha256=config.sha256(folder/'complete.json')))
    return rows,inventory,new,reused


def run(root,workers):
    lock=verify(root)
    if (root/'run-complete.json').exists(): raise ValueError('Execution complete; analyze saved results')
    rows=[]; inventory=[]; new=reused=0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures={pool.submit(worker,str(root),rep):rep for rep in range(REPLICATES)}
        for future in as_completed(futures):
            r,i,n,u=future.result(); rows.extend(r); inventory.extend(i); new+=n; reused+=u
            print(f'Audited replicate {futures[future]+1}/{REPLICATES}; {len(inventory)}/{lock["classrooms"]} classrooms',flush=True)
    assert len(inventory)==lock['classrooms']
    config.save_json(root/'class-metrics.json',sorted(rows,key=lambda r:(r['case'],r['profile'],r['arm'],r['group'],r['replicate'],r['section'])))
    config.save_json(root/'raw-inventory.json',sorted(inventory,key=lambda r:(r['replicate'],r['condition'])))
    config.save_json(root/'run-complete.json',dict(classrooms=len(inventory),raw_audits='all passed',
        file_hashes_verified=sum(i['hashes'] for i in inventory),new=new,reused=reused,workers=workers,
        design_sha256=config.sha256(root/'design-lock.json'),
        hashes={p:config.sha256(root/p) for p in ('class-metrics.json','raw-inventory.json')}))
    verify(root)


def paired(values,alpha=.05):
    values=np.array(values,float); assert len(values)==REPLICATES and np.all(np.isfinite(values))
    values[np.abs(values)<1e-10]=0.
    indices=np.random.default_rng(BOOTSTRAP_SEED).integers(0,REPLICATES,(BOOTSTRAPS,REPLICATES))
    lo,hi=np.quantile(values[indices].mean(axis=1),[alpha/2,1-alpha/2])
    return dict(effect=float(values.mean()),lo95=float(lo),hi95=float(hi))


def aggregate(parts):
    n=sum(r['students'] for r in parts); result={'students':n}
    for key in metrics_keys(parts[0]):
        result[key]=sum(r[key]*r['students'] for r in parts)/n if all(r[key] is not None for r in parts) else None
    return result


def metrics_keys(row):
    return [k for k in row if k not in ('students','case','profile','arm','group','section','replicate')]


def analyze(root):
    lock=verify(root); complete=config.load_config(root/'run-complete.json')
    assert complete['design_sha256']==config.sha256(root/'design-lock.json')
    for name,digest in complete['hashes'].items(): assert config.sha256(root/name)==digest
    for item in config.load_config(root/'raw-inventory.json'):
        assert config.sha256(root/'raw'/f'rep{item["replicate"]:04d}'/item['condition']/'complete.json')==item['complete_sha256']
    collected=defaultdict(list)
    for r in config.load_config(root/'class-metrics.json'):
        collected[(r['case'],r['profile'],r['arm'],r['group'],r['replicate'])].append(r)
    by={k:aggregate(parts) for k,parts in collected.items()}; effects=[]
    for spec in comparisons():
        for profile in spec['profiles']:
            for metric in metrics_keys(next(v for k,v in by.items() if k[0]==spec['case'])):
                a=[by[(spec['case'],profile,spec['a'],spec['group'],rep)][metric] for rep in range(REPLICATES)]
                b=[by[(spec['case'],profile,spec['b'],spec['group'],rep)][metric] for rep in range(REPLICATES)]
                if any(x is None for x in a+b): continue
                delta=np.array(a)-b; primary=spec['primary'] and profile=='default' and metric==spec['metric']
                simultaneous=paired(delta,.05/lock['primary_family_size']) if primary else None
                effects.append(dict(**{k:v for k,v in spec.items() if k not in ('metric','profiles')},
                    profile=profile,metric=metric,headline_metric=spec['metric'],**paired(delta),
                    simultaneous_lo95=simultaneous['lo95'] if simultaneous else None,
                    simultaneous_hi95=simultaneous['hi95'] if simultaneous else None))
    out=root/'derived'
    if out.exists(): raise ValueError('Preserve existing analysis')
    out.mkdir(); config.save_json(out/'effects.json',effects)
    config.save_json(out/'cohort-metrics.json',[dict(case=k[0],profile=k[1],arm=k[2],group=k[3],replicate=k[4],**v) for k,v in sorted(by.items())])
    config.save_json(out/'analysis-manifest.json',dict(raw_audits='all passed',
        design_sha256=config.sha256(root/'design-lock.json'),execution_sha256=config.sha256(root/'run-complete.json'),
        hashes={p.name:config.sha256(p) for p in sorted(out.iterdir())}))
    for r in effects:
        if r['profile']=='default' and r['metric']==r['headline_metric']:
            print(f'{r["case"]}/{r["group"]}/{r["a"]}-{r["b"]}/{r["metric"]}: {r["effect"]:+.3f} [{r["lo95"]:+.3f}, {r["hi95"]:+.3f}]',flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('command',choices=['prepare','run','analyze','verify'])
    parser.add_argument('--root',type=Path,default=ROOT); parser.add_argument('--workers',type=int,default=4); a=parser.parse_args()
    if a.command=='prepare': prepare(a.root)
    elif a.command=='run': run(a.root,a.workers)
    elif a.command=='analyze': analyze(a.root)
    else: verify(a.root); print('E22 and historical source hashes passed.')


if __name__=='__main__': main()
