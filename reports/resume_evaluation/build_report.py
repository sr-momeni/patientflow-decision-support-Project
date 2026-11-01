"""Independently reconcile raw simulation outputs, then build static report figures."""
from pathlib import Path
import json
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
O=Path(__file__).resolve().parent
d=pd.read_csv(O/'per_seed_results.csv')
k=pd.read_csv(O/'kpi_comparison.csv')
m=json.loads((O/'artifacts/manifest.json').read_text())
checks=[]
for r in d.to_dict('records'):
    prefix=f'{r["scenario"]}_{r["seed"]}'
    raw=pd.read_csv(O/'artifacts/raw'/f'{prefix}_{r["Model"]}.csv')
    inp=pd.read_csv(O/'artifacts/raw'/f'{prefix}_input.csv')
    merged=raw.merge(inp,left_on='id',right_on='patient_id',validate='one_to_one')
    assert len(merged)==r['n_patients']
    assert (merged.urgency==merged.urgency_level).all()
    assert (merged.bed_type==merged.bed_assigned_type).all()
    assert np.allclose(merged.los_minutes_x,merged.los_minutes_y)
    assert (pd.to_datetime(merged.arrival)==pd.to_datetime(merged.arrival_ts)).all()
    wait=(pd.to_datetime(raw.service_start)-pd.to_datetime(raw.arrival)).dt.total_seconds()/60
    system=(pd.to_datetime(raw.discharge)-pd.to_datetime(raw.arrival)).dt.total_seconds()/60
    assert np.allclose(wait,raw.wait_minutes)
    assert np.isclose(wait.mean(),r['avg_wait'])
    assert np.isclose(system.mean(),r['avg_los'])
    for level in range(1,6):
        assert np.isclose(wait[raw.urgency==level].mean(),r[f'wait_l{level}'])
    for bed in ['ED','ICU']:
        cap={'normal':(50,20),'ed_congestion':(26,8),'severe_congestion':(20,5),'icu_bottleneck':(36,2),'critical_burst':(50,20)}[r['scenario']][bed=='ICU']
        subset=raw[raw.bed_type==bed]
        a=pd.to_datetime(subset.service_start).clip(lower=pd.Timestamp('2026-10-26'))
        b=pd.to_datetime(subset.discharge).clip(upper=pd.Timestamp('2026-10-31'))
        occ=((b-a).dt.total_seconds()/60).clip(lower=0).sum()/(7200*cap)
        assert np.isclose(occ,r[bed.lower()+'_time_occupancy'])
    if r['Model']=='Agent':
        assert np.isclose(r['successful_catches']/r['total_reservations'],r['reservation_success_rate'])
    checks.append({'scenario':r['scenario'],'seed':r['seed'],'model':r['Model'],'patient_reconciliation':'passed','metric_reconciliation':'passed'})
assert len(d)==30 and (d.status=='success').all()
assert (d.groupby(['scenario','seed']).input_sha256.nunique()==1).all()
normal=d[d.scenario=='normal'].reset_index(drop=True)
burst=d[d.scenario=='critical_burst'].reset_index(drop=True)
assert (normal.input_sha256==burst.input_sha256).all()
assert np.allclose(normal.avg_wait,burst.avg_wait)
for r in k.to_dict('records'):
    if pd.notna(r['improvement_pct']):
        assert np.isclose((r['fcfs_mean']-r['agent_mean'])/r['fcfs_mean']*100,r['improvement_pct'])
pd.DataFrame(checks).to_csv(O/'validation_checks.csv',index=False)

order=list(d.scenario.unique())
labels=['Normal','ED congestion','Severe congestion','ICU bottleneck','Critical burst*']
colors=['#315a87','#c76b27']
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
def chart(filename,metrics,titles,ylabels,percent=False):
    fig,axes=plt.subplots(1,len(metrics),figsize=(max(10,7*len(metrics)),5),squeeze=False)
    for ax,metric,title,ylabel in zip(axes[0],metrics,titles,ylabels):
        for j,model in enumerate(['FCFS','Agent']):
            g=d[d.Model==model].groupby('scenario')[metric].agg(['mean','std']).reindex(order)
            scale=100 if percent else 1
            ax.bar(np.arange(5)+(j-.5)*.36,g['mean']*scale,.36,yerr=g['std']*scale,
                   capsize=3,label=model,color=colors[j],hatch='' if j==0 else '//')
        ax.set_xticks(range(5),labels,rotation=20,ha='right');ax.set_title(title);ax.set_ylabel(ylabel);ax.set_ylim(bottom=0);ax.legend()
    fig.text(.01,.015,'Synthetic data; mean ± sample SD across 3 seeds. *Critical burst duplicates Normal; configured surge is unused.',fontsize=9)
    fig.tight_layout(rect=(0,.06,1,1));fig.savefig(O/filename,dpi=160);plt.close(fig)
