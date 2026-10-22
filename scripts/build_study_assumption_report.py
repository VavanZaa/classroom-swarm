"""Read-only comparison of frozen simulation results with primary education studies."""
from __future__ import annotations
import csv,json,hashlib
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/reports/Classroom-study-comparison-and-assumption-review-2026-10-01.md'
SOURCES={
 'peer_lab':'https://www.crepe.e.u-tokyo.ac.jp/events/20190325_shigeoka.pdf',
 'star':'https://www.nber.org/papers/w6051',
 'tracking':'https://www.povertyactionlab.org/sites/default/files/research-paper/39%20Peer%20Effects%2C%20Teacher%20Incentives%2C%20and%20the%20Impact%20of%20Tracking%20Project.pdf',
 'rewards':'https://www.aeaweb.org/content/file?id=15848',
 'ai':'https://www.pnas.org/doi/10.1073/pnas.2422633122',
 'university':'https://leuven.economists.nl/pdf/ability_final.pdf',
 'teaching':'https://doi.org/10.1016/j.cedpsych.2013.06.001',
 'quality':'https://onlinelibrary.wiley.com/doi/full/10.1002/acp.4100',
 'retrieval':'https://learninglab.psych.purdue.edu/downloads/2008/2008_Karpicke_Roediger_Science.pdf',
}
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8'))
def file_link(label,path):return f'[{label}](<{path.as_posix()}>)'
def cite(label,key):return f'[{label}]({SOURCES[key]})'

def verify_evidence():
    manifests=[ROOT/'runs/E14/derived/analysis_manifest.json',
        ROOT/'runs/E16-tutoring-r1/development_derived/analysis_manifest.json',
        ROOT/'runs/E16-tutoring-r1/validation_derived/analysis_manifest.json']
    inputs={}
    for path in manifests:
        manifest=read(path)
        for name,value in manifest['hashes'].items():
            p=path.parent/name;assert digest(p)==value,p
        inputs[str(path.relative_to(ROOT))]=digest(path)
    for path in [ROOT/'runs/E14/preregistration-lock.json', ROOT/'runs/E16-tutoring-r1/diagnostic-lock.json']:
        for name,value in read(path)['sources'].items():assert digest(ROOT/name)==value,name
        inputs[str(path.relative_to(ROOT))]=digest(path)
    with (manifests[0].parent/'effects.csv').open(encoding='utf-8',newline='') as f:old=list(csv.DictReader(f))
    with (manifests[2].parent/'effects.csv').open(encoding='utf-8',newline='') as f:new=list(csv.DictReader(f))
    inputs['src/classroom_swarm/tutoring_settings.py']=digest(ROOT/'src/classroom_swarm/tutoring_settings.py')
    inputs['src/classroom_swarm/v4_tutoring.py']=digest(ROOT/'src/classroom_swarm/v4_tutoring.py')
    return old,new,inputs

def effect(rows,group,a,b,old=False,reverse=False,metric=None):
    metric=metric or ('focal_exam' if old else 'exam')
    found=[r for r in rows if (r['group'],r['condition'],r['reference'],r['metric'])==(group,a,b,metric)]
    assert len(found)==1,(group,a,b,metric)
    r=found[0];keys=['delta','simultaneous_lo','simultaneous_hi'] if old else ['effect','lo95','hi95']
    values=[float(r[k]) for k in keys]
    if reverse:values=[-values[0],-values[2],-values[1]]
    return f'{values[0]:+.2f} pp [{values[1]:+.2f}, {values[2]:+.2f}]'

