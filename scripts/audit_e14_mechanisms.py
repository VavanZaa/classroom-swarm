"""Read-only, post-E14 mechanism audit. No fitted parameters or engine changes."""
from collections import Counter
import csv
import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

REPO=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('e14',REPO/'scripts/e14_classroom_trends.py')
e14=importlib.util.module_from_spec(spec)
spec.loader.exec_module(e14)


def write(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def mean(rows,key):
    return float(np.mean([r[key] for r in rows])) if rows else None


def main():
    root=REPO/'runs/E14'
    out=REPO/'runs/E14-audit'
    if out.exists(): raise ValueError('audit root exists; preserve prior output')
    e14.verify_design(root)
    out.mkdir()
    rows=[]
    for group in ('peer_composition','grouping'):
        config=e14.resolve_config(e14.load_config(root/f'{group}.json'))
        for rep in range(100):
            for condition in config['conditions']:
                p=condition['params'];n=p['N'];h=p['H']
                focal=set(range(15 if group=='peer_composition' else 4 if n==8 else 16))
                path=root/group/'raw'/f'rep{rep:04d}'/condition['name']
                hashes=e14.load_config(path/'complete.json')['hashes']
                tables={}
                for table in ('students','requests','hint_receipts','packets','events','traits'):
                    file=path/f'{table}.parquet'
                    assert e14.sha256(file)==hashes[file.name]
                    tables[table]=pq.read_table(file).to_pylist()
                students=[r for r in tables['students'] if r['student'] in focal]
                receipts=[r for r in tables['hint_receipts'] if r['student'] in focal and r['source']=='peer']
                requests=[r for r in tables['requests'] if r['requester'] in focal]
                attempts=[r for r in tables['packets'] if r['student'] in focal and r['origin']=='student']
                guided=[r for r in attempts if r['hint_source']=='peer']
                assert len(guided)<=len(receipts)
                row=dict(group=group,condition=condition['name'],replicate=rep,
                    attempts_per_episode=mean(students,'attempt'),
                    final_copied=mean([r for r in students if r['homework']==h],'copied'),
                    hint_deliveries_per_episode=len(receipts)/(len(focal)*h),
                    guided_attempts_per_episode=len(guided)/(len(focal)*h),
                    hints_not_consumed_fraction=(len(receipts)-len(guided))/len(receipts) if receipts else None,
                    mean_delivered_hint_strength=mean(receipts,'strength'),
                    max_alpha=max(r['alpha'] for r in tables['traits']))
                for mode in ('hint','answer'):
                    req=[r for r in requests if r['mode']==mode]
                    success=[r for r in req if r['success']]
                    reasons=Counter(r['reason'] for r in req if not r['success'])
                    row.update({f'{mode}_requests_per_episode':len(req)/(len(focal)*h),
                                f'{mode}_success_fraction':len(success)/len(req) if req else None,
                                f'{mode}_provider_K_on_delivery':mean(success,'research_provider_K'),
                                f'{mode}_knowledge_gap_on_delivery':float(np.mean([r['research_provider_K']-r['research_requester_K'] for r in success])) if success else None})
                    for reason in ('busy','declined','deadline','no_packet'):
                        row[f'{mode}_fail_{reason}_per_episode']=reasons[reason]/(len(focal)*h)
                rows.append(row)
        print(f'Audited {group}',flush=True)
    write(out/'replicate_mechanisms.csv',rows)
    keys=[k for k in rows[0] if k not in ('group','condition','replicate')]
    summaries=[]
    for group,condition in dict.fromkeys((r['group'],r['condition']) for r in rows):
        selected=[r for r in rows if r['group']==group and r['condition']==condition]
        summaries.append(dict(group=group,condition=condition,
            **{key:float(np.mean([r[key] for r in selected if r[key] is not None]))
               if any(r[key] is not None for r in selected) else None for key in keys}))
    write(out/'condition_mechanisms.csv',summaries)
    # An analytical controlled path comparison, not a classroom treatment estimate.
    k=.35;alpha=.0584;a=alpha/3
    two_solo=(1-k)*(1-(1-a)**2)
    strengths={str(provider):.15+.35*provider for provider in (0.,.35,.75,1.)}
    economics=dict(receiver_K=k,alpha=alpha,elapsed_ticks=6,two_solo_gain=two_solo,
        guided_paths={provider:dict(strength=s,gain=(1-k)*a*(1+s)) for provider,s in strengths.items()},
        break_even_hint_strength=1-a,
        warning='Fixed actions, nominal alpha and equal elapsed time: an identity of the current rule, not an empirical finding. No helper gain or subsequent policy changes included.')
    e14.save_json(out/'learning_path_identity.json',economics)
    e14.save_json(out/'audit_manifest.json',dict(
        status='post-outcome descriptive mechanism audit; no new parameter intervention',
        runs_read=len(rows),E14_lock_sha256=e14.sha256(root/'preregistration-lock.json'),
        audit_script_sha256=e14.sha256(Path(__file__)),
        hashes={p.name:e14.sha256(p) for p in sorted(out.iterdir())}))
    print(json.dumps(economics,indent=2))


if __name__=='__main__':main()
