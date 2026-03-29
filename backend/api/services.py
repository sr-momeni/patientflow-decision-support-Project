from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.agents.resource_allocation_agent import allocate_resources
from backend.agents.urgency_scoring_agent import UrgencyScoringAgent
from backend.api.schemas import (
    AllocationPatient,
    AllocationResponse,
    BedAvailabilityResponse,
    BedDetailResponse,
    BedPatientInfo,
    BedSlot,
    BedUnitSummary,
    ClinicalData,
    ClinicalSummaryResponse,
    CTASResponse,
    FinalizedTriageResponse,
    MetricsResponse,
    PatientHistoryItem,
    TriagePipelineResponse,
)
from backend.chatbot.chatbot_agent import build_triage_reason, urgency_band
from backend.optimization.congestion_scenarios import get_scenario


CTAS_DESCRIPTIONS = {
    1: ("Resuscitation", "Immediate life-threatening - requires resuscitation now."),
    2: ("Emergent", "High risk - must be seen within 15 minutes."),
    3: ("Urgent", "Should be seen within 30 minutes."),
    4: ("Less Urgent", "Should be seen within 1 hour."),
    5: ("Non-Urgent", "Can wait up to 2 hours. Not immediately life-threatening."),
}

CTAS_COLORS = {1: "#c0392b", 2: "#e67e22", 3: "#f1c40f", 4: "#27ae60", 5: "#2980b9"}
VITAL_FIELDS = ("systolic_bp", "temperature", "heart_rate", "spo2", "respiratory_rate")
VITAL_LABELS = {
    "systolic_bp": "Systolic BP",
    "temperature": "Temperature",
    "heart_rate": "Heart rate",
    "spo2": "SpO2",
    "respiratory_rate": "Respiratory rate",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


def _split_values(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    text_value = str(value).replace(";", ",")
    return [item.strip() for item in text_value.split(",") if item.strip()]


def _coerce_optional_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    text_value = str(value).strip()
    if not text_value:
        return None
    try:
        return int(float(text_value))
    except (TypeError, ValueError):
        return None


def _coerce_optional_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    text_value = str(value).strip()
    if not text_value:
        return None
    try:
        return float(text_value)
    except (TypeError, ValueError):
        return None


def _dedupe(items: Sequence[str]) -> List[str]:
    result: List[str] = []
    seen = set()
    for item in items:
        cleaned = _to_text(item)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            result.append(cleaned)
    return result


def _normalize_patient_id(patient_id: Optional[str]) -> str:
    if patient_id and str(patient_id).strip():
        return str(patient_id).strip()
    return f"P{uuid.uuid4().hex[:8].upper()}"


def _normalize_red_flags(form_data: Dict[str, Any]) -> List[str]:
    red_flags = _split_values(form_data.get("red_flag_symptoms"))
    complaint = _to_text(form_data.get("presenting_complaint_Main_Concern")).lower()
    if "seizure" in complaint:
        red_flags.append("Seizure")
    return _dedupe(red_flags)


def _map_consciousness(status: Any, speech: Any) -> Optional[str]:
    status_text = _to_text(status).lower()
    speech_text = _to_text(speech).lower()
    if not status_text and not speech_text:
        return None
    if "unresponsive" in status_text or "loss of consciousness" in status_text:
        return "unresponsive"
    if "pain" in status_text:
        return "pain"
    if "confused" in status_text or "slurred" in speech_text or "verbal" in status_text:
        return "verbal"
    return "alert"


def _map_resp_distress(sob: Any, effort: Any, red_flags: Sequence[str]) -> Optional[str]:
    sob_text = _to_text(sob).lower()
    effort_text = _to_text(effort).lower()
    combined_flags = " ".join(str(flag).lower() for flag in red_flags)
    if not sob_text and not effort_text and not combined_flags:
        return None
    if "difficulty breathing" in combined_flags:
        return "severe"
    if "severe" in sob_text or "labored" in effort_text:
        return "severe"
    if "moderate" in sob_text:
        return "moderate"
    if "mild" in sob_text:
        return "mild"
    return "none"


def _normalize_history(form_data: Dict[str, Any]) -> List[str]:
    history: List[str] = []
    medical_history = _to_text(form_data.get("medical_history")).lower()
    immunocompromised = _to_text(form_data.get("immunocompromised_status")).lower()
    if medical_history and medical_history != "none":
        history.append("chronic_disease")
    if immunocompromised == "yes":
        history.append("immunocompromised")
    if "stroke" in medical_history or "slurred" in _to_text(form_data.get("cns_speech_clarity")).lower():
        history.append("stroke_history")
    return _dedupe(history)


def _missing_vitals(clinical_data: ClinicalData) -> List[str]:
    return [VITAL_LABELS[field_name] for field_name in VITAL_FIELDS if getattr(clinical_data, field_name) is None]


def _assessment_is_preliminary(clinical_data: ClinicalData) -> bool:
    return bool(_missing_vitals(clinical_data))


def _build_summary(form_data: Dict[str, Any], primary_complaint: str, age: Optional[int], resp_distress: Optional[str], clinical_data: ClinicalData) -> str:
    details: List[str] = []
    if primary_complaint:
        details.append(primary_complaint)
    onset = _to_text(form_data.get("symptom_onset"))
    if onset:
        details.append(f"{onset.lower()} onset")
    if age is not None:
        details.append(f"age {age}")
    if clinical_data.pain_score is not None:
        details.append(f"pain {clinical_data.pain_score}/10")
    if resp_distress:
        details.append(f"respiratory distress {resp_distress}")
    if not details:
        details.append("symptom-only assessment")

    summary = ", ".join(details[:4]).strip()
    if _assessment_is_preliminary(clinical_data):
        return f"{summary}. Preliminary assessment pending nurse vital signs."
    return f"{summary}."


def normalize_manual_triage_payload(form_data: Dict[str, Any]) -> ClinicalData:
    red_flags = _normalize_red_flags(form_data)
    age = _coerce_optional_int(form_data.get("age"))
    primary_complaint = _to_text(form_data.get("presenting_complaint_Main_Concern")) or "Undifferentiated complaint"
    consciousness = _map_consciousness(form_data.get("consciousness_status"), form_data.get("cns_speech_clarity"))
    resp_distress = _map_resp_distress(
        form_data.get("respiratory_sob_status"),
        form_data.get("breathing_effort"),
        red_flags,
    )
    history = _normalize_history(form_data)
    active_seizure = True if any("seizure" in flag.lower() for flag in red_flags) else None
    uncontrollable_hemorrhage = True if any("bleeding" in flag.lower() for flag in red_flags) else None

    clinical_data = ClinicalData(
        primary_complaint=primary_complaint,
        pain_score=_coerce_optional_int(form_data.get("Pain_assessment_pain_scale")),
        consciousness=consciousness,
        spo2=_coerce_optional_float(form_data.get("spo2")),
        heart_rate=_coerce_optional_int(form_data.get("heart_rate")),
        systolic_bp=_coerce_optional_int(form_data.get("systolic_bp")),
        respiratory_rate=_coerce_optional_int(form_data.get("respiratory_rate")),
        temperature=_coerce_optional_float(form_data.get("temperature")),
        active_seizure=active_seizure,
        uncontrollable_hemorrhage=uncontrollable_hemorrhage,
        resp_distress=resp_distress,
        age=age,
        history=history,
        summary="",
    )
    clinical_data.summary = _build_summary(form_data, primary_complaint, age, resp_distress, clinical_data)
    return clinical_data


def score_clinical_data(clinical_data: ClinicalData) -> CTASResponse:
    scorer = UrgencyScoringAgent()
    missing_vitals = _missing_vitals(clinical_data)
    level = scorer.calculate_urgency(clinical_data.model_dump())
    name, description = CTAS_DESCRIPTIONS.get(level, ("Unknown", ""))
    return CTASResponse(
        level=level,
        name=name,
        description=description,
        color=CTAS_COLORS.get(level, "#7f8c8d"),
        preliminary=bool(missing_vitals),
        missing_vitals=missing_vitals,
    )


def build_allocation_input(patient_id: str, clinical_data: ClinicalData, ctas: CTASResponse) -> AllocationPatient:
    complaint = clinical_data.primary_complaint.lower()
    history = set(clinical_data.history)
    lab_required = any(token in complaint for token in ("fever", "infection", "abdominal", "nausea")) or "chronic_disease" in history
    imaging_required = any(token in complaint for token in ("chest", "head", "injury", "trauma", "stroke", "abdomen"))
    preferred_bed = "ICU" if ctas.level == 1 or clinical_data.resp_distress == "severe" else "ED"
    risk_modifier = 5.0 if (clinical_data.age is not None and clinical_data.age >= 65) or "immunocompromised" in history else 0.0
    return AllocationPatient(
        patient_id=patient_id,
        urgency_level=ctas.level,
        waiting_time_minutes=0.0,
        lab_required=lab_required,
        imaging_required=imaging_required,
        bed_assigned_type=preferred_bed,
        risk_modifier=risk_modifier,
    )


def _load_active_queue(db: Session, scenario_name: str, exclude_patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
    query = text(
        """
        SELECT
            patient_id,
            urgency_level,
            COALESCE(estimated_wait_minutes, waiting_time_minutes, 0) AS waiting_time_minutes,
            COALESCE(lab_required, 0) AS lab_required,
            COALESCE(imaging_required, 0) AS imaging_required,
            COALESCE(NULLIF(recommended_bed, ''), NULLIF(bed_assigned_type, ''), 'ED') AS bed_assigned_type
        FROM patient_history
        WHERE (:scenario = '' OR scenario = :scenario)
          AND (discharge_ts IS NULL OR discharge_ts = '')
        ORDER BY id DESC
        LIMIT 100
        """
    )
    rows = db.execute(query, {"scenario": scenario_name}).mappings().all()
    queue: List[Dict[str, Any]] = []
    for row in rows:
        patient_id = _to_text(row.get("patient_id"))
        if not patient_id or patient_id == exclude_patient_id:
            continue
        queue.append(
            {
                "patient_id": patient_id,
                "urgency_level": int(row.get("urgency_level") or 3),
                "waiting_time_minutes": float(row.get("waiting_time_minutes") or 0.0),
                "lab_required": bool(row.get("lab_required") or 0),
                "imaging_required": bool(row.get("imaging_required") or 0),
                "bed_assigned_type": _to_text(row.get("bed_assigned_type")) or "ED",
            }
        )
    return queue


def _serialize_alerts(alerts: Sequence[str]) -> str:
    return json.dumps(_dedupe(alerts))


def _deserialize_alerts(raw_value: Any) -> List[str]:
    if raw_value is None:
        return []
    if isinstance(raw_value, list):
        return _dedupe(raw_value)
    text_value = str(raw_value).strip()
    if not text_value:
        return []
    try:
        parsed = json.loads(text_value)
        if isinstance(parsed, list):
            return _dedupe(parsed)
    except json.JSONDecodeError:
        pass
    return _dedupe(text_value.split(","))


def _bed_capacity(scenario_name: str, unit: str) -> int:
    scenario = get_scenario(scenario_name)
    return scenario.ed_beds if unit.upper() == "ED" else scenario.icu_beds


def _existing_active_patient_bed(db: Session, patient_id: str, scenario_name: str) -> Dict[str, Any]:
    row = db.execute(
        text(
            """
            SELECT id, bed_id, COALESCE(NULLIF(recommended_bed, ''), NULLIF(bed_assigned_type, ''), 'ED') AS bed_type
            FROM patient_history
            WHERE patient_id = :patient_id
              AND (:scenario = '' OR scenario = :scenario)
              AND (discharge_ts IS NULL OR discharge_ts = '')
              AND COALESCE(bed_status, 'occupied') <> 'cleaning'
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"patient_id": patient_id, "scenario": scenario_name},
    ).mappings().first()
    return dict(row) if row else {}


def _active_bed_ids(db: Session, scenario_name: str, unit: str) -> List[str]:
    rows = db.execute(
        text(
            """
            SELECT bed_id
            FROM patient_history
            WHERE (:scenario = '' OR scenario = :scenario)
              AND (discharge_ts IS NULL OR discharge_ts = '')
              AND COALESCE(NULLIF(recommended_bed, ''), NULLIF(bed_assigned_type, ''), 'ED') = :unit
              AND COALESCE(bed_status, 'occupied') IN ('occupied', 'reserved', 'cleaning')
              AND COALESCE(bed_id, '') <> ''
            ORDER BY id DESC
            """
        ),
        {"scenario": scenario_name, "unit": unit.upper()},
    ).mappings().all()
    return [_to_text(row.get("bed_id")) for row in rows if _to_text(row.get("bed_id"))]


def _allocate_bed_id(db: Session, scenario_name: str, unit: str) -> str:
    unit_name = unit.upper()
    total = _bed_capacity(scenario_name, unit_name)
    occupied_ids = set(_active_bed_ids(db, scenario_name, unit_name))
    for index in range(1, total + 1):
        candidate = f"{unit_name}-{index:02d}"
        if candidate not in occupied_ids:
            return candidate
    overflow_index = len([bed_id for bed_id in occupied_ids if bed_id.startswith(f"{unit_name}-OVERFLOW-")]) + 1
    return f"{unit_name}-OVERFLOW-{overflow_index}"


def _ensure_patient_exists(db: Session, patient_id: str, raw_form_data: Optional[Dict[str, Any]], source: str) -> None:
    exists = db.execute(text("SELECT 1 FROM patients WHERE p_id = :p_id LIMIT 1"), {"p_id": patient_id}).first()
    if exists:
        return

    name = _to_text((raw_form_data or {}).get("name")) or ("Chatbot Patient" if source == "chatbot" else "Unknown Patient")
    health_card = _to_text((raw_form_data or {}).get("health_card"))
    notes = _to_text((raw_form_data or {}).get("notes"))
    db.execute(
        text(
            """
            INSERT INTO patients (name, p_id, health_card, notes)
            VALUES (:name, :p_id, :health_card, :notes)
            """
        ),
        {
            "name": name,
            "p_id": patient_id,
            "health_card": health_card,
            "notes": notes,
        },
    )


def persist_triage_result(
    db: Session,
    patient_id: str,
    scenario_name: str,
    clinical_data: ClinicalData,
    ctas: CTASResponse,
    allocation: AllocationResponse,
    raw_form_data: Optional[Dict[str, Any]] = None,
    source: str = "manual",
) -> int:
    _ensure_patient_exists(db, patient_id, raw_form_data, source)

    form_data = raw_form_data or {}
    arrival_time = _to_text(form_data.get("arrival_time")) or _now_iso()
    assessment_start_ts = _now_iso()
    bed_choice = allocation.recommended_bed or "ED"
    los_minutes = float(allocation.estimated_wait_minutes + allocation.estimated_los_delta_minutes)
    clinical_summary = clinical_data.summary or "Triage intake recorded."
    if ctas.preliminary and ctas.missing_vitals:
        clinical_summary = f"{clinical_summary} Missing vitals: {', '.join(ctas.missing_vitals)}."

    existing_bed = _existing_active_patient_bed(db, patient_id, scenario_name)
    if _to_text(existing_bed.get("bed_id")) and _to_text(existing_bed.get("bed_type")).upper() == bed_choice.upper():
        bed_id = _to_text(existing_bed.get("bed_id"))
    else:
        bed_id = _allocate_bed_id(db, scenario_name, bed_choice)

    db.execute(
        text(
            """
            INSERT INTO triage_a (
                p_id, arrival_time, age, gender, presenting_complaint_Main_Concern,
                symptom_location, symptom_onset, Pain_assessment_pain_scale,
                pain_pattern, modifying_factors, red_flag_symptoms,
                cns_speech_clarity, consciousness_status, fever_infection,
                gi_symptoms, recent_sick_contact, respiratory_sob_status,
                cough_type, breathing_effort, palpitations, leg_swelling,
                recent_hospitalization, recent_surgery, immunocompromised_status,
                medications_allergies, drug_allergies, medical_history,
                clinical_summary, clinical_data_json, source
            ) VALUES (
                :p_id, :arrival_time, :age, :gender, :complaint,
                :location, :onset, :pain_scale,
                :pain_pattern, :modifying_factors, :red_flags,
                :speech_clarity, :consciousness_status, :fever_infection,
                :gi_symptoms, :recent_sick_contact, :respiratory_sob_status,
                :cough_type, :breathing_effort, :palpitations, :leg_swelling,
                :recent_hospitalization, :recent_surgery, :immunocompromised_status,
                :medications_allergies, :drug_allergies, :medical_history,
                :clinical_summary, :clinical_data_json, :source
            )
            """
        ),
        {
            "p_id": patient_id,
            "arrival_time": arrival_time,
            "age": _coerce_optional_int(form_data.get("age")) if form_data.get("age") is not None else clinical_data.age,
            "gender": _to_text(form_data.get("gender")),
            "complaint": _to_text(form_data.get("presenting_complaint_Main_Concern")) or clinical_data.primary_complaint,
            "location": _to_text(form_data.get("symptom_location")),
            "onset": _to_text(form_data.get("symptom_onset")),
            "pain_scale": _coerce_optional_int(form_data.get("Pain_assessment_pain_scale")) if form_data.get("Pain_assessment_pain_scale") is not None else clinical_data.pain_score,
            "pain_pattern": _to_text(form_data.get("pain_pattern")),
            "modifying_factors": _to_text(form_data.get("modifying_factors")),
            "red_flags": _to_text(form_data.get("red_flag_symptoms")),
            "speech_clarity": _to_text(form_data.get("cns_speech_clarity")),
            "consciousness_status": _to_text(form_data.get("consciousness_status")) or _to_text(clinical_data.consciousness),
            "fever_infection": _to_text(form_data.get("fever_infection")),
            "gi_symptoms": _to_text(form_data.get("gi_symptoms")),
            "recent_sick_contact": _to_text(form_data.get("recent_sick_contact")),
            "respiratory_sob_status": _to_text(form_data.get("respiratory_sob_status")) or _to_text(clinical_data.resp_distress),
            "cough_type": _to_text(form_data.get("cough_type")),
            "breathing_effort": _to_text(form_data.get("breathing_effort")),
            "palpitations": _to_text(form_data.get("palpitations")),
            "leg_swelling": _to_text(form_data.get("leg_swelling")),
            "recent_hospitalization": _to_text(form_data.get("recent_hospitalization")),
            "recent_surgery": _to_text(form_data.get("recent_surgery")),
            "immunocompromised_status": _to_text(form_data.get("immunocompromised_status")),
            "medications_allergies": _to_text(form_data.get("medications_allergies")),
            "drug_allergies": _to_text(form_data.get("drug_allergies")),
            "medical_history": _to_text(form_data.get("medical_history")) or ", ".join(clinical_data.history),
            "clinical_summary": clinical_summary,
            "clinical_data_json": json.dumps(clinical_data.model_dump()),
            "source": source,
        },
    )

    history_result = db.execute(
        text(
            """
            INSERT INTO patient_history (
                patient_id, scenario, urgency_level, ctas_name, arrival_mode,
                assessment_start_ts, lab_required, imaging_required, bed_assigned_type,
                recommended_bed, bed_id, bed_status, current_location,
                estimated_wait_minutes, estimated_los_delta_minutes,
                allocation_alerts, admit_decision, discharge_ts, waiting_time_minutes,
                los_minutes, clinical_summary
            ) VALUES (
                :patient_id, :scenario, :urgency_level, :ctas_name, :arrival_mode,
                :assessment_start_ts, :lab_required, :imaging_required, :bed_assigned_type,
                :recommended_bed, :bed_id, :bed_status, :current_location,
                :estimated_wait_minutes, :estimated_los_delta_minutes,
                :allocation_alerts, :admit_decision, :discharge_ts, :waiting_time_minutes,
                :los_minutes, :clinical_summary
            )
            """
        ),
        {
            "patient_id": patient_id,
            "scenario": scenario_name,
            "urgency_level": ctas.level,
            "ctas_name": ctas.name,
            "arrival_mode": "chatbot" if source == "chatbot" else ("nurse-finalization" if source == "nurse_finalization" else "walk-in"),
            "assessment_start_ts": assessment_start_ts,
            "lab_required": int(any(token in clinical_data.primary_complaint.lower() for token in ("fever", "infection", "abdominal")) or ("chronic_disease" in clinical_data.history)),
            "imaging_required": int(any(token in clinical_data.primary_complaint.lower() for token in ("chest", "head", "injury", "trauma", "stroke", "abdomen"))),
            "bed_assigned_type": bed_choice,
            "recommended_bed": allocation.recommended_bed,
            "bed_id": bed_id,
            "bed_status": "occupied",
            "current_location": bed_choice,
            "estimated_wait_minutes": allocation.estimated_wait_minutes,
            "estimated_los_delta_minutes": allocation.estimated_los_delta_minutes,
            "allocation_alerts": _serialize_alerts(allocation.alerts),
            "admit_decision": "pending",
            "discharge_ts": None,
            "waiting_time_minutes": allocation.estimated_wait_minutes,
            "los_minutes": los_minutes,
            "clinical_summary": clinical_summary,
        },
    )

    db.commit()
    return int(getattr(history_result, "lastrowid", 0) or 0)


def run_triage_pipeline(
    db: Session,
    patient_id: Optional[str],
    scenario_name: str,
    clinical_data: ClinicalData,
    raw_form_data: Optional[Dict[str, Any]] = None,
    source: str = "manual",
) -> TriagePipelineResponse:
    resolved_patient_id = _normalize_patient_id(patient_id)
    scenario = get_scenario(scenario_name)
    ctas = score_clinical_data(clinical_data)
    allocation_patient = build_allocation_input(resolved_patient_id, clinical_data, ctas)
    queue_snapshot = _load_active_queue(db, scenario.name, exclude_patient_id=resolved_patient_id)
    recommendations, alerts = allocate_resources(queue_snapshot + [allocation_patient.model_dump()], scenario)

    recommendation = next((item for item in recommendations if item.patient_id == resolved_patient_id), None)
    if recommendation is None:
        raise RuntimeError("Allocation recommendation could not be generated")

    allocation = AllocationResponse(
        recommended_bed=recommendation.recommended_bed,
        estimated_wait_minutes=recommendation.estimated_wait_minutes,
        estimated_los_delta_minutes=recommendation.estimated_los_delta_minutes,
        alerts=_dedupe(list(recommendation.alerts) + list(alerts)),
    )

    persist_triage_result(
        db=db,
        patient_id=resolved_patient_id,
        scenario_name=scenario.name,
        clinical_data=clinical_data,
        ctas=ctas,
        allocation=allocation,
        raw_form_data=raw_form_data,
        source=source,
    )

    return TriagePipelineResponse(
        patient_id=resolved_patient_id,
        scenario=scenario.name,
        clinical_data=clinical_data,
        ctas=ctas,
        allocation=allocation,
    )


def allocate_only(patient: AllocationPatient, scenario_name: str) -> AllocationResponse:
    scenario = get_scenario(scenario_name)
    recommendations, alerts = allocate_resources([patient.model_dump()], scenario)
    recommendation = recommendations[0]
    return AllocationResponse(
        recommended_bed=recommendation.recommended_bed,
        estimated_wait_minutes=recommendation.estimated_wait_minutes,
        estimated_los_delta_minutes=recommendation.estimated_los_delta_minutes,
        alerts=_dedupe(list(recommendation.alerts) + list(alerts)),
    )


def _latest_active_history_row(db: Session, patient_id: str, scenario_name: str = "") -> Dict[str, Any]:
    row = db.execute(
        text(
            """
            SELECT *
            FROM patient_history
            WHERE patient_id = :patient_id
              AND (:scenario = '' OR scenario = :scenario)
              AND (discharge_ts IS NULL OR discharge_ts = '')
              AND COALESCE(bed_status, 'occupied') <> 'cleaning'
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"patient_id": patient_id, "scenario": scenario_name},
    ).mappings().first()
    return dict(row) if row else {}


def _archive_previous_active_patient_rows(db: Session, patient_id: str, keep_id: int) -> None:
    if not keep_id:
        return
    db.execute(
        text(
            """
            UPDATE patient_history
            SET discharge_ts = :timestamp,
                admit_decision = CASE
                    WHEN COALESCE(admit_decision, '') = '' OR admit_decision = 'pending' THEN 'superseded'
                    ELSE admit_decision
                END
            WHERE patient_id = :patient_id
              AND id <> :keep_id
              AND (discharge_ts IS NULL OR discharge_ts = '')
              AND COALESCE(bed_status, 'occupied') <> 'cleaning'
            """
        ),
        {"timestamp": _now_iso(), "patient_id": patient_id, "keep_id": keep_id},
    )
    db.commit()


def _build_finalized_summary(clinical_data: ClinicalData, nurse_note: str = "") -> str:
    parts: List[str] = [clinical_data.primary_complaint]
    if clinical_data.age is not None:
        parts.append(f"age {clinical_data.age}")
    if clinical_data.pain_score is not None:
        parts.append(f"pain {clinical_data.pain_score}/10")

    vital_parts = []
    if clinical_data.systolic_bp is not None:
        vital_parts.append(f"SBP {clinical_data.systolic_bp}")
    if clinical_data.heart_rate is not None:
        vital_parts.append(f"HR {clinical_data.heart_rate}")
    if clinical_data.spo2 is not None:
        vital_parts.append(f"SpO2 {clinical_data.spo2:g}%")
    if clinical_data.respiratory_rate is not None:
        vital_parts.append(f"RR {clinical_data.respiratory_rate}")
    if clinical_data.temperature is not None:
        vital_parts.append(f"Temp {clinical_data.temperature:g} C")
    if vital_parts:
        parts.append(", ".join(vital_parts))

    summary = ". ".join(part.strip() for part in parts if part and str(part).strip()).strip()
    if nurse_note.strip():
        summary = f"{summary}. Nurse note: {nurse_note.strip()}"
    return summary + "."


def finalize_nurse_evaluation(
    db: Session,
    patient_id: str,
    nurse_vitals: Dict[str, Any],
    nurse_note: str = "",
    scenario_name: str = "normal",
) -> FinalizedTriageResponse:
    triage = db.execute(
        text("SELECT * FROM triage_a WHERE p_id = :p_id ORDER BY id DESC LIMIT 1"),
        {"p_id": patient_id},
    ).mappings().first()
    if not triage:
        raise ValueError("No preliminary triage record was found for this patient")

    clinical_payload = _parse_clinical_json(triage.get("clinical_data_json"))
    if clinical_payload:
        clinical_data = ClinicalData(**clinical_payload)
    else:
        clinical_data = ClinicalData(
            primary_complaint=_to_text(triage.get("presenting_complaint_Main_Concern")) or "Undifferentiated complaint",
            pain_score=_coerce_optional_int(triage.get("Pain_assessment_pain_scale")),
            consciousness=_to_text(triage.get("consciousness_status")) or None,
            resp_distress=_to_text(triage.get("respiratory_sob_status")) or None,
            age=_coerce_optional_int(triage.get("age")),
            history=_normalize_history(dict(triage)),
            summary=_to_text(triage.get("clinical_summary")),
        )

    merged_payload = clinical_data.model_dump()
    for field_name in VITAL_FIELDS:
        value = nurse_vitals.get(field_name)
        if value is not None:
            merged_payload[field_name] = value
    finalized_clinical_data = ClinicalData(**merged_payload)
    missing_vitals = _missing_vitals(finalized_clinical_data)
    if missing_vitals:
        raise ValueError(f"Final CTAS requires nurse validation for: {', '.join(missing_vitals)}")

    finalized_clinical_data.summary = _build_finalized_summary(finalized_clinical_data, nurse_note)
    raw_form_data = {
        "arrival_time": triage.get("arrival_time"),
        "age": finalized_clinical_data.age,
        "gender": triage.get("gender"),
        "presenting_complaint_Main_Concern": finalized_clinical_data.primary_complaint,
        "symptom_location": triage.get("symptom_location"),
        "symptom_onset": triage.get("symptom_onset"),
        "Pain_assessment_pain_scale": finalized_clinical_data.pain_score,
        "pain_pattern": triage.get("pain_pattern"),
        "modifying_factors": triage.get("modifying_factors"),
        "red_flag_symptoms": triage.get("red_flag_symptoms"),
        "cns_speech_clarity": triage.get("cns_speech_clarity"),
        "consciousness_status": finalized_clinical_data.consciousness,
        "fever_infection": triage.get("fever_infection"),
        "gi_symptoms": triage.get("gi_symptoms"),
        "recent_sick_contact": triage.get("recent_sick_contact"),
        "respiratory_sob_status": finalized_clinical_data.resp_distress,
        "cough_type": triage.get("cough_type"),
        "breathing_effort": triage.get("breathing_effort"),
        "palpitations": triage.get("palpitations"),
        "leg_swelling": triage.get("leg_swelling"),
        "recent_hospitalization": triage.get("recent_hospitalization"),
        "recent_surgery": triage.get("recent_surgery"),
        "immunocompromised_status": triage.get("immunocompromised_status"),
        "medications_allergies": triage.get("medications_allergies"),
        "drug_allergies": triage.get("drug_allergies"),
        "medical_history": triage.get("medical_history"),
        **{field_name: getattr(finalized_clinical_data, field_name) for field_name in VITAL_FIELDS},
    }
    if nurse_note.strip():
        raw_form_data["notes"] = nurse_note.strip()

    pipeline = run_triage_pipeline(
        db=db,
        patient_id=patient_id,
        scenario_name=scenario_name,
        clinical_data=finalized_clinical_data,
        raw_form_data=raw_form_data,
        source="nurse_finalization",
    )
    latest_row = _latest_active_history_row(db, patient_id, scenario_name)
    if latest_row:
        _archive_previous_active_patient_rows(db, patient_id, int(latest_row.get("id") or 0))

    return FinalizedTriageResponse(
        patient_id=pipeline.patient_id,
        scenario=pipeline.scenario,
        clinical_data=pipeline.clinical_data,
        ctas=pipeline.ctas,
        allocation=pipeline.allocation,
        urgency=urgency_band(pipeline.ctas.level),
        reason=build_triage_reason(pipeline.clinical_data.model_dump(), pipeline.ctas.level),
        summary=pipeline.clinical_data.summary,
    )


def _create_cleaning_marker(db: Session, scenario_name: str, unit: str, bed_id: str) -> None:
    if not bed_id:
        return
    marker_id = f"CLEANING-{bed_id}-{uuid.uuid4().hex[:6].upper()}"
    db.execute(
        text(
            """
            INSERT INTO patient_history (
                patient_id, scenario, urgency_level, ctas_name, arrival_mode,
                assessment_start_ts, lab_required, imaging_required, bed_assigned_type,
                recommended_bed, bed_id, bed_status, current_location,
                estimated_wait_minutes, estimated_los_delta_minutes,
                allocation_alerts, admit_decision, discharge_ts, waiting_time_minutes,
                los_minutes, clinical_summary
            ) VALUES (
                :patient_id, :scenario, 0, '', 'system',
                :assessment_start_ts, 0, 0, :unit,
                :unit, :bed_id, 'cleaning', :unit,
                0, 0,
                '[]', 'cleaning', NULL, 0,
                0, :clinical_summary
            )
            """
        ),
        {
            "patient_id": marker_id,
            "scenario": scenario_name,
            "assessment_start_ts": _now_iso(),
            "unit": unit,
            "bed_id": bed_id,
            "clinical_summary": f"{bed_id} cleaning in progress.",
        },
    )


def discharge_patient_from_bed(db: Session, patient_id: str, scenario_name: str = "normal") -> BedAvailabilityResponse:
    row = _latest_active_history_row(db, patient_id, scenario_name)
    if not row:
        raise ValueError("No active bed assignment was found for this patient")

    timestamp = _now_iso()
    db.execute(
        text(
            """
            UPDATE patient_history
            SET discharge_ts = :timestamp,
                admit_decision = 'discharged',
                current_location = 'Discharged'
            WHERE id = :row_id
            """
        ),
        {"timestamp": timestamp, "row_id": int(row.get("id") or 0)},
    )
    db.commit()
    return compute_bed_availability(db, scenario_name=scenario_name)


def transfer_patient_to_ward(db: Session, patient_id: str, ward: str, scenario_name: str = "normal") -> BedAvailabilityResponse:
    row = _latest_active_history_row(db, patient_id, scenario_name)
    if not row:
        raise ValueError("No active bed assignment was found for this patient")
    if not _to_text(ward):
        raise ValueError("A transfer ward is required")

    timestamp = _now_iso()
    db.execute(
        text(
            """
            UPDATE patient_history
            SET discharge_ts = :timestamp,
                admit_decision = 'transferred',
                current_location = :ward
            WHERE id = :row_id
            """
        ),
        {"timestamp": timestamp, "ward": ward, "row_id": int(row.get("id") or 0)},
    )
    db.commit()
    return compute_bed_availability(db, scenario_name=scenario_name)


def complete_bed_cleaning(db: Session, bed_id: str, scenario_name: str = "normal") -> BedAvailabilityResponse:
    row = db.execute(
        text(
            """
            SELECT id
            FROM patient_history
            WHERE bed_id = :bed_id
              AND (:scenario = '' OR scenario = :scenario)
              AND (discharge_ts IS NULL OR discharge_ts = '')
              AND COALESCE(bed_status, '') = 'cleaning'
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"bed_id": bed_id, "scenario": scenario_name},
    ).mappings().first()
    if not row:
        raise ValueError("No active cleaning record was found for this bed")

    db.execute(
        text(
            """
            UPDATE patient_history
            SET discharge_ts = :timestamp,
                admit_decision = 'available'
            WHERE id = :row_id
            """
        ),
        {"timestamp": _now_iso(), "row_id": int(row.get("id") or 0)},
    )
    db.commit()
    return compute_bed_availability(db, scenario_name=scenario_name)


def _bed_unit_from_id(bed_id: str) -> str:
    bed_text = _to_text(bed_id).upper()
    if bed_text.startswith("ICU"):
        return "ICU"
    return "ED"


def _active_bed_row_by_id(db: Session, bed_id: str, scenario_name: str = "") -> Dict[str, Any]:
    row = db.execute(
        text(
            """
            SELECT *
            FROM patient_history
            WHERE bed_id = :bed_id
              AND (:scenario = '' OR scenario = :scenario)
              AND (discharge_ts IS NULL OR discharge_ts = '')
            ORDER BY id DESC
            LIMIT 1
            """
        ),
        {"bed_id": bed_id, "scenario": scenario_name},
    ).mappings().first()
    return dict(row) if row else {}


def fetch_bed_detail(db: Session, bed_id: str, scenario_name: str = "normal") -> BedDetailResponse:
    normalized_bed_id = _to_text(bed_id)
    if not normalized_bed_id:
        raise ValueError("A bed ID is required")

    row = _active_bed_row_by_id(db, normalized_bed_id, scenario_name)
    fallback_location = _bed_unit_from_id(normalized_bed_id)
    if not row:
        return BedDetailResponse(
            bed_id=normalized_bed_id,
            bed_status="available",
            current_location=fallback_location,
            patient=None,
        )

    bed_status = (_to_text(row.get("bed_status")) or "occupied").lower()
    if bed_status not in {"available", "occupied", "reserved", "cleaning"}:
        bed_status = "occupied"
    current_location = _to_text(row.get("current_location")) or fallback_location
    patient_id = _to_text(row.get("patient_id"))

    patient = None
    if bed_status == "occupied" and patient_id and not patient_id.startswith("CLEANING-"):
        summary = fetch_clinical_summary(db, patient_id)
        patient = BedPatientInfo(
            patient_id=patient_id,
            ctas_level=summary.ctas_level,
            urgency=summary.urgency,
            summary=summary.summary,
            wait_time=summary.estimated_wait_minutes,
            systolic_bp=summary.systolic_bp,
            temperature=summary.temperature,
            heart_rate=summary.heart_rate,
            spo2=summary.spo2,
            respiratory_rate=summary.respiratory_rate,
        )

    return BedDetailResponse(
        bed_id=normalized_bed_id,
        bed_status=bed_status.capitalize(),
        current_location=current_location,
        patient=patient,
    )


def send_patient_to_service(db: Session, patient_id: str, service: str, scenario_name: str = "normal") -> BedDetailResponse:
    service_name = _to_text(service).lower()
    if service_name not in {"lab", "imaging"}:
        raise ValueError("Service must be 'lab' or 'imaging'")

    row = _latest_active_history_row(db, patient_id, scenario_name)
    if not row:
        raise ValueError("No active patient assignment was found for this patient")

    db.execute(
        text(
            """
            UPDATE patient_history
            SET current_location = :service
            WHERE id = :row_id
            """
        ),
        {"service": service_name, "row_id": int(row.get("id") or 0)},
    )
    db.commit()
    return fetch_bed_detail(db, _to_text(row.get("bed_id")), scenario_name=scenario_name)


def update_patient_record(
    db: Session,
    patient_id: str,
    symptoms: str = "",
    pain_scale: Optional[int] = None,
    notes: str = "",
    nurse_vitals: Optional[Dict[str, Any]] = None,
    scenario_name: str = "normal",
) -> ClinicalSummaryResponse:
    triage = db.execute(
        text("SELECT * FROM triage_a WHERE p_id = :p_id ORDER BY id DESC LIMIT 1"),
        {"p_id": patient_id},
    ).mappings().first()
    if not triage:
        raise ValueError("No clinical record was found for this patient")

    clinical_payload = _parse_clinical_json(triage.get("clinical_data_json"))
    if clinical_payload:
        clinical_data = ClinicalData(**clinical_payload)
    else:
        clinical_data = ClinicalData(
            primary_complaint=_to_text(triage.get("presenting_complaint_Main_Concern")) or "Undifferentiated complaint",
            pain_score=_coerce_optional_int(triage.get("Pain_assessment_pain_scale")),
            consciousness=_to_text(triage.get("consciousness_status")) or None,
            resp_distress=_to_text(triage.get("respiratory_sob_status")) or None,
            age=_coerce_optional_int(triage.get("age")),
            history=_normalize_history(dict(triage)),
            summary=_to_text(triage.get("clinical_summary")),
        )

    merged_payload = clinical_data.model_dump()
    if _to_text(symptoms):
        merged_payload["primary_complaint"] = _to_text(symptoms)
    if pain_scale is not None:
        merged_payload["pain_score"] = pain_scale

    vitals_payload = nurse_vitals or {}
    for field_name in VITAL_FIELDS:
        if vitals_payload.get(field_name) is not None:
            merged_payload[field_name] = vitals_payload.get(field_name)

    updated_clinical_data = ClinicalData(**merged_payload)
    if _missing_vitals(updated_clinical_data):
        updated_clinical_data.summary = f"{updated_clinical_data.primary_complaint}. Preliminary assessment pending nurse vital signs."
    else:
        updated_clinical_data.summary = _build_finalized_summary(updated_clinical_data)

    raw_form_data = {
        "arrival_time": triage.get("arrival_time"),
        "age": updated_clinical_data.age,
        "gender": triage.get("gender"),
        "presenting_complaint_Main_Concern": updated_clinical_data.primary_complaint,
        "symptom_location": triage.get("symptom_location"),
        "symptom_onset": triage.get("symptom_onset"),
        "Pain_assessment_pain_scale": updated_clinical_data.pain_score,
        "pain_pattern": triage.get("pain_pattern"),
        "modifying_factors": triage.get("modifying_factors"),
        "red_flag_symptoms": triage.get("red_flag_symptoms"),
        "cns_speech_clarity": triage.get("cns_speech_clarity"),
        "consciousness_status": updated_clinical_data.consciousness,
        "fever_infection": triage.get("fever_infection"),
        "gi_symptoms": triage.get("gi_symptoms"),
        "recent_sick_contact": triage.get("recent_sick_contact"),
        "respiratory_sob_status": updated_clinical_data.resp_distress,
        "cough_type": triage.get("cough_type"),
        "breathing_effort": triage.get("breathing_effort"),
        "palpitations": triage.get("palpitations"),
        "leg_swelling": triage.get("leg_swelling"),
        "recent_hospitalization": triage.get("recent_hospitalization"),
        "recent_surgery": triage.get("recent_surgery"),
        "immunocompromised_status": triage.get("immunocompromised_status"),
        "medications_allergies": triage.get("medications_allergies"),
        "drug_allergies": triage.get("drug_allergies"),
        "medical_history": triage.get("medical_history"),
        **{field_name: getattr(updated_clinical_data, field_name) for field_name in VITAL_FIELDS},
    }

    db.execute(
        text(
            """
            UPDATE patients
            SET notes = :notes
            WHERE p_id = :p_id
            """
        ),
        {"notes": notes, "p_id": patient_id},
    )

    pipeline = run_triage_pipeline(
        db=db,
        patient_id=patient_id,
        scenario_name=scenario_name,
        clinical_data=updated_clinical_data,
        raw_form_data=raw_form_data,
        source="patient_update",
    )
    latest_row = _latest_active_history_row(db, patient_id, scenario_name)
    if latest_row:
        _archive_previous_active_patient_rows(db, patient_id, int(latest_row.get("id") or 0))

    return fetch_clinical_summary(db, pipeline.patient_id)


def compute_live_metrics(db: Session, scenario_name: str = "normal") -> MetricsResponse:
    scenario = get_scenario(scenario_name)
    rows = db.execute(
        text(
            """
            SELECT
                urgency_level,
                recommended_bed,
                bed_assigned_type,
                bed_status,
                estimated_wait_minutes,
                waiting_time_minutes,
                estimated_los_delta_minutes,
                los_minutes,
                discharge_ts
            FROM patient_history
            WHERE (:scenario = '' OR scenario = :scenario)
              AND COALESCE(bed_status, 'occupied') <> 'cleaning'
            ORDER BY id DESC
            LIMIT 500
            """
        ),
        {"scenario": scenario.name},
    ).mappings().all()

    active_rows = [row for row in rows if not _to_text(row.get("discharge_ts"))]
    relevant_rows = active_rows or rows
    if not relevant_rows:
        return MetricsResponse(
            average_waiting_time=0.0,
            average_los=0.0,
            ed_bed_utilization=0.0,
            icu_bed_utilization=0.0,
            queue_length=0,
            high_urgency_count=0,
        )

    wait_values = [float(row.get("estimated_wait_minutes") or row.get("waiting_time_minutes") or 0.0) for row in relevant_rows]
    los_values = [
        float(row.get("los_minutes") or 0.0)
        or float((row.get("estimated_wait_minutes") or 0.0) + (row.get("estimated_los_delta_minutes") or 0.0))
        for row in relevant_rows
    ]

    ed_count = 0
    icu_count = 0
    for row in active_rows:
        bed_type = (_to_text(row.get("recommended_bed")) or _to_text(row.get("bed_assigned_type")) or "ED").upper()
        if bed_type == "ICU":
            icu_count += 1
        elif bed_type == "ED":
            ed_count += 1

    high_urgency_count = sum(1 for row in active_rows if int(row.get("urgency_level") or 0) in (1, 2))
    queue_length = len(active_rows)

    return MetricsResponse(
        average_waiting_time=round(sum(wait_values) / len(wait_values), 2),
        average_los=round(sum(los_values) / len(los_values), 2),
        ed_bed_utilization=round(ed_count / scenario.ed_beds, 4) if scenario.ed_beds else 0.0,
        icu_bed_utilization=round(icu_count / scenario.icu_beds, 4) if scenario.icu_beds else 0.0,
        queue_length=queue_length,
        high_urgency_count=high_urgency_count,
    )


def fetch_patient_history(db: Session, limit: int = 20, scenario_name: str = "") -> List[PatientHistoryItem]:
    rows = db.execute(
        text(
            """
            SELECT
                patient_id,
                COALESCE(scenario, '') AS scenario,
                COALESCE(urgency_level, 0) AS urgency_level,
                COALESCE(ctas_name, '') AS ctas_name,
                COALESCE(arrival_mode, '') AS arrival_mode,
                COALESCE(assessment_start_ts, '') AS assessment_start_ts,
                COALESCE(lab_required, 0) AS lab_required,
                COALESCE(imaging_required, 0) AS imaging_required,
                COALESCE(bed_assigned_type, '') AS bed_assigned_type,
                COALESCE(recommended_bed, '') AS recommended_bed,
                COALESCE(bed_id, '') AS bed_id,
                COALESCE(bed_status, 'occupied') AS bed_status,
                COALESCE(current_location, '') AS current_location,
                COALESCE(estimated_wait_minutes, 0) AS estimated_wait_minutes,
                COALESCE(estimated_los_delta_minutes, 0) AS estimated_los_delta_minutes,
                COALESCE(allocation_alerts, '') AS allocation_alerts,
                COALESCE(admit_decision, '') AS admit_decision,
                discharge_ts,
                COALESCE(waiting_time_minutes, 0) AS waiting_time_minutes,
                COALESCE(los_minutes, 0) AS los_minutes,
                COALESCE(clinical_summary, '') AS clinical_summary
            FROM patient_history
            WHERE (:scenario = '' OR scenario = :scenario)
              AND COALESCE(bed_status, 'occupied') <> 'cleaning'
            ORDER BY id DESC
            LIMIT :limit_value
            """
        ),
        {"scenario": scenario_name, "limit_value": int(limit)},
    ).mappings().all()

    return [
        PatientHistoryItem(
            patient_id=_to_text(row.get("patient_id")),
            scenario=_to_text(row.get("scenario")) or "normal",
            urgency_level=int(row.get("urgency_level") or 0),
            ctas_name=_to_text(row.get("ctas_name")),
            arrival_mode=_to_text(row.get("arrival_mode")),
            assessment_start_ts=_to_text(row.get("assessment_start_ts")),
            lab_required=bool(row.get("lab_required") or 0),
            imaging_required=bool(row.get("imaging_required") or 0),
            bed_assigned_type=_to_text(row.get("bed_assigned_type")),
            recommended_bed=_to_text(row.get("recommended_bed")),
            bed_id=_to_text(row.get("bed_id")),
            bed_status=_to_text(row.get("bed_status")) or "occupied",
            current_location=_to_text(row.get("current_location")),
            estimated_wait_minutes=float(row.get("estimated_wait_minutes") or 0.0),
            estimated_los_delta_minutes=float(row.get("estimated_los_delta_minutes") or 0.0),
            allocation_alerts=_deserialize_alerts(row.get("allocation_alerts")),
            admit_decision=_to_text(row.get("admit_decision")),
            discharge_ts=_to_text(row.get("discharge_ts")) or None,
            waiting_time_minutes=float(row.get("waiting_time_minutes") or 0.0),
            los_minutes=float(row.get("los_minutes") or 0.0),
            clinical_summary=_to_text(row.get("clinical_summary")),
        )
        for row in rows
    ]


def _urgency_label(ctas_level: int) -> str:
    if ctas_level in (1, 2):
        return "HIGH"
    if ctas_level == 3:
        return "MEDIUM"
    return "LOW"


def _parse_clinical_json(raw_value: Any) -> Dict[str, Any]:
    text_value = _to_text(raw_value)
    if not text_value:
        return {}
    try:
        parsed = json.loads(text_value)
        return parsed if isinstance(parsed, dict) else {}
    except json.JSONDecodeError:
        return {}


def fetch_clinical_summary(db: Session, patient_id: str) -> ClinicalSummaryResponse:
    patient = db.execute(
        text("SELECT name, notes FROM patients WHERE p_id = :p_id ORDER BY id DESC LIMIT 1"),
        {"p_id": patient_id},
    ).mappings().first() or {}

    triage = db.execute(
        text("SELECT * FROM triage_a WHERE p_id = :p_id ORDER BY id DESC LIMIT 1"),
        {"p_id": patient_id},
    ).mappings().first() or {}

    history = db.execute(
        text("SELECT * FROM patient_history WHERE patient_id = :p_id ORDER BY id DESC LIMIT 1"),
        {"p_id": patient_id},
    ).mappings().first() or {}

    clinical_payload = _parse_clinical_json(triage.get("clinical_data_json"))
    clinical_data = ClinicalData(**clinical_payload) if clinical_payload else ClinicalData(primary_complaint=_to_text(triage.get("presenting_complaint_Main_Concern")) or "Undifferentiated complaint")
    scored = score_clinical_data(clinical_data)

    ctas_level = int(history.get("urgency_level") or scored.level or 0)
    ctas_name = _to_text(history.get("ctas_name")) or scored.name
    ctas_description = CTAS_DESCRIPTIONS.get(ctas_level, ("Unknown", ""))[1]

    return ClinicalSummaryResponse(
        patient_id=patient_id,
        name=_to_text(patient.get("name")) or "Unknown",
        notes=_to_text(patient.get("notes")),
        age=_coerce_optional_int(triage.get("age")) if triage.get("age") is not None else clinical_data.age,
        gender=_to_text(triage.get("gender")),
        arrival_time=_to_text(triage.get("arrival_time")),
        chief_complaint=_to_text(triage.get("presenting_complaint_Main_Concern")) or clinical_data.primary_complaint,
        location=_to_text(triage.get("symptom_location")),
        onset=_to_text(triage.get("symptom_onset")),
        pain_scale=_coerce_optional_int(triage.get("Pain_assessment_pain_scale")) if triage.get("Pain_assessment_pain_scale") is not None else clinical_data.pain_score,
        pattern=_to_text(triage.get("pain_pattern")),
        modifying_factors=_to_text(triage.get("modifying_factors")),
        neurologic=_to_text(triage.get("cns_speech_clarity")),
        consciousness_status=_to_text(triage.get("consciousness_status")) or _to_text(clinical_data.consciousness),
        cough=_to_text(triage.get("cough_type")),
        breathing_effort=_to_text(triage.get("breathing_effort")),
        fever=_to_text(triage.get("fever_infection")),
        gi_symptoms=_to_text(triage.get("gi_symptoms")),
        recent=_to_text(triage.get("recent_sick_contact")),
        respiratory=_to_text(triage.get("respiratory_sob_status")) or _to_text(clinical_data.resp_distress),
        red_flag_symptoms=_to_text(triage.get("red_flag_symptoms")),
        palpitations=_to_text(triage.get("palpitations")),
        leg_swelling=_to_text(triage.get("leg_swelling")),
        medications_allergies=_to_text(triage.get("medications_allergies")),
        medical_history=_to_text(triage.get("medical_history")),
        recent_hospitalization=_to_text(triage.get("recent_hospitalization")),
        recent_surgery=_to_text(triage.get("recent_surgery")),
        immunocompromised=_to_text(triage.get("immunocompromised_status")),
        drug=_to_text(triage.get("drug_allergies")),
        systolic_bp=clinical_data.systolic_bp,
        temperature=clinical_data.temperature,
        heart_rate=clinical_data.heart_rate,
        spo2=clinical_data.spo2,
        respiratory_rate=clinical_data.respiratory_rate,
        ctas_level=ctas_level,
        ctas_name=ctas_name or "Unknown",
        ctas_description=ctas_description,
        urgency=_urgency_label(ctas_level),
        preliminary=scored.preliminary,
        missing_vitals=scored.missing_vitals,
        recommended_bed=_to_text(history.get("recommended_bed")) or _to_text(history.get("bed_assigned_type")),
        current_location=_to_text(history.get("current_location")) or _to_text(history.get("recommended_bed")) or _to_text(history.get("bed_assigned_type")),
        estimated_wait_minutes=float(history.get("estimated_wait_minutes") or 0.0),
        estimated_los_delta_minutes=float(history.get("estimated_los_delta_minutes") or 0.0),
        allocation_alerts=_deserialize_alerts(history.get("allocation_alerts")),
        summary=_to_text(history.get("clinical_summary")) or _to_text(triage.get("clinical_summary")),
    )


def _load_bed_rows(db: Session, scenario_name: str) -> List[Dict[str, Any]]:
    rows = db.execute(
        text(
            """
            SELECT
                patient_id,
                urgency_level,
                ctas_name,
                COALESCE(NULLIF(recommended_bed, ''), NULLIF(bed_assigned_type, ''), 'ED') AS bed_type,
                COALESCE(clinical_summary, '') AS clinical_summary,
                COALESCE(bed_id, '') AS bed_id,
                COALESCE(bed_status, 'occupied') AS bed_status,
                COALESCE(current_location, '') AS current_location,
                COALESCE(estimated_wait_minutes, 0) AS estimated_wait_minutes,
                COALESCE(allocation_alerts, '') AS allocation_alerts
            FROM patient_history
            WHERE (:scenario = '' OR scenario = :scenario)
              AND (discharge_ts IS NULL OR discharge_ts = '')
              AND COALESCE(bed_id, '') <> ''
            ORDER BY id DESC
            LIMIT 500
            """
        ),
        {"scenario": scenario_name},
    ).mappings().all()
    return [dict(row) for row in rows]


def _build_unit_beds(unit: str, total: int, rows: List[Dict[str, Any]]) -> BedUnitSummary:
    active_by_bed: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        bed_id = _to_text(row.get("bed_id"))
        if not bed_id or bed_id in active_by_bed:
            continue
        active_by_bed[bed_id] = row

    beds: List[BedSlot] = []
    occupied_count = 0
    reserved_count = 0
    cleaning_count = 0
    available_count = 0

    for index in range(1, total + 1):
        bed_id = f"{unit}-{index:02d}"
        row = active_by_bed.get(bed_id)
        if not row:
            beds.append(BedSlot(bed_id=bed_id, unit=unit, status="available"))
            available_count += 1
            continue

        status = (_to_text(row.get("bed_status")) or "occupied").lower()
        if status not in {"available", "occupied", "reserved", "cleaning"}:
            status = "occupied"
        urgency_level = int(row.get("urgency_level") or 0) or None
        ctas_label = _to_text(row.get("ctas_name")) or (f"CTAS {urgency_level}" if urgency_level else None)
        slot = BedSlot(
            bed_id=bed_id,
            unit=unit,
            status=status,
            patient_id=_to_text(row.get("patient_id")) or None,
            ctas_name=ctas_label,
            urgency_level=urgency_level,
            urgency=_urgency_label(urgency_level) if urgency_level else None,
            estimated_wait_minutes=float(row.get("estimated_wait_minutes") or 0.0),
            summary=_to_text(row.get("clinical_summary")),
            current_location=_to_text(row.get("current_location")),
            allocation_alerts=_deserialize_alerts(row.get("allocation_alerts")),
        )
        beds.append(slot)
        if status == "occupied":
            occupied_count += 1
        elif status == "reserved":
            reserved_count += 1
        elif status == "cleaning":
            cleaning_count += 1
        else:
            available_count += 1

    overflow_rows = [
        row for bed_id, row in active_by_bed.items()
        if bed_id.startswith(f"{unit}-OVERFLOW-")
    ]
    for row in overflow_rows:
        urgency_level = int(row.get("urgency_level") or 0) or None
        ctas_label = _to_text(row.get("ctas_name")) or (f"CTAS {urgency_level}" if urgency_level else None)
        status = (_to_text(row.get("bed_status")) or "occupied").lower()
        beds.append(
            BedSlot(
                bed_id=_to_text(row.get("bed_id")),
                unit=unit,
                status=status if status in {"available", "occupied", "reserved", "cleaning"} else "occupied",
                patient_id=_to_text(row.get("patient_id")) or None,
                ctas_name=ctas_label,
                urgency_level=urgency_level,
                urgency=_urgency_label(urgency_level) if urgency_level else None,
                estimated_wait_minutes=float(row.get("estimated_wait_minutes") or 0.0),
                summary=_to_text(row.get("clinical_summary")),
                current_location=_to_text(row.get("current_location")),
                allocation_alerts=_deserialize_alerts(row.get("allocation_alerts")),
            )
        )
        if status == "occupied":
            occupied_count += 1
        elif status == "reserved":
            reserved_count += 1
        elif status == "cleaning":
            cleaning_count += 1

    return BedUnitSummary(
        unit=unit,
        total=total,
        occupied=occupied_count,
        reserved=reserved_count,
        available=available_count,
        cleaning=cleaning_count,
        beds=beds,
    )


def compute_bed_availability(db: Session, scenario_name: str = "normal") -> BedAvailabilityResponse:
    scenario = get_scenario(scenario_name)
    active_rows = _load_bed_rows(db, scenario.name)
    ed_rows = [row for row in active_rows if _to_text(row.get("bed_type")).upper() == "ED"]
    icu_rows = [row for row in active_rows if _to_text(row.get("bed_type")).upper() == "ICU"]

    return BedAvailabilityResponse(
        scenario=scenario.name,
        source="Live patient_history bed states with scenario capacity and manual discharge/transfer/cleaning actions.",
        refreshed_at=_now_iso(),
        ed=_build_unit_beds("ED", scenario.ed_beds, ed_rows),
        icu=_build_unit_beds("ICU", scenario.icu_beds, icu_rows),
    )
