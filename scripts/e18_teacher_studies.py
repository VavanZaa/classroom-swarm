"""E18: frozen setup search, observed-baseline school assignment and fresh-seed checks."""
from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import csv
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO/'src'))
sys.path.insert(0,str(REPO/'scripts'))
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq
from classroom_swarm.teacher_config import (template, resolve_config, make_graph, sha256,
                                            save_json, load_config)
from classroom_swarm.tutoring_settings import TutoringParams
from classroom_swarm.v4_public_ai import PublicAIDraws
from classroom_swarm.v4_teacher import simulate_teacher, validate_teacher_log
from classroom_swarm.v4 import V4Log
from a30_teacher_diagnostic import check_historical_sources

SEEDS = {'development':10061801,'confirmation':10061802}
REPLICATES = {'development':12,'confirmation':60}
BASELINE_STREAMS = {'assessment':131,'assignment':132,'permutation':133}


def profiles():
    def profile(name,parent='reference',**patch):
        return dict(name=name,parent=parent,**patch)
    star = [profile('reference'),profile('guidance_02',teacher={'guidance_strength':.2}),
        profile('guidance_03',teacher={'guidance_strength':.3}),
        profile('confidence_off',teacher={'guidance_confidence_rate':0.}),
        profile('guidance_only',teacher={'actions':['guidance']}),
        profile('explanation_only',teacher={'actions':['explanation']}),
        profile('short_explanations',parent='explanation_only',teacher={'explanation_ticks':2}),
        profile('budget_12',teacher={'time_budget':12})]
    kenya = [profile('reference'),profile('readiness_03',params={'readiness_band':.3}),
        profile('readiness_08',params={'readiness_band':.8}),
        profile('target_offset_01',teacher={'difficulty_offset':.1}),
        profile('learning_2',teacher={'learning_multiplier':2.}),
        profile('narrow_population',population={'span':.4}),
        profile('homework_signal',teacher={'observation_sources':['exam','homework']})]
    return {'star':star,'kenya':kenya}


def resolve_profile(study,name):
    by = {p['name']:p for p in profiles()[study]}
    selected = by[name]
    value = dict(name=name,parent=selected['parent'],params={},teacher={},population={})
    if name != 'reference':
        parent = resolve_profile(study,selected['parent'])
        for key in ('params','teacher','population'):
            value[key].update(parent[key])
            value[key].update(selected.get(key,{}))
    return value


def balanced_population(n,mean=.45,std=.1):
    q = (np.arange(n)+.5)/n
    return mean + std*(q-q.mean())/q.std()


