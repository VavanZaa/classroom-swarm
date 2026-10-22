"""E14: freeze literature-informed declarations, audit raw outputs and compare directions.

prepare --root runs/E14; execute each generated config using experiment_config;
analyze --root runs/E14. No parameter fitting or outcome-based scenario selection.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import csv
from datetime import datetime, timezone
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pyarrow.parquet as pq

from classroom_swarm.experiment_config import (
    REPO, differences, load_config, preflight, resolve_config, save_json, sha256, template,
)
from classroom_swarm.v4 import V4Log
from classroom_swarm.v4_declared import validate_declared_log

GROUPS = ('class_size', 'peer_composition', 'grouping', 'ai_and_spread')
REPLICATES = 100
BOOTSTRAPS = 5000
BOOTSTRAP_SEED = 10011499
DELTA_PP = 1.


def base(name, seed):
    config = template()
    config.update(experiment_id='E14_' + name, seed=seed, replicates=REPLICATES,
                  conditions=[], contrasts=[], network={'family': 'ER', 'd_bar': 6},
                  notes='Literature-informed directional probe. No empirical calibration or fitting. See E14 preregistration.')
    # Isolate knowledge/composition changes from default confidence/prior coupling.
    config['initial']['confidence'] = dict(kind='constant', value=.5)
    for key in config['initial']:
        if key.startswith('benefit_'):
            config['initial'][key] = dict(kind='constant', value=.5)
    config['stated_identities'] = [
        'Copying and direct answer AI give zero direct knowledge, by construction.',
        'Practice learning is nonnegative and bounded by remaining knowledge headroom, by construction.',
        'Disabling hint and answer requests blocks all social learning channels; unchanged focal students must then have identical outcomes across changed peers/networks.',
        'AI grade/exam directions are not mathematical guarantees: they depend on uptake, substitution and capability relative to students.',
    ]
    return config


def contrast(config, a, b, kind='single_parameter', reason=None):
    row = dict(condition=a, reference=b, kind=kind, identity='not_identity')
    if reason:
        row['reason'] = reason
    config['contrasts'].append(row)


def clique(groups):
    return [[i,j] for group in groups for pos,i in enumerate(group) for j in group[pos+1:]]


def declarations():
    result = {}
    size = base('class_size', 10011401)
    for contact, weight in [('friends', 0.), ('acquaintances', .1)]:
        for label, n in [('small',15), ('regular',24), ('large',45)]:
            size['conditions'].append(dict(name=f'{label}_{contact}', params=dict(N=n,distant_weight=weight)))
        contrast(size, f'small_{contact}', f'regular_{contact}')
        contrast(size, f'large_{contact}', f'regular_{contact}')
    result['class_size'] = size

    composition = base('peer_composition', 10011402)
    for channel, allow_answer, allow_hint in [('current',True,True),('hint_only',False,True)]:
        for label, level in [('low',.35),('middle',.55),('high',.75)]:
            composition['conditions'].append(dict(name=f'{label}_{channel}',
                params=dict(allow_answer=allow_answer,allow_hint=allow_hint),
                initial=dict(knowledge=dict(kind='values',values=[.35]*15+[level]*15))))
        contrast(composition, f'high_{channel}', f'low_{channel}')
        contrast(composition, f'middle_{channel}', f'low_{channel}')
    for label, level in [('low',.35),('high',.75)]:
        composition['conditions'].append(dict(name=f'{label}_no_peer',
            params=dict(allow_answer=False,allow_hint=False),
            initial=dict(knowledge=dict(kind='values',values=[.35]*15+[level]*15))))
    contrast(composition,'high_no_peer','low_no_peer')
    result['peer_composition'] = composition

    grouping = base('grouping', 10011403)
    mixed = clique([[0,1,4,5],[2,3,6,7]])
    tracked = clique([[0,1,2,3],[4,5,6,7]])
    for teaching in (True,False):
        for label, edges in [('mixed',mixed),('tracked',tracked)]:
            grouping['conditions'].append(dict(name=f'{label}_{"teaching" if teaching else "no_teaching"}',
                params=dict(N=8,distant_weight=0.,closeness_spread=0.,allow_hint=teaching,allow_answer=False),
                initial=dict(knowledge=dict(kind='values',values=[.35]*4+[.75]*4)),
                network=dict(family='CUSTOM',edges=edges)))
    contrast(grouping,'mixed_teaching','tracked_teaching')
    contrast(grouping,'mixed_no_teaching','tracked_no_teaching')
    contrast(grouping,'mixed_teaching','mixed_no_teaching')
    contrast(grouping,'tracked_teaching','tracked_no_teaching')
    permutation = np.random.default_rng(10011430).permutation(32).tolist()
    random_pairs = [sorted(permutation[i:i+2]) for i in range(0,32,2)]
    cross_pairs = [[i,i+16] for i in range(16)]
    for label, edges in [('random_pairs',random_pairs),('cross_pairs',cross_pairs)]:
        grouping['conditions'].append(dict(name=label,
            params=dict(N=32,distant_weight=0.,closeness_spread=0.),
            initial=dict(knowledge=dict(kind='values',values=[.35]*16+[.75]*16)),
            network=dict(family='CUSTOM',edges=edges)))
    contrast(grouping,'cross_pairs','random_pairs')
    result['grouping'] = grouping

    ai = base('ai_and_spread', 10011404)
    ai['params'].update(H=4,exam_every=1,ai_start=1)
    for label, mean in [('low',.35),('middle',.50),('high',.80)]:
        for mode in ('none','answer','tutor'):
            ai['conditions'].append(dict(name=f'{label}_{mode}',params=dict(ai_mode=mode),
                initial=dict(knowledge=dict(kind='truncated_normal',mean=mean,std=.10,low=0.,high=1.))))
        contrast(ai,f'{label}_answer',f'{label}_none')
        contrast(ai,f'{label}_tutor',f'{label}_none')
        contrast(ai,f'{label}_tutor',f'{label}_answer')
    for label, mean in [('low',.35),('middle',.50)]:
        ai['conditions'].append(dict(name=f'{label}_answer51',params=dict(ai_mode='answer',ai_accuracy=.51),
            initial=dict(knowledge=dict(kind='truncated_normal',mean=mean,std=.10,low=0.,high=1.))))
        contrast(ai,f'{label}_answer51',f'{label}_none',kind='bundled',
                 reason='AI availability and assumed per-item accuracy both differ; cannot attribute their parts separately. Whole-problem correctness in the paper is not per-item capability.')
    for label, std in [('narrow',.05),('wide',.20)]:
        ai['conditions'].append(dict(name=f'{label}_none',
            initial=dict(knowledge=dict(kind='truncated_normal',mean=.50,std=std,low=0.,high=1.))))
        contrast(ai,f'{label}_none','middle_none')
    result['ai_and_spread'] = ai
    return result


# Ten literature comparisons fixed before outcomes; primary metric is always unaided final exam.
PRIMARY = [
    ('class_size','small_friends','regular_friends','positive','STAR: smaller class'),
    ('class_size','small_acquaintances','regular_acquaintances','positive','STAR: smaller class'),
    ('peer_composition','high_current','low_current','positive','Higher-knowledge peers: current model'),
    ('peer_composition','high_hint_only','low_hint_only','positive','Higher-knowledge peers: hint channel'),
    ('grouping','mixed_teaching','tracked_teaching','positive','Kimbrough et al.: mixed groups help low starters'),
    ('grouping','mixed_teaching','mixed_no_teaching','positive','Kimbrough et al.: peer teaching benefit'),
    ('grouping','cross_pairs','random_pairs','zero','Wu et al.: seating without rewards'),
    ('ai_and_spread','middle_answer','middle_none','negative','Bastani et al.: unrestricted AI harms unaided test'),
    ('ai_and_spread','middle_tutor','middle_none','zero','Bastani et al.: tutor no detectable test benefit'),
    ('ai_and_spread','middle_tutor','middle_answer','positive','Bastani et al.: guardrails reduce harm'),
]


def prepare(root):
    if root.exists():
        raise ValueError('E14 root already exists; use a separate experiment identity')
    configs = declarations()
    for config in configs.values():
        resolved = resolve_config(config)
        preflight(resolved)
    root.mkdir(parents=True)
    sources = sorted((REPO/'src/classroom_swarm').glob('*.py')) + [
        Path(__file__),REPO/'docs/experiments/E14-preregistration.md',REPO/'tests/test_e14_trends.py']
    source_hashes = {str(path.resolve().relative_to(REPO)).replace('\\','/'):sha256(path) for path in sources}
    for name, config in configs.items():
        save_json(root/f'{name}.json',config)
    save_json(root/'preregistration-lock.json',dict(
        created_utc=datetime.now(timezone.utc).isoformat(),status='fixed before treatment outcomes',
        sources=source_hashes,configs={name:sha256(root/f'{name}.json') for name in GROUPS},
        total_runs=sum(len(config['conditions'])*REPLICATES for config in configs.values()),
        replicates=REPLICATES,bootstraps=BOOTSTRAPS,bootstrap_seed=BOOTSTRAP_SEED,
        primary_comparisons=PRIMARY,delta_score_pp=DELTA_PP,
        uncertainty='replicate-level Monte Carlo uncertainty; no observed human data fitted',
        primary_intervals='Bonferroni simultaneous 95% over ten exam comparisons; pointwise 95% also shown'))
    print(f'Prepared {sum(len(c["conditions"]) for c in configs.values())} conditions, '+
          f'{sum(len(c["conditions"])*REPLICATES for c in configs.values())} runs')


def verify_design(root):
    lock = load_config(root/'preregistration-lock.json')
    for name,digest in lock['sources'].items():
        if sha256(REPO/name) != digest:
            raise ValueError(f'preregistered source changed: {name}')
    for name,digest in lock['configs'].items():
        if sha256(root/f'{name}.json') != digest:
            raise ValueError(f'preregistered config changed: {name}')
    return lock


def metrics(log, ids):
    p = log.manifest['params']
    ids = set(ids)
    final = [r for r in log.tables['students'] if r['homework']==p['H'] and r['student'] in ids]
    episodes = [r for r in log.tables['students'] if r['student'] in ids]
    initial = [r for r in log.tables['traits'] if r['student'] in ids]
    exam = [r for r in log.tables['exams'] if r['homework']==p['H'] and r['student'] in ids]
    requests = [r for r in log.tables['requests'] if r['requester'] in ids]
    hints = [r for r in requests if r['mode']=='hint' and r['success']]
    k0 = np.array([r['K0'] for r in initial])
    k = np.array([r['K'] for r in final])
    return dict(initial_knowledge=float(k0.mean()),final_knowledge=float(k.mean()),
                knowledge_gain=float(k.mean()-k0.mean()),exam=float(np.mean([r['score'] for r in exam])),
                homework=float(np.mean([r['grade'] for r in final])),
                initial_sd=float(k0.std()),final_sd=float(k.std()),
                copied=float(np.mean([r['copied'] for r in final])),
                attempts_per_episode=float(np.mean([r['attempt'] for r in episodes])),
                hint_deliveries_per_episode=len(hints)/(len(ids)*p['H']),
                request_success=sum(r['success'] for r in requests)/len(requests) if requests else 0.,
                ai_uses_per_episode=sum(r['student'] in ids for r in log.tables['ai_uses'])/(len(ids)*p['H']))


def interval(values, rng, alpha=.05):
    values = np.asarray(values,float)
    sample_means = values[rng.integers(0,len(values),size=(BOOTSTRAPS,len(values)))].mean(axis=1)
    return float(values.mean()),float(np.quantile(sample_means,alpha/2)),float(np.quantile(sample_means,1-alpha/2))


def write_csv(path, rows):
    with path.open('w',encoding='utf-8',newline='') as handle:
        writer=csv.DictWriter(handle,fieldnames=list(rows[0]))
        writer.writeheader();writer.writerows(rows)


def analyze(root):
    design = verify_design(root)
    rows,raw_inventory = [],[]
    for group in GROUPS:
        folder=root/group
        complete=load_config(folder/'complete.json')
        for name,digest in complete['hashes'].items():
            if sha256(folder/name)!=digest: raise ValueError(f'output hash mismatch: {folder/name}')
        config=resolve_config(load_config(root/f'{group}.json'))
        if load_config(folder/'lock.json')['conditions']!=config['conditions']:
            raise ValueError('run declarations do not match research design')
        for rep in range(REPLICATES):
            for condition in config['conditions']:
                path=folder/'raw'/f'rep{rep:04d}'/condition['name']
                hashes=load_config(path/'complete.json')['hashes']
                for name,digest in hashes.items():
                    if sha256(path/name)!=digest: raise ValueError(f'raw hash mismatch: {path/name}')
                manifest=load_config(path/'manifest.json')
                log=V4Log(manifest)
                for name in hashes:
                    if name.endswith('.parquet'):
                        log.tables[name[:-8]]=pq.read_table(path/name).to_pylist()
                validate_declared_log(log)
                n=manifest['params']['N']
                focal=list(range(15 if group=='peer_composition' else
                                 (4 if n==8 else 16) if group=='grouping' else n))
                row=dict(group=group,condition=condition['name'],replicate=rep,N=n,H=manifest['params']['H'])
                row.update({f'all_{key}':value for key,value in metrics(log,range(n)).items()})
                row.update({f'focal_{key}':value for key,value in metrics(log,focal).items()})
                rows.append(row)
                raw_inventory.append(dict(group=group,condition=condition['name'],replicate=rep,
                                          complete_sha256=sha256(path/'complete.json')))
        print(f'Audited {group}',flush=True)
    if len(rows)!=design['total_runs']: raise ValueError('unexpected run count')
    output=root/'derived';output.mkdir(exist_ok=False)
    write_csv(output/'run_metrics.csv',rows)
    write_csv(output/'raw_inventory.csv',raw_inventory)
    # Exact invariance controls: changing only peers/network cannot leak into disabled channels.
    for group,a,b in [('peer_composition','high_no_peer','low_no_peer'),
                      ('grouping','mixed_no_teaching','tracked_no_teaching')]:
        by={(r['condition'],r['replicate']):r for r in rows if r['group']==group}
        for rep in range(REPLICATES):
            for metric in ('focal_final_knowledge','focal_exam','focal_homework'):
                if by[a,rep][metric]!=by[b,rep][metric]:
                    raise ValueError(f'social-channel null failed: {group} {metric}')
    rng=np.random.default_rng(BOOTSTRAP_SEED)
    summaries=[]
    keys=[key for key in rows[0] if key.startswith(('focal_','all_'))]
    by_condition={}
    for group in GROUPS:
        for condition in resolve_config(load_config(root/f'{group}.json'))['conditions']:
            selected=sorted([r for r in rows if r['group']==group and r['condition']==condition['name']],
                            key=lambda r:r['replicate'])
            by_condition[group,condition['name']]=selected
            for key in keys:
                mean,lo,hi=interval([r[key] for r in selected],rng)
                summaries.append(dict(group=group,condition=condition['name'],metric=key,mean=mean,lo95=lo,hi95=hi))
    effects=[]
    for group in GROUPS:
        config=resolve_config(load_config(root/f'{group}.json'))
        for contrast in config['contrasts']:
            a,b=contrast['condition'],contrast['reference']
            primary=next((p for p in PRIMARY if p[:3]==(group,a,b)),None)
            for metric in keys:
                diffs=np.array([x[metric]-y[metric] for x,y in zip(by_condition[group,a],by_condition[group,b])])*100
                mean,lo,hi=interval(diffs,rng)
                adjusted_lo,adjusted_hi=(interval(diffs,rng,.05/len(PRIMARY))[1:] if primary and metric=='focal_exam' else (lo,hi))
                unit = 'per 100 student episodes' if metric.endswith(('attempts_per_episode','hint_deliveries_per_episode','ai_uses_per_episode')) else 'percentage points of normalized scale'
                effects.append(dict(group=group,condition=a,reference=b,metric=metric,delta=mean,
                    lo95=lo,hi95=hi,unit=unit,primary=bool(primary and metric=='focal_exam'),
                    simultaneous_lo=adjusted_lo,simultaneous_hi=adjusted_hi))
    write_csv(output/'condition_estimates.csv',summaries)
    write_csv(output/'effects.csv',effects)
    verdicts=[]
    for group,a,b,expected,label in PRIMARY:
        row=next(r for r in effects if r['group']==group and r['condition']==a and r['reference']==b and r['metric']=='focal_exam')
        lo,hi=row['simultaneous_lo'],row['simultaneous_hi']
        if expected=='zero':
            verdict='within declared equivalence band' if lo>=-DELTA_PP and hi<=DELTA_PP else 'not established as equivalent'
        elif expected=='positive':
            verdict='same direction' if lo>0 else 'opposite direction' if hi<0 else 'inconclusive'
        else:
            verdict='same direction' if hi<0 else 'opposite direction' if lo>0 else 'inconclusive'
        verdicts.append(dict(label=label,expected=expected,verdict=verdict,**row))
    write_csv(output/'literature_comparison.csv',verdicts)
    self_plot(output,by_condition,verdicts)
    save_json(output/'analysis_manifest.json',dict(total_runs=len(rows),exact_nulls_passed=True,
        source_lock_sha256=sha256(root/'preregistration-lock.json'),
        hashes={path.name:sha256(path) for path in sorted(output.iterdir())},
        findings='Directional probes of an uncalibrated numerical model; no human effect-size replication claimed.'))
    for row in verdicts:
        print(f'{row["label"]}: {row["delta"]:+.3f} pp [{row["simultaneous_lo"]:+.3f}, {row["simultaneous_hi"]:+.3f}] {row["verdict"]}')


def self_plot(output,by_condition,verdicts):
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,axs=plt.subplots(2,2,figsize=(13,9),layout='constrained')
    ax=axs[0,0]
    for suffix,color in [('friends','#236a9f'),('acquaintances','#d87a21')]:
        rr=[by_condition['class_size',f'{name}_{suffix}'] for name in ('small','regular','large')]
        y=[np.mean([r['all_exam'] for r in rows])*100 for rows in rr]
        ax.plot([15,24,45],y,'o-',label=suffix,color=color)
    ax.set(xlabel='Students per class',ylabel='Final unaided exam (%)',title='Class size: peer channels only');ax.legend()
    ax=axs[0,1]
    for suffix,color in [('current','#236a9f'),('hint_only','#238b63')]:
        rr=[by_condition['peer_composition',f'{name}_{suffix}'] for name in ('low','middle','high')]
        y=[np.mean([r['focal_exam'] for r in rows])*100 for rows in rr]
        ax.plot([.35,.55,.75],y,'o-',label=suffix,color=color)
    ax.set(xlabel='Other students initial knowledge',ylabel='Fixed low starters final exam (%)',title='Peers improve: do focal students learn?');ax.legend()
    ax=axs[1,0]
    chosen=[v for v in verdicts if v['group']=='grouping']
    labels=['Mixed vs tracked','Peer teaching vs solo','Cross vs random pairs']
    for i,(label,row) in enumerate(zip(labels,chosen)):
        ax.plot([row['simultaneous_lo'],row['simultaneous_hi']],[i,i],lw=3,color='#236a9f')
        ax.plot(row['delta'],i,'o',color='#236a9f')
    ax.axvline(0,color='gray',lw=1);ax.set(yticks=range(3),yticklabels=labels,xlabel='Low starters exam difference (pp)',title='Grouping: simultaneous 95% intervals')
    ax=axs[1,1]
    for mode,color in [('none','#555555'),('answer','#cb5246'),('tutor','#238b63')]:
        rr=[by_condition['ai_and_spread',f'{name}_{mode}'] for name in ('low','middle','high')]
        y=[np.mean([r['all_knowledge_gain'] for r in rows])*100 for rows in rr]
        ax.plot([.35,.5,.8],y,'o-',label=mode,color=color)
    ax.set(xlabel='Underlying initial knowledge mean',ylabel='Knowledge gained over four episodes (pp)',title='AI mode across starting populations');ax.legend()
    fig.suptitle('E14: literature-informed tests, not calibrated human predictions',fontsize=15)
    fig.savefig(output/'classroom_trends.png',dpi=180)
    plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','analyze'])
    parser.add_argument('--root',type=Path,default=REPO/'runs/E14')
    args=parser.parse_args()
    (prepare if args.command=='prepare' else analyze)(args.root)


if __name__=='__main__':
    main()
