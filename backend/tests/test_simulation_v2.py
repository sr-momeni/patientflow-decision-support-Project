from dataclasses import replace,asdict
from datetime import date,datetime,timedelta
import random
import numpy as np
import pytest
from backend.data.synthetic_generator import generate_events,hourly_intensity,generate_patients
from backend.optimization.congestion_scenarios import get_scenario,list_scenarios
from backend.simulation.event_model import SimulationPatient
from backend.simulation.queue_engine import QueueEngine
from backend.simulation.metrics import calculate_kpis,create_patients
from backend.ml.predictor import HighUrgencyPredictor,FEATURE_NAMES
from backend.ml.train_model import snapshot_dataset

T=datetime(2026,1,5)
class Constant:
    def __init__(self,value): self.value=value
    def predict(self,*args): return self.value

def patient(name,t=0,urgency=3,service=60,bed='ED',**kwargs):
    return SimulationPatient(name,T+timedelta(minutes=t),urgency,service,bed,**kwargs)

def engine(policy='FCFS',**kwargs):
    return QueueEngine(1,0,policy=policy,observation_start=T,
                       observation_end=T+timedelta(minutes=120),**kwargs)

@pytest.mark.parametrize('name',list(list_scenarios()))
def test_scenario_rates_and_ctas_distribution(name):
    cfg=get_scenario(name)
    events=generate_events(14,cfg,seed=987,start_date=T.date())
    counts={k:sum(e.urgency_level==k for e in events) for k in range(1,6)}
    for level in range(1,6):
        expected=sum(hourly_intensity(cfg,T.date()+timedelta(days=d),h,level) for d in range(14) for h in range(24))
        assert abs(counts[level]-expected) < 6*np.sqrt(expected)
    # No generator-fabricated waiting, assessment or departure times.
    assert all(e.assessment_start_ts=='' and e.discharge_ts=='' for e in events)

def test_generator_reproducible_local_rng_and_capacity_independent_inputs():
    cfg=get_scenario('normal')
    random.seed(123);before=random.getstate()
    a=generate_events(1,cfg,123);b=generate_events(1,cfg,123)
    assert a==b and random.getstate()==before
    assert a==generate_events(1,replace(cfg,ed_beds=1,icu_beds=1,nurses=1,physicians=1),123)
    burst=generate_events(1,get_scenario('critical_burst'),123)
    assert len(burst)>len(a) and sum(x.urgency_level<=2 for x in burst)>sum(x.urgency_level<=2 for x in a)

def test_zero_rates_and_fixed_count():
    cfg=replace(get_scenario('normal'),arrival_rates_per_hour={k:0 for k in range(1,6)})
    assert generate_events(2,cfg)==[]
    assert len(generate_patients(17,get_scenario('normal')))==17
    with pytest.raises(ValueError): generate_patients(1,cfg)

def test_fcfs_vs_ctas_and_disabled_predictive():
    def inputs(): return [patient('busy',0,3,60),patient('low',1,5,30),patient('high',2,1,30)]
    f,c,p=inputs(),inputs(),inputs()
    engine().run(f);engine('CTAS').run(c);engine('Predictive',predictor=Constant(0)).run(p)
    assert f[1].service_start < f[2].service_start
    assert c[2].service_start < c[1].service_start
    assert [asdict(x) for x in c]==[asdict(x) for x in p]

def test_ties_deterministic_nonpreemptive():
    def inputs(): return [patient('busy',0,5,60),patient('b',1,2,30),patient('a',1,2,30)]
    a,b=inputs(),inputs();engine('CTAS').run(a);engine('CTAS').run(b)
    assert a==b and a[0].discharge==T+timedelta(minutes=60)
    assert a[1].service_start<a[2].service_start

def test_expiry_releases_waiter_exactly_without_future_arrivals():
    p=[patient('low',0,5,60)]
    e=engine('Predictive',predictor=Constant(10),reservation_timeout_minutes=30)
    e.run(p)
    assert p[0].service_start==T+timedelta(minutes=30)
    assert e.reservation_log[0]['reason']=='expired'
    assert e.reservation_log[0]['duration_minutes']==30
    assert e.metrics['blocked_idle_bed_minutes']>=30
    assert e.metrics['reserved_idle_bed_minutes']<=e.metrics['reservation_duration_minutes']+1e-8

def test_future_ctas2_counts_as_success_and_horizon_accounts_all():
    p=[patient('high',10,2,60)]
    e=engine('Predictive',predictor=Constant(10));e.run(p)
    assert e.metrics['successful_catches']==1
    assert e.reservation_log[0]['duration_minutes']==10
    assert e.metrics['total_reservations']==sum(e.metrics[k] for k in ['successful_catches','expired_reservations','cancelled_reservations'])

def test_full_beds_are_not_reserved_or_counted_idle():
    p=[patient('high',0,1,120),patient('low',1,5,30)]
    e=engine('Predictive',predictor=Constant(10));e.run(p)
    # Initial hold is immediately consumed by simultaneous eligible arrival; no fake idle.
    assert e.metrics['reserved_idle_bed_minutes']==0
    assert p[1].service_start==T+timedelta(minutes=120)

def test_low_patient_does_not_consume_hold_with_other_beds_free():
    e=QueueEngine(2,0,policy='Predictive',predictor=Constant(10),observation_start=T,observation_end=T+timedelta(minutes=40))
    p=[patient('low',0,5,60),patient('high',10,1,60)]
    e.run(p)
    assert p[0].wait_minutes==0 and p[1].wait_minutes==0
    assert e.metrics['successful_catches']==1