def cohort(study,seed,replicate,n=None,span=.6):
    n = n if study=='star' else 84
    k = balanced_population(n) if study=='star' else np.linspace(.5-span/2,.5+span/2,n)
    rng = np.random.default_rng(np.random.SeedSequence([seed,replicate,133,n]))
    k = rng.permutation(k)
    u = np.random.default_rng(np.random.SeedSequence([seed,replicate,131,n])).random((100,n))
    scores = (u < k).mean(axis=0)
    ranks = sorted(range(n),key=lambda i:(scores[i],i))
    low,high = ranks[:n//2],ranks[n//2:]
    if study=='kenya':
        rng = np.random.default_rng(np.random.SeedSequence([seed,replicate,132,n]))
        order = rng.permutation(n).tolist()
        mixed = [sorted(order[:42]),sorted(order[42:])]
        tracked = [sorted(low),sorted(high)]
    else:
        mixed,tracked = [list(range(n))],[]
    return dict(student_ids=list(range(n)),knowledge=k.tolist(),observed_baseline=scores.tolist(),
                low=low,high=high,mixed=mixed,tracked=tracked)


def base_config(study):
    c = template()
    c.update(experiment_id='E18_teacher_studies',replicates=1)
    c['params'].update(H=12,ticks=12,items=12,exam_items=100,exam_every=1,feedback_delay=0,
        allow_answer=False,allow_hint=False,ai_mode='none',distant_weight=0.,closeness_spread=0.)
    for name in ('confidence','control','benefit_attempt','benefit_hint','benefit_answer','benefit_ai_answer','benefit_ai_tutor'):
        c['initial'][name] = {'kind':'constant','value':.5}
    c['initial']['learning_efficiency'] = {'kind':'constant','value':.0584}
    c['initial']['effort_aversion'] = {'kind':'constant','value':.15}
    c['network'].update(family='CUSTOM',edges=[],block_sizes=None)
    c['teacher'].update(enabled=True,time_budget=8 if study=='star' else 3,admin_ticks=0,
        grading_ticks_per_student=0,actions=['instruction','guidance'] if study=='star' else ['instruction'],
        allocation='round_robin',curriculum='adaptive',observation_sources=['exam'])
    return c


def specifications(stage,selection=None):
    result = []
    for study in ('star','kenya'):
        names = [p['name'] for p in profiles()[study]] if stage=='development' else list(dict.fromkeys(['reference',selection[study]['profile']]))
        for name in names:
            result.append(dict(study=study,profile=name,control='main',label=name))
        if stage=='confirmation':
            if study=='star':
                result += [dict(study=study,profile='reference',control='disabled',label='no_teacher'),
                           dict(study=study,profile='reference',control='scaled',label='scaled_guidance')]
            else:
                name = selection[study]['profile']
                result += [dict(study=study,profile=name,control='fixed',label='fixed_curriculum'),
                           dict(study=study,profile=name,control='peers',label='with_peers')]
    return result


def jobs(stage,replicate,selection=None):
    seed = SEEDS[stage]
    for spec in specifications(stage,selection):
        study,profile,control = spec['study'],spec['profile'],spec['control']
        patch = resolve_profile(study,profile)
        sizes = [15,24] if study=='star' else [42]
        for n in sizes:
            pop = cohort(study,seed,replicate,n=n,span=patch['population'].get('span',.6))
            arms = [('small' if n==15 else 'regular',pop['mixed'])] if study=='star' else [('mixed',pop['mixed']),('tracked',pop['tracked'])]
            for arm,sections in arms:
                for section,ids in enumerate(sections):
                    c = base_config(study)
                    c['seed'] = seed + (1000 if study=='star' else 2000) + section
                    c['params'].update(N=n,**patch['params'])
                    c['teacher'].update(patch['teacher'])
                    c['teacher']['identity'] = f'{study}-section-{section}'
                    c['teacher']['observation_prior'] = float(np.mean([pop['observed_baseline'][i] for i in ids]))
                    c['initial']['knowledge'] = {'kind':'values','values':[pop['knowledge'][i] for i in ids]}
                    if control=='disabled':
                        c['teacher']['enabled'] = False
                    elif control=='scaled':
                        c['teacher'].update(actions=['guidance'],time_budget=5 if n==15 else 8)
                    elif control=='fixed':
                        c['teacher'].update(curriculum='fixed',fixed_difficulty=.5)
                    elif control=='peers':
                        c['params']['allow_hint'] = True
                        c['network'].update(family='ER',edges=None,d_bar=6)
                    name = f'{study}_{spec["label"]}_{arm}_s{section}'
                    c['conditions'] = [dict(name=name,params={},initial={},network={},teacher={})]
                    c['notes'] = 'E18 class declaration; global membership and baseline scores are separate observed cohort data.'
                    resolved = resolve_config(c)['conditions'][0]
                    yield dict(**spec,arm=arm,section=section,name=name,seed=c['seed'],replicate=replicate,
                               config=c,resolved=resolved,global_ids=ids,cohort=pop)


def source_hashes():
    sources = sorted((REPO/'src/classroom_swarm').glob('*.py')) + [Path(__file__),
        REPO/'tests/test_e18_teacher_studies.py',REPO/'docs/experiments/E18-teacher-study-plan.md']
    return {str(p.relative_to(REPO)).replace('\\','/'):sha256(p) for p in sources}


def historical():
    count = check_historical_sources()
    lock = load_config(REPO/'runs/A30-teacher-functional-r1/diagnostic-lock.json')
    for name,digest in lock['sources'].items():
        if sha256(REPO/name)!=digest:
            raise ValueError('Historical A30 source changed: '+name)
        count += 1
    return count


def prepare(root):
    if root.exists():
        raise ValueError('Use a new E18 output directory')
    # Check actual class declarations before locking, without running outcomes.
    for stage in ('development','confirmation'):
        for rep in range(REPLICATES[stage]):
            for study in ('star','kenya'):
                for p in profiles()[study]:
                    for n in ([15,24] if study=='star' else [42]):
                        cohort(study,SEEDS[stage],rep,n=n,span=resolve_profile(study,p['name'])['population'].get('span',.6))
    for job in jobs('development',0):
        r = job['resolved']
        make_graph(r['network'],r['params']['N'],job['seed'],0)
    root.mkdir(parents=True,exist_ok=False)
    for stage in SEEDS:
        populations = {}
        for rep in range(REPLICATES[stage]):
            populations[str(rep)] = {'star15':cohort('star',SEEDS[stage],rep,n=15),
                'star24':cohort('star',SEEDS[stage],rep,n=24),
                'kenya06':cohort('kenya',SEEDS[stage],rep,span=.6),
                'kenya04':cohort('kenya',SEEDS[stage],rep,span=.4)}
        save_json(root/f'{stage}-cohorts.json',populations)
    save_json(root/'design-lock.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
        sources=source_hashes(),seeds=SEEDS,replicates=REPLICATES,profiles=profiles(),
        cohorts={stage:sha256(root/f'{stage}-cohorts.json') for stage in SEEDS},
        historical_entries_verified=historical(),bootstrap_seed=10061899,bootstrap_resamples=3000,
        primary_family_size=3,selection_rule='positive knowledge and exams in all required groups; fewest changes, highest minimum exam, name; otherwise best minimum exam marked unmet',
        study_sources=['https://www.nber.org/papers/w6051','https://www.povertyactionlab.org/sites/default/files/research-paper/39%20Peer%20Effects%2C%20Teacher%20Incentives%2C%20and%20the%20Impact%20of%20Tracking%20Project.pdf'],
        identities=['Teacher content gains are nonnegative by rule.','Guidance encouragement directly changes independent-practice utility.','Finite resource quotas bound appointments; net learning need not be positive.'],
        interpretation='Study-informed directional setup fitting; fresh seeds test simulation repeatability, not independent human validation.'))
    print('Prepared E18; development and fresh-seed pools locked.',flush=True)


