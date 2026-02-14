"""Capacity and queue helpers for CTAS MVP."""

from dataclasses import dataclass
from typing import Tuple


@dataclass
class ResourceConstraints:
    ed_beds: int
    icu_beds: int
    physicians: int
    nurses: int
    lab_slots_per_hour: int
    imaging_slots_per_hour: int


def utilization(occupied: int, capacity: int) -> float:
    """
    Return utilization as occupied/capacity capped at 1.0 for reporting.
    Overflow should be tracked separately.
    """

    if capacity <= 0:
        return 1.0
    return min(occupied / capacity, 1.0)


def queue_delay_minutes(requests: int, slots_per_hour: int) -> float:
    """Linear delay when demand exceeds hourly slots; zero otherwise."""

    if slots_per_hour <= 0:
        return 60.0
    overload = max(requests - slots_per_hour, 0)
    if overload <= 0:
        return 0.0
    return (overload / slots_per_hour) * 60.0


def rough_los_minutes(base_minutes: float, wait: float, lab_delay: float, img_delay: float) -> float:
    """Simple LOS proxy: base care time plus waits and ancillary delays."""

    return base_minutes + wait + lab_delay + img_delay
