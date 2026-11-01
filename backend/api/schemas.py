from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    model_config = ConfigDict(extra="ignore")


class LoginRequest(APIModel):
    email: str
    password: str
    role: str


class SignupRequest(APIModel):
    role: str
    email: str
    password: str


class PatientCreate(APIModel):
    name: str = ""
    full_name: str = ""
    p_id: str
    health_card: str = ""
    health_card_number: str = ""
    notes: str = ""
    age: Optional[int] = None
    gender: str = ""
    phone: str = ""
    address: str = ""
    emergency_contact: str = ""


class NurseVitals(APIModel):
    """Optional local nurse-entered vitals kept separate from registration/identity data."""

    systolic_bp: Optional[int] = None
    temperature: Optional[float] = None
    heart_rate: Optional[int] = None
    spo2: Optional[float] = None
    respiratory_rate: Optional[int] = None


class ClinicalData(APIModel):
    primary_complaint: str
    pain_score: Optional[int] = None
    consciousness: Optional[str] = None
    spo2: Optional[float] = None
    heart_rate: Optional[int] = None
    systolic_bp: Optional[int] = None
    respiratory_rate: Optional[int] = None
    temperature: Optional[float] = None
    active_seizure: Optional[bool] = None
    uncontrollable_hemorrhage: Optional[bool] = None
    resp_distress: Optional[str] = None
    age: Optional[int] = None
    history: List[str] = Field(default_factory=list)
    summary: str = ""


class ManualTriageRequest(APIModel):
    patient_id: str
    scenario: str = "normal"
    form_data: Dict[str, Any] = Field(default_factory=dict)


class ChatbotTriageRequest(APIModel):
    patient_id: Optional[str] = None
    scenario: str = "normal"
    clinical_data: ClinicalData
    nurse_vitals: Optional[NurseVitals] = None


class NurseFinalizeRequest(APIModel):
    patient_id: str
    scenario: str = "normal"
    nurse_vitals: NurseVitals
    nurse_note: str = ""


class CTASResponse(APIModel):
    level: int
    name: str
    description: str
    color: str
    preliminary: bool = False
    missing_vitals: List[str] = Field(default_factory=list)


class AllocationPatient(APIModel):
    patient_id: str
    urgency_level: int
    waiting_time_minutes: float = 0.0
    lab_required: bool = False
    imaging_required: bool = False
    bed_assigned_type: str = "ED"
    risk_modifier: float = 0.0


class AllocationRequest(APIModel):
    scenario: str = "normal"
    patient: AllocationPatient


class AllocationResponse(APIModel):
    recommended_bed: str
    current_location: str = ""
    requested_service: str = ""
    estimated_wait_minutes: float
    estimated_los_delta_minutes: float
    alerts: List[str] = Field(default_factory=list)


class TriagePipelineResponse(APIModel):
    patient_id: str
    scenario: str
    clinical_data: ClinicalData
    ctas: CTASResponse
    allocation: AllocationResponse


class FinalizedTriageResponse(APIModel):
    patient_id: str
    scenario: str
    clinical_data: ClinicalData
    ctas: CTASResponse
    allocation: AllocationResponse
    urgency: str
    reason: str
    summary: str


class MetricsResponse(APIModel):
    average_waiting_time: float
    average_los: float
    ed_bed_utilization: float
    icu_bed_utilization: float
    queue_length: int
    high_urgency_count: int


class PatientHistoryItem(APIModel):
    patient_id: str
    scenario: str
    urgency_level: int
    ctas_name: str
    arrival_mode: str
    assessment_start_ts: str
    lab_required: bool
    imaging_required: bool
    bed_assigned_type: str
    recommended_bed: str
    bed_id: str = ""
    bed_status: str = "occupied"
    current_location: str = ""
    requested_service: str = ""
    estimated_wait_minutes: float
    estimated_los_delta_minutes: float
    allocation_alerts: List[str] = Field(default_factory=list)
    admit_decision: str
    discharge_ts: Optional[str] = None
    waiting_time_minutes: float = 0.0
    los_minutes: float = 0.0
    clinical_summary: str = ""


class ScoringRequest(APIModel):
    clinical_data: ClinicalData


