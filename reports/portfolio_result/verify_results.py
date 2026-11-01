"""Independent saved-result checks and daily counts; does not rerun simulations."""
from pathlib import Path
import sys,json,hashlib
from datetime import datetime
from dataclasses import asdict
P=Path(__file__).resolve().parent; ROOT=P.parents[1]; sys.path.insert(0,str(ROOT))
import numpy as np
import pandas as pd
from scipy.integrate import quad
from scipy.stats import lognorm,t
from backend.data.synthetic_generator import generate_events,_SERVICE_PARAMS
from backend.optimization.congestion_scenarios import ScenarioConfig
p=json.loads((P/'protocol.json').read_text()); d=pd.read_csv(P/'results.csv'); seeds=d[d.record_type=='seed']; daily=[]
assert seeds.groupby(['scenario','seed']).input_sha256.nunique().eq(1).all()
assert seeds.groupby(['scenario','seed']).method.nunique().eq(3).all()
for key,expected in p['clamped_service_means'].items():
    mu,sigma,lo,hi=_SERVICE_PARAMS[int(key)]
    independent=lo+quad(lambda x:lognorm.sf(x,sigma,scale=np.exp(mu)),lo,hi)[0]
    assert np.isclose(independent,expected,rtol=1e-10)
for _,r in d[d.record_type=='paired_difference'].iterrows():
    w=seeds[(seeds.scenario==r.scenario)&(seeds.metric==r.metric)].pivot(index='seed',columns='method',values='value')
    v=w[r.method]-w[r.baseline]; interval=t.interval(.95,9,loc=v.mean(),scale=v.std(ddof=1)/np.sqrt(10)) if v.std(ddof=1)>0 else (v.mean(),v.mean())
    assert np.allclose([r.value,r.ci95_low,r.ci95_high],[v.mean(),*interval],atol=1e-9)
for a in p['scenarios']:
    cfg=a['configuration']; cfg['arrival_rates_per_hour']={int(k):v for k,v in cfg['arrival_rates_per_hour'].items()}; cfg=ScenarioConfig(**cfg)
    for seed in p['seeds']:
        events=generate_events(35,cfg,seed,datetime.fromisoformat(p['start']).date())
        h=hashlib.sha256(json.dumps([asdict(e) for e in events],sort_keys=True).encode()).hexdigest()
        assert set(seeds[(seeds.scenario==cfg.name)&(seeds.seed==seed)].input_sha256)=={h}
        dates=pd.to_datetime([e.arrival_ts for e in events],format='ISO8601'); counts=pd.Series(dates.date).value_counts()
        for stamp in pd.date_range(p['measurement_start'],periods=21):
            daily.append(dict(scenario=cfg.name,seed=seed,date=str(stamp.date()),patients=int(counts.get(stamp.date(),0))))
counts=pd.DataFrame(daily)
for (s,seed),g in counts.groupby(['scenario','seed']):
    expected=seeds[(seeds.scenario==s)&(seeds.seed==seed)&(seeds.method=='FCFS')&(seeds.metric=='patients_arrived')].value.iloc[0]
    assert g.patients.sum()==expected
counts.to_csv(P/'daily_arrivals.csv',index=False)
print('Verified: 20 regenerated stream hashes, 420 daily counts, exact clamped means by numerical integration, all paired estimates and intervals.')
