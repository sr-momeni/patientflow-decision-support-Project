"""Synthetic ED patient-flow event generator.

Generates data for a specified number of days (not a fixed patient count).
Day 0 is always a Monday (defaults to the most recent Monday).

Arrival patterns:
- Realistic daily volume (~155/day for a 50-bed ED)
- Diurnal (time-of-day) weighting — peak 10:00–14:00, trough 03:00–05:00
- Day-of-week multipliers (Sat +25%, Tue/Wed/Thu −10%, etc.)
- National CTAS urgency distribution
- Log-normal service times (no bed-queue wait time simulation)
"""

from __future__ import annotations

import argparse
import csv
import math
import random
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Dict, List, Sequence

from backend.optimization.congestion_scenarios import ScenarioConfig, get_scenario
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
    los_minutes: float

    @property
    def ctas_level(self) -> int:
        """Backward-compatible alias for older tests."""
        return self.urgency_level


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _most_recent_monday() -> date:
    """Return today's date adjusted back to the most recent Monday."""
    today = date.today()
    return today - timedelta(days=today.weekday())  # weekday() == 0 on Monday


def _sample_minute_in_day() -> float:
    """Return a random minute (0–1439) weighted by the diurnal pattern."""
    r = random.random() * _HOURLY_TOTAL
    cumulative = 0.0
    for hour, weight in enumerate(HOURLY_WEIGHTS):
        cumulative += weight
        if r <= cumulative:
            return hour * 60.0 + random.uniform(0, 60)
    return 1439.0


def _choose_urgency_level(hour: int) -> int:
    """Sample an urgency level based on the hour of arrival."""
    if hour >= 22 or hour < 6:
        weights = CTAS_WEIGHTS_NIGHT
    else:
        weights = CTAS_WEIGHTS_DAY
    return random.choices(population=[1, 2, 3, 4, 5], weights=weights, k=1)[0]



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


def _service_minutes(level: int) -> float:
    mu, sigma, lo, hi = _SERVICE_PARAMS[level]
    raw = math.exp(random.gauss(mu, sigma))
    return max(lo, min(hi, raw))


def _choose_disposition(level: int, bed_type: str) -> str:
    roll = random.random()
    if level == 1:
        return "admit" if roll < 0.80 else "transfer"
    if level == 2:
        return "admit" if roll < 0.55 else "discharge"
    if level == 3:
        return "discharge" if roll < 0.80 else "admit"
    return "discharge"


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_events(
    days: int,
    scenario: ScenarioConfig,
    seed: int = 42,
    start_date: date | None = None,
) -> List[PatientEvent]:
    """Generate patient events for the given number of days.

    Args:
        days:       Number of days to simulate.
        scenario:   Capacity / slot configuration.
        seed:       Random seed for reproducibility.
        start_date: First day of simulation.  Defaults to the most recent Monday.
                    Must be a Monday (or explicitly overridden).

    Returns:
        Sorted list of PatientEvent records (chronological by arrival).
    """
    random.seed(seed)

    if start_date is None:
        start_date = _most_recent_monday()

    events: List[PatientEvent] = []
    patient_counter = 1

    for day_idx in range(days):
        current_date = start_date + timedelta(days=day_idx)
        weekday      = current_date.weekday()       # 0 = Mon, 6 = Sun
        dow_mult     = DOW_MULTIPLIERS[weekday]
        daily_mean   = BASE_DAILY_VOLUME * dow_mult
        daily_n      = int(max(60, random.gauss(daily_mean, daily_mean * 0.08)))

        # Arrival minutes within this day, weighted by diurnal pattern
        day_minutes = sorted(_sample_minute_in_day() for _ in range(daily_n))
        # track hourly lab/imaging requests to compute queue delays
        lab_by_hour:     Dict[int, int] = defaultdict(int)
        imaging_by_hour: Dict[int, int] = defaultdict(int)

        for arrival_minute in day_minutes:
            hour_bucket = int(arrival_minute // 60)
            urgency_level = _choose_urgency_level(hour_bucket)
            probs = _probabilities_by_level(urgency_level)

            # Arrival mode
            r = random.random()
            if r < probs["ambulance"]:
                arrival_mode = "ambulance"
            elif r < probs["ambulance"] + probs["walkin"]:
                arrival_mode = "walk-in"
            else:
                arrival_mode = "transfer"

            # Timestamps (no wait time — assessment starts right after triage)
            arrival_dt       = datetime.combine(current_date, time()) + timedelta(minutes=arrival_minute)
            triage_dt        = arrival_dt + timedelta(minutes=random.uniform(3, 10))
            assessment_start = triage_dt

            # Clinical flags
            lab_required     = random.random() < probs["lab"]
            imaging_required = random.random() < probs["imaging"]
            icu_needed       = random.random() < probs["icu_need"]

            if lab_required:
                lab_by_hour[hour_bucket] += 1
            if imaging_required:
                imaging_by_hour[hour_bucket] += 1

            # Bed type (probabilistic, no heap simulation)
            bed_type = "ICU" if (icu_needed and scenario.icu_beds > 0) else "ED"

            # Service time: log-normal base + lab/imaging queue delay
            service_min = _service_minutes(urgency_level)
            if lab_required:
                service_min += constraints.estimate_queue_delay_minutes(
                    lab_by_hour[hour_bucket], scenario.lab_slots_per_hour
                )
            if imaging_required:
                service_min += constraints.estimate_queue_delay_minutes(
                    imaging_by_hour[hour_bucket], scenario.imaging_slots_per_hour
                )

            discharge_dt = assessment_start + timedelta(minutes=service_min)
            los_minutes  = (discharge_dt - arrival_dt).total_seconds() / 60.0

            events.append(
                PatientEvent(
                    patient_id           = f"P{patient_counter:06d}",
                    arrival_ts           = arrival_dt.isoformat(),
                    urgency_level        = urgency_level,
                    arrival_mode         = arrival_mode,
                    triage_ts            = triage_dt.isoformat(),
                    assessment_start_ts  = assessment_start.isoformat(),
                    lab_required         = lab_required,
                    imaging_required     = imaging_required,
                    bed_assigned_type    = bed_type,
                    admit_decision       = _choose_disposition(urgency_level, bed_type),
                    discharge_ts         = discharge_dt.isoformat(),
                    waiting_time_minutes = 0.0,
                    los_minutes          = round(los_minutes, 2),
                )
            )
            patient_counter += 1

    return events


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def save_events_to_csv(events: Sequence[PatientEvent], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
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

    events = generate_events(
        n=n,
        scenario=scenario,
        seed=seed,
        start_date=kwargs.get("start_date"),
    )

    if inject_cases:
        benchmark_levels = [1, 2, 3, 4, 5]
        for idx, level in enumerate(benchmark_levels):
            if idx >= len(events):
                break
            events[idx].urgency_level = level

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
    start_monday = _most_recent_monday()
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
