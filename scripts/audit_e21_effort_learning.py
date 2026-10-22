"""Read-only E21 audit for the requested effort/learning/incentive design review.

Reads saved results and raw event components. Never simulates or changes an E21
artifact. A new derived audit is written once; repeat execution verifies parity.
"""
from pathlib import Path
import hashlib
import json
import sys

import numpy as np
import pyarrow.parquet as pq

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / 'scripts'))
import e21_study_mechanisms as e21


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    root = e21.ROOT
    e21.verify(root)
    evidence = {}
    manifest_path = REPO / 'docs/experiments/E21-study-mechanism-results.sources.json'
    for name, expected in load(manifest_path)['sources'].items():
        assert digest(REPO / name) == expected, name
        evidence[name] = expected
    evidence[str(manifest_path.relative_to(REPO)).replace('\\', '/')] = digest(manifest_path)
    rows = load(root / 'derived/school-metrics.json')
    inventory = load(root / 'raw-inventory.json')
    ai_means = []
    fields = ('exam', 'exam_active', 'homework', 'knowledge_gain', 'practice_ticks',
              'ai_use', 'teacher_gain_active', 'helper_gain_active')
    for profile in ('reference', 'bridge', 'topics', 'peer_observation', 'combined'):
        for arm in ('none', 'answer', 'tutor'):
            selected = [r for r in rows if (r['case'], r['profile'], r['arm'], r['group']) ==
                        ('ai', profile, arm, 'all')]
            assert len(selected) == 24
            ai_means.append(dict(profile=profile, arm=arm,
                **{key: float(np.mean([r[key] for r in selected])) for key in fields}))

    raw_attempts = []
    for arm in ('none', 'answer', 'tutor'):
        selected = [r for r in inventory if (r['case'], r['profile'], r['arm']) == ('ai', 'combined', arm)]
        assert len(selected) == 24
        counts = dict(bare_attempts=0, positive_base_gain=0, all_incorrect=0,
                      all_incorrect_positive_base_gain=0, at_most_half_correct=0,
                      at_most_half_correct_positive_base_gain=0)
        all_incorrect_gain = 0.
        for item in selected:
            folder = root / 'raw' / f"rep{item['replicate']:04d}" / item['condition']
            assert digest(folder / 'complete.json') == item['complete_sha256']
            evidence[str((folder / 'complete.json').relative_to(REPO)).replace('\\', '/')] = item['complete_sha256']
            complete = load(folder / 'complete.json')
            tables = {}
            for name in ('events', 'packets', 'learning_components'):
                path = folder / (name + '.parquet')
                expected = complete['hashes'][path.name]
                assert digest(path) == expected, str(path)
                evidence[str(path.relative_to(REPO)).replace('\\', '/')] = expected
                tables[name] = pq.read_table(path).to_pylist()
            packets = {r['packet_id']: r for r in tables['packets']}
            components = {(r['homework'], r['tick'], r['student']): r for r in tables['learning_components']}
            for event in tables['events']:
                if event['action'] != 'attempt':
                    continue
                packet = packets[event['packet_id']]
                if packet['origin'] != 'student' or packet['hint_source'] != 'none':
                    continue
                component = components[(event['homework'], event['end'], event['student'])]
                positive = component['practice_gain'] > 0
                bits = packet['item_bits']
                correct = bits.count('1')
                counts['bare_attempts'] += 1
                counts['positive_base_gain'] += positive
                if correct == 0:
                    counts['all_incorrect'] += 1
                    counts['all_incorrect_positive_base_gain'] += positive
                    all_incorrect_gain += component['practice_gain']
                if correct <= len(bits) / 2:
                    counts['at_most_half_correct'] += 1
                    counts['at_most_half_correct_positive_base_gain'] += positive
        raw_attempts.append(dict(arm=arm, classrooms=24, **counts,
            all_incorrect_mean_gain_active_pp=(100 * all_incorrect_gain / counts['all_incorrect'])
                if counts['all_incorrect'] else None))

    teacher_means = []
    contexts = [('star', 'reference', 'small', 'all'), ('star', 'linear_incentives', 'small', 'all'),
                ('star', 'reference', 'regular', 'all'), ('star', 'linear_incentives', 'regular', 'all'),
                ('kenya', 'reference', 'tracked', 'low'), ('kenya', 'combined', 'tracked', 'low'),
                ('kenya', 'resourced_combined', 'tracked', 'low')]
    for case, profile, arm, group in contexts:
        selected = [r for r in rows if (r['case'], r['profile'], r['arm'], r['group']) == (case, profile, arm, group)]
        assert len(selected) == 24
        teacher_means.append(dict(case=case, profile=profile, arm=arm, group=group,
            **{key: float(np.mean([r[key] for r in selected])) for key in
               ('teacher_effort', 'teacher_attention', 'instruction_count', 'mandatory_work', 'practice_ticks')}))
    control = next(r for r in ai_means if r['profile'] == 'combined' and r['arm'] == 'none')
    answer = next(r for r in ai_means if r['profile'] == 'combined' and r['arm'] == 'answer')
    def relative(key):
        return 100 * (answer[key] - control[key]) / control[key]
    result = dict(date='2026-10-07', interpretation='Read-only review, no new simulation or fit.',
        ai_means=ai_means, raw_bare_attempts=raw_attempts, teacher_means=teacher_means,
        combined_answer_vs_none=dict(practice_ticks_change=answer['practice_ticks'] - control['practice_ticks'],
            practice_ticks_relative_pct=relative('practice_ticks'),
            exam_active_change_pp=answer['exam_active'] - control['exam_active'],
            exam_active_relative_pct=relative('exam_active'),
            broad_exam_change_pp=answer['exam'] - control['exam'],
            knowledge_gain_change_pp=answer['knowledge_gain'] - control['knowledge_gain'],
            knowledge_increment_relative_pct=relative('knowledge_gain')),
        caveat='Wrong answers alone do not prove no learning. These counts show unconditional base credit; cognitive processing and corrective content are not observed in that rule.',
        sources=evidence)
    output = REPO / 'docs/reports/E21-effort-learning-audit-2026-10-07.json'
    if output.exists():
        assert load(output) == result, 'Preserve the existing review audit'
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, indent=2, sort_keys=True) + '\n', encoding='utf-8')
    print(json.dumps({key: result[key] for key in ('combined_answer_vs_none', 'raw_bare_attempts')}, indent=2))


if __name__ == '__main__':
    main()
