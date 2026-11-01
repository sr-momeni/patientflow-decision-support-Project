"""Shared causal feature contract and complete-window forecasting labels.

Training rows are simulator snapshots at fixed 15-minute decision times.
Never use fabricated assessment/departure timestamps from generated inputs.
"""
import numpy as np
from backend.ml.predictor import FEATURE_NAMES


def snapshot_dataset(snapshots,events,observation_end,window_minutes=60,burn_in_minutes=240,observation_start=None):
    arrivals=np.array([np.datetime64(e.arrival_ts,'us') for e in events if e.urgency_level<=2])
    arrivals.sort()
    X=[]; y=[]; baseline=[]; times=[]
    for row in snapshots:
        t=np.datetime64(row['time'],'us')
        finish=t+np.timedelta64(window_minutes,'m')
        if finish>np.datetime64(observation_end,'us'):
            continue
        if observation_start is not None and t<np.datetime64(observation_start,'us')+np.timedelta64(burn_in_minutes,'m'):
            continue
        X.append(row['features'])
        y.append(int(np.searchsorted(arrivals,finish,side='left')-np.searchsorted(arrivals,t,side='left')))
        baseline.append(row['past_high_60m'])
        times.append(str(t))
    return np.asarray(X,dtype=float).reshape(-1,len(FEATURE_NAMES)),np.asarray(y),np.asarray(baseline),times


def prepare_training_data(csv_path,prediction_window_minutes=60):
    """Read explicit feature/target exports, rejecting ambiguous legacy patient CSVs."""
    import pandas as pd
    frame=pd.read_csv(csv_path)
    required=[*FEATURE_NAMES,'target_count']
    if not set(required)<=set(frame.columns):
        raise ValueError('Use causal snapshot features exported by backend.optimization.validate_simulation; legacy patient CSV training is not supported')
    return frame[list(FEATURE_NAMES)].to_numpy(),frame.target_count.to_numpy()


def main():
    raise SystemExit('Run python -m backend.optimization.validate_simulation --phase develop to train and validate without overwriting legacy models.')

if __name__=='__main__':
    main()
