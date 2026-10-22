"""A31 declarations and observed-only teacher decision geometry (docs/21)."""
from __future__ import annotations
from dataclasses import dataclass,field,asdict,replace,fields
import math
import numpy as np
from .teacher_settings import plan_teacher


def bounded(x,name,lo=0.,hi=1.):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or not lo<=x<=hi:
        raise ValueError(f'{name} must be finite in [{lo},{hi}]')


def integer(x,name,lo=0):
    if isinstance(x,bool) or not isinstance(x,int) or x<lo:raise ValueError(f'{name} must be integer >= {lo}')


@dataclass(frozen=True)
class IncentiveSettings:
    enabled: bool=False
    reward_strength: float=1.
    reward_power: float=1.
    intrinsic_weight: float=.2
    effort_cost: float=.001
    quadratic_cost: float=.002
    fatigue_cost: float=1.
    belief_gain_rate: float=.03
    belief_guidance_gain: float=.01
    payment_delay: int=1
    difficulty_grid: list=field(default_factory=lambda:[.1,.3,.5,.7,.9])


@dataclass(frozen=True)
class WorkloadSettings:
    enabled: bool=False
    admin_bursts: list=field(default_factory=list)
    preparation_ticks: int=0
    topic_switch_ticks: int=0
    fatigue_per_tick: float=.01
    recovery: float=.5
    quality_loss: float=.5


@dataclass(frozen=True)
class TopicSettings:
    enabled: bool=False
    names: list=field(default_factory=lambda:['topic_0','topic_1'])
    schedule: list=field(default_factory=list)
    initial_offsets: list=field(default_factory=list)
    initial_values: list|None=None
    transfer: list=field(default_factory=list)
    helper_consolidation_rate: float=0.


@dataclass(frozen=True)
class PeerObservationSettings:
    enabled: bool=False
    coverage: float=1.
    sensitivity: float=1.
    specificity: float=1.
    delay_ticks: int=0
    topic_specific: bool=True


@dataclass(frozen=True)
class MechanismSettings:
    incentives: IncentiveSettings=field(default_factory=IncentiveSettings)
    workload: WorkloadSettings=field(default_factory=WorkloadSettings)
    topics: TopicSettings=field(default_factory=TopicSettings)
    peer_observation: PeerObservationSettings=field(default_factory=PeerObservationSettings)

    @property
    def active(self):return any(getattr(self,k).enabled for k in ('incentives','workload','topics','peer_observation'))

    def validate(self,p,teacher):
        for branch in ('incentives','workload','topics','peer_observation'):
            if not isinstance(getattr(self,branch).enabled,bool):raise ValueError(branch+'.enabled must be boolean')
        if self.active and p.tutoring_activity not in {'joint_practice','shared_practice'}:
            raise ValueError('A31 features require joint_practice or shared_practice')
        if (self.incentives.enabled or self.workload.enabled) and not teacher.enabled:
            raise ValueError('teacher incentives/workload require an enabled teacher')
        x=self.incentives
        for key in ('reward_strength','intrinsic_weight','fatigue_cost'):bounded(getattr(x,key),key,0,10)
        for key in ('effort_cost','quadratic_cost','belief_gain_rate','belief_guidance_gain'):bounded(getattr(x,key),key)
        bounded(x.reward_power,'reward_power',.1,5);integer(x.payment_delay,'payment_delay')
        if not isinstance(x.difficulty_grid,list) or not x.difficulty_grid:raise ValueError('difficulty_grid must be a nonempty list')
        for d in x.difficulty_grid:bounded(d,'difficulty_grid')
        w=self.workload
        for k in ('preparation_ticks','topic_switch_ticks'):integer(getattr(w,k),k)
        for k in ('fatigue_per_tick','recovery','quality_loss'):bounded(getattr(w,k),k)
        if not isinstance(w.admin_bursts,list) or len(w.admin_bursts) not in (0,p.H):raise ValueError('admin_bursts must have H entries or be empty')
        for b in w.admin_bursts:integer(b,'admin_bursts')
        t=self.topics
        if not isinstance(t.names,list) or not t.names or any(not isinstance(k,str) or not k.strip() for k in t.names) or len(set(t.names))!=len(t.names):
            raise ValueError('topic names must be distinct nonempty strings')
        count=len(t.names)
        if t.enabled and p.exam_items<count:raise ValueError('exam_items must cover every topic')
        if not isinstance(t.schedule,list) or len(t.schedule) not in (0,p.H):raise ValueError('topic schedule must have H entries or be empty')
        for k in t.schedule:
            integer(k,'schedule')
            if k>=count:raise ValueError('schedule topic index out of range')
        if not isinstance(t.initial_offsets,list) or len(t.initial_offsets) not in (0,count):raise ValueError('initial_offsets must have T entries or be empty')
        for k in t.initial_offsets:bounded(k,'initial_offsets',-1,1)
        for value,shape,name in [(t.initial_values,(p.N,count),'initial_values'),(t.transfer,(count,count),'transfer')]:
            if name=='initial_values' and value==[]:raise ValueError('initial_values must be N by T or null')
            if value is not None and value!=[]:
                if not isinstance(value,list):raise ValueError(name+' must be a matrix')
                a=np.asarray(value)
                if a.shape!=shape or a.dtype.kind not in 'fi' or not np.all(np.isfinite(a)) or np.any((a<0)|(a>1)):
                    raise ValueError(name+' has invalid shape/type/bounds')
                if name=='transfer' and not np.all(np.diag(a)==1):raise ValueError('transfer diagonal must be one')
        bounded(t.helper_consolidation_rate,'helper_consolidation_rate')
        o=self.peer_observation
        for k in ('coverage','sensitivity','specificity'):bounded(getattr(o,k),k)
        integer(o.delay_ticks,'delay_ticks')
        if not isinstance(o.topic_specific,bool):raise ValueError('topic_specific must be boolean')


