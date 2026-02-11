"""Synthetic ED patient-flow event generator (MVP)."""

from __future__ import annotations

import argparse
import csv
import heapq
import random
from collections import defaultdict, Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Sequence

from backend.optimization.congestion_scenarios import ScenarioConfig, get_scenario
from backend.optimization import constraints


RAW_DIR = Path(__file__).resolve().parent / "raw"


# Required output columns for tests/contract
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
    icu_wait_flag: bool = False  # internal flag, not part of required columns


def _choose_urgency_levels(n: int, scenario: ScenarioConfig) -> List[int]:
    rates = scenario.arrival_rates_per_hour
    total = sum(rates.values())
    weights = [rates[level] / total for level in (1, 2, 3)]
    return random.choices(population=[1, 2, 3], weights=weights, k=n)


def _arrival_minutes(n: int) -> List[float]:
    # Uniformly spread over 24 hours, then sorted to preserve temporal order
    return sorted(random.uniform(0, 24 * 60) for _ in range(n))


def _probabilities_by_level(level: int) -> Dict[str, float]:
    arrival_mode = {
        1: (0.7, 0.05, 0.25),  # ambulance, walk-in, transfer
        2: (0.3, 0.65, 0.05),
        3: (0.05, 0.9, 0.05),
    }
    lab = {1: 0.8, 2: 0.6, 3: 0.3}
    imaging = {1: 0.6, 2: 0.4, 3: 0.15}
    icu_need = {1: 0.7, 2: 0.15, 3: 0.0}
    return {
        "arrival_mode_ambulance": arrival_mode[level][0],
        "arrival_mode_walkin": arrival_mode[level][1],
        "arrival_mode_transfer": arrival_mode[level][2],
        "lab": lab[level],
        "imaging": imaging[level],
        "icu_need": icu_need[level],
    }


def _base_service_minutes(level: int) -> float:
    if level == 1:
        return random.uniform(240, 420)
    if level == 2:
        return random.uniform(120, 240)
    return random.uniform(60, 120)


