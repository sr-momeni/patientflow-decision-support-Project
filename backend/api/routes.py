from __future__ import annotations

from typing import Any, Dict, List

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api.schemas import (
    AllocationRequest,
    AllocationResponse,
    BedAvailabilityResponse,
    BedCleaningCompleteRequest,
    BedDetailResponse,
    BedDischargeRequest,
    BedTransferRequest,
    ChatbotTriageRequest,
    ClinicalSummaryResponse,
    CTASResponse,
    FinalizedTriageResponse,
    LoginRequest,
    ManualTriageRequest,
    MetricsResponse,
    NurseFinalizeRequest,
    PatientCreate,
    PatientHistoryItem,
    PatientServiceRequest,
    PatientUpdateRequest,
    ScoringRequest,
    SignupRequest,
    TriagePipelineResponse,
)
from backend.api.services import (
    allocate_only,
    complete_bed_cleaning,
    compute_bed_availability,
    compute_live_metrics,
    discharge_patient_from_bed,
    fetch_bed_detail,
    fetch_clinical_summary,
    fetch_patient_history,
    finalize_nurse_evaluation,
    normalize_manual_triage_payload,
    run_triage_pipeline,
    score_clinical_data,
    send_patient_to_service,
    transfer_patient_to_ward,
    update_patient_record,
)
from backend.database import get_db


router = APIRouter(tags=["api"])


