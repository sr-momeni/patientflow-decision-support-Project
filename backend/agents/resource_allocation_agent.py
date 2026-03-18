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


def compute_priority_score(patient: Dict[str, Any], scenario: ScenarioConfig | None = None) -> float:
    """
    Compute a sortable priority score without changing the patient schema.

    Score components:
    - CTAS/urgency base score
    - accrued waiting time
    - optional risk modifier when present
    """

    urgency = int(patient.get("urgency_level", 3))
    base_score = {
        1: 100.0,
        2: 80.0,
        3: 60.0,
        4: 40.0,
        5: 20.0,
    }.get(urgency, 20.0)

    waiting_time = float(patient.get("waiting_time_minutes", 0.0) or 0.0)
    waiting_time_weight = 5.0
    if scenario and scenario.name == "ed_congestion":
        waiting_time_weight = 2.5

    risk_modifier = patient.get("risk_modifier", 0.0)
    if isinstance(risk_modifier, bool):
        risk_modifier = 10.0 if risk_modifier else 0.0
    elif isinstance(risk_modifier, (int, float)):
        risk_modifier = float(risk_modifier)
    else:
        risk_modifier = 0.0

    return base_score + (waiting_time / waiting_time_weight) + risk_modifier


def _baseline_wait(urgency: int) -> float:
    return {1: 15.0, 2: 45.0, 3: 90.0, 4: 120.0, 5: 180.0}.get(urgency, 60.0)


def _baseline_los(urgency: int) -> float:
    return {1: 360.0, 2: 180.0, 3: 90.0, 4: 60.0, 5: 45.0}.get(urgency, 120.0)


def _estimate_lab_imaging_delay(batch: Sequence[Dict[str, Any]], scenario: ScenarioConfig) -> Tuple[float, float]:
    lab_requests = sum(1 for p in batch if p.get("lab_required"))
    imaging_requests = sum(1 for p in batch if p.get("imaging_required"))
    lab_delay = constraints.estimate_queue_delay_minutes(lab_requests, scenario.lab_slots_per_hour)
    imaging_delay = constraints.estimate_queue_delay_minutes(imaging_requests, scenario.imaging_slots_per_hour)
    return lab_delay, imaging_delay


def allocate_resources(
    patient_batch: Sequence[Dict[str, Any]],
    scenario: ScenarioConfig,
) -> Tuple[List[Recommendation], List[str]]:
    """
    Produce bed/LOS recommendations and scenario-level alerts.

    patient_batch: list of dict-like items containing at least:
        patient_id, urgency_level, lab_required, imaging_required, bed_assigned_type (optional)
    """

    ed_in_use = sum(1 for p in patient_batch if p.get("bed_assigned_type") == "ED")
    icu_in_use = sum(1 for p in patient_batch if p.get("bed_assigned_type") == "ICU")
    ed_util = constraints.utilization(ed_in_use, scenario.ed_beds)
    icu_util = constraints.utilization(icu_in_use, scenario.icu_beds)

    lab_delay, imaging_delay = _estimate_lab_imaging_delay(patient_batch, scenario)

    alerts: List[str] = []
    if ed_util >= scenario.ed_near_full_threshold:
        alerts.append("ED congestion")
    if icu_util >= 0.9:
        alerts.append("ICU bottleneck")

    recommendations: List[Recommendation] = []
    prioritized_batch = sorted(
        patient_batch,
        key=lambda patient: compute_priority_score(patient, scenario),
        reverse=True,
    )

    for p in prioritized_batch:
        pid = str(p.get("patient_id"))
        urgency = int(p.get("urgency_level", 2))
        bed_choice = "ED"
        patient_alerts: List[str] = []

        if scenario.name == "icu_bottleneck" and urgency in (1, 2) and scenario.icu_beds > 0 and icu_util < 1.1:
            bed_choice = "ICU"
        elif urgency == 1 and scenario.icu_beds > 0 and icu_util < 1.1:
            bed_choice = "ICU"
        elif urgency == 1 and scenario.icu_beds == 0:
            bed_choice = "ED"
            patient_alerts.append("ICU-waiting")
        elif urgency in (3, 4, 5) and ed_util >= scenario.ed_near_full_threshold:
            bed_choice = "waiting"
            patient_alerts.append(f"Deprioritized Level {urgency} due to ED crowding")

        base_wait = _baseline_wait(urgency)
        congestion_factor = 1.0 + max(ed_util - 1.0, 0) + (0.5 if bed_choice == "waiting" else 0.0)
        est_wait = round(base_wait * congestion_factor, 2)

        base_los = _baseline_los(urgency)
        los_delta = lab_delay + imaging_delay
        if "ICU bottleneck" in alerts and urgency == 1:
            los_delta += 60.0  # Level 1 waits longer when ICU blocked
        est_los_delta = round(los_delta, 2)

        if patient_alerts:
            alerts.extend([a for a in patient_alerts if a not in alerts])

        recommendations.append(
            Recommendation(
                patient_id=pid,
                recommended_bed=bed_choice,
                estimated_wait_minutes=est_wait,
                estimated_los_delta_minutes=est_los_delta,
                alerts=patient_alerts,
            )
        )

    return recommendations, alerts
