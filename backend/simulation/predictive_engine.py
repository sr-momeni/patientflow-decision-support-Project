"""Predictive simulation engine with AI-based bed reservation."""

import heapq
from typing import List
from datetime import timedelta
import os
from backend.simulation.event_model import SimulationPatient, HospitalState
from backend.ml.predictor import HighUrgencyPredictor

class PredictiveEngine:
    """Simulation engine with strict ML-based predictive bed reservation."""
    
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
        
        # Logging
        self.log_path = "data/simulation_events.log"
        os.makedirs("data", exist_ok=True)
        with open(self.log_path, "w") as f:
            f.write("timestamp,event,patient_id,urgency,bed_type,wait_time,reservation_status\n")
            
    def _log(self, ts, event, p_id="", urgency="", bed_type="", wait=0, res_status=""):
        with open(self.log_path, "a") as f:
            f.write(f"{ts},{event},{p_id},{urgency},{bed_type},{wait},{res_status}\n")

    def run(self, patients: List[SimulationPatient]):
        """Run simulation with predictive bed reservation."""
        patients.sort(key=lambda p: p.arrival)
        
        for i, p in enumerate(patients):
            self._process_patient(p, patients, i)
    
    def _calculate_occupancy(self, current_time) -> tuple:
        """Count beds currently in use (release time > current time)."""
        # Count beds currently in use (release time > current time)
        ed_in_use = sum(1 for t in self.state.ed_beds if t > current_time)
        icu_in_use = sum(1 for t in self.state.icu_beds if t > current_time)
        
        ed_occ = ed_in_use / self.state.ed_capacity if self.state.ed_capacity > 0 else 1.0
        icu_occ = icu_in_use / self.state.icu_capacity if self.state.icu_capacity > 0 else 1.0
        
        return ed_occ, icu_occ, ed_in_use, icu_in_use
    
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
            self._log(current_time, "reservation_expired", bed_type="ED")
            self.ed_reserved_count = 0
            self.ed_reservation_expiry = None
            
        if self.icu_reservation_expiry and current_time >= self.icu_reservation_expiry:
            self._log(current_time, "reservation_expired", bed_type="ICU")
            self.icu_reserved_count = 0
            self.icu_reservation_expiry = None
        
        # Get current state
        ed_occ, icu_occ, ed_in_use, icu_in_use = self._calculate_occupancy(current_time)
        recent_rate = self._calculate_recent_rate(patients, current_idx, current_time)
        
        # Predict arrival probabilities distribution
        probs = self.predictor.predict(current_time, ed_occ, icu_occ, recent_rate)
        
        # Reserve beds if probability of Level 1 (Critical) is high
        l1_prob = probs.get(1, 0.0)
        if l1_prob >= self.reservation_threshold:
            if self.ed_reserved_count == 0:
                self.ed_reserved_count = 1
                self.ed_reservation_expiry = current_time + timedelta(
                    minutes=self.reservation_timeout_minutes
                )
                self._log(current_time, "reserved", bed_type="ED", res_status=f"p={l1_prob:.2f}")
            if self.icu_reserved_count == 0:
                self.icu_reserved_count = 1
                self.icu_reservation_expiry = current_time + timedelta(
                    minutes=self.reservation_timeout_minutes
                )
                self._log(current_time, "reserved", bed_type="ICU", res_status=f"p={l1_prob:.2f}")
    
    def _process_patient(self, p: SimulationPatient, patients: List[SimulationPatient], 
                        current_idx: int):
        """Process a patient with predictive logic."""
        # Update reservations
        self._update_reservations(p.arrival, patients, current_idx)
        
        # Determine which resource they need
        if p.bed_type == 'ICU':
            beds = self.state.icu_beds
            capacity = self.state.icu_capacity
            reserved = self.icu_reserved_count
        else:
            beds = self.state.ed_beds
            capacity = self.state.ed_capacity
            reserved = self.ed_reserved_count
        
        # Cleanup past beds to find available ones
        active_ends = []
        while beds:
            end = heapq.heappop(beds)
            if end > p.arrival:
                heapq.heappush(active_ends, end)
                break
            # Bed is free, we don't push it back
        for b in beds:
            heapq.heappush(active_ends, b)
        
        if p.bed_type == 'ICU': self.state.icu_beds = active_ends
        else: self.state.ed_beds = active_ends
        
        beds = active_ends
        available_beds = capacity - len(beds)
        
        # Decision Logic
        can_assign = False
        if p.urgency == 1:
            if available_beds > 0:
                can_assign = True
                # Used a reservation if it exists
                if p.bed_type == 'ICU' and self.icu_reserved_count > 0:
                    self.icu_reserved_count = 0
                    self.icu_reservation_expiry = None
                    self._log(p.arrival, "reservation_used", p.id, urgency=1, bed_type="ICU")
                elif p.bed_type != 'ICU' and self.ed_reserved_count > 0:
                    self.ed_reserved_count = 0
                    self.ed_reservation_expiry = None
                    self._log(p.arrival, "reservation_used", p.id, urgency=1, bed_type="ED")
        else:
            # Others can only take non-reserved beds
            if available_beds > reserved:
                can_assign = True

        if can_assign:
            start_time = p.arrival
        else:
            # Must wait for earliest bed
            # BUT: If it was a Level 1 patient and all beds full, wait for ANY bed.
            # If it was Level 2-5, wait for a bed that becomes "non-reserved".
            # For simplicity: wait for any release.
            if not beds: # Should not happen if capacity > 0
                 start_time = p.arrival
            else:
                 earliest_release = heapq.heappop(beds)
                 start_time = max(p.arrival, earliest_release)
                 # Note: The bed is popped, we will push its new release later
        
        # Record results
        release_time = start_time + timedelta(minutes=p.los_minutes)
        heapq.heappush(beds, release_time)
        
        p.service_start = start_time
        p.wait_minutes = (start_time - p.arrival).total_seconds() / 60.0
        p.discharge = release_time
        
        status = "admitted" if p.wait_minutes == 0 else "waited_and_admitted"
        self._log(p.arrival, status, p.id, p.urgency, p.bed_type, p.wait_minutes)
