"""Simple rule-based resource allocation agent."""

from __future__ import annotations
import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Sequence, Tuple, Optional
from openai import OpenAI

from backend.optimization.congestion_scenarios import ScenarioConfig
from backend.optimization import constraints

# Load API Key for the explainer
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ROOT_DIR = os.path.dirname(BACKEND_DIR)
_KEY_PATH = os.path.join(ROOT_DIR, "openAI_key.txt")

_API_KEY = None
if os.path.exists(_KEY_PATH):
    with open(_KEY_PATH, "r") as _f:
        _API_KEY = _f.read().strip()

client = OpenAI(api_key=_API_KEY) if _API_KEY else None


@dataclass
class Recommendation:
    patient_id: str
    recommended_bed: str  # ED | ICU | waiting
    estimated_wait_minutes: float
    estimated_los_delta_minutes: float
    alerts: List[str]
    decision_explanation: str = ""


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


class ResourceAllocationAgent:
    """Enhanced agent that allocates resources and explains decisions using AI."""

    def __init__(self, api_key: Optional[str] = None):
        if api_key:
            self.client = OpenAI(api_key=api_key)
        else:
            self.client = client # Use global client if initialized

    def allocate_resources(
        self,
        patient_batch: Sequence[Dict[str, Any]],
        scenario: ScenarioConfig,
        ed_reserved: int = 0,
        icu_reserved: int = 0
    ) -> Tuple[List[Recommendation], List[str]]:
        """
        Produce bed/LOS recommendations and scenario-level alerts.
        """
        ed_in_use = sum(1 for p in patient_batch if p.get("bed_assigned_type") == "ED")
        icu_in_use = sum(1 for p in patient_batch if p.get("bed_assigned_type") == "ICU")
        
        # Effective capacity accounts for reservations
        ed_effective_free = max(0, scenario.ed_beds - ed_in_use - ed_reserved)
        icu_effective_free = max(0, scenario.icu_beds - icu_in_use - icu_reserved)

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
            key=lambda p: compute_priority_score(p, scenario),
            reverse=True,
        )

        for p in prioritized_batch:
            pid = str(p.get("patient_id"))
            urgency = int(p.get("urgency_level", 2))
            bed_choice = "ED"
            patient_alerts: List[str] = []

            # Allocation Logic with Reservation Awareness
            if urgency == 1:
                if scenario.icu_beds > 0 and icu_util < 1.1:
                    bed_choice = "ICU"
                else:
                    bed_choice = "ED"
            elif urgency == 2:
                if scenario.icu_beds > 0 and icu_util < 0.9:
                    bed_choice = "ICU"
                else:
                    bed_choice = "ED"
            
            # Check availability (including reservations)
            if bed_choice == "ICU" and icu_effective_free <= 0 and urgency > 1:
                 # Need a bed but only reserved ones left and we aren't L1
                 bed_choice = "waiting"
                 patient_alerts.append("ICU-waiting (Reserved for Level 1)")
            elif bed_choice == "ED" and ed_effective_free <= 0 and urgency > 1:
                 bed_choice = "waiting"
                 patient_alerts.append("ED-waiting (Reserved for Level 1)")
            elif ed_in_use >= scenario.ed_beds and bed_choice == "ED":
                 bed_choice = "waiting"
                 patient_alerts.append("ED full")

            base_wait = _baseline_wait(urgency)
            congestion_factor = 1.0 + max(ed_util - 1.0, 0) + (0.5 if bed_choice == "waiting" else 0.0)
            est_wait = round(base_wait * congestion_factor, 2)

            base_los = _baseline_los(urgency)
            los_delta = lab_delay + imaging_delay
            est_los_delta = round(los_delta, 2)

            if patient_alerts:
                alerts.extend([a for a in patient_alerts if a not in alerts])

            # Generate Explanation (Rule-based first, then AI if available)
            explanation = self._generate_rule_explanation(
                urgency, bed_choice, ed_effective_free, icu_effective_free, ed_reserved, icu_reserved, scenario
            )
            
            # Optimization: Only call AI for patients we are actively recommending (not already admitted)
            is_new = p.get("bed_assigned_type") is None
            if self.client and is_new:
                ai_explanation = self._generate_ai_explanation(
                    urgency, bed_choice, ed_util, icu_util, ed_reserved, icu_reserved, scenario, explanation
                )
                if ai_explanation:
                    explanation = ai_explanation

            recommendations.append(
                Recommendation(
                    patient_id=pid,
                    recommended_bed=bed_choice,
                    estimated_wait_minutes=est_wait,
                    estimated_los_delta_minutes=est_los_delta,
                    alerts=patient_alerts,
                    decision_explanation=explanation
                )
            )

        return recommendations, alerts

    def _generate_rule_explanation(self, urgency, choice, ed_free, icu_free, ed_res, icu_res, scenario) -> str:
        if choice in ("ED", "ICU"):
            return f"Patient (CTAS {urgency}) assigned to {choice} bed."
        
        if (choice == "waiting"):
            if ed_res > 0 or icu_res > 0:
                return f"Wait required. Free beds are currently reserved for predicted high-urgency (Level 1) arrivals based on historical patterns."
            return "Wait required due to current capacity limits."
        return "Assessment in progress."

    def _generate_ai_explanation(self, urgency, choice, ed_util, icu_util, ed_res, icu_res, scenario, base_explanation) -> Optional[str]:
        try:
            prompt = f"""
            You are a senior hospital resource coordinator. Explain a triage decision to a patient.
            
            CONTEXT:
            - Patient CTAS Level: {urgency}
            - Recommendation: {choice}
            - ED Occupancy: {ed_util*100:.1f}%
            - Reserved Beds (for L1): ED={ed_res}, ICU={icu_res}
            - Scenario: {scenario.description}
            
            RULES:
            1. Use CTAS terminology (e.g., 'primary clinical urgency' or 'life-saving priority').
            2. If they are waiting despite free beds (Reserved > 0), explain that historical patterns for this time of day suggest a high probability of incoming life-saving emergencies.
            3. Be empathetic but professional.
            4. Keep it to 2 sentences.
            
            BASE REASON: {base_explanation}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "system", "content": "You provide clear, empathetic hospital staffing explanations."},
                          {"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except:
            return None

# Backward compatibility wrapper
def allocate_resources(patient_batch, scenario):
    agent = ResourceAllocationAgent()
    return agent.allocate_resources(patient_batch, scenario)
