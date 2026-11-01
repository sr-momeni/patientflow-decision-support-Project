"""Scenario-driven synthetic arrivals and service requirements (not observed outcomes).

Hourly CTAS-specific Poisson rates use normalized diurnal shape, a peak multiplier,
and weekday multipliers. No Ontario/CIHI calibration has been performed.
Capacity queues are applied by the simulation, never fabricated in the generator.
"""

from __future__ import annotations

import argparse
import csv
import math
import random
import numpy as np
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Sequence

from backend.optimization.congestion_scenarios import ScenarioConfig, get_scenario, validate_scenario
from backend.optimization import constraints


RAW_DIR = Path(__file__).resolve().parent / "raw"

REQUIRED_COLUMNS = [
    "patient_id",
    "arrival_ts",
    "urgency_level",
    "arrival_mode",
    "triage_ts",
    "assessment_start_ts",
    "lab_required",
    "imaging_required",
    "bed_assigned_type",
    "admit_decision",
    "discharge_ts",
    "waiting_time_minutes",
    "los_minutes",
]

# Backward-compatible alias for older tests/imports.
OUTPUT_COLUMNS = REQUIRED_COLUMNS


@dataclass
class PatientEvent:
    patient_id: str
    arrival_ts: str
    urgency_level: int
    arrival_mode: str
    triage_ts: str
    assessment_start_ts: str
    lab_required: bool
    imaging_required: bool
    bed_assigned_type: str
    admit_decision: str
    discharge_ts: str
    waiting_time_minutes: float
    los_minutes: float  # compatibility alias: required bed service, NOT ED LOS
    service_minutes: float = 0.0
    triage_minutes: float = 0.0

    @property
    def ctas_level(self) -> int:
        """Backward-compatible alias for older tests."""
        return self.urgency_level


# ---------------------------------------------------------------------------
# Arrival Pattern Constants
# ---------------------------------------------------------------------------

# Diurnal pattern (relative weights for each of the 24 hours, starting at 00:00)
# peak 10:00-14:00, trough 03:00-05:00
HOURLY_WEIGHTS = [
    0.4, 0.3, 0.2, 0.15, 0.15, 0.2,  # 00:00 - 05:00 (trough)
    0.4, 0.7, 1.0, 1.3, 1.5, 1.6,  # 06:00 - 11:00 (building to peak)
    1.6, 1.5, 1.4, 1.3, 1.2, 1.1,  # 12:00 - 17:00 (peak/afternoon)
    1.0, 0.9, 0.8, 0.7, 0.6, 0.5   # 18:00 - 23:00 (tapering off)
]
_HOURLY_TOTAL = sum(HOURLY_WEIGHTS)

# Day-of-week multipliers (0=Mon, 1=Tue, ..., 6=Sun)
# Sat +25%, Tue/Wed/Thu -10%
DOW_MULTIPLIERS = [
    1.0, 0.9, 0.9, 0.9, 1.0, 1.25, 1.1
]

def _probabilities_by_level(level: int) -> Dict[str, float]:
    arrival_mode = {
        1: (0.70, 0.05, 0.25),
        2: (0.30, 0.65, 0.05),
        3: (0.05, 0.90, 0.05),
        4: (0.02, 0.95, 0.03),
        5: (0.01, 0.98, 0.01),
    }
    lab     = {1: 0.80, 2: 0.60, 3: 0.30, 4: 0.15, 5: 0.05}
    imaging = {1: 0.60, 2: 0.40, 3: 0.15, 4: 0.05, 5: 0.02}
    icu     = {1: 0.70, 2: 0.15, 3: 0.00, 4: 0.00, 5: 0.00}
    amb, walk, xfer = arrival_mode[level]
    return {
        "ambulance": amb,
        "walkin":    walk,
        "transfer":  xfer,
        "lab":       lab[level],
        "imaging":   imaging[level],
        "icu_need":  icu[level],
    }


# Log-normal service-time parameters: (mu, sigma, lo_clamp, hi_clamp) in minutes
_SERVICE_PARAMS: Dict[int, tuple] = {
    1: (5.10, 0.60,  60, 480),  # mean ≈ 200 min
    2: (5.40, 0.50,  90, 600),  # mean ≈ 270 min
    3: (5.50, 0.65, 120, 720),  # mean ≈ 320 min
    4: (4.40, 0.50,  40, 300),  # mean ≈ 100 min
    5: (3.80, 0.40,  20, 150),  # mean ≈  50 min
}


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def hourly_intensity(scenario: ScenarioConfig, day: date, hour: int, level: int) -> float:
    """Per-level rate is the daily-average hourly rate before weekday effects.

    Peak multiplier redistributes within-day demand; normalizing preserves volume.
    """
    weights = np.asarray(HOURLY_WEIGHTS, dtype=float).copy()
    weights[10:15] *= scenario.peak_hour_multiplier
    shape = weights / weights.mean()
    return scenario.arrival_rate(level) * DOW_MULTIPLIERS[day.weekday()] * shape[hour]