def verify(root):
    lock = load_config(root/'design-lock.json')
    for name,digest in lock['sources'].items():
        if sha256(REPO/name)!=digest:
            raise ValueError('E18 source changed: '+name)
    for stage,digest in lock['cohorts'].items():
        if sha256(root/f'{stage}-cohorts.json')!=digest:
            raise ValueError('Changed predeclared cohort pool')
    historical()
    return lock


def selected(root):
    selection = load_config(root/'selection.json')
    for name,digest in selection['gate_hashes'].items():
        if sha256(root/name)!=digest:
            raise ValueError('Development selection gate changed: '+name)
    return selection['studies']


def load_raw(folder):
    complete = load_config(folder/'complete.json')
    for name,digest in complete['hashes'].items():
        if sha256(folder/name)!=digest:
            raise ValueError('Raw hash differs: '+str(folder/name))
    log = V4Log(load_config(folder/'manifest.json'))
    for name in complete['hashes']:
        if name.endswith('.parquet'):
            log.tables[name[:-8]] = pq.read_table(folder/name).to_pylist()
    validate_teacher_log(log)
    return log


def check_identity(log,job):
    r = job['resolved']
    assert log.manifest['params'] == asdict(TutoringParams(**r['params']))
    assert log.manifest['initial'] == r['initial']
    if r['teacher']['enabled']:
        assert log.manifest['teacher'] == r['teacher']
    assert (log.manifest['seed'],log.manifest['replicate'],log.manifest['condition']) == (job['seed'],job['replicate'],job['name'])
    assert log.manifest['cohort_global_ids'] == job['global_ids']
    assert log.manifest['cohort_baseline_scores'] == [job['cohort']['observed_baseline'][i] for i in job['global_ids']]