chart('average_wait.png',['avg_wait'],['Average patient waiting time'],['Minutes'])
chart('urgent_wait.png',['wait_l1','wait_l2'],['CTAS 1 waiting time','CTAS 2 waiting time'],['Minutes','Minutes'])
chart('utilization.png',['ed_time_occupancy','icu_time_occupancy'],['ED occupancy within 5-day window','ICU occupancy within 5-day window'],['Occupied bed-minutes / available (%)']*2,True)
chart('reservation_metrics.png',['reservation_success_rate','wasted_bed_minutes'],['Recorded reservation success (FCFS: N/A)','Recorded reservation duration ("waste")'],['Successful catches / reservations','Recorded bed-minutes'])

def table(metrics):
    lines=['| Scenario | Method | '+' | '.join(label for _,label in metrics)+' |',
           '|---|---|'+'---:|'*len(metrics)]
    for scenario in order:
        for model in ['FCFS','Agent']:
            g=d[(d.scenario==scenario)&(d.Model==model)]
            vals=[]
            for metric,label in metrics:
                vals.append('N/A' if g[metric].isna().all() else f'{g[metric].mean():.3f} ± {g[metric].std():.3f}')
            lines.append('| '+scenario+' | '+model+' | '+' | '.join(vals)+' |')
    return '\n'.join(lines)
