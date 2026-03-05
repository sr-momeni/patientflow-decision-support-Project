"""Simple capacity and queue utility helpers for the MVP."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class CapacityState:
    ed_beds: int
    icu_beds: int
    physicians: int
    nurses: int
    lab_slots_per_hour: int
    imaging_slots_per_hour: int


def has_capacity(current: int, capacity: int) -> bool:
    """Return True when capacity is available (current load below capacity)."""

    return current < capacity


def utilization(current: int, capacity: int) -> float:
    """Compute utilization ratio, guarding divide-by-zero."""

    if capacity <= 0:
        return 1.0
    return min(current / capacity, 1.5)  # cap to avoid runaway


def estimate_queue_delay_minutes(requests_this_hour: int, slots_per_hour: int) -> float:
    """
    Crude delay approximation: if demand exceeds hourly slots, add linear delay.

    When requests <= slots, delay is zero. Otherwise each extra request adds
    one slot's worth of time evenly spread through the hour.
    """

    if slots_per_hour <= 0:
        return 60.0  # totally blocked
    overload = max(requests_this_hour - slots_per_hour, 0)
    if overload == 0:
        return 0.0
    return (overload / slots_per_hour) * 60.0


def estimate_bed_wait_minutes(occupied_until_minutes: float, arrival_minute: float) -> float:
    """Return minutes to wait for a bed; 0 when arrival is after release."""

    return max(occupied_until_minutes - arrival_minute, 0.0)


def rough_bed_utilization(total_patient_minutes: float, capacity: int, horizon_hours: float) -> Tuple[float, float]:
    """
    Approximate bed utilization and average occupancy.

    Returns (utilization_ratio, avg_occupied_beds).
    """

    if capacity <= 0 or horizon_hours <= 0:
        return 1.0, float(capacity)
    total_capacity_minutes = capacity * horizon_hours * 60.0
    util = min(total_patient_minutes / total_capacity_minutes, 1.5)
    avg_occupied = (util * capacity)
    return util, avg_occupied