def run(root,stage):
    lock = verify(root)
    selection = selected(root) if stage=='confirmation' else None
    out = root/stage
    if (out/'complete.json').exists():
        raise ValueError('Stage complete; analyze instead')
    out.mkdir(exist_ok=True)
    save_json(out/'stage-lock.json',dict(design_lock_sha256=sha256(root/'design-lock.json'),
        selection_sha256=sha256(root/'selection.json') if selection else None,
        stage=stage,seed=SEEDS[stage],replicates=REPLICATES[stage],specifications=specifications(stage,selection)))
    inventory,used,new = [],0,0
    for rep in range(REPLICATES[stage]):
        for job in jobs(stage,rep,selection):
            folder = out/'raw'/f'rep{rep:04d}'/job['name']
            if (folder/'complete.json').exists():
                log = load_raw(folder)
                check_identity(log,job)
                used += 1
            else:
                if folder.exists():
                    target = folder.with_name(folder.name+'-partial-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f'))
                    if not folder.resolve().is_relative_to(out.resolve()) or not target.resolve().is_relative_to(out.resolve()):
                        raise ValueError('Partial preservation path escapes stage')
                    folder.rename(target)
                r = job['resolved']
                p = TutoringParams(**r['params'])
                graph = make_graph(r['network'],p.N,job['seed'],rep)
                log = simulate_teacher(p,graph,PublicAIDraws(job['seed'],rep,p.N,p.items,p.exam_items),
                    condition=job['name'],initial=r['initial'],teacher=r['teacher'])
                log.manifest.update(cohort_global_ids=job['global_ids'],
                    cohort_baseline_scores=[job['cohort']['observed_baseline'][i] for i in job['global_ids']],
                    study=job['study'],profile=job['profile'],control=job['control'],assignment=job['arm'],
                    section=job['section'],network=r['network'])
                validate_teacher_log(log)
                folder.mkdir(parents=True)
                save_json(folder/'declared_class.json',dict(config=job['config'],resolved=r))
                save_json(folder/'manifest.json',log.manifest)
                for name,rows in log.tables.items():
                    pq.write_table(pa.Table.from_pylist(rows),folder/f'{name}.parquet',compression='zstd')
                save_json(folder/'complete.json',{'hashes':{p.name:sha256(p) for p in sorted(folder.iterdir())}})
                new += 1
            inventory.append(dict(replicate=rep,condition=job['name'],study=job['study'],profile=job['profile'],
                control=job['control'],arm=job['arm'],section=job['section'],path=str(folder.relative_to(out)),
                complete_sha256=sha256(folder/'complete.json')))
        print(f'{stage}: {rep+1}/{REPLICATES[stage]} replicates; {new} new, {used} reused classrooms',flush=True)
    save_json(out/'inventory.json',inventory)
    save_json(out/'complete.json',dict(classrooms=len(inventory),hashes={p:sha256(out/p) for p in ('stage-lock.json','inventory.json')}))
    verify(root)


def metrics(log,local_ids):
    ids = set(local_ids)
    h = log.manifest['params']['H']
    rows = [r for r in log.tables['students'] if r['homework']==h and r['student'] in ids]
    exam = [r for r in log.tables['exams'] if r['homework']==h and r['student'] in ids]
    events = [r for r in log.tables['events'] if r['student'] in ids]
    learning = [r for r in log.tables.get('teacher_learning',[]) if r['student'] in ids]
    guidance = [r for r in log.tables.get('teacher_guidance',[]) if r['student'] in ids]
    n = len(rows)
    assert n and len(exam)==n
    traits = {r['student']:r for r in log.tables['traits']}
    return dict(students=n,exam=100*float(np.mean([r['score'] for r in exam])),
        knowledge=100*float(np.mean([r['K'] for r in rows])),
        knowledge_gain=100*float(np.mean([r['K']-traits[r['student']]['K0'] for r in rows])),
        practice_count=sum(r['attempt'] for r in log.tables['students'] if r['student'] in ids)/n,
        practice_ticks=sum(r['end']-r['start'] for r in events if r['action'] in {'attempt','guided_practice','scheduled_practice'})/n,
        teacher_ticks=sum(r['end']-r['start'] for r in events if r['action'] in {'teacher_instruction','teacher_explanation','teacher_corrective_feedback','teacher_guidance'})/n,
        guidance_count=len(guidance)/n,
        teacher_gain=100*sum(r['gain'] for r in learning)/n,
        teacher_difficulty=float(np.mean([r['difficulty'] for r in learning])) if learning else 0.,
        teacher_usable=float(np.mean([r['usable_fraction'] for r in learning])) if learning else 0.)


