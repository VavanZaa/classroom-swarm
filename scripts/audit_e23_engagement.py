"""Post-run explanation of curriculum stalls and peer effort, from saved events."""
from collections import defaultdict
from pathlib import Path
import json
import sys
import numpy as np
import pyarrow.parquet as pq

sys.path.insert(0, str(Path(__file__).resolve().parent))
import e23_promising_mechanisms as e


def main():
    e.verify(e.ROOT)
    phase = e.ROOT / 'confirmation'
    sources, records = {}, []
    counts = defaultdict(lambda: dict(events=0, zero_explanation_events=0,
                                      effort_sum=0., discussed_items=0, constructed_items=0))
    for replicate in range(e.PHASES['confirmation'][0]):
        for job in e.config.load_config(phase / f'cohort{replicate:04d}.json'):
            if job['variant'] != 'A33' or job['case'] not in ('kenya', 'lab_single', 'lab_repeated', 'seating', 'composition'):
                continue
            folder = phase / 'raw' / f'cohort{replicate:04d}' / job['condition']
            hashes = e.config.load_config(folder / 'complete.json')['hashes']
            def read(name):
                path = folder / (name + '.parquet')
                if path.name not in hashes:
                    return []
                digest = e.config.sha256(path)
                assert digest == hashes[path.name], path
                sources[str(path.relative_to(e.REPO)).replace('\\', '/')] = digest
                return pq.read_table(path).to_pylist()
            if job['case'] == 'kenya':
                choices = read('curriculum_choices')
                for group, ids in job['groups'].items():
                    if group not in ('low', 'high') or not ids:
                        continue
                    records.append(dict(arm=job['arm'], group=group, replicate=replicate,
                                        section=job['section'], students=len(ids),
                                        first_observed_foundation=json.loads(choices[0]['observed_means'])[0],
                                        last_observed_foundation=json.loads(choices[-1]['observed_means'])[0],
                                        last_observed_application=json.loads(choices[-1]['observed_means'])[1]))
                continue
            sessions = read('helper_sessions')
            contracted = {(r['homework'], r['start'], r['helper'], r['recipient']) for r in sessions if r['completed']}
            for row in read('shared_reasoning'):
                scope = 'contract' if (row['homework'], row['start'], row['provider'], row['requester']) in contracted else 'ordinary'
                for group, ids in job['groups'].items():
                    if row['requester'] not in ids:
                        continue
                    aggregate = counts[job['case'], job['arm'], group, scope]
                    aggregate['events'] += 1
                    aggregate['zero_explanation_events'] += row['explanation_probability'] == 0
                    aggregate['effort_sum'] += row['reasoning_effort']
                    aggregate['discussed_items'] += len(row['correct_bits'])
                    aggregate['constructed_items'] += row['constructed']
    grouped = defaultdict(list)
    for row in records:
        grouped[row['arm'], row['group'], row['replicate']].append(row)
    cohorts = []
    fields = ('first_observed_foundation', 'last_observed_foundation', 'last_observed_application')
    for key, parts in sorted(grouped.items()):
        n = sum(r['students'] for r in parts)
        cohorts.append(dict(arm=key[0], group=key[1], replicate=key[2],
                            **{f: sum(r[f] * r['students'] for r in parts) / n for f in fields}))
    observed = []
    for arm, group in sorted({(r['arm'], r['group']) for r in cohorts}):
        parts = [r for r in cohorts if r['arm'] == arm and r['group'] == group]
        observed.append(dict(arm=arm, group=group,
                             **{f: float(np.mean([r[f] for r in parts])) for f in fields}))
    peer = [dict(case=key[0], arm=key[1], group=key[2], scope=key[3], **value,
                 zero_explanation_share=value['zero_explanation_events'] / value['events'],
                 mean_reasoning_effort=value['effort_sum'] / value['events'])
            for key, value in sorted(counts.items())]
    output = e.REPO / 'docs/reports/E23-engagement-audit-2026-10-10.json'
    assert not output.exists(), 'Preserve completed audit'
    e.config.save_json(output, dict(scope='Exploratory descriptive explanation; peer event counts pooled, no causal identification or fitting',
                                   observed_curriculum=observed, curriculum_cohorts=cohorts, peer_events=peer))
    for path in (Path(__file__), output, e.ROOT / 'design-lock.json', phase / 'run-complete.json', phase / 'raw-inventory.json'):
        sources[str(path.relative_to(e.REPO)).replace('\\', '/')] = e.config.sha256(path)
    e.config.save_json(output.with_suffix('.sources.json'), dict(sources=sources))
    print(json.dumps(dict(observed_curriculum=observed,
                          peer_events=[r for r in peer if r['group'] == 'low']), indent=2), flush=True)


if __name__ == '__main__':
    main()
