"""Synthetic CTAS-ready generator with benchmark injections."""

import argparse
import csv
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Sequence

from backend.agents.urgency_scoring_agent import BENCHMARKS, TriageResult, triage_to_ctas
from backend.optimization.congestion_scenarios import ScenarioConfig, get_scenario

OUTPUT_COLUMNS = [
    "patient_id",
    "arrival_time_min",
    "arrival_mode",
    "age",
    "complaint_category",
    "pain_score_0_10",
    "hr",
    "systolic_bp",
    "rr",
    "spo2",
    "temp_c",
    "loc",
    "risk_chronic",
    "risk_immunocompromised",
    "risk_pregnancy",
    "red_flag",
    "ctas_level",
    "expected_target_min",
]


@dataclass
class PatientRecord:
    patient_id: str
    arrival_time_min: float
    arrival_mode: str
    age: int
    complaint_category: str
    pain_score_0_10: int
    hr: int
    systolic_bp: int
    rr: int
    spo2: int
    temp_c: float
    loc: str
    risk_chronic: bool
    risk_immunocompromised: bool
    risk_pregnancy: bool
    red_flag: bool
    ctas_level: int
    expected_target_min: int


TARGET_MIN = {1: 0, 2: 15, 3: 30}


def _sample_vitals() -> Dict:
    return {
        "age": random.randint(18, 90),
        "complaint_category": random.choice(["chest_pain", "sob", "abdominal_pain", "fever", "ankle_pain"]),
        "pain_score_0_10": random.randint(0, 10),
        "hr": random.randint(55, 140),
        "systolic_bp": random.randint(90, 160),
        "rr": random.randint(12, 30),
        "spo2": random.randint(88, 100),
        "temp_c": round(random.uniform(35.5, 39.5), 1),
        "loc": random.choice(["alert", "verbal", "unresponsive"]),
        "risk_chronic": random.random() < 0.25,
        "risk_immunocompromised": random.random() < 0.1,
        "risk_pregnancy": random.random() < 0.05,
    }


def _arrival_mode_for_level(level: int) -> str:
    if level == 1:
        return random.choices(["ambulance", "transfer", "walk-in"], weights=[0.8, 0.15, 0.05])[0]
    if level == 2:
        return random.choices(["ambulance", "walk-in"], weights=[0.3, 0.7])[0]
    return "walk-in"


def generate_patients(n: int, scenario: ScenarioConfig, seed: int, inject_cases: bool = True) -> List[PatientRecord]:
    """Generate reproducible patient rows aligned to CTAS 1/2/3."""

    random.seed(seed)
    records: List[PatientRecord] = []
    pid = 1

    def add_record(
        vitals: Dict,
        pid_value: int,
        fixed_ctas: int | None = None,
        arrival_time_min: float | None = None,
        arrival_mode: str | None = None,
    ) -> None:
        if fixed_ctas is not None:
            ctas_level = fixed_ctas
            red_flag = fixed_ctas == 1
            expected_target_min = TARGET_MIN[fixed_ctas]
        else:
            triage: TriageResult = triage_to_ctas(vitals)
            ctas_level = triage.ctas_level
            red_flag = triage.red_flag
            expected_target_min = triage.expected_target_min

        arrival_mode_val = arrival_mode or _arrival_mode_for_level(ctas_level)
        arrival_time_val = arrival_time_min if arrival_time_min is not None else random.uniform(0, 24 * 60)

        records.append(
            PatientRecord(
                patient_id=f"P{pid_value:05d}",
                arrival_time_min=arrival_time_val,
                arrival_mode=arrival_mode_val,
                red_flag=red_flag,
                ctas_level=ctas_level,
                expected_target_min=expected_target_min,
                **{k: vitals[k] for k in (
                    "age",
                    "complaint_category",
                    "pain_score_0_10",
                    "hr",
                    "systolic_bp",
                    "rr",
                    "spo2",
                    "temp_c",
                    "loc",
                    "risk_chronic",
                    "risk_immunocompromised",
                    "risk_pregnancy",
                )},
            )
        )

    if inject_cases:
        fixed_cases = [
            (
                1,
                {
                    "age": 64,
                    "complaint_category": "sob",
                    "pain_score_0_10": 2,
                    "hr": 128,
                    "systolic_bp": 82,
                    "rr": 30,
                    "spo2": 85,
                    "temp_c": 36.9,
                    "loc": "unresponsive",
                    "risk_chronic": True,
                    "risk_immunocompromised": False,
                    "risk_pregnancy": False,
                },
            ),
            (
                2,
                {
                    "age": 55,
                    "complaint_category": "chest_pain",
                    "pain_score_0_10": 7,
                    "hr": 110,
                    "systolic_bp": 120,
                    "rr": 20,
                    "spo2": 97,
                    "temp_c": 37.0,
                    "loc": "alert",
                    "risk_chronic": False,
                    "risk_immunocompromised": False,
                    "risk_pregnancy": False,
                },
            ),
            (
                3,
                {
                    "age": 32,
                    "complaint_category": "ankle_pain",
                    "pain_score_0_10": 3,
                    "hr": 82,
                    "systolic_bp": 124,
                    "rr": 16,
                    "spo2": 98,
                    "temp_c": 36.8,
                    "loc": "alert",
                    "risk_chronic": False,
                    "risk_immunocompromised": False,
                    "risk_pregnancy": False,
                },
            ),
        ]
        for idx, vitals in fixed_cases:
            if pid > n:
                break
            add_record(
                vitals,
                pid,
                fixed_ctas=idx,
                arrival_time_min=pid * 5.0,
                arrival_mode="ambulance" if idx == 1 else "walk-in",
            )
            pid += 1

    for _ in range(pid, n + 1):
        vitals = _sample_vitals()
        add_record(vitals, pid)
        pid += 1

    return records


def save_csv(records: Sequence[PatientRecord], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        for rec in records:
            writer.writerow(asdict(rec))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="normal")
    parser.add_argument("--n", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, default=Path("backend/data/raw/normal.csv"))
    args = parser.parse_args()

    scenario = get_scenario(args.scenario)
    records = generate_patients(args.n, scenario, seed=args.seed, inject_cases=True)
    save_csv(records, args.out)
    print(f"Wrote {len(records)} rows to {args.out}")


if __name__ == "__main__":
    main()
