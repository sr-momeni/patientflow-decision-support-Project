import heapq
from collections import deque
from typing import List
from datetime import timedelta
from .event_model import SimulationPatient, HospitalState

class SimulationEngine:
    def __init__(self, ed_capacity: int, icu_capacity: int):
        self.state = HospitalState(ed_capacity=ed_capacity, icu_capacity=icu_capacity)
        # We don't strictly need a deque attribute if we process by sorting, 
        # but it helps conceptualize.
        
    def run(self, patients: List[SimulationPatient]):
        # 1. Sort by arrival time (Critical for DES)
        patients.sort(key=lambda p: p.arrival)
        
        # 2. Process each patient
        for p in patients:
            self._process_patient(p)

    def _process_patient(self, p: SimulationPatient):
        # Determine which resource they need
        if p.bed_type == 'ICU':
            beds = self.state.icu_beds
            capacity = self.state.icu_capacity
        else:
            beds = self.state.ed_beds
            capacity = self.state.ed_capacity
            
        # 3. Bed Assignment Logic (FCFS)
        # Since we iterate in arrival order, the 'next available bed' in the heap
        # is correctly the one this patient will get.
        
        if len(beds) < capacity:
            # Bed available immediately
            # Start = Arrival
            start_time = p.arrival
        else:
            # Must wait for earliest bed to free up
            earliest_release = heapq.heappop(beds)
            
            # Start is when the bed frees up (or arrival, if bed freed up long ago)
            # The max() handles cases where the bed was free before arrival.
            start_time = max(p.arrival, earliest_release)
            
        # 4. Calculate new release time
        # Release = Start + LOS
        release_time = start_time + timedelta(minutes=p.los_minutes)
        heapq.heappush(beds, release_time)
            
        # 5. Record results
        p.service_start = start_time
        p.wait_minutes = (start_time - p.arrival).total_seconds() / 60.0
        p.discharge = release_time
