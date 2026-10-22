"""A33 independently optional, strictly declared numerical hypotheses (docs/25)."""
from dataclasses import dataclass, field, fields, replace
import numpy as np
from .mechanism_settings import bounded, integer, topic_arrays, TopicSettings

@dataclass(frozen=True)
class Curriculum:
    enabled: bool = False
    levels: list = field(default_factory=lambda: ['foundation','application','advanced'])
    offsets: list = field(default_factory=lambda: [.25,0.,-.25])
    prerequisites: list = field(default_factory=lambda: [-1,0,1])
    initial_values: list | None = None
    adaptive: bool = True
    fixed_level: int = 0
    level_schedule: list = field(default_factory=list)
    mastery_threshold: float = .7
    readiness_width: float = .3
    pretest_items: int = 30
    independent_teacher_accuracy: bool = True

@dataclass(frozen=True)
class TeacherForecast:
    enabled: bool = False
    uncertainty: float = .15
    update_rate: float = .2
    initial_bias: float = 0.

@dataclass(frozen=True)
class GroupPreparation:
    enabled: bool = False
    delivery_ticks: int = 2
    feedback_ticks: int = 1
    feedback_capacity: int = 30

@dataclass(frozen=True)
class SharedReasoning:
    enabled: bool = False
    reasoning_probability: float = .8

@dataclass(frozen=True)
class PromisingSettings:
    curriculum: Curriculum = field(default_factory=Curriculum)
    teacher_forecast: TeacherForecast = field(default_factory=TeacherForecast)
    group_preparation: GroupPreparation = field(default_factory=GroupPreparation)
    shared_reasoning: SharedReasoning = field(default_factory=SharedReasoning)

    @property
    def active(self):
        return any(getattr(self,k).enabled for k in BRANCHES)

    def validate(self,p,teacher,mechanisms,x):
        for name in BRANCHES:
            b=getattr(self,name)
            if not isinstance(b.enabled,bool): raise ValueError(name+'.enabled must be boolean')
            for f in fields(b):
                v=getattr(b,f.name)
                if f.type is bool and not isinstance(v,bool): raise ValueError(f.name+' must be boolean')
                if f.type is float: bounded(v,f.name,-1 if f.name=='initial_bias' else 0,1)
                if f.type is int: integer(v,f.name)
        if self.active and not x.learning_process.enabled: raise ValueError('A33 needs productive learning_process')
        if (self.teacher_forecast.enabled or self.group_preparation.enabled) and not (teacher.enabled and x.teacher_work.enabled):
            raise ValueError('teacher design needs enabled teacher and teacher_work')
        if self.group_preparation.enabled and not (self.teacher_forecast.enabled and x.test_preparation.enabled):
            raise ValueError('group preparation needs forecasts and test_preparation')
        c=self.curriculum; l=len(c.levels)
        if not isinstance(c.levels,list) or not l or any(not isinstance(v,str) or not v for v in c.levels) or len(set(c.levels))!=l:
            raise ValueError('levels must be distinct names')
        if len(c.offsets)!=l or len(c.prerequisites)!=l: raise ValueError('level arrays have wrong dimensions')
        for v in c.offsets: bounded(v,'offset',-1,1)
        for k,v in enumerate(c.prerequisites):
            if isinstance(v,bool) or not isinstance(v,int) or v < -1 or v>=k: raise ValueError('prerequisites must precede skill or be -1')
        if c.fixed_level>=l or c.readiness_width<=0 or c.pretest_items<1: raise ValueError('invalid curriculum threshold/test/level')
        if not isinstance(c.level_schedule,list) or len(c.level_schedule) not in (0,p.H): raise ValueError('level_schedule needs H entries or empty')
        for v in c.level_schedule:
            integer(v,'level_schedule')
            if v>=l: raise ValueError('level_schedule out of range')
        domains=len(mechanisms.topics.names) if mechanisms.topics.enabled else 1
        if c.enabled and p.exam_items<domains*l: raise ValueError('exam_items must cover all curriculum skills')
        if c.initial_values is not None:
            a=np.asarray(c.initial_values)
            if a.shape!=(p.N,domains*l) or a.dtype.kind not in 'fi' or not np.all(np.isfinite(a)) or np.any((a<0)|(a>1)):
                raise ValueError('initial_values must be bounded N by domains*levels')
        if self.teacher_forecast.uncertainty<=0: raise ValueError('forecast uncertainty must be positive')
        g=self.group_preparation
        if min(g.delivery_ticks,g.feedback_capacity)<1: raise ValueError('group duration/capacity must be positive')

BRANCHES={'curriculum':Curriculum,'teacher_forecast':TeacherForecast,'group_preparation':GroupPreparation,'shared_reasoning':SharedReasoning}

def resolve_promising(value=None):
    if isinstance(value,PromisingSettings): return value
    value={} if value is None else value
    if not isinstance(value,dict) or set(value)-set(BRANCHES): raise ValueError('unknown A33 design branch')
    parts={}
    for name,cls in BRANCHES.items():
        b=value.get(name,{})
        if not isinstance(b,dict) or set(b)-{f.name for f in fields(cls)}: raise ValueError('unknown '+name+' fields')
        parts[name]=cls(**b)
    return PromisingSettings(**parts)

def centered_skills(k,offsets):
    k=np.asarray(k,float); offsets=np.asarray(offsets,float)
    lo=np.full(len(k),-2.); hi=np.full(len(k),2.)
    for _ in range(60):
        mid=(lo+hi)/2
        mean=np.clip(k[:,None]+offsets+mid[:,None],0,1).mean(axis=1)
        lo=np.where(mean<k,mid,lo); hi=np.where(mean>=k,mid,hi)
    return np.clip(k[:,None]+offsets+((lo+hi)/2)[:,None],0,1)

def expand_curriculum(settings,x,k,p,c):
    if not c.enabled: return settings,x
    original,transfer,schedule=topic_arrays(settings,k,p.H); domains=original.shape[1]; l=len(c.levels)
    values=np.concatenate([centered_skills(original[:,d],c.offsets) for d in range(domains)],axis=1)
    if c.initial_values is not None: values=np.asarray(c.initial_values,float)
    names=settings.topics.names if settings.topics.enabled else ['core']
    t=TopicSettings(enabled=True,names=[f'{name}:{level}' for name in names for level in c.levels],
        initial_values=values.tolist(),schedule=[int(d)*l for d in schedule],
        transfer=np.kron(transfer,np.eye(l)).tolist(),helper_consolidation_rate=settings.topics.helper_consolidation_rate)
    exams=[{**e,'topic_weights':[w/l for w in e['topic_weights'] for _ in range(l)]} for e in x.test_preparation.exams]
    if not exams:
        from .effort_settings import default_exams
        exams=[{**e,'topic_weights':[w/l for w in e['topic_weights'] for _ in range(l)]} for e in default_exams(x.test_preparation,domains)]
    return replace(settings,topics=t),replace(x,test_preparation=replace(x.test_preparation,exams=exams))
