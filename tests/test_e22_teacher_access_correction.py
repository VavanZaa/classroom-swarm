from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import e22_teacher_access_correction as c


def test_correction_changes_only_the_duplicate_cost_preserving_pairing():
    before={j['condition']:j for j in c.original_jobs(0) if j['case']=='teacher_rewards'}
    after=c.corrected_jobs(0)
    assert len(after)==8
    for j in after:
        old=before[j['condition']]
        differences=c.e.config.legacy.differences(old,j)
        active=j['resolved']['extensions']['test_preparation']['participation']
        assert differences==(['resolved.extensions.test_preparation.participation_cost'] if active else [])
        assert j['seed']==old['seed'] and j['global_ids']==old['global_ids']
        if active:
            t=j['resolved']['extensions']['test_preparation']
            assert all(d['access_cost']+t['participation_cost']==.6 for d in t['exams'])
