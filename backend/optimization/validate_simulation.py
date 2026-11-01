"""Frozen development/final-test protocol for the corrected simulation.

python -m backend.optimization.validate_simulation --phase develop
python -m backend.optimization.validate_simulation --phase final
"""
import os
os.environ.setdefault('OMP_NUM_THREADS','1')
import argparse
from dataclasses import asdict
from datetime import date,datetime,timedelta
import hashlib
import json
from pathlib import Path
import platform
import importlib.metadata
import shutil
import time
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error,mean_squared_error,r2_score
from scipy.stats import t as student_t
from backend.data.synthetic_generator import generate_events,hourly_intensity
from backend.optimization.congestion_scenarios import list_scenarios
from backend.simulation.queue_engine import QueueEngine
from backend.simulation.metrics import create_patients,calculate_kpis
from backend.ml.predictor import HighUrgencyPredictor,FEATURE_NAMES,FEATURE_SCHEMA
from backend.ml.train_model import snapshot_dataset

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'reports/simulation_validation'
SOURCE=[*sorted((ROOT/'backend/simulation').glob('*.py')),
        *sorted((ROOT/'backend/ml').glob('*.py')),
        ROOT/'backend/data/synthetic_generator.py',ROOT/'backend/optimization/congestion_scenarios.py',
        Path(__file__).resolve()]

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def fingerprints(): return {str(p.relative_to(ROOT)):sha(p) for p in SOURCE}
def write_json(path,data): path.write_text(json.dumps(data,indent=2,default=str),encoding='utf-8')

def validate_run(patients,events,cfg,metrics,start,end,engine):
    """Independent timestamp and interval validation for every patient/run."""
    assert len(patients)==len(events)==metrics['n_patients']
    assert len({p.id for p in patients})==len(patients)
    original={e.patient_id:e for e in events}
    for p in patients:
        e=original[p.id]
        assert p.arrival==datetime.fromisoformat(e.arrival_ts)
        assert p.urgency==e.urgency_level and p.bed_type==e.bed_assigned_type
        assert p.los_minutes==e.service_minutes
        assert p.arrival<=p.triage_start<=p.triage_end<=p.service_start<=p.physician_end<=p.discharge
        assert np.isclose((p.discharge-p.service_start).total_seconds()/60,p.los_minutes) or (p.discharge-p.service_start).total_seconds()/60>=p.los_minutes-1e-7
        assert np.isclose(p.wait_minutes,(p.service_start-p.arrival).total_seconds()/60)
    intervals=[]
    for bed,cap in [('ED',cfg.ed_beds),('ICU',cfg.icu_beds)]:
        subset=[p for p in patients if p.bed_type==bed]
        intervals.append(([(p.service_start,p.discharge) for p in subset],cap,bed))
    intervals.extend([
        ([(p.triage_start,p.triage_end) for p in patients],cfg.nurses,'nurse'),
        ([(p.service_start,p.physician_end) for p in patients],cfg.physicians,'physician'),
        ([(p.lab_start,p.lab_end) for p in patients if p.lab_start],1,'lab'),
        ([(p.imaging_start,p.imaging_end) for p in patients if p.imaging_start],1,'imaging')])
    for pairs,cap,label in intervals:
        edges=sorted([(a,1) for a,b in pairs if b>a]+[(b,-1) for a,b in pairs if b>a])
        active=peak=0;occupied=0.;previous=start
        for stamp,delta in edges:
            occupied+=active*max(0,(min(stamp,end)-max(previous,start)).total_seconds()/60)
            active+=delta;peak=max(peak,active);previous=stamp
            assert 0<=active<=cap,(label,active,cap)
        assert active==0
        if label in ('ED','ICU'):
            assert np.isclose(occupied,metrics[label.lower()+'_occupied_minutes'])
    assert metrics['departed_by_horizon']+metrics['waiting_at_horizon']+metrics['in_service_at_horizon']==len(patients)
    for lvl in range(1,6):
        waits=[(p.service_start-p.arrival).total_seconds()/60 for p in patients if p.urgency==lvl]
        if waits: assert np.isclose(np.mean(waits),metrics[f'wait_l{lvl}'])
    assert np.isclose(sum(x['duration_minutes'] for x in engine.reservation_log),engine.metrics['reservation_duration_minutes'])
    assert engine.metrics['blocked_idle_bed_minutes']<=engine.metrics['reserved_idle_bed_minutes']+1e-6
    assert engine.metrics['reserved_idle_bed_minutes']<=engine.metrics['reservation_duration_minutes']+1e-6
    return {'patients_checked':len(patients),'resource_interval_checks':len(intervals),'passed':True}