class ClinicalSummaryResponse(APIModel):
    patient_id: str
    name: str
    full_name: str = ""
    health_card_number: str = ""
    phone: str = ""
    address: str = ""
    emergency_contact: str = ""
    notes: str
    age: Optional[int]
    gender: str
    arrival_time: str
    chief_complaint: str
    location: str
    onset: str
    pain_scale: Optional[int]
    pattern: str
    modifying_factors: str
    neurologic: str
    consciousness_status: str
    cough: str
    breathing_effort: str
    fever: str
    gi_symptoms: str
    recent: str
    respiratory: str
    red_flag_symptoms: str
    palpitations: str
    leg_swelling: str
    medications_allergies: str
    medical_history: str
    recent_hospitalization: str
    recent_surgery: str
    immunocompromised: str
    drug: str
    systolic_bp: Optional[int] = None
    temperature: Optional[float] = None
    heart_rate: Optional[int] = None
    spo2: Optional[float] = None
    respiratory_rate: Optional[int] = None
    ctas_level: int
    ctas_name: str
    ctas_description: str
    urgency: str
    preliminary: bool = False
    missing_vitals: List[str] = Field(default_factory=list)
    recommended_bed: str
    current_location: str = ""
    requested_service: str = ""
    estimated_wait_minutes: float
    estimated_los_delta_minutes: float
    allocation_alerts: List[str] = Field(default_factory=list)
    summary: str = ""


class BedSlot(APIModel):
    bed_id: str
    unit: Literal["ED", "ICU"]
    status: Literal["available", "occupied", "reserved", "cleaning"]
    patient_id: Optional[str] = None
    ctas_name: Optional[str] = None
    urgency_level: Optional[int] = None
    urgency: Optional[str] = None
    estimated_wait_minutes: float = 0.0
    summary: str = ""
    current_location: str = ""
    allocation_alerts: List[str] = Field(default_factory=list)


class BedUnitSummary(APIModel):
    unit: Literal["ED", "ICU"]
    total: int
    occupied: int
    reserved: int
    available: int
    cleaning: int
    beds: List[BedSlot] = Field(default_factory=list)


class BedAvailabilityResponse(APIModel):
    scenario: str
    source: str
    refreshed_at: str
    ed: BedUnitSummary
    icu: BedUnitSummary


class BedPatientInfo(APIModel):
    patient_id: str
    ctas_level: int
    urgency: str
    summary: str = ""
    wait_time: float = 0.0
    requested_service: str = ""
    systolic_bp: Optional[int] = None
    temperature: Optional[float] = None
    heart_rate: Optional[int] = None
    spo2: Optional[float] = None
    respiratory_rate: Optional[int] = None


class BedDetailResponse(APIModel):
    bed_id: str
    bed_status: str
    current_location: str
    patient: Optional[BedPatientInfo] = None


class PatientServiceRequest(APIModel):
    p_id: str
    service: Literal["lab", "imaging"]
    requested_service: str = ""
    scenario: str = "normal"


class PatientUpdateRequest(APIModel):
    p_id: str
    scenario: str = "normal"
    full_name: str = ""
    age: Optional[int] = None
    gender: str = ""
    phone: str = ""
    address: str = ""
    health_card_number: str = ""
    emergency_contact: str = ""
    symptoms: str = ""
    pain_scale: Optional[int] = None
    notes: str = ""
    nurse_vitals: NurseVitals = Field(default_factory=NurseVitals)


class BedDischargeRequest(APIModel):
    patient_id: str
    scenario: str = "normal"


class BedTransferRequest(APIModel):
    patient_id: str
    ward: str
    scenario: str = "normal"


class BedCleaningCompleteRequest(APIModel):
    bed_id: str
    scenario: str = "normal"


class ServiceQueueItem(APIModel):
    patient_id: str
    current_location: str
    requested_service: str
    ctas_name: str
    urgency: str
    estimated_wait_time: float
    summary: str = ""


class ServiceQueueResponse(APIModel):
    department: Literal["lab", "imaging"]
    queue_length: int
    average_wait_time: float
    refreshed_at: str
    available_services: List[str] = Field(default_factory=list)
    patients: List[ServiceQueueItem] = Field(default_factory=list)