@router.post("/add-patient")
def add_patient(patient: PatientCreate, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        existing = db.execute(
            text("SELECT id FROM patients WHERE p_id = :p_id LIMIT 1"),
            {"p_id": patient.p_id},
        ).mappings().first()

        if existing:
            db.execute(
                text(
                    """
                    UPDATE patients
                    SET name = :name,
                        health_card = :health_card,
                        notes = :notes
                    WHERE p_id = :p_id
                    """
                ),
                {
                    "name": patient.name,
                    "p_id": patient.p_id,
                    "health_card": patient.health_card,
                    "notes": patient.notes,
                },
            )
        else:
            db.execute(
                text(
                    """
                    INSERT INTO patients (name, p_id, health_card, notes)
                    VALUES (:name, :p_id, :health_card, :notes)
                    """
                ),
                {
                    "name": patient.name,
                    "p_id": patient.p_id,
                    "health_card": patient.health_card,
                    "notes": patient.notes,
                },
            )
        db.commit()
        return {"id": patient.p_id, "patient_id": patient.p_id}
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to save patient: {exc}")


@router.post("/login")
def login(request: LoginRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    user = db.execute(
        text(
            """
            SELECT email, role
            FROM users
            WHERE email = :email AND role = :role AND password_hash = :password
            LIMIT 1
            """
        ),
        {
            "email": request.email,
            "role": request.role,
            "password": request.password,
        },
    ).mappings().first()

    if not user:
        raise HTTPException(status_code=400, detail="Invalid Email, Role or Password")

    return {"message": "Login Successful", "user": user["email"], "role": user["role"]}


@router.post("/signup")
def signup(request: SignupRequest, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        existing = db.execute(
            text("SELECT id FROM users WHERE email = :email LIMIT 1"),
            {"email": request.email},
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Email already registered in system")

        db.execute(
            text(
                """
                INSERT INTO users (role, email, password_hash)
                VALUES (:role, :email, :password_hash)
                """
            ),
            {
                "role": request.role,
                "email": request.email,
                "password_hash": request.password,
            },
        )
        db.commit()
        return {"status": "success", "message": "Staff account created and stored in database"}
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create account: {exc}")


@router.post("/triage/manual", response_model=TriagePipelineResponse)
def triage_manual(request: ManualTriageRequest, db: Session = Depends(get_db)) -> TriagePipelineResponse:
    try:
        clinical_data = normalize_manual_triage_payload(request.form_data)
        return run_triage_pipeline(
            db=db,
            patient_id=request.patient_id,
            scenario_name=request.scenario,
            clinical_data=clinical_data,
            raw_form_data=request.form_data,
            source="manual",
        )
    except HTTPException:
        raise
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Manual triage pipeline failed: {exc}")


@router.post("/triage/chatbot", response_model=TriagePipelineResponse)
def triage_chatbot(request: ChatbotTriageRequest, db: Session = Depends(get_db)) -> TriagePipelineResponse:
    try:
        return run_triage_pipeline(
            db=db,
            patient_id=request.patient_id,
            scenario_name=request.scenario,
            clinical_data=request.clinical_data,
            raw_form_data={
                "presenting_complaint_Main_Concern": request.clinical_data.primary_complaint,
                "Pain_assessment_pain_scale": request.clinical_data.pain_score,
                "age": request.clinical_data.age,
                "medical_history": ", ".join(request.clinical_data.history),
            },
            source="chatbot",
        )
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Chatbot triage pipeline failed: {exc}")


@router.post("/triage-finalize", response_model=FinalizedTriageResponse)
def triage_finalize(request: NurseFinalizeRequest, db: Session = Depends(get_db)) -> FinalizedTriageResponse:
    try:
        return finalize_nurse_evaluation(
            db=db,
            patient_id=request.patient_id,
            nurse_vitals=request.nurse_vitals.model_dump(),
            nurse_note=request.nurse_note,
            scenario_name=request.scenario,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Nurse finalization failed: {exc}")


@router.post("/scoring", response_model=CTASResponse)
def score_only(request: ScoringRequest) -> CTASResponse:
    try:
        return score_clinical_data(request.clinical_data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {exc}")


@router.post("/allocate", response_model=AllocationResponse)
def allocate_only_route(request: AllocationRequest) -> AllocationResponse:
    try:
        return allocate_only(request.patient, request.scenario)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Allocation failed: {exc}")


@router.get("/metrics", response_model=MetricsResponse)
def metrics(scenario: str = Query(default="normal"), db: Session = Depends(get_db)) -> MetricsResponse:
    try:
        return compute_live_metrics(db, scenario_name=scenario)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Metrics failed: {exc}")


@router.get("/bed-availability", response_model=BedAvailabilityResponse)
def bed_availability(scenario: str = Query(default="normal"), db: Session = Depends(get_db)) -> BedAvailabilityResponse:
    try:
        return compute_bed_availability(db, scenario_name=scenario)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch bed availability: {exc}")


@router.get("/beds/{bed_id}", response_model=BedDetailResponse)
def bed_detail(bed_id: str, scenario: str = Query(default="normal"), db: Session = Depends(get_db)) -> BedDetailResponse:
    try:
        return fetch_bed_detail(db, bed_id=bed_id, scenario_name=scenario)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch bed detail: {exc}")


@router.post("/beds/discharge", response_model=BedAvailabilityResponse)
def bed_discharge(request: BedDischargeRequest, db: Session = Depends(get_db)) -> BedAvailabilityResponse:
    try:
        return discharge_patient_from_bed(db, patient_id=request.patient_id, scenario_name=request.scenario)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to discharge patient from bed: {exc}")


@router.post("/beds/transfer", response_model=BedAvailabilityResponse)
def bed_transfer(request: BedTransferRequest, db: Session = Depends(get_db)) -> BedAvailabilityResponse:
    try:
        return transfer_patient_to_ward(db, patient_id=request.patient_id, ward=request.ward, scenario_name=request.scenario)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to transfer patient: {exc}")


@router.post("/beds/cleaning-complete", response_model=BedAvailabilityResponse)
def bed_cleaning_complete(request: BedCleaningCompleteRequest, db: Session = Depends(get_db)) -> BedAvailabilityResponse:
    try:
        return complete_bed_cleaning(db, bed_id=request.bed_id, scenario_name=request.scenario)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to complete bed cleaning: {exc}")


@router.post("/patient/send-to-service", response_model=BedDetailResponse)
def patient_send_to_service(request: PatientServiceRequest, db: Session = Depends(get_db)) -> BedDetailResponse:
    try:
        return send_patient_to_service(db, patient_id=request.p_id, service=request.service, scenario_name=request.scenario)
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to send patient to service: {exc}")


@router.post("/patient/update", response_model=ClinicalSummaryResponse)
def patient_update(request: PatientUpdateRequest, db: Session = Depends(get_db)) -> ClinicalSummaryResponse:
    try:
        return update_patient_record(
            db,
            patient_id=request.p_id,
            symptoms=request.symptoms,
            pain_scale=request.pain_scale,
            notes=request.notes,
            nurse_vitals=request.nurse_vitals.model_dump(),
            scenario_name=request.scenario,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update patient: {exc}")


@router.get("/patient-history", response_model=List[PatientHistoryItem])
def patient_history(
    limit: int = Query(default=20, ge=1, le=200),
    scenario: str = Query(default=""),
    db: Session = Depends(get_db),
) -> List[PatientHistoryItem]:
    try:
        return fetch_patient_history(db, limit=limit, scenario_name=scenario)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch history: {exc}")


@router.get("/clinical/{p_id}", response_model=ClinicalSummaryResponse)
def clinical_summary(p_id: str, db: Session = Depends(get_db)) -> ClinicalSummaryResponse:
    try:
        return fetch_clinical_summary(db, p_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to fetch clinical summary: {exc}")
