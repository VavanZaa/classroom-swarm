"""A32 effort, resource and assessment physics; decisions receive private observations."""
from dataclasses import asdict, replace
import json
import math
import numpy as np
from .distributions import sample_distribution
from .tutoring_settings import resolve_initial, content_effect
from .v3 import TraitState
from .v4 import MAX_TICKS, probabilities
from .mechanism_runtime import MechanismRuntime
from .teacher_settings import TeacherObserver
from .effort_settings import contract_value

# Fixed, private semantic codes, independent of consumption order. Student IDs are
# global identities; opportunity keys use dates/ticks, never completed-event counts.
STREAMS32 = {'initial': 140, 'traits': 141, 'attention': 142, 'distraction': 143,
    'processing': 144, 'effort': 145, 'exam': 146, 'participation': 147,
    'baseline': 148, 'helper_boundary': 149, 'helper_tie': 150, 'helper_accept': 151,
    'choice': 152, 'target': 153, 'accept': 154, 'priority': 155, 'items': 156,
    'ai_items': 157, 'retrieval': 158, 'explanation': 159, 'checks': 160,
    'teacher_attendance': 161, 'observation_coverage': 162, 'observation_noise': 163,
    'peer_error': 164}
TABLES32 = ('effort_initial', 'effort_choices', 'learning_doses', 'student_costs',
    'student_fatigue', 'material_exposure', 'teacher_work_schedule', 'teacher_preparation',
    'teacher_forecasts', 'contract_observations', 'contract_payments', 'contract_backlog',
    'helper_eligibility', 'helper_offers', 'helper_sessions', 'helper_checkpoints',
    'helper_payments', 'helper_payment_backlog', 'format_initial', 'format_learning',
    'format_states', 'assessment_design', 'assessment_items', 'assessment_scores',
    'exam_participation', 'teacher_followup', 'teacher_resources', 'teacher_baseline', 'task_responses')


def semantic(draws, code, identity, *key, size=None, normal=False):
    rng = np.random.default_rng(np.random.SeedSequence([draws.seed, draws.replicate, code, identity, *key]))
    return rng.standard_normal(size) if normal else rng.random(size)


def stable_initial(p, draws, initial, ids):
    specs = resolve_initial(p, initial); state = {}
    for index, name in enumerate(sorted(specs)):
        if name == 'task_difficulty': continue
        spec = specs[name]
        if spec == {'kind': 'from_knowledge'}: continue
        if name.startswith('access_') or name == 'source_quality':
            z = np.array([[semantic(draws, 140, i, index, j, normal=True) for j in ids] for i in ids])
        else:
            z = np.array([semantic(draws, 140, i, index, normal=True) for i in ids])
        state[name] = sample_distribution(spec, z, low=-1 if name == 'grade_satisfaction' else 0,
            high=None if name in ('learning_efficiency', 'effort_aversion') else 1,
            strict_low=name == 'learning_efficiency' or name.startswith('access_'))
    for name, spec in specs.items():
        if spec == {'kind': 'from_knowledge'}: state[name] = state['knowledge'].copy()
    traits = TraitState(state['knowledge'], state['learning_efficiency'], state['effort_aversion'])
    B = np.column_stack([state['benefit_' + a] for a in ('attempt', 'hint', 'answer', 'ai_answer', 'ai_tutor')])
    A = np.stack([state['access_hint'], state['access_answer']], axis=2)
    return specs, state, traits, B, A


class StableObserver(TeacherObserver):
    def __init__(self, settings, n, ids):
        super().__init__(settings, n); self.ids = ids

    def release(self, homework, draws, tick=0):
        s = self.settings; rows = []
        for item in sorted([q for q in self.queue if (q['release'], q['release_tick']) <= (homework, tick)],
                key=lambda q: (q['release'], q['release_tick'], q['source_homework'], q['source'], q['student'])):
            i = item['student']; source = int(item['source'] == 'exam')
            coverage = semantic(draws, 162, self.ids[i], item['source_homework'], source)
            noise = semantic(draws, 163, self.ids[i], item['source_homework'], source, normal=True)
            observed = float(np.clip(item['score'] + s.observation_noise_std * noise, 0, 1)) if coverage < s.observation_coverage else None
            weight = s.assisted_observation_weight if item['assisted'] else 1.
            before = float(self.estimate[i])
            if observed is not None and weight > 0:
                self.estimate[i] += s.observation_learning_rate * weight * (observed - self.estimate[i]); self.seen[i] += 1
            rows.append(dict(homework=homework, tick=item['release_tick'] if item['release'] == homework else 0,
                teacher=s.identity, **item, observed_score=observed, weight=weight,
                estimate_before=before, estimate_after=float(self.estimate[i]), seen=int(self.seen[i])))
            self.queue.remove(item)
        return rows


def dose_fraction(alpha, divisor, multiplier, dose):
    theta = min(1., alpha / divisor)
    if dose <= 0 or multiplier <= 0 or theta <= 0: return 0.
    if theta == 1: return 1.
    return float(-math.expm1(math.log1p(-theta) * multiplier * dose))


