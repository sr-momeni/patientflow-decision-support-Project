from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime

@dataclass
class SimulationPatient:
    id: str
    arrival: datetime
    urgency: int
    los_minutes: float
    bed_type: str  # 'ED' or 'ICU'
    
    # Simulation Output
    service_start: Optional[datetime] = None
    discharge: Optional[datetime] = None
    wait_minutes: float = 0.0

@dataclass
class HospitalState:
    # Capacity
    ed_capacity: int
    icu_capacity: int
    
    # State
    # We use heaps for release times to track available beds
    # Values are timestamps (float timestamp or datetime)
    ed_beds: List[datetime] = field(default_factory=list) 
    icu_beds: List[datetime] = field(default_factory=list)
