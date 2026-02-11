"""Simple rule-based resource allocation agent."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple

from backend.optimization.congestion_scenarios import ScenarioConfig
from backend.optimization import constraints


@dataclass
class Recommendation:
    patient_id: str
    recommended_bed: str  # ED | ICU | waiting
    estimated_wait_minutes: float
    estimated_los_delta_minutes: float
    alerts: List[str]


def _baseline_wait(urgency: int) -> float:
    return {1: 15.0, 2: 45.0, 3: 90.0}.get(urgency, 60.0)


def _baseline_los(urgency: int) -> float:
    return {1: 360.0, 2: 180.0, 3: 90.0}.get(urgency, 120.0)


def _estimate_lab_imaging_delay(batch: Sequence[Dict[str, Any]], scenario: ScenarioConfig) -> Tuple[float, float]:
    lab_requests = sum(1 for p in batch if p.get("lab_required"))
    imaging_requests = sum(1 for p in batch if p.get("imaging_required"))
    lab_delay = constraints.estimate_queue_delay_minutes(lab_requests, scenario.lab_slots_per_hour)
    imaging_delay = constraints.estimate_queue_delay_minutes(imaging_requests, scenario.imaging_slots_per_hour)
    return lab_delay, imaging_delay


def allocate_resources(
    patient_batch: Sequence[Dict[str, Any]],
    scenario: ScenarioConfig,
) -> Tuple[List[Recommendation], List[str], Dict[str, float]]:
    """
    Produce bed/LOS recommendations and scenario-level alerts.

    patient_batch: list of dict-like items containing at least:
        patient_id, urgency_level, lab_required, imaging_required, bed_assigned_type (optional)
    """

    lab_delay, imaging_delay = _estimate_lab_imaging_delay(patient_batch, scenario)

    recommendations: List[Recommendation] = []
    waiting_queue_len = 0
    level3_waiting = False
    assigned_ed = 0
    assigned_icu = 0
    icu_queue_len = 0

    for p in patient_batch:
        pid = str(p.get("patient_id"))
        urgency = int(p.get("urgency_level", 2))
        bed_choice = "ED"
        patient_alerts: List[str] = []

        current_ed_util = constraints.utilization(assigned_ed, scenario.ed_beds)

        if urgency == 1:
            if scenario.icu_beds > 0 and assigned_icu < scenario.icu_beds:
                bed_choice = "ICU"
                assigned_icu += 1
            else:
                icu_queue_len += 1
                if assigned_ed < scenario.ed_beds:
                    bed_choice = "ED"
                    assigned_ed += 1
                    patient_alerts.append("ICU-waiting")
                else:
                    bed_choice = "waiting"
                    waiting_queue_len += 1
                    patient_alerts.append("ICU-waiting")
        elif urgency == 2:
            if assigned_ed < scenario.ed_beds:
                bed_choice = "ED"
                assigned_ed += 1
            else:
                bed_choice = "waiting"
                waiting_queue_len += 1
        else:  # Level 3
            if current_ed_util >= scenario.ed_near_full_threshold or assigned_ed >= scenario.ed_beds:
                bed_choice = "waiting"
                waiting_queue_len += 1
                level3_waiting = True
            else:
                bed_choice = "ED"
                assigned_ed += 1

        base_wait = _baseline_wait(urgency)
        congestion_factor = 1.0 + (0.5 if bed_choice == "waiting" else 0.0)
        est_wait = round(base_wait * congestion_factor, 2)

        base_los = _baseline_los(urgency)
        los_delta = lab_delay + imaging_delay
        if urgency == 1 and bed_choice != "ICU":
            los_delta += 60.0  # Level 1 waits longer when ICU blocked or unavailable
        est_los_delta = round(los_delta, 2)

        recommendations.append(
            Recommendation(
                patient_id=pid,
                recommended_bed=bed_choice,
                estimated_wait_minutes=est_wait,
                estimated_los_delta_minutes=est_los_delta,
                alerts=patient_alerts,
            )
        )

    ed_util = constraints.utilization(assigned_ed, scenario.ed_beds)
    icu_util = constraints.utilization(assigned_icu, scenario.icu_beds)
    overflow = waiting_queue_len

    alerts: List[str] = []
    ed_congestion = ed_util > 0.9 or waiting_queue_len > 20
    icu_bottleneck = icu_util > 0.9 or icu_queue_len > 5
    if ed_congestion:
        alerts.append("ED congestion")
    if icu_bottleneck:
        alerts.append("ICU bottleneck")
    if ed_congestion and level3_waiting:
        alerts.append("Deprioritized Level 3 due to ED crowding")

    metrics = {
        "ed_util": ed_util,
        "icu_util": icu_util,
        "waiting_queue": waiting_queue_len,
        "icu_queue": icu_queue_len,
        "assigned_ed": assigned_ed,
        "assigned_icu": assigned_icu,
        "overflow": overflow,
    }

    return recommendations, alerts, metrics
