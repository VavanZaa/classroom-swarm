"""Lock, execute and independently re-read A30 functional teacher diagnostics."""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO/'src'))
import numpy as np
import pyarrow.parquet as pq
from classroom_swarm.teacher_config import load_config, resolve_config, preflight, run_experiment, save_json, sha256
from classroom_swarm.v4 import V4Log
from classroom_swarm.v4_teacher import validate_teacher_log

HISTORICAL_LOCKS = [
    'E9r1/lock.json','E10/lock.json','E11/lock.json','E12r1/lock.json',
    'E13/lock.json','E14/preregistration-lock.json','E16-tutoring-r1/diagnostic-lock.json',
    'E17-tutoring-robustness-r1/design-lock.json','teacher-role-audit-2026-10-06/audit-lock.json']


def check_historical_sources():
    checked = 0
    for relative in HISTORICAL_LOCKS:
        for name,digest in load_config(REPO/'runs'/relative)['sources'].items():
            assert sha256(REPO/name) == digest, (relative,name)
            checked += 1
    return checked


def summarize(root):
    runs = []
    for manifest in sorted((root/'probes'/'raw').glob('rep*/*/manifest.json')):
        folder = manifest.parent
        completion = load_config(folder/'complete.json')
        for name,digest in completion['hashes'].items():
            assert sha256(folder/name) == digest, (folder,name)
        log = V4Log(load_config(manifest))
        for name in completion['hashes']:
            if name.endswith('.parquet'):
                log.tables[name[:-8]] = pq.read_table(folder/name).to_pylist()
        validate_teacher_log(log)
        h = log.manifest['params']['H']
        final = [r for r in log.tables['students'] if r['homework']==h]
        exams = [r for r in log.tables['exams'] if r['homework']==h]
        budgets = {r['homework']:r for r in log.tables.get('teacher_budget',[])}
        actions = log.tables.get('teacher_actions',[])
        work = log.tables.get('teacher_workload',[])
        runs.append(dict(condition=log.manifest['condition'],replicate=log.manifest['replicate'],
            final_K_pp=100*float(np.mean([r['K'] for r in final])),
            final_exam_pp=100*float(np.mean([r['score'] for r in exams])),
            appointments=len(actions),lessons=sum(r['action']=='instruction' for r in actions),
            guidance_attendance=len(log.tables.get('teacher_guidance',[])),
            teacher_content_gain_pp_per_student=100*sum(r['gain'] for r in log.tables.get('teacher_learning',[]))/len(final),
            grading_ticks=sum(r['cost'] for r in work if r['kind']=='grading' and r['homework']<=h),
            ungraded_at_final_homework=budgets.get(h,{}).get('grading_backlog',0),
            ungraded_after_closing_day=budgets.get(h+1,{}).get('grading_backlog',0),
            complete_sha256=sha256(folder/'complete.json')))
    by_condition = defaultdict(list)
    for row in runs:
        by_condition[row['condition']].append(row)
    means = {}
    metrics = [key for key in runs[0] if key not in {'condition','replicate','complete_sha256'}]
    for condition,rows in by_condition.items():
        means[condition] = {key:float(np.mean([r[key] for r in rows])) for key in metrics}
    # Structural expectations declared before outcomes, never desired net signs.
    assert means['no_teacher']['appointments'] == 0
    assert means['fixed_automated']['grading_ticks'] == 0
    assert means['fixed_manual']['grading_ticks'] > 0
    assert means['fixed_automated']['guidance_attendance'] > means['fixed_manual']['guidance_attendance']
    assert means['incorrect_automated']['teacher_content_gain_pp_per_student'] == 0
    assert means['guidance_only']['teacher_content_gain_pp_per_student'] == 0
    assert means['guidance_time_only']['teacher_content_gain_pp_per_student'] == 0
    return dict(runs=runs,means=means,raw_audits='all passed',
                interpretation='Functional implementation checks; no human-study validation or fitted coefficients.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config',type=Path,default=REPO/'configs/A30-teacher-diagnostic.json')
    parser.add_argument('--output',type=Path,default=REPO/'runs/A30-teacher-functional-r1')
    args = parser.parse_args()
    config = load_config(args.config)
    resolved = resolve_config(config)
    preflight(resolved)
    if args.output.exists():
        parser.error('output already exists; use a new diagnostic identity')
    historical = check_historical_sources()
    sources = sorted((REPO/'src/classroom_swarm').glob('*.py')) + [Path(__file__),args.config,
        REPO/'tests/test_v4_teacher.py',REPO/'docs/20-v4-teacher-role.md',
        REPO/'docs/experiments/A30-teacher-functional-plan.md']
    hashes = {str(p.resolve().relative_to(REPO)).replace('\\','/'):sha256(p) for p in sources}
    args.output.mkdir(parents=True,exist_ok=False)
    save_json(args.output/'diagnostic-lock.json',dict(
        declared_utc=datetime.now(timezone.utc).isoformat(),sources=hashes,
        configuration=resolved,historical_entries_verified=historical,
        interpretation='Functional probes, not calibration or empirical validation.'))
    run_experiment(config,args.output/'probes')
    result = summarize(args.output)
    assert len(result['runs']) == resolved['replicates']*len(resolved['conditions'])
    for name,digest in hashes.items():
        assert sha256(REPO/name)==digest,name
    result['historical_entries_verified'] = check_historical_sources()
    save_json(args.output/'summary.json',result)
    print(json.dumps({'runs':len(result['runs']),'means':result['means'],
                      'historical_entries_verified':historical,'raw_audits':result['raw_audits']},indent=2))


if __name__=='__main__':
    main()