def aggregate_class_metrics(rows):
    n = sum(r['students'] for r in rows)
    return {key:sum(r[key]*r['students'] for r in rows)/n for key in rows[0] if key!='students'} | {'students':n}


def paired(values,alpha=.05,seed=10061899):
    delta = np.asarray(values,float)
    rng = np.random.default_rng(seed)
    boot = delta[rng.integers(0,len(delta),(3000,len(delta)))].mean(axis=1)
    return dict(effect=float(delta.mean()),lo95=float(np.quantile(boot,alpha/2)),
                hi95=float(np.quantile(boot,1-alpha/2)),replicates=len(delta))


def write_csv(path,rows):
    with path.open('w',encoding='utf-8',newline='') as handle:
        writer = csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def analyze(root,stage):
    verify(root)
    selection = selected(root) if stage=='confirmation' else None
    out = root/stage
    complete = load_config(out/'complete.json')
    for name,digest in complete['hashes'].items():
        if sha256(out/name)!=digest:
            raise ValueError('Stage artifact differs')
    expected_gate = sha256(root/'selection.json') if selection else None
    assert load_config(out/'stage-lock.json')['selection_sha256'] == expected_gate
    grouped,inventory = defaultdict(list),[]
    for rep in range(REPLICATES[stage]):
        for job in jobs(stage,rep,selection):
            folder = out/'raw'/f'rep{rep:04d}'/job['name']
            log = load_raw(folder)
            check_identity(log,job)
            population = job['cohort']
            for group in ('all','low','high'):
                global_ids = set(population['student_ids'] if group=='all' else population[group])
                local_ids = [i for i,g in enumerate(job['global_ids']) if g in global_ids]
                if local_ids:
                    key = (job['study'],job['label'],job['control'],job['arm'],group,rep)
                    grouped[key].append(metrics(log,local_ids))
            inventory.append(dict(condition=job['name'],replicate=rep,complete_sha256=sha256(folder/'complete.json')))
        print(f'Audited {stage} replicate {rep+1}/{REPLICATES[stage]}',flush=True)
    assert len(inventory)==complete['classrooms']
    rows,by = [],{}
    for key,parts in sorted(grouped.items()):
        study,label,control,arm,group,rep = key
        value = aggregate_class_metrics(parts)
        row = dict(study=study,profile=label,control=control,arm=arm,group=group,replicate=rep,**value)
        rows.append(row);by[key]=value
    effects=[]
    for spec in specifications(stage,selection):
        study,label,control = spec['study'],spec['label'],spec['control']
        a,b = ('small','regular') if study=='star' else ('tracked','mixed')
        for group in ('all','low','high'):
            for metric in [key for key in next(iter(by.values())) if key!='students']:
                delta = [by[study,label,control,a,group,r][metric]-by[study,label,control,b,group,r][metric] for r in range(REPLICATES[stage])]
                primary = stage=='confirmation' and control=='main' and label==selection[study]['profile'] and metric=='exam' and (group=='all' if study=='star' else group in {'low','high'})
                result = paired(delta)
                simultaneous = paired(delta,alpha=.05/3) if primary else None
                effects.append(dict(study=study,profile=label,control=control,group=group,metric=metric,
                    condition=a,reference=b,primary=primary,**result,
                    simultaneous_lo95=simultaneous['lo95'] if simultaneous else '',
                    simultaneous_hi95=simultaneous['hi95'] if simultaneous else ''))
    derived = root/f'{stage}_derived'
    if derived.exists():
        raise ValueError('Derived stage already exists; preserve it before a new analysis')
    derived.mkdir()
    write_csv(derived/'run_metrics.csv',rows)
    write_csv(derived/'effects.csv',effects)
    save_json(derived/'effects.json',effects)
    save_json(derived/'analysis_manifest.json',dict(classrooms=len(inventory),raw_audits='all passed',
        design_lock_sha256=sha256(root/'design-lock.json'),stage_completion_sha256=sha256(out/'complete.json'),
        selection_sha256=expected_gate,historical_entries_verified=historical(),
        inventory=inventory,hashes={p.name:sha256(p) for p in sorted(derived.iterdir())},
        interpretation='Paired Monte Carlo uncertainty, not human-study sampling uncertainty.'))
    for effect in effects:
        if effect['metric']=='exam' and (effect['group']=='all' if effect['study']=='star' else effect['group'] in {'low','high'}):
            print(f"{effect['study']}/{effect['profile']}/{effect['group']}: {effect['effect']:+.3f} [{effect['lo95']:+.3f}, {effect['hi95']:+.3f}]",flush=True)


