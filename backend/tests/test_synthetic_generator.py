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


def test_icu_bottleneck_increases_los():
    normal = get_scenario("normal")
    bottleneck = get_scenario("icu_bottleneck")

    normal_events = generate_events(150, normal, seed=1)
    bottleneck_events = generate_events(150, bottleneck, seed=1)

    normal_avg_los = summarize(normal_events)["avg_los"]
    bottleneck_avg_los = summarize(bottleneck_events)["avg_los"]

    assert bottleneck_avg_los > normal_avg_los
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
