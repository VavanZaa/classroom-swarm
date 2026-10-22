"""A33 optional content/observed-choice fork; frozen A32 remains the comparator."""
from __future__ import annotations
import json
import math
from dataclasses import asdict, replace
import numpy as np
from .graphs import Graph
from .rng import weighted_pick
from .declared_settings import declared_grade_credit
from .tutoring_settings import TutoringParams, initial_state, tutoring_scores, task_content, content_effect
from .v4 import MAX_TICKS
from dataclasses import fields
from .declared_settings import DeclaredParams
from copy import deepcopy
from .v4 import V4Log, STREAMS, probabilities, feedback_update
from .v4_grades import grade_update
from .v4_public_ai import PublicAIDraws, contact_matrix, target_options
from .v4_corrected import BENEFIT_ACTIONS
from .teacher_settings import (TeacherSettings, TeacherObserver, plan_teacher, teacher_random, resolve_teacher)
from .v4_tutoring import simulate_tutoring, validate_tutoring_log
from .v4_teacher import simulate_teacher
from .mechanism_settings import resolve_mechanisms, incentive_plan
from .effort_runtime import stable_initial
from .promising_runtime import PromisingRuntime
from .promising_settings import resolve_promising, expand_curriculum
from .v4_effort_learning import simulate_effort
from .effort_settings import resolve_effort
from .v4_mechanisms import simulate_mechanisms

