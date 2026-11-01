"""Focused portfolio experiment. Run from repository root; refuses to replace results."""
import os
os.environ['OMP_NUM_THREADS'] = '1'
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import json, hashlib, platform, importlib.metadata
from dataclasses import replace, asdict
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
from scipy.stats import norm, t
from backend.data.synthetic_generator import generate_events, _SERVICE_PARAMS, _probabilities_by_level, DOW_MULTIPLIERS
from backend.optimization.congestion_scenarios import get_scenario
from backend.simulation.queue_engine import QueueEngine
from backend.simulation.metrics import create_patients, calculate_kpis
from backend.optimization.validate_simulation import validate_run
from backend.ml.predictor import HighUrgencyPredictor

OUT = Path(__file__).resolve().parent
START = datetime(2026, 1, 5)
WARM, DAYS, GUARD = 7, 21, 7
A, B = START + timedelta(days=WARM), START + timedelta(days=WARM+DAYS)
END = B + timedelta(days=GUARD)
METHODS = ['FCFS', 'CTAS', 'Predictive']
MODEL = ROOT/'reports/simulation_validation/development/predictor.pkl'
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def ci(x):
    x=np.asarray(x,float); m=x.mean(); h=t.ppf(.975,len(x)-1)*x.std(ddof=1)/np.sqrt(len(x))
    return float(m), float(m-h), float(m+h)
def clamped_mean(mu,sigma,lo,hi):
    zlo=(np.log(lo)-mu)/sigma; zhi=(np.log(hi)-mu)/sigma
    return lo*norm.cdf(zlo)+np.exp(mu+sigma*sigma/2)*(norm.cdf(zhi-sigma)-norm.cdf(zlo-sigma))+hi*norm.sf(zhi)
