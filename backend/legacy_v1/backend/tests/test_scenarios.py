import pytest

from backend.optimization.congestion_scenarios import get_scenario, list_scenarios, validate_scenario


def test_named_scenarios_exist():
    available = set(list_scenarios().keys())
    assert {"normal", "ed_congestion", "icu_bottleneck"}.issubset(available)


@pytest.mark.parametrize("name", ["normal", "ed_congestion", "icu_bottleneck"])
def test_scenario_fields_positive(name):
    scenario = get_scenario(name)
    validate_scenario(scenario)
