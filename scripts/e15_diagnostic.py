"""Predeclared diagnostic sensitivities after E14; no new engine or empirical fit."""
import argparse
from copy import deepcopy
import csv
from datetime import datetime,timezone
import importlib.util
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

REPO=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('e14',REPO/'scripts/e14_classroom_trends.py')
e14=importlib.util.module_from_spec(spec);spec.loader.exec_module(e14)
REPS=50
GROUPS=('hint','copy')
FACTORS={
    'hint':{'reference':{},'quality_flat':{'peer_hint_knowledge_weight':0.},
            'no_generic_boost':{'peer_hint_base':0.},'faster_hint':{'peer_hint_ticks':1},
            'steeper_quality':{'peer_hint_knowledge_weight':.85},
            'larger_learning_boost':{'hint_learning_multiplier':2.}},
    'copy':{'reference':{},'no_grade_pressure':{'grade_response':0.},
            'no_public_blend':{'public_signal':0.},'no_grade_target_weight':{'grade_bias':0.}}
}


def prepare(root):
    if root.exists():raise ValueError('use a fresh diagnostic root')
    e14.verify_design(REPO/'runs/E14')
    original=e14.load_config(REPO/'runs/E14/peer_composition.json')
    configs={}
    for group in GROUPS:
        config=deepcopy(original)
        config.update(experiment_id='E15_diagnostic_'+group,replicates=REPS,conditions=[],contrasts=[],
            notes='Post-E14 exploratory diagnostics, fixed before these outcomes; no fitted values and no human replication claim. See E15-diagnostic-plan.')
        channel='hint_only' if group=='hint' else 'current'
        for factor,change in FACTORS[group].items():
            for label in ('low','high'):
                c=deepcopy(next(c for c in original['conditions'] if c['name']==f'{label}_{channel}'))
                c['name']=factor+'_'+label;c['params'].update(change);config['conditions'].append(c)
                if factor!='reference':e14.contrast(config,c['name'],'reference_'+label)
            e14.contrast(config,factor+'_high',factor+'_low')
        e14.preflight(e14.resolve_config(config));configs[group]=config
    root.mkdir(parents=True)
    for group,c in configs.items():e14.save_json(root/f'{group}.json',c)
    sources=[Path(__file__),REPO/'docs/experiments/E15-diagnostic-plan.md']
    e14.save_json(root/'diagnostic-lock.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
        purpose='exploratory parameter diagnostics motivated by E14; not validation or calibration',
        E14_lock_sha256=e14.sha256(REPO/'runs/E14/preregistration-lock.json'),
        sources={str(p.resolve().relative_to(REPO)).replace('\\','/'):e14.sha256(p) for p in sources},
        configs={g:e14.sha256(root/f'{g}.json') for g in GROUPS},total_runs=1000,replicates=REPS,
        bootstrap_samples=2000,bootstrap_seed=10011599))
    print('Prepared 20 conditions / 1000 diagnostic runs')


def ci(x,rng):
    x=np.array(x)*100
    boot=x[rng.integers(0,len(x),(2000,len(x)))].mean(axis=1)
    return float(x.mean()),float(np.quantile(boot,.025)),float(np.quantile(boot,.975))


def analyze(root):
    e14.verify_design(REPO/'runs/E14')
    lock=e14.load_config(root/'diagnostic-lock.json')
    for name,digest in lock['sources'].items():assert e14.sha256(REPO/name)==digest,name
    for name,digest in lock['configs'].items():assert e14.sha256(root/f'{name}.json')==digest,name
    rows=[];by={}
    for group in GROUPS:
        folder=root/group
        complete=e14.load_config(folder/'complete.json')
        for name,digest in complete['hashes'].items():assert e14.sha256(folder/name)==digest
        config=e14.resolve_config(e14.load_config(root/f'{group}.json'))
        assert e14.load_config(folder/'lock.json')['conditions']==config['conditions']
        for condition in config['conditions']:
            records=[]
            for rep in range(REPS):
                path=folder/'raw'/f'rep{rep:04d}'/condition['name']
                hashes=e14.load_config(path/'complete.json')['hashes']
                for name,digest in hashes.items():assert e14.sha256(path/name)==digest
                log=e14.V4Log(e14.load_config(path/'manifest.json'))
                for name in hashes:
                    if name.endswith('.parquet'):log.tables[name[:-8]]=pq.read_table(path/name).to_pylist()
                e14.validate_declared_log(log)
                values=e14.metrics(log,range(15))
                records.append(values);rows.append(dict(group=group,condition=condition['name'],replicate=rep,**values))
            by[group,condition['name']]=records
        print('Audited '+group,flush=True)
    assert len(rows)==1000
    output=root/'derived';output.mkdir(exist_ok=False)
    e14.write_csv(output/'run_metrics.csv',rows)
    rng=np.random.default_rng(10011599);effects=[]
    for group in GROUPS:
        for factor in FACTORS[group]:
            high=by[group,factor+'_high'];low=by[group,factor+'_low']
            ref_high=by[group,'reference_high'];ref_low=by[group,'reference_low']
            for metric in ('exam','knowledge_gain','homework','copied','attempts_per_episode'):
                delta=[a[metric]-b[metric] for a,b in zip(high,low)]
                interaction=[d-(a[metric]-b[metric]) for d,a,b in zip(delta,ref_high,ref_low)]
                d,lo,hi=ci(delta,rng);i,ilo,ihi=ci(interaction,rng)
                effects.append(dict(group=group,factor=factor,metric=metric,peer_effect=d,lo95=lo,hi95=hi,
                    change_in_peer_effect=i,interaction_lo95=ilo,interaction_hi95=ihi,
                    unit='per 100 student episodes' if metric=='attempts_per_episode' else 'normalized percentage points'))
    e14.write_csv(output/'diagnostic_effects.csv',effects)
    e14.save_json(output/'analysis_manifest.json',dict(total_runs=1000,raw_audits='all passed',
        lock_sha256=e14.sha256(root/'diagnostic-lock.json'),
        interpretation='Exploratory, pointwise Monte Carlo intervals without multiplicity adjustment; coefficients are probes, not estimates or defaults.',
        hashes={p.name:e14.sha256(p) for p in sorted(output.iterdir())}))
    for r in effects:
        if r['metric']=='exam':print(f"{r['group']}/{r['factor']}: peer effect {r['peer_effect']:+.3f} [{r['lo95']:+.3f},{r['hi95']:+.3f}], interaction {r['change_in_peer_effect']:+.3f}")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('prepare','analyze'));parser.add_argument('--root',type=Path,default=REPO/'runs/E15-diagnostic')
    args=parser.parse_args();(prepare if args.command=='prepare' else analyze)(args.root)


if __name__=='__main__':main()
