"""Reconstruct A32 learning, work and measurements from raw evidence."""
import json
import math
import numpy as np
from .effort_runtime import dose_fraction
from .effort_settings import resolve_effort, contract_value
from .mechanism_validation import validate_mechanism_log


def validate_effort_log(log, p=None):
    if log.manifest['model'] != 'A32-v4.7-effort-learning':
        return validate_mechanism_log(log)
    if p is None:
        from .tutoring_settings import TutoringParams
        p = TutoringParams(**log.manifest['params'])
    errors = []; x = resolve_effort(log.manifest['extensions'])
    def check(ok, reason):
        if not ok: errors.append(reason)
    for row in log.tables['learning_doses']:
        dose = row['effort'] * row['duration'] / x.learning_process.reference_ticks
        if x.learning_process.enabled:
            dose *= row['attention'] * row['processed']
            check(row['attention'] == (row['attention_draw'] < row['attention_probability']), 'attention gate mismatch')
            check(row['processed'] == (row['processing_draw'] < row['processing_probability']), 'processing gate mismatch')
            check(abs(dose - row['dose']) < 1e-12, 'productive dose mismatch')
        expected = dose_fraction(row['alpha'], row['divisor'], row['multiplier'], row['dose'] * row['concept_share'])
        if not row.get('rate_rule','').startswith('legacy'):
            check(abs(expected - row['fraction']) < 1e-12, 'learning fraction mismatch')
        check(row['concept_share'] + row['format_share'] <= 1 + 1e-12, 'duplicate dose allocation')
    ledger = {(r['student'], r['topic']): r['knowledge'] for r in log.tables['topic_initial']}
    doses = {r['event_id']: r for r in log.tables['learning_doses']}
    check(len(doses) == len(log.tables['learning_doses']), 'duplicate learning event identity')
    for row in log.tables['topic_learning']:
        key = row['student'], row['topic']
        check(abs(ledger[key] - row['before']) < 1e-10, 'topic learning continuity')
        expected = row['before'] + (1 - row['before']) * row['fraction'] * row['transfer']
        check(abs(expected - row['after']) < 1e-10 and 0 <= row['after'] <= 1, 'topic learning reconstruction')
        linked = json.loads(row['source_event_ids'])
        check(bool(linked) and all(identity in doses for identity in linked), 'missing causal dose reference')
        if linked and all(identity in doses for identity in linked):
            fraction = 1 - np.prod([1 - doses[identity]['fraction'] for identity in linked])
            check(abs(fraction - row['fraction']) < 1e-12, 'dose-to-gain reconstruction')
        ledger[key] = row['after']
    for row in log.tables['format_learning']:
        expected = row['before'] + (1 - row['before']) * row['fraction'] * row['transfer']
        check(abs(expected - row['after']) < 1e-12 and 0 <= row['after'] <= 1, 'format learning reconstruction')
    for row in log.tables['student_costs']:
        cognitive=(x.learning_process.minimum_operational_effort+row['effort'])*(row['end']-row['start'])
        expected=(row['effort_aversion']*row['cost_multiplier']+x.learning_process.fatigue_cost*row['fatigue_before'])*cognitive/p.effort_time_scale
        check(abs(cognitive-row['cognitive_effort_ticks'])<1e-12 and abs(expected-row['cost'])<1e-12, 'student effort cost mismatch')
        expected_fatigue=min(1.,row['fatigue_before']+x.learning_process.fatigue_per_effort_tick*cognitive) if x.learning_process.enabled else row['fatigue_before']
        check(abs(expected_fatigue-row['fatigue_after'])<1e-12, 'student fatigue mismatch')
    for row in log.tables['task_responses']:
        supported=row['pre_learning_K']+row['assistance']*(1-row['pre_learning_K'])
        execution=row['effort']+(1-row['effort'])*row['assistance']
        expected=x.learning_process.guess_probability+execution*(supported-x.learning_process.guess_probability)
        check(abs(expected-row['probability'])<1e-12, 'pre-learning task performance mismatch')
        packet=next((r for r in log.tables['packets'] if r['packet_id']==row['packet_id']),None)
        check(packet is not None, 'task response lacks packet')
        if packet:
            bits=''.join('1' if u<expected else '0' for u in json.loads(row['item_draws']))
            check(bits==packet['item_bits'] and abs(packet['probability']-expected)<1e-12, 'task packet mismatch')
    if x.teacher_work.enabled:
        for h in range(1, p.H + 1):
            rows = sorted([r for r in log.tables['teacher_work_schedule'] if r['homework'] == h and r['cost']], key=lambda r: r['start'])
            check(sum(r['cost'] for r in rows) <= x.teacher_work.total_budget, 'teacher exceeds total work budget')
            check(all(a['end'] <= b['start'] for a, b in zip(rows, rows[1:])), 'teacher services overlap')
            for r in rows:
                check(r['end'] - r['start'] == r['cost'], 'teacher work duration mismatch')
                check(-x.teacher_work.before_class_ticks <= r['start'] and r['end'] <= p.ticks + x.teacher_work.after_class_ticks, 'teacher work outside timetable')
            if not x.teacher_work.allow_instruction_crowdout:
                delivered = sum(r['cost'] for r in rows if r['kind'] == 'instruction')
                check(delivered >= x.teacher_work.protected_instruction_ticks, 'protected lesson lost')
    for row in log.tables['assessment_items']:
        expected = row['core_probability'] + (1 - row['core_probability']) * row['familiarity'] * next(
            d['format_loading'] for d in log.tables['assessment_design'] if d['name'] == row['assessment'])
        check(abs(expected - row['probability']) < 1e-12, 'exam probability mismatch')
        check(row['potential_correct'] == (row['potential_draw'] < row['probability']), 'potential exam outcome mismatch')
    for row in log.tables['assessment_scores']:
        items = [r for r in log.tables['assessment_items'] if r['homework'] == row['homework'] and r['student'] == row['student'] and r['assessment'] == row['assessment']]
        potential = np.mean([r['potential_correct'] for r in items])
        check(abs(potential - row['potential_score']) < 1e-12, 'exam score mismatch')
        check((row['score'] is not None) == row['participated'], 'missing score overwritten')
        if row['participated']: check(abs(potential - row['score']) < 1e-12, 'observed score mismatch')
    for row in log.tables['contract_observations']:
        expected = contract_value(x.teacher_work.contract, json.loads(row['scores']), json.loads(row['baseline']), row['source'], row['form'])
        check(abs(row['amount'] - expected) < 1e-12, 'teacher payment contract mismatch')
    for row in log.tables['contract_payments']:
        check(row['homework'] >= row['due'] and row['due'] == row['signal_homework'] + x.teacher_work.contract.payment_delay, 'premature teacher payment')
    for row in log.tables['helper_payments']:
        check(row['homework'] >= row['due'], 'premature helper payment')
        source = next((r for r in log.tables['helper_checkpoints'] if r['source_homework']==row['source_homework']
            and r['helper']==row['helper'] and r['recipient']==row['recipient']), None)
        check(source is not None, 'helper payment lacks observed checkpoint')
        if source:
            check(row['amount']==(x.helper_contract.prize if source['winner'] else 0.), 'helper prize mismatch')
            check(row['due']==source['homework']+x.helper_contract.payment_delay, 'helper payment delay mismatch')
    for row in log.tables['helper_checkpoints']:
        if row['score'] is not None: check(abs(row['progress'] - (row['score'] - row['baseline'])) < 1e-12, 'helper progress mismatch')
    # A32 requires scarce helper time for its explicit reward protocol. Legacy
    # helper-time-free and shared-practice controls retain their own semantics.
    for i in range(p.N):
        for h in range(1, p.H + 1):
            rows = sorted([r for r in log.tables['events'] if r['student'] == i and r['homework'] == h and r['occupied'] and r['end'] > r['start']], key=lambda r: r['start'])
            check(all(a['end'] <= b['start'] for a, b in zip(rows, rows[1:])), 'student activities overlap')
            check(all(0 <= r['start'] <= r['end'] <= p.ticks for r in rows), 'student time outside classroom')
    if errors: raise AssertionError('; '.join(dict.fromkeys(errors)))