def generate_events(
    n: int,
    scenario: ScenarioConfig,
    seed: int = 42,
    start_date: date | None = None,
) -> List[PatientEvent]:
    """Generate a reproducible list of PatientEvent records."""

    random.seed(seed)
    base_date = start_date or date.today()

    urgency_levels = _choose_urgency_levels(n, scenario)
    arrivals = _arrival_minutes(n)

    ed_heap: List[float] = []  # stores release times (minutes since midnight)
    icu_heap: List[float] = []
    lab_requests_by_hour: Dict[int, int] = defaultdict(int)
    imaging_requests_by_hour: Dict[int, int] = defaultdict(int)

    events: List[PatientEvent] = []

    for idx, (arrival_minute, urgency_level) in enumerate(zip(arrivals, urgency_levels), start=1):
        probs = _probabilities_by_level(urgency_level)
        mode_roll = random.random()
        if mode_roll < probs["arrival_mode_ambulance"]:
            arrival_mode = "ambulance"
        elif mode_roll < probs["arrival_mode_ambulance"] + probs["arrival_mode_walkin"]:
            arrival_mode = "walk-in"
        else:
            arrival_mode = "transfer"

        arrival_dt = datetime.combine(base_date, time()) + timedelta(minutes=arrival_minute)
        triage_dt = arrival_dt + timedelta(minutes=random.uniform(3, 10))

        hour_bucket = int(arrival_minute // 60)

        lab_required = random.random() < probs["lab"]
        imaging_required = random.random() < probs["imaging"]
        if lab_required:
            lab_requests_by_hour[hour_bucket] += 1
        if imaging_required:
            imaging_requests_by_hour[hour_bucket] += 1

        lab_delay = constraints.estimate_queue_delay_minutes(
            lab_requests_by_hour[hour_bucket], scenario.lab_slots_per_hour
        ) if lab_required else 0.0
        imaging_delay = constraints.estimate_queue_delay_minutes(
            imaging_requests_by_hour[hour_bucket], scenario.imaging_slots_per_hour
        ) if imaging_required else 0.0

        icu_needed = random.random() < probs["icu_need"]
        service_minutes = _base_service_minutes(urgency_level) + lab_delay + imaging_delay

        wait_minutes = 0.0
        bed_type = "ED"
        icu_wait_flag = False

        # ICU first if required and available
        if icu_needed and scenario.icu_beds > 0:
            while icu_heap and icu_heap[0] <= arrival_minute:
                heapq.heappop(icu_heap)
            if len(icu_heap) >= scenario.icu_beds:
                wait_minutes = icu_heap[0] - arrival_minute
            start_minute = arrival_minute + wait_minutes
            heapq.heappush(icu_heap, start_minute + service_minutes)
            bed_type = "ICU"
        else:
            # Either not ICU or no ICU capacity -> ED path
            while ed_heap and ed_heap[0] <= arrival_minute:
                heapq.heappop(ed_heap)
            if len(ed_heap) >= scenario.ed_beds:
                wait_minutes = ed_heap[0] - arrival_minute
                if icu_needed and scenario.icu_beds == 0:
                    icu_wait_flag = True
            start_minute = arrival_minute + wait_minutes
            bed_type = "ED"

        # Extra congestion penalty if ED near full and Level 3
        release_time = start_minute + service_minutes
        ed_util_pre = constraints.utilization(len(ed_heap), scenario.ed_beds)
        if bed_type == "ED" and urgency_level == 3 and ed_util_pre >= scenario.ed_near_full_threshold:
            wait_minutes += 20.0
            start_minute += 20.0
            release_time += 20.0

        if bed_type == "ICU":
            heapq.heappush(icu_heap, release_time)
        else:
            heapq.heappush(ed_heap, release_time)

        assessment_start_dt = datetime.combine(base_date, time()) + timedelta(minutes=start_minute)
        discharge_dt = datetime.combine(base_date, time()) + timedelta(minutes=start_minute + service_minutes)

        los_minutes = (discharge_dt - arrival_dt).total_seconds() / 60.0

        admit_decision = _choose_disposition(urgency_level, bed_type)

        events.append(
            PatientEvent(
                patient_id=f"P{idx:05d}",
                arrival_ts=arrival_dt.isoformat(),
                urgency_level=urgency_level,
                arrival_mode=arrival_mode,
                triage_ts=triage_dt.isoformat(),
                assessment_start_ts=assessment_start_dt.isoformat(),
                lab_required=lab_required,
                imaging_required=imaging_required,
                bed_assigned_type=bed_type,
                admit_decision=admit_decision,
                discharge_ts=discharge_dt.isoformat(),
                waiting_time_minutes=round(wait_minutes, 2),
                los_minutes=round(los_minutes, 2),
                icu_wait_flag=icu_wait_flag,
            )
        )

    return events


def _choose_disposition(level: int, bed_type: str) -> str:
    roll = random.random()
    if level == 1:
        return "admit" if roll < 0.8 else "transfer"
    if level == 2:
        if bed_type == "ICU":
            return "admit" if roll < 0.7 else "transfer"
        return "discharge" if roll < 0.5 else "admit"
    # level 3
    return "discharge" if roll < 0.85 else "admit"


def save_events_to_csv(events: Sequence[PatientEvent], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED_COLUMNS)
        writer.writeheader()
        for ev in events:
            row = asdict(ev)
            row.pop("icu_wait_flag", None)  # not required in CSV
            writer.writerow(row)


def summarize(events: Sequence[PatientEvent]) -> Dict[str, float]:
    waiting = [ev.waiting_time_minutes for ev in events]
    los = [ev.los_minutes for ev in events]
    by_urgency = defaultdict(list)
    for ev in events:
        by_urgency[ev.urgency_level].append(ev.waiting_time_minutes)

    summary = {
        "count": len(events),
        "avg_wait": round(sum(waiting) / len(waiting), 2) if events else 0.0,
        "avg_los": round(sum(los) / len(los), 2) if events else 0.0,
    }
    for level, waits in by_urgency.items():
        summary[f"avg_wait_level_{level}"] = round(sum(waits) / len(waits), 2)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Synthetic ED patient-flow generator.")
    parser.add_argument("--scenario", default="normal", help="Scenario name (normal|ed_congestion|icu_bottleneck)")
    parser.add_argument("--n", type=int, default=500, help="Number of patients to generate")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    parser.add_argument("--output", type=str, default=None, help="Optional output CSV path")
    args = parser.parse_args()

    scenario = get_scenario(args.scenario)
    events = generate_events(args.n, scenario, seed=args.seed)

    output_path = Path(args.output) if args.output else RAW_DIR / f"synthetic_{scenario.name}.csv"
    save_events_to_csv(events, output_path)

    summary = summarize(events)
    print(f"Generated {summary['count']} records for scenario '{scenario.name}' -> {output_path}")
    print(f"Average waiting time: {summary['avg_wait']} minutes")
    print(f"Average LOS: {summary['avg_los']} minutes")
    for level in (1, 2, 3):
        key = f"avg_wait_level_{level}"
        if key in summary:
            print(f"Level {level} avg wait: {summary[key]} minutes")


if __name__ == "__main__":
    main()
