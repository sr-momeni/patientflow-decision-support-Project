"""Definitions of operational scenarios for CTAS 1/2/3 MVP."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ScenarioConfig:
    """Capacity + arrival assumptions for CTAS 1/2/3."""

    name: str
    description: str
    ed_beds: int
    icu_beds: int
    physicians: int
    nurses: int
    lab_slots_per_hour: int
    imaging_slots_per_hour: int
    arrival_rates_per_hour: Dict[int, float]  # CTAS level -> hourly arrivals
    ed_util_alert: float = 0.9
    icu_util_alert: float = 0.9

    @property
    def ed_beds_available(self) -> int:
        return self.ed_beds

    @property
    def icu_beds_available(self) -> int:
        return self.icu_beds


def _build_scenarios() -> Dict[str, ScenarioConfig]:
    """Create the three requested scenarios with documented assumptions."""

    normal = ScenarioConfig(
        name="normal",
        description="Balanced arrivals with comfortable ED/ICU capacity.",
        ed_beds=40,
        icu_beds=10,
        physicians=8,
        nurses=22,
        lab_slots_per_hour=22,
        imaging_slots_per_hour=14,
        arrival_rates_per_hour={1: 2.0, 2: 8.0, 3: 12.0},
        ed_util_alert=0.9,
        icu_util_alert=0.9,
    )

    ed_congestion = ScenarioConfig(
        name="ed_congestion",
        description="ED beds nearly saturated with heavier CTAS2/3 walk-ins.",
        ed_beds=26,
        icu_beds=8,
        physicians=7,
        nurses=18,
        lab_slots_per_hour=18,
        imaging_slots_per_hour=12,
        arrival_rates_per_hour={1: 2.2, 2: 12.0, 3: 20.0},
        ed_util_alert=0.9,
        icu_util_alert=0.9,
    )

    icu_bottleneck = ScenarioConfig(
        name="icu_bottleneck",
        description="ICU almost full; CTAS1 may stay in ED while waiting.",
        ed_beds=36,
        icu_beds=2,
        physicians=8,
        nurses=22,
        lab_slots_per_hour=22,
        imaging_slots_per_hour=14,
        arrival_rates_per_hour={1: 3.0, 2: 9.0, 3: 12.0},
        ed_util_alert=0.9,
        icu_util_alert=0.9,
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


def validate_scenario(cfg: ScenarioConfig) -> None:
    """Basic sanity checks to keep scenarios reasonable."""

    assert cfg.ed_beds > 0 and cfg.icu_beds >= 0
    assert cfg.lab_slots_per_hour > 0 and cfg.imaging_slots_per_hour > 0
    for lvl in (1, 2, 3):
        assert cfg.arrival_rates_per_hour.get(lvl, 0) >= 0
    assert 0 < cfg.ed_util_alert <= 1.0
    assert 0 < cfg.icu_util_alert <= 1.0