def simulate_promising(p: TutoringParams, graph: Graph, draws: PublicAIDraws,
                     condition="declared", initial=None, teacher=None, mechanisms=None, extensions=None, design=None) -> V4Log:
    p.validate()
    teacher = resolve_teacher(teacher) if isinstance(teacher, dict) or teacher is None else teacher
    if not isinstance(teacher, TeacherSettings):
        raise ValueError("teacher must be TeacherSettings or a declaration object")
    teacher.validate(p)
    settings = resolve_mechanisms(mechanisms)
    settings.validate(p, teacher)
    extension_settings = resolve_effort(extensions)
    extension_settings.validate(p, teacher, settings)
    design_settings = resolve_promising(design)
    design_settings.validate(p, teacher, settings, extension_settings)
    if not design_settings.active:
        return simulate_effort(p, graph, draws, condition, initial, teacher, settings, extension_settings)
    if not extension_settings.active:
        return simulate_mechanisms(p, graph, draws, condition, initial, teacher, settings)
    if p.tutoring_activity == 'legacy_hint':
        raise ValueError('A32 active features require joint_practice or shared_practice')
    if extension_settings.helper_contract.enabled and (not p.helper_time or p.tutoring_activity == 'shared_practice'):
        raise ValueError('helper contract requires scarce helper time and joint_practice')
    base_teacher = teacher
    if not teacher.enabled:
        teacher = replace(teacher, time_budget=0, admin_ticks=0, grading_ticks_per_student=0,
                          actions=[], observation_sources=[])
    if graph.N != p.N or draws.N != p.N or draws.M_H != p.items or draws.legacy.M_E != p.exam_items:
        raise ValueError("graph/draw dimensions do not match V4 parameters")
    n = p.N
    specs, state, traits, B, A = stable_initial(p, draws, initial, extension_settings.student_ids or list(range(n)))
    original_settings, original_extensions = settings, extension_settings
    settings, extension_settings = expand_curriculum(settings, extension_settings, traits.K0, p, design_settings.curriculum)
    settings.validate(p, teacher)
    extension_settings.validate(p, teacher, settings)
    K, C = traits.K0.copy(), state['confidence'].copy()
    control = state['control'].copy()
    quality = state['source_quality'].copy()
    skills = state['teaching_skill']
    extra_tables = ('tutoring_content','quality_feedback','initial_quality','task_content','learning_components')
    teacher_tables = ('teacher_identity', 'teacher_observations', 'teacher_observation_state',
        'teacher_queue', 'teacher_actions', 'teacher_attendance', 'teacher_learning',
        'teacher_guidance', 'teacher_workload', 'teacher_budget', 'teacher_backlog',
        'teacher_displaced_practice')
    observer = TeacherObserver(teacher, n)
    last_served = np.full(n, -1, dtype=int)
    guidance_bonus = np.zeros(n)
    admin_backlog = 0
    contacts = contact_matrix(p, graph, draws)
    public_grades = np.full(n, np.nan)
    log = V4Log({"model": "A33-v4.8-content-choice", "design": asdict(design_settings), "original_mechanisms": asdict(original_settings), "original_extensions": asdict(original_extensions), "extensions": asdict(extension_settings), "teacher": asdict(base_teacher), "mechanisms": asdict(settings), "condition": condition, "params": asdict(p),
                 "seed": draws.seed, "replicate": draws.replicate, "graph_hash": graph.edge_hash,
                 "weight_hash": graph.weight_hash, "family": graph.family, "initial": specs})
    for name in extra_tables:
        log.tables[name] = []
    for name in teacher_tables:
        log.tables[name] = []
    runtime = PromisingRuntime(settings, teacher, p, K, quality, log, extension_settings, draws, traits, design_settings)
    K = runtime.knowledge[:,0].copy()
    log.manifest['topic_count'] = runtime.count
    log.tables['teacher_identity'].append(dict(teacher=teacher.identity, role='teacher',
        knowledge=teacher.knowledge, teaching_skill=teacher.teaching_skill,
        student_count=n, included_in_student_outcomes=False))
    log.tables['initial_quality'] = [dict(requester=i, provider=j, quality=float(quality[i,j]))
        for i in range(n) for j in range(n) if i != j]
    for i in range(n):
        log.tables["traits"].append(dict(student=i, K0=float(runtime.knowledge[i].mean()), alpha=float(traits.alpha[i]),
                                         kappa=float(traits.kappa[i]), degree=graph.degree[i]))
    for (i, j), w in zip(graph.edges, graph.weights):
        log.tables["graph"].append(dict(u=i, v=j, weight=w))
    log.tables['initial_states'] = [dict(student=i, **{name: float(values[i]) for name, values in state.items() if values.ndim == 1}) for i in range(n)]
    log.tables['initial_access'] = [dict(requester=i, provider=j, hint=float(A[i,j,0]), answer=float(A[i,j,1])) for i in range(n) for j in range(n) if i != j]
    feedback_queue = []
    grade_queue = []
    shortfall, satisfaction = state['grade_shortfall'].copy(), state['grade_satisfaction'].copy()
    log.tables["homework_feedback"] = []
    log.tables["ai_uses"] = []
    log.tables["hint_receipts"] = []
    log.tables["contacts"] = [dict(u=i, v=j, closeness=float(contacts[i, j]), friend=graph.has_edge(i, j))
                              for i in range(n) for j in range(i + 1, n) if contacts[i, j] > 0]

    def return_grades(h, graded):
        for row in graded:
            runtime.homework_contract(row, h)
            i = row["student"]
            public_grades[i] = row["grade"]
            result = grade_update(B[i], C[i], row["grade"], row["credit"],
                                  row["assisted"], row["complete"], p)
            new_b, new_c, pressure, feeling = result
            log.tables["homework_feedback"].append(dict(
                homework=h, tick=row['_return_tick'], source_homework=row["homework"], student=i,
                grade=row["grade"], route=row["route"], assisted=row["assisted"],
                credit=json.dumps(row["credit"]), B_before=json.dumps(B[i].tolist()),
                B_after=json.dumps(new_b.tolist()), C_before=float(C[i]), C_after=new_c,
                shortfall_before=float(shortfall[i]), shortfall_after=pressure,
                satisfaction=feeling, K_before=float(K[i]), K_after=float(K[i])))
            B[i], C[i], shortfall[i], satisfaction[i] = new_b, new_c, pressure, feeling

    def teacher_work(h, closing=False):
        nonlocal admin_backlog
        if runtime.w.enabled:
            graded = list(runtime.returned) if closing else runtime.begin_work(h, topic, grade_queue)
            if closing: runtime.returned.clear()
            log.tables['teacher_observations'].extend(runtime.release_observers(h, draws, 0))
            for i in range(n):
                log.tables['teacher_observation_state'].append(dict(homework=h, tick=0, teacher=teacher.identity,
                    student=i, topic=topic, estimate=float(observer.estimate[i]), seen=int(observer.seen[i]), last_served=int(last_served[i])))
            return 0, graded
        previous = admin_backlog
        arrived = 0 if closing else teacher.admin_ticks
        admin_backlog += arrived
        spent = min(teacher.time_budget, admin_backlog)
        admin_backlog -= spent
        cursor = spent
        log.tables['teacher_workload'].append(dict(homework=h, teacher=teacher.identity,
            kind='admin', start=0, end=spent, cost=spent, due=previous + arrived,
            arrived=arrived, backlog_before=previous, backlog_after=admin_backlog,
            source_homework=-1, student=-1))
        due = sorted([r for r in grade_queue if r['release'] <= h],
                     key=lambda r: (r['homework'], r['student']))
        graded = []
        for row in due:
            cost = teacher.grading_cost
            if cursor + cost > teacher.time_budget or (admin_backlog and cost > 0):
                break
            log.tables['teacher_workload'].append(dict(homework=h, teacher=teacher.identity,
                kind='grading', start=cursor if cost else 0, end=cursor + cost if cost else 0, cost=cost,
                due=1, arrived=0, backlog_before=0, backlog_after=0,
                source_homework=row['homework'], student=row['student']))
            cursor += cost
            row['_return_tick'] = cursor if cost else 0
            runtime.enqueue_homework(row, h, teacher)
            graded.append(row)
            grade_queue.remove(row)
        # This plan begins after the reserved grading interval. Its observations
        # are available by cursor; student feedback is delivered at the actual tick.
        log.tables['teacher_observations'].extend(runtime.release_observers(h, draws, cursor))
        for i in range(n):
            log.tables['teacher_observation_state'].append(dict(homework=h, tick=cursor, teacher=teacher.identity,
                student=i, topic=topic, estimate=float(observer.estimate[i]), seen=int(observer.seen[i]),
                last_served=int(last_served[i])))
        return cursor, graded

    for h in range(1, p.H + 1):
        runtime.begin(h)
        topic = runtime.choose_topic(h)
        K = runtime.knowledge[:,topic].copy()
        quality = runtime.quality_for(topic)
        observer = runtime.observers[topic]
        aggregate_start = runtime.knowledge.mean(axis=1).copy()
        teacher = runtime.prepare_teacher(h,topic)
        cursor, graded = teacher_work(h)
        teacher = runtime.after_work(h,topic,teacher,cursor)
        if runtime.w.enabled:
            teacher = replace(teacher, teaching_skill=min(1., teacher.teaching_skill +
                runtime.w.preparation_quality_bonus * runtime.preparation[topic]))
        runtime.release_peers(h,0)
        return_grades(h, [row for row in graded if row['_return_tick'] == 0])
        guidance_bonus *= teacher.guidance_decay
        for fb in [x for x in feedback_queue if x["release"] == h]:
            i = fb["student"]
            cb, rb = float(C[i]), float(control[i])
            C[i], control[i] = feedback_update(cb, rb, fb["score"], fb["prediction"], p)
            log.tables["feedback"].append(dict(homework=h, student=i, exam_homework=fb["homework"],
                score=fb["score"], prediction=fb["prediction"], C_before=cb, C_after=float(C[i]),
                control_before=rb, control_after=float(control[i]), K_before=float(K[i]), K_after=float(K[i])))
        K_start, C_start = K.copy(), C.copy()
        packets = [None] * n
        estimates = np.zeros(n)
        hints = np.zeros(n)
        hint_sources = ["none"] * n
        ai_used = np.zeros(n, dtype=int)
        submitted = np.zeros(n, dtype=bool)
        busy = np.zeros(n, dtype=int)
        jobs, pending = [], {}
        sequences = [[] for _ in range(n)]
        activity_counts = np.zeros((n, 5), dtype=int)
        helpful = np.zeros(n, dtype=int)
        helper_ticks = np.zeros(n, dtype=int)
        arrays = {name: draws.tensor(name, h) for name in STREAMS}
        arrays["ai_items"] = draws.tensor("ai_items", h)
        difficulty = task_content(specs['task_difficulty'], draws, h)
        log.tables['task_content'].extend(dict(homework=h, item=m, topic=topic, difficulty=float(d)) for m,d in enumerate(difficulty))
        for name,stream in [('retrieval',123), ('explanation',124), ('checks',125)]:
            arrays[name] = np.random.default_rng(np.random.SeedSequence([draws.seed,draws.replicate,stream,h])).random((MAX_TICKS,n,p.items))
        arrays['teacher_retrieval'] = teacher_random(draws, 'retrieval', h, (4, MAX_TICKS, p.items))
        arrays['teacher_explanation'] = teacher_random(draws, 'explanation', h, (4, MAX_TICKS, p.items))
        arrays['teacher_attendance'] = teacher_random(draws, 'attendance', h, (4, MAX_TICKS, n))
        runtime.arrays(h, arrays)

        def event(i, action, start, end, before=None, after=None, occupied=True, packet=None,
                  provider=-1, extra=""):
            log.tables["events"].append(dict(homework=h, student=i, action=action, start=int(start),
                end=int(end), occupied=bool(occupied), K_before=float(K[i] if before is None else before),
                K_after=float(K[i] if after is None else after), C=float(C[i]), control=float(control[i]),
                estimate=float(estimates[i]), packet_id="" if packet is None else packet["id"],
                root=-1 if packet is None else packet["root"], depth=0 if packet is None else packet["depth"],
                provider=int(provider), detail=extra))

        def receive_hint(i, provider, strength, source, tick):
            hints[i], hint_sources[i] = strength, source
            log.tables["hint_receipts"].append(dict(homework=h, student=i, provider=int(provider),
                tick=int(tick), strength=float(strength), source=source,
                remaining=int(p.ticks - tick), usable=bool(p.ticks - tick >= p.attempt_ticks)))

        def resolve(req, finish, success, reason):
            i, j, mode = req["i"], req["j"], req["mode"]
            m = int(mode == "answer")
            before = float(A[i, j, m])
            A[i, j, m] += p.eta_access * (int(success) - A[i, j, m])
            log.tables["requests"].append(dict(homework=h, requester=i, provider=j, mode=mode,
                start=req["start"], finish=int(finish), success=bool(success), reason=reason,
                blocked_busy=req["blocked_busy"], declined=req["declined"],
                no_packet=req["no_packet"], A_before=before, A_after=float(A[i, j, m]),
                observed="delivered" if success else "unavailable",
                requester_public_grade=req["own_grade"], provider_public_grade=req["source_grade"],
                closeness=req["closeness"], research_requester_K=req["own_K"], research_provider_K=req["source_K"]))

        def complete(t):
            finishing = [job for job in jobs if job["end"] == t]
            if not finishing:
                return
            # Aggregate gains from the same frozen state, including the helper-time-free control.
            before = K.copy()
            residuals = runtime.complete_learning(h, t, topic, finishing, before, arrays, difficulty, teacher, skills)
            base_residual, practice_residual = residuals['base'], residuals['practice']
            help_residual, teacher_residual = residuals['helper'], residuals['teacher']
            fraction = 1-practice_residual*help_residual*teacher_residual
            K[:] = runtime.learn(h,t,topic,fraction,before)
            if not runtime.l.enabled:
                for job in finishing:
                    if job['kind'] == 'attempt':
                        i = job['i']; job['response_probability'] = float(K[i] + p.hint_performance_multiplier * job['hint'] * (1 - K[i]))
                    elif job['kind'] in {'guided', 'shared'}:
                        i = job['i']; job['response_probability'] = float(K[i] + p.content_performance_multiplier * job['content']['learner_quality'] * (1 - K[i]))
            for i in range(n):
                if base_residual[i] < 1 or help_residual[i] < 1 or teacher_residual[i] < 1:
                    log.tables['learning_components'].append(dict(homework=h,tick=t,student=i,
                        K_before=float(before[i]),K_after=float(K[i]),
                        practice_gain=float((1-before[i])*(1-base_residual[i])),
                        content_gain=float((1-before[i])*(base_residual[i]-practice_residual[i])),
                        helper_gain=float((1-before[i])*practice_residual[i]*(1-help_residual[i])),
                        teacher_gain=float((1-before[i])*practice_residual[i]*help_residual[i]*(1-teacher_residual[i]))))
            for job in finishing:
                i, kind, start = job["i"], job["kind"], job["start"]
                if kind == 'teacher':
                    plan = job['plan']
                    last_served[i] = h
                    if plan['action'] == 'followup':
                        before_cost = float(runtime.followup[i])
                        runtime.followup[i] += runtime.tp.followup_cost_reduction
                        log.tables['teacher_followup'].append(dict(homework=h, student=i, start=start, end=t,
                            before=before_cost, after=float(runtime.followup[i]), K_before=float(before[i]), K_after=float(K[i])))
                    elif plan['action'] == 'guidance':
                        cb, gb = float(C[i]), float(guidance_bonus[i])
                        C[i] += teacher.guidance_confidence_rate * (plan['observed_estimate'] - C[i])
                        guidance_bonus[i] = min(1., guidance_bonus[i] + teacher.guidance_strength * (1 - plan['observed_estimate']))
                        log.tables['teacher_guidance'].append(dict(homework=h, teacher=teacher.identity,
                            action_id=plan['action_id'], student=i, start=start, end=t,
                            observed_estimate=plan['observed_estimate'], C_before=cb, C_after=float(C[i]),
                            bonus_before=gb, bonus_after=float(guidance_bonus[i]),
                            K_before=float(before[i]), K_after=float(K[i])))
                    else:
                        result = job['content']
                        component = next(r for r in reversed(log.tables['learning_components'])
                            if r['homework'] == h and r['tick'] == t and r['student'] == i) if teacher_residual[i] < 1 else None
                        log.tables['teacher_learning'].append(dict(homework=h, teacher=teacher.identity,
                            action_id=plan['action_id'], student=i, action=plan['action'], start=start, end=t,
                            difficulty=plan['difficulty'], usable_fraction=result['learner_quality'],
                            correct_bits=''.join('1' if x else '0' for x in result['correct']),
                            novel_bits=''.join('1' if x else '0' for x in result['novel']),
                            transfer=json.dumps(result['transfer'].tolist()),
                            K_before=float(before[i]), K_after=float(K[i]),
                            gain=0. if component is None else component['teacher_gain']))
                    event(i, 'teacher_' + plan['action'], start, t, before[i], K[i],
                          extra=plan['action_id'])
                elif kind in {'guided','shared'}:
                    j = job['j']
                    result = job['content']
                    q = result['learner_quality']
                    prob = job['response_probability']
                    bits = arrays['items'][start,i] < prob
                    packet = dict(id=f'guided-h{h}-i{i}-t{start}',root=i,depth=0,bits=bits,
                        assisted=j>=0,copied=False,via='attempt',origin='peer_guided_attempt' if j>=0 else 'student')
                    parent = '' if packets[i] is None else packets[i]['id']
                    packets[i] = packet
                    estimates[i] = float(min(1., C[i]+p.perceived_hint_boost*quality[i,j]*(1-C[i]))) if j>=0 else float(C[i])
                    log.tables['packets'].append(dict(homework=h,student=i,tick=t,packet_id=packet['id'],
                        parent_id=parent,root=i,probability=prob,assisted=j>=0,
                        item_bits=''.join('1' if x else '0' for x in bits),origin=packet['origin'],hint_source='peer' if j>=0 else 'none'))
                    event(i, 'guided_practice' if j>=0 else 'scheduled_practice', start,t,before[i],K[i],packet=packet,provider=j)
                    if j>=0:
                        coverage = settings.peer_observation.coverage if settings.peer_observation.enabled else 1.
                        checks = arrays['checks'][start,i] < p.quality_check_probability*coverage
                        runtime.peer_signal(h,t,start,i,j,topic,result['correct'],checks,draws)
                        runtime.release_peers(h,t)
                        log.tables['tutoring_content'].append(dict(homework=h,requester=i,provider=j,topic=topic,start=start,end=t,
                            protocol=kind,correct_fraction=float(np.mean(result['correct'])),
                            novel_fraction=float(np.mean(result['novel'])),usable_fraction=q,
                            helper_fraction=result['helper_quality'],provider_skill=float(skills[j]),
                            correct_bits=''.join('1' if x else '0' for x in result['correct']),
                            novel_bits=''.join('1' if x else '0' for x in result['novel']),
                            transfer=json.dumps(result['transfer'].tolist())))
                        helpful[j] += 1
                        # Shared explaining occurs inside the helper's own practice interval.
                        if kind == 'guided':
                            helper_ticks[j] += t-start
                            event(j,'help_guided',start,t,before[j],K[j],occupied=p.helper_time,provider=i)
                            resolve(job['request'],t,True,'guided_practice_completed')
                            if job.get('contract_session'):
                                log.tables['helper_sessions'].append(dict(homework=h, helper=j, recipient=i, start=start, end=t,
                                    helper_effort=job['helper_effort'], recipient_effort=job['effort'], completed=True))
                elif kind == "attempt":
                    hint = job["hint"]
                    # A26: credit the tutor by the hint's source, so a zero-strength tutor is learnable.
                    ai_guided = job["hint_source"] == "ai" and (p.tutor_credit_by_source or hint > 0)
                    prob = job['response_probability']
                    bits = arrays["items"][start, i] < prob
                    packet = dict(id=f"h{h}-i{i}-t{start}", root=i, depth=0,
                                  bits=bits, assisted=hint > 0, copied=False, via="attempt",
                                  origin="ai_tutor_attempt" if ai_guided else "student")
                    parent = "" if packets[i] is None else packets[i]["id"]
                    packets[i] = packet
                    estimates[i] = min(1., C[i] + (p.perceived_hint_boost * (1 - C[i]) if hint > 0 else 0))
                    log.tables["packets"].append(dict(homework=h, student=i, tick=t, packet_id=packet["id"],
                        parent_id=parent, root=i, probability=prob, assisted=bool(hint > 0),
                        item_bits="".join("1" if x else "0" for x in bits), origin=packet["origin"],
                        hint_source=job["hint_source"]))
                    event(i, "attempt", start, t, before[i], K[i], packet=packet)
                elif kind in {"ai_answer", "ai_tutor"}:
                    packet = None
                    if kind == "ai_answer":
                        bits = arrays["ai_items"][start, i] < p.ai_accuracy
                        packet = dict(id=f"ai-h{h}-i{i}-t{start}", root=-1, depth=0, bits=bits,
                                      assisted=True, copied=True, origin="ai_answer", via="ai")
                        parent = "" if packets[i] is None else packets[i]["id"]
                        packets[i] = packet
                        estimates[i] = float(B[i, 3])
                        log.tables["packets"].append(dict(homework=h, student=i, tick=t, packet_id=packet["id"],
                            parent_id=parent, root=-1, probability=p.ai_accuracy, assisted=True,
                            item_bits="".join("1" if x else "0" for x in bits), origin="ai_answer", hint_source="none"))
                    else:
                        receive_hint(i, -1, p.ai_hint_strength, "ai", t)
                    log.tables["ai_uses"].append(dict(homework=h, student=i, mode=kind, start=start, end=t,
                        K_before=float(before[i]), K_after=float(K[i]),
                        packet_id="" if packet is None else packet["id"],
                        accuracy=p.ai_accuracy if kind == "ai_answer" else None,
                        hint_strength=p.ai_hint_strength if kind == "ai_tutor" else None))
                    event(i, kind + "_receive", start, t, before[i], K[i], packet=packet)
                elif kind in {"hint", "answer"}:
                    j = job["j"]
                    if kind == "hint":
                        receive_hint(i, j, job["strength"], "peer", t)
                        event(i, "hint_receive", start, t, before[i], K[i], provider=j)
                    else:
                        src = job["source"]
                        packets[i] = dict(src, depth=src["depth"] + 1, assisted=True, copied=True, via="peer")
                        estimates[i] = job["request"]["expected_grade"]
                        event(i, "answer_receive", start, t, before[i], K[i], packet=packets[i], provider=j)
                    event(j, "help_" + kind, start, t, before[j], K[j], occupied=p.helper_time,
                          packet=job.get("source"), provider=i)
                    helpful[j] += 1
                    helper_ticks[j] += t - start
                    resolve(job["request"], t, True, "delivered")
                elif kind in {'format_practice', 'concept_revision'}:
                    event(i, kind, start, t, before[i], K[i])
                elif kind == "submit":
                    submitted[i] = True
                    event(i, "submit", start, t, before[i], K[i], packet=packets[i])
                else:
                    event(i, "wait", start, t, before[i], K[i])
            jobs[:] = [job for job in jobs if job["end"] != t]

        if runtime.w.enabled:
            plans, queue, teacher_end, candidates = runtime.teacher_plan(teacher, observer.estimate,
                observer.seen, last_served, h, topic, len(grade_queue) + n)
        else:
            plans, queue, teacher_end, candidates = incentive_plan(settings.incentives,teacher,p,
                observer.estimate,observer.seen,last_served,h,cursor,runtime.fatigue)
        for row in candidates:
            log.tables['incentive_candidates'].append({**row,'topic':topic,
                'estimates':json.dumps(row['estimates']),'predicted_after':json.dumps(row['predicted_after'])})
        runtime.after_teaching(h,teacher_end-cursor)
        for row in queue:
            log.tables['teacher_queue'].append({**row, 'targets': json.dumps(row['targets']),
                                               'seen': json.dumps(row['seen'])})
        reservations = [[] for _ in range(n)]
        for plan in plans:
            attended = []
            action_index = ['instruction', 'explanation', 'corrective_feedback', 'guidance', 'coaching', 'followup'].index(plan['action'])
            attendance = arrays['teacher_attendance']
            for i in plan['targets']:
                yes = bool(attendance[action_index, plan['start'], i] < teacher.participation_probability)
                log.tables['teacher_attendance'].append(dict(homework=h, teacher=teacher.identity,
                    action_id=plan['action_id'], student=i, start=plan['start'], end=plan['end'], attended=yes))
                if yes:
                    attended.append(i)
                    reservations[i].append(plan)
            log.tables['teacher_actions'].append({**plan, 'targets': json.dumps(plan['targets']),
                'seen': json.dumps(plan['seen']), 'attendees': json.dumps(attended), 'status': 'completed',
                'cost': plan['end'] - plan['start']})
        log.tables['teacher_budget'].append(dict(homework=h, teacher=teacher.identity,
            budget=teacher.time_budget, workload=cursor, actions=teacher_end-cursor,
            spent=teacher_end, unused=teacher.time_budget-teacher_end,
            admin_backlog=admin_backlog, grading_backlog=len(grade_queue)))
        shared_start = teacher_end if p.tutoring_activity == 'shared_practice' else None
        shared_fits = shared_start is not None and shared_start + p.guided_practice_ticks <= p.ticks
        if shared_start is not None and not shared_fits:
            log.tables['teacher_displaced_practice'].append(dict(homework=h, students=n,
                planned_start=shared_start, duration=p.guided_practice_ticks, reason='deadline'))

        def remaining_before_teacher(i, tick):
            return min([p.ticks-tick] + [r['start']-tick for r in reservations[i] if r['start'] >= tick])

        for t in range(p.ticks):
            runtime.release_peers(h,t)
            complete(t)
            if t > 0:
                return_grades(h, [row for row in graded if row['_return_tick'] == t])
            for i in range(n):
                for plan in reservations[i]:
                    if plan['start'] == t:
                        assert busy[i] <= t
                        if i in pending:
                            resolve(pending.pop(i), t, False, 'teacher_appointment')
                        job = dict(i=i, kind='teacher', start=t, end=plan['end'], plan=plan)
                        runtime.start_job(job, h, topic, C[i])
                        jobs.append(job)
                        busy[i] = plan['end']
                        sequences[i].append('teacher_' + plan['action'])
            if shared_fits and t == shared_start:
                shared_jobs = []
                for i in range(n):
                    ids = [j for j in range(n) if j!=i and contacts[i,j]>0]
                    ws = [float(contacts[i,j]**p.relationship_strength * max(1e-12,quality[i,j])**p.quality_target_weight) for j in ids]
                    j = weighted_pick(ids,ws,float(arrays['target'][t,i])) if p.allow_hint and ids else -1
                    job = dict(i=i,j=j,kind='shared',start=t,end=t+p.guided_practice_ticks)
                    shared_jobs.append(job)
                    busy[i] = t+p.guided_practice_ticks
                    activity_counts[i,0] += 1
                    if j>=0:
                        activity_counts[i,1] += 1
                    sequences[i].append('shared_practice' if j>=0 else 'scheduled_practice')
                if runtime.l.enabled:
                    full_effort = [runtime.best_effort(i, 'guided', p.guided_practice_ticks, C[i],
                        assistance=.25, future=runtime.student_traits['future_test_value'][i], h=h, t=t)[0] for i in range(n)]
                    serving = np.bincount([job['j'] for job in shared_jobs if job['j'] >= 0], minlength=n)
                    fatigue_snapshot = runtime.student_fatigue.copy()
                    for job in shared_jobs:
                        i, j = job['i'], job['j']; share = runtime.l.shared_explanation_share if serving[i] else 0.
                        job.update(effort=full_effort[i] * (1 - share), paid_effort=full_effort[i])
                        if j >= 0:
                            job.update(helper_effort=full_effort[j] * runtime.l.shared_explanation_share,
                                helper_dose_weight=1 / serving[j], provider_fatigue=float(fatigue_snapshot[j]))
                for job in shared_jobs:
                    runtime.start_job(job, h, topic, C[job['i']]); jobs.append(job)
            if shared_start is not None and t < shared_start:
                for i in range(n):
                    if busy[i] <= t:
                        event(i, 'teacher_phase_wait', t, t+1)
                        busy[i] = t+1
            for job in runtime.offers(h, t, remaining_before_teacher, busy, pending, submitted, C, topic):
                jobs.append(job); i, j = job['i'], job['j']
                busy[i] = busy[j] = job['end']; activity_counts[i, 0] += 1; activity_counts[i, 1] += 1
                sequences[i].append('contract_guided_practice')
            used_helpers = set()
            # Requests created in a previous tick compete for currently free partners.
            for i in sorted(list(pending), key=lambda x: (arrays["priority"][t, x], x)):
                req = pending[i]
                j, mode = req["j"], req["mode"]
                if t < req['start'] + p.peer_request_ticks:
                    continue
                duration = p.guided_practice_ticks if mode == "hint" else p.peer_answer_ticks
                # A26: a hint is only served if a full attempt still fits, as the AI tutor already requires.
                tail = 0  # practice is inside a completed guided session
                eligible = busy[j] <= t and j not in pending and j not in used_helpers
                reason = "busy"
                if not eligible:
                    req["blocked_busy"] += 1
                elif mode == "answer" and packets[j] is None:
                    req["no_packet"] += 1
                    reason = "no_packet"
                    eligible = False
                if eligible and duration + tail <= remaining_before_teacher(i, t) and duration <= remaining_before_teacher(j, t):
                    base = p.willingness
                    if base in (0., 1.):
                        willingness = base
                    else:
                        urgency = 0. if submitted[j] else t / p.ticks
                        z = math.log(base / (1 - base)) + p.reciprocity * (A[j, i, int(mode == "answer")] - p.reciprocity_reference)
                        willingness = 1 / (1 + math.exp(-z + p.urgency_cost * urgency))
                    if mode == 'hint' and runtime.hc.enabled:
                        marginal = runtime.helper_value(j, i) + runtime.hc.helper_intrinsic_value - runtime.cost(j, 'helper', 1., duration)
                        willingness = 1. if marginal >= 0 else willingness
                    if arrays["accept"][t, i] < willingness:
                        job = dict(i=i, j=j, kind="guided" if mode=="hint" else mode, start=t, end=t + duration, request=req,
                                   strength=float(p.peer_hint_base + p.peer_hint_knowledge_weight * K[j]))
                        if mode == "answer":
                            job["source"] = dict(packets[j])
                        job['helper_belief'] = float(C[j])
                        runtime.start_job(job, h, topic, C[i], helper=mode == 'hint')
                        jobs.append(job)
                        if mode == 'hint':
                            activity_counts[i, 0] += 1  # completed joint practice is an attempt
                        busy[i] = t + duration
                        if p.helper_time:
                            busy[j] = t + duration
                        used_helpers.add(j)
                        del pending[i]
                        continue
                    req["declined"] += 1
                    reason = "declined"
                elif eligible:
                    reason = "deadline"
                event(i, "waiting", t, t + 1)
                busy[i] = t + 1
                if t - req["start"] >= p.request_timeout_ticks or t == p.ticks - 1:
                    resolve(req, t + 1, False, reason)
                    del pending[i]

            for i in range(n):
                if busy[i] > t or i in pending or submitted[i]:
                    continue
                pools, target_weights, access = [], [], []
                for mode in ("hint", "answer"):
                    ids, ws = target_options(i, mode, contacts, A, public_grades, p)
                    pools.append(ids); target_weights.append(ws)
                    if mode == 'hint':
                        ws = [w*max(1e-12,quality[i,j])**p.quality_target_weight for j,w in zip(ids,ws)]
                        target_weights[-1] = ws
                    m = int(mode == "answer")
                    access.append(float(np.dot(ws, [A[i, j, m] for j in ids]) / sum(ws)) if ws else 0.)
                peer_prediction = float(B[i, 2])
                if pools[1] and np.isfinite(public_grades[i]):
                    observed = float(np.dot(target_weights[1], public_grades[pools[1]]) / sum(target_weights[1]))
                    peer_prediction = (1 - p.public_signal) * peer_prediction + p.public_signal * observed
                for j in pools[0]:
                    log.tables['quality_choice_state'].append(dict(homework=h,tick=t,requester=i,provider=j,topic=topic,quality=float(quality[i,j])))
                expected_quality = float(np.average(quality[i,pools[0]], weights=target_weights[0])) if target_weights[0] else .5
                scores = tutoring_scores(p, C[i], control[i], B[i], traits.kappa[i], estimates[i],
                    packets[i] is not None, hints[i] > 0, access, bool(pools[0]), bool(pools[1]), remaining_before_teacher(i, t),
                    shortfall=float(shortfall[i]), peer_prediction=peer_prediction,
                    ai_available=h >= p.ai_start and ai_used[i] < p.max_ai_uses, quality=expected_quality)
                if p.tutoring_activity == 'shared_practice':
                    scores.pop('hint',None)
                scores, effort_choices = runtime.choices(scores, i, h, t, float(C[i]), float(estimates[i]),
                    float(hints[i]) if hints[i] > 0 else p.perceived_hint_boost * expected_quality,
                    hints[i] > 0, remaining_before_teacher(i, t))
                if 'attempt' in scores: scores['attempt'] += guidance_bonus[i]
                names, prob = probabilities(scores, p)
                index = min(len(names) - 1, int(np.searchsorted(np.cumsum(prob), arrays["choice"][t, i], side="right")))
                action = names[index]
                event(i, "choose_" + action, t, t, occupied=False,
                      extra=json.dumps({"scores": {k: float(v) for k, v in scores.items()},
                                        "probabilities": dict(zip(names, map(float, prob))),
                                        "grade_shortfall": float(shortfall[i]),
                                        "teacher_guidance_bonus": float(guidance_bonus[i]),
                                        "answer_pressure_bonus": float(p.grade_response * shortfall[i]) if "answer" in scores else 0.,
                                        "ai_answer_pressure_bonus": float(p.grade_response * shortfall[i]) if "ai_answer" in scores else 0.,
                                        "eligible_answer_sources": pools[1]}, sort_keys=True))
                sequences[i].append(action)
                if action in BENEFIT_ACTIONS:
                    activity_counts[i, BENEFIT_ACTIONS.index(action)] += 1
                if action in {"hint", "answer"}:
                    mode = int(action == "answer")
                    target = weighted_pick(pools[mode], target_weights[mode], float(arrays["target"][t, i]))
                    pending[i] = dict(i=i, j=target, mode=action, start=t,
                                      blocked_busy=0, declined=0, no_packet=0,
                                      own_grade=float(public_grades[i]) if np.isfinite(public_grades[i]) else None,
                                      source_grade=float(public_grades[target]) if np.isfinite(public_grades[target]) else None,
                                      closeness=float(contacts[i, target]), own_K=float(K[i]), source_K=float(K[target]),
                                      expected_grade=float((1 - p.public_signal) * B[i, 2] + p.public_signal * public_grades[target])
                                                     if np.isfinite(public_grades[target]) else float(B[i, 2]))
                    busy[i] = t + p.peer_request_ticks
                    event(i, "request_" + action, t, t + p.peer_request_ticks, provider=target)
                else:
                    duration = {"attempt": p.attempt_ticks, "wait": min(p.wait_ticks, remaining_before_teacher(i, t)), "submit": p.submit_ticks,
                                "ai_answer": p.ai_answer_ticks, "ai_tutor": p.ai_tutor_ticks,
                                "format_practice": runtime.tp.practice_ticks, "concept_revision": runtime.tp.practice_ticks}[action]
                    if action in {"ai_answer", "ai_tutor"}:
                        ai_used[i] += 1
                    job = dict(i=i, kind=action, start=t, end=t + duration, hint=float(hints[i]),
                        hint_source=hint_sources[i], effort=effort_choices.get(action, 0. if action in {'wait','submit','ai_answer','ai_tutor'} else 1.))
                    runtime.start_job(job, h, topic, C[i])
                    jobs.append(job)
                    if action == "attempt":
                        hints[i], hint_sources[i] = 0, "none"
                    busy[i] = t + duration
        runtime.release_peers(h,p.ticks)
        complete(p.ticks)
        return_grades(h, [row for row in graded if row['_return_tick'] == p.ticks])
        assert not jobs and not pending
        for i in range(n):
            packet = packets[i]
            grade = 0. if packet is None else float(np.mean(packet["bits"]))
            used = activity_counts[i]
            credit, route = declared_grade_credit(packet, used, p)
            grade_queue.append(dict(homework=h, release=h + 1, student=i, topic=topic, grade=grade,
                credit=credit.tolist(), route=route, complete=packet is not None,
                assisted=bool(packet and packet["assisted"])))
            log.tables["students"].append(dict(homework=h, student=i, topic=topic,
                K_before=float(aggregate_start[i]), K=float(runtime.knowledge[i].mean()),
                K_active_before=float(K_start[i]), K_active=float(K[i]), C_before=float(C_start[i]), C=float(C[i]), control=float(control[i]),
                grade=grade, complete=packet is not None, copied=bool(packet and packet["copied"]),
                assisted=bool(packet and packet["assisted"]), packet_id="" if packet is None else packet["id"],
                root=-1 if packet is None else packet["root"], depth=0 if packet is None else packet["depth"],
                attempt=int(used[0]), hint=int(used[1]), answer=int(used[2]), check=0,
                help_count=int(helpful[i]), helper_ticks=int(helper_ticks[i]),
                mixed=bool(np.count_nonzero(used) >= 2), sequence=">".join(sequences[i]),
                B_attempt=float(B[i, 0]), B_hint=float(B[i, 1]), B_answer=float(B[i, 2]), B_check=0.,
                grade_shortfall=float(shortfall[i]), grade_satisfaction=float(satisfaction[i]),
                B_ai_answer=float(B[i, 3]), B_ai_tutor=float(B[i, 4]),
                ai_answer=int(used[3]), ai_tutor=int(used[4]), final_route=route,
                peer_copied=bool(packet and packet["via"] == "peer"),
                direct_ai_answer=bool(packet and packet["via"] == "ai"),
                ai_answer_origin=bool(packet and packet["origin"] == "ai_answer")))
        for i in range(n):
            for k in range(runtime.count):
                log.tables['topic_states'].append(dict(homework=h,student=i,topic=k,knowledge=float(runtime.knowledge[i,k])))
        if runtime.w.enabled:
            runtime.end_work(h, grade_queue)
            runtime.resources(h)
            budget_row = log.tables['teacher_budget'][-1]
            resource_row = log.tables['teacher_resources'][-1]
            budget_row.update(budget=runtime.w.total_budget, workload=resource_row['before'] + resource_row['after'],
                actions=resource_row['classroom'], spent=resource_row['spent'], unused=resource_row['unused'])
        if h % p.exam_every == 0:
            runtime.assess(h, C, teacher, feedback_queue)
    runtime.release_payments(p.H + 1)
    teacher=runtime.prepare_teacher(p.H+1,topic,closing=True)
    closing_cost, graded = teacher_work(p.H + 1, closing=True)
    teacher=runtime.after_work(p.H+1,topic,teacher,closing_cost)
    runtime.after_teaching(p.H+1,0)
    return_grades(p.H + 1, graded)
    runtime.release_payments(p.H + 1)
    log.tables['teacher_budget'].append(dict(homework=p.H+1, teacher=teacher.identity,
        budget=teacher.time_budget, workload=closing_cost, actions=0, spent=closing_cost,
        unused=teacher.time_budget-closing_cost, admin_backlog=admin_backlog, grading_backlog=len(grade_queue)))
    if runtime.w.enabled:
        log.tables['teacher_budget'][-1].update(budget=0, workload=0, actions=0, spent=0, unused=0)
    for row in grade_queue:
        log.tables['teacher_backlog'].append(dict(kind='grading', student=row['student'],
            source='', source_homework=row['homework'], due=row['release'], amount=1))
    if admin_backlog:
        log.tables['teacher_backlog'].append(dict(kind='admin', student=-1, source_homework=-1,
            source='', due=p.H+1, amount=admin_backlog))
    for k,ob in enumerate(runtime.observers):
        for row in ob.queue:
            log.tables['teacher_backlog'].append(dict(kind='observation', student=row['student'],topic=k,
                source=row['source'],source_homework=row['source_homework'],due=row['release'],amount=1))
    runtime.close()
    return log


from .promising_validation import validate_promising_log
