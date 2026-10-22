"""A31 raw replay of topics, observations, budgets, fatigue and observed-only policy."""
from collections import defaultdict
from dataclasses import replace
from dataclasses import fields
from copy import deepcopy
import json
import numpy as np
from .v4 import validate_log,MAX_TICKS
from .v4_teacher import validate_teacher_log
from .teacher_settings import TeacherSettings,teacher_random
from .tutoring_settings import TutoringParams,content_effect
from .v4_public_ai import PublicAIDraws
from .mechanism_settings import resolve_mechanisms,incentive_plan
from .teacher_validation import validate_teacher_student_tables
from .declared_settings import DeclaredParams


def close(a,b):assert abs(a-b)<1e-12,(a,b)


def validate_mechanism_log(log):
    if log.manifest['model']!='A31-v4.6-classroom-mechanisms':return validate_teacher_log(log)
    m,t=log.manifest,log.tables;p=TutoringParams(**m['params']);p.validate()
    base=TeacherSettings(**m['teacher']);s=resolve_mechanisms(m['mechanisms']);s.validate(p,base)
    validate_log(log);n,T=p.N,m['topic_count']
    # Retain all A30 grade/provenance/time audits using the active-topic coordinate.
    proxy=deepcopy(log)
    proxy.manifest['params']={f.name:getattr(p,f.name) for f in fields(DeclaredParams)}
    for row in proxy.tables['students']:
        row['K_before'],row['K']=row['K_active_before'],row['K_active']
    validate_teacher_student_tables(proxy)
    draws=PublicAIDraws(m['seed'],m['replicate'],n,p.items,p.exam_items)
    assert T==(len(s.topics.names) if s.topics.enabled else 1)
    schedule=s.topics.schedule if s.topics.enabled and s.topics.schedule else [h%T for h in range(p.H)]
    transfer=np.array(s.topics.transfer) if s.topics.enabled and s.topics.transfer else np.eye(T)
    k=np.empty((n,T));initial=t['topic_initial'];assert len(initial)==n*T
    for r in initial:assert 0<=r['knowledge']<=1;k[r['student'],r['topic']]=r['knowledge']
    for r in t['traits']:close(r['K0'],k[r['student']].mean())
    snapshots={};start={};components={(r['homework'],r['tick'],r['student']):r for r in t['learning_components']}
    learning=defaultdict(list)
    for r in t['topic_learning']:learning[r['homework']].append(r)
    students={(r['homework'],r['student']):r for r in t['students']}
    for h in range(1,p.H+1):
        start[h]=k.copy();active=schedule[h-1]
        for r in learning[h]:
            i,target=r['student'],r['topic'];assert r['source_topic']==active
            assert 0<r['fraction']<=1 and r['transfer']==transfer[active,target]
            close(r['before'],k[i,target]);close(r['after'],r['before']+(1-r['before'])*r['fraction']*r['transfer'])
            if target==active:
                c=components[h,r['tick'],i]
                close(c['K_before'],r['before']);close(c['K_after'],r['after'])
                close(sum(c[x] for x in ('practice_gain','content_gain','helper_gain','teacher_gain')),r['after']-r['before'])
            k[i,target]=r['after']
        snapshots[h]=k.copy()
        for i in range(n):
            r=students[h,i];assert r['topic']==active
            close(r['K_before'],start[h][i].mean());close(r['K'],k[i].mean())
            close(r['K_active_before'],start[h][i,active]);close(r['K_active'],k[i,active])
        states=[r for r in t['topic_states'] if r['homework']==h];assert len(states)==n*T
        for r in states:close(r['knowledge'],k[r['student'],r['topic']])
    # Measurement-only exams exactly reconstruct from semantic uniforms and topic state.
    examtopics={(r['homework'],r['student'],r['topic']):r for r in t['exam_topics']}
    itemgroups=defaultdict(list)
    for r in t['exam_items']:
        h,i,topic=r['homework'],r['student'],r['topic'];assert topic==r['item']%T
        close(r['probability'],snapshots[h][i,topic])
        u=draws.legacy.exam(h//p.exam_every)
        assert r['correct']==bool(u[r['item'],i]<r['probability']);itemgroups[h,i].append(r)
    for r in t['exams']:
        rows=itemgroups[r['homework'],r['student']];assert len(rows)==p.exam_items
        close(r['score'],np.mean([a['correct'] for a in rows]))
        close(r['K'],snapshots[r['homework']][r['student']].mean())
        for topic in range(T):close(examtopics[r['homework'],r['student'],topic]['score'],np.mean([a['correct'] for a in rows if a['topic']==topic]))
    # Private peer signals: replay coverage and observation error, then arrival order.
    content={(r['homework'],r['start'],r['requester'],r['provider']):r for r in t['tutoring_content']}
    assert len(content)==len(t['peer_signals'])
    o=s.peer_observation;pending=[];signals={}
    for r in t['peer_signals']:
        h,st,i,j=r['homework'],r['start'],r['requester'],r['provider'];c=content[h,st,i,j]
        correct=np.array([x=='1' for x in c['correct_bits']])
        checks=np.random.default_rng(np.random.SeedSequence([draws.seed,draws.replicate,125,h])).random((MAX_TICKS,n,p.items))[st,i]<p.quality_check_probability*(o.coverage if o.enabled else 1)
        u=np.random.default_rng(np.random.SeedSequence([draws.seed,draws.replicate,134,h,st,i])).random(p.items)
        observed=np.where(correct,u<o.sensitivity,u>=o.specificity) if o.enabled else correct
        assert r['checked_items']==int(checks.sum()) and r['correct_checked']==int(np.sum(correct&checks))
        assert r['observed_bits']==''.join('1' if x else '0' for x in observed[checks])
        assert r['observed_quality']==(float(observed[checks].mean()) if np.any(checks) else None)
        assert r['release_absolute']==(h-1)*p.ticks+r['source_tick']+(o.delay_ticks if o.enabled else 0)
        signals[h,r['source_tick'],i,j]=r
        if np.any(checks):pending.append(r)
    q={}
    for r in t['initial_quality']:
        for topic in range(T if o.enabled and o.topic_specific else 1):q[topic,r['requester'],r['provider']]=r['quality']
    ordered=[((r['homework'],r['tick'],0,idx),'arrival',r) for idx,r in enumerate(t['quality_feedback'])]
    ordered += [((r['homework'],r['tick'],1,idx),'choice',r) for idx,r in enumerate(t['quality_choice_state'])]
    for _,kind,r in sorted(ordered,key=lambda x:x[0]):
        key=(r['topic'] if o.enabled and o.topic_specific else 0,r['requester'],r['provider'])
        if kind=='choice':close(r['quality'],q[key]);continue
        source=signals[r['source_homework'],r['source_tick'],r['requester'],r['provider']]
        assert source in pending;pending.remove(source)
        assert (r['homework']-1)*p.ticks+r['tick']>=source['release_absolute']
        assert r['observed_quality']==source['observed_quality'];close(r['Q_before'],q[key])
        q[key]+=p.quality_learning_rate*(source['observed_quality']-q[key]);close(r['Q_after'],q[key])
    assert pending==t['peer_signal_backlog']
    # Teacher information, mandatory time, fatigue and choice are replayed independently.
    budgets={r['homework']:r for r in t['teacher_budget']};assert len(budgets)==p.H+1
    runtimes={r['homework']:TeacherSettings(**json.loads(r['settings'])) for r in t['teacher_runtime']}
    arrivals={r['homework']:r for r in t['workload_arrivals']};fatigue={r['homework']:r for r in t['teacher_fatigue']}
    estimates=np.full((T,n),base.observation_prior);seen=np.zeros((T,n),int);last=np.full(n,-1,int)
    backlog=0;old_fatigue=0.;returned={(r['source_homework'],r['student']):r for r in t['homework_feedback']}
    for h in range(1,p.H+2):
        active=schedule[min(h-1,p.H-1)];rt=runtimes[h];b=budgets[h];a=arrivals[h];w=s.workload;f=fatigue[h]
        assert rt.time_budget==(base.time_budget if base.enabled else 0)
        expected_admin=0 if h>p.H else (base.admin_ticks if base.enabled else 0)
        burst=w.admin_bursts[h-1] if w.enabled and w.admin_bursts and h<=p.H else 0
        prep=w.preparation_ticks if w.enabled and h<=p.H else 0
        switch=w.topic_switch_ticks if w.enabled and 1<h<=p.H and active!=schedule[h-2] else 0
        assert (a['base_admin'],a['burst'],a['preparation'],a['topic_switch'])==(expected_admin,burst,prep,switch)
        assert a['arrived']==expected_admin+burst+prep+switch
        close(f['before'],old_fatigue);close(f['recovered'],old_fatigue*(1-w.recovery) if w.enabled and h<=p.H else old_fatigue)
        close(f['after_workload'],min(1,f['recovered']+(w.fatigue_per_tick*b['workload'] if w.enabled else 0)))
        close(rt.teaching_skill,base.teaching_skill*(1-w.quality_loss*f['after_workload']) if w.enabled else base.teaching_skill)
        close(f['after'],min(1,f['after_workload']+(w.fatigue_per_tick*b['actions'] if w.enabled else 0)));old_fatigue=f['after']
        work=[r for r in t['teacher_workload'] if r['homework']==h];assert sum(r['cost'] for r in work)==b['workload']
        admin=next(r for r in work if r['kind']=='admin');assert admin['due']==backlog+a['arrived']
        assert admin['cost']==min(rt.time_budget,admin['due']);backlog=admin['due']-admin['cost'];assert b['admin_backlog']==backlog
        cursor=admin['cost']
        for r in work:
            if r['kind']=='grading':
                assert r['cost']==rt.grading_cost;cursor+=r['cost']
                row=returned[r['source_homework'],r['student']]
                assert row['homework']==h and row['tick']==(cursor if r['cost'] else 0)
                assert row['grade']==students[r['source_homework'],r['student']]['grade']
        for r in [a for a in t['teacher_observations'] if a['homework']==h]:
            topic,i=r['topic'],r['student'];assert (h,r['tick'])>=(r['release'],r['release_tick'])
            source=returned[r['source_homework'],i] if r['source']=='homework' else examtopics[r['source_homework'],i,topic]
            assert r['score']==source['grade' if r['source']=='homework' else 'score']
            earliest=(source['homework'] if r['source']=='homework' else source['release'])+base.observation_delay
            assert r['release']==earliest
            coverage=teacher_random(draws,'observation_coverage',r['source_homework'],(2,n))[int(r['source']=='exam'),i]
            noise=teacher_random(draws,'observation_noise',r['source_homework'],(2,n))[int(r['source']=='exam'),i]
            expected=float(np.clip(r['score']+base.observation_noise_std*noise,0,1)) if coverage<base.observation_coverage else None
            assert r['observed_score']==expected;close(r['estimate_before'],estimates[topic,i])
            if expected is not None and r['weight']>0:
                estimates[topic,i]+=base.observation_learning_rate*r['weight']*(expected-estimates[topic,i]);seen[topic,i]+=1
            close(r['estimate_after'],estimates[topic,i]);assert r['seen']==seen[topic,i]
        state=[r for r in t['teacher_observation_state'] if r['homework']==h];assert len(state)==n
        for r in state:close(r['estimate'],estimates[active,r['student']]);assert r['seen']==seen[active,r['student']]
        acts=[r for r in t['teacher_actions'] if r['homework']==h]
        if h<=p.H:
            plans,queue,end,candidates=incentive_plan(s.incentives,rt,p,estimates[active],seen[active],last,h,b['workload'],f['after_workload'])
            assert len(plans)==len(acts)
            recorded=[r for r in t['incentive_candidates'] if r['homework']==h];assert len(recorded)==len(candidates)
            for expected,actual in zip(candidates,recorded):
                for key,val in expected.items():
                    if isinstance(val,list):assert json.loads(actual[key])==val
                    else:assert actual[key]==val,(key,actual[key],val)
            for expected,actual in zip(plans,acts):
                for key in ('start','end','difficulty','action','observed_estimate'):assert expected[key]==actual[key]
                assert expected['targets']==json.loads(actual['targets'])
                for i in json.loads(actual['attendees']):last[i]=h
            assert b['spent']==end
        else:assert not acts and b['actions']==0
        assert b['spent']==b['workload']+sum(r['cost'] for r in acts)<=b['budget']
        assert b['unused']==b['budget']-b['spent']
    # Completed teacher content must match runtime skill and latent active-topic physics.
    alpha={r['student']:r['alpha'] for r in t['traits']}
    cache={}
    for r in t['teacher_learning']:
        h,i=r['homework'],r['student'];rt=runtimes[h]
        if h not in cache:
            cache[h]=np.random.default_rng(np.random.SeedSequence([draws.seed,draws.replicate,123,h])).random((MAX_TICKS,n,p.items))
        index=['instruction','explanation','corrective_feedback','guidance'].index(r['action'])
        result=content_effect(p,r['K_before'],rt.knowledge,rt.teaching_skill,np.full(p.items,r['difficulty']),cache[h][r['start'],i],
            teacher_random(draws,'retrieval',h,(4,MAX_TICKS,p.items))[index,r['start']],
            teacher_random(draws,'explanation',h,(4,MAX_TICKS,p.items))[index,r['start']])
        assert r['correct_bits']==''.join('1' if x else '0' for x in result['correct'])
        close(r['usable_fraction'],result['learner_quality'])
        c=components.get((h,r['end'],i));preceding=sum(c[x] for x in ('practice_gain','content_gain','helper_gain')) if c else 0
        close(r['gain'],(1-r['K_before']-preceding)*min(1,alpha[i]/p.attempt_learning_divisor*rt.learning_multiplier*result['learner_quality']))
    reward=s.incentives
    for r in t['teacher_rewards']+t['reward_backlog']:
        assert reward.enabled and r['due']==r['signal_homework']+reward.payment_delay
        source=next(x for x in t['teacher_observations'] if x['source_homework']==r['source_homework'] and x['source']==r['source'] and x['student']==r['student'] and x['topic']==r['topic'])
        assert r['observed']==source['observed_score']
        close(r['amount'],reward.reward_strength*source['weight']*r['observed']**reward.reward_power/(n*T))
        if 'homework' in r:assert r['homework']>=r['due']