def resolve_mechanisms(value=None):
    if isinstance(value,MechanismSettings):return value
    value={} if value is None else value
    branches={'incentives':IncentiveSettings,'workload':WorkloadSettings,'topics':TopicSettings,'peer_observation':PeerObservationSettings}
    if not isinstance(value,dict) or set(value)-set(branches):raise ValueError('unknown mechanism branch')
    result={}
    for name,cls in branches.items():
        v=value.get(name,{})
        if not isinstance(v,dict) or set(v)-{f.name for f in fields(cls)}:raise ValueError('unknown '+name+' settings')
        result[name]=cls(**v)
    return MechanismSettings(**result)


def topic_arrays(settings,k,horizon):
    t=settings.topics
    count=len(t.names) if t.enabled else 1
    values=np.tile(k[:,None],(1,count))
    if t.enabled:
        if t.initial_values is not None:values=np.array(t.initial_values,dtype=float)
        elif t.initial_offsets:values=np.clip(values+np.array(t.initial_offsets)[None,:],0,1)
    transfer=np.array(t.transfer,dtype=float) if t.enabled and t.transfer else np.eye(count)
    schedule=t.schedule if t.enabled and t.schedule else [h%count for h in range(horizon)]
    return values,transfer,schedule


def incentive_plan(s,teacher,p,estimates,seen,last_served,h,cursor,fatigue):
    """Only estimates, declared settings and past service are accepted here."""
    if not s.enabled:
        plans,queue,end=plan_teacher(teacher,estimates,seen,last_served,h,cursor,p.ticks)
        return plans,queue,end,[]
    mean=float(np.mean(estimates));choices=[]
    targets=sorted(set(s.difficulty_grid+[mean]))
    for budget in range(cursor,teacher.time_budget+1):
        for d in targets:
            runtime=replace(teacher,time_budget=budget,curriculum='fixed',fixed_difficulty=d)
            plans,queue,end=plan_teacher(runtime,estimates,seen,last_served,h,cursor,p.ticks)
            after=np.asarray(estimates,float).copy()
            for plan in plans:
                ids=plan['targets'];before=after[ids]
                if plan['action']=='guidance':
                    fraction=s.belief_guidance_gain*teacher.guidance_strength*(1-before)
                else:
                    own=np.clip(before+.5-d,0,1);known=float(np.clip(teacher.knowledge+.5-d,0,1))
                    usable=(1-own)*known*teacher.teaching_skill*np.clip(1-np.maximum(0,d-before)/p.readiness_band,0,1)
                    fraction=s.belief_gain_rate*teacher.learning_multiplier*usable
                after[ids]+= (1-before)*np.minimum(1,fraction)
            ticks=end-cursor
            intrinsic=s.intrinsic_weight*float(np.mean(after-estimates))
            incentive=s.reward_strength*float(np.mean(after**s.reward_power-np.asarray(estimates)**s.reward_power))
            cost=s.effort_cost*(1+s.fatigue_cost*fatigue)*ticks+s.quadratic_cost*(ticks/max(1,teacher.time_budget))**2
            choices.append(dict(homework=h,difficulty=d,budget=budget,teaching_ticks=ticks,
                estimates=np.asarray(estimates).tolist(),predicted_after=after.tolist(),intrinsic=intrinsic,
                expected_reward=incentive,cost=cost,utility=intrinsic+incentive-cost,plans=plans,queue=queue,end=end))
    best=min(choices,key=lambda c:(-c['utility'],c['teaching_ticks'],abs(c['difficulty']-mean),c['difficulty'],c['budget']))
    rows=[{k:v for k,v in c.items() if k not in {'plans','queue','end'}}|{'selected':c is best} for c in choices]
    return best['plans'],best['queue'],best['end'],rows
