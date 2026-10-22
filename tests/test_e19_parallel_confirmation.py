"""The execution transport preserves deterministic raw tables and reuse identity."""
from copy import deepcopy
from scripts import e19_teacher_studies as e19
from scripts import run_e19_parallel_confirmation as driver


def test_transport_matches_serial_simulation_raw_tables_and_settings(tmp_path):
    job=deepcopy(next(e19.jobs('development',0)))
    job['config']['params']['H']=1
    job['resolved']['params']['H']=1
    record,reused=driver.execute((job,tmp_path))
    assert not reused
    loaded=e19.load_raw(tmp_path/record['path'])
    e19.check_identity(loaded,job)
    r=job['resolved'];p=e19.TutoringParams(**r['params'])
    expected=e19.simulate_teacher(p,e19.make_graph(r['network'],p.N,job['seed'],0),
        e19.PublicAIDraws(job['seed'],0,p.N,p.items,p.exam_items),
        condition=job['name'],initial=r['initial'],teacher=r['teacher'])
    assert expected.tables==loaded.tables
    for key,value in expected.manifest.items():assert loaded.manifest[key]==value
    again,reused=driver.execute((job,tmp_path))
    assert again==record and reused
    parts,inventory=driver.audit_job((job,tmp_path))
    assert inventory['complete_sha256']==record['complete_sha256']
    for key,value in parts:
        group=key[4]
        ids=set(job['cohort']['student_ids'] if group=='all' else job['cohort'][group])
        local=[i for i,g in enumerate(job['global_ids']) if g in ids]
        assert value==e19.metrics(expected,local)