def interval(values):
    v=np.asarray(values,dtype=float);v=v[np.isfinite(v)];n=len(v)
    mean=float(np.mean(v)) if n else np.nan
    sd=float(np.std(v,ddof=1)) if n>1 else np.nan
    half=float(student_t.ppf(.975,n-1)*sd/np.sqrt(n)) if n>1 else np.nan
    return dict(n=n,mean=mean,sd=sd,ci95_low=mean-half,ci95_high=mean+half)

def aggregate(folder):
    d=pd.read_csv(folder/'per_seed_results.csv')
    numeric=[c for c in d.select_dtypes(include='number') if c not in ('seed','runtime_seconds')]
    summary=[]; comparisons=[]
    rng=np.random.default_rng(918274)
    for scenario,g in d.groupby('scenario',sort=False):
        for method,h in g.groupby('method',sort=False):
            for metric in numeric:
                summary.append(dict(scenario=scenario,method=method,metric=metric,**interval(h[metric])))
        for base,method in [('FCFS','CTAS'),('FCFS','Predictive'),('CTAS','Predictive')]:
            a=g[g.method==base].set_index('seed');b=g[g.method==method].set_index('seed')
            assert set(a.index)==set(b.index)
            b=b.reindex(a.index)
            for metric in numeric:
                delta=b[metric]-a[metric]
                f=float(a[metric].mean());v=float(b[metric].mean())
                lower=metric in ['avg_wait','avg_system_time','p90_wait','p90_system_time',*[f'wait_l{i}' for i in range(1,6)]]
                improvement=(f-v)/f*100 if lower and f>0 else np.nan
                low=high=np.nan
                if lower and f>0:
                    ix=rng.integers(0,len(a),size=(5000,len(a)))
                    bm=a[metric].to_numpy()[ix].mean(axis=1)
                    am=b[metric].to_numpy()[ix].mean(axis=1)
                    valid=bm>0
                    low,high=np.quantile((bm[valid]-am[valid])/bm[valid]*100,[.025,.975])
                comparisons.append(dict(scenario=scenario,baseline=base,method=method,metric=metric,
                    baseline_mean=f,method_mean=v,**{f'delta_{key}':val for key,val in interval(delta).items()},
                    improvement_pct=improvement,improvement_ci95_low=low,improvement_ci95_high=high))
    pd.DataFrame(summary).to_csv(folder/'scenario_summary.csv',index=False)
    pd.DataFrame(comparisons).to_csv(folder/'paired_comparisons.csv',index=False)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['develop','final'],required=True)
    args=parser.parse_args();protocol=json.loads((OUT/'protocol.json').read_text())
    folder=OUT/('development' if args.phase=='develop' else 'final_test')
    if folder.exists(): raise SystemExit(f'Refusing to overwrite {folder}; retain this evidence and select a new version explicitly.')
    if args.phase=='final':
        frozen=json.loads((OUT/'development/frozen.json').read_text())
        if frozen['source_hashes']!=fingerprints() or frozen['protocol_sha256']!=sha(OUT/'protocol.json'):
            raise SystemExit('Code/protocol differs from validation. Revalidate in a new version before accessing final test.')
        if frozen['model_sha256']!=sha(OUT/'development/predictor.pkl'):
            raise SystemExit('Model changed after validation')
    folder.mkdir();(folder/'raw').mkdir();(folder/'inputs').mkdir()
    start=datetime.fromisoformat(protocol['start_date']);end=start+timedelta(days=protocol['days'])
    write_json(folder/'environment.json',{'python':platform.python_version(),'packages':{x:importlib.metadata.version(x) for x in ['numpy','pandas','scikit-learn','scipy','joblib','pytest']},'schema':FEATURE_SCHEMA,'source_hashes':fingerprints(),'protocol_sha256':sha(OUT/'protocol.json')})
    rows=[];forecast_rows=[];audits=[];generator_rows=[];training_frames=[]
    def simulate(scenario,index,seed,methods,predictor,split):
        events=generate_events(protocol['days'],scenario,seed,start.date())
        input_df=pd.DataFrame([asdict(e) for e in events])
        identifier=f'{split}_{scenario.name}_{seed}'
        input_path=folder/'inputs'/f'{identifier}.csv.gz'
        input_df.to_csv(input_path,index=False,compression={'method':'gzip','mtime':0})
        input_hash=sha(input_path)
        for level in range(1,6):
            expected=sum(hourly_intensity(scenario,(start+timedelta(days=i)).date(),hour,level) for i in range(protocol['days']) for hour in range(24))
            generator_rows.append(dict(split=split,scenario=scenario.name,seed=seed,ctas=level,observed=sum(e.urgency_level==level for e in events),expected=expected))
        features=None
        for method in methods:
            began=time.perf_counter()
            patients=create_patients(events)
            engine=QueueEngine(scenario.ed_beds,scenario.icu_beds,policy=method,predictor=predictor,
                scenario=scenario,observation_start=start,observation_end=end,capture_snapshots=(method=='CTAS'),
                reservation_threshold=protocol['threshold'],reservation_timeout_minutes=protocol['reservation_minutes'],
                assessment_minutes=protocol['physician_initial_assessment_minutes'])
            engine.run(patients)
            result=calculate_kpis(patients,start,end,scenario.ed_beds,scenario.icu_beds,engine.metrics)
            audit=validate_run(patients,events,scenario,result,start,end,engine)
            audits.append(dict(split=split,scenario=scenario.name,seed=seed,method=method,**audit))
            if split!='train':
                pd.DataFrame([asdict(p) for p in patients]).to_csv(folder/'raw'/f'{identifier}_{method}.csv.gz',index=False,compression={'method':'gzip','mtime':0})
                if method=='Predictive':
                    pd.DataFrame(engine.reservation_log).to_csv(folder/'raw'/f'{identifier}_reservations.csv.gz',index=False,compression={'method':'gzip','mtime':0})
                rows.append(dict(split=split,scenario=scenario.name,seed=seed,method=method,input_sha256=input_hash,runtime_seconds=time.perf_counter()-began,**result))
            if method=='CTAS':
                X,y,persistence,times=snapshot_dataset(engine.snapshots,events,end,observation_start=start)
                features=pd.DataFrame(X,columns=FEATURE_NAMES)
                features['target_count']=y;features['persistence']=persistence;features['time']=times
                features['scenario']=scenario.name;features['seed']=seed;features['split']=split
            print(split,scenario.name,seed,method,'n=',len(events),'wait=',round(result['avg_wait'],3),flush=True)
        return features
    try:
        if args.phase=='develop':
            for i,(name,cfg) in enumerate(list_scenarios().items()):
                for j in range(protocol['train_seeds_per_scenario']):
                    seed=protocol['train_seed_base']+i*protocol['scenario_seed_offset']+j
                    training_frames.append(simulate(cfg,i,seed,['CTAS'],None,'train'))
            train=pd.concat(training_frames,ignore_index=True)
            train.to_csv(folder/'training_features.csv.gz',index=False,compression={'method':'gzip','mtime':0})
            predictor=HighUrgencyPredictor();predictor.train(train[list(FEATURE_NAMES)].to_numpy(),train.target_count.to_numpy())
            predictor.save(folder/'predictor.pkl')
            baseline_mean=float(train.target_count.mean())
            write_json(folder/'baseline.json',{'training_mean':baseline_mean})
        else:
            predictor=HighUrgencyPredictor.load(OUT/'development/predictor.pkl')
            baseline_mean=json.loads((OUT/'development/baseline.json').read_text())['training_mean']
        split='validation' if args.phase=='develop' else 'final'
        for i,(name,cfg) in enumerate(list_scenarios().items()):
            for j in range(protocol[f'{split}_seeds_per_scenario']):
                seed=protocol[f'{split}_seed_base']+i*protocol['scenario_seed_offset']+j
                f=simulate(cfg,i,seed,protocol['methods'],predictor,split)
                X=f[list(FEATURE_NAMES)].to_numpy();y=f.target_count.to_numpy()
                predictions={'model':np.maximum(0,predictor.model.predict(X)),
                             'training_mean':np.full(len(y),baseline_mean),'persistence_60m':f.persistence.to_numpy()}
                for label,pred in predictions.items():
                    f['prediction_'+label]=pred
                    forecast_rows.append(dict(split=split,scenario=name,seed=seed,predictor=label,n=len(y),
                        mae=mean_absolute_error(y,pred),rmse=np.sqrt(mean_squared_error(y,pred)),r2=r2_score(y,pred),bias=float(np.mean(pred-y))))
                f.to_csv(folder/'raw'/f'{split}_{name}_{seed}_forecast.csv.gz',index=False,compression={'method':'gzip','mtime':0})
                pd.DataFrame(rows).to_csv(folder/'per_seed_results.csv',index=False)
                pd.DataFrame(forecast_rows).to_csv(folder/'forecast_results.csv',index=False)
            print('Completed scenario',name,flush=True)
        aggregate(folder)
        if args.phase=='develop':
            write_json(folder/'frozen.json',{'source_hashes':fingerprints(),'protocol_sha256':sha(OUT/'protocol.json'),'model_sha256':sha(folder/'predictor.pkl'),'validation_runs':len(rows),'training_runs':len(training_frames),'parameters_tuned':False})
        write_json(folder/'completion.json',{'successful_comparison_runs':len(rows),'training_runs':len(training_frames),'patient_outputs':sum(r['n_patients'] for r in rows),'independent_scenario_streams':len(rows)//3,'complete':True})
    except Exception:
        import traceback
        (folder/'FAILURE.txt').write_text(traceback.format_exc())
        raise
    finally:
        pd.DataFrame(audits).to_csv(folder/'validation_checks.csv',index=False)
        pd.DataFrame(generator_rows).to_csv(folder/'generator_checks.csv',index=False)

if __name__=='__main__': main()
