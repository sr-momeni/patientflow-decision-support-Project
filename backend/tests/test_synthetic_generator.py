from dataclasses import asdict

import pytest

from backend.data.synthetic_generator import OUTPUT_COLUMNS, generate_patients
from backend.optimization.congestion_scenarios import get_scenario


def test_columns_and_seed_repro():
    s = get_scenario("normal")
    a = generate_patients(10, s, seed=1)
    b = generate_patients(10, s, seed=1)
    assert [asdict(a[i]) for i in range(len(a))] == [asdict(b[i]) for i in range(len(b))]
    for col in OUTPUT_COLUMNS:
        assert col in asdict(a[0])


@pytest.mark.parametrize(
    "pid,expected",
    [("P00001", 1), ("P00002", 2), ("P00003", 3)],
)
def test_benchmark_ctas(pid, expected):
    s = get_scenario("normal")
    patients = generate_patients(3, s, seed=123, inject_cases=True)
    target = next(p for p in patients if p.patient_id == pid)
    assert target.ctas_level == expected
