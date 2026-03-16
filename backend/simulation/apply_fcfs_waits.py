"""
FCFS Wait-Time Simulation
=========================
Reads an existing patient CSV (generated with waiting_time_minutes = 0),
applies first-come-first-serve bed allocation using min-heaps, and
rewrites the timing columns in place.

Constraints respected:
  - ED beds: configurable (default 50)
  - ICU beds: configurable (default 20)
  - Bed assignment: ICU for patients flagged icu (Level 1 / pre-assigned ICU),
                   ED for all others.
  - FCFS order: strictly by arrival_ts.

Columns updated:
  - waiting_time_minutes   (was 0, now queue wait)
  - assessment_start_ts    (shifted right by wait)
  - discharge_ts           (shifted right by wait)
  - los_minutes            (wait + service duration)

Usage:
  python -m backend.simulation.apply_fcfs_waits                       # default paths
  python -m backend.simulation.apply_fcfs_waits --input data/patients_2500.csv --ed-beds 50 --icu-beds 20
"""

from __future__ import annotations

import argparse
import csv
import heapq
from datetime import datetime
from pathlib import Path
from typing import Dict, List


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_DT_FMT = "%Y-%m-%dT%H:%M:%S.%f"
_DT_FMT_SHORT = "%Y-%m-%dT%H:%M:%S"


def _parse_dt(s: str) -> datetime:
    try:
        return datetime.strptime(s, _DT_FMT)
    except ValueError:
        return datetime.strptime(s, _DT_FMT_SHORT)


def _fmt_dt(dt: datetime) -> str:
    return dt.isoformat()


# ---------------------------------------------------------------------------
# FCFS simulation
# ---------------------------------------------------------------------------

def apply_fcfs(
    rows: List[Dict[str, str]],
    ed_beds: int,
    icu_beds: int,
) -> List[Dict[str, str]]:
    """
    Process patients in arrival order.
    For each patient:
      1. Determine bed type (ICU if bed_assigned_type == 'ICU', else ED).
      2. Pop the earliest-free bed from the appropriate heap.
      3. The patient starts when the bed is free OR when they arrive,
         whichever is later.
      4. Push the new release time back onto the heap.
      5. Recompute timestamps and wait/LOS.
    """

    # Sort strictly by arrival timestamp
    rows = sorted(rows, key=lambda r: _parse_dt(r["arrival_ts"]))

    # Min-heaps: each entry is a float (minutes since epoch start)
    # Initialise with 0.0 — meaning all beds free at time 0
    ed_heap:  List[float] = [0.0] * ed_beds
    icu_heap: List[float] = [0.0] * icu_beds

    # Reference epoch = arrival of first patient (simplifies arithmetic)
    epoch = _parse_dt(rows[0]["arrival_ts"])

    def to_min(dt: datetime) -> float:
        return (dt - epoch).total_seconds() / 60.0

    def from_min(m: float) -> datetime:
        from datetime import timedelta
        return epoch + timedelta(minutes=m)

    heapq.heapify(ed_heap)
    heapq.heapify(icu_heap)

    updated: List[Dict[str, str]] = []

    for row in rows:
        arrival_dt    = _parse_dt(row["arrival_ts"])
        arrival_min   = to_min(arrival_dt)

        # Original service duration (was: los = 0 wait + service, so service = los)
        original_los  = float(row["los_minutes"])
        service_min   = original_los   # wait was 0 in original data

        bed_type = row.get("bed_assigned_type", "ED").strip().upper()
        use_icu  = (bed_type == "ICU") and (icu_beds > 0)

        if use_icu:
            earliest_free = heapq.heappop(icu_heap)
            start_min     = max(arrival_min, earliest_free)
            release_min   = start_min + service_min
            heapq.heappush(icu_heap, release_min)
        else:
            earliest_free = heapq.heappop(ed_heap)
            start_min     = max(arrival_min, earliest_free)
            release_min   = start_min + service_min
            heapq.heappush(ed_heap, release_min)

        wait_min     = start_min - arrival_min
        new_los      = wait_min + service_min

        assessment_dt = from_min(start_min)
        discharge_dt  = from_min(release_min)

        updated_row = dict(row)
        updated_row["waiting_time_minutes"] = f"{wait_min:.2f}"
        updated_row["assessment_start_ts"]  = _fmt_dt(assessment_dt)
        updated_row["discharge_ts"]         = _fmt_dt(discharge_dt)
        updated_row["los_minutes"]          = f"{new_los:.2f}"
        updated.append(updated_row)

    return updated


# ---------------------------------------------------------------------------
# Summary stats
# ---------------------------------------------------------------------------

def print_summary(rows: List[Dict[str, str]]) -> None:
    waits = [float(r["waiting_time_minutes"]) for r in rows]
    los   = [float(r["los_minutes"]) for r in rows]

    by_level: Dict[int, List[float]] = {}
    for r in rows:
        lvl = int(r["urgency_level"])
        by_level.setdefault(lvl, []).append(float(r["waiting_time_minutes"]))

    print(f"\nTotal patients : {len(rows)}")
    print(f"Avg wait       : {sum(waits)/len(waits):.1f} min")
    print(f"Max wait       : {max(waits):.1f} min")
    print(f"Avg LOS        : {sum(los)/len(los):.1f} min")
    print(f"Patients waited: {sum(1 for w in waits if w > 0)} "
          f"({sum(1 for w in waits if w > 0)/len(waits)*100:.1f}%)")
    print("\nAvg wait by urgency level:")
    for lvl in sorted(by_level):
        w_list = by_level[lvl]
        waited = sum(1 for w in w_list if w > 0)
        print(f"  Level {lvl}: avg {sum(w_list)/len(w_list):6.1f} min  "
              f"| {waited}/{len(w_list)} patients waited")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Apply FCFS wait times to patient CSV.")
    parser.add_argument(
        "--input", type=str, default="data/patients_2500.csv",
        help="Input CSV path",
    )
    parser.add_argument(
        "--output", type=str, default=None,
        help="Output CSV path (defaults to overwriting input)",
    )
    parser.add_argument("--ed-beds",  type=int, default=50)
    parser.add_argument("--icu-beds", type=int, default=20)
    args = parser.parse_args()

    input_path  = Path(args.input)
    output_path = Path(args.output) if args.output else input_path

    print(f"Reading  : {input_path}")
    with input_path.open(encoding="utf-8") as f:
        reader   = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows     = list(reader)

    print(f"Patients : {len(rows)}")
    print(f"ED beds  : {args.ed_beds}   ICU beds: {args.icu_beds}")
    print("Running FCFS simulation…")

    updated = apply_fcfs(rows, ed_beds=args.ed_beds, icu_beds=args.icu_beds)

    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated)

    print(f"Written  : {output_path}")
    print_summary(updated)


if __name__ == "__main__":
    main()
