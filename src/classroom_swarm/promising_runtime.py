"""A33 observed policy state and skill/content physics; frozen A32 is untouched."""
import json
import math
import numpy as np
from .effort_runtime import EffortRuntime, semantic
from .tutoring_settings import content_effect

STREAMS33 = {'skill_pretest':170,'assessment_tags':171,'fragments':172,'reasoning':173}
TABLES33 = ('curriculum_pretest','curriculum_choices','curriculum_readiness','teacher_belief_updates',
    'participation_forecast_evidence','teacher_format_expectations','shared_reasoning','curriculum_projection')

class PromisingRuntime(EffortRuntime):
    def __init__(self,*args):
        *old, self.design = args
        super().__init__(*old)
        for name in TABLES33: self.log.tables[name]=[]
        self.format_belief=np.zeros_like(self.formats)
        self.participation_bias=np.full((self.p.N,len(self.tp.forms)),self.design.teacher_forecast.initial_bias)
        self.participation_queue=[]
        if self.design.curriculum.enabled:
            for i in range(self.p.N):
                self.log.tables['curriculum_projection'].append(dict(student=i,student_id=self.ids[i],initial_mean=float(self.knowledge[i].mean()),base_K=float(self.traits.K0[i])))
                for k in range(self.count):
                    u=semantic(self.draws,170,self.ids[i],k,size=self.design.curriculum.pretest_items)
                    score=float(np.mean(u<self.knowledge[i,k]))
                    seen=self.uniform('observation_coverage',i,0,k)>=1-self.base.observation_coverage
                    noise=semantic(self.draws,163,self.ids[i],0,k,normal=True)
                    observed=float(np.clip(score+self.base.observation_noise_std*noise,0,1)) if seen else None
                    if observed is not None:
                        self.observers[k].estimate[i]=observed; self.observers[k].seen[i]=1
                    self.log.tables['curriculum_pretest'].append(dict(student=i,topic=k,score=score,observed=observed,release=0,item_draws=json.dumps(u.tolist())))

    def begin(self,h):
        super().begin(h)
        if self.design.teacher_forecast.enabled: self.format_belief *= 1-self.tp.format_decay
        if self.base.enabled:
            self.log.tables['teacher_observations'].extend(self.release_observers(h,self.draws,0))
        for evidence in list(self.participation_queue):
            if evidence['release']>h: continue
            i=evidence['student']; f=self.tp.forms.index(evidence['form']); before=float(self.participation_bias[i,f])
            self.participation_bias[i,f]=np.clip(before+self.design.teacher_forecast.update_rate*(int(evidence['participated'])-evidence['predicted_probability'])*self.design.teacher_forecast.uncertainty,-1,1)
            self.log.tables['teacher_belief_updates'].append(dict(**evidence,homework=h,bias_before=before,bias_after=float(self.participation_bias[i,f])))
            self.participation_queue.remove(evidence)

    def choose_topic(self,h):
        original=int(self.schedule[h-1]); c=self.design.curriculum
        if not c.enabled: return original
        l=len(c.levels); domain=original//l; estimates=np.stack([o.estimate for o in self.observers],axis=1)
        means=estimates[:,domain*l:(domain+1)*l].mean(axis=0)
        if c.adaptive and self.base.enabled and self.base.curriculum!='fixed':
            eligible=[k for k,prerequisite in enumerate(c.prerequisites) if prerequisite<0 or means[prerequisite]>=c.mastery_threshold]
            level=max(eligible)
        else: level=c.level_schedule[h-1] if c.level_schedule else c.fixed_level
        selected=domain*l+level
        self.log.tables['curriculum_choices'].append(dict(homework=h,domain=domain,topic=selected,level=level,observed_means=json.dumps(means.tolist()),rule='observed_prerequisites' if c.adaptive and self.base.enabled and self.base.curriculum!='fixed' else 'fixed'))
        return selected

    def start_job(self,job,h,topic,c,helper=False):
        super().start_job(job,h,topic,c,helper)
        job['skill_snapshot']={job['i']:self.knowledge[job['i']].copy()}
        if job.get('j',-1)>=0: job['skill_snapshot'][job['j']]=self.knowledge[job['j']].copy()

    def productive(self,h,job,i,kind,topic,quality,readiness=1.,**kwargs):
        if self.design.curriculum.enabled:
            c=self.design.curriculum; l=len(c.levels); prerequisite=c.prerequisites[topic%l]
            value=1. if prerequisite<0 else float(job['skill_snapshot'][i][topic//l*l+prerequisite])
            readiness=1. if prerequisite<0 else float(np.clip((value-(c.mastery_threshold-c.readiness_width))/c.readiness_width,0,1))
            self.log.tables['curriculum_readiness'].append(dict(homework=h,start=job['start'],student=i,topic=topic,prerequisite=prerequisite,value=value,readiness=readiness))
        working=job
        if kind=='coaching' and job['plan'].get('scope')=='group':
            working={**job,'end':job['start']+job['plan']['delivery_ticks']}
        fraction=super().productive(h,working,i,kind,topic,quality,readiness,**kwargs)
        row=self.log.tables['learning_doses'][-1]
        row.update(end=job['end'],reserved_duration=job['end']-job['start'])
        return fraction

    def content_result(self,result,job,h,topic,arrays,teacher,skills):
        i=job['i']; start=job['start']
        if job['kind']=='teacher' and self.design.curriculum.enabled and self.design.curriculum.independent_teacher_accuracy:
            action=job['plan']['action']; ai=['instruction','explanation','corrective_feedback','guidance','coaching','followup'].index(action)
            correct=(arrays['teacher_retrieval'][min(3,ai),start]<teacher.knowledge)&(arrays['teacher_explanation'][min(3,ai),start]<teacher.teaching_skill)
            novel=arrays['retrieval'][start,i]>=job['pre_k']
            return dict(correct=correct,novel=novel,transfer=correct*novel,learner_quality=float(np.mean(correct*novel)),helper_quality=0.)
        if job['kind'] in ('guided','shared') and job['j']>=0 and self.design.shared_reasoning.enabled:
            j=job['j']; a=semantic(self.draws,172,self.ids[i],h,start,size=(2,self.p.items))<math.sqrt(job['pre_k'])
            b=semantic(self.draws,172,self.ids[j],h,start,size=(2,self.p.items))<math.sqrt(job['provider_k'])
            u=semantic(self.draws,173,self.ids[i],h,start,self.ids[j],size=self.p.items)
            own=a.all(axis=0); known=b.all(axis=0); union=(a|b).all(axis=0)
            e=job.get('helper_effort',1.); reasoning=union&(u<self.design.shared_reasoning.reasoning_probability*min(job['effort'],e))
            correct=(known|reasoning)&(arrays['explanation'][start,j]<skills[j]*e)
            self.log.tables['shared_reasoning'].append(dict(homework=h,start=start,requester=i,provider=j,requester_fragments=json.dumps(a.astype(int).tolist()),provider_fragments=json.dumps(b.astype(int).tolist()),own_bits=''.join(map(str,own.astype(int))),provider_bits=''.join(map(str,known.astype(int))),union_bits=''.join(map(str,union.astype(int))),correct_bits=''.join(map(str,correct.astype(int))),constructed=int(np.sum(correct&~own&~known)),reasoning_probability=self.design.shared_reasoning.reasoning_probability,reasoning_effort=float(min(job['effort'],e)),reasoning_draws=json.dumps(u.tolist()),explanation_draws=json.dumps(arrays['explanation'][start,j].tolist()),explanation_probability=float(skills[j]*e)))
            return dict(correct=correct,novel=~own,transfer=correct*(~own),learner_quality=float(np.mean(correct*(~own))),helper_quality=float(np.mean(correct)))
        return result

    def predict_participation(self,topics,followup,design):
        if not self.tp.participation: return np.ones(self.p.N)
        confidence=np.clip(topics@np.asarray(design['topic_weights'])+self.participation_bias[:,self.tp.forms.index(design['form'])],0,1)
        predicted=np.clip(confidence+.5-design['difficulty'],0,1)
        stakes=design['stakes']*self.tp.participation_stakes
        cost=np.maximum(0,design['access_cost']+self.tp.participation_cost-followup)
        z=(stakes*predicted-cost)/self.design.teacher_forecast.uncertainty
        probability=np.array([.5*(1+math.erf(float(v)/math.sqrt(2))) for v in z])
        return np.where(cost<=0,1.,probability)

    def observe_delivered_format(self,h,job,i):
        if not self.design.teacher_forecast.enabled: return
        f=self.tp.forms.index(self.tp.practice_form); before=self.format_belief[i].copy()
        duration=job['plan'].get('delivery_ticks',job['end']-job['start'])
        fraction=1-(1-self.w.belief_format_rate)**(self.w.expected_engagement*self.tp.coaching_format_share*duration/self.l.reference_ticks)
        self.format_belief[i]+=(1-self.format_belief[i])*fraction*self.form_transfer[f]
        self.log.tables['teacher_format_expectations'].append(dict(homework=h,student=i,action_id=job['plan']['action_id'],before=json.dumps(before.tolist()),after=json.dumps(self.format_belief[i].tolist()),fraction=fraction))

    def adjust_observed_score(self,i,f,score,loading):
        if not self.design.teacher_forecast.enabled: return score
        effect=float(loading*self.format_belief[i,f])
        return float(np.clip((score-effect)/max(1e-12,1-effect),0,1))

    def assessment_tags(self,index,weights):
        weights=np.asarray(weights,float)
        u=semantic(self.draws,171,0,index,size=self.p.exam_items)
        return np.minimum(len(weights)-1,np.searchsorted(np.cumsum(weights),u,side='right'))

    def queue_participation(self,h,index,design,teacher):
        if not self.design.teacher_forecast.enabled: return
        topics=np.stack([o.estimate for o in self.observers],axis=1)
        predicted=self.predict_participation(topics,self.followup,design)
        for row in self.log.tables['exam_participation'][-self.p.N:]:
            record=dict(source_homework=h,student=row['student'],form=design['form'],participated=row['participated'],predicted_probability=float(predicted[row['student']]),release=h+self.p.feedback_delay+1+teacher.observation_delay)
            self.participation_queue.append(record)
            self.log.tables['participation_forecast_evidence'].append(record.copy())

    def teacher_plan(self,*args):
        result=self.observed_teacher_plan(*args) if self.design.teacher_forecast.enabled else super().teacher_plan(*args)
        for plan in result[0]:
            plan.setdefault('scope','class' if plan['action']=='instruction' else 'individual')
            plan.setdefault('delivery_ticks',plan['duration'])
        return result

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
                result = self.content_result(result, job, h, topic, arrays, teacher, skills)
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
                    result = self.content_result(result, job, h, topic, arrays, teacher, skills)
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
            if kind == 'teacher' and job['plan']['action'] == 'coaching': self.observe_delivered_format(h, job, i)
            target = 'teacher' if kind == 'teacher' else 'practice'
            residuals[target][i] *= 1 - fraction
            if kind == 'attempt': residuals['base'][i] *= 1 - fraction
        return residuals

    def observed_teacher_plan(self, teacher, estimates, seen, last_served, h, topic, grading_backlog):
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
        predicted_formats = self.format_belief[:, self.tp.forms.index(self.tp.practice_form)].copy()
        predicted_followup = np.zeros(self.p.N)
        predicted_participation = self.predict_participation(observed_topics, predicted_followup, self.designs[0])
        if length: after += (1 - after) * self.productivity * engagement * length / self.l.reference_ticks
        candidates = []
        order = sorted(range(self.p.N), key=lambda i: (estimates[i], last_served[i], self.ids[i]))
        for _ in range(self.p.ticks):
            candidates = []
            options = []
            for action in w.actions:
                duration = teacher.guidance_ticks if action in ('guidance', 'followup') else (teacher.explanation_ticks if action == 'explanation' else self.tp.practice_ticks)
                options.extend((action,[i],duration,'individual',duration) for i in order if cursor+duration <= capacity)
            g = self.design.group_preparation
            duration = g.delivery_ticks + math.ceil(self.p.N/g.feedback_capacity)*g.feedback_ticks
            if g.enabled and 'coaching' in w.actions and self.preparation[topic] > 0 and cursor+duration <= capacity:
                options.append(('coaching',list(range(self.p.N)),duration,'group',g.delivery_ticks))
            for action, targets, duration, scope, delivered in options:
                for i in [targets[0]]:
                    predicted = after.copy(); predicted_format = predicted_formats.copy(); participation = predicted_participation.copy(); next_followup = predicted_followup.copy()
                    immediate_gain = 0.
                    if action == 'guidance':
                        projected = (1 - predicted[targets]) * self.productivity * engagement * teacher.guidance_strength * w.expected_study_opportunities * w.planning_horizon
                        predicted[targets] += projected
                    elif action == 'followup':
                        next_followup[i] += self.tp.followup_cost_reduction
                    elif action == 'coaching':
                        predicted[targets] += (1 - predicted[targets]) * self.productivity * engagement * self.tp.coaching_concept_share * delivered / self.l.reference_ticks
                        predicted_format[targets] += (1 - predicted_format[targets]) * w.belief_format_rate * engagement * self.tp.coaching_format_share * delivered / self.l.reference_ticks
                        immediate_gain = predicted[targets] - after[targets]
                    else:
                        predicted[targets] += (1 - predicted[targets]) * self.productivity * engagement * delivered / self.l.reference_ticks
                        immediate_gain = predicted[targets] - after[targets]
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
                        before_part = self.predict_participation(before_topics, predicted_followup, design)
                        after_part = self.predict_participation(after_topics, next_followup, design)
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
                        observed_before=float(np.mean(after[targets])), predicted_after=float(np.mean(predicted[targets])), immediate_concept_gain=float(np.mean(immediate_gain)),
                        planning_horizon=w.planning_horizon, expected_study_opportunities=w.expected_study_opportunities,
                        predicted_format=float(np.mean(predicted_format[targets])), scope=scope, targets=targets, delivery_ticks=delivered, expected_payment_increment=float(expected_reward),
                        intrinsic=intrinsic, cost=cost, utility=intrinsic + expected_reward - cost,
                        duration=duration, predicted=predicted, format_state=predicted_format, participation_state=after_part, followup_state=next_followup))
            if not candidates: break
            best = min(candidates, key=lambda r: (-r['utility'], r['duration'], r['student'], r['action']))
            selected = best['utility'] > 0
            for row in candidates:
                self.log.tables['teacher_forecasts'].append({k: v for k, v in row.items() if k not in ('predicted','format_state','participation_state','followup_state')} | {'selected': selected and row is best})
            if not selected: break
            plans.append(plan(best['action'], best['targets'], best['duration'], cursor) | {'scope':best['scope'], 'delivery_ticks':best['delivery_ticks']})
            after = best['predicted']; predicted_formats = best['format_state']; predicted_participation = best['participation_state']; predicted_followup = best['followup_state']; cursor += best['duration']
        for action in plans:
            self.record_work(h, action['action'], action['start'], action['end'] - action['start'], 'class', topic)
        return plans, queue, cursor, []

    def assess(self, h, c, teacher, feedback_queue):
        scores_by_form = {}
        for design_index, design in enumerate(self.designs):
            form = design['form']; scores = []; exam_rows = []
            topic_weights = np.array(design['topic_weights'])
            f = self.tp.forms.index(form) if self.tp.enabled else 0
            for i in range(self.p.N):
                tags = self.assessment_tags(design_index, topic_weights)
                item_core = np.clip(self.knowledge[i,tags] + .5 - design['difficulty'],0,1) if self.design.curriculum.enabled else np.full(self.p.exam_items, np.clip(np.dot(self.knowledge[i],topic_weights)+.5-design['difficulty'],0,1))
                core = item_core
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
                        item=m, topic=int(tags[m]), core_probability=float(core[m]), familiarity=familiarity, probability=float(probability[m]),
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
                        if self.design.curriculum.enabled and not np.any(tags==k): continue
                        measured = float(np.mean(correct[tags==k])) if self.design.curriculum.enabled and np.any(tags==k) else score
                        self.log.tables['exam_topics'].append(dict(homework=h, student=i, topic=k, score=measured,
                            topic_weight=float(topic_weights[k]), measurement='administered_tagged_items' if self.design.curriculum.enabled else 'administered_composite_proxy', release=row['release']))
                        adjusted = self.adjust_observed_score(i, f, measured, design['format_loading'])
                        self.observers[k].enqueue('exam', h, i, adjusted, False, row['release'] + teacher.observation_delay)
                    if self.p.feedback_mode != 'none': feedback_queue.append(row)
            self.queue_participation(h, design_index, design, teacher)
            scores_by_form[form] = scores
            if self.w.enabled:
                self.contract_evidence.append(dict(source_homework=h, source='exam', form=form, scores=scores,
                    release=h + self.p.feedback_delay + 1 + teacher.observation_delay))
        if self.hc.enabled and h in (self.hc.checkpoints or list(range(self.p.exam_every, self.p.H + 1, self.p.exam_every))):
            self.helper_pending.append(dict(source_homework=h, scores=scores_by_form[self.hc.form],
                release=h + self.p.feedback_delay + 1))

