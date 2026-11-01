from dataclasses import asdict

from backend.data.synthetic_generator import (
    REQUIRED_COLUMNS,
    generate_events,
    summarize,
)
import pytest
from dataclasses import asdict

from backend.data.synthetic_generator import OUTPUT_COLUMNS, generate_patients
from backend.optimization.congestion_scenarios import get_scenario


def test_generator_outputs_required_columns():
    scenario = get_scenario("normal")
    events = generate_events(20, scenario, seed=123)
    first_row = asdict(events[0])
    for col in REQUIRED_COLUMNS:
        assert col in first_row


def test_icu_bottleneck_increases_simulated_wait_not_service_requirement():
    # Bed capacity belongs to the queue engine, not generated service duration.
    from datetime import datetime
    from backend.simulation.event_model import SimulationPatient
    from backend.simulation.engine import SimulationEngine
    def patients():
        return [SimulationPatient(str(i), datetime(2026,1,5), 1, 60., 'ICU') for i in range(4)]
    normal, bottleneck = patients(), patients()
    SimulationEngine(1,4).run(normal)
    SimulationEngine(1,1).run(bottleneck)
    assert sum(p.wait_minutes for p in bottleneck) > sum(p.wait_minutes for p in normal)
    assert [p.los_minutes for p in normal] == [p.los_minutes for p in bottleneck]

@pytest.mark.parametrize(
    "pid,expected",
    [
        ("P00001", 1),
        ("P00002", 2),
        ("P00003", 3),
        ("P00004", 4),
        ("P00005", 5),
    ],
)
def test_benchmark_ctas(pid, expected):
    s = get_scenario("normal")
    # generate at least 5 so P00004/P00005 exist
    patients = generate_patients(5, s, seed=123, inject_cases=True)
    target = next(p for p in patients if p.patient_id == pid)
    assert target.ctas_level == expected
