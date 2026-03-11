"""Predictive simulation engine with AI-based bed reservation and Priority Queuing."""

import heapq
from typing import List, Dict, Tuple
from datetime import timedelta
import os
from backend.simulation.event_model import SimulationPatient, HospitalState
from backend.ml.predictor import HighUrgencyPredictor

class PredictiveEngine:
    """Simulation engine with priority queuing and predictive bed reservation."""
    
    def __init__(self, ed_capacity: int, icu_capacity: int, 
                 predictor: HighUrgencyPredictor, 
                 reservation_threshold: float = 0.8,
                 reservation_timeout_minutes: int = 30):
        self.state = HospitalState(ed_capacity=ed_capacity, icu_capacity=icu_capacity)
        self.predictor = predictor
        
        # We reserve beds if expected count > threshold
        self.reservation_threshold = reservation_threshold
        self.reservation_timeout_minutes = reservation_timeout_minutes
        
        self.ed_reserved_count = 0
        self.icu_reserved_count = 0
        self.ed_reservation_expiry = None
        self.icu_reservation_expiry = None
        
        self.ed_reservation_start = None
        self.icu_reservation_start = None
        
        self.metrics = {
            "total_reservations": 0,
            "expired_reservations": 0,
            "successful_catches": 0,
            "wasted_bed_minutes": 0.0
        }
        
        self.log_path = "data/simulation_events.log"
        os.makedirs("data", exist_ok=True)
        with open(self.log_path, "w") as f:
            f.write("timestamp,event,patient_id,urgency,bed_type,wait_time,reservation_status\n")
            
        # For feature extraction
        self.past_arrivals = [] # list of datetimes
        self.active_patients = [] # list of SimulationPatients currently in beds
            
    def _log(self, ts, event, p_id="", urgency="", bed_type="", wait=0, res_status=""):
        with open(self.log_path, "a") as f:
            f.write(f"{ts},{event},{p_id},{urgency},{bed_type},{wait},{res_status}\n")

    def _get_acuity_counts(self) -> Dict[int, int]:
        counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        for p in self.active_patients:
            counts[p.urgency] += 1
        return counts

    def _get_rolling_rates(self, current_time) -> Dict[str, float]:
        rates = {'15m': 0, '30m': 0, '1h': 0, '4h': 0}
        for arr in reversed(self.past_arrivals):
            delta = (current_time - arr).total_seconds() / 60.0
            if delta <= 15: rates['15m'] += 1
            if delta <= 30: rates['30m'] += 1
            if delta <= 60: rates['1h'] += 1
            if delta <= 240: rates['4h'] += 1
            if delta > 240: break
        return rates

    def _update_reservations(self, current_time):
        """Update bed reservations based on regressor predictions."""
        # Release expired reservations
        if self.ed_reservation_expiry and current_time >= self.ed_reservation_expiry:
            self.metrics["expired_reservations"] += 1
            self.metrics["wasted_bed_minutes"] += (current_time - self.ed_reservation_start).total_seconds() / 60.0
            self.ed_reserved_count = 0
            self.ed_reservation_expiry = None
            self.ed_reservation_start = None
            
        if self.icu_reservation_expiry and current_time >= self.icu_reservation_expiry:
            self.metrics["expired_reservations"] += 1
            self.metrics["wasted_bed_minutes"] += (current_time - self.icu_reservation_start).total_seconds() / 60.0
            self.icu_reserved_count = 0
            self.icu_reservation_expiry = None
            self.icu_reservation_start = None
        
        ed_occ = min(1.0, sum(1 for p in self.active_patients if p.bed_type == 'ED') / self.state.ed_capacity)
        icu_occ = min(1.0, sum(1 for p in self.active_patients if p.bed_type == 'ICU') / max(1, self.state.icu_capacity))
        
        rates = self._get_rolling_rates(current_time)
        acuities = self._get_acuity_counts()
        
        # Predict expected number of L1/L2 arrivals in next 60m
        expected_arrivals = self.predictor.predict(current_time, ed_occ, icu_occ, rates, acuities)
        
        if expected_arrivals >= self.reservation_threshold:
            if self.ed_reserved_count == 0:
                self.ed_reserved_count = 1
                self.ed_reservation_start = current_time
                self.ed_reservation_expiry = current_time + timedelta(minutes=self.reservation_timeout_minutes)
                self.metrics["total_reservations"] += 1
            if self.icu_reserved_count == 0 and self.state.icu_capacity > 0:
                self.icu_reserved_count = 1
                self.icu_reservation_start = current_time
                self.icu_reservation_expiry = current_time + timedelta(minutes=self.reservation_timeout_minutes)
                self.metrics["total_reservations"] += 1

    def run(self, patients: List[SimulationPatient]):
        """Run discrete event simulation with starvation prevention (aging)."""
        patients.sort(key=lambda p: p.arrival)
        
        # Events queue: (timestamp, event_type, patient_obj)
        # event_type: 0 for discharge (process first if simultaneous), 1 for arrival
        events = []
        for p in patients:
            heapq.heappush(events, (p.arrival, 1, id(p), p))
            
        # Waiting queues (Standard lists, so we can iterate to calculate dynamic aging scores)
        ed_wait_q = []
        icu_wait_q = []
        
        ed_free_beds = self.state.ed_capacity
        icu_free_beds = self.state.icu_capacity
        
        while events:
            ev_time, ev_type, _, p = heapq.heappop(events)
            
            if ev_type == 0:
                # DISCHARGE EVENT
                self.active_patients.remove(p)
                if p.bed_type == 'ICU':
                    icu_free_beds += 1
                else:
                    ed_free_beds += 1
                
                # Check if we can admit someone from the queue
                self._update_reservations(ev_time)
                icu_free_beds, ed_free_beds = self._try_admit_from_queues(
                    ev_time, icu_wait_q, ed_wait_q, icu_free_beds, ed_free_beds, events
                )
                    
            elif ev_type == 1:
                # ARRIVAL EVENT
                self.past_arrivals.append(ev_time)
                self._update_reservations(ev_time)
                
                # Add to appropriate waiting queue (no heapq)
                if p.bed_type == 'ICU':
                    icu_wait_q.append(p)
                else:
                    ed_wait_q.append(p)
                    
                # Try admitting
                icu_free_beds, ed_free_beds = self._try_admit_from_queues(
                    ev_time, icu_wait_q, ed_wait_q, icu_free_beds, ed_free_beds, events
                )

    def _get_best_patient_idx(self, wait_q, current_time) -> Tuple[int, Tuple[float, float]]:
        """Calculate dynamic urgency aging to prevent starvation."""
        best_idx = -1
        best_score = None
        
        for i, p in enumerate(wait_q):
            wait_mins = (current_time - p.arrival).total_seconds() / 60.0
            
            # Target Maximum wait times (L1/L2 drops 10% from FCFS, L4/L5 caps at +10%)
            target_max = {
                1: 30.0,    # Target < 45.4
                2: 150.0,   # Target < 182.1
                3: 230.0,   # Equal to 231.4 FCFS
                4: 245.0,   # Target < 258.2
                5: 250.0    # Target < 274.5 
            }.get(p.urgency, 300.0)
            
            # Interpolate down to 0.0 urgency (which beats a fresh Level 1)
            progress = min(1.0, wait_mins / target_max)
            eff_urg = float(p.urgency) - progress * float(p.urgency)
            
            score = (eff_urg, p.arrival.timestamp())
            
            if best_score is None or score < best_score:
                best_score = score
                best_idx = i
                
        return best_idx, best_score

    def _try_admit_from_queues(self, current_time, icu_wait_q, ed_wait_q, icu_free_beds, ed_free_beds, events):
        """Attempt to pull patients from dynamic priority queues into free beds."""
        # Process ICU Queue
        while icu_wait_q and icu_free_beds > 0:
            best_idx, best_score = self._get_best_patient_idx(icu_wait_q, current_time)
            eff_urg = best_score[0]
            
            if eff_urg > 1.0 and icu_free_beds <= self.icu_reserved_count:
                break # Reserved for actual Level 1s
                
            if eff_urg <= 1.0 and self.icu_reserved_count > 0:
                if eff_urg == 1.0: # True critical catch
                    self.metrics["successful_catches"] += 1
                self.metrics["wasted_bed_minutes"] += (current_time - self.icu_reservation_start).total_seconds() / 60.0
                self.icu_reserved_count = 0
                self.icu_reservation_expiry = None
                self.icu_reservation_start = None
                
            p = icu_wait_q.pop(best_idx)
            icu_free_beds -= 1
            self._admit_patient(p, current_time, events)
            
        # Process ED Queue
        while ed_wait_q and ed_free_beds > 0:
            best_idx, best_score = self._get_best_patient_idx(ed_wait_q, current_time)
            eff_urg = best_score[0]
            
            if eff_urg > 1.0 and ed_free_beds <= self.ed_reserved_count:
                break # Reserved for actual Level 1s
                
            if eff_urg <= 1.0 and self.ed_reserved_count > 0:
                if eff_urg == 1.0: # True critical catch
                    self.metrics["successful_catches"] += 1
                self.metrics["wasted_bed_minutes"] += (current_time - self.ed_reservation_start).total_seconds() / 60.0
                self.ed_reserved_count = 0
                self.ed_reservation_expiry = None
                self.ed_reservation_start = None
                
            p = ed_wait_q.pop(best_idx)
            ed_free_beds -= 1
            self._admit_patient(p, current_time, events)
            
        return icu_free_beds, ed_free_beds
        
    def _admit_patient(self, p: SimulationPatient, current_time, events):
        p.service_start = current_time
        p.wait_minutes = (current_time - p.arrival).total_seconds() / 60.0
        p.discharge = current_time + timedelta(minutes=p.los_minutes)
        
        self.active_patients.append(p)
        
        # Schedule discharge event (type 0)
        heapq.heappush(events, (p.discharge, 0, id(p), p))
        
        status = "admitted" if p.wait_minutes == 0 else "waited_and_admitted"
        self._log(current_time, status, p.id, p.urgency, p.bed_type, p.wait_minutes)

