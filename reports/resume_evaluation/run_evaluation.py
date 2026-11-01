"""Reproduce the existing scenario evaluator with isolated artifacts and raw evidence.
Run from repository root: python reports/resume_evaluation/run_evaluation.py
"""
import os
os.environ.setdefault('OMP_NUM_THREADS', '1')
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import json, hashlib, shutil, platform, importlib.metadata, traceback
from datetime import date, datetime, timedelta
from dataclasses import asdict
from unittest.mock import patch
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from backend.optimization import evaluate_agent as ev
from backend.ml.train_model import prepare_training_data
from backend.data.synthetic_generator import generate_events, save_events_to_csv

OUT = Path(__file__).resolve().parent
RUN = OUT / 'artifacts'
if RUN.exists():
    backup = OUT / ('backup_' + datetime.now().strftime('%Y%m%d_%H%M%S'))
    shutil.copytree(RUN, backup / 'artifacts')
    for old in OUT.glob('*.csv'):
        shutil.copy2(old, backup / old.name)
RUN.mkdir(exist_ok=True)
(RUN / 'data').mkdir(exist_ok=True)
(RUN / 'raw').mkdir(exist_ok=True)
def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

meta = {'python': platform.python_version(), 'packages': {n: importlib.metadata.version(n) for n in
        ['numpy','pandas','scikit-learn','joblib','matplotlib','seaborn','python-dateutil','pytest']},
        'evaluation_start': '2026-10-26', 'days': 5, 'seeds': [42,43,44],
        'initial_failures': ['Original CLI: NameError: Tuple not imported',
        'Saved model smoke test: 13 expected features versus 4 supplied; sklearn 1.8.0 artifact loaded under 1.7.2'],
        'source_sha256': {str(p.relative_to(ROOT)): digest(p) for p in
            [ROOT/'backend'/s for s in ['optimization/evaluate_agent.py','optimization/congestion_scenarios.py',
             'simulation/engine.py','simulation/predictive_engine.py','data/synthetic_generator.py',
             'ml/predictor.py','ml/train_model.py']]},
        'original_model_sha256': digest(ROOT/'models/urgency_predictor.pkl')}
for source in meta['source_sha256']:
    target = RUN / 'source_snapshot' / source
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / source, target)

# Independent synthetic streams; no evaluation data used for training or selection.
cfg = ev.list_scenarios()['normal']
datasets = {}
for label, days, seed, start in [('train',30,202601,date(2026,1,5)),('validation',7,202602,date(2026,3,2))]:
    events = generate_events(days,cfg,seed,start)
    path = RUN / (label + '.csv')
    save_events_to_csv(events,path)
    X,y = prepare_training_data(path)
    # Existing trainer emits 13 columns; current inference uses its first four.
    X = X[:,:4]
    times = pd.to_datetime([e.arrival_ts for e in events])
    end = datetime.combine(start + timedelta(days=days),datetime.min.time())
    mask = times <= end - timedelta(minutes=60)
    datasets[label] = (X[mask], y[mask])
    meta[label] = {'days':days,'seed':seed,'start':str(start),'patients':len(events),
                   'samples':int(mask.sum()),'sha256':digest(path)}
p = ev.HighUrgencyPredictor()
p.model.fit(*datasets['train'])
p.is_trained = True
p.save(RUN/'evaluation_predictor.pkl')
yhat = p.model.predict(datasets['validation'][0])
y = datasets['validation'][1]
meta['validation_metrics'] = {'mae':mean_absolute_error(y,yhat),'mse':mean_squared_error(y,yhat),'r2':r2_score(y,yhat)}
meta['evaluation_model_sha256'] = digest(RUN/'evaluation_predictor.pkl')
print('Training complete',meta['train'],meta['validation_metrics'],flush=True)

rows=[]
context={}
original_metrics=ev.calculate_metrics
def generate_fixed(days,scenario,seed):
    context.update(scenario=scenario.name,seed=seed)
    events=generate_events(days,scenario,seed,date(2026,10,26))
    path=RUN/'raw'/f'{scenario.name}_{seed}_input.csv'
    save_events_to_csv(events,path)
    context['input_sha256']=digest(path)
    return events

