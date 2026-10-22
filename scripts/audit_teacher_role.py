"""Read-only model assessment: is a teacher role represented in the A29 engine?"""
from __future__ import annotations
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime,timezone
from pathlib import Path
import json
import pyarrow.parquet as pq
from classroom_swarm.tutoring_config import (
    REPO,PARAM_NAMES,template,resolve_config,run_experiment,load_config,save_json,sha256)
from classroom_swarm.tutoring_settings import TutoringParams
from classroom_swarm.v4 import V4Log
from classroom_swarm.v4_tutoring import validate_tutoring_log


def rejected(config):
    try:resolve_config(config)
    except ValueError as error:return str(error)
    raise AssertionError('Unsupported teacher declaration was unexpectedly accepted')


def probe_config():
    c=template()
    c.update(experiment_id='Teacher_role_audit_20261006',seed=10060601,replicates=1,
        notes='Two mechanical probes, not a study replication or parameter fit. Node 4 is an analyst-designated teacher-like peer; no teacher role is declared.')
    c['params'].update(N=5,H=3,exam_every=1,allow_answer=False,ai_mode='none',
        tutoring_activity='shared_practice',distant_weight=0.,closeness_spread=0.)
    c['initial']['knowledge']={'kind':'values','values':[.35]*4+[.95]}
    c['initial']['confidence']={'kind':'constant','value':.5}
    c['initial']['learning_efficiency']={'kind':'constant','value':.0584}
    c['initial']['effort_aversion']={'kind':'constant','value':.15}
    for name in c['initial']:
        if name.startswith('benefit_'):c['initial'][name]={'kind':'constant','value':.5}
    c['network'].update(family='CUSTOM',edges=[[i,4] for i in range(4)])
    c['conditions']=[dict(name='star_tutoring',params={},initial={},network={}),
        dict(name='star_independent',params={'allow_hint':False},initial={},network={})]
    c['contrasts']=[dict(condition='star_tutoring',reference='star_independent',
        kind='single_parameter',identity='not_identity')]
    c['stated_identities'] += [
        'All graph nodes are processed as students; analyst labels do not assign an engine role.',
        'Scheduled explanations can serve multiple recipients in parallel; no teacher budget is represented.',
        'The high-knowledge fifth node is included in all-node student/exam aggregates.']
    return c


def main():
    root=REPO/'runs/teacher-role-audit-2026-10-06'
    c=probe_config()
    unsupported={}
    for key,value in [('teacher_capacity',1),('teacher_time_budget',12),('teacher_mode','adaptive')]:
        bad=deepcopy(c);bad['params'][key]=value
        unsupported[key]=rejected(bad)
    bad=deepcopy(c);bad['node_roles']={'4':'teacher'}
    unsupported['node_roles']=rejected(bad)
    bad=deepcopy(c);bad['params']['N']=4
    bad['initial']['knowledge']={'kind':'values','values':[.35]*4}
    unsupported['external_teacher_node_id_4_with_N_4']=rejected(bad)
    assert not any(name.startswith('teacher') for name in PARAM_NAMES)
    sources=sorted((REPO/'src/classroom_swarm').glob('*.py'))+[Path(__file__)]
    before={str(p.relative_to(REPO)).replace('\\','/'):sha256(p) for p in sources}
    root.mkdir(parents=True,exist_ok=False)
    save_json(root/'audit-lock.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
        sources=before,probe_declaration=c,interpretation='mechanical role audit, not an outcome experiment'))
    run_experiment(c,root/'probes')
    evidence={}
    for condition in ('star_tutoring','star_independent'):
        folder=root/'probes/raw/rep0000'/condition
        hashes=load_config(folder/'complete.json')['hashes']
        for name,digest in hashes.items():assert sha256(folder/name)==digest,name
        log=V4Log(load_config(folder/'manifest.json'))
        for name in hashes:
            if name.endswith('.parquet'):log.tables[name[:-8]]=pq.read_table(folder/name).to_pylist()
        validate_tutoring_log(log)
        assert log.manifest['params']==asdict(TutoringParams(**resolve_config(c)['conditions'][0 if condition=='star_tutoring' else 1]['params']))
        actor=4
        exams=[r for r in log.tables['exams'] if r['student']==actor]
        rows=[r for r in log.tables['students'] if r['student']==actor]
        receipts=[r for r in log.tables['tutoring_content'] if r['requester']==actor]
        provided=[r for r in log.tables['tutoring_content'] if r['provider']==actor]
        feedback=log.tables['homework_feedback']+log.tables['feedback']
        assert all(r['K_before']==r['K_after'] for r in feedback)
        assert len(rows)==len(exams)==3
        assert set(r['student'] for r in log.tables['traits'])==set(range(5))
        evidence[condition]=dict(
            analyst_designated_teacher_id=actor,engine_student_ids=list(range(5)),
            designated_node_student_rows=len(rows),designated_node_exam_rows=len(exams),
            designated_node_homework_feedback_rows=sum(r['student']==actor for r in log.tables['homework_feedback']),
            designated_node_received_peer_sessions=len(receipts),
            designated_node_provided_peer_sessions=len(provided),
            designated_node_K0=.95,designated_node_final_K=rows[-1]['K'],
            teacher_like_providers_by_episode={str(h):sum(r['homework']==h for r in provided) for h in range(1,4)},
            designated_node_help_ticks_by_episode=[r['helper_ticks'] for r in rows],
            initial_all_node_knowledge=.47,initial_actual_learner_knowledge=.35,
            final_actual_learner_knowledge=sum(r['K'] for r in log.tables['students'] if r['homework']==3 and r['student']<4)/4,
            final_all_node_knowledge=sum(r['K'] for r in log.tables['students'] if r['homework']==3)/5,
            feedback_rows_checked=len(feedback),feedback_direct_knowledge_changes=0,
            teacher_event_tables=[name for name in log.tables if name.startswith('teacher')],
            completion_sha256=sha256(folder/'complete.json'))
    assert evidence['star_tutoring']['designated_node_received_peer_sessions']==3
    assert evidence['star_tutoring']['designated_node_provided_peer_sessions']==12
    assert evidence['star_tutoring']['designated_node_help_ticks_by_episode']==[0,0,0]
    assert not any(v['teacher_event_tables'] for v in evidence.values())
    for name,digest in before.items():assert sha256(REPO/name)==digest,name
    historical=0
    for path in [REPO/'runs/E16-tutoring-r1/diagnostic-lock.json',
                 REPO/'runs/E17-tutoring-robustness-r1/design-lock.json']:
        for name,digest in load_config(path)['sources'].items():
            assert sha256(REPO/name)==digest,(path,name);historical+=1
    result=dict(unsupported_declarations=unsupported,probes=evidence,
        locked_historical_source_entries_checked=historical,
        engine_sources_unchanged=True,raw_audits='all passed',
        interpretation='No separate teacher role exists in the audited model. A high-knowledge node can help as a peer but is still processed as a learner.')
    save_json(root/'assessment.json',result)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