def main():
    if (OUT/'results.csv').exists(): raise SystemExit('Refusing to overwrite existing results; use a separate copy for reproduction.')
    historical={str(p.relative_to(ROOT)):sha(p) for folder in ['resume_evaluation','simulation_validation'] for p in (ROOT/'reports'/folder).rglob('*') if p.is_file()}
    base=get_scenario('normal'); mix={k:v/sum(base.arrival_rates_per_hour.values()) for k,v in base.arrival_rates_per_hour.items()}
    means={k:clamped_mean(*v) for k,v in _SERVICE_PARAMS.items()}
    demand={pool:sum(mix[k]*means[k]*(_probabilities_by_level(k)['icu_need'] if pool=='ICU' else 1-_probabilities_by_level(k)['icu_need']) for k in mix) for pool in ['ED','ICU']}
    configs=[]; assumptions=[]
    for name,load in [('Normal',.775),('Moderate Congestion',.925)]:
        daily=load*50*1440/demand['ED']
        cfg=replace(base,name=name,arrival_rates_per_hour={k:daily/24/np.mean(DOW_MULTIPLIERS)*mix[k] for k in mix})
        configs.append(cfg)
        assumptions.append(dict(scenario=name,target_ed_load=load,expected_patients_day=daily,icu_offered_load=daily*demand['ICU']/(20*1440),configuration=asdict(cfg),physician_offered_load=daily*15/(8*1440),nurse_offered_load=daily*6.5/(22*1440),lab_offered_load=daily*sum(mix[k]*_probabilities_by_level(k)['lab'] for k in mix)/(24*22),imaging_offered_load=daily*sum(mix[k]*_probabilities_by_level(k)['imaging'] for k in mix)/(24*14)))
    protocol=dict(warmup_days=WARM,measurement_days=DAYS,guard_days=GUARD,start=str(START),measurement_start=str(A),measurement_end=str(B),seeds=list(range(910000,910010)),methods=METHODS,reservation_threshold=.8,reservation_minutes=30,assessment_minutes=15,ctas_mix=mix,clamped_service_means=means,bed_minutes_per_arrival=demand,scenarios=assumptions,model_path=str(MODEL.relative_to(ROOT)),model_sha256=sha(MODEL),python=platform.python_version(),packages={p:importlib.metadata.version(p) for p in ['numpy','pandas','scipy','scikit-learn','matplotlib','joblib']},source_sha256={str(p.relative_to(ROOT)):sha(p) for p in [Path(__file__),ROOT/'backend/data/synthetic_generator.py',ROOT/'backend/simulation/queue_engine.py',ROOT/'backend/simulation/metrics.py',ROOT/'backend/ml/predictor.py',ROOT/'backend/optimization/congestion_scenarios.py']})
    (OUT/'protocol.json').write_text(json.dumps(protocol,indent=2))
    predictor=HighUrgencyPredictor.load(MODEL)
    rows=[]
    for cfg in configs:
        for seed in protocol['seeds']:
            events=generate_events(WARM+DAYS+GUARD,cfg,seed,START.date())
            signature=hashlib.sha256(json.dumps([asdict(e) for e in events],sort_keys=True).encode()).hexdigest()
            measured=[e for e in events if A<=datetime.fromisoformat(e.arrival_ts)<B]
            counts=np.array([sum(A+timedelta(days=d)<=datetime.fromisoformat(e.arrival_ts)<A+timedelta(days=d+1) for e in measured) for d in range(DAYS)])
            for method in METHODS:
                patients=create_patients(events)
                engine=QueueEngine(50,20,policy=method,predictor=predictor,scenario=cfg,observation_start=START,observation_end=END,reservation_threshold=.8,reservation_timeout_minutes=30,assessment_minutes=15)
                engine.run(patients)
                full=calculate_kpis(patients,START,END,50,20,engine.metrics)
                validate_run(patients,events,cfg,full,START,END,engine)
                cohort=[p for p in patients if A<=p.arrival<B]
                waits=np.array([p.wait_minutes for p in cohort]); urgent=[p.wait_minutes for p in cohort if p.urgency<=2]
                def backlog(stamp): return sum(p.arrival<stamp<=p.service_start for p in patients)
                weekly=[backlog(A+timedelta(days=7*d)) for d in range(4)]
                def week_wait(k): return np.mean([p.wait_minutes for p in cohort if A+timedelta(days=7*k)<=p.arrival<A+timedelta(days=7*(k+1))])
                metrics=dict(avg_wait_minutes=waits.mean(),urgent_wait_minutes=np.mean(urgent),p90_wait_minutes=np.quantile(waits,.9),patients_arrived=len(cohort),patients_per_day=len(cohort)/DAYS,daily_arrivals_min=counts.min(),daily_arrivals_max=counts.max(),completed_in_window=sum(A<=p.discharge<B for p in patients),cohort_completed_by_end=sum(p.discharge<B for p in cohort),waiting_backlog_start=weekly[0],waiting_backlog_end=weekly[-1],waiting_backlog_week1=weekly[1],waiting_backlog_week2=weekly[2],weekly_backlog_slope=np.polyfit(np.arange(4),weekly,1)[0],last_minus_first_week_wait=week_wait(2)-week_wait(0),max_daily_waiting_backlog=max(backlog(A+timedelta(days=d)) for d in range(22)),in_service_end=sum(p.service_start<B<=p.discharge for p in patients),unfinished_end=sum(p.arrival<B<=p.discharge for p in patients),carry_in=sum(p.arrival<A<=p.discharge for p in patients),cohort_service_after_guard=sum(p.service_start>=END for p in cohort),max_service_extension_minutes=max((p.discharge-p.service_start).total_seconds()/60-p.los_minutes for p in patients))
                assert metrics['carry_in']+len(cohort)==metrics['completed_in_window']+metrics['unfinished_end']
                for pool,cap in [('ED',50),('ICU',20)]:
                    occupied=sum(max(0,(min(B,p.discharge)-max(A,p.service_start)).total_seconds()/60) for p in patients if p.bed_type==pool)
                    metrics[pool.lower()+'_utilization_pct']=100*occupied/(cap*DAYS*1440)
                    metrics[pool.lower()+'_realized_offered_load_pct']=100*sum(p.los_minutes for p in cohort if p.bed_type==pool)/(cap*DAYS*1440)
                for key,value in metrics.items(): rows.append(dict(record_type='seed',scenario=cfg.name,method=method,baseline='',seed=seed,metric=key,value=value,input_sha256=signature))
                print(cfg.name,seed,method,'mean wait',round(waits.mean(),2),'end waiting',weekly[-1],flush=True)
            pd.DataFrame(rows).to_csv(OUT/'seed_results.partial.csv',index=False)
    data=pd.DataFrame(rows); summaries=[]
    for (scenario,method,metric),g in data.groupby(['scenario','method','metric'],sort=False):
        m,lo,hi=ci(g.value); summaries.append(dict(record_type='summary',scenario=scenario,method=method,baseline='',metric=metric,value=m,ci95_low=lo,ci95_high=hi,n=10))
    for (scenario,metric),g in data.groupby(['scenario','metric'],sort=False):
        wide=g.pivot(index='seed',columns='method',values='value')
        for base,method in [('FCFS','CTAS'),('FCFS','Predictive'),('CTAS','Predictive')]:
            m,lo,hi=ci(wide[method]-wide[base]); bm=wide[base].mean()
            summaries.append(dict(record_type='paired_difference',scenario=scenario,method=method,baseline=base,metric=metric,value=m,ci95_low=lo,ci95_high=hi,n=10,baseline_mean=bm,method_mean=wide[method].mean(),relative_change_pct=100*m/bm if bm else np.nan))
    pd.concat([data,pd.DataFrame(summaries)],ignore_index=True).to_csv(OUT/'results.csv',index=False)
    assert all(sha(ROOT/p)==h for p,h in historical.items())
    (OUT/'validation.json').write_text(json.dumps(dict(runs=60,streams=20,independent_seeds=10,all_resource_and_timestamp_checks_passed=True,historical_files_unchanged=len(historical),no_parameter_tuning=True,complete=True),indent=2))
if __name__=='__main__': main()
