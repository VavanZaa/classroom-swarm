"""A31 state, queued evidence and workload; no true student K enters teacher policy."""
from dataclasses import asdict,replace
import json
import numpy as np
from .teacher_settings import TeacherObserver
from .mechanism_settings import topic_arrays

NEW_TABLES=('topic_initial','topic_states','topic_learning','exam_items','exam_topics',
    'peer_signals','peer_signal_backlog','quality_choice_state','teacher_runtime',
    'workload_arrivals','teacher_fatigue','incentive_candidates','teacher_rewards','reward_backlog')


class MechanismRuntime:
    def __init__(self,settings,base,p,k,quality,log):
        self.settings,self.base,self.p,self.log=settings,base,p,log
        self.knowledge,self.transfer,self.schedule=topic_arrays(settings,k,p.H)
        self.count=self.knowledge.shape[1]
        self.observers=[TeacherObserver(base,p.N) for _ in range(self.count)]
        pooled=not(settings.peer_observation.enabled and settings.peer_observation.topic_specific)
        self.quality=np.tile(quality[None,:,:],(1 if pooled else self.count,1,1))
        self.pooled=pooled;self.peer_queue=[];self.reward_queue=[];self.fatigue=0.;self.previous_topic=None
        for name in NEW_TABLES:log.tables[name]=[]
        for i in range(p.N):
            for t in range(self.count):log.tables['topic_initial'].append(dict(student=i,topic=t,knowledge=float(self.knowledge[i,t])))

    def quality_for(self,topic):return self.quality[0 if self.pooled else topic]

    def prepare_teacher(self,h,topic,closing=False):
        base=self.base;w=self.settings.workload
        before=self.fatigue;self.fatigue*=1-w.recovery if w.enabled and not closing else 1
        self.fatigue_before=before;self.fatigue_recovered=self.fatigue
        burst=w.admin_bursts[h-1] if w.enabled and w.admin_bursts and not closing else 0
        prep=w.preparation_ticks if w.enabled and not closing else 0
        switch=w.topic_switch_ticks if w.enabled and self.previous_topic is not None and topic!=self.previous_topic and not closing else 0
        arrived=0 if closing else base.admin_ticks+burst+prep+switch
        self.log.tables['workload_arrivals'].append(dict(homework=h,topic=topic,base_admin=0 if closing else base.admin_ticks,
            burst=burst,preparation=prep,topic_switch=switch,arrived=arrived))
        if not closing:self.previous_topic=topic
        runtime=replace(base,admin_ticks=arrived)
        if not base.enabled:runtime=replace(base,time_budget=0,admin_ticks=0,grading_ticks_per_student=0,actions=[],observation_sources=[])
        return runtime

    def after_work(self,h,topic,teacher,cursor):
        w=self.settings.workload
        if w.enabled:self.fatigue=float(np.clip(self.fatigue+w.fatigue_per_tick*cursor,0,1))
        self.fatigue_work=self.fatigue
        skill=teacher.teaching_skill*(1-w.quality_loss*self.fatigue) if w.enabled else teacher.teaching_skill
        teacher=replace(teacher,teaching_skill=skill)
        self.log.tables['teacher_runtime'].append(dict(homework=h,topic=topic,workload=cursor,settings=json.dumps(asdict(teacher),sort_keys=True)))
        return teacher

    def after_teaching(self,h,ticks):
        w=self.settings.workload
        if w.enabled:self.fatigue=float(np.clip(self.fatigue+w.fatigue_per_tick*ticks,0,1))
        self.log.tables['teacher_fatigue'].append(dict(homework=h,before=self.fatigue_before,
            recovered=self.fatigue_recovered,after_workload=self.fatigue_work,teaching_ticks=ticks,after=self.fatigue))

    def enqueue_homework(self,row,h,teacher):
        topic=row['topic']
        self.observers[topic].enqueue('homework',row['homework'],row['student'],row['grade'],row['assisted'],
            h+teacher.observation_delay,row['_return_tick'] if teacher.observation_delay==0 else 0)

    def release_observers(self,h,draws,tick):
        result=[];s=self.settings.incentives
        for topic,observer in enumerate(self.observers):
            for row in observer.release(h,draws,tick):
                row['topic']=topic;result.append(row)
                if s.enabled and row['observed_score'] is not None and row['weight']>0:
                    self.reward_queue.append(dict(source_homework=row['source_homework'],source=row['source'],
                        student=row['student'],topic=topic,observed=row['observed_score'],signal_homework=h,
                        due=h+s.payment_delay,amount=s.reward_strength*row['weight']*row['observed_score']**s.reward_power/(self.p.N*self.count)))
        for row in list(self.reward_queue):
            if row['due']<=h:
                self.log.tables['teacher_rewards'].append(dict(**row,homework=h,tick=tick))
                self.reward_queue.remove(row)
        return result

    def learn(self,h,t,topic,fraction,before):
        for i,f in enumerate(fraction):
            if f<=0:continue
            for target in range(self.count):
                rate=float(f*self.transfer[topic,target])
                if rate<=0:continue
                old=float(self.knowledge[i,target]);new=old+(1-old)*rate
                self.knowledge[i,target]=new
                self.log.tables['topic_learning'].append(dict(homework=h,tick=t,student=i,source_topic=topic,topic=target,
                    fraction=float(f),transfer=float(self.transfer[topic,target]),before=old,after=float(new)))
        return self.knowledge[:,topic].copy()

    def peer_signal(self,h,t,start,i,j,topic,correct,checks,draws):
        o=self.settings.peer_observation
        checks=np.asarray(checks,bool)
        if o.enabled:
            # Separate Bernoulli observation error, not the hidden retrieval stream.
            u=np.random.default_rng(np.random.SeedSequence([draws.seed,draws.replicate,134,h,start,i])).random(self.p.items)
            observed=np.where(correct,u<o.sensitivity,u>=o.specificity)
        else:observed=np.asarray(correct,bool)
        delay=o.delay_ticks if o.enabled else 0
        stamp=(h-1)*self.p.ticks+t+delay
        signal=dict(homework=h,requester=i,provider=j,topic=topic,start=start,source_tick=t,
            release_absolute=stamp,checked_items=int(checks.sum()),correct_checked=int(np.sum(correct&checks)),
            observed_quality=float(np.mean(observed[checks])) if np.any(checks) else None,
            observed_bits=''.join('1' if x else '0' for x in observed[checks]))
        self.log.tables['peer_signals'].append(signal.copy())
        if np.any(checks):self.peer_queue.append(signal)
        return signal

    def release_peers(self,h,t):
        stamp=(h-1)*self.p.ticks+t
        for row in sorted([r for r in self.peer_queue if r['release_absolute']<=stamp],
                          key=lambda r:(r['release_absolute'],r['homework'],r['source_tick'],r['requester'],r['provider'])):
            q=self.quality_for(row['topic']);i,j=row['requester'],row['provider'];before=float(q[i,j])
            q[i,j]+=self.p.quality_learning_rate*(row['observed_quality']-q[i,j])
            self.log.tables['quality_feedback'].append(dict(homework=h,requester=i,provider=j,topic=row['topic'],tick=t,
                source_homework=row['homework'],source_tick=row['source_tick'],release_absolute=row['release_absolute'],
                checked_items=row['checked_items'],correct_checked=row['correct_checked'],observed_quality=row['observed_quality'],
                Q_before=before,Q_after=float(q[i,j])))
            self.peer_queue.remove(row)

    def close(self):
        self.log.tables['peer_signal_backlog']=[r.copy() for r in self.peer_queue]
        self.log.tables['reward_backlog']=[r.copy() for r in self.reward_queue]
