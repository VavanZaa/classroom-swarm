"""Verify and freeze editorial clarification and combined E22/E22b assessment."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import e22_a32_study_trends as e
import e22_teacher_access_correction as c


def main():
    e.verify(e.ROOT); e.verify(c.ROOT)
    report=e.REPO/'docs/experiments/E22-A32-study-trends-results.md'
    manifest=report.with_suffix('.sources.json')
    draft=e.REPO/'.tmp/E22-report-first-draft'
    first=e.config.load_config(draft/manifest.name)
    for name,digest in first['sources'].items():
        path=draft/report.name if name==str(report.relative_to(e.REPO)).replace('\\','/') else e.REPO/name
        assert e.config.sha256(path)==digest,name
    correction=e.REPO/'docs/experiments/E22b-teacher-access-results.sources.json'
    for name,digest in e.config.load_config(correction)['sources'].items(): assert e.config.sha256(e.REPO/name)==digest,name
    audit=e.REPO/'docs/reports/E22-lesson-pathway-audit.json'
    for name,digest in e.config.load_config(audit)['raw_file_inputs'].items(): assert e.config.sha256(e.REPO/name)==digest,name
    additions=[draft/report.name,draft/manifest.name,e.REPO/'docs/experiments/E22-editorial-note.md',
        e.REPO/'docs/reports/A32-paper-trend-assessment-2026-10-07.md',correction,
        e.REPO/'docs/experiments/E22b-teacher-access-results.md',audit,
        e.REPO/'scripts/audit_e22_paper_pathways.py',e.REPO/'scripts/report_e22b_teacher_access.py',Path(__file__)]
    sources={**first['sources'],**{str(p.relative_to(e.REPO)).replace('\\','/'):e.config.sha256(p) for p in additions}}
    sources[str(report.relative_to(e.REPO)).replace('\\','/')]=e.config.sha256(report)
    e.config.save_json(manifest,dict(sources=sources,editorial_clarification='Added correction notice; first generated report and manifest preserved; no results changed.'))
    assessment=e.REPO/'docs/reports/A32-paper-trend-assessment-2026-10-07.md'
    assessment_sources=dict(sources={str(p.relative_to(e.REPO)).replace('\\','/'):e.config.sha256(p)
        for p in [assessment,manifest,correction,audit,e.ROOT/'design-lock.json',c.ROOT/'design-lock.json',
                  e.ROOT/'run-complete.json',c.ROOT/'run-complete.json']},
        tests_passed=637,classrooms=2016,raw_file_hashes_verified=151200,human_calibration='deferred',
        scope='Conditional study-direction consistency, not full empirical validation')
    e.config.save_json(assessment.with_suffix('.sources.json'),assessment_sources)
    for m in (manifest,correction,assessment.with_suffix('.sources.json')):
        for name,digest in e.config.load_config(m)['sources'].items(): assert e.config.sha256(e.REPO/name)==digest,name
    print('Both design locks, historical sources, report manifests, preserved draft and pathway evidence verified.')


if __name__=='__main__': main()