def choose(study,effects):
    groups = ['all'] if study=='star' else ['low','high']
    candidates=[]
    for p in profiles()[study]:
        relevant = [e for e in effects if e['study']==study and e['profile']==p['name'] and e['control']=='main' and e['group'] in groups and e['metric'] in {'exam','knowledge_gain'}]
        assert len(relevant)==2*len(groups)
        eligible = all(e['effect']>1e-10 for e in relevant)
        patch = resolve_profile(study,p['name'])
        complexity = sum(len(patch[k]) for k in ('params','teacher','population'))
        minimum_exam = min(e['effect'] for e in relevant if e['metric']=='exam')
        candidates.append(dict(profile=p['name'],eligible=eligible,changes_from_reference=complexity,
                               minimum_exam=minimum_exam,effects=relevant,patch=patch))
    eligible = [c for c in candidates if c['eligible']]
    best = sorted(eligible,key=lambda c:(c['changes_from_reference'],-c['minimum_exam'],c['profile']))[0] if eligible else sorted(candidates,key=lambda c:(-c['minimum_exam'],c['changes_from_reference'],c['profile']))[0]
    return dict(profile=best['profile'],development_target_met=best['eligible'],selection=best,candidates=candidates)


def select(root):
    verify(root)
    if (root/'selection.json').exists():
        raise ValueError('Selection already frozen')
    derived = root/'development_derived'
    manifest = load_config(derived/'analysis_manifest.json')
    for name,digest in manifest['hashes'].items():
        if sha256(derived/name)!=digest:
            raise ValueError('Development analysis changed')
    effects = load_config(derived/'effects.json')
    studies = {study:choose(study,effects) for study in ('star','kenya')}
    lines = ['# E18 development selection review','',
        'Written before confirmation. These choices use known human-study directions and development outcomes, so they are exploratory directional fitting.',
        'The fresh-seed confirmation pool remains unopened. Every candidate remains in the development tables.','']
    for study,result in studies.items():
        best=result['selection']
        lines += [f"## {study}: {result['profile']}",'',
            f"Development target met: {result['development_target_met']}. Changes from reference: {best['changes_from_reference']}. Minimum exam mean: {best['minimum_exam']:+.4f} model points.",
            '',f"Selected patch: `{json.dumps(best['patch'],sort_keys=True)}`",'']
        for candidate in result['candidates']:
            lines.append(f"- {candidate['profile']}: eligible={candidate['eligible']}, changes={candidate['changes_from_reference']}, minimum exam={candidate['minimum_exam']:+.4f}.")
        lines.append('')
    (root/'development-review.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    save_json(root/'selection.json',dict(selected_utc=datetime.now(timezone.utc).isoformat(),studies=studies,
        gate_hashes={name:sha256(root/name) for name in ['development-review.md','development_derived/analysis_manifest.json','development_derived/effects.json']},
        interpretation='Directional setup fitting on development only; do not reselect on confirmation.'))
    for study,result in studies.items():
        print(study+': '+result['profile']+', development target met='+str(result['development_target_met']),flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','run','analyze','select','verify'])
    parser.add_argument('--root',type=Path,default=REPO/'runs/E18-teacher-study-r1')
    parser.add_argument('--stage',choices=list(SEEDS),default='development')
    args=parser.parse_args()
    if args.command=='prepare':prepare(args.root)
    elif args.command=='run':run(args.root,args.stage)
    elif args.command=='analyze':analyze(args.root,args.stage)
    elif args.command=='select':select(args.root)
    else:
        lock=verify(args.root);print('Verified E18 and '+str(lock['historical_entries_verified'])+' historical source entries.')


if __name__=='__main__':
    main()
