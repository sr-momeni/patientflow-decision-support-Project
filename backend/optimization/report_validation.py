"""Audit persisted results and render the technical report; never fit or tune."""
from pathlib import Path
import hashlib,json,shutil
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from backend.optimization.validate_simulation import interval

ROOT=Path(__file__).resolve().parents[2]
O=ROOT/'reports/simulation_validation'
F=O/'final_test'

def md(frame):
    def fmt(x):
        if isinstance(x,(float,np.floating)):
            return 'N/A' if not np.isfinite(x) else f'{x:,.3f}'
        return str(x)
    return '| '+' | '.join(map(str,frame.columns))+' |\n|'+ '|'.join(['---']*len(frame.columns))+'|\n'+'\n'.join('| '+' | '.join(fmt(v) for v in row)+' |' for row in frame.itertuples(index=False,name=None))

def main():
    completion=json.loads((F/'completion.json').read_text())
    assert completion['complete']
    d=pd.read_csv(F/'per_seed_results.csv')
    pairs=pd.read_csv(F/'paired_comparisons.csv')
    summary=pd.read_csv(F/'scenario_summary.csv')
    forecast=pd.read_csv(F/'forecast_results.csv')
    assert len(d)==450 and (d.groupby(['scenario','method']).size()==30).all()
    assert (d.groupby(['scenario','seed']).input_sha256.nunique()==1).all()
    history=json.loads((O/'historical_sha256.json').read_text())
    for path,digest in history.items():
        assert hashlib.sha256((ROOT/path).read_bytes()).hexdigest()==digest,path
    audits=[]
    loads=[]
    for row in d.to_dict('records'):
        prefix=f'final_{row["scenario"]}_{row["seed"]}'
        raw=pd.read_csv(F/'raw'/f'{prefix}_{row["method"]}.csv.gz')
        if row['method']=='FCFS':
            from backend.optimization.congestion_scenarios import get_scenario
            cfg=get_scenario(row['scenario'])
            inp=pd.read_csv(F/'inputs'/f'{prefix}.csv.gz')
            assert hashlib.sha256((F/'inputs'/f'{prefix}.csv.gz').read_bytes()).hexdigest()==row['input_sha256']
            joined=raw.merge(inp,left_on='id',right_on='patient_id',validate='one_to_one')
            assert len(joined)==len(raw)
            assert (joined.urgency==joined.urgency_level).all()
            assert (joined.bed_type==joined.bed_assigned_type).all()
            assert np.allclose(joined.los_minutes_x,joined.service_minutes)
            loads.append(dict(scenario=row['scenario'],seed=row['seed'],
                ed_service_demand_ratio=inp.loc[inp.bed_assigned_type=='ED','service_minutes'].sum()/(7200*cfg.ed_beds),
                icu_service_demand_ratio=inp.loc[inp.bed_assigned_type=='ICU','service_minutes'].sum()/(7200*cfg.icu_beds),
                triage_demand_ratio=inp.triage_minutes.sum()/(7200*cfg.nurses),
                initial_assessment_demand_ratio=len(inp)*15/(7200*cfg.physicians),
                lab_demand_ratio=inp.lab_required.sum()/(120*cfg.lab_slots_per_hour),
                imaging_demand_ratio=inp.imaging_required.sum()/(120*cfg.imaging_slots_per_hour)))
        arrival=pd.to_datetime(raw.arrival);assessment=pd.to_datetime(raw.service_start);departure=pd.to_datetime(raw.discharge)
        waits=(assessment-arrival).dt.total_seconds()/60
        system=(departure-arrival).dt.total_seconds()/60
        assert len(raw)==row['n_patients'] and raw.id.nunique()==len(raw)
        assert np.isclose(waits.mean(),row['avg_wait'])
        assert np.isclose(system.mean(),row['avg_system_time'])
        assert np.isclose(waits.quantile(.9),row['p90_wait'])
        assert np.isclose(system.quantile(.9),row['p90_system_time'])
        if row['method']=='Predictive':
            holds=pd.read_csv(F/'raw'/f'{prefix}_reservations.csv.gz')
            assert len(holds)==row['total_reservations']
            assert (holds.reason=='caught_future_high_urgency').sum()==row['successful_catches']
            assert (holds.reason=='expired').sum()==row['expired_reservations']
            elapsed=(pd.to_datetime(holds.end)-pd.to_datetime(holds.start)).dt.total_seconds()/60
            assert np.allclose(elapsed,holds.duration_minutes)
            assert np.isclose(elapsed.sum(),row['reservation_duration_minutes'])
        audits.append(dict(scenario=row['scenario'],seed=row['seed'],method=row['method'],patient_rows=len(raw),passed=True))
    pd.DataFrame(audits).to_csv(F/'persisted_output_audit.csv',index=False)
    load_frame=pd.DataFrame(loads)
    load_frame.to_csv(F/'offered_resource_load.csv',index=False)
    load_summary=load_frame.groupby('scenario',sort=False).mean(numeric_only=True).drop(columns='seed').reset_index()
    # Independent paired-difference reconciliation from per-seed data.
    for row in pairs.to_dict('records'):
        g=d[d.scenario==row['scenario']]
        a=g[g.method==row['baseline']].set_index('seed')[row['metric']]
        b=g[g.method==row['method']].set_index('seed')[row['metric']].reindex(a.index)
        value=(b-a).mean()
        assert (pd.isna(value) and pd.isna(row['delta_mean'])) or np.isclose(value,row['delta_mean'])
    forecast_summary=[];forecast_pairs=[]
    for (scenario,model),g in forecast.groupby(['scenario','predictor'],sort=False):
        for metric in ['mae','rmse','r2','bias']:
            forecast_summary.append(dict(scenario=scenario,predictor=model,metric=metric,**interval(g[metric])))
    for scenario,g in forecast.groupby('scenario',sort=False):
        model=g[g.predictor=='model'].set_index('seed')
        for baseline in ['training_mean','persistence_60m']:
            b=g[g.predictor==baseline].set_index('seed').reindex(model.index)
            forecast_pairs.append(dict(scenario=scenario,baseline=baseline,**interval(model.mae-b.mae)))
    fs=pd.DataFrame(forecast_summary);fp=pd.DataFrame(forecast_pairs)
    fs.to_csv(F/'forecast_summary.csv',index=False);fp.to_csv(F/'forecast_paired_mae.csv',index=False)
    order=list(d.scenario.unique());methods=['FCFS','CTAS','Predictive'];colors=['#41678e','#58804c','#bd6b29']
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
    def plot(filename,metrics,titles,units,scale=1):
        fig,axes=plt.subplots(1,len(metrics),figsize=(max(10,7*len(metrics)),5),squeeze=False)
        for ax,metric,title,unit in zip(axes[0],metrics,titles,units):
            for i,method in enumerate(methods):
                g=summary[(summary.method==method)&(summary.metric==metric)].set_index('scenario').reindex(order)
                ax.bar(np.arange(5)+(i-1)*.25,g['mean']*scale,.25,
                    yerr=(g['ci95_high']-g['mean'])*scale,capsize=3,label=method,color=colors[i],hatch=['','//','..'][i])
            ax.set_xticks(range(5),[x.replace('_','\n') for x in order]);ax.set_title(title);ax.set_ylabel(unit);ax.set_ylim(bottom=0);ax.legend()
        fig.text(.01,.015,'Synthetic, uncalibrated stress tests. Mean across 30 independent streams per scenario; bars show 95% t intervals.',fontsize=9)
        fig.tight_layout(rect=(0,.05,1,1));fig.savefig(O/filename,dpi=150);plt.close(fig)
    plot('waiting_comparison.png',['avg_wait'],['Arrival-to-initial-assessment waiting'],['Hours'],1/60)
    plot('urgency_comparison.png',['wait_l1','wait_l2'],['CTAS 1 wait','CTAS 2 wait'],['Hours','Hours'],1/60)
    plot('occupancy_comparison.png',['ed_occupancy','icu_occupancy'],['ED occupied bed time','ICU occupied bed time'],['Percent of 5-day capacity']*2,100)
    plot('reservation_comparison.png',['reserved_idle_bed_minutes','blocked_idle_bed_minutes'],['Physically idle reserved beds','Reserved idle bed with waiting demand'],['Bed-minutes','Bed-minutes'])
    main_table=summary[summary.metric=='avg_wait'][['scenario','method','mean','sd','ci95_low','ci95_high']]
    contrast=pairs[(pairs.metric=='avg_wait')&(((pairs.baseline=='FCFS')&(pairs.method=='CTAS'))|((pairs.baseline=='CTAS')&(pairs.method=='Predictive')))][['scenario','baseline','method','delta_mean','delta_ci95_low','delta_ci95_high','improvement_pct']]
    scale=d[d.method=='FCFS'].groupby('scenario',sort=False).agg(streams=('seed','count'),patient_inputs=('n_patients','sum'),mean_patients=('n_patients','mean'),min_patients=('n_patients','min'),max_patients=('n_patients','max'))
    forecast_table=fs[fs.metric=='mae'][['scenario','predictor','mean','ci95_low','ci95_high']]
    reservations=d[d.method=='Predictive'].groupby('scenario',sort=False)[['total_reservations','successful_catches','expired_reservations','cancelled_reservations','reservation_duration_minutes','reserved_idle_bed_minutes','blocked_idle_bed_minutes']].sum()
    reservations['pooled_success_rate']=reservations.successful_catches/reservations.total_reservations
    generation=pd.read_csv(F/'generator_checks.csv')
    generation=generation.groupby(['scenario','ctas'],sort=False)[['observed','expected']].sum().reset_index()
    generation['poisson_z']=(generation.observed-generation.expected)/np.sqrt(generation.expected)
    generation.to_csv(F/'arrival_calibration_checks.csv',index=False)
    backlog=d.groupby(['scenario','method'],sort=False)[['waiting_at_horizon','in_service_at_horizon','departed_by_horizon','drain_minutes']].mean().reset_index()
    urgent=d.groupby(['scenario','method'],sort=False)[['wait_l1','wait_l2','wait_l3','wait_l4','wait_l5']].mean().reset_index()
    historical=json.loads((ROOT/'reports/resume_evaluation/artifacts/manifest.json').read_text())
    assert hashlib.sha256((ROOT/'models/urgency_predictor.pkl').read_bytes()).hexdigest()==historical['original_model_sha256']
    frozen=json.loads((O/'development/frozen.json').read_text())
    for path,digest in frozen['source_hashes'].items():
        src=ROOT/path
        assert hashlib.sha256(src.read_bytes()).hexdigest()==digest
        dest=O/'source_snapshot'/path;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dest)
    report=f'''# ED simulation correction and validation

Prepared 2026-11-01. Status: **verified within the synthetic finite-cohort model; not calibrated or externally validated for Ontario**.

## Executive summary

The corrected pipeline completed {len(d)} final comparison runs on 150 independent scenario streams, with 30 streams in each of five scenarios. Each stream was shared unchanged by FCFS, strict CTAS priority and predictive CTAS priority. There were {int(scale.patient_inputs.sum()):,} synthetic input records and {int(d.n_patients.sum()):,} method-patient outputs. Training used 25 separate streams; validation used 25 further streams (75 comparison runs). No final-test stream was used for fitting, parameter selection or bug-driven performance tuning.

The scenario generator, causal feature contract, reservation lifecycle and KPI calculations were corrected. All automated tests pass (see [test output](tests.txt)), and every final run passed patient conservation and bed/nurse/physician/diagnostic capacity checks. Persisted final outputs were independently reread and reconciled. The original evaluation and model remain unchanged, verified by SHA-256.

CTAS-only priority increased overall mean waiting in all five final scenarios while reducing CTAS 1 and CTAS 2 waiting. Adding reservations increased overall mean waiting by 0.226?1.725 minutes versus CTAS alone. Critical Burst?s paired 95% interval spans zero; the ED-congestion lower bound is only 0.0003 minutes and is not a robust multiple-comparison finding. The forecasting model had lower held-out MAE than both training-mean and last-hour persistence in every scenario; all paired model-minus-persistence MAE intervals were below zero. Better forecasting therefore did not demonstrate better scheduling.

These configured rates are stress loads, including the scenario named Normal. Large queues persist after five arrival days. Correct event execution does not establish a realistic Ontario ED model. The admitted ED departure/boarding pathway is absent; system time must not be presented as NACRS admitted ED length of stay.

## Root causes and what can be concluded

1. **Scenario generation was disconnected from configuration.** The old generator used roughly 155 arrivals/day and fixed day/night CTAS weights, ignoring per-level scenario rates and the peak multiplier. Critical Burst duplicated Normal. The correction activates the configured rates; it does not reduce them to make results look plausible. Old and corrected experiment percentages are therefore not an apples-to-apples estimate of a code-fix benefit.
2. **Predictor contracts disagreed.** Training prepared 13 features; inference supplied four. The old saved model also came from another sklearn version. The earlier resume evaluation deliberately trained a separate four-feature model, with validation R² about −0.112. The new model uses one named, versioned 13-feature extractor for both training snapshots and inference, requires compatible model metadata, and leaves old artifacts intact.
3. **Reservation accounting understated catches and mislabeled waste.** Old catches required aged urgency exactly 1.0; CTAS 2 and aged CTAS 1 patients could consume holds without success. Holds could be created against fully occupied units, expired only on later patient events, and accumulated duration even when no bed was idle. The corrected ledger reconciles every hold and separately measures physical idleness and blocked demand.
4. **Priority and prediction were confounded.** FCFS was compared with priority plus reservations. The new CTAS-only arm isolates the incremental reservation policy under this model. Strict nonpreemptive CTAS priority replaces the old aging formula and its hard-coded targets; this is an explicit policy definition change, not a claimed clinical correction or tuned improvement. FCFS/CTAS use identical resource mechanics.
5. **KPI definitions were inconsistent.** Old avg_los included waiting; an alternative helper excluded it. Old utilization was a capped demand ratio. New metrics use actual timestamps and window-clipped occupied intervals.

The previous negative outcomes are valid observations of that implementation, not proof that one particular bug caused all of the deterioration. Mechanistic defects above are established by code and regression tests; precise contributions to old outcome differences would require a separate historical ablation. Negative corrected results and uncertainty are retained below.

## Corrected methods

**Arrivals and CTAS.** For level c, day d and hour h, N follows Poisson(rate[c] × weekday[d] × normalized_hour_shape[h]). The peak multiplier applies to hours 10–14 before normalization; the hourly shape has mean one, preserving the configured daily-average rate. Within-hour arrivals are uniform. Each configured CTAS rate generates its own counts, so expected CTAS share is rate[c]/sum(rate). Monday–Friday weekday multipliers remain 1.0, 0.9, 0.9, 0.9, 1.0. Local independent NumPy RNG streams generate arrivals and care requirements; capacities do not alter exogenous patient inputs. See [arrival checks](final_test/arrival_calibration_checks.csv) for observed/expected counts and Poisson residuals; these check the generator, not calibration to healthcare data.

**Service and resources.** Existing clamped log-normal service parameters and care-need probabilities are retained as uncalibrated assumptions. Generated los_minutes is explicitly a compatibility alias for bed service requirement, not observed LOS. Generated assessment/departure fields are blank. Nurse triage lasts the sampled 3–10 minutes and is FCFS for all methods. After triage, admission requires a free fixed-type bed and physician. The physician performs a fixed 15-minute initial assessment, then becomes available. Requested lab and imaging services enter explicit sequential queues, each modelled as one throughput server with service time 60/slots_per_hour minutes. Beds remain occupied until both base care and diagnostics finish. Nurse and physician staffing limits apply to these defined tasks, not all care over the whole visit. Senior-staff flags and alert thresholds remain descriptive metadata; no skill-mix capability model is claimed.

**Scheduling.** FCFS orders by arrival. CTAS and Predictive order by clinical level then arrival then stable input sequence. There is no preemption, no shortest-job scheduling and no outcome-tuned aging. Strict priority can impose long lower-acuity waits; finite cohorts eventually drain, but continuous-load starvation is not ruled out. Two fixed ED/ICU pools are used; an unavailable ICU does not silently change the patient's requirement.

**Prediction.** Thirteen features: sine/cosine of hour and weekday, ED/ICU occupied fractions, arrivals in trailing 15/30/60/240 minutes, and active CTAS 1/2/3 counts. Features use only state available at decision time. Forecast samples occur every 15 minutes; labels count CTAS 1/2 arrivals in [t,t+60 minutes). Initial four hours are excluded from forecasting evaluation and training; the last hour is excluded unless its full target window is observed. This does not remove the initial transient from scheduling outcomes. Training snapshots are collected under CTAS-only scheduling; model use under reservations can shift state, which remains a limitation. The estimator is HistGradientBoostingRegressor with the original fixed settings (100 iterations, depth 10, learning rate 0.1, random_state 42).

**Holds.** Every 15 minutes until the fixed five-day horizon, expected CTAS 1/2 count ≥0.8 can reserve at most one physically free bed in each pool, for 30 minutes. No hold is created when a high-urgency patient is already in that pool's waiting queue. Unreserved beds are used first. A CTAS 1/2 patient arriving at/after hold creation consumes the last held free bed and counts as a catch; an older patient needing it cancels the hold. Expiry is a scheduled event and cannot immediately rehold the bed at the same timestamp, allowing the queue to advance. Horizon closure cancels remaining holds; post-horizon draining creates no new holds. Threshold 0.8 is an expected count, not a probability. The shared forecast is not unit-specific; its inability to distinguish demand for ED versus ICU is a substantive policy limitation.

**Reservation measures.** Total holds = successful catches + expired + cancelled. Duration is elapsed hold lifetime. Reserved idle bed-minutes integrate actual free capacity under a hold; under this policy they equal duration by construction because occupied beds cannot be reserved. Blocked idle bed-minutes additionally require a waiting patient, no other free bed in that pool, and a free physician. This is a local opportunity-cost measure, not a causal estimate of total delay or a monetary saving. Reservation success is utilization of holds, not clinical accuracy and not general forecasting precision. Low success can remain because high-urgency patients use other free beds, because a forecast is not unit-specific, or because queues leave no free beds to reserve.

## Prespecified splits and uncertainty

[protocol.json](protocol.json) was written before development runs. For scenario index i (0–4 in repository order), train seeds are 100000+1000i+j (j=0…4), validation seeds 200000+1000i+j (j=0…4), final seeds 300000+1000i+j (j=0…29). All streams cover five arrival days from 2026-01-05 00:00, starting empty and draining to completion. Reusing weekday dates across independent streams does not share patient records. Dates are naive synthetic clocks, with no DST transitions; future Ontario ingestion needs explicit timezone handling.

Development froze code hashes, model hash and protocol hash before final access. The final runner checks them and refuses overwrite. Neither the threshold nor estimator was selected by validation or final results. Same-stream paired comparisons control input randomness. Reported mean/SD/t-based 95% intervals use 30 stream-level values per scenario, never patient rows as independent replications. Paired differences are method minus baseline, so positive waiting-time differences indicate deterioration. Improvement percentages use (baseline mean − method mean)/baseline mean ×100; their percentile bootstrap intervals use 5,000 paired stream resamples with a fixed analysis RNG. Multiple comparisons are descriptive and unadjusted; the intervals quantify Monte Carlo uncertainty conditional on this simulator, not real-world model validity. No overall performance average across different scenarios is reported.

## Final cohort scale

{md(scale.reset_index())}

## Overall waiting: minutes, seed-level mean and uncertainty

{md(main_table)}

![Overall waiting in hours](waiting_comparison.png)

### Separating priority from reservations

{md(contrast)}

The CTAS-versus-FCFS contrast measures the scheduling-order change within the corrected resource model. Predictive-versus-CTAS measures the incremental hold policy. A confidence interval spanning zero does not establish a benefit or prove equivalence. Large FCFS-to-Predictive differences must not all be attributed to forecasting.

### Waiting by urgency (minutes)

{md(urgent)}

![CTAS waits](urgency_comparison.png)

Full per-urgency uncertainty, time in system, median/P90 waits, occupancy and cohort completeness are in [scenario_summary.csv](final_test/scenario_summary.csv). Mean seed P90 is not a pooled population percentile.

### Occupancy and unfinished work at the arrival horizon

![Time-based occupancy](occupancy_comparison.png)

{md(backlog)}

### Offered workload relative to five-day resource capacity

{md(load_summary)}

These ratios are input workload / available service capacity, **not occupancy**. A value above one exceeds the resource's five-day capacity even before timing mismatch. Bed-service ratios exclude added diagnostic blocking; physician ratios cover initial assessment only. These measurements help explain backlog without changing demand or claiming Ontario calibration.

Waiting patients are followed through drain, not discarded or assigned zero wait. drain_minutes is time beyond the five-day arrival horizon until the last departure. All resource intervals are checked for capacity violations. These enormous finite-cohort delays and backlogs make current rate/capacity settings unsuitable as empirical Ontario estimates; increasing the number of seeds cannot repair that structural issue.

## Held-out predictive performance

Forecast MAE is measured in CTAS 1/2 arrivals per next hour. Each stream supplies complete-window fixed-grid observations; interval calculations cluster at the stream level. The training-mean baseline uses training data only. Persistence predicts the preceding hour's high-urgency count. Neither baseline uses future labels or final-set fitting.

{md(forecast_table)}

[Forecast paired MAE contrasts](final_test/forecast_paired_mae.csv) report model minus baseline with 95% intervals; negative values favor the model. RMSE, bias and R² are also available in [forecast_summary.csv](final_test/forecast_summary.csv), with per-window truth/predictions retained in compressed raw forecast files. Better count forecasts do not establish improved scheduling, suitable calibration, or clinical prediction accuracy.

## Reservation ledger: totals across 30 streams per scenario

{md(reservations.reset_index())}

The pooled success fraction here uses sum(catches)/sum(holds); per-seed rates and their seed-mean uncertainty are separately retained. FCFS and CTAS have no holds and an undefined success rate, not zero accuracy.

![Physical reserved idle and blocked capacity](reservation_comparison.png)

## KPI definitions and Ontario boundary

- Arrival: generated registration time; assumed no earlier triage. Actual nurse triage start/end are retained separately.
- wait: physician initial assessment start minus arrival. In this model it includes triage and bed/physician queue delays and is not a pure bed-queue metric.
- system time: physical simulated resource departure minus arrival, not the input service duration. It includes ICU treatment when the patient is routed to ICU and is therefore not generally ED LOS.
- ED/ICU occupancy: sum of each bed-service interval intersected with the fixed five-day window, divided by capacity ×7,200 minutes. It is not capped; impossible occupancy is detected by capacity assertions.
- Missing urgency/disposition strata produce NaN, not invented zero waits. Incomplete patients cause KPI calculation to fail rather than hide censoring.
- P50/P90 use NumPy linear interpolation and retain units in minutes. Benchmark export must explicitly convert to hours and verify the source's quantile convention and exclusions.

Only official **definitions** were consulted. CIHI defines initial physician wait from the earlier of registration or triage to initial assessment, and admitted ED total time ends when the patient actually leaves the ED. See [CIHI initial assessment](https://www.cihi.ca/en/indicators/emergency-department-wait-time-for-physician-initial-assessment) and [CIHI admitted ED time](https://www.cihi.ca/en/indicators/total-time-spent-in-emergency-department-for-admitted-patients). No Ontario aggregate statistics were used or claimed as validation. [Ontario readiness](ontario_benchmark_readiness.md) and [benchmark contract](benchmark_contract.json) specify required sources, cohorts, missing pathway work, calibration/validation separation and explicit status gates.

## Verification, preservation and reproducibility

The six prior failing tests were resolved: the fixed-count compatibility wrapper now returns exactly n consistently generated records with legacy fixture IDs; the invalid assertion that ICU capacity alters generated service duration was replaced with a controlled queue test where fewer ICU beds increase waiting on identical service inputs. New tests cover all five scenarios' rate/CTAS expectations, fixed RNG behavior, peak normalization, resource queues, FCFS/CTAS ordering, disabled-prediction equivalence, deterministic ties, exact expiry, future CTAS 2 catches, terminal reconciliation, no full-bed reservation, KPI window clipping, missing strata, feature persistence and no future-feature contamination.

Every comparison run was checked against its original inputs, for nonnegative ordered timestamps, patient conservation, occupied resource intervals and complete reservation accounting. All {int(d.n_patients.sum()):,} final raw patient rows were reread to reconcile waits, system time and percentiles; every reservation ledger was reread for counts and durations. [validation_checks.csv](final_test/validation_checks.csv) and [persisted_output_audit.csv](final_test/persisted_output_audit.csv) retain evidence. Every paired metric difference was independently recomputed from saved per-seed values. Historical file hashes and the original model hash were verified unchanged.

Sources before edits are preserved under before/. The previous [resume evaluation](../resume_evaluation/evaluation_summary.md), its negative results and original model were not overwritten. Corrected source files are copied under source_snapshot/; protocol/environment/model fingerprints are retained in development/frozen.json and final_test/environment.json. Existing user changes in the chatbot, server, README, database and app requirements were preserved. Predictor changes build on the existing edited file; no Git commit or push occurred. The live application's separate realtime workflow and model path were not deployed or clinically validated; incompatible legacy models fail with a clear retraining error rather than being silently adapted.

On a fresh checkout/copy with the frozen source and protocol (do not overwrite evidence):

```powershell
python -m pip install -r backend/optimization/requirements-evaluation.txt
$env:OMP_NUM_THREADS="1"
python -m pytest -q
python -m backend.optimization.validate_simulation --phase develop
python -m backend.optimization.validate_simulation --phase final
python -m backend.optimization.report_validation
```

Completed output directories deliberately cause the runner to stop. For a rerun, use a separate working copy containing the source and protocol but no development/final_test outputs. New methodological changes require a new version and fresh untouched final seeds; these final streams are now consumed. The compatibility scenario CLI delegates to this workflow. Old threshold/duration sweeps and historical report scripts must use their archived source if reproduced, because the feature and metric schemas have intentionally changed.

## Remaining limitations

No real-hospital calibration or deployment; no admitted ED-to-ward transfer/boarding, dynamic staffing/skill mix, ambulance diversion, abandonment, re-triage, preemption, inpatient discharge dynamics, geography/case-mix calibration or clinical outcome model. Static independent service draws and Poisson arrivals may understate real clustering/dependence. The five-day Monday–Friday experiment does not establish weekend, seasonal or steady-state performance. Initial assessment requires a bed by construction; real ED workflows may assess patients elsewhere. Disposition is an exogenous synthetic flag, not a modelled admission decision. The 13-feature model is evaluated on independent streams from the same generator, so good synthetic forecast scores do not establish external validity.

The deliverable is ready for a separately designed calibration stage with these gaps explicit; it is **not ready to claim agreement with Ontario CIHI/NACRS outcomes**.
'''
    (O/'technical_report.md').write_text(report,encoding='utf-8')
    print('Report generated; historical hashes, 450 saved runs and all paired differences verified.')

if __name__=='__main__': main()
