"""A25 public-grade and AI study, locked before its own outcomes are observed."""
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
from .e10 import early_groups
from .e11 import measures as grade_measures
from .graphs import generate_graph
from .rng import graph_seed
from .v3 import V3Params
from .v4 import V4Log
from .v4_public_ai import PublicAIParams, PublicAIDraws, simulate_public_ai, validate_public_log

SEED, REPLICATES = 924301, 100
LOCK_FILES = ('docs/14-v4-public-grades-ai.md','docs/experiments/E12-deviations.md','src/classroom_swarm/v4_public_ai.py',
              'src/classroom_swarm/e12.py','tests/test_v4_public_ai.py',
              'src/classroom_swarm/v4_grades.py','src/classroom_swarm/e11.py',
              'src/classroom_swarm/e10.py','src/classroom_swarm/v4_learning.py',
              'src/classroom_swarm/v4.py','src/classroom_swarm/e9.py',
              'src/classroom_swarm/v3.py','src/classroom_swarm/graphs.py','src/classroom_swarm/rng.py')

AI_USES_SCHEMA=pa.schema([('homework',pa.int64()),('student',pa.int64()),('mode',pa.string()),
    ('start',pa.int64()),('end',pa.int64()),('K_before',pa.float64()),('K_after',pa.float64()),
    ('packet_id',pa.string()),('accuracy',pa.float64()),('hint_strength',pa.float64())])


def encode_table(name,rows):
    # Both AI modes share nullable numeric fields; do not infer an all-null field as null type.
    return pa.Table.from_pylist(rows,schema=AI_USES_SCHEMA if name=='ai_uses' else None)


def conditions():
    p=PublicAIParams()
    return [('legacy','SBM',replace(p,peer_rule='legacy',distant_weight=0,closeness_spread=0,grade_bias=0,public_signal=0,
                                  grade_effort_only=False,learning_value=.25)),
            ('motivation_only','SBM',replace(p,peer_rule='legacy',distant_weight=0,closeness_spread=0,grade_bias=0,public_signal=0)),
            ('public_no_ai','SBM',p),
            ('answer_ai','SBM',replace(p,ai_mode='answer')),
            ('tutor_ai','SBM',replace(p,ai_mode='tutor')),
            ('answer_ai80','SBM',replace(p,ai_mode='answer',ai_accuracy=.8)),
            ('answer_ai100','SBM',replace(p,ai_mode='answer',ai_accuracy=1)),
            ('tutor_ai0','SBM',replace(p,ai_mode='tutor',ai_hint_strength=0)),
            ('tutor_ai50','SBM',replace(p,ai_mode='tutor',ai_hint_strength=.5)),
            ('no_pressure','SBM',replace(p,grade_response=0)),
            ('answer_no_pressure','SBM',replace(p,ai_mode='answer',grade_response=0)),
            ('tutor_no_pressure','SBM',replace(p,ai_mode='tutor',grade_response=0)),
            ('public_relaxed','SBM',replace(p,peer_rule='relaxed')),
            ('answer_relaxed','SBM',replace(p,ai_mode='answer',peer_rule='relaxed')),
            ('score_only','SBM',replace(p,relationship_strength=0)),
            ('friends_only','SBM',replace(p,distant_weight=0)),
            ('H40_no_ai','SBM',replace(p,H=40)),
            ('H40_answer','SBM',replace(p,H=40,ai_mode='answer')),
            ('H40_tutor','SBM',replace(p,H=40,ai_mode='tutor')),
            ('effort0_no_ai','SBM',replace(p,kappa=0)),
            ('effort0_answer','SBM',replace(p,kappa=0,ai_mode='answer')),
            ('effort0_tutor','SBM',replace(p,kappa=0,ai_mode='tutor')),
            ('effort50_no_ai','SBM',replace(p,kappa=.5)),
            ('effort50_answer','SBM',replace(p,kappa=.5,ai_mode='answer')),
            ('effort50_tutor','SBM',replace(p,kappa=.5,ai_mode='tutor')),
            ('answer_no_exam_feedback','SBM',replace(p,ai_mode='answer',feedback_mode='none'))]


