"""Definitions of configurable ED congestion scenarios for the MVP."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ScenarioConfig:
    """Lightweight container describing capacity and arrival assumptions."""

    name: str
    description: str
    ed_beds: int
    icu_beds: int
    physicians: int
    nurses: int
    lab_slots_per_hour: int
    imaging_slots_per_hour: int
    arrival_rates_per_hour: Dict[int, float]  # urgency level -> expected hourly arrivals
    senior_staff_available: bool = True
    ed_near_full_threshold: float = 0.9
    peak_hour_multiplier: float = 1.2  # simple way to bump volumes during peaks


def _build_scenarios() -> Dict[str, ScenarioConfig]:
    """Create the three requested scenarios with documented assumptions."""

    normal = ScenarioConfig(
        name="normal",
        description="Balanced arrivals with comfortable ED and ICU capacity.",
        ed_beds=50,
        icu_beds=20,
        physicians=8,
        nurses=22,
        lab_slots_per_hour=22,
        imaging_slots_per_hour=14,
        arrival_rates_per_hour={1: 2.0, 2: 8.0, 3: 12.0},
        senior_staff_available=True,
        ed_near_full_threshold=0.85,
    )

    ed_congestion = ScenarioConfig(
        name="ed_congestion",
        description="ED beds nearly saturated with heavier Level 2/3 walk-ins.",
        ed_beds=26,
        icu_beds=8,
        physicians=7,
        nurses=18,
        lab_slots_per_hour=18,
        imaging_slots_per_hour=12,
        arrival_rates_per_hour={1: 2.2, 2: 12.0, 3: 20.0},
        senior_staff_available=True,
        ed_near_full_threshold=0.9,
    )

    icu_bottleneck = ScenarioConfig(
        name="icu_bottleneck",
        description="ICU essentially full; Level 1 stays in ED while waiting.",
        ed_beds=36,
        icu_beds=2,
        physicians=8,
        nurses=22,
        lab_slots_per_hour=22,
        imaging_slots_per_hour=14,
        arrival_rates_per_hour={1: 3.0, 2: 9.0, 3: 12.0},
        senior_staff_available=True,
        ed_near_full_threshold=0.9,
    )

    return {cfg.name: cfg for cfg in (normal, ed_congestion, icu_bottleneck)}


_SCENARIOS = _build_scenarios()


def get_scenario(name: str) -> ScenarioConfig:
    """Return a ScenarioConfig by name (case-insensitive)."""

    key = name.lower()
    if key not in _SCENARIOS:
        available = ", ".join(_SCENARIOS.keys())
        raise KeyError(f"Unknown scenario '{name}'. Available: {available}")
    return _SCENARIOS[key]


def list_scenarios() -> Dict[str, ScenarioConfig]:
    """Expose the scenarios mapping for discovery/testing."""

    return dict(_SCENARIOS)
