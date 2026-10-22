"""A24 corrected grade-feedback study, locked before its own outcomes are observed."""
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

from .e9 import REPO, digest, dump, write_csv, interval
from .e10 import early_groups, measures as activity_measures
from .graphs import generate_graph
from .rng import graph_seed
from .v3 import V3Params
from .v4 import V4Draws, V4Log
from .v4_grades import GradeParams, simulate_grades, validate_grade_log

SEED, REPLICATES = 924201, 100
LOCK_FILES = ('docs/13-v4-homework-feedback.md', 'src/classroom_swarm/v4_grades.py',
              'src/classroom_swarm/e11.py', 'tests/test_v4_grades.py',
              'src/classroom_swarm/e10.py', 'src/classroom_swarm/v4_learning.py',
              'src/classroom_swarm/v4.py', 'src/classroom_swarm/e9.py',
              'src/classroom_swarm/v3.py', 'src/classroom_swarm/graphs.py', 'src/classroom_swarm/rng.py')


def conditions():
    p = GradeParams()
    return [('reference', 'SBM', replace(p, grade_response=0)),
            ('grade_response', 'SBM', p),
            ('response20', 'SBM', replace(p, grade_response=.2)),
            ('response80', 'SBM', replace(p, grade_response=.8)),
            ('no_reinforcement', 'SBM', replace(p, eta_benefit=0)),
            ('no_answer', 'SBM', replace(p, allow_answer=False)),
            ('no_hint', 'SBM', replace(p, allow_hint=False)),
            ('misattribute0', 'SBM', replace(p, misattribution=0)),
            ('misattribute80', 'SBM', replace(p, misattribution=.8)),
            ('H40_reference', 'SBM', replace(p, H=40, grade_response=0)),
            ('H40_grade_response', 'SBM', replace(p, H=40)),
            ('ER_reference', 'ER', replace(p, grade_response=0)),
            ('ER_grade_response', 'ER', p)]


def lock(root):
    root.mkdir(parents=True, exist_ok=True)
    if (root/'lock.json').exists():
        raise FileExistsError('Never replace an existing scientific lock')
    dump(root/'lock.json', dict(status='exploratory correction of checking semantics; bad grades motivate cheating; fixed E11 design',
        seed=SEED, replicates=REPLICATES, bootstrap_seed=924202, bootstrap_samples=2000,
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
            log = simulate_grades(p,graphs[family],draws,name)
            validate_grade_log(log)
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


def read_log(folder, name, all_tables=True):
    manifests = json.loads((folder/'manifests.json').read_text())
    groups = json.loads((folder/'row_groups.json').read_text())
    result = V4Log(manifests[name])
    result.tables['homework_feedback'] = []
    for table in result.tables:
        if table in groups and name in groups[table]:
            result.tables[table] = pq.ParquetFile(folder/f'{table}.parquet').read_row_group(groups[table].index(name)).to_pylist()
    return result


def measures(log, labels):
    out, students, tr = activity_measures(log, labels)
    p = log.manifest['params']
    rows = log.tables['students']
    feedback = log.tables['homework_feedback']
    by = {(r['homework'],r['student']):r for r in rows}
    def mean(values):
        return float(np.mean(values)) if len(values) else float('nan')
    late = [r for r in rows if r['homework']>p['H']-5]
    out['grade_shortfall_late'] = mean([r['grade_shortfall'] for r in late])
    out['grade_satisfaction_late'] = mean([r['grade_satisfaction'] for r in late])
    out['homework_feedback_count'] = len(feedback)
    out['hint_requests_total'] = sum(r['hint'] for r in rows)/p['N']
    out['answer_requests_total'] = sum(r['answer'] for r in rows)/p['N']
    out['hint_receipts_total'] = sum(e['action']=='hint_receive' for e in log.tables['events'])/p['N']
    for label, select in [('below_target',lambda r:r['grade']<p['grade_target']),
                          ('at_or_above_target',lambda r:r['grade']>=p['grade_target']),
                          ('good_copied',lambda r:r['grade']>=p['grade_target'] and r['route']=='answer')]:
        ff=[r for r in feedback if r['homework']<=p['H'] and select(r)]
        following=[by[r['homework'],r['student']] for r in ff]
        out[label+'_n']=len(ff)
        out[label+'_next_answer_request']=mean([r['answer']>0 for r in following])
        out[label+'_next_copy']=mean([r['copied'] for r in following])
        out[label+'_next_attempts']=mean([r['attempt'] for r in following])
        out[label+'_next_hint_request']=mean([r['hint']>0 for r in following])
    for label,select in [('good_copied',lambda r:r['route']=='answer' and r['grade']>=p['grade_target']),
                         ('bad_copied',lambda r:r['route']=='answer' and r['grade']<p['grade_target'])]:
        ff=[r for r in feedback if select(r)]
        deltas=[json.loads(r['B_after'])[2]-json.loads(r['B_before'])[2] for r in ff]
        out[label+'_feedback_n']=len(ff)
        out[label+'_B_answer_delta']=mean(deltas)
        out[label+'_B_answer_increased']=mean([v>0 for v in deltas])
        out[label+'_B_answer_decreased']=mean([v<0 for v in deltas])
    for ev in log.tables['events']:
        if ev['action'].startswith('choose_'):
            detail=json.loads(ev['detail'])
            pressure=by[ev['homework'],ev['student']]['grade_shortfall']
            assert detail['grade_shortfall']==pressure
            assert detail['answer_pressure_bonus']==(p['grade_response']*pressure if 'answer' in detail['scores'] else 0.)
    return out,students,tr


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
    # Corrected grade rule and zero-pressure reference get independent deterministic reruns.
    for name in ('reference','grade_response'):
        p = next(p for n,f,p in conditions() if n==name)
        graph = generate_graph('SBM',V3Params(),graph_seed(SEED,0,'SBM'))
        rerun = simulate_grades(p,graph,V4Draws(SEED,0,30,10,30),name)
        assert rerun.tables==read_log(root/'raw'/'rep0000',name,all_tables=True).tables
    grouped = {n:[r for r in summaries if r['condition']==n] for n,_,_ in conditions()}
    metrics = sorted(set(summaries[0])-{'condition','replicate'})
    rng = np.random.default_rng(locked['bootstrap_seed'])
    estimates, effects = [],[]
    for name,rs in grouped.items():
        reference = ('H40_reference' if name.startswith('H40') else 'ER_reference' if name.startswith('ER')
                     else 'reference' if name in {'reference','grade_response','response20','response80'} else 'grade_response')
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
        student_gain_reconstruction='all within 1e-12',independent_reruns='reference and grade_response: every raw table identical',
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