def capture(patients,cfg,days,metrics_dict=None):
    result=original_metrics(patients,cfg,days,metrics_dict)
    model='Agent' if metrics_dict is not None else 'FCFS'
    raw=pd.DataFrame([asdict(x) for x in patients])
    raw.to_csv(RUN/'raw'/f'{cfg.name}_{context["seed"]}_{model}.csv',index=False)
    complete=all(x.service_start is not None and x.discharge is not None for x in patients)
    row={**context,'Model':model,'n_patients':len(patients),'completed_patients':sum(x.discharge is not None for x in patients),
         'status':'success' if complete else 'incomplete',**result,**(metrics_dict or {})}
    for key in ['total_reservations','expired_reservations','successful_catches','wasted_bed_minutes']:
        row.setdefault(key,0)
    row['reservation_success_rate']=row['successful_catches']/row['total_reservations'] if row['total_reservations'] else np.nan
    start=datetime(2026,10,26); end=start+timedelta(days=days)
    for bed,capacity in [('ED',cfg.ed_beds),('ICU',cfg.icu_beds)]:
        ps=[x for x in patients if x.bed_type==bed and x.discharge is not None]
        minutes=sum(max(0,(min(x.discharge,end)-max(x.service_start,start)).total_seconds()/60) for x in ps)
        row[bed.lower()+'_time_occupancy']=minutes/(days*1440*capacity)
        edges=sorted([(x.service_start,1) for x in ps]+[(x.discharge,-1) for x in ps])
        active=peak=0
        for _,delta in edges:
            active+=delta; peak=max(peak,active)
        assert peak<=capacity
        row[bed.lower()+'_peak_occupied']=peak
    for level in range(1,6): row[f'n_l{level}']=sum(x.urgency==level for x in patients)
    assert complete, 'Simulation left unserved patients'
    assert all(x.wait_minutes>=0 for x in patients)
    assert np.isclose(result['avg_wait'],raw.wait_minutes.mean())
    assert np.isclose(result['avg_los'],(raw.wait_minutes+raw.los_minutes).mean())
    rows.append(row)
    pd.DataFrame(rows).to_csv(OUT/'per_seed_results.csv',index=False)
    if model=='Agent': shutil.copy2(RUN/'data/simulation_events.log',RUN/'raw'/f'{cfg.name}_{context["seed"]}_events.log')
    print(cfg.name,context['seed'],model,len(patients),result['avg_wait'],flush=True)
    return result

os.chdir(RUN) # Existing evaluator's data/ writes stay isolated; originals untouched.
try:
    with patch.object(ev,'generate_events',generate_fixed),patch.object(ev,'calculate_metrics',capture),patch.object(ev.HighUrgencyPredictor,'load',return_value=p):
        ev.run_scenarios(days=5,seeds=[42,43,44])
except Exception:
    meta['execution_error']=traceback.format_exc()
    raise
finally:
    meta['successful_runs']=sum(r['status']=='success' for r in rows)
    (RUN/'manifest.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')

df=pd.DataFrame(rows)
metrics=['n_patients','avg_wait','wait_l1','wait_l2','avg_los','ed_occ','icu_occ','ed_time_occupancy','icu_time_occupancy',
         'total_reservations','successful_catches','expired_reservations','reservation_success_rate','wasted_bed_minutes']
agg=df.groupby(['scenario','Model'],sort=False)[metrics].agg(['mean','std','min','max'])
agg.columns=['_'.join(c) for c in agg.columns]
agg.reset_index().to_csv(OUT/'evaluation_results.csv',index=False)
comparisons=[]
for scenario,group in df.groupby('scenario',sort=False):
    for metric in metrics:
        f=group[group.Model=='FCFS'].set_index('seed')[metric]
        a=group[group.Model=='Agent'].set_index('seed')[metric]
        lower=metric in ['avg_wait','wait_l1','wait_l2','avg_los','wasted_bed_minutes']
        comparisons.append({'scenario':scenario,'metric':metric,'fcfs_mean':f.mean(),'agent_mean':a.mean(),
          'fcfs_sd':f.std(),'agent_sd':a.std(),'agent_minus_fcfs':(a-f).mean(),'paired_delta_sd':(a-f).std(),
          'improvement_pct':(f.mean()-a.mean())/f.mean()*100 if lower and f.mean()!=0 else np.nan,
          'paired_improvement_mean_pct':((f-a)/f.replace(0,np.nan)*100).mean() if lower else np.nan})
pd.DataFrame(comparisons).to_csv(OUT/'kpi_comparison.csv',index=False)
print('COMPLETE',meta['successful_runs'],flush=True)
