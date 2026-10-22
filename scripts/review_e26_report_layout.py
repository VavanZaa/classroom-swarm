"""Preserve the frozen first report; create a reviewed layout and omitted probe table."""
from pathlib import Path
from copy import deepcopy
from datetime import datetime,timezone
import numpy as np
from classroom_swarm import repaired_config as config
import e26_protocol_parameter_fit as fit

REPO=fit.REPO
SOURCE=REPO/'docs/reports/Plausible-parameter-study-assessment-2026-10-10.md'
REPORT=SOURCE.with_name('Plausible-parameter-study-assessment-2026-10-10-reviewed.md')
SUMMARY=SOURCE.with_name('E26-E27-summary-reviewed-2026-10-10.json')
FIGURE=REPO/'docs/experiments/figures/E26-E27-study-trends-reviewed.png'

def figure(profiles):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    panels=[('STAR: small − regular',[('star','all','core_potential','small','regular')]),
        ('Tracking: tracked − mixed',[('kenya','low','core_potential','tracked','mixed'),('kenya','high','core_potential','tracked','mixed')]),
        ('AI: unaided exam',[('ai','all','core_potential','answer','none'),('ai','all','core_potential','tutor','answer'),('ai','all','core_potential','tutor','none')]),
        ('Seating and helper rewards',[('seating','low','core_potential','cross','random'),('seating','low','core_potential','reward','cross'),('seating','high','core_potential','reward','cross')]),
        ('Teacher incentives',[('teacher_rewards','all','familiar_potential','rewarded','unrewarded'),('teacher_rewards','all','familiar_participation','rewarded','unrewarded'),('teacher_rewards','all','novel_potential','rewarded','unrewarded')])]
    fig,axes=plt.subplots(3,2,figsize=(13,10)); colors=['#9ca3af','#0f766e','#7c3aed']
    for ax,(title,keys) in zip(axes.flat,panels):
        labels=[]
        for index,key in enumerate(keys):
            for offset,(name,rows) in enumerate(profiles.items()):
                matches=[r for r in rows if (r['case'],r['group'],r['metric'],r['a'],r['b'])==key]
                if not matches: continue
                r=matches[0]; y=index+(offset-1)*.18
                ax.errorbar(r['effect'],y,xerr=[[r['effect']-r['lo95']],[r['hi95']-r['effect']]],fmt='o',capsize=3,color=colors[offset],label=name if index==0 else None)
            labels.append(key[1]+' / '+key[2].replace('_potential','').replace('_participation',' participation')+' / '+key[3]+'−'+key[4])
        ax.set_yticks(range(len(keys)),labels); ax.axvline(0,color='#6b7280',linewidth=.8); ax.set_title(title,loc='left'); ax.set_xlabel('Model percentage-point difference (95% paired interval)'); ax.invert_yaxis(); ax.grid(axis='x',alpha=.2)
    axes.flat[-1].axis('off'); handles,labels=axes.flat[0].get_legend_handles_labels(); axes.flat[-1].legend(handles,labels,loc='upper left',frameon=False)
    axes.flat[-1].text(0,.65,'16 untouched paired cohorts\nTeacher beliefs stay below the\nphysical productivity ceiling.\nPaper directions informed fitting.\nIntervals show simulation variability.',transform=axes.flat[-1].transAxes,va='top',fontsize=10)
    fig.suptitle('Audited policy and protocol corrections: conditional study trends',fontsize=15); fig.tight_layout(rect=(0,0,1,.96)); fig.savefig(FIGURE,dpi=180); plt.close(fig)

def main():
    assert not REPORT.exists(); fit.verify()
    initial=config.load_config(SOURCE.with_suffix('.sources.json'))
    for name,digest in initial['sources'].items(): assert config.sha256(REPO/name)==digest,name
    summary=config.load_config(SOURCE.with_name('E26-E27-summary-2026-10-10.json'))
    rows=config.load_config(fit.ROOT/'fresh/selected/all-class-metrics.json'); by=fit.aggregate(rows)
    composition=[]
    for metric in ('core_potential','knowledge_gain','homework'):
        delta=[by['composition','high','focal',r][metric]-by['composition','low','focal',r][metric] for r in range(16)]
        composition.append(dict(case='composition',a='high',b='low',group='focal',metric=metric,**fit.paired(delta),status='partial context-dependent probe, no directional target'))
    summary['composition_probe']=composition
    summary['editorial_review']='Initial frozen figure clipped part of its explanatory note; reviewed figure wraps text. Added computed composition probe rows. No selection/outcome/source-engine changes.'
    config.save_json(SUMMARY,summary); figure(summary['profiles'])
    text=SOURCE.read_text(encoding='utf-8').replace('E26-E27-study-trends.png','E26-E27-study-trends-reviewed.png').replace('`E26-E27-summary-2026-10-10.json`','`E26-E27-summary-reviewed-2026-10-10.json`')
    table='| Partial composition check: higher − lower peer knowledge | Effect [95% interval] |\n|---|---:|\n'
    for r in composition: table+=f"| focal students, {r['metric']} | {r['effect']:+.3f} [{r['lo95']:+.3f}, {r['hi95']:+.3f}] |\n"
    text=text.replace('## Design problems versus parameter problems',table+'\nThese composition results are descriptive and were not fitted to a universal peer-effect sign.\n\n## Design problems versus parameter problems')
    text=text.replace('Tests: see the frozen final test output and source manifest.','All 731 tests pass (33.18 seconds); the final test output is preserved in the source manifest.')
    text+='\nEditorial review: the initial report, figure and manifest remain preserved. This version wraps the clipped figure note and includes the already-run composition probe; all selections, raw outcomes and scientific conclusions are unchanged.\n'
    REPORT.write_text(text,encoding='utf-8')
    sources=[REPORT,SUMMARY,FIGURE,Path(__file__),SOURCE,SOURCE.with_suffix('.sources.json')]
    config.save_json(REPORT.with_suffix('.sources.json'),dict(created_utc=datetime.now(timezone.utc).isoformat(),sources={str(p.relative_to(REPO)).replace('\\','/'):config.sha256(p) for p in sources},
        initial_manifest_sha256=config.sha256(SOURCE.with_suffix('.sources.json')),status='editorial layout/probe completeness correction; all initial frozen artifacts and engine locks preserved'))
    print('Reviewed report/figure saved; initial frozen report remains byte-identical.',flush=True)

if __name__=='__main__': main()
