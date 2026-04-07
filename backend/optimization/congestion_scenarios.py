"""Definitions of operational scenarios for the CTAS 1-5 MVP."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ScenarioConfig:
    """Capacity and arrival assumptions for ED simulation scenarios."""

    name: str
    description: str
    ed_beds: int
    icu_beds: int
    physicians: int
    nurses: int
    lab_slots_per_hour: int
    imaging_slots_per_hour: int
    arrival_rates_per_hour: Dict[int, float]
    senior_staff_available: bool = True
    ed_near_full_threshold: float = 0.9
    peak_hour_multiplier: float = 1.2
    ed_util_alert: float = 0.9
    icu_util_alert: float = 0.9

    @property
    def ed_beds_available(self) -> int:
        return self.ed_beds

    @property
    def icu_beds_available(self) -> int:
        return self.icu_beds

    def arrival_rate(self, ctas_level: int) -> float:
        """Safe accessor for per-level arrival rates."""
        return float(self.arrival_rates_per_hour.get(ctas_level, 0.0))


def _build_scenarios() -> Dict[str, ScenarioConfig]:
    """Create scenarios with CTAS 1-5 documented assumptions."""

    normal = ScenarioConfig(
        name="normal",
        description="Balanced arrivals with comfortable ED and ICU capacity.",
        ed_beds=50,
        icu_beds=20,
        physicians=8,
        nurses=22,
        lab_slots_per_hour=22,
        imaging_slots_per_hour=14,
        arrival_rates_per_hour={
            1: 2.0,
            2: 8.0,
            3: 12.0,
            4: 10.0,
            5: 6.0,
        },
        senior_staff_available=True,
        ed_near_full_threshold=0.85,
        ed_util_alert=0.9,
        icu_util_alert=0.9,
    )

    ed_congestion = ScenarioConfig(
        name="ed_congestion",
        description="ED beds nearly saturated with heavier CTAS 2/3/4 walk-ins.",
        ed_beds=26,
        icu_beds=8,
        physicians=7,
        nurses=18,
        lab_slots_per_hour=18,
        imaging_slots_per_hour=12,
        arrival_rates_per_hour={
            1: 2.2,
            2: 12.0,
            3: 20.0,
            4: 16.0,
            5: 10.0,
        },
        senior_staff_available=True,
        ed_near_full_threshold=0.9,
        ed_util_alert=0.9,
        icu_util_alert=0.9,
    )
    
    severe_congestion = ScenarioConfig(
        name="severe_congestion",
        description="Severe congestion with very high arrivals vs capacity.",
        ed_beds=20,
        icu_beds=5,
        physicians=6,
        nurses=14,
        lab_slots_per_hour=15,
        imaging_slots_per_hour=10,
        arrival_rates_per_hour={1: 3.0, 2: 15.0, 3: 25.0, 4: 20.0, 5: 15.0},
        senior_staff_available=True,
        ed_near_full_threshold=0.95,
        ed_util_alert=0.95,
        icu_util_alert=0.95,
    )

    icu_bottleneck = ScenarioConfig(
        name="icu_bottleneck",
        description="ICU essentially full; high-acuity patients may remain in ED while waiting.",
        ed_beds=36,
        icu_beds=2,
        physicians=8,
        nurses=22,
        lab_slots_per_hour=22,
        imaging_slots_per_hour=14,
        arrival_rates_per_hour={
            1: 3.0,
            2: 9.0,
            3: 12.0,
            4: 9.0,
            5: 5.0,
        },
        senior_staff_available=True,
        ed_near_full_threshold=0.9,
        ed_util_alert=0.9,
        icu_util_alert=0.9,
    )

    critical_burst = ScenarioConfig(
        name="critical_burst",
        description="Surge in Level 1 and Level 2 critical arrivals.",
        ed_beds=50,
        icu_beds=20,
        physicians=8,
        nurses=22,
        lab_slots_per_hour=22,
        imaging_slots_per_hour=14,
        arrival_rates_per_hour={1: 10.0, 2: 20.0, 3: 12.0, 4: 10.0, 5: 6.0},
        senior_staff_available=True,
        ed_near_full_threshold=0.85,
        ed_util_alert=0.9,
        icu_util_alert=0.9,
    )

    return {cfg.name: cfg for cfg in (
        normal, ed_congestion, 
        severe_congestion, icu_bottleneck, critical_burst
    )}


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

    if not (cfg.ed_beds > 0 and cfg.icu_beds >= 0):
        raise ValueError("ed_beds must be > 0 and icu_beds must be >= 0")
    if cfg.physicians <= 0 or cfg.nurses <= 0:
        raise ValueError("physicians and nurses must be > 0")
    if cfg.lab_slots_per_hour <= 0 or cfg.imaging_slots_per_hour <= 0:
        raise ValueError("lab_slots_per_hour and imaging_slots_per_hour must be > 0")

    for lvl in (1, 2, 3, 4, 5):
        rate = cfg.arrival_rates_per_hour.get(lvl, 0.0)
        if rate < 0:
            raise ValueError(f"arrival rate for CTAS{lvl} must be >= 0")
    if not (0 < cfg.ed_util_alert <= 1.0):
        raise ValueError("ed_util_alert must be in (0, 1]")
    if not (0 < cfg.icu_util_alert <= 1.0):
        raise ValueError("icu_util_alert must be in (0, 1]")
