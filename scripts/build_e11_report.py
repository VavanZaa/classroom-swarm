"""Present the corrected A24/E11 grade-feedback experiment without retuning it."""
import argparse
import csv
import html
import json
from pathlib import Path
import re
import shutil
import zipfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from classroom_swarm.e9 import REPO, digest, dump


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output
    d=json.loads((out/'analysis.json').read_text())
    e={(r['condition'],r['metric']):r for r in d['estimates']}
    fx={(r['condition'],r['metric']):r for r in d['effects']}
    def val(c,m,scale=100): return e[c,m]['mean']*scale
    def effect(c,m):
        r=fx[c,m]
        return f"{100*r['mean']:+.2f} points (95% CI {100*r['low']:+.2f} to {100*r['high']:+.2f})"
    with (out/'trajectories.csv').open(encoding='utf-8-sig',newline='') as f:
        tr=list(csv.DictReader(f))
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    fig,ax=plt.subplots(1,3,figsize=(14,4.7),layout='constrained')
    names={'reference':'No bad-grade copying pressure','grade_response':'Bad-grade copying pressure'}
    colors={'reference':'#3b6596','grade_response':'#be593b'}
    for c in names:
        rs=[r for r in tr if r['condition']==c]
        hs=sorted({int(r['homework']) for r in rs})
        ys=[100*np.mean([float(r['K']) for r in rs if int(r['homework'])==h]) for h in hs]
        ax[0].plot(hs,ys,label=names[c],color=colors[c],lw=2.5)
    ax[0].set(title='Less knowledge accumulates',xlabel='Homework',ylabel='Knowledge /100',ylim=(45,80))
    ax[0].legend(fontsize=8,frameon=False,loc='upper left')
    cs=['reference','response20','grade_response','response80']
    for axis,metric,title,ylabel in [(ax[1],'copy_late','More work is submitted as copies','Late copied submissions (%)'),
                                      (ax[2],'grade_late','Seeking higher grades can backfire','Late homework grade /100')]:
        ys=[val(c,metric) for c in cs]
        err=np.array([[100*(e[c,metric]['mean']-e[c,metric]['low']) for c in cs],
                      [100*(e[c,metric]['high']-e[c,metric]['mean']) for c in cs]])
        axis.errorbar([0,.2,.4,.8],ys,yerr=err,fmt='o-',capsize=4,color='#be593b')
        axis.set(title=title,xlabel='Bad-grade copying response strength',ylabel=ylabel,xticks=[0,.2,.4,.8])
    ax[1].set_ylim(0,30);ax[2].set_ylim(65,80)
    for a in ax:
        a.grid(axis='y',alpha=.18);a.set_axisbelow(True)
    fig.suptitle('Everyone gets a grade. Bad grades raise interest in copying.',fontsize=17,fontweight='bold')
    fig.supxlabel('100 paired classrooms per condition; error bars are pointwise 95% bootstrap intervals. Rates are assumptions, not calibrated data.',fontsize=10)
    fig.savefig(out/'grade-feedback.png',dpi=170);plt.close(fig)
    labels={'reference':'Grades + reinforcement; no copying pressure','grade_response':'Grades + reinforcement + copying pressure (.4)',
        'response20':'Weaker copying pressure (.2)','response80':'Stronger copying pressure (.8)',
        'no_reinforcement':'No action-benefit reinforcement','no_answer':'Answer requests unavailable','no_hint':'Explanation requests unavailable',
        'misattribute0':'No assisted-grade self-assessment update','misattribute80':'Stronger assisted-grade self-assessment update',
        'H40_reference':'40 homeworks: no copying pressure','H40_grade_response':'40 homeworks: copying pressure',
        'ER_reference':'ER network: no copying pressure','ER_grade_response':'ER network: copying pressure'}
    table='| Condition | Knowledge /100 | Unaided exam /100 | Late homework /100 | Late copied work | K P90–P10 |\n|---|---:|---:|---:|---:|---:|\n'
    for c,label in labels.items():
        table+=f"| {label} | {val(c,'K_final'):.2f} | {val(c,'exam_final'):.2f} | {val(c,'grade_late'):.2f} | {val(c,'copy_late'):.2f}% | {val(c,'K_p90_p10'):.2f} |\n"
    report=f'''# Corrected model: previous-homework grades and cheating

24 September 2026 · V4.2-G / A24 · E11 · 1,300 simulations · 100 paired classrooms × 13 conditions · 276 passing tests

**The user's intended rule is now implemented: every student receives the previous homework grade automatically. A bad grade increases interest in cheating; a good copied grade can reinforce copying. Receiving a grade is not studying and adds no knowledge.** The earlier E9/E10 optional-checking interpretation was mistaken. Those records are preserved, but their checking conclusions do not describe this corrected mechanism.

## The feedback loop

- Finish homework → grade returned to everyone before the next homework, without spending homework time.
- Below-target grade → pressure to obtain a better grade → greater attraction of requesting an answer to copy.
- Good copied grade → copying's expected grade benefit usually increases → copying can become attractive again.
- Copying replaces opportunities to attempt or explain → less learning → subsequent grades can disappoint again.
- A sufficiently good grade clears the immediate bad-grade pressure. Students may change approach; copying is never compulsory.

The provisional target is 75/100. Bad-grade pressure adds `response × max(.75 − previous_grade, 0)` only to the answer-request score, with response=.4 by default. Attempts and explanation requests receive no extra bad-grade bonus. Independent attempts, guided attempts and explaining to peers still produce knowledge. Grade receipt and copied answers produce none directly.

Action-benefit beliefs update from the returned grade of the submitted route. Copied final work credits the answer action; independent work credits attempting; a guided attempt splits credit between attempting and requesting an explanation. Confidence also responds, with reduced attribution for assisted work. Separately delayed unaided exams can recalibrate confidence. The signed grade-minus-target value is a satisfaction proxy, not a validated happiness measurement or an additional hidden reward.

## What happened

Both the reference and proposed model receive universal grades and learn from them. Their only primary difference is whether bad grades add copying pressure. Compared with the no-pressure reference:

- Late copied submissions increase from **{val('reference','copy_late'):.2f}% to {val('grade_response','copy_late'):.2f}%**: {effect('grade_response','copy_late')}.
- Final knowledge falls from **{val('reference','K_final'):.2f} to {val('grade_response','K_final'):.2f}**: {effect('grade_response','K_final')}.
- Late homework grades fall from **{val('reference','grade_late'):.2f} to {val('grade_response','grade_late'):.2f}**: {effect('grade_response','grade_late')}.
- The within-class final P90–P10 knowledge gap increases from **{val('reference','K_p90_p10'):.2f} to {val('grade_response','K_p90_p10'):.2f}**: {effect('grade_response','K_p90_p10')}.

![Corrected grade feedback results](grade-feedback.png)

The population-level result is an unintended consequence of grade-seeking: more copying does not improve average homework grades in these settings, and knowledge grows more slowly. This is consistent with a reinforcing dependency mechanism, but it is not proof of an irreversible trap, a real-world effect size or a scientifically unique phenomenon.

## Behavior and the two different reactions

Students make {val('grade_response','answer_requests_total',1):.2f} answer requests across 20 homeworks, compared with {val('reference','answer_requests_total',1):.2f} without bad-grade pressure. Completed attempts fall from {val('reference','attempts',1):.2f} to {val('grade_response','attempts',1):.2f}; received explanations fall from {val('reference','hint_receipts_total',1):.2f} to {val('grade_response','hint_receipts_total',1):.2f}. A request is not necessarily successful: peer availability, willingness and existing answers still constrain actual copying.

After a below-target grade, an answer request occurs on {val('grade_response','below_target_next_answer_request'):.2f}% of next homeworks; after an at/above-target grade, {val('grade_response','at_or_above_target_next_answer_request'):.2f}%. These are classroom-averaged conditional associations, affected by who receives each grade, rather than randomized comparisons between good and bad grades. The paired pressure-versus-no-pressure comparison above is the experimental contrast.

After an above-target copied grade, B_answer increases in {val('grade_response','good_copied_B_answer_increased'):.2f}% of feedback events, averaging the proportions within each classroom. This verifies the intended reward channel. However, only {val('grade_response','good_copied_next_copy'):.2f}% of next homeworks after a good copied grade are also submitted as copies. Reinforcement does not create a permanent cheating type.

There are two standards of success: the grade target and the expected benefit of copying. Only {val('grade_response','bad_copied_B_answer_decreased'):.2f}% of below-target copied grades decrease B_answer. A grade can disappoint relative to 75/100 yet exceed a student's previously low expectation for copying, thereby reinforcing it. That distinction is explicitly encoded by the expectation update; the observed frequency depends on the evolving histories.

## Knowledge gaps and limits of the emergence claim

The overall student spread widens relative to the no-pressure reference. But early high- and low-attempt groups do not become more separated: their final gap decreases from {val('reference','group_gap_K_final'):.2f} to {val('grade_response','group_gap_K_final'):.2f} points. These groups are fixed using each reference classroom's first five homeworks; they are observational, tied ranks and initial traits can matter, and they are not assigned student types.

Both variants still narrow their initial knowledge spread of {val('reference','K0_p90_p10'):.2f} points. There is no demonstrated permanent low-knowledge class or collapse. At 40 homeworks, knowledge is still increasing, and copying remains higher under pressure ({val('H40_grade_response','copy_late'):.2f}% versus {val('H40_reference','copy_late'):.2f}%). The model permits improvement and switching.

The individual tendencies—bad grades increasing answer-request attraction and successful copied grades reinforcing expected benefit—are assumptions supplied by the user, not discoveries. Their joint classroom consequences, including lost practice, constrained delivery, lower average grades and differences in spread, are simulation outputs. A fuller causal decomposition of the feedback cycle would require additional interventions; these results establish the total effect of the declared copying-pressure rule.

## All conditions

{table}
We report both weaker and stronger pressure without selecting a preferred rate to maximize the gap. All non-reference ablations compare with the proposed model; response-strength variants compare with the no-pressure reference, and H40/ER compare with their matched references. Removing action-benefit reinforcement affects every action, so it is not a pure test of the copying-reward channel alone.

## Timing, validation and reproducibility

All students receive one grade for every homework, including missing work. Homework h's grade arrives at h+1; the final homework is returned at a terminal boundary with no extra work. There is no same-homework grade leak, no optional checking event, no study-time charge for receiving a grade and no direct competence update. End-of-homework snapshots precede receipt of that homework's grade; final feedback is separately logged.

All 276 tests pass, including universal delivery, exact reinforcement equations, no first-homework effect, no checking, missing-work grades, local information, no overlapping time use, and no pressure effect when answer requests are unavailable. Every one of {d['verified_raw_files']} raw files was hash-verified. Every student's event gains reconstruct total knowledge change within 1e-12. Independent reruns of reference and pressure conditions match every raw table. The E9, E10 and E11 source locks remain intact.

This is a phenomenological experiment implementing the user's hypothesis, not an assertion that every real student cheats after a bad grade. The 75-point target and all reaction strengths are assumptions. Alpha comes from a chosen trajectory, not educational calibration. Confidence intervals use 2,000 resamples of 100 whole paired classrooms; they are pointwise, not multiplicity-adjusted. Rate/target sensitivity is not exhausted, and knowledge remains a single monotone scalar.

- [Classroom results](classroom_results.csv), [student results](student_results.csv) and [trajectories](trajectories.csv).
- [Condition estimates](condition_estimates.csv), [paired effects](paired_effects.csv) and [analysis metadata](analysis.json).
- [Raw dataset locations and hashes](dataset_manifest.json).
- [Analysis data bundle](grade-feedback-data.zip) and [source, tests and locked specification](grade-feedback-source.zip).

Raw logs remain at the project's `runs/E11`. Reproduce the analysis with `python -m classroom_swarm.e11 analyze --root runs/E11 --output <directory>`. New simulations require a new empty directory and `lock` followed by `run --workers 4`; existing completed runs are verified rather than overwritten.
'''
    (out/'grade-feedback-report.md').write_text(report,encoding='utf-8')
    def inline(s):
        s=html.escape(s)
        s=re.sub(r'\[([^\]]+)\]\(([^)]+)\)',r'<a href="\2">\1</a>',s)
        s=re.sub(r'\*\*([^*]+)\*\*',r'<strong>\1</strong>',s)
        return re.sub(r'`([^`]+)`',r'<code>\1</code>',s)
    blocks=[];lines=report.splitlines();i=0
    while i<len(lines):
        line=lines[i]
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].startswith('|'):
                if not re.match(r'^\|[-:| ]+\|$',lines[i]):
                    tag='th' if not rows else 'td'
                    rows.append('<tr>'+''.join(f'<{tag}>{inline(c.strip())}</{tag}>' for c in lines[i].strip('|').split('|'))+'</tr>')
                i+=1
            blocks.append('<div class="table"><table>'+''.join(rows)+'</table></div>');continue
        if line.startswith('!['):
            alt,src=re.match(r'!\[([^]]*)\]\(([^)]+)\)',line).groups()
            blocks.append(f'<img src="{src}" alt="{html.escape(alt)}">')
        elif line.startswith('#'):
            n=len(line)-len(line.lstrip('#'));blocks.append(f'<h{n}>{inline(line[n:].strip())}</h{n}>')
        elif line:
            blocks.append('<p>'+inline(line)+'</p>')
        i+=1
    css='body{background:#f4f7fb;color:#20334b;font:17px/1.65 system-ui;margin:0}main{max-width:1150px;margin:35px auto;padding:45px;background:white;border-radius:14px}h1{line-height:1.2;color:#153c60}h2{margin-top:36px}img{width:100%}table{border-collapse:collapse;width:100%;font-size:14px}th,td{padding:9px;border-bottom:1px solid #dce3eb}th{background:#264b6d;color:white;text-align:left}.table{overflow-x:auto}a{color:#1859a9}code{font-size:13px;overflow-wrap:anywhere}@media(max-width:700px){main{margin:0;padding:20px}}'
    (out/'grade-feedback-report.html').write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Previous homework grades and cheating</title><style>'+css+'</style><main>'+''.join(blocks)+'</main></html>',encoding='utf-8')
    with zipfile.ZipFile(out/'grade-feedback-data.zip','w',zipfile.ZIP_DEFLATED) as z:
        for f in out.iterdir():
            if f.suffix in {'.csv','.json'} and f.name!='deliverable_hashes.json':z.write(f,f.name)
    bundle=list((REPO/'src/classroom_swarm').glob('*.py'))+list((REPO/'tests').glob('*.py'))
    bundle += [REPO/p for p in ['pyproject.toml','uv.lock','docs/11-v4-activity-feedback.md','docs/12-v4-learning-differentiation.md',
        'docs/13-v4-homework-feedback.md','scripts/build_e11_report.py','runs/E11/lock.json','runs/E11/execution.json']]
    with zipfile.ZipFile(out/'grade-feedback-source.zip','w',zipfile.ZIP_DEFLATED) as z:
        for f in bundle:z.write(f,f.relative_to(REPO).as_posix())
    dump(out/'deliverable_hashes.json',{f.name:digest(f) for f in out.iterdir() if f.is_file() and f.name!='deliverable_hashes.json'})
    canonical=REPO/'runs/E11/derived';canonical.mkdir(exist_ok=True)
    for f in out.iterdir():
        if f.is_file():shutil.copy2(f,canonical/f.name)
    for f in out.iterdir():report=report.replace(f']({f.name})',f'](../../runs/E11/derived/{f.name})')
    (REPO/'docs/experiments/E11-results.md').write_text(report,encoding='utf-8')
    print('Corrected report, figure, data and source bundles written.')


if __name__=='__main__':main()
