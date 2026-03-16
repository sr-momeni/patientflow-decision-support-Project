import os
import sys
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Add the project root to sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from backend.ml.predictor import HighUrgencyPredictor
from backend.optimization.congestion_scenarios import get_scenario
from backend.agents.resource_allocation_agent import ResourceAllocationAgent

class RealTimeSimulationManager:
    """
    Manages a persistent, 'real-time' hospital state for the triage chatbot.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RealTimeSimulationManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.scenario = get_scenario("normal")
        self.ed_capacity = self.scenario.ed_beds
        self.icu_capacity = self.scenario.icu_beds
        
        # Load Predictor
        model_path = os.path.join(ROOT_DIR, "backend", "ml", "models", "high_urgency_predictor.joblib")
        if os.path.exists(model_path):
            self.predictor = HighUrgencyPredictor.load(model_path)
        else:
            self.predictor = HighUrgencyPredictor()
        
        # Resource Allocation Agent
        self.allocation_agent = ResourceAllocationAgent()
        
        # Active patients: list of {id, urgency, bed_type, checkout_ts}
        self.active_patients: List[Dict[str, Any]] = []
        
        # Warm up the simulation state
        self._warm_up()
        
        self._initialized = True
        print(f"DEBUG: RealTimeSimulationManager initialized with {len(self.active_patients)} active patients.")

    def _warm_up(self):
        """Populates the hospital with a realistic initial state based on time of day."""
        now = datetime.now()
        hour = now.hour
        
        # Deterministic but realistic occupancy based on hour
        # Peak hours (10-18) -> high occupancy
        # Night hours (02-06) -> low occupancy
        occupancy_weights = [
            0.5, 0.4, 0.3, 0.25, 0.25, 0.3, # 00-05
            0.4, 0.6, 0.8, 0.9, 0.95, 0.98, # 06-11
            0.98, 0.95, 0.9, 0.85, 0.8, 0.75, # 12-17
            0.7, 0.65, 0.6, 0.55, 0.5, 0.45 # 18-23
        ]
        
        base_occ = occupancy_weights[hour]
        # Spread slightly around base
        ed_occ_count = int(self.ed_capacity * base_occ * random.uniform(0.9, 1.1))
        ed_occ_count = max(0, min(ed_occ_count, self.ed_capacity - 1)) # Leave at least 1 spot for demo if possible
        
        icu_occ_count = int(self.icu_capacity * 0.6) # Constant fill for ICU
        
        # Generate ED patients
        for i in range(ed_occ_count):
            urgency = random.choices([1, 2, 3, 4, 5], weights=[0.05, 0.15, 0.4, 0.3, 0.1])[0]
            # Random time left (LOS usually 120-400 mins)
            mins_left = random.randint(10, 300)
            self.active_patients.append({
                "patient_id": f"INIT_ED_{i}",
                "urgency_level": urgency,
                "bed_assigned_type": "ED",
                "checkout_ts": now + timedelta(minutes=mins_left)
            })
            
        # Generate ICU patients
        for i in range(icu_occ_count):
            self.active_patients.append({
                "patient_id": f"INIT_ICU_{i}",
                "urgency_level": 1,
                "bed_assigned_type": "ICU",
                "checkout_ts": now + timedelta(hours=random.randint(12, 72))
            })

    def _refresh_state(self):
        """Removes patients who have reached their checkout time."""
        now = datetime.now()
        before_count = len(self.active_patients)
        self.active_patients = [p for p in self.active_patients if p["checkout_ts"] > now]
        after_count = len(self.active_patients)
        if before_count != after_count:
            print(f"DEBUG: Discharged {before_count - after_count} patients.")

    def get_current_state(self) -> Dict[str, Any]:
        self._refresh_state()
        ed_count = sum(1 for p in self.active_patients if p["bed_assigned_type"] == "ED")
        icu_count = sum(1 for p in self.active_patients if p["bed_assigned_type"] == "ICU")
        
        # Predict reservations
        now = datetime.now()
        rates = {'15m': 1, '30m': 2, '1h': 4, '4h': 16} # Mock rates for simplify
        acuities = {1: 1, 2: 2, 3: 5, 4: 5, 5: 2} # Mock acuities
        
        expected = self.predictor.predict(
            now, 
            ed_count / self.ed_capacity, 
            icu_count / max(1, self.icu_capacity),
            rates,
            acuities
        )
        
        # Reserve if expected >= 0.8
        ed_reserved = 1 if expected >= 0.8 else 0
        icu_reserved = 1 if expected >= 0.9 else 0
        
        return {
            "active_patients": self.active_patients,
            "ed_occupied": ed_count,
            "icu_occupied": icu_count,
            "ed_reserved": ed_reserved,
            "icu_reserved": icu_reserved,
            "expected_high_urgency": expected
        }

    def process_new_patient(self, ctas_level: int) -> Dict[str, Any]:
        """
        Calculates a real-time recommendation for a new patient from the chatbot.
        """
        state = self.get_current_state()
        
        # Prepare batch for allocation agent
        # We include all active patients to get correct occupancy context
        patient_batch = []
        for p in state["active_patients"]:
            patient_batch.append({
                "patient_id": p["patient_id"],
                "urgency_level": p["urgency_level"],
                "bed_assigned_type": p["bed_assigned_type"]
            })
            
        # Add the new patient
        new_patient_id = f"CHAT_{datetime.now().strftime('%M%S')}"
        patient_batch.append({
            "patient_id": new_patient_id,
            "urgency_level": ctas_level,
            "bed_assigned_type": None
        })
        
        # Run allocation
        recommendations, _ = self.allocation_agent.allocate_resources(
            patient_batch, 
            self.scenario,
            ed_reserved=state["ed_reserved"],
            icu_reserved=state["icu_reserved"]
        )
        
        # Find the recommendation for our new patient
        my_rec = next(r for r in recommendations if r.patient_id == new_patient_id)
        
        # If admitted, add to active patients locally
        if my_rec.recommended_bed != "waiting":
            self.active_patients.append({
                "patient_id": new_patient_id,
                "urgency_level": ctas_level,
                "bed_assigned_type": my_rec.recommended_bed,
                "checkout_ts": datetime.now() + timedelta(minutes=random.randint(60, 240))
            })
            
        return {
            "recommended_bed": my_rec.recommended_bed,
            "explanation": my_rec.decision_explanation,
            "hospital_state": {
                "ed_util": f"{state['ed_occupied']}/{self.ed_capacity}",
                "icu_util": f"{state['icu_occupied']}/{self.icu_capacity}",
                "reservations": state['ed_reserved'] + state['icu_reserved']
            }
        }
