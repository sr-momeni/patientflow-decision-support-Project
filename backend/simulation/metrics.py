"""Timestamp-based KPIs. Bed service duration is never labelled ED length of stay."""
from datetime import datetime
import numpy as np
from .event_model import SimulationPatient


def create_patients(events):
    return [SimulationPatient(id=e.patient_id,arrival=datetime.fromisoformat(e.arrival_ts),
        urgency=e.urgency_level,los_minutes=e.service_minutes,bed_type=e.bed_assigned_type,
        triage_minutes=e.triage_minutes,lab_required=e.lab_required,
        imaging_required=e.imaging_required,disposition=e.admit_decision) for e in events]


def calculate_kpis(patients,start,end,ed_capacity,icu_capacity,reservation_metrics=None):
    if end<=start:
        raise ValueError('Invalid measurement window')
    if any(p.discharge is None or p.service_start is None for p in patients):
        raise ValueError('Incomplete cohort: never treat unserved patients as zero wait')
    def mean(values):
        return float(np.mean(values)) if len(values) else float('nan')
    def quantile(values,q):
        return float(np.quantile(values,q,method='linear')) if len(values) else float('nan')
    waits=[(p.service_start-p.arrival).total_seconds()/60 for p in patients]
    system=[(p.discharge-p.arrival).total_seconds()/60 for p in patients]
    result={'n_patients':len(patients),'avg_wait':mean(waits),'p50_wait':quantile(waits,.5),
            'p90_wait':quantile(waits,.9),'avg_system_time':mean(system),
            'p50_system_time':quantile(system,.5),'p90_system_time':quantile(system,.9),
            'departed_by_horizon':sum(p.discharge<=end for p in patients),
            'waiting_at_horizon':sum(p.service_start>=end for p in patients),
            'in_service_at_horizon':sum(p.service_start<end<p.discharge for p in patients),
            'drain_minutes':max([0.]+[(p.discharge-end).total_seconds()/60 for p in patients])}
    for level in range(1,6):
        subset=[w for p,w in zip(patients,waits) if p.urgency==level]
        result[f'n_l{level}']=len(subset)
        result[f'wait_l{level}']=mean(subset)
        result[f'p90_wait_l{level}']=quantile(subset,.9)
    for bed,cap in [('ED',ed_capacity),('ICU',icu_capacity)]:
        subset=[p for p in patients if p.bed_type==bed]
        occupied=sum(max(0.,(min(end,p.discharge)-max(start,p.service_start)).total_seconds()/60) for p in subset)
        result[bed.lower()+'_occupied_minutes']=occupied
        result[bed.lower()+'_occupancy']=occupied/(cap*(end-start).total_seconds()/60) if cap else float('nan')
    for name,predicate in [('ed_pool_discharged_high',lambda p:p.bed_type=='ED' and p.disposition=='discharge' and p.urgency<=3),
                           ('ed_pool_discharged_low',lambda p:p.bed_type=='ED' and p.disposition=='discharge' and p.urgency>=4),
                           ('admit_intent_system',lambda p:p.disposition=='admit')]:
        subset=[s for p,s in zip(patients,system) if predicate(p)]
        result[name+'_n']=len(subset)
        result[name+'_p50']=quantile(subset,.5)
        result[name+'_p90']=quantile(subset,.9)
    if reservation_metrics:
        result.update(reservation_metrics)
    total=result.get('total_reservations',0)
    result['reservation_success_rate']=result.get('successful_catches',0)/total if total else float('nan')
    return result