def lock(root):
    root.mkdir(parents=True, exist_ok=True)
    if (root/'lock.json').exists():
        raise FileExistsError('Never replace an existing scientific lock')
    dump(root/'lock.json', dict(status='exploratory public grade and relationship-aware sources plus AI; fixed E12 design',
        seed=SEED, replicates=REPLICATES, bootstrap_seed=924302, bootstrap_samples=2000,
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
    draws = PublicAIDraws(SEED,rep,30,10,30)
    writers, groups, manifests = {}, {}, {}
    try:
        for name, family, p in conditions():
            log = simulate_public_ai(p,graphs[family],draws,name)
            validate_public_log(log)
            manifests[name] = log.manifest
            for table, rows in log.tables.items():
                if not rows:
                    continue
                data = encode_table(table,rows)
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
    result.tables['ai_uses'] = []
    result.tables['contacts'] = []
    for table in result.tables:
        if table in groups and name in groups[table]:
            result.tables[table] = pq.ParquetFile(folder/f'{table}.parquet').read_row_group(groups[table].index(name)).to_pylist()
    return result


def measures(log,labels):
    out,students,tr=grade_measures(log,labels)
    p=log.manifest['params']; rows=log.tables['students']
    h_exam=max(r['homework'] for r in log.tables['exams'])
    final=[r for r in rows if r['homework']==p['H']]
    matched=[r for r in rows if r['homework']==h_exam]
    late=[r for r in rows if r['homework']>p['H']-5]
    def mean(xs): return float(np.mean(xs)) if len(xs) else float('nan')
    out['homework_final']=mean([r['grade'] for r in final])
    out['homework_at_final_exam']=mean([r['grade'] for r in matched])
    out['late_homework_final_exam_gap']=out['grade_exam_gap']
    out['grade_exam_gap']=out['homework_at_final_exam']-out['exam_final']
    out['final_assessment_homework']=h_exam
    for metric in ('peer_copied','direct_ai_answer','ai_answer_origin','ai_answer','ai_tutor'):
        out[metric+'_late']=mean([r[metric] for r in late])
        out[metric+'_final']=mean([r[metric] for r in final])
    out['peer_ai_origin_late']=mean([r['peer_copied'] and r['ai_answer_origin'] for r in late])
    out['ai_answer_total']=sum(r['ai_answer'] for r in rows)/p['N']
    out['ai_tutor_total']=sum(r['ai_tutor'] for r in rows)/p['N']
    tutor_uses=sum(r['mode']=='ai_tutor' for r in log.tables['ai_uses'])
    consumed=sum(r['hint_source']=='ai' for r in log.tables['packets'])
    out['tutor_followthrough']=consumed/tutor_uses if tutor_uses else float('nan')
    peer_requests=[r for r in log.tables['requests'] if r['mode']=='answer']
    higher=[r for r in peer_requests if r['provider_public_grade'] is not None
            and r['provider_public_grade']>r['requester_public_grade']]
    out['higher_grade_source_requests']=len(higher)
    out['higher_grade_source_not_higher_K']=mean([r['research_provider_K']<=r['research_requester_K'] for r in higher])
    out['source_closeness']=mean([r['closeness'] for r in peer_requests])
    contacts={(r['u'],r['v']):r['friend'] for r in log.tables['contacts']}
    out['friend_source_share']=mean([contacts[tuple(sorted((r['requester'],r['provider'])))] for r in peer_requests])
    for row in students:
        rr=[r for r in rows if r['student']==row['student']]
        end=next(r for r in rr if r['homework']==p['H'])
        row.update(ai_answer_uses=sum(r['ai_answer'] for r in rr),ai_tutor_uses=sum(r['ai_tutor'] for r in rr),
                   final_grade=end['grade'],final_route=end['final_route'],final_ai_answer_origin=end['ai_answer_origin'])
    for row in tr:
        rr=[r for r in rows if r['homework']==row['homework']]
        ex=[r for r in log.tables['exams'] if r['homework']==row['homework']]
        row.update(grade=mean([r['grade'] for r in rr]),exam=mean([r['score'] for r in ex]),
                   peer_copy=mean([r['peer_copied'] for r in rr]),direct_ai=mean([r['direct_ai_answer'] for r in rr]),
                   ai_origin=mean([r['ai_answer_origin'] for r in rr]))
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
                  for f,n in [('SBM','public_no_ai')]}
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
    for name in ('public_no_ai','answer_ai','tutor_ai'):
        p = next(p for n,f,p in conditions() if n==name)
        graph = generate_graph('SBM',V3Params(),graph_seed(SEED,0,'SBM'))
        rerun = simulate_public_ai(p,graph,PublicAIDraws(SEED,0,30,10,30),name)
        assert rerun.tables==read_log(root/'raw'/'rep0000',name,all_tables=True).tables
    grouped = {n:[r for r in summaries if r['condition']==n] for n,_,_ in conditions()}
    metrics = sorted(set(summaries[0])-{'condition','replicate'})
    rng = np.random.default_rng(locked['bootstrap_seed'])
    estimates, effects = [],[]
    for name,rs in grouped.items():
        for metric in metrics:
            estimates.append(dict(condition=name,metric=metric,**interval([r[metric] for r in rs],rng)))
    primary=[('motivation_only','legacy'),('public_no_ai','motivation_only'),('answer_ai','public_no_ai'),('tutor_ai','public_no_ai'),('tutor_ai','answer_ai')]
    contrasts=primary+[('answer_ai80','answer_ai'),('answer_ai100','answer_ai'),('tutor_ai0','tutor_ai'),
        ('tutor_ai50','tutor_ai'),('no_pressure','public_no_ai'),('answer_no_pressure','answer_ai'),
        ('tutor_no_pressure','tutor_ai'),('public_relaxed','public_no_ai'),('answer_relaxed','answer_ai'),
        ('score_only','public_no_ai'),('friends_only','public_no_ai'),('H40_answer','H40_no_ai'),
        ('H40_tutor','H40_no_ai'),('effort0_no_ai','public_no_ai'),('effort0_answer','answer_ai'),
        ('effort0_tutor','tutor_ai'),('effort50_no_ai','public_no_ai'),('effort50_answer','answer_ai'),
        ('effort50_tutor','tutor_ai'),('answer_no_exam_feedback','answer_ai')]
    for name,reference in contrasts:
        for metric in metrics:
            effects.append(dict(condition=name,reference=reference,primary=(name,reference) in primary,metric=metric,
                **interval([a[metric]-b[metric] for a,b in zip(grouped[name],grouped[reference])],rng)))
    write_csv(output/'classroom_results.csv',summaries)
    write_csv(output/'student_results.csv',students)
    write_csv(output/'trajectories.csv',trajectory)
    write_csv(output/'condition_estimates.csv',estimates)
    write_csv(output/'paired_effects.csv',effects)
    dump(output/'dataset_manifest.json',dict(raw_root=str(root.resolve()),files=inventory))
    dump(output/'analysis.json',dict(status='exploratory',runs=len(summaries),replicates=REPLICATES,
        source_lock=digest(root/'lock.json'),verified_raw_files=len(inventory),
        student_gain_reconstruction='all within 1e-12',independent_reruns='public_no_ai, answer_ai and tutor_ai: every raw table identical',
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
