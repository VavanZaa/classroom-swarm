"""A23 exploratory sensitivity study, locked before its own outcomes are observed."""
from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import asdict, replace
import json
from pathlib import Path
import platform
import time

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from .e9 import REPO, digest, dump, read_log, write_csv, interval
from .graphs import generate_graph
from .rng import graph_seed
from .v3 import V3Params
from .v4 import V4Draws, summarize, validate_log
from .v4_learning import LearningParams, simulate_learning

SEED, REPLICATES = 924101, 100
LOCK_FILES = ('docs/12-v4-learning-differentiation.md', 'src/classroom_swarm/v4_learning.py',
              'src/classroom_swarm/e10.py', 'tests/test_v4_learning.py',
              'src/classroom_swarm/v4.py', 'src/classroom_swarm/e9.py',
              'src/classroom_swarm/v3.py', 'src/classroom_swarm/graphs.py', 'src/classroom_swarm/rng.py')


def conditions():
    p = LearningParams()
    return [('reference', 'SBM', replace(p, check_learning_fraction=1)),
            ('check25', 'SBM', replace(p, check_learning_fraction=.25)),
            ('check10', 'SBM', replace(p, check_learning_fraction=.1)),
            ('check0', 'SBM', p),
            ('check0_unaligned', 'SBM', replace(p, align_check_value=False)),
            ('no_check', 'SBM', replace(p, allow_check=False)),
            ('H40_reference', 'SBM', replace(p, H=40, check_learning_fraction=1)),
            ('H40_check0', 'SBM', replace(p, H=40)),
            ('ER_reference', 'ER', replace(p, check_learning_fraction=1)),
            ('ER_check0', 'ER', p)]


def lock(root):
    root.mkdir(parents=True, exist_ok=True)
    if (root/'lock.json').exists():
        raise FileExistsError('Never replace an existing scientific lock')
    dump(root/'lock.json', dict(status='exploratory extension motivated by E9 results; fixed E10 design',
        seed=SEED, replicates=REPLICATES, bootstrap_seed=924102, bootstrap_samples=2000,
        python=platform.python_version(), numpy=np.__version__, pyarrow=pa.__version__,
        sources={f:digest(REPO/f) for f in LOCK_FILES},
        conditions=[dict(name=n, family=f, params=asdict(p)) for n,f,p in conditions()]))


def verify_lock(root):
    value = json.loads((root/'lock.json').read_text())
    for f, expected in value['sources'].items():
        if digest(REPO/f) != expected:
            raise RuntimeError(f'Locked source changed: {f}')
    return value


def run_replicate(root_text, rep):
    root = Path(root_text)
    verify_lock(root)
    folder = root/'raw'/f'rep{rep:04d}'
    if (folder/'complete.json').exists():
        hashes = json.loads((folder/'complete.json').read_text())['hashes']
        for f, expected in hashes.items():
            assert digest(folder/f) == expected
        return rep
    if folder.exists():
        raise FileExistsError(f'Inspect incomplete shard instead of overwriting: {folder}')
    folder.mkdir(parents=True)
    graphs = {f:generate_graph(f, V3Params(), graph_seed(SEED,rep,f)) for f in ('SBM','ER')}
    draws = V4Draws(SEED,rep,30,10,30)
    writers, groups, manifests = {}, {}, {}
    try:
        for name, family, p in conditions():
            log = simulate_learning(p,graphs[family],draws,name)
            validate_log(log)
            manifests[name] = log.manifest
            for table, rows in log.tables.items():
                if not rows:
                    continue
                data = pa.Table.from_pylist(rows)
                if table not in writers:
                    writers[table] = pq.ParquetWriter(folder/f'{table}.parquet',data.schema,compression='zstd')
                    groups[table] = []
                writers[table].write_table(data,row_group_size=data.num_rows)
                groups[table].append(name)
    finally:
        for w in writers.values():
            w.close()
    dump(folder/'manifests.json',manifests)
    dump(folder/'row_groups.json',groups)
    dump(folder/'complete.json',dict(replicate=rep,runs=len(conditions()),
        hashes={f.name:digest(f) for f in sorted(folder.iterdir()) if f.is_file()}))
    return rep


