import pytest

from backend.optimization.congestion_scenarios import get_scenario, list_scenarios


def test_named_scenarios_exist():
    available = set(list_scenarios().keys())
    assert {"normal", "ed_congestion", "icu_bottleneck"}.issubset(available)


@pytest.mark.parametrize("name", ["normal", "ed_congestion", "icu_bottleneck"])
def test_scenario_fields_positive(name):
    scenario = get_scenario(name)
    assert scenario.ed_beds > 0
    assert scenario.physicians > 0
    assert scenario.lab_slots_per_hour > 0
