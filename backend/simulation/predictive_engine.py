"""Strict CTAS priority and predictive reservation entry points."""
from .queue_engine import QueueEngine

class PriorityEngine(QueueEngine):
    def __init__(self, ed_capacity, icu_capacity, **kwargs):
        super().__init__(ed_capacity, icu_capacity, policy='CTAS', **kwargs)

class PredictiveEngine(QueueEngine):
    def __init__(self, ed_capacity, icu_capacity, predictor,
                 reservation_threshold=.8, reservation_timeout_minutes=30, **kwargs):
        super().__init__(ed_capacity, icu_capacity, policy='Predictive', predictor=predictor,
            reservation_threshold=reservation_threshold,
            reservation_timeout_minutes=reservation_timeout_minutes, **kwargs)

def summarize_simulation_metrics(patients, ed_capacity, icu_capacity):
    from .metrics import calculate_kpis
    if not patients:
        return dict(average_waiting_time=0.,average_los=0.,ed_bed_utilization=0.,icu_bed_utilization=0.)
    result=calculate_kpis(patients,min(p.arrival for p in patients),
        max(p.discharge for p in patients),ed_capacity,icu_capacity)
    return dict(average_waiting_time=result['avg_wait'], average_los=result['avg_system_time'],
        ed_bed_utilization=result['ed_occupancy'],icu_bed_utilization=result['icu_occupancy'])
