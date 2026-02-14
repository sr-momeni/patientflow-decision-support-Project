"""CTAS 1/2/3 scorer with red-flag overrides."""

from dataclasses import dataclass
from typing import Dict


@dataclass
class TriageResult:
    ctas_level: int
    expected_target_min: int
    red_flag: bool


RED_FLAG_TARGET = {1: 0, 2: 15, 3: 30}


def is_red_flag(vitals: Dict) -> bool:
    return (
        vitals.get("loc", "").lower() in {"unresponsive", "gcs<8"}
        or vitals.get("spo2", 100) < 90
        or vitals.get("systolic_bp", 200) < 90
        or vitals.get("active_seizure", False)
        or vitals.get("hemorrhage_uncontrolled", False)
    )


def score_weighted(v: Dict) -> int:
    score = 0
    # vital instability
    hr = v.get("hr", 80)
    sbp = v.get("systolic_bp", 120)
    rr = v.get("rr", 16)
    temp = v.get("temp_c", 36.8)
    score += 2 if hr < 50 or hr > 130 else 1 if hr > 110 else 0
    score += 2 if sbp < 95 else 1 if sbp < 105 else 0
    score += 2 if rr < 10 or rr > 30 else 1 if rr > 24 else 0
    score += 1 if temp > 38.5 or temp < 35.0 else 0
    # pain + complaint
    pain = v.get("pain_score_0_10", 0)
    score += 2 if pain >= 8 else 1 if pain >= 5 else 0
    severe_complaints = {"chest_pain", "sob", "neuro_deficit"}
    score += 2 if v.get("complaint_category") in severe_complaints else 0
    # risk modifiers
    if v.get("age", 40) > 65:
        score += 1
    if v.get("risk_chronic"):
        score += 1
    if v.get("risk_immunocompromised"):
        score += 1
    if v.get("risk_pregnancy"):
        score += 1
    return score


def map_score_to_ctas(score: int) -> int:
    if score >= 6:
        return 1
    if score >= 3:
        return 2
    return 3


def triage_to_ctas(vitals: Dict) -> TriageResult:
    red = is_red_flag(vitals)
    if red:
        level = 1
    else:
        level = map_score_to_ctas(score_weighted(vitals))
    return TriageResult(ctas_level=level, expected_target_min=RED_FLAG_TARGET[level], red_flag=red)


# Benchmark patients
BENCHMARKS = {
    "A": {"loc": "unresponsive", "spo2": 85, "systolic_bp": 80, "complaint_category": "sob"},
    "B": {"hr": 120, "systolic_bp": 105, "rr": 24, "complaint_category": "chest_pain", "pain_score_0_10": 7},
    "C": {"hr": 88, "systolic_bp": 125, "rr": 16, "complaint_category": "ankle_pain", "pain_score_0_10": 3},
}