def test_physician_nurse_and_diagnostic_resources():
    cfg=replace(get_scenario('normal'),ed_beds=5,icu_beds=0,physicians=1,nurses=1,lab_slots_per_hour=1,imaging_slots_per_hour=1)
    p=[patient(str(i),0,3,20,triage_minutes=5,lab_required=True,imaging_required=True) for i in range(3)]
    e=QueueEngine(5,0,scenario=cfg);e.run(p)
    assert [x.triage_start for x in p]==[T+timedelta(minutes=x) for x in (0,5,10)]
    assert [x.service_start for x in p]==[T+timedelta(minutes=x) for x in (5,20,35)]
    for a,b in zip(p,p[1:]):
        assert a.lab_end<=b.lab_start and a.imaging_end<=b.imaging_start
    assert all(x.discharge>=x.imaging_end for x in p)

def test_kpis_clipped_occupancy_missing_strata_and_conservation():
    p=[patient('a',0,3,60),patient('b',10,3,60)]
    engine().run(p)
    k=calculate_kpis(p,T,T+timedelta(minutes=90),1,0)
    assert k['avg_wait']==25 and k['avg_system_time']==85
    assert k['ed_occupancy']==1 and np.isnan(k['icu_occupancy'])
    assert k['departed_by_horizon']==1 and k['in_service_at_horizon']==1
    assert np.isnan(k['wait_l1']) and np.isnan(k['reservation_success_rate'])
    assert k['p90_wait']==45
    with pytest.raises(ValueError): calculate_kpis([patient('unserved')],T,T+timedelta(hours=1),1,0)

def test_shared_feature_contract_save_load_and_training_validation(tmp_path):
    model=HighUrgencyPredictor()
    x=model._extract_features(T,.5,.25,{'15m':1,'30m':2,'1h':3,'4h':4},{1:5,2:6,3:7})
    assert x.shape==(1,13) and tuple(x[0,4:])==(.5,.25,1,2,3,4,5,6,7)
    X=np.repeat(x,40,axis=0);y=np.arange(40)%3
    model.train(X,y,validation=(X[:5],y[:5]))
    path=tmp_path/'model.pkl';model.save(path)
    loaded=HighUrgencyPredictor.load(path)
    assert loaded.model.predict(x)==model.model.predict(x)
    with pytest.raises(ValueError): model.train(X[:,:4],y)

def test_snapshot_targets_exclude_current_future_features_and_censored_windows():
    cfg=replace(get_scenario('normal'),arrival_rates_per_hour={1:1,2:0,3:0,4:0,5:0})
    events=generate_events(1,cfg,9)
    p=create_patients(events)
    e=QueueEngine(cfg.ed_beds,cfg.icu_beds,policy='CTAS',scenario=cfg,
                  observation_start=T,observation_end=T+timedelta(days=1),capture_snapshots=True)
    e.run(p)
    X,y,b,times=snapshot_dataset(e.snapshots,events,T+timedelta(days=1),observation_start=T)
    assert X.shape[1]==len(FEATURE_NAMES) and len(y)==77
    for row,target in zip(times,y):
        t=datetime.fromisoformat(row)
        assert target==sum(t<=datetime.fromisoformat(x.arrival_ts)<t+timedelta(minutes=60) for x in events)
    assert e.snapshots[0]['features'][6:10]==[0,0,0,0]

def test_invalid_zero_icu_fails_instead_of_rerouting():
    with pytest.raises(ValueError): engine().run([patient('icu',bed='ICU')])

def test_future_arrivals_cannot_change_earlier_features():
    def collect(extra):
        p=[patient('early',0,3,60),*extra]
        e=QueueEngine(2,0,policy='CTAS',observation_start=T,observation_end=T+timedelta(minutes=120),capture_snapshots=True)
        e.run(p)
        return [r for r in e.snapshots if r['time']<T+timedelta(minutes=60)]
    assert collect([])==collect([patient('future',60,1,30)])

def test_expiry_tie_does_not_rehold_before_queue_can_progress():
    p=[patient('low',0,5,60),patient('high',30,1,30)]
    e=engine('Predictive',predictor=Constant(10));e.run(p)
    assert e.reservation_log[0]['reason']=='expired'
    assert p[1].service_start==T+timedelta(minutes=30)
    assert e.metrics['successful_catches']==0

def test_legacy_model_metadata_rejected(tmp_path):
    import joblib
    p=tmp_path/'legacy.pkl'
    joblib.dump({'model':None,'prediction_window':60,'is_trained':True},p)
    with pytest.raises(ValueError,match='Legacy/incompatible'):
        HighUrgencyPredictor.load(p)

def test_peak_shape_normalized_and_weekday_volume_explicit():
    cfg=get_scenario('normal')
    stronger=replace(cfg,peak_hour_multiplier=2)
    for level in range(1,6):
        assert np.isclose(sum(hourly_intensity(cfg,date(2026,1,5),h,level) for h in range(24)),24*cfg.arrival_rate(level))
        assert np.isclose(sum(hourly_intensity(stronger,date(2026,1,5),h,level) for h in range(24)),24*cfg.arrival_rate(level))
        assert hourly_intensity(stronger,date(2026,1,5),12,level)>hourly_intensity(cfg,date(2026,1,5),12,level)
        assert np.isclose(hourly_intensity(cfg,date(2026,1,6),12,level),.9*hourly_intensity(cfg,date(2026,1,5),12,level))
