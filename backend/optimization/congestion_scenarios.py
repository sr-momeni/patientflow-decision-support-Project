"""Definitions of operational scenarios for CTAS 1/2/3/4/5 MVP."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class ScenarioConfig:
    """Capacity + arrival assumptions for CTAS 1–5."""

    name: str
    description: str
    ed_beds: int
    icu_beds: int
    physicians: int
    nurses: int
    lab_slots_per_hour: int
    imaging_slots_per_hour: int

    # CTAS level -> hourly arrivals (now supports 1..5)
    arrival_rates_per_hour: Dict[int, float]

    # Utilization thresholds that can trigger alerts
    ed_util_alert: float = 0.9
    icu_util_alert: float = 0.9

    @property
    def ed_beds_available(self) -> int:
        return self.ed_beds

    @property
    def icu_beds_available(self) -> int:
        return self.icu_beds

    def arrival_rate(self, ctas_level: int) -> float:
        """Safe accessor (returns 0.0 if a level isn't specified)."""
        return float(self.arrival_rates_per_hour.get(ctas_level, 0.0))


def _build_scenarios() -> Dict[str, ScenarioConfig]:
    """Create scenarios with CTAS 1–5 documented assumptions."""

    # Notes on added CTAS 4/5 rates:
    # - CTAS4: less urgent, often fewer labs/imaging than CTAS2/3
    # - CTAS5: non-urgent, typically lowest acuity (still counts as ED load)
    #
    # You can tune these to match your site data.

    normal = ScenarioConfig(
        name="normal",
        description="Balanced arrivals with comfortable ED/ICU capacity.",
        ed_beds=40,
        icu_beds=10,
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
        ed_util_alert=0.9,
        icu_util_alert=0.9,
    )

    ed_congestion = ScenarioConfig(
        name="ed_congestion",
        description="ED beds nearly saturated with heavier CTAS2/3/4 walk-ins.",
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
        arrival_rates_per_hour={
            1: 3.0,
            2: 9.0,
            3: 12.0,
            4: 9.0,
            5: 5.0,
        },
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
    """Basic sanity checks to keep scenarios reasonable (CTAS 1–5)."""

    if not (cfg.ed_beds > 0 and cfg.icu_beds >= 0):
        raise ValueError("ed_beds must be > 0 and icu_beds must be >= 0")

    if cfg.physicians <= 0 or cfg.nurses <= 0:
        raise ValueError("physicians and nurses must be > 0")

    if cfg.lab_slots_per_hour <= 0 or cfg.imaging_slots_per_hour <= 0:
        raise ValueError("lab_slots_per_hour and imaging_slots_per_hour must be > 0")

    # Now validate CTAS levels 1..5
    for lvl in (1, 2, 3, 4, 5):
        rate = cfg.arrival_rates_per_hour.get(lvl, 0.0)
        if rate < 0:
            raise ValueError(f"arrival rate for CTAS{lvl} must be >= 0")

    if not (0 < cfg.ed_util_alert <= 1.0):
        raise ValueError("ed_util_alert must be in (0, 1]")

    if not (0 < cfg.icu_util_alert <= 1.0):
        raise ValueError("icu_util_alert must be in (0, 1]")
