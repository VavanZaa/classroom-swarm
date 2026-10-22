"""Post-run descriptive pathway audit; reads frozen E23, never changes settings."""
from collections import defaultdict
from pathlib import Path
import json
import sys
import numpy as np
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e23_promising_mechanisms as e


def average(values):
    return float(np.mean(values)) if values else None


def main():
    root = e.ROOT
    e.verify(root)
    phase = root / 'confirmation'
    complete = e.config.load_config(phase / 'run-complete.json')
    for name, digest in complete['hashes'].items():
        assert e.config.sha256(phase / name) == digest, name
    rows, sources, checked = [], {}, 0
    names = ('topic_initial', 'topic_states', 'curriculum_choices',
             'curriculum_readiness', 'learning_doses', 'teacher_actions',
             'teacher_forecasts', 'shared_reasoning', 'participation_forecast_evidence')
    for replicate in range(e.PHASES['confirmation'][0]):
        for job in e.config.load_config(phase / f'cohort{replicate:04d}.json'):
            folder = phase / 'raw' / f'cohort{replicate:04d}' / job['condition']
            record = e.config.load_config(folder / 'complete.json')
            sources[str((folder / 'complete.json').relative_to(e.REPO)).replace('\\', '/')] = e.config.sha256(folder / 'complete.json')
            tables = {}
            for name in names:
                path = folder / f'{name}.parquet'
                if path.name not in record['hashes']:
                    tables[name] = []
                    continue
                assert e.config.sha256(path) == record['hashes'][path.name], path
                checked += 1
                tables[name] = pq.read_table(path).to_pylist()
            h = job['resolved']['params']['H']
            curriculum = job['resolved']['design']['curriculum']
            levels = len(curriculum['levels']) if curriculum['enabled'] else 0
            initial = {(r['student'], r['topic']): r['knowledge'] for r in tables['topic_initial']}
            final = {(r['student'], r['topic']): r['knowledge'] for r in tables['topic_states'] if r['homework'] == h}
            choices = tables['curriculum_choices']
            forecasts = tables['teacher_forecasts']
            group_candidates = {(r['homework'], r['tick']) for r in forecasts if r.get('scope') == 'group'}
            group_selected = {(r['homework'], r['tick']) for r in forecasts if r.get('scope') == 'group' and r['selected']}
            for group, ids_list in job['groups'].items():
                if not ids_list:
                    continue
                ids = set(ids_list)
                n = len(ids)
                row = dict(case=job['case'], profile=job['profile'], arm=job['arm'],
                           variant=job['variant'], group=group, replicate=replicate,
                           section=job['section'], students=n)
                for level in range(3):
                    row[f'lesson_level_{level}_share'] = average([float(r['level'] == level) for r in choices])
                    keys = [key for key in initial if key[0] in ids and levels and key[1] % levels == level]
                    row[f'level_{level}_initial'] = average([100 * initial[k] for k in keys])
                    row[f'level_{level}_gain'] = average([100 * (final[k] - initial[k]) for k in keys])
                    row[f'level_{level}_initial_mastered'] = average([float(initial[k] >= 1 - 1e-12) for k in keys])
                row['prerequisite_readiness'] = average([r['readiness'] for r in tables['curriculum_readiness'] if r['student'] in ids])
                for source in ('attempt', 'teacher', 'coaching', 'guided', 'helper'):
                    doses = [r for r in tables['learning_doses'] if r['student'] in ids and r['source'] == source]
                    row[source + '_duration_per_student_block'] = sum(r['duration'] for r in doses) / (n * h)
                    row[source + '_dose_per_student_block'] = sum(r['dose'] for r in doses) / (n * h)
                    row[source + '_productive_event_share'] = average([float(r['dose'] > 0) for r in doses])
                reasoning = [r for r in tables['shared_reasoning'] if r['requester'] in ids]
                row['reasoning_sessions_per_student_block'] = len(reasoning) / (n * h)
                row['constructed_items_per_student_block'] = sum(r['constructed'] for r in reasoning) / (n * h)
                row['constructed_fraction_of_discussed_items'] = sum(r['constructed'] for r in reasoning) / sum(len(r['correct_bits']) for r in reasoning) if reasoning else None
                row['group_feasible_planning_rounds_per_block'] = len(group_candidates) / h
                row['group_selected_planning_rounds_per_block'] = len(group_selected) / h
                for action in ('instruction', 'guidance', 'coaching', 'followup'):
                    events = [r for r in tables['teacher_actions'] if r['action'] == action]
                    row[action + '_teacher_ticks_per_block'] = sum(r['cost'] for r in events) / h
                evidence = [r for r in tables['participation_forecast_evidence'] if r['student'] in ids]
                dates = sorted({r['source_homework'] for r in evidence})
                for label, date in [('first', dates[0] if dates else None), ('last', dates[-1] if dates else None)]:
                    records = [r for r in evidence if r['source_homework'] == date]
                    row[label + '_participation_brier'] = average([(r['predicted_probability'] - int(r['participated'])) ** 2 for r in records])
                rows.append(row)
    grouped = defaultdict(list)
    ignore = {'case', 'profile', 'arm', 'variant', 'group', 'replicate', 'section', 'students'}
    for row in rows:
        grouped[tuple(row[k] for k in ('case', 'profile', 'arm', 'variant', 'group', 'replicate'))].append(row)
    cohorts = []
    for key, parts in sorted(grouped.items()):
        n = sum(r['students'] for r in parts)
        cohorts.append(dict(zip(('case', 'profile', 'arm', 'variant', 'group', 'replicate'), key)) | {
            metric: sum(r[metric] * r['students'] for r in parts) / n if all(r[metric] is not None for r in parts) else None
            for metric in parts[0] if metric not in ignore})
    by_condition = defaultdict(list)
    for row in cohorts:
        by_condition[tuple(row[k] for k in ('case', 'profile', 'arm', 'variant', 'group'))].append(row)
    means = []
    for key, parts in sorted(by_condition.items()):
        means.append(dict(zip(('case', 'profile', 'arm', 'variant', 'group'), key)) | {
            metric: average([r[metric] for r in parts]) if all(r[metric] is not None for r in parts) else None
            for metric in parts[0] if metric not in ignore})
    output = e.REPO / 'docs/reports/E23-pathway-audit-2026-10-10.json'
    assert not output.exists(), 'Preserve completed audit'
    e.config.save_json(output, dict(scope='Post-run descriptive audit, no parameter fitting or new confirmatory test',
                                   checked_raw_files=checked, class_rows=rows, cohort_rows=cohorts, condition_means=means))
    for path in (Path(__file__), output, root / 'design-lock.json', phase / 'run-complete.json', phase / 'raw-inventory.json'):
        sources[str(path.relative_to(e.REPO)).replace('\\', '/')] = e.config.sha256(path)
    e.config.save_json(output.with_suffix('.sources.json'), dict(checked_raw_files=checked, sources=sources))
    print(f'Post-run audit saved: {output}; {checked:,} raw files checked.', flush=True)


if __name__ == '__main__':
    main()
