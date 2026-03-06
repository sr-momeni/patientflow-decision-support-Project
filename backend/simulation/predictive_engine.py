"""Predictive simulation engine with AI-based bed reservation."""

import heapq
from typing import Dict, List
from datetime import timedelta
from backend.simulation.event_model import SimulationPatient, HospitalState
from backend.ml.predictor import HighUrgencyPredictor


def summarize_simulation_metrics(
    patients: List[SimulationPatient],
    ed_capacity: int,
    icu_capacity: int,
) -> Dict[str, float]:
    """Compute basic performance metrics from completed simulation results."""

    if not patients:
        return {
            "average_waiting_time": 0.0,
            "average_los": 0.0,
            "ed_bed_utilization": 0.0,
            "icu_bed_utilization": 0.0,
        }

    avg_wait = sum(p.wait_minutes for p in patients) / len(patients)
    avg_los = sum(p.los_minutes for p in patients) / len(patients)

    start_time = min(p.arrival for p in patients)
    end_time = max(p.discharge for p in patients if p.discharge is not None)
    horizon_minutes = max((end_time - start_time).total_seconds() / 60.0, 1.0)

    ed_patient_minutes = sum(p.los_minutes for p in patients if p.bed_type == "ED")
    icu_patient_minutes = sum(p.los_minutes for p in patients if p.bed_type == "ICU")

    ed_util = ed_patient_minutes / (ed_capacity * horizon_minutes) if ed_capacity > 0 else 0.0
    icu_util = icu_patient_minutes / (icu_capacity * horizon_minutes) if icu_capacity > 0 else 0.0

    return {
        "average_waiting_time": round(avg_wait, 2),
        "average_los": round(avg_los, 2),
        "ed_bed_utilization": round(ed_util, 4),
        "icu_bed_utilization": round(icu_util, 4),
    }

class PredictiveEngine:
    """Simulation engine with ML-based predictive bed reservation."""
    
    def __init__(self, ed_capacity: int, icu_capacity: int, 
                 predictor: HighUrgencyPredictor, 
                 reservation_threshold: float = 0.7,
                 reservation_timeout_minutes: int = 30):
        self.state = HospitalState(ed_capacity=ed_capacity, icu_capacity=icu_capacity)
        self.predictor = predictor
        self.reservation_threshold = reservation_threshold
        self.reservation_timeout_minutes = reservation_timeout_minutes
        
        # Track reserved beds
        self.ed_reserved_count = 0
        self.icu_reserved_count = 0
        self.ed_reservation_expiry = None
        self.icu_reservation_expiry = None
        
    def run(self, patients: List[SimulationPatient]):
        """Run simulation with predictive bed reservation."""
        patients.sort(key=lambda p: p.arrival)
        
        for i, p in enumerate(patients):
            self._process_patient(p, patients, i)
    
    def _calculate_occupancy(self, current_time) -> tuple:
        """Calculate current occupancy rates."""
        # Count beds currently in use (release time > current time)
        ed_in_use = sum(1 for t in self.state.ed_beds if t > current_time)
        icu_in_use = sum(1 for t in self.state.icu_beds if t > current_time)
        
        ed_occupancy = ed_in_use / self.state.ed_capacity
        icu_occupancy = icu_in_use / self.state.icu_capacity
        
        return ed_occupancy, icu_occupancy
    
    def _calculate_recent_rate(self, patients: List[SimulationPatient], 
                               current_idx: int, current_time) -> float:
        """Calculate arrival rate in last 2 hours."""
        lookback = current_time - timedelta(hours=2)
        count = 0
        
        # Count backwards from current
        for i in range(current_idx - 1, -1, -1):
            if patients[i].arrival < lookback:
                break
            count += 1
        
        return count / 2.0  # patients per hour
    
    def _update_reservations(self, current_time, patients: List[SimulationPatient], 
                            current_idx: int):
        """Update bed reservations based on predictions."""
        # Release expired reservations
        if self.ed_reservation_expiry and current_time >= self.ed_reservation_expiry:
            self.ed_reserved_count = 0
            self.ed_reservation_expiry = None
            
        if self.icu_reservation_expiry and current_time >= self.icu_reservation_expiry:
            self.icu_reserved_count = 0
            self.icu_reservation_expiry = None
        
        # Get current state
        ed_occ, icu_occ = self._calculate_occupancy(current_time)
        recent_rate = self._calculate_recent_rate(patients, current_idx, current_time)
        
        # Predict high-urgency arrival
        prob = self.predictor.predict(current_time, ed_occ, icu_occ, recent_rate)
        
        # Reserve beds if probability is high
        if prob >= self.reservation_threshold:
            if self.ed_reserved_count == 0:
                self.ed_reserved_count = 1
                self.ed_reservation_expiry = current_time + timedelta(
                    minutes=self.reservation_timeout_minutes
                )
            if self.icu_reserved_count == 0:
                self.icu_reserved_count = 1
                self.icu_reservation_expiry = current_time + timedelta(
                    minutes=self.reservation_timeout_minutes
                )
    
    def _process_patient(self, p: SimulationPatient, patients: List[SimulationPatient], 
                        current_idx: int):
        """Process a patient with predictive logic."""
        # Update reservations
        self._update_reservations(p.arrival, patients, current_idx)
        
        # Determine which resource they need
        if p.bed_type == 'ICU':
            beds = self.state.icu_beds
            capacity = self.state.icu_capacity
            reserved_count = self.icu_reserved_count
        else:
            beds = self.state.ed_beds
            capacity = self.state.ed_capacity
            reserved_count = self.ed_reserved_count
        
        # Effective capacity = total - reserved (unless patient is high urgency)
        effective_capacity = capacity
        if p.urgency != 1:  # Not critical
            effective_capacity = capacity - reserved_count
        else:
            # Critical patient can use reserved bed
            if p.bed_type == 'ICU':
                self.icu_reserved_count = max(0, self.icu_reserved_count - 1)
            else:
                self.ed_reserved_count = max(0, self.ed_reserved_count - 1)
        
        # Bed assignment logic
        if len(beds) < effective_capacity:
            # Bed available
            start_time = p.arrival
        else:
            # Must wait for earliest bed
            earliest_release = heapq.heappop(beds)
            start_time = max(p.arrival, earliest_release)
        
        # Record results
        release_time = start_time + timedelta(minutes=p.los_minutes)
        heapq.heappush(beds, release_time)
        
        p.service_start = start_time
        p.wait_minutes = (start_time - p.arrival).total_seconds() / 60.0
        p.discharge = release_time
