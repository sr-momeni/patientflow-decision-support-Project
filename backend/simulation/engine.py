"""FCFS entry point using the shared resource engine."""
from .queue_engine import QueueEngine

class SimulationEngine(QueueEngine):
    def __init__(self, ed_capacity, icu_capacity, **kwargs):
        super().__init__(ed_capacity, icu_capacity, policy='FCFS', **kwargs)