def early_groups(log):
    n = log.manifest['params']['N']
    counts = np.bincount([e['student'] for e in log.tables['events']
                         if e['action']=='attempt' and e['homework']<=5], minlength=n)
    order = sorted(range(n),key=lambda i:(counts[i],i))
    labels = {i:('low' if rank < n//3 else 'high' if rank >= n-n//3 else 'middle')
              for rank,i in enumerate(order)}
    tied = int(counts[order[n//3-1]]==counts[order[n//3]]) + int(counts[order[-n//3]]==counts[order[-n//3-1]])
    return labels, tied


def measures(log, labels):
    p = log.manifest['params']
    n, horizon = p['N'],p['H']
    rows, events, traits = log.tables['students'],log.tables['events'],log.tables['traits']
    by = {(r['homework'],r['student']):r for r in rows}
    student_rows = []
    for i in range(n):
        es = [e for e in events if e['student']==i]
        gains = {a:sum(e['K_after']-e['K_before'] for e in es if e['action']==a)
                 for a in ('attempt','check','help_hint')}
        final, initial = by[horizon,i]['K'],traits[i]['K0']
        assert abs(sum(gains.values())-(final-initial))<1e-12
        student_rows.append(dict(student=i, group=labels[i], K0=initial, K_final=final,
            gain=final-initial, later_gain=final-by[5,i]['K'], alpha=traits[i]['alpha'],
            kappa=traits[i]['kappa'], attempts=sum(e['action']=='attempt' for e in es),
            checks=sum(e['action']=='check' for e in es), answers=sum(e['action']=='answer_receive' for e in es),
            later_attempts=sum(e['action']=='attempt' and e['homework']>5 for e in es)/(horizon-5),
            **{a+'_gain':v for a,v in gains.items()}))
    out = summarize(log)
    final_k = [r['K_final'] for r in student_rows]
    initial_k = [r['K0'] for r in student_rows]
    out['K_p90_p10'] = float(np.diff(np.quantile(final_k,[.1,.9]))[0])
    out['K0_p90_p10'] = float(np.diff(np.quantile(initial_k,[.1,.9]))[0])
    out['K_iqr'] = float(np.diff(np.quantile(final_k,[.25,.75]))[0])
    out['boundary_ties'] = 0. # filled using fixed reference labels by caller
    for metric in ('K0','gain','later_gain','attempts','checks','answers','attempt_gain','check_gain','help_hint_gain','later_attempts'):
        out[metric] = float(np.mean([r[metric] for r in student_rows]))
    for metric in ('K0','K_final','gain','later_gain','alpha','attempts','checks','answers','later_attempts'):
        for group in ('low','high'):
            out[f'{group}_{metric}'] = float(np.mean([r[metric] for r in student_rows if r['group']==group]))
        out[f'group_gap_{metric}'] = out[f'high_{metric}']-out[f'low_{metric}']
    tr = []
    for h in range(horizon+1):
        vals = np.array([traits[i]['K0'] if h==0 else by[h,i]['K'] for i in range(n)])
        tr.append(dict(homework=h,K=float(vals.mean()), K_p90_p10=float(np.diff(np.quantile(vals,[.1,.9]))[0]),
            low_K=float(np.mean([vals[i] for i in range(n) if labels[i]=='low'])),
            high_K=float(np.mean([vals[i] for i in range(n) if labels[i]=='high']))))
    return out,student_rows,tr


def analyze(root, output):
    locked = verify_lock(root)
    output.mkdir(parents=True,exist_ok=True)
    summaries, students, trajectory, inventory = [],[],[],[]
    for rep in range(REPLICATES):
        folder = root/'raw'/f'rep{rep:04d}'
        hashes = json.loads((folder/'complete.json').read_text())['hashes']
        for f, expected in hashes.items():
            assert digest(folder/f)==expected, f
            inventory.append(dict(path=str((folder/f).resolve()),sha256=expected))
        labels = {f:early_groups(read_log(folder,n,all_tables=True))
                  for f,n in [('SBM','reference'),('ER','ER_reference')]}
        for name,family,p in conditions():
            log = read_log(folder,name,all_tables=True)
            result,ss,tr = measures(log,labels[family][0])
            result['boundary_ties'] = labels[family][1]
            summaries.append(dict(condition=name,replicate=rep,**result))
            students.extend(dict(condition=name,replicate=rep,**r) for r in ss)
            trajectory.extend(dict(condition=name,replicate=rep,**r) for r in tr)
        if (rep+1)%20==0:
            print(f'Raw audit and decomposition: {rep+1}/{REPLICATES}',flush=True)
    # New zero-check rule and exact baseline get independent deterministic reruns.
    for name in ('reference','check0'):
        p = next(p for n,f,p in conditions() if n==name)
        graph = generate_graph('SBM',V3Params(),graph_seed(SEED,0,'SBM'))
        rerun = simulate_learning(p,graph,V4Draws(SEED,0,30,10,30),name)
        assert rerun.tables==read_log(root/'raw'/'rep0000',name,all_tables=True).tables
    grouped = {n:[r for r in summaries if r['condition']==n] for n,_,_ in conditions()}
    metrics = sorted(set(summaries[0])-{'condition','replicate'})
    rng = np.random.default_rng(locked['bootstrap_seed'])
    estimates, effects = [],[]
    for name,rs in grouped.items():
        reference = 'H40_reference' if name.startswith('H40') else 'ER_reference' if name.startswith('ER') else 'reference'
        for metric in metrics:
            estimates.append(dict(condition=name,metric=metric,**interval([r[metric] for r in rs],rng)))
            if name!=reference:
                effects.append(dict(condition=name,reference=reference,metric=metric,
                    **interval([a[metric]-b[metric] for a,b in zip(rs,grouped[reference])],rng)))
    write_csv(output/'classroom_results.csv',summaries)
    write_csv(output/'student_results.csv',students)
    write_csv(output/'trajectories.csv',trajectory)
    write_csv(output/'condition_estimates.csv',estimates)
    write_csv(output/'paired_effects.csv',effects)
    dump(output/'dataset_manifest.json',dict(raw_root=str(root.resolve()),files=inventory))
    dump(output/'analysis.json',dict(status='exploratory',runs=len(summaries),replicates=REPLICATES,
        source_lock=digest(root/'lock.json'),verified_raw_files=len(inventory),
        student_gain_reconstruction='all within 1e-12',independent_reruns='reference and check0: every raw table identical',
        estimates=estimates,effects=effects))
    print(f'Analysis saved to {output}',flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['lock','run','analyze'])
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--output',type=Path)
    parser.add_argument('--workers',type=int,default=4)
    args=parser.parse_args()
    if args.command=='lock':
        lock(args.root)
    elif args.command=='run':
        verify_lock(args.root)
        start=time.perf_counter()
        with ProcessPoolExecutor(max_workers=args.workers) as pool:
            futures=[pool.submit(run_replicate,str(args.root),r) for r in range(REPLICATES)]
            for j,f in enumerate(as_completed(futures),1):
                f.result()
                if j%10==0:
                    print(f'Completed {j}/{REPLICATES} replicate sets',flush=True)
        dump(args.root/'execution.json',dict(runs=REPLICATES*len(conditions()),seconds=time.perf_counter()-start))
    else:
        if args.output is None:
            parser.error('--output required for analysis')
        analyze(args.root,args.output)


if __name__=='__main__':
    main()
