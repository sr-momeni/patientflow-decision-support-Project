"""Rule-based allocator using CTAS levels 1/2/3."""

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from backend.optimization.congestion_scenarios import ScenarioConfig
from backend.optimization import constraints


@dataclass
class Recommendation:
    patient_id: str
    assigned_location: str  # ICU | ED | waiting
    est_wait_min: float
    alerts: List[str]


def allocate_resources(
    patient_batch: Sequence[Dict[str, Any]], scenario: ScenarioConfig
) -> Tuple[List[Recommendation], List[str], Dict[str, float]]:
    """
    Assign locations based on CTAS: ICU for level1 if possible, ED for 2/3 otherwise waiting.
    Adds simple wait estimates driven by overflow and ancillary queues.
    """

    assigned_ed = 0
    assigned_icu = 0
    waiting = 0
    icu_waitlist = 0
    recs: List[Recommendation] = []

    lab_requests = sum(1 for p in patient_batch if p.get("lab_required"))
    img_requests = sum(1 for p in patient_batch if p.get("imaging_required"))
    lab_delay = constraints.queue_delay_minutes(lab_requests, scenario.lab_slots_per_hour)
    img_delay = constraints.queue_delay_minutes(img_requests, scenario.imaging_slots_per_hour)

    for p in patient_batch:
        level = int(p.get("ctas_level", p.get("urgency_level", 3)))
        pid = p.get("patient_id", "unknown")
        alerts: List[str] = []
        location = "waiting"
        wait = 0.0

        if level == 1:
            if assigned_icu < scenario.icu_beds:
                location = "ICU"
                assigned_icu += 1
            elif assigned_ed < scenario.ed_beds:
                location = "ED"
                assigned_ed += 1
                icu_waitlist += 1
                alerts.append("ICU-waiting")
            else:
                waiting += 1
                icu_waitlist += 1
                alerts.append("ICU-waiting")
        elif level == 2:
            if assigned_ed < scenario.ed_beds:
                location = "ED"
                assigned_ed += 1
            else:
                waiting += 1
        else:  # level 3
            if assigned_ed < scenario.ed_beds:
                location = "ED"
                assigned_ed += 1
            else:
                waiting += 1

        overflow_factor = waiting / max(scenario.ed_beds, 1)
        wait = round(10 + overflow_factor * 30, 2)
        wait += lab_delay + img_delay

        recs.append(Recommendation(pid, location, wait, alerts))

    ed_util = constraints.utilization(assigned_ed, scenario.ed_beds)
    icu_util = constraints.utilization(assigned_icu, scenario.icu_beds)

    alerts: List[str] = []
    ed_congestion = ed_util > scenario.ed_util_alert or waiting > 0
    icu_bottleneck = icu_util > scenario.icu_util_alert or icu_waitlist > 0
    if ed_congestion:
        alerts.append("ED congestion")
    if icu_bottleneck:
        alerts.append("ICU bottleneck")
    if ed_congestion and any(
        r.assigned_location == "waiting" and int(patient_batch[idx].get("ctas_level", 3)) == 3
        for idx, r in enumerate(recs)
    ):
        alerts.append("Deprioritized Level 3 due to ED crowding")

    metrics = {
        "ed_util": ed_util,
        "icu_util": icu_util,
        "overflow": waiting,
        "icu_waitlist": icu_waitlist,
    }
    return recs, alerts, metrics
