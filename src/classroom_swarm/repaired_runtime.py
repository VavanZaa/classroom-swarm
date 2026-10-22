"""A34 reconnects private feedback and service beliefs, without hidden information."""
from .promising_runtime import PromisingRuntime


class RepairedRuntime(PromisingRuntime):
    def __init__(self, *args):
        super().__init__(*args)
        self.log.tables['policy_inputs'] = []

    def choices(self, scores, i, h, t, c, estimate, hint, has_hint, remaining, *, benefits, access):
        # Use the inherited evaluator for other actions, with attempt/hint removed
        # so their effort candidates are recorded exactly once.
        out, chosen = super().choices({k:v for k,v in scores.items() if k not in ('attempt','hint')},
            i,h,t,c,estimate,hint,has_hint,remaining)
        row = dict(homework=h,tick=t,student=i,confidence=c,benefits=list(map(float,benefits)),
            estimate=estimate,hint_access=float(access[0]),request_cost=self.cost(i,'guided',0.,self.p.peer_request_ticks),
            attempt_belief=None,attempt_utility=None,hint_belief=None,hint_utility=None)
        for action,index in [('attempt',0),('hint',1)]:
            if action not in scores: continue
            belief = self.p.confidence_weight * benefits[index] + (1-self.p.confidence_weight)*c
            kind = 'attempt' if action=='attempt' else 'guided'
            duration = self.p.attempt_ticks if action=='attempt' else self.p.guided_practice_ticks
            assistance = min(1.,hint) if has_hint or action=='hint' else 0.
            effort,utility=self.best_effort(i,kind,duration,float(belief),assistance,
                future=self.student_traits['future_test_value'][i],h=h,t=t)
            value=utility-estimate
            if action=='hint': value=access[0]*value-row['request_cost']
            out[action]=float(value); chosen[action]=effort
            row[action+'_belief']=float(belief); row[action+'_utility']=float(utility)
        self.log.tables['policy_inputs'].append(row)
        return out,chosen