def _make_event(pid, arrival, level, rng):
    probs = _probabilities_by_level(level)
    mode = rng.choice(['ambulance', 'walk-in', 'transfer'],
                      p=[probs['ambulance'], probs['walkin'], probs['transfer']])
    lab = bool(rng.random() < probs['lab'])
    imaging = bool(rng.random() < probs['imaging'])
    bed = 'ICU' if rng.random() < probs['icu_need'] else 'ED'
    mu, sigma, lo, hi = _SERVICE_PARAMS[level]
    service = round(float(np.clip(rng.lognormal(mu, sigma), lo, hi)), 2)
    triage = round(float(rng.uniform(3, 10)), 2)
    roll = rng.random()
    disposition = ('admit' if roll < .8 else 'transfer') if level == 1 else (
        ('admit' if roll < .55 else 'discharge') if level == 2 else
        ('admit' if level == 3 and roll >= .8 else 'discharge'))
    # Actual triage/assessment/departure cannot be known before queues are run.
    return PatientEvent(pid, arrival.isoformat(), level, str(mode), '', '', lab,
                        imaging, bed, disposition, '', 0.0, service, service, triage)


def generate_events(days: int, scenario: ScenarioConfig, seed: int = 42,
                    start_date: date | None = None) -> List[PatientEvent]:
    """Independent Poisson arrivals per hour/CTAS; local RNG, no global mutation."""
    validate_scenario(scenario)
    if not isinstance(days, int) or days < 0:
        raise ValueError('days must be a nonnegative integer')
    start_date = start_date or date(2026, 1, 5)
    streams = np.random.SeedSequence(seed).spawn(2)
    arrival_rng, service_rng = [np.random.default_rng(x) for x in streams]
    arrivals = []
    for offset in range(days):
        day = start_date + timedelta(days=offset)
        for hour in range(24):
            for level in range(1, 6):
                count = arrival_rng.poisson(hourly_intensity(scenario, day, hour, level))
                for minute in arrival_rng.uniform(0, 60, count):
                    arrivals.append((datetime.combine(day, time(hour)) + timedelta(minutes=float(minute)), level))
    arrivals.sort()
    return [_make_event(f'P{i:06d}', arrival, level, service_rng)
            for i, (arrival, level) in enumerate(arrivals, 1)]


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def save_events_to_csv(events: Sequence[PatientEvent], output_path: str | Path) -> None:
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(PatientEvent.__dataclass_fields__))
        writer.writeheader()
        for ev in events:
            writer.writerow(asdict(ev))


def summarize(events: Sequence[PatientEvent]) -> Dict:
    los      = [ev.los_minutes for ev in events]
    by_level: Dict[int, List[float]] = defaultdict(list)
    for ev in events:
        by_level[ev.urgency_level].append(ev.los_minutes)

    summary: Dict = {
        "count":   len(events),
        "avg_los": round(sum(los) / len(los), 2) if events else 0.0,
    }
    for level, vals in by_level.items():
        summary[f"avg_los_level_{level}"] = round(sum(vals) / len(vals), 2)
        summary[f"count_level_{level}"]   = len(vals)
    return summary


def generate_patients(
    n: int,
    scenario: ScenarioConfig,
    seed: int = 0,
    inject_cases: bool = False,
    **kwargs,
) -> List[PatientEvent]:
    """
    Backward-compatible wrapper for older tests.

    This maps the legacy generator name onto the current event generator
    without changing the current simulation data model.
    """

    if n < 0:
        raise ValueError('n must be nonnegative')
    if n == 0:
        return []
    if sum(scenario.arrival_rates_per_hour.values()) <= 0:
        raise ValueError('cannot generate a fixed count from zero arrival rates')
    days = max(1, math.ceil(n / (24 * sum(scenario.arrival_rates_per_hour.values()))))
    events = generate_events(days, scenario, seed, kwargs.get('start_date'))
    while len(events) < n:
        days *= 2
        events = generate_events(days, scenario, seed, kwargs.get('start_date'))
    events = events[:n]
    # Legacy fixture option; explicitly excluded from experiment generation.
    rng = np.random.default_rng(seed)
    for idx, event in enumerate(events):
        event.patient_id = f'P{idx + 1:05d}'
        if inject_cases and idx < 5:
            events[idx] = _make_event(event.patient_id, datetime.fromisoformat(event.arrival_ts), idx + 1, rng)
    return events


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synthetic ED patient-flow generator (day-based)."
    )
    parser.add_argument(
        "--days", type=int, default=7,
        help="Number of days to generate (default: 7). Day 0 is always Monday.",
    )
    parser.add_argument(
        "--scenario", default="normal",
        help="Scenario name: normal | ed_congestion | icu_bottleneck",
    )
    parser.add_argument("--seed",   type=int, default=42)
    parser.add_argument("--output", type=str, default=None,
                        help="Output CSV path (optional)")
    args = parser.parse_args()

    scenario     = get_scenario(args.scenario)
    start_monday = date(2026, 1, 5)
    events       = generate_events(args.days, scenario, seed=args.seed,
                                   start_date=start_monday)

    output_path = (
        Path(args.output) if args.output
        else RAW_DIR / f"synthetic_{scenario.name}_{args.days}d.csv"
    )
    save_events_to_csv(events, output_path)

    summary = summarize(events)
    print(f"Generated {summary['count']} patients over {args.days} days "
          f"(Mon {start_monday}) → {output_path}")
    print(f"Average LOS: {summary['avg_los']} min")
    print("\nBy urgency level:")
    for level in (1, 2, 3, 4, 5):
        cnt = summary.get(f"count_level_{level}", 0)
        avg = summary.get(f"avg_los_level_{level}", 0.0)
        pct = cnt / summary["count"] * 100 if summary["count"] else 0
        print(f"  Level {level}: {cnt:5d} patients ({pct:5.1f}%)  |  avg LOS: {avg:.0f} min")


if __name__ == "__main__":
    main()
