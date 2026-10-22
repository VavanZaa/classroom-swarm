"""Post-lock read-only counterexamples discovered during the E24 source audit."""
from pathlib import Path
from copy import deepcopy
import sys
import json
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tests'))
from test_v4_promising import declaration, run, constant
from classroom_swarm import promising_config as config
from classroom_swarm.effort_settings import resolve_effort, RewardContract, contract_value
from classroom_swarm.effort_runtime import EffortRuntime
from classroom_swarm.tutoring_settings import TutoringParams, tutoring_scores
from classroom_swarm.teacher_settings import resolve_teacher
from classroom_swarm.mechanism_settings import resolve_mechanisms
from classroom_swarm.v3 import TraitState
from classroom_swarm.v4 import V4Log
from classroom_swarm.v4_public_ai import PublicAIDraws

REPO = Path(__file__).resolve().parents[1]
OUTPUT = REPO / 'docs/reports/E24-configuration-authority-probes-2026-10-10.json'


def main():
    assert not OUTPUT.exists(), 'preserve prior audit evidence'
    findings = []
    c = declaration(h=4, teacher=False)
    c['params'].update(allow_hint=True, allow_answer=True, ai_mode='tutor', ai_start=1)
    c['network']['edges'] = [[0, 1], [2, 3]]
    for field in ('benefit_attempt', 'benefit_hint'):
        a_config, b_config = deepcopy(c), deepcopy(c)
        a_config['initial'][field] = constant(0.); b_config['initial'][field] = constant(1.)
        a, b = run(a_config), run(b_config)
        def selected(log):
            return [r for r in log.tables['events'] if r['action'].startswith('choose_')]
        equal = selected(a) == selected(b) and a.tables['topic_states'] == b.tables['topic_states'] and a.tables['assessment_scores'] == b.tables['assessment_scores']
        assert equal
        findings.append(dict(probe='disconnected_benefit', field=field, endpoints=[0., 1.],
                             selected_choices=len(selected(a)), choice_and_outcome_tables_identical=equal,
                             grade_feedback_records=len(a.tables['homework_feedback']), scope='productive-learning branch; not legacy comparator'))
    # Probe the effective score function directly, holding availability and observed
    # quality constant. Changing expected service success affects the old score,
    # but the replacement drops that term from the productive-learning score.
    resolved = config.resolve_config(c)['conditions'][0]
    p = TutoringParams(**resolved['params']); x = resolve_effort(resolved['extensions'])
    traits = TraitState(np.full(4, .45), np.full(4, .0584), np.full(4, .1))
    runtime = EffortRuntime(resolve_mechanisms(resolved['mechanisms']), resolve_teacher(resolved['teacher']), p,
                           traits.K0, np.full((4, 4), .5), V4Log({}), x, PublicAIDraws(88101, 0, 4, p.items, p.exam_items), traits)
    scores = []
    for access in (.05, .95):
        old = tutoring_scores(p, .5, .5, np.full(5, .5), .1, 0., False, False,
                              [access, .5], True, True, p.ticks, quality=.5, ai_available=True)
        new, _ = runtime.choices(old, 0, 1, 0, .5, 0., p.perceived_hint_boost * .5, False, p.ticks)
        scores.append(dict(expected_hint_access=access, old_hint_score=old['hint'], effective_hint_score=new['hint']))
    assert scores[0]['old_hint_score'] != scores[1]['old_hint_score']
    assert scores[0]['effective_hint_score'] == scores[1]['effective_hint_score']
    findings.append(dict(probe='discarded_hint_service_probability', scores=scores,
                         scope='conditional score given a feasible partner; access still affects target selection and reciprocity elsewhere'))
    c = declaration(h=1, teacher=False)
    c['initial'].update(knowledge=constant(.9), confidence={'kind': 'from_knowledge'})
    c['extensions']['learning_process']['effort_grid'] = [0.]
    c['design']['curriculum'].update(enabled=True, adaptive=False, initial_values=[[.1, .2, .3]] * 4)
    a = run(c)
    confidence = [r['confidence'] for r in a.tables['initial_states']]
    effective = [r['K0'] for r in a.tables['traits']]
    assert confidence == [.9] * 4 and np.allclose(effective, .2)
    findings.append(dict(probe='explicit_skill_override_reference', base_declared_knowledge=.9,
                         actual_initial_mean=effective, derived_initial_confidence=confidence,
                         artificial_knowledge_gain=False,
                         workaround='Declare confidence/benefit priors explicitly when an explicit skill matrix changes initial means.'))
    c = declaration(h=3); c['design']['curriculum']['enabled'] = True
    a = run(c); c['extensions']['teacher_work']['preparation_quality_bonus'] = 0.; b = run(c)
    equal = all(a.tables[name] == b.tables[name] for name in ('teacher_actions', 'learning_doses', 'topic_states', 'assessment_scores'))
    assert equal
    findings.append(dict(probe='saturated_preparation_quality', teacher_skill=1., bonus_endpoints=[.3, 0.],
                         prep_ticks=1, outcomes_and_actions_identical=equal,
                         limitation='Group eligibility may still require preparation stock; removing prep changes resources.'))
    # The exact expected value over an exam-score distribution differs from paying
    # the contract at a point forecast, even with no missingness.
    contract = RewardContract(power=2.)
    plug_in = contract_value(contract, [.5], [0.])
    exact_one_item = .5 * contract_value(contract, [0.], [0.]) + .5 * contract_value(contract, [1.], [0.])
    assert plug_in == .25 and exact_one_item == .5
    findings.append(dict(probe='nonlinear_point_score_forecast', power=2., correctness_probability=.5,
                         one_item_plug_in=plug_in, one_item_exact=exact_one_item,
                         sixty_item_plug_in=.25, sixty_item_exact=.25 + .25 / 60,
                         scope='participation integration may be exact conditional on a point score; nonlinear score uncertainty is omitted'))
    sources = sorted((REPO / 'src/classroom_swarm').glob('*.py')) + [Path(__file__), REPO / 'tests/test_v4_promising.py']
    config.save_json(OUTPUT, dict(classification='post-lock exploratory correctness probes; no engine changes, coefficient fitting or field-validation claims', findings=findings))
    config.save_json(OUTPUT.with_name(OUTPUT.stem + '.sources.json'), dict(sources={str(path.relative_to(REPO)).replace('\\', '/'): config.sha256(path) for path in sources + [OUTPUT]}))
    print(json.dumps(findings, indent=2))


if __name__ == '__main__': main()