def main():
    old,new,inputs=verify_evidence()
    e14=lambda g,a,b:effect(old,g,a,b,old=True)
    e16=lambda g,a,b,reverse=False:effect(new,g,a,b,reverse=reverse)
    mixed=e16('lab','mixed_reference','tracked_reference')
    teaching=e16('lab','mixed_solo','mixed_reference',True)
    tracked_teaching=e16('lab','tracked_solo','tracked_reference',True)
    peer=e16('composition','high_joint','low_joint')
    copying=e16('composition','high_joint_copy','low_joint_copy')
    hard=e16('lab','mixed_hard','tracked_hard')
    slow=e16('lab','mixed_slow','mixed_reference')
    nohelper=e16('lab','mixed_no_helper','tracked_no_helper')
    ai=e14('ai_and_spread','middle_answer','middle_none')
    tutor=e14('ai_and_spread','middle_tutor','middle_none')
    safer=e14('ai_and_spread','middle_tutor','middle_answer')
    seating=e14('grouping','cross_pairs','random_pairs')
    size=e14('class_size','small_friends','regular_friends')
    size_acq=e14('class_size','small_acquaintances','regular_acquaintances')
    config=read(ROOT/'runs/E16-tutoring-r1/validation_lab/declared_config.json')
    params,initial=config['params'],config['initial']
    parameter_rows=[
        ('Starting knowledge','Four students at 0.35; four at 0.75','Declared two-level population, not measured ability conversion.'),
        ('Learning efficiency',f"Lognormal mean {initial['learning_efficiency']['mean']}; log SD {initial['learning_efficiency']['log_sd']}",'Inherited numerical trajectory, not estimated from participant data.'),
        ('Effort aversion',f"Lognormal mean {initial['effort_aversion']['mean']}; log SD {initial['effort_aversion']['log_sd']}",'Assumed preference scale and heterogeneity.'),
        ('Time',f"{params['H']} episodes; {params['ticks']} ticks per episode; {params['guided_practice_ticks']}-tick shared block",'No fitted conversion from ticks to human minutes.'),
        ('Task difficulty',json.dumps(initial['task_difficulty'],sort_keys=True),'Unmeasured numerical content distribution.'),
        ('Practice and helper fractions',f"alpha/{params['attempt_learning_divisor']:g} and alpha/{params['helper_learning_divisor']:g}",'Separate assumed rates, modified by usable content/helper opportunity.'),
        ('Content learning multiplier',str(params['content_learning_multiplier']),'Declared magnitude, not calibrated.'),
        ('Readiness band',str(params['readiness_band']),'Declared linear-cutoff width, not calibrated.'),
        ('Conditional teaching skill',str(initial['teaching_skill']['value']),'Perfect delivery once content is retrieved.'),
        ('Correctness-check probability',str(params['quality_check_probability']),'Full coverage with error-free observed signals.'),
        ('Quality belief and update',f"Initial {initial['source_quality']['value']}; rate {params['quality_learning_rate']}; target weight {params['quality_target_weight']}",'Assumed priors and learning/selection coefficients.'),
        ('Initial confidence and benefit priors','All 0.5','Deliberately isolates knowledge composition but omits real correlations.'),
    ]
    parameter_table='\n'.join('| '+ ' | '.join(r)+' |' for r in parameter_rows)
    text=f'''# Classroom simulation study comparisons and assumption review

Prepared for the Classroom AI simulation project on 1 October 2026.

The simulation shows **partial qualitative agreement with the peer-teaching lab study and the unrestricted-AI study**. It does not yet reproduce every result in those studies, and it has not reproduced the class-size, teacher-adaptation, helper-reward or university-distribution interventions. The assumptions make sense as a deliberately simplified mechanism model, but several reference settings are optimistic or untested. Matching a direction is evidence of what the assumed model can produce, rather than independent confirmation of the human causal mechanism.

This report compares six classroom studies and uses three additional learning studies to assess the assumptions. Published findings, simulation outputs, and our judgments are identified separately. It uses existing frozen results; no parameters were changed and no new simulations were run for this review.

## What the comparisons establish

The earlier classroom comparisons contain 3,300 simulations. The tutoring extension contains 720 initial diagnostic runs and 2,400 runs on additional random seeds. Both seed sets and settings were fixed before inspecting the initial outcomes. The previously used label “validation” means a **fresh-seed simulation check**, not validation against human participants. The same model and the same 24 scenarios were used in both sets.

All simulation effects below are differences in final unaided exam percentage scores. They are not human standardized effect sizes, percentile-rank changes, solving times, or estimates of what will happen in a school. Brackets contain simulation uncertainty intervals. The earlier comparisons use intervals adjusted across ten planned comparisons; the new tutoring comparisons use exploratory pointwise 95% intervals. Their widths are therefore not directly comparable.

| Study | Published pattern | What our simulation shows | Current claim |
|---|---|---|---|
| {cite('Kimbrough, McGee and Shigeoka, peer-teaching lab','peer_lab')} | Teaching helps low performers; tracking reduces the benefit. | Shared practice: mixed minus tracked {mixed}; shared minus independent {teaching}. | Partial qualitative agreement. |
| {cite('Bastani and colleagues, high-school AI','ai')} | Answer-oriented AI improves practice but harms subsequent unaided performance; tutor safeguards mitigate harm. | Answer AI minus no AI {ai}; tutor minus answer AI {safer}. | Agreement on these two directions, with assumptions about copying. |
| {cite('Krueger, Project STAR','star')} | Small classes improve test outcomes. | Small minus regular classes {size}; interval crosses zero. | Inconclusive network-only comparison. |
| {cite('Duflo, Dupas and Kremer, Kenyan tracking','tracking')} | Tracking benefits students when instruction can match their level. | Teacher instruction and targeting are absent. | Corresponding intervention not represented. |
| {cite('Wu, Zhang and Wang, seating and rewards','rewards')} | Seating alone has no detectable benefit; seating plus helper incentives benefits low performers. | Seating-only proxy {seating}; reward treatment absent. | Mismatch for seating alone; reward effect untested. |
| {cite('Booij, Leuven and Oosterbeek, university ability distributions','university')} | Effects depend on peer mean, spread and own ability; assignment calculations favor tracking for some students. | Our spread changes alter students’ own knowledge as well as their peers. | No comparable isolated distribution test. |

The positive stronger-peer contrast in the new voluntary-practice model, {peer}, is a useful mechanism diagnostic. It is not a reproduction of a separate universally positive peer-effect estimate. With copying available, the same contrast is {copying}.

## Peer teaching and ability grouping

**Published evidence.** The lab participants worked in groups of four on a common Sudoku puzzle, could communicate through audio, knew within-group performance ranks, and subsequently worked individually. Teaching especially helped low performers; tracking reduced that benefit and the frequency of teaching. Each participant completed one ability–practice–evaluation sequence. The paper’s experimental session counts refer to different groups of participants, not repeated classroom episodes for one participant. {cite('Primary author manuscript, sections 2 and 4','peer_lab')}.

**Our representation.** Eight numerical students form two groups of four. Four begin at knowledge 0.35 and four at 0.75. Mixed groups contain two of each; tracked groups separate them. There are 20 homework episodes, a reserved three-tick shared-practice block per episode, and no copying in this comparison. Each learner samples one peer explanation during the block. Explanations can support learning only when their content is correct, previously unresolved and accessible to the learner. The final outcome is a simulated exam, not puzzle-solving speed.

**Result and judgment.** The fresh-seed results match the directions of mixed versus tracked and shared versus independent practice. However, tracked low starters also benefit from teaching by {tracked_teaching}. We have therefore not reproduced the stronger pattern in which tracking removes most of the teaching benefit. We also have not established that benefits are concentrated among low starters relative to high starters: the reported effect analysis focuses on the predefined low group. Guaranteed sampled explanations do not reproduce endogenous conversational teaching frequency.

**Do the assumptions make sense?** Joint practice and differences in useful content are plausible abstractions of collaboration. Reserving the same practice time in teaching and independent arms is a reasonable comparison of task opportunities. Mandatory explanation exposure, missing rank information, repeated homework choices, perfect explanation delivery conditional on retrieval, and fully checked correctness make this an imperfect reconstruction of the lab. Our interpretation is that the model can demonstrate a plausible composition mechanism; the existing evidence does not identify its numerical learning rule as the human mechanism.

At an otherwise identical practice history, the model adds nonnegative content and helper-learning terms. Part of the teaching benefit therefore follows from the assumed learning mechanism. Subsequent choices can alter the total effect, but the positive bonus itself is not a discovery. The mixed-versus-tracked contrast is more informative about the consequences of group composition, while still depending on these assumptions.

## Answer AI and guarded tutoring

**Published evidence.** Bastani and colleagues studied nearly 1,000 high-school mathematics students. Unrestricted GPT access improved assisted practice but reduced later unaided performance. Teacher-designed safeguards in the tutor condition mitigated the harm; tutor versus control exam performance was statistically indistinguishable. This concerns learning under access to a real conversational tool. {cite('PNAS research article, abstract and Table 2','ai')}.

**Our representation.** Four numerical homework episodes compare no AI, answer AI and tutor AI. A direct AI answer supplies a packet, costs time, and grants zero direct knowledge. Tutor access supplies a hint and requires a subsequent attempt. Reference answer accuracy is 0.90 per item. Students choose activities using expected homework benefit and effort, with no intrinsic learning bonus in the main setting.

**Result and judgment.** Answer access improves homework but has an unaided-exam effect of {ai}; guarded tutoring exceeds answer access by {safer}. Those directions agree. Tutor versus no AI is {tutor}, a small positive effect whose interval excludes zero. The earlier report treated it as within a declared ±1 pp practical band; that is not the same as reproducing the human study’s statistical nondetection.

**Do the assumptions make sense?** It is plausible that obtaining finished answers displaces active practice. Setting learning from all copied material to exactly zero is a strong assumption: reading or studying a worked example may itself teach something. The reference AI accuracy and hint strength are illustrative coefficients, not measurements of the study’s GPT systems. Whole-problem correctness cannot be substituted for per-item accuracy. Numerical hints omit questioning, explanations, answer checking and teacher-provided solutions. Our mechanism interpretation is a credible candidate, not a demonstrated explanation of the field result. A follow-up should test whether the negative effect survives modest learning from reading answers and an explicit future-exam objective.

## Class size

**Published evidence.** Project STAR randomized students and teachers to small classes, regular classes and regular classes with an aide. Small classes were approximately 13–17 pupils versus 22–25 in regular classes. Krueger reports better standardized-test outcomes, including an initial gain of about four percentile-rank points. That unit is different from our exam percentage-point scale. {cite('NBER working paper 6051 abstract','star')}.

**Our representation and result.** We compared 15 with 24 students, retaining expected friend degree six; the acquaintance channel was either absent or weak. Effects were {size} for friends only and {size_acq} with acquaintances. Both are inconclusive. No teacher attention, instructional pacing or classroom disruption is represented.

**Do the assumptions make sense?** Keeping friend degree fixed can isolate a network consequence of class size. It does not represent the full classroom intervention. A smaller numerical population does not automatically give students more instruction in this model. Missing teacher capacity is therefore a structural gap, not evidence against STAR. A finite teacher budget and an allocation policy are sensible future hypotheses; STAR by itself does not establish that a particular inverse-class-size formula is the correct mechanism. Adding such a formula would partly encode a small-class advantage and should be labeled accordingly.

## Tracking and instructional adaptation

**Published evidence.** In 121 Kenyan primary schools, Duflo, Dupas and Kremer compared sections formed by initial achievement with randomly formed sections. Tracking improved outcomes for students across the starting distribution. The authors interpret the findings through teachers’ instructional targets and incentives: lower-achieving students can benefit when instruction becomes closer to their level. {cite('AER 2011 paper, introduction','tracking')}.

**Our representation and judgment.** Our lab-style grouping comparison changes peer contacts while holding the absence of teachers constant. It cannot test this classroom intervention. Its mixed-group advantage is not a contradiction of the Kenyan finding because the represented causal channels differ.

**Do the assumptions make sense?** Teaching material suited to student readiness is a plausible mechanism to add, but it needs a teacher agent or an explicit instructional process, time capacity, assessment-based targeting and an intervention definition. The current learner-readiness factor applies to peer content; it is not adaptive teacher instruction. We should compare fixed and adaptive instruction under the same resource constraints. Teachers should use observed assessments rather than read hidden true knowledge. We should not choose a coefficient solely to make tracked classes win.

## Seating and helper rewards

**Published evidence.** Wu, Zhang and Wang paired high- and low-achieving elementary pupils as deskmates for 20 weeks. The seating-only arm had no detectable performance difference from random seating. With tournament incentives for high achievers to help their partners, low achievers’ mathematics improved by about 0.24 SD. Rewards included money and commendation when the partner’s improvement ranked near the top of the class; friendship patterns also changed. {cite('Accepted manuscript, introduction and intervention description','rewards')}.

**Our representation and result.** The earlier cross-ability versus random-pair comparison allows hints and copying but has no helper reward, producing {seating}. It does not reproduce the seating-only nondetection. The new voluntary-practice results concern an altered activity model, not a rerun of the field-study seating design. A rewarded treatment has not been simulated.

**Do the assumptions make sense?** Helper availability and deadline competition are useful components, but helper willingness currently omits an explicit reward and the helper’s individual effort cost. Static contacts cannot represent changing friendships. A future incentive model should connect expected rewards to observable partner improvement, account for helper time/effort, and distinguish incentive effects from merely increasing an availability probability. Rewarded and unrewarded seating arms must remain separate. A positive result from guaranteed collaborative practice cannot be renamed a replication of this reward intervention.

## Peer mean and knowledge distribution

**Published evidence.** Booij, Leuven and Oosterbeek manipulated the ability composition of university tutorial groups of roughly 40 students. Estimated effects depended on peer mean, spread and their interactions with own prior ability. Tracking advantages were calculated from the fitted peer-effect model, not simply a randomized two-arm tracking treatment. Surveys suggested differences in involvement and peer interaction, without evidence of instructor adjustment. {cite('Author manuscript, abstract and sections 4 and 5','university')}.

**Our representation and judgment.** Our configurable distributions permit changes to initial mean and spread, but the existing whole-class spread comparison changes each student’s own starting knowledge as well as peer composition. It does not isolate a contextual peer-spread effect. The new high-versus-low peer comparison holds the first 15 low starters fixed, which improves identification of peer mean, but uses scalar knowledge rather than GPA and does not reproduce the full mean–spread interaction.

**Do the assumptions make sense?** Adjustable distributions are necessary experimental controls, not a validated social mechanism. Knowledge 0.35 and 0.75 are declared competence levels; they are not empirical IQ or GPA conversions. A stronger comparison would hold focal own ability fixed, vary peer mean and SD separately while checking their realized values, and test exogenous low, middle and high focal groups. Participation, engagement and task fit may be relevant hypotheses. Neither this study nor the lab result justifies a universal rule that mixing always helps or tracking always helps.

## Evidence about the learning assumptions

Three additional studies inform our judgments below. They were not targets of the simulation comparison and their effect sizes were not used to set coefficients.

* **Learning by actually teaching.** Fiorella and Mayer compared studying, preparing to teach and delivering a recorded explanation about the Doppler Effect. Their experiments found more persistent learning from actually teaching than from preparation alone. This supports including a helper-learning channel in principle. It does not establish our fixed helper coefficient or the rule that the learner must initially lack the explained item. {cite('Contemporary Educational Psychology 2013 primary abstract','teaching')}.
* **Explanation form and quality.** Fiorella’s 2023 registered report compared ways of explaining the respiratory system. Visual-supported explanations produced better transfer than word-supported explanations; elaboration was associated with later performance. All groups explained, so this is evidence about explanation conditions rather than a teaching-versus-no-teaching effect. It supports treating explanation quality as a substantive process, not granting a universal reward for any delivered help. {cite('Applied Cognitive Psychology primary study','quality')}.
* **Retrieval and assessment.** Karpicke and Roediger experimentally varied repeated study and retrieval of vocabulary. Repeated retrieval improved delayed recall even after successful initial learning. This supports activity-specific learning, but also exposes a simplification: our repeated diagnostic exams change beliefs through feedback but grant no direct knowledge. Human tests can themselves be learning activities. The vocabulary results do not specify a tutoring coefficient for mathematical problem solving. {cite('Science 2008 author-hosted paper','retrieval')}.

## Assumption assessment

The judgments in this table are our assessment of the model, not conclusions demonstrated by the cited human studies.

| Model assumption | Why it can make sense | Limitation and judgment |
|---|---|---|
| Learners practice while receiving tutoring. | Collaboration can include active work rather than only receiving a message. | **Reasonable mechanism.** Mandatory explanation exposure is stronger than voluntary conversation. |
| Helpers retrieve content and learn by explaining it. | Actual explanation can consolidate or reorganize knowledge. | **Reasonable channel, unvalidated rule.** Our helper gain depends on correct content the learner lacked, not measured explanatory effort or elaboration. |
| Retrieval depends on scalar knowledge and task difficulty. | Competence and difficulty should influence success. | **Useful coarse model.** The linear clipped probability is assumed; item knowledge is redrawn rather than stored as persistent topics. |
| Novel, accessible content adds learning. | Already resolved material offers less new information; inaccessible content may not help. | **Plausible direction, unvalidated function.** The readiness cutoff at band 0.5 and multiplier 1 were not estimated. |
| Teaching skill is 1 in reference runs. | Separates content availability from failures to deliver explanations. | **Strong idealization.** Every retrieved item is successfully explained; this is not perfect knowledge, but it is perfect conditional delivery. |
| Every explanation item has an accurate correctness check. | Objective worksheet feedback can support judgments of source quality. | **Strong added information channel.** Check probability 1 with error-free signals is not established for the peer-teaching study. |
| Private quality starts at 0.5 and learns at rate 0.2. | Neutral priors and gradual updating are interpretable. | **Illustrative coefficients.** Uniform priors omit the public ability ranks in the lab. The benefit of quality learning was not separately identified by the existing diagnostics. |
| Copied answers grant zero direct learning. | Pure answer substitution can avoid active practice. | **Strong limiting case.** Worked-example reading and self-explanation are absent; this may overstate learning displacement. |
| Choice optimizes homework benefit minus effort. | Grades and effort can influence student decisions. | **Restricted motivation.** Future-test goals, mastery, social duties and helping rewards are absent from the main objective. |
| Knowledge gains are nonnegative with diminishing headroom. | Bounds and a ceiling make the numerical state stable. | **Simplifying assumption.** Forgetting, misconceptions and learning from correcting mistakes are not represented. A ceiling effect is encoded. |
| Session learning is specified separately from duration. | Allows explicit comparison of time costs and learning content. | **Needs an exposure model.** Three- and five-tick sessions receive the same base learning rule; longer-session penalties do not establish a real optimum duration. |
| Graph and relationship closeness remain fixed. | Provides controlled peer-access comparisons. | **Reasonable baseline, incomplete field model.** It cannot reproduce the friendship changes documented in the reward study. |
| Exams only measure knowledge directly. | Keeps a clear model measurement boundary. | **Useful computational convention.** Repeated real tests may themselves teach through retrieval. |

## Reference numerical assumptions

These values are read from the locked shared-practice configuration. They specify an illustrative numerical experiment, not fitted characteristics of the human samples. Alpha denotes an individual learning-efficiency draw. The corresponding learning gains are also limited by remaining knowledge headroom.

| Setting | Reference value | Evidential status |
|---|---|---|
{parameter_table}

An assumption can make conceptual sense without its particular coefficient making empirical sense. We have evidence for investigating active practice and explanation, but we do not have evidence that a multiplier of 1, readiness width of 0.5 or quality update rate of 0.2 is the correct value for the reviewed classrooms. The existing controls test selected structural changes; they do not calibrate these numbers or exhaust their sensitivity.

## What the existing diagnostics say about these assumptions

Several tests distinguish a content mechanism from a rule that always favors one group. In the additional-seed shared-practice comparisons, very hard content changes mixed minus tracked to {hard}. A five-tick block instead of a three-tick block changes the mixed-group exam by {slow}. With teaching skill set to zero, the mixed-minus-tracked effect is exactly zero in this declared probe. These results demonstrate model dependence on content and opportunities; they do not establish that the chosen content distributions are realistic.

Disabling helper learning changes mixed minus tracked to {nohelper}, larger than the reference {mixed}. Helpers’ learning benefits also help tracked groups and can narrow the mixed-group advantage. This is a useful counterweight to an account that considers only what low learners receive. It does not identify the true size of helper learning in people.

The no-copying stronger-peer contrast is positive, while the copying-enabled contrast remains negative. This supports inspecting activity substitution rather than forcing one peer-effect sign. Quality learning, the perfect-feedback assumption, the readiness function, motivation, and persistent topic knowledge have not all been individually tested in the saved diagnostic design. Their plausibility should not be confused with demonstrated robustness.

**Our overall assessment:** the causal structure is defensible as a transparent hypothesis model. The reference coefficients and information conditions are not sufficiently grounded to call it an empirically validated classroom simulator. Joint practice is a meaningful improvement over the old content-free hint route, but it does not by itself settle which human mechanism explains the published results.

## Claims suitable for a report

For the peer-teaching comparison:

> Under the declared shared-practice assumptions, the model showed qualitative agreement with two peer-teaching comparisons: low-starting-knowledge agents performed better in mixed than tracked groups and in shared than independent practice. These directions persisted across additional random seeds. The model did not reproduce the complete experimental protocol or establish that the assumed learning mechanism generated the human effects.

For the AI comparison:

> The answer-AI and tutor-AI scenarios produced an assisted-performance versus unaided-learning tradeoff consistent with the published field-study directions. This agreement depends partly on assumed activity substitution and zero direct learning from copied answers; the simulated tutor-versus-control result differs from the field study’s statistical nondetection.

For all studies together:

> Across the reviewed evidence, the model captures selected peer-practice and answer-substitution patterns. Other comparisons remain inconclusive, inconsistent or outside the represented interventions. The results motivate further mechanism tests rather than a claim of general empirical validation.

## Tests that would strengthen the model

1. **Check the optimistic tutoring assumptions first.** Test imperfect and heterogeneous explanation delivery, partial/noisy/delayed observed checks, and public baseline ranks. Keep protocol and all other settings fixed, and retain adverse results. These are proposed experiments, not completed tests.
2. **Represent stable content and explanatory activity.** Add persistent topic/strategy competence and an observable practice or explanation-quality measure. Test helper consolidation separately from whether the recipient initially knew the item. Do not infer content mastery from a single scalar chance draw.
3. **Test motivation and answer-reading learning.** Compare the homework-only objective with an explicitly specified expected future-test objective; allow a small, declared learning channel from worked examples. This would test how much the AI/copying match depends on restrictive assumptions.
4. **Specify teacher and reward interventions separately.** Teacher capacity and fixed/adaptive instructional targets address class size and Kenyan tracking. Observable helper incentives and their costs address rewarded seating. These additions should not be hidden inside a larger peer-benefit coefficient.
5. **Test distributions with the right controls.** Keep focal own ability fixed, vary peer mean and SD independently, preserve total resources, and report realized moments and heterogeneous effects. Add participation mechanisms only as separately defined hypotheses.
6. **Compare more than the final sign.** A stronger empirical check would target teaching frequency, explanation quality, helper outcomes, time allocation, unaided gain and subgroup patterns using the same intervention and measurement scale as a specific study. Use additional studies or participant data that did not guide model design when evaluating generalization.

Matching a sign can justify saying the model is consistent with a finding under its assumptions. Matching several intermediate behaviors and outcomes under the same protocol would provide a stronger test of whether those assumptions make sense.

## Evidence and reproducibility

Simulation numbers were read from hash-verified saved effect tables. The earlier and new model source locks were checked before rendering this report. Historical code, frozen reports and raw runs were not modified. The earlier 429-test result and the raw-audit status establish implementation checks, not human validity. No new test execution is needed for this read-only report.

The published Sudoku protocol above also corrects a misleading phrase in the frozen diagnostic plan referring to “the human study’s eight sessions.” Those counts describe separate experimental sessions in treatment cells, not eight repeated learning episodes per participant. This report records the correction without altering the frozen plan.

Source coverage: primary author manuscripts were read for peer teaching, Kenyan tracking, seating/rewards, university distributions and retrieval practice; the PNAS and Wiley primary articles were read for AI and explanation quality. The STAR and Fiorella–Mayer summaries are limited to their primary publisher abstract/indexed article text. No effect-size conversion or participant-data calibration was performed.

Project evidence: {file_link('earlier classroom results',ROOT/'docs/experiments/E14-results.md')}, {file_link('tutoring results',ROOT/'docs/experiments/E16-results.md')}, {file_link('tutoring model definition',ROOT/'docs/18-v4-tutoring-content.md')}, {file_link('editable shared-practice comparison',ROOT/'configs/A29-shared-practice-example.json')}.

Progress: review complete; no input pending. The next scientific step is testing the strongest assumptions and then defining the teacher/instruction and helper-reward interventions separately.
'''
    OUT.parent.mkdir(parents=True,exist_ok=True)
    OUT.write_text(text,encoding='utf-8')
    manifest=dict(date='2026-10-01',scope='read-only study comparison and assumption review',
        literature_sources=SOURCES,simulation_evidence_sha256=inputs,
        report_sha256=digest(OUT),script_sha256=digest(Path(__file__)),new_simulations=0,
        interpretation='Partial qualitative agreement, plausibility judgments and untested assumptions; no empirical validation claim.')
    (OUT.with_suffix('.sources.json')).write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n',encoding='utf-8')
    print(OUT)
    print(f'{len(text.split())} words; 9 studies; source/config/effect-table hashes verified')

if __name__=='__main__':main()