summary='''# ED simulation evaluation for resume evidence

Prepared 2026-11-01. Synthetic academic simulation; no hospital outcome or deployment evidence.

## Executive summary

All 30 reproduced runs completed: five named configurations × three seeds × two methods. Each configuration used 752, 742 and 690 generated patients (2,184 patient inputs per configuration), yielding 10,920 scenario-patient inputs and 21,840 method-patient outputs. These are repeated synthetic streams, not 10,920 independent people: arrivals and acuities repeat across scenarios. The strongest defensible achievement is the reproducible comparative analysis and validation, not an overall performance improvement.

The Agent increased average waiting time under ED congestion (27.692 to 36.399 minutes, +31.44%), severe congestion (121.446 to 146.803, +20.88%) and ICU bottleneck (5.479 to 8.004, +46.09%). Under ED congestion, mean CTAS 1 waiting fell from 3.721 to 0.163 minutes (95.62%), and CTAS 2 from 24.966 to 18.109 (27.47%). Those subgroup benefits coexist with worse overall waiting. Only three seeds and few CTAS 1 patients support these estimates; they are not clinical efficacy estimates.

The original CLI failed before running simulations (missing Tuple import). A subsequent saved-model smoke test failed because the model expects 13 features but current inference supplies four; its saved sklearn version also differs. Therefore this is explicitly a **reproduced model evaluation**, not a successful execution of the original model. No reservation, prioritization or allocation policy was tuned.

## Architecture and inspected implementation

Sources: `backend/optimization/evaluate_agent.py`, `congestion_scenarios.py`, `backend/simulation/engine.py`, `predictive_engine.py`, `event_model.py`, `backend/data/synthetic_generator.py`, `backend/ml/predictor.py`, `train_model.py`, `backend/agents/resource_allocation_agent.py`, `urgency_scoring_agent.py`, `backend/simulation/realtime_manager.py`, README, datasets, existing evaluation CSVs and test files. Source hashes and package versions are in [manifest](artifacts/manifest.json).

The generator samples daily volumes around 155 multiplied by weekday effects, with 8% Gaussian variability and a 60-patient floor. It applies hourly weights, day/night CTAS probabilities, probabilistic ICU need (70% for level 1, 15% for level 2), clamped log-normal service durations and laboratory/imaging queue estimates. Generated `los_minutes` includes the triage interval; the engines treat all of it as bed service duration. CTAS is sampled here, not derived from symptoms.

Scenario per-level arrival rates, peak multiplier, physicians and nurses do not drive simulated arrivals or staffing constraints. Bed capacities and lab/imaging capacity can matter. Normal and Critical Burst have identical operative inputs and outputs: the latter is not a tested critical surge. The ICU bottleneck simulation fixes patients to their generated bed type; it does not implement the described ED boarding/ICU transfer pathway.

FCFS sorts arrivals and assigns the earliest available bed separately within ED and ICU. PredictiveEngine uses event queues, dynamic effective urgency `level × (1 - min(1, wait / target))`, targets 30/150/230/245/250 minutes for levels 1–5, and arrival-time tie breaking. All urgency scores eventually reach zero; these targets are aging parameters, not guaranteed service limits. Expected L1/L2 count ≥0.8 triggers one reservation in each unit, nominally held 30 minutes. The threshold is an expected count, not an 80% probability. No priority-only ablation was run, so subgroup effects cannot be attributed to prediction alone.

The application is different: UrgencyScoringAgent combines clinical rules, overrides and thresholds; ResourceAllocationAgent sorts a base urgency score plus waiting/risk modifiers and produces bed recommendations and heuristic waits. RealtimeManager loads a different model path and applies occupancy gates to reservations. The scenario evaluator never calls this application workflow, database, chatbot or OpenAI. README assertions about working UI, voice, live allocation and end-to-end integration were not established by this evaluation.

## Environment and model reproduction

Python and all evaluation imports were available; exact versions are in the manifest. requirements.txt does not explicitly list matplotlib, seaborn, python-dateutil or pytest, despite their use here. The only production-source change is importing Tuple in predictive_engine.py. Existing user modifications, model, database and old data/evaluation outputs were preserved. All evaluator writes were redirected into artifacts/ through a working-directory change.

The current four-feature inference (sine/cosine of hour and weekday) was preserved. The existing prepare_training_data function calculates 13 features and next-60-minute L1/L2 labels; the reproduction uses its first four columns, matching inference. The same HistGradientBoostingRegressor parameters are fitted directly on a separate 30-day synthetic normal stream beginning 2026-01-05, seed 202601. A seven-day stream starting 2026-03-02, seed 202602, is validation only. Evaluation begins Monday 2026-10-26, seeds 42–44, and never enters training or model selection. Last-hour training/validation observations are removed to avoid incomplete target windows. No random row split, overlapping training/validation target windows, hyperparameter selection or threshold search was used. This avoids the overlapping-window leakage risk in the existing random 80/20 split; it does not establish generalization to real patients or unseen generators. Original saved-model training provenance is unknown.

TRAINING_DETAILS

## Metric definitions and caveats

- `avg_wait`: arithmetic mean of service_start minus arrival, in minutes. CTAS means use only that level; counts n_l1…n_l5 are retained per seed.
- `avg_los`: evaluator mean of waiting plus input los_minutes, so it is total simulated time in system, not service-only LOS. The unused summarize_simulation_metrics helper instead labels service-only duration average_los and uses a different occupancy denominator; those definitions must not be mixed.
- `ed_occ`/`icu_occ`: min(1, sum of all input service minutes / (5 × 1,440 × beds)). They include service outside the arrival window and do not respond to scheduling; they are capped demand estimates, not observed occupancy.
- `ed_time_occupancy`/`icu_time_occupancy`: added reporting-only measurements. Sum each patient's service interval intersected with [2026-10-26 00:00, 2026-10-31 00:00), divided by 7,200 × capacity. These are actual simulated bed-time occupancy fractions; no policy change was made.
- `total_reservations`, `successful_catches`, `expired_reservations`: original engine counters. A success requires effective urgency exactly 1.0, not simply a high-urgency arrival. Aged patients can consume reservations without incrementing success; outstanding reservations may remain. Success plus expiry therefore need not equal total. Reservation success is not clinical prediction accuracy.
- `wasted_bed_minutes`: engine sums elapsed reservation time on expiration and consumption, including successful consumption. It neither checks whether a reserved bed was physically idle nor counts all pending terminal reservations. Expiry is processed at the next arrival/discharge, not its own scheduled timeout event. This is recorded reservation duration, not a valid measurement of avoidable idle capacity or a financial saving.
- FCFS reservation counts/duration are zero; its success rate is N/A. Original precision field is retained but its zero-denominator zero is not treated as a measured rate. Missing/zero-baseline percentage improvements are blank rather than invented.

## Scenario results

Means ± sample SD (ddof=1) across three seeds, equally weighting seeds within each scenario. These are seed-level means, not pooled patient means; no cross-scenario performance average is claimed.

WAIT_TABLE

![Average waiting](average_wait.png)
![High urgency waiting](urgent_wait.png)

OCC_TABLE

Occupancy fractions above are 0–1; the figure shows percentages. The raw demand estimates and all reservation counters are in evaluation_results.csv.

![Time-based occupancy](utilization.png)

RES_TABLE

![Reservation metrics](reservation_metrics.png)

## Calculations, uncertainty and operational interpretation

For lower-is-better metrics, improvement = (FCFS seed-mean − Agent seed-mean) / FCFS seed-mean × 100. kpi_comparison.csv also retains the mean of per-seed percentage improvements separately; it can differ substantially and excludes undefined zero-baseline ratios. Example ED congestion: (27.6923459406 − 36.3991838875) / 27.6923459406 × 100 = approximately −31.44%. Use the full-precision CSV values for exact recalculation.

Severe congestion had the longest overall waits. Its mean CTAS 1 wait fell 73.68% (24.765 to 6.519 minutes), and CTAS 2 fell 21.04% (111.722 to 88.218), while overall waiting increased 25.357 minutes. ICU bottleneck worsened both CTAS 1 (+13.97%) and CTAS 2 (+30.92%) waiting. Normal and duplicated Critical Burst had zero FCFS mean wait and only 0.00534 minutes Agent mean wait; percentage improvement is undefined. The negative overall results are consistent with prioritization and reservation trade-offs but do not isolate their individual causal contributions.

Capacity planning should monitor overall and urgency-specific waits, tail waits, time in system, time-based occupancy, arrivals by urgency, completion/backlog, and actual idle held-bed time. High occupancy alone is not evidence of better care. The existing capped utilization estimate cannot support a utilization improvement claim, and recorded reservation waste cannot support saved-capacity claims. A larger preregistered seed set, priority-only comparison, corrected scenario-generation sensitivity tests and reservation event accounting would distinguish prediction value from scheduling effects. Those would be separate validation work, not retrospective tuning of this benchmark.

## Validation and coverage

All 30 runs completed all patients, with nonnegative waits and peak occupied beds within capacity. build_report.py independently rereads all 30 raw output files, joins each one-to-one to its input, verifies unchanged arrivals/urgency/service/bed type, recomputes waits and time in system from timestamps, CTAS means, clipped occupancy and percentage improvements. validation_checks.csv records those checks. Each FCFS/Agent pair has the same input hash. Inputs are fixed-date and seeded; event ties use object identity in the original engine and could be nondeterministic if exact same-type timestamp ties occur.

`python -m pytest -q`: 5 passed, 6 failed. Four scenario checks and one required-column generator check passed. One obsolete test assumes generator ICU bottlenecks increase LOS (both were 188.47); five legacy wrapper tests fail because generate_patients passes unsupported n to generate_events. These defects were reported rather than changing unrelated code. `python -m backend.agents.test_triage`: five printed clinical-rule examples passed, not a comprehensive clinical validation. The realtime integration script exists but calls the chatbot/service workflow and was not executed. Frontend, external APIs, MySQL, deployment, privacy and clinical safety were not tested.

Existing data/evaluation_scenarios.csv contains a removed moderate_congestion scenario and materially different numbers. It has no demonstrated provenance matching the current generator and was not used as new evidence or overwritten.

## Reproduce and audit

From repository root, with the manifest's Python/package versions available:

```powershell
$env:OMP_NUM_THREADS="1"
python reports/resume_evaluation/run_evaluation.py
python reports/resume_evaluation/build_report.py
python -m pytest -q
python -m backend.agents.test_triage
```

run_evaluation.py calls the existing run_scenarios(days=5, seeds=[42,43,44]) with scoped adapters for fixed dates, the separate model and metric capture. Its generated original-format CSV is artifacts/data/evaluation_scenarios.csv. The untouched CLI still points at the incompatible original model; use the documented runner for this reproduction. Re-running backs up existing artifacts and result CSVs before replacing them. Training/validation datasets, the fitted model, input CSVs, patient outputs, per-run event logs, source hashes and environment metadata are retained. execution.log records the completed run; tests.txt and triage_checks.txt retain test evidence.

Deliverables: evaluation_results.csv (means, SD, minima, maxima), per_seed_results.csv (30 rows), kpi_comparison.csv (75 comparisons), evaluation_summary.md and resume_bullets.md. No SQL/MySQL analysis was performed; no SQL achievement is inferred from a database dependency. Team contribution ownership cannot be established from this run; resume wording should be used only if you can explain and take responsibility for this assisted evaluation.
'''
summary=summary.replace('TRAINING_DETAILS',f"Training: {m['train']['patients']:,} generated patients, {m['train']['samples']:,} complete-window samples. Validation: {m['validation']['patients']:,} patients, {m['validation']['samples']:,} samples. Held-out synthetic count MAE {m['validation_metrics']['mae']:.3f}, MSE {m['validation_metrics']['mse']:.3f}, R² {m['validation_metrics']['r2']:.3f}; these are forecasting diagnostics, not clinical accuracy.")
summary=summary.replace('WAIT_TABLE',table([('avg_wait','Wait min'),('wait_l1','CTAS 1 min'),('wait_l2','CTAS 2 min'),('avg_los','System time min')]))
summary=summary.replace('OCC_TABLE',table([('ed_time_occupancy','ED occupancy'),('icu_time_occupancy','ICU occupancy')]))
summary=summary.replace('RES_TABLE',table([('total_reservations','Reservations'),('successful_catches','Successes'),('expired_reservations','Expired'),('reservation_success_rate','Success fraction'),('wasted_bed_minutes','Recorded duration min')]))
summary=summary.replace('Only three seeds and few CTAS 1 patients support these estimates;', 'Only three seeds, with 11, 2 and 13 CTAS 1 patients respectively (and 108, 103 and 105 CTAS 2 patients), support these estimates;')
example=k[(k.scenario=='ed_congestion') & (k.metric=='avg_wait')].iloc[0]
summary=summary.replace('(27.6923459406 − 36.3991838875) / 27.6923459406',f'({example.fcfs_mean:.10f} − {example.agent_mean:.10f}) / {example.fcfs_mean:.10f}')
(O/'evaluation_summary.md').write_text(summary,encoding='utf-8')
(O/'resume_bullets.md').write_text('''# Ranked resume bullet candidates

Use only if you can explain and take responsibility for this assisted evaluation. These describe this analysis, not sole authorship of the team system. Synthetic simulation only; no hospital deployment or SQL execution claim.

1. Evaluated ED scheduling methods in Python across 30 simulation runs, five configurations and three random seeds, reporting waiting-time and capacity KPIs for 10,920 synthetic scenario-patient inputs.
2. Built reproducible Python KPI reports comparing FCFS and predictive scheduling, identifying 20.9%–46.1% longer average waits across three congested configurations.
3. Validated 21,840 simulated patient outputs against source inputs and timestamps, reconciling waiting time, time in system and bed occupancy across 30 runs.
4. Analyzed urgency-based scheduling trade-offs: ED-congestion CTAS 2 waits fell 27.5% while overall waiting increased 31.4% in a three-seed synthetic evaluation.
5. Audited five simulation configurations and identified an unused arrival-rate setting that made Critical Burst duplicate Normal, limiting surge-performance claims.

## Evidence mapping

- Bullet 1: per_seed_results.csv has 30 successful rows, five scenarios, seeds 42/43/44; patient counts per scenario are 752 + 742 + 690 = 2,184; 5 × 2,184 = 10,920 scenario inputs. Repeated streams across scenarios are not independent people.
- Bullet 2: kpi_comparison.csv, metric avg_wait: ED congestion improvement −31.4413%, severe congestion −20.8793%, ICU bottleneck −46.0898%. Negative improvement means longer waits. run_evaluation.py and build_report.py implement the reporting pipeline.
- Bullet 3: sum(per_seed_results.n_patients) = 21,840; validation_checks.csv and build_report.py verify each raw file against artifacts/raw/*_input.csv. This count includes both methods.
- Bullet 4: kpi_comparison.csv, ed_congestion, wait_l2 and avg_wait. Formula (FCFS mean − Agent mean) / FCFS mean × 100; means are equally weighted across three seeds.
- Bullet 5: synthetic_generator.py generate_events never reads arrival_rates_per_hour; same-seed normal and critical_burst input hashes and outputs match.

The first two are the strongest general Junior Data Analyst / Reporting Analyst candidates. The third suits data-validation roles; the fourth suits healthcare analytics when accompanied by the trade-off. Do not claim a 95.6% overall improvement, clinical prediction accuracy, real bed savings, MySQL work, or personal ownership of the original team system from this evidence.
''',encoding='utf-8')
print('Validated 30 runs and 21,840 patient outputs; generated report and four charts.')