class EffortRuntime(MechanismRuntime):
    def __init__(self, settings, base, p, k, quality, log, extensions, draws, traits):
        super().__init__(settings, base, p, k, quality, log)
        self.x, self.draws, self.traits = extensions, draws, traits
        self.ids = extensions.student_ids or list(range(p.N))
        self.observers = [StableObserver(base, p.N, self.ids) for _ in range(self.count)]
        for name in TABLES32: log.tables[name] = []
        self.l, self.w, self.hc, self.tp = (getattr(extensions, key) for key in
            ('learning_process', 'teacher_work', 'helper_contract', 'test_preparation'))
        self.student_traits = {}
        for index, name in enumerate(('attention', 'distraction', 'fatigue_sensitivity', 'future_test_value', 'fatigue_initial')):
            z = np.array([semantic(draws, 141, identity, index, normal=True) for identity in self.ids])
            self.student_traits[name] = sample_distribution(getattr(self.l, name), z, low=0,
                high=None if name == 'future_test_value' else 1)
        z = np.array([semantic(draws, 141, identity, 5, normal=True) for identity in self.ids])
        self.reward_preference = sample_distribution(self.hc.reward_preference, z, low=0, high=None)
        self.student_fatigue = self.student_traits['fatigue_initial'].copy()
        self.preparation = np.full(self.count, self.w.preparation_initial)
        self.formats = np.array(self.tp.initial_format, float) if self.tp.initial_format else np.zeros((p.N, len(self.tp.forms)))
        self.form_transfer = np.array(self.tp.format_transfer, float) if self.tp.format_transfer else np.eye(len(self.tp.forms))
        self.followup = np.zeros(p.N)
        self.baseline = np.array(self.hc.baseline_scores, float) if self.hc.baseline_scores else np.array([
            np.mean(semantic(draws, 148, identity, size=p.exam_items) < self.knowledge[i].mean()) for i, identity in enumerate(self.ids)])
        self.progress = np.zeros(p.N); self.released_cutoff = 0.
        self.helper_pending = []; self.contract_pending = []; self.contract_evidence = []
        self.teacher_baseline = {}; self.homework_evidence = {}; self.productivity = self.w.belief_gain_rate
        self.returned = []; self.remaining_total = 0; self.work_end = 0; self.after_remaining = 0
        for i in range(p.N):
            log.tables['effort_initial'].append(dict(student=i, student_id=self.ids[i],
                **{key: float(v[i]) for key, v in self.student_traits.items()}, reward_preference=float(self.reward_preference[i])))
            for f, name in enumerate(self.tp.forms):
                log.tables['format_initial'].append(dict(student=i, form=name, familiarity=float(self.formats[i, f])))
        for helper, recipient in self.hc.pairs:
            log.tables['helper_eligibility'].append(dict(helper=helper, recipient=recipient,
                helper_id=self.ids[helper], recipient_id=self.ids[recipient], baseline=float(self.baseline[recipient]),
                form=self.hc.form, frozen=True))
        from .effort_settings import default_exams
        self.designs = self.tp.exams if self.tp.enabled and self.tp.exams else default_exams(self.tp, self.count)
        log.tables['assessment_design'] = [{**d, 'topic_weights': json.dumps(d['topic_weights'])} for d in self.designs]
        for design_index, design in enumerate(self.designs):
            for i in range(p.N):
                probability = float(np.clip(np.dot(self.knowledge[i], design['topic_weights']) + .5 - design['difficulty'], 0, 1))
                score = float(np.mean(self.uniform('baseline', i, design_index + 1, size=p.exam_items) < probability))
                if design['form'] in self.w.contract.baseline_scores: score = self.w.contract.baseline_scores[design['form']][i]
                self.teacher_baseline[i, design['form']] = score
                log.tables['teacher_baseline'].append(dict(student=i, form=design['form'], observed_score=score,
                    source='pre_intervention_unaided_assessment'))
        for i, score in enumerate(self.w.contract.baseline_scores.get('homework', [])):
            self.teacher_baseline[i, 'homework'] = score
            log.tables['teacher_baseline'].append(dict(student=i, form='homework', observed_score=score, source='declared_observed_baseline'))
        if self.hc.enabled and not self.hc.baseline_scores:
            self.baseline = np.array([self.teacher_baseline[i, self.hc.form] for i in range(p.N)])
            for row in log.tables['helper_eligibility']: row['baseline'] = float(self.baseline[row['recipient']])

    def uniform(self, name, i, *key, size=None):
        return semantic(self.draws, STREAMS32[name], self.ids[i], *key, size=size)

    def learn(self, h, t, topic, fraction, before):
        start = len(self.log.tables['topic_learning'])
        result = super().learn(h, t, topic, fraction, before)
        for row in self.log.tables['topic_learning'][start:]:
            ids = [r['event_id'] for r in self.log.tables['learning_doses'] if r['homework'] == h
                and r['end'] == t and r['student'] == row['student'] and r['fraction'] > 0]
            row['source_event_ids'] = json.dumps(ids)
        return result

    def peer_signal(self, h, t, start, i, j, topic, correct, checks, draws):
        o = self.settings.peer_observation; checks = np.asarray(checks, bool)
        u = self.uniform('peer_error', i, h, start, self.ids[j], size=self.p.items)
        observed = np.where(correct, u < o.sensitivity, u >= o.specificity) if o.enabled else np.asarray(correct, bool)
        stamp = (h - 1) * self.p.ticks + t + (o.delay_ticks if o.enabled else 0)
        signal = dict(homework=h, requester=i, provider=j, topic=topic, start=start, source_tick=t,
            release_absolute=stamp, checked_items=int(checks.sum()), correct_checked=int(np.sum(correct & checks)),
            observed_quality=float(np.mean(observed[checks])) if np.any(checks) else None,
            observed_bits=''.join('1' if bit else '0' for bit in observed[checks]))
        self.log.tables['peer_signals'].append(signal.copy())
        if np.any(checks): self.peer_queue.append(signal)
        return signal

    def arrays(self, h, arrays):
        for name in ('choice', 'target', 'accept', 'priority', 'items', 'ai_items', 'retrieval', 'explanation', 'checks'):
            shape = (MAX_TICKS, self.p.items) if name in ('items', 'ai_items', 'retrieval', 'explanation', 'checks') else (MAX_TICKS,)
            arrays[name] = np.stack([self.uniform(name, i, h, size=shape) for i in range(self.p.N)], axis=1)
        arrays['teacher_attendance'] = np.stack([self.uniform('teacher_attendance', i, h, size=(6, MAX_TICKS))
            for i in range(self.p.N)], axis=2)

    def begin(self, h):
        before = self.student_fatigue.copy()
        if self.l.enabled: self.student_fatigue *= 1 - self.l.recovery
        if self.tp.enabled: self.formats *= 1 - self.tp.format_decay
        self.followup[:] = 0
        for i in range(self.p.N):
            self.log.tables['student_fatigue'].append(dict(homework=h, student=i, before=float(before[i]),
                recovered=float(self.student_fatigue[i]), recovery=self.l.recovery if self.l.enabled else 0.))
        self.release_payments(h)

    def cost(self, i, kind, e, duration):
        multiplier = self.l.costs.get(kind, .1)
        if kind == 'helper': multiplier *= self.hc.helper_cost_multiplier
        effort = (self.l.minimum_operational_effort + e) * duration
        return float((self.traits.kappa[i] * multiplier + self.l.fatigue_cost * self.student_fatigue[i]) * effort / self.p.effort_time_scale)

    def expected(self, kind, c, effort, assistance=0.):
        supported = float(np.clip(c + assistance * (1 - c), 0, 1))
        # Assistance can carry the response; producing an unaided solution needs effort.
        execution = effort + (1 - effort) * assistance
        return self.l.guess_probability + execution * (supported - self.l.guess_probability)

    def best_effort(self, i, kind, duration, belief, assistance=0., bonus=0., future=0., h=1, t=0, performance_weight=1.):
        grid = self.l.effort_grid if self.l.enabled else [1.]
        rows = []
        for e in grid:
            performance = self.expected(kind, belief, e, assistance) if self.l.enabled else belief + assistance * (1 - belief)
            expected_attention = np.clip(self.student_traits['attention'][i] + self.l.attention_effort_weight * e -
                self.student_traits['fatigue_sensitivity'][i] * self.student_fatigue[i],0,1) * (1-self.student_traits['distraction'][i])
            content_belief = max(self.l.self_reasoning_quality,
                self.l.material_quality if self.l.material_access and self.l.corrective_feedback else 0.) if kind=='attempt' else .5
            uptake = e * expected_attention * content_belief
            gain = self.l.belief_gain_rate * uptake * (1 - belief) * duration / self.l.reference_ticks
            reward = bonus * e
            value = performance_weight * performance + future * gain + reward - self.cost(i, kind, e, duration)
            rows.append(dict(homework=h, tick=t, student=i, activity=kind, effort=float(e),
                predicted_performance=float(performance), expected_gain=float(gain), expected_helper_reward=float(reward),
                cost=self.cost(i, kind, e, duration), utility=float(value)))
        best = min(rows, key=lambda r: (-r['utility'], r['effort']))
        for row in rows: self.log.tables['effort_choices'].append(dict(row, selected=row is best))
        return best['effort'], best['utility']

    def choices(self, scores, i, h, t, c, estimate, hint, has_hint, remaining):
        out = dict(scores); chosen = {}
        if self.l.enabled:
            for action in ('attempt', 'hint'):
                if action not in out: continue
                kind = 'attempt' if action == 'attempt' else 'guided'
                duration = self.p.attempt_ticks if action == 'attempt' else self.p.peer_request_ticks + self.p.guided_practice_ticks
                assistance = min(1., hint) if (has_hint or action == 'hint') else 0.
                e, utility = self.best_effort(i, kind, duration, c, assistance,
                    future=self.student_traits['future_test_value'][i], h=h, t=t)
                # Retain the existing guidance preference and peer accessibility signal.
                out[action] = utility - estimate
                chosen[action] = e
            for action in ('answer', 'ai_answer', 'ai_tutor'):
                if action in out:
                    duration = getattr(self.p, action + '_ticks', self.p.peer_answer_ticks)
                    old_cost = self.traits.kappa[i] * duration / self.p.effort_time_scale
                    out[action] += old_cost - self.cost(i, action, 0., duration)
                    chosen[action] = 0.
        if self.tp.enabled and remaining >= self.tp.practice_ticks:
            for action in ('format_practice', 'concept_revision'):
                share = self.tp.format_share if action == 'format_practice' else self.tp.revision_concept_share
                # Future stakes are measured in utility per expected test point.
                future = self.student_traits['future_test_value'][i] * share
                rate = self.tp.format_rate if action == 'format_practice' else self.l.belief_gain_rate
                grid = self.l.effort_grid if self.l.enabled else [1.]
                candidates = []
                for effort in grid:
                    gain = rate * effort * self.student_traits['attention'][i] * (1 - c) * self.tp.practice_ticks / self.l.reference_ticks
                    cost = self.cost(i, action, effort, self.tp.practice_ticks)
                    candidates.append(dict(homework=h, tick=t, student=i, activity=action, effort=effort,
                        predicted_performance=0., expected_gain=gain, expected_helper_reward=0., cost=cost, utility=future * gain - cost))
                best = min(candidates, key=lambda r: (-r['utility'], r['effort']))
                for row in candidates: self.log.tables['effort_choices'].append(dict(row, selected=row is best))
                e, value = best['effort'], best['utility']
                out[action] = value
                chosen[action] = e
        return out, chosen

    def start_job(self, job, h, topic, c, helper=False):
        i = job['i']; kind = job['kind']; duration = job['end'] - job['start']
        job['pre_k'] = float(self.knowledge[i, topic])
        job['pre_fatigue'] = float(self.student_fatigue[i])
        if 'j' in job and job['j'] >= 0:
            job['provider_k'] = float(self.knowledge[job['j'], topic])
            job.setdefault('provider_fatigue', float(self.student_fatigue[job['j']]))
        activity = kind if kind != 'shared' else 'guided'
        if kind == 'teacher':
            activity = 'coaching' if job['plan']['action'] == 'coaching' else 'teacher'
        if 'effort' not in job:
            job['effort'], _ = self.best_effort(i, activity, duration, c,
                assistance=.25 if activity in ('teacher', 'guided', 'coaching') else 0.,
                future=self.student_traits['future_test_value'][i], h=h, t=job['start'])
        self.charge(h, job['start'], job['end'], i, activity, job.get('paid_effort', job['effort']))
        if helper and job.get('j', -1) >= 0:
            j = job['j']; bonus = self.helper_value(j, i) + self.hc.helper_intrinsic_value
            job['helper_effort'], _ = self.best_effort(j, 'helper', duration, job.get('helper_belief', self.base.observation_prior),
                bonus=bonus, future=self.student_traits['future_test_value'][j], h=h, t=job['start'], performance_weight=0.)
            self.charge(h, job['start'], job['end'], j, 'helper', job['helper_effort'])
        elif kind == 'answer' and job.get('j', -1) >= 0:
            self.charge(h, job['start'], job['end'], job['j'], 'answer', 0.)

    def charge(self, h, start, end, i, kind, effort):
        cognitive = (self.l.minimum_operational_effort + effort) * (end - start)
        before = float(self.student_fatigue[i]); cost = self.cost(i, kind, effort, end - start)
        if self.l.enabled: self.student_fatigue[i] = min(1., before + self.l.fatigue_per_effort_tick * cognitive)
        self.log.tables['student_costs'].append(dict(homework=h, student=i, activity=kind, start=start, end=end,
            effort=effort, cognitive_effort_ticks=cognitive, cost=cost, fatigue_before=before,
            fatigue_after=float(self.student_fatigue[i]), effort_aversion=float(self.traits.kappa[i]),
            cost_multiplier=self.l.costs.get(kind,.1) * (self.hc.helper_cost_multiplier if kind=='helper' else 1.)))

    def rest(self, h, job):
        if self.l.enabled:
            self.student_fatigue[job['i']] *= (1 - self.l.recovery) ** ((job['end'] - job['start']) / self.l.reference_ticks)

    def productive(self, h, job, i, kind, topic, quality, readiness=1., effort=None, concept_share=1., format_share=0.):
        e = job['effort'] if effort is None else effort
        duration = job['end'] - job['start']; fatigue = job.get('provider_fatigue' if kind == 'helper' else 'pre_fatigue', float(self.student_fatigue[i]))
        distraction = float(self.uniform('distraction', i, h, job['start'], STREAMS32.get(kind, 0)) < self.student_traits['distraction'][i])
        attention_p = float(np.clip(self.student_traits['attention'][i] + self.l.attention_effort_weight * e
            - self.student_traits['fatigue_sensitivity'][i] * fatigue - distraction, 0, 1))
        attention_u = float(self.uniform('attention', i, h, job['start'], 1 if kind == 'helper' else 0))
        processing_p = float(np.clip(quality * readiness, 0, 1))
        processing_u = float(self.uniform('processing', i, h, job['start'], 1 if kind == 'helper' else 0))
        attention = attention_u < attention_p; processed = processing_u < processing_p
        dose = float(e * duration / self.l.reference_ticks * attention * processed)
        if not self.l.enabled:
            # Other A32 branches retain a deterministic quality-conditioned dose.
            attention = True; processed = quality > 0 and readiness > 0
            dose = float(e * duration / self.l.reference_ticks * quality * readiness)
        divisor = self.p.helper_learning_divisor if kind == 'helper' else self.p.attempt_learning_divisor
        multiplier = self.l.source_multipliers[kind]
        if kind in ('teacher', 'coaching'): multiplier *= self.base.learning_multiplier
        fraction = dose_fraction(self.traits.alpha[i], divisor, multiplier, dose * concept_share)
        flags = []
        if e == 0: flags.append('no_effort')
        if not attention: flags.append('inattention')
        if distraction: flags.append('distraction')
        if quality == 0: flags.append('no_useful_content')
        if readiness == 0: flags.append('prerequisite_failure')
        if not processed: flags.append('processing_failure')
        if self.knowledge[i, topic] >= 1: flags.append('mastered')
        event_id = f'h{h}-s{self.ids[i]}-t{job["start"]}-{kind}' + (f'-to{self.ids[job["i"]]}' if kind == 'helper' else '')
        self.log.tables['material_exposure'].append(dict(event_id=event_id, homework=h, student=i, source=kind,
            quality=float(quality), readiness=float(readiness), corrective_feedback=self.l.corrective_feedback))
        self.log.tables['learning_doses'].append(dict(event_id=event_id, homework=h, student=i, source=kind, topic=topic,
            start=job['start'], end=job['end'], duration=duration, effort=float(e), attention_probability=attention_p,
            attention_draw=attention_u, attended=True, attention=bool(attention), processing_probability=processing_p,
            processing_draw=processing_u, processed=bool(processed), distraction=bool(distraction),
            dose=dose, concept_share=concept_share, format_share=format_share, alpha=float(self.traits.alpha[i]),
            divisor=divisor, multiplier=multiplier, fraction=fraction, zero_gain_flags=json.dumps(flags)))
        if self.tp.enabled and format_share > 0:
            f = self.tp.forms.index(self.tp.practice_form)
            rate = dose_fraction(self.tp.format_rate, 1., 1., dose * format_share)
            for target, name in enumerate(self.tp.forms):
                before = float(self.formats[i, target]); transfer = float(self.form_transfer[f, target])
                after = before + (1 - before) * rate * transfer
                self.formats[i, target] = after
                self.log.tables['format_learning'].append(dict(event_id=event_id, homework=h, student=i,
                    source_form=self.tp.practice_form, form=name, fraction=rate, transfer=transfer, before=before, after=float(after)))
        return fraction

    def complete_learning(self, h, t, topic, finishing, before, arrays, difficulty, teacher, skills):
        residuals = {name: np.ones(self.p.N) for name in ('base', 'practice', 'helper', 'teacher')}
        for job in finishing:
            i = job['i']; kind = job['kind']; start = job['start']; pre = job['pre_k']
            q = 0.; readiness = 1.; share = 1.; form_share = 0.; source = kind
            if kind == 'teacher':
                action = job['plan']['action']
                if action in ('guidance', 'followup'): continue
                ai = ['instruction', 'explanation', 'corrective_feedback', 'guidance', 'coaching', 'followup'].index(action)
                d = np.full(self.p.items, job['plan']['difficulty'])
                result = content_effect(self.p, pre, teacher.knowledge, teacher.teaching_skill, d,
                    arrays['retrieval'][start, i], arrays['teacher_retrieval'][min(3, ai), start], arrays['teacher_explanation'][min(3, ai), start])
                job['content'] = result
                q = float(np.mean(result['correct']))
                readiness = float(np.mean(np.clip(1 - np.maximum(0, d - pre) / self.p.readiness_band, 0, 1)))
                source = 'coaching' if action == 'coaching' else 'teacher'
                if source == 'coaching': share, form_share = self.tp.coaching_concept_share, self.tp.coaching_format_share
            elif kind in ('guided', 'shared'):
                j = job['j']; source = 'guided'
                if j >= 0:
                    helper_e = job.get('helper_effort', job['effort'] if kind == 'shared' else 1.)
                    result = content_effect(self.p, pre, job['provider_k'], skills[j] * helper_e, difficulty,
                        arrays['retrieval'][start, i], arrays['retrieval'][start, j], arrays['explanation'][start, j])
                    q = float(np.mean(result['correct']))
                    helper_q = float(np.mean(result['correct'])) if self.p.helper_content_learning else 0.
                    if self.settings.topics.enabled:
                        helper_q = min(1., helper_q + self.settings.topics.helper_consolidation_rate * float(np.mean(result['correct'])))
                    helper_fraction = self.productive(h, job, j, 'helper', topic, helper_q,
                        effort=helper_e * job.get('helper_dose_weight', 1.))
                    if not self.l.enabled:
                        helper_fraction = min(1., self.traits.alpha[j] / self.p.helper_learning_divisor *
                            ((result['helper_quality'] if self.p.helper_content_learning else 0.) +
                             (self.settings.topics.helper_consolidation_rate * float(np.mean(result['correct'])) if self.settings.topics.enabled else 0.)))
                        self.log.tables['learning_doses'][-1].update(fraction=helper_fraction, rate_rule='legacy_helper')
                    residuals['helper'][j] *= 1 - helper_fraction
                else:
                    result = dict(learner_quality=0., helper_quality=0., correct=np.zeros(self.p.items, bool),
                        novel=np.ones(self.p.items, bool), transfer=np.zeros(self.p.items))
                    q = self.l.material_quality if self.l.material_access and self.l.corrective_feedback else self.l.self_reasoning_quality
                job['content'] = result
                readiness = float(np.mean(np.clip(1 - np.maximum(0, difficulty - pre) / self.p.readiness_band, 0, 1)))
                job['response_probability'] = self.expected('guided', pre, job['effort'], self.p.content_performance_multiplier * result['learner_quality'])
            elif kind == 'attempt':
                hint = job['hint']; q = max(self.l.self_reasoning_quality,
                    self.l.material_quality if self.l.material_access and self.l.corrective_feedback else 0., hint)
                readiness = float(np.mean(np.clip(1 - np.maximum(0, difficulty - pre) / self.p.readiness_band, 0, 1)))
                job['response_probability'] = self.expected(kind, pre, job['effort'], self.p.hint_performance_multiplier * hint)
            elif kind in ('format_practice', 'concept_revision'):
                q = self.l.material_quality if self.l.material_access else 0.
                share, form_share = ((self.tp.concept_share, self.tp.format_share) if kind == 'format_practice'
                    else (self.tp.revision_concept_share, self.tp.revision_format_share))
            elif kind == 'wait':
                self.rest(h, job); continue
            else: continue
            if kind in ('attempt', 'guided', 'shared') and self.l.enabled:
                assistance = self.p.hint_performance_multiplier * job['hint'] if kind=='attempt' else self.p.content_performance_multiplier * job['content']['learner_quality']
                packet_id = f'h{h}-i{i}-t{start}' if kind=='attempt' else f'guided-h{h}-i{i}-t{start}'
                self.log.tables['task_responses'].append(dict(homework=h, student=i, start=start, end=t,
                    packet_id=packet_id, pre_learning_K=pre, effort=job['effort'], assistance=float(assistance),
                    probability=job['response_probability'], item_draws=json.dumps(arrays['items'][start,i].tolist())))
            fraction = self.productive(h, job, i, source, topic, q, readiness,
                concept_share=share, format_share=form_share)
            if not self.l.enabled and kind in ('attempt', 'guided', 'shared', 'teacher') and source != 'coaching':
                if kind == 'teacher':
                    fraction = min(1., self.traits.alpha[i] / self.p.attempt_learning_divisor * teacher.learning_multiplier * job['content']['learner_quality'])
                    if self.w.enabled: fraction *= (job['end'] - job['start']) / self.l.reference_ticks
                else:
                    boost = self.p.hint_learning_multiplier * job['hint'] if kind == 'attempt' else self.p.content_learning_multiplier * job['content']['learner_quality']
                    fraction = min(1., self.traits.alpha[i] / self.p.attempt_learning_divisor * (1 + boost))
                fraction = min(1., fraction)
                self.log.tables['learning_doses'][-1].update(fraction=fraction, rate_rule='legacy_' + kind)
            target = 'teacher' if kind == 'teacher' else 'practice'
            residuals[target][i] *= 1 - fraction
            if kind == 'attempt': residuals['base'][i] *= 1 - fraction
        return residuals

    def helper_value(self, helper, recipient):
        if not self.hc.enabled or [helper, recipient] not in self.hc.pairs or self.hc.placebo_payment: return 0.
        before = np.clip(self.hc.belief_win_probability + self.progress[recipient] - self.released_cutoff, 0, 1)
        projected_progress = self.hc.belief_progress_rate * (1 - min(1., self.baseline[recipient] + self.progress[recipient]))
        after = np.clip(before + projected_progress, 0, 1)
        return float((self.hc.prize + self.hc.certificate_value) * self.reward_preference[helper] *
            (after - before) * self.hc.discount ** self.hc.payment_delay)

    def offers(self, h, t, remaining, busy, pending, submitted, c, topic):
        if not self.hc.enabled or t not in self.hc.offer_ticks: return []
        jobs = []
        for helper, recipient in self.hc.pairs:
            duration = self.hc.session_ticks; value = self.helper_value(helper, recipient)
            cost = self.cost(helper, 'helper', 1., duration)
            # Helping competes with a full own-practice opportunity; no hidden K.
            own_gain = self.l.belief_gain_rate * (1 - c[helper]) * self.student_traits['future_test_value'][helper]
            offered = value + self.hc.helper_intrinsic_value >= cost + own_gain
            feasible = all(busy[i] <= t and i not in pending and not submitted[i] and remaining(i, t) >= duration for i in (helper, recipient))
            accepted = bool(offered and feasible and self.uniform('helper_accept', recipient, h, t) < self.hc.recipient_acceptance)
            self.log.tables['helper_offers'].append(dict(homework=h, tick=t, helper=helper, recipient=recipient,
                expected_reward=value, cost=cost, displaced_study_value=float(own_gain), offered=bool(offered),
                feasible=bool(feasible), accepted=accepted, reason='accepted' if accepted else ('unavailable' if not feasible else 'refused')))
            if accepted:
                req = dict(i=recipient, j=helper, mode='hint', start=t, blocked_busy=0, declined=0, no_packet=0,
                    own_grade=None, source_grade=None, closeness=1., own_K=float(self.knowledge[recipient, topic]),
                    source_K=float(self.knowledge[helper, topic]), expected_grade=float(c[recipient]))
                job = dict(i=recipient, j=helper, kind='guided', start=t, end=t + duration, request=req, contract_session=True,
                    helper_belief=float(c[helper]))
                self.start_job(job, h, topic, c[recipient], helper=True)
                jobs.append(job)
        return jobs

    def record_work(self, h, kind, start, duration, period, topic=-1, student=-1):
        self.log.tables['teacher_work_schedule'].append(dict(homework=h, teacher=self.base.identity,
            kind=kind, period=period, start=start, end=start + duration, cost=duration, topic=topic, student=student))
        self.remaining_total -= duration

    def begin_work(self, h, topic, grade_queue):
        w = self.w; self.remaining_total = w.total_budget; self.after_remaining = w.after_class_ticks
        cursor = -w.before_class_ticks; protected = min(w.protected_instruction_ticks, self.p.ticks)
        available = max(0, self.remaining_total - (0 if w.allow_instruction_crowdout else protected))
        admin = min(self.base.admin_ticks, available)
        self.record_work(h, 'admin', cursor, admin, 'before'); cursor += admin
        prep = min(w.preparation_ticks, self.remaining_total, -cursor)
        before = float(self.preparation[topic]); stocks_before = self.preparation.copy(); self.preparation *= 1 - w.preparation_decay
        self.preparation[topic] += (1 - self.preparation[topic]) * (1 - (1 - w.preparation_rate) ** prep)
        self.record_work(h, 'preparation', cursor, prep, 'before', topic); cursor += prep
        self.log.tables['teacher_preparation'].append(dict(homework=h, topic=topic, ticks=prep, before=before,
            after=float(self.preparation[topic]), skill_before=self.base.teaching_skill,
            effective_skill=min(1., self.base.teaching_skill + w.preparation_quality_bonus * self.preparation[topic]),
            stocks_before=json.dumps(stocks_before.tolist()), stocks_after=json.dumps(self.preparation.tolist())))
        # Previous-homework grading can use remaining before-class work, without delaying students.
        graded = list(self.returned); self.returned.clear()
        for row in sorted([r for r in grade_queue if r['release'] <= h], key=lambda r: (r['homework'], r['student'])):
            cost = self.base.grading_cost
            if cost > min(-cursor, max(0, self.remaining_total - protected)): break
            self.record_work(h, 'grading', cursor, cost, 'before', row['topic'], row['student']); cursor += cost
            row['_return_tick'] = 0; self.enqueue_homework(row, h, self.base)
            graded.append(row); grade_queue.remove(row)
        self.work_end = cursor
        return graded

    def end_work(self, h, grade_queue):
        cursor = self.p.ticks
        for row in sorted(list(grade_queue), key=lambda r: (r['homework'], r['student'])):
            cost = self.base.grading_cost
            if cost > min(self.after_remaining, self.remaining_total): break
            self.record_work(h, 'grading', cursor, cost, 'after', row['topic'], row['student'])
            cursor += cost; self.after_remaining -= cost
            row['_return_tick'] = 0; self.enqueue_homework(row, h + 1, self.base)
            self.returned.append(row); grade_queue.remove(row)

    def teacher_plan(self, teacher, estimates, seen, last_served, h, topic, grading_backlog):
        w = self.w; plans = []; queue = []; cursor = 0
        reserve = min(w.after_class_ticks, grading_backlog * teacher.grading_cost,
            max(0, self.remaining_total - (0 if w.allow_instruction_crowdout else w.protected_instruction_ticks)))
        capacity = min(self.p.ticks, max(0, self.remaining_total - reserve))
        length = min(w.protected_instruction_ticks, capacity)
        length -= length % w.minimum_segment_ticks
        def plan(action, ids, duration, begin):
            estimate = float(np.mean(estimates[ids]))
            difficulty = teacher.fixed_difficulty if teacher.curriculum == 'fixed' else float(np.clip(estimate + teacher.difficulty_offset, 0, 1))
            return dict(homework=h, teacher=teacher.identity, action=action, targets=ids,
                observed_estimate=estimate, seen=[int(seen[i]) for i in ids], difficulty=difficulty,
                duration=duration, start=begin, end=begin + duration, action_id=f'teacher-h{h}-a{len(plans)}',
                status='queued', reason='')
        if length:
            plans.append(plan('instruction', list(range(self.p.N)), length, cursor)); cursor += length
        if length < w.protected_instruction_ticks:
            queue.append(dict(homework=h, teacher=teacher.identity, action='instruction', targets=list(range(self.p.N)),
                seen=seen.tolist(), status='unserved', reason='declared_crowdout', duration=w.protected_instruction_ticks - length))
        # Discretionary actions compete on one evaluator. Guidance projects future
        # study; it does not pretend to produce immediate conceptual knowledge.
        after = np.array(estimates, float); engagement = w.expected_engagement
        observed_topics = np.stack([o.estimate for o in self.observers], axis=1)
        predicted_formats = np.zeros(self.p.N)
        predicted_participation = np.full(self.p.N, engagement if self.tp.participation else 1.)
        if length: after += (1 - after) * self.productivity * engagement * length / self.l.reference_ticks
        candidates = []
        order = sorted(range(self.p.N), key=lambda i: (estimates[i], last_served[i], self.ids[i]))
        for _ in range(self.p.ticks):
            candidates = []
            for action in w.actions:
                duration = teacher.guidance_ticks if action in ('guidance', 'followup') else (teacher.explanation_ticks if action == 'explanation' else self.tp.practice_ticks)
                if cursor + duration > capacity: continue
                for i in order:
                    predicted = after.copy(); predicted_format = predicted_formats.copy(); participation = predicted_participation.copy()
                    immediate_gain = 0.
                    if action == 'guidance':
                        projected = (1 - predicted[i]) * self.productivity * engagement * teacher.guidance_strength * w.expected_study_opportunities * w.planning_horizon
                        predicted[i] += projected
                    elif action == 'followup':
                        participation[i] = min(1., participation[i] + self.tp.followup_cost_reduction)
                    elif action == 'coaching':
                        predicted[i] += (1 - predicted[i]) * self.productivity * engagement * self.tp.coaching_concept_share * duration / self.l.reference_ticks
                        predicted_format[i] += (1 - predicted_format[i]) * w.belief_format_rate * engagement * self.tp.coaching_format_share * duration / self.l.reference_ticks
                        immediate_gain = predicted[i] - after[i]
                    else:
                        predicted[i] += (1 - predicted[i]) * self.productivity * engagement * duration / self.l.reference_ticks
                        immediate_gain = predicted[i] - after[i]
                    predicted = np.clip(predicted, 0, 1)
                    before_topics = np.clip(observed_topics + (after - estimates)[:,None] * self.transfer[topic][None,:], 0, 1)
                    after_topics = np.clip(before_topics + (predicted - after)[:,None] * self.transfer[topic][None,:], 0, 1)
                    before_part = predicted_participation.copy()
                    after_part = before_part.copy()
                    if action == 'followup': after_part[i] = participation[i]
                    # Expected missing contribution uses a distribution over observed
                    # versus missing outcomes, retaining the contract denominator.
                    before_reward = reward = 0.
                    for design in self.designs:
                        form = design['form']
                        if w.contract.forms and form not in w.contract.forms: continue
                        before_score = np.clip(before_topics @ np.array(design['topic_weights']) + .5 - design['difficulty'], 0, 1)
                        after_score = np.clip(after_topics @ np.array(design['topic_weights']) + .5 - design['difficulty'], 0, 1)
                        transfer = self.form_transfer[self.tp.forms.index(self.tp.practice_form), self.tp.forms.index(form)] if self.tp.enabled else 0.
                        before_score += (1 - before_score) * design['format_loading'] * predicted_formats * transfer
                        after_score += (1 - after_score) * design['format_loading'] * predicted_format * transfer
                        base = [self.teacher_baseline[j, form] for j in range(self.p.N)]
                        before_reward += self.expected_contract(before_score, before_part, base, form)
                        reward += self.expected_contract(after_score, after_part, base, form)
                    base = [self.teacher_baseline.get((j, 'homework'), self.base.observation_prior) for j in range(self.p.N)]
                    before_reward += self.expected_contract(after, np.ones(self.p.N), base, 'homework', source='homework')
                    reward += self.expected_contract(predicted, np.ones(self.p.N), base, 'homework', source='homework')
                    expected_reward = (reward - before_reward) * w.contract.discount ** (w.contract.payment_delay + w.planning_horizon)
                    intrinsic = w.intrinsic_weight * float(np.mean(predicted - after))
                    cost = w.effort_cost * duration + w.quadratic_cost * ((cursor + duration) / max(1, w.total_budget)) ** 2
                    candidates.append(dict(homework=h, tick=cursor, action=action, student=i,
                        observed_before=float(after[i]), predicted_after=float(predicted[i]), immediate_concept_gain=float(immediate_gain),
                        planning_horizon=w.planning_horizon, expected_study_opportunities=w.expected_study_opportunities,
                        predicted_format=float(predicted_format[i]), expected_payment_increment=float(expected_reward),
                        intrinsic=intrinsic, cost=cost, utility=intrinsic + expected_reward - cost,
                        duration=duration, predicted=predicted, format_state=predicted_format, participation_state=after_part))
            if not candidates: break
            best = min(candidates, key=lambda r: (-r['utility'], r['duration'], r['student'], r['action']))
            selected = best['utility'] > 0
            for row in candidates:
                self.log.tables['teacher_forecasts'].append({k: v for k, v in row.items() if k not in ('predicted','format_state','participation_state')} | {'selected': selected and row is best})
            if not selected: break
            plans.append(plan(best['action'], [best['student']], best['duration'], cursor))
            after = best['predicted']; predicted_formats = best['format_state']; predicted_participation = best['participation_state']; cursor += best['duration']
        for action in plans:
            self.record_work(h, action['action'], action['start'], action['end'] - action['start'], 'class', topic)
        return plans, queue, cursor, []

    def expected_contract(self, scores, participation, baseline, form, source='exam'):
        # Exact expectation by independent Bernoulli enumeration for small cohorts;
        # for eligible denominators, linearity gives the exact same evaluator sum.
        c = self.w.contract
        if c.denominator == 'eligible' or c.missing == 'zero':
            return sum(participation[i] * contract_value(c, [float(scores[i])], [baseline[i]], form=form, source=source)
                + (1 - participation[i]) * contract_value(c, [None], [baseline[i]], form=form, source=source)
                for i in range(len(scores))) / len(scores)
        # Observed denominator expectation: integrate the Poisson-binomial count of
        # other observed scores. This avoids dividing by the expected count.
        contributions = 0.
        for i in range(len(scores)):
            pmf = np.array([1.])
            for j in range(len(scores)):
                if i != j: pmf = np.convolve(pmf, [1 - participation[j], participation[j]])
            contribution = contract_value(c, [float(scores[i])], [baseline[i]], form=form, source=source)
            contributions += participation[i] * contribution * sum(pmf[k] / (k + 1) for k in range(len(pmf)))
        return float(contributions)

    def resources(self, h):
        rows = [r for r in self.log.tables['teacher_work_schedule'] if r['homework'] == h]
        costs = {period: sum(r['cost'] for r in rows if r['period'] == period) for period in ('before', 'class', 'after')}
        self.log.tables['teacher_resources'].append(dict(homework=h, total_budget=self.w.total_budget,
            before=costs['before'], classroom=costs['class'], after=costs['after'],
            spent=sum(costs.values()), unused=self.remaining_total))

    def homework_contract(self, row, h):
        if not self.w.enabled or self.w.contract.sources['homework'] == 0: return
        block = self.homework_evidence.setdefault(row['homework'], {})
        block[row['student']] = row['grade'] if not row['assisted'] or self.base.assisted_observation_weight > 0 else None
        if len(block) == self.p.N:
            self.contract_evidence.append(dict(source_homework=row['homework'], source='homework', form='homework',
                scores=[block[i] for i in range(self.p.N)], release=h + self.base.observation_delay))
            del self.homework_evidence[row['homework']]

    def assess(self, h, c, teacher, feedback_queue):
        scores_by_form = {}
        for design_index, design in enumerate(self.designs):
            form = design['form']; scores = []; exam_rows = []
            topic_weights = np.array(design['topic_weights'])
            f = self.tp.forms.index(form) if self.tp.enabled else 0
            for i in range(self.p.N):
                core = float(np.clip(np.dot(self.knowledge[i], topic_weights) + .5 - design['difficulty'], 0, 1))
                familiarity = float(self.formats[i, f]) if self.tp.enabled else 0.
                probability = core + (1 - core) * design['format_loading'] * familiarity
                u = self.uniform('exam', i, h, design_index, size=self.p.exam_items)
                correct = u < probability
                stakes = design['stakes'] * self.tp.participation_stakes
                access_cost = max(0., design['access_cost'] + self.tp.participation_cost - self.followup[i])
                predicted = float(np.clip(c[i] + .5 - design['difficulty'], 0, 1))
                utility = stakes * predicted - access_cost
                participates = not (self.tp.enabled and self.tp.participation) or utility >= 0
                score = float(correct.mean()) if participates else None
                scores.append(score)
                self.log.tables['exam_participation'].append(dict(homework=h, student=i, assessment=design['name'], form=form,
                    prediction=predicted, stakes=stakes, access_cost=access_cost, utility=utility, participated=bool(participates)))
                for m in range(self.p.exam_items):
                    self.log.tables['assessment_items'].append(dict(homework=h, student=i, assessment=design['name'], form=form,
                        item=m, core_probability=core, familiarity=familiarity, probability=probability,
                        potential_draw=float(u[m]), potential_correct=bool(correct[m]), observed_correct=bool(correct[m]) if participates else None))
                self.log.tables['assessment_scores'].append(dict(homework=h, student=i, assessment=design['name'], form=form,
                    participated=bool(participates), score=score, cohort_contribution=0. if score is None else score,
                    K=float(self.knowledge[i].mean()), potential_score=float(correct.mean()), release=h + self.p.feedback_delay + 1))
                if design_index == 0 and participates:
                    row = dict(homework=h, student=i, score=score, prediction=float(c[i]), K=float(self.knowledge[i].mean()), release=h + self.p.feedback_delay + 1)
                    self.log.tables['exams'].append(row)
                    # Only the actually administered score is observed. Mixed-topic
                    # scores are a declared proxy, not extra invisible diagnostic tests.
                    for k in range(self.count):
                        if topic_weights[k] <= 0: continue
                        self.log.tables['exam_topics'].append(dict(homework=h, student=i, topic=k, score=score,
                            topic_weight=float(topic_weights[k]), measurement='administered_composite_proxy', release=row['release']))
                        self.observers[k].enqueue('exam', h, i, score, False, row['release'] + teacher.observation_delay)
                    if self.p.feedback_mode != 'none': feedback_queue.append(row)
            scores_by_form[form] = scores
            if self.w.enabled:
                self.contract_evidence.append(dict(source_homework=h, source='exam', form=form, scores=scores,
                    release=h + self.p.feedback_delay + 1 + teacher.observation_delay))
        if self.hc.enabled and h in (self.hc.checkpoints or list(range(self.p.exam_every, self.p.H + 1, self.p.exam_every))):
            self.helper_pending.append(dict(source_homework=h, scores=scores_by_form[self.hc.form],
                release=h + self.p.feedback_delay + 1))

    def release_payments(self, h):
        for event in list(self.contract_evidence):
            if event['release'] > h: continue
            form = event['form']; observed = []
            for i, score in enumerate(event['scores']):
                seen = score
                if score is not None:
                    if self.uniform('observation_coverage', i, event['source_homework'], 10) >= self.base.observation_coverage: seen = None
                    else:
                        noise = semantic(self.draws, 163, self.ids[i], event['source_homework'], 10, normal=True)
                        seen = float(np.clip(score + self.base.observation_noise_std * noise, 0, 1))
                observed.append(seen)
                self.teacher_baseline.setdefault((i, form), float(self.base.observation_prior))
            baseline = [self.teacher_baseline[(i, form)] for i in range(self.p.N)]
            amount = contract_value(self.w.contract, observed, baseline, event['source'], form)
            self.log.tables['contract_observations'].append(dict(homework=h, source_homework=event['source_homework'], source=event['source'],
                form=form, scores=json.dumps(observed), baseline=json.dumps(baseline), amount=amount))
            self.contract_pending.append(dict(signal_homework=h, source_homework=event['source_homework'], source=event['source'],
                form=form, due=h + self.w.contract.payment_delay, amount=amount))
            if self.w.belief_update_rate:
                valid = [max(0., s - baseline[i]) for i, s in enumerate(observed) if s is not None]
                if valid: self.productivity += self.w.belief_update_rate * (float(np.mean(valid)) - self.productivity)
            self.contract_evidence.remove(event)
        for event in list(self.helper_pending):
            if 'amounts' not in event:
                if event['release'] > h: continue
                recipient_ids = sorted(r for _, r in self.hc.pairs)
                progress = {r: (event['scores'][r] - self.baseline[r] if event['scores'][r] is not None else -math.inf) for r in recipient_ids}
                tie = {r: self.uniform('helper_tie', r, event['source_homework']) for r in recipient_ids}
                ranked = sorted(recipient_ids, key=lambda r: (-progress[r], tie[r]))
                q = self.hc.top_fraction * len(ranked); count = int(math.floor(q))
                boundary = semantic(self.draws, 149, 0, event['source_homework']) < q - count
                winners = set(ranked[:count + int(boundary)])
                winners = {r for r in winners if event['scores'][r] is not None}
                self.released_cutoff = min((progress[r] for r in winners), default=0.)
                amounts = []
                for helper, recipient in self.hc.pairs:
                    win = recipient in winners
                    if event['scores'][recipient] is not None: self.progress[recipient] = progress[recipient]
                    # Placebo pays independently of progress, and offers do not
                    # value it as a marginal return to helping.
                    if self.hc.placebo_payment: win = self.uniform('helper_tie', recipient, event['source_homework'], 1) < self.hc.top_fraction
                    amount = self.hc.prize if win else 0.; certificate = self.hc.certificate_value if win else 0.
                    self.log.tables['helper_checkpoints'].append(dict(homework=h, source_homework=event['source_homework'], helper=helper,
                        recipient=recipient, baseline=float(self.baseline[recipient]), score=event['scores'][recipient],
                        progress=None if not math.isfinite(progress[recipient]) else progress[recipient], quota=q,
                        boundary=bool(boundary), tie_draw=float(tie[recipient]), winner=bool(win), released_cutoff=float(self.released_cutoff)))
                    amounts.append(dict(helper=helper, recipient=recipient, amount=amount, certificate=certificate))
                event.update(amounts=amounts, due=h + self.hc.payment_delay)
            if event['due'] <= h:
                for amount in event['amounts']: self.log.tables['helper_payments'].append(dict(**amount, homework=h, source_homework=event['source_homework'], due=event['due']))
                self.helper_pending.remove(event)
        for event in list(self.contract_pending):
            if event['due'] <= h:
                self.log.tables['contract_payments'].append(dict(event, homework=h)); self.contract_pending.remove(event)

    def close(self):
        super().close()
        self.log.tables['contract_backlog'] = [dict(r, stage='payment') for r in self.contract_pending] + [dict(r, stage='observation') for r in self.contract_evidence]
        self.log.tables['helper_payment_backlog'] = [r.copy() for r in self.helper_pending]
        for i in range(self.p.N):
            for f, name in enumerate(self.tp.forms):
                self.log.tables['format_states'].append(dict(student=i, form=name, familiarity=float(self.formats[i, f])))
