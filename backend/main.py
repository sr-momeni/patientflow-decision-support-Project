from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Union, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import database  

app = FastAPI()

# CORS Middleware: This allows React (port 3000) to talk to FastAPI (port 8000)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://3.142.37.67:3000",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SignupRequest(BaseModel):
    role: str
    email: str
    password: str
    
class PatientCreate(BaseModel):
    name: str
    p_id: int
    health_card: str
    notes: str

#New Patient
@app.post("/add-patient")
async def add_patient(patient: PatientCreate):
    db = database.SessionLocal()
    try:
        
        query = text("""
            INSERT INTO patients (name, p_id, health_card, notes) 
            VALUES (:name, :p_id, :health_card, :notes)
        """)
        
        result = db.execute(query, {
            "name": patient.name,
            "p_id": patient.p_id,
            "health_card": patient.health_card,
            "notes": patient.notes
        })
        db.commit()
        
      
        return {"id": result.lastrowid}
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Database insertion failed")
    finally:
        db.close()
#Login
@app.post("/login")
async def login(user_data: dict):
    email = user_data.get("email")
    password = user_data.get("password")
    role = user_data.get("role")

    
    db = database.SessionLocal()
    
    try:
        # Search MySQL for a matching user and role
       
        query = text("SELECT * FROM users WHERE email = :email AND role = :role AND password_hash = :password")
        result = db.execute(query, {"email": email, "role": role, "password": password}).fetchone()
        
        if not result:
            raise HTTPException(status_code=400, detail="Invalid Email, Role or Password")

        return {
            "message": "Login Successful", 
            "user": result.email, 
            "role": result.role
        }

    finally:
        
        db.close()

@app.post("/signup")
async def signup(user: SignupRequest):
    db = database.SessionLocal()
    try:
        
        check_query = text("SELECT * FROM users WHERE email = :email")
        existing_user = db.execute(check_query, {"email": user.email}).fetchone()
        
        if existing_user:
            raise HTTPException(status_code=400, detail="Email already registered in system")

       
        insert_query = text("""
            INSERT INTO users (role, email, password_hash) 
            VALUES (:role, :email, :password_hash)
        """)
        
        db.execute(insert_query, {
            "role": user.role,
            "email": user.email,
            "password_hash": user.password  
        })
        
        db.commit()
        return {"status": "success", "message": "Staff account created and stored in database"}

    except Exception as e:
        db.rollback()
        print(f"Signup Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to create account")
    finally:
        db.close()




class TriageSchema(BaseModel):
    p_id: str
    arrival_time: Optional[str] = ""
    age: Optional[int] = 0
    gender: Optional[str] = ""
    presenting_complaint_Main_Concern: Optional[str] = ""
    symptom_location: Optional[str] = ""
    symptom_onset: Optional[str] = ""
    Pain_assessment_pain_scale: Optional[int] = 0
    pain_pattern: Optional[str] = ""
    modifying_factors: Optional[str] = ""
    red_flag_symptoms: Optional[str] = ""
    cns_speech_clarity: Optional[str] = ""
    consciousness_status: Optional[str] = ""
    fever_infection: Optional[str] = "" # Changed to Union to handle strings/lists
    gi_symptoms: Optional[str] = ""
    recent_sick_contact: Optional[str] = ""
    respiratory_sob_status: Optional[str] = ""
    cough_type: Optional[str] = ""
    breathing_effort: Optional[str] = ""
    cardiovascular: Optional[str] = ""
    palpitations: Optional[str] = ""
    leg_swelling: Optional[str] = ""
    recent_hospitalization: Optional[str] = ""
    recent_surgery: Optional[str] = ""
    immunocompromised_status: Optional[str] = ""
    drug_allergies: Optional[str] = ""
    medical_history: Optional[str] = ""
    medications_allergies: Optional[str] = ""



@app.post("/submit-triage")
async def save_triage(data: TriageSchema):
    db = database.SessionLocal()
    try:
        # This query handles BOTH Step 1 (Insert) and Step 2/3 (Update)
        query = text("""
            INSERT INTO triage_a (
                p_id, arrival_time, age, gender, presenting_complaint_Main_Concern, 
                symptom_location, symptom_onset, Pain_assessment_pain_scale, 
                pain_pattern, modifying_factors, cns_speech_clarity,consciousness_status, fever_infection, 
                gi_symptoms, recent_sick_contact, respiratory_sob_status, red_flag_symptoms,
                cough_type, breathing_effort,  palpitations, 
                leg_swelling, recent_hospitalization, recent_surgery, 
                immunocompromised_status, medications_allergies, drug_allergies, medical_history
            ) VALUES (
                :p_id, :at, :age, :gender, :pc, :sl, :so, :ps, :pp, :mf, :csc, :cs, :fi, :gi, :rsc, :rss, :rf,
                :ct, :be, :p, :ls, :rh, :rs, :is, :pmu, :da, :ca
            )
            ON DUPLICATE KEY UPDATE 
                arrival_time = IF(:at != '', :at, arrival_time),
                age = IF(:age != 0, :age, age),
                gender = IF(:gender != '', :gender, gender),
                presenting_complaint_Main_Concern = IF(:pc != '', :pc, presenting_complaint_Main_Concern),
                Pain_assessment_pain_scale = :ps,
                pain_pattern = :pp,
                modifying_factors = :mf,
                red_flag_symptoms = :rf,
                cns_speech_clarity = :csc,
                consciousness_status = :cs,
                fever_infection = :fi,
                gi_symptoms = :gi,
                recent_sick_contact = :rsc,
                respiratory_sob_status = :rss,
                cough_type = :ct,
                breathing_effort = :be,
                
                palpitations = :p,
                leg_swelling = :ls,
                recent_hospitalization = :rh,
                recent_surgery = :rs,
                immunocompromised_status = :is,
                medications_allergies = :pmu,
                drug_allergies = :da,
                medical_history = :ca
        """)

        db.execute(query, {
            "p_id": data.p_id, "at": data.arrival_time, "age": data.age, "gender": data.gender,
            "pc": data.presenting_complaint_Main_Concern, "sl": data.symptom_location,
            "so": data.symptom_onset, "ps": data.Pain_assessment_pain_scale,
            "pp": data.pain_pattern, "mf": data.modifying_factors,
            "csc": data.cns_speech_clarity if isinstance(data.cns_speech_clarity, str) else ", ".join(data.cns_speech_clarity),
            "cs": data.consciousness_status,
            "fi": ", ".join(data.fever_infection) if isinstance(data.fever_infection, list) else data.fever_infection,
            "gi": data.gi_symptoms, "rsc": data.recent_sick_contact,
            "rss": data.respiratory_sob_status, "ct": data.cough_type, "be": data.breathing_effort, "p": data.palpitations,
            "ls": data.leg_swelling,
            "rh": data.recent_hospitalization,
            "rs": data.recent_surgery,
            "is": data.immunocompromised_status,
            "pmu": data.medications_allergies,
            "da": data.drug_allergies,
            "ca": data.medical_history,
            "p": data.palpitations,
            "rf": data.red_flag_symptoms
        })
        db.commit()
        return {"status": "success", "message": "Record merged successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/clinical/{p_id}")
async def get_patient_summary(p_id: str):
    db = database.SessionLocal()
    try:
        # 1. Direct SQL Select for Patient Name
        patient_query = text("SELECT name, notes FROM patients WHERE p_id = :p_id")
        patient = db.execute(patient_query, {"p_id": p_id}).fetchone()

        # 2. Direct SQL Select for Triage Details (Latest record)
        triage_query = text("SELECT * FROM triage_a WHERE p_id = :p_id ORDER BY id DESC LIMIT 1")
        triage = db.execute(triage_query, {"p_id": p_id}).fetchone()

        if not triage:
            raise HTTPException(status_code=404, detail="Triage data not found")
        
        
        # 3. Map the Row object to JSON keys for React
        return {
            "name": patient.name if patient else "Unknown",
            "notes": patient.notes if patient else "",
            "age": triage.age, 
            "gender": triage.gender,
            "arrival_time": triage.arrival_time,
            "chief_complaint": triage.presenting_complaint_Main_Concern, 
            "location": triage.symptom_location, 
            "onset": triage.symptom_onset,
            "pain_scale": triage.Pain_assessment_pain_scale,
            "pattern": triage.pain_pattern, 
            "modifying_factors": triage.modifying_factors,
            "neurologic": triage.cns_speech_clarity,
            "consciousness_status":triage.consciousness_status,
            "cough": triage.cough_type,
            "breathing_effort": triage.breathing_effort,
            "fever": triage.fever_infection,
            "gi_symptoms": triage.gi_symptoms,
            "recent": triage.recent_sick_contact,
            "respiratory": triage.respiratory_sob_status,
            "red_flag_symptoms": triage.red_flag_symptoms,
            "palpitations": triage.palpitations,
            "leg_swelling": triage.leg_swelling,
            "medications_allergies": triage.medications_allergies,
            "medical_history":triage.medical_history,
            "recent_hospitalization": triage.recent_hospitalization,
            "recent_surgery": triage.recent_surgery,
            "immunocompromised": triage.immunocompromised_status,
            "drug": triage.drug_allergies,
            
            "urgency": "HIGH" if triage.Pain_assessment_pain_scale >= 7 else "LOW" if triage.Pain_assessment_pain_scale <= 3 else 
        "MEDIUM"
        }
    except Exception as e:
        print(f"Error fetching summary: {e}")
        raise HTTPException(status_code=500, detail="Database fetch failed")
    finally:
        db.close()

@app.get("/patient-history")
async def get_patient_history():
    db = database.SessionLocal()
    try:
        query = text("""
            SELECT 
                patient_id, urgency_level, arrival_mode, assessment_start_ts, 
                lab_required, imaging_required, bed_assigned_type, 
                admit_decision, discharge_ts 
            FROM patient_history 
            ORDER BY id DESC
            LIMIT 10
        """)
        result = db.execute(query).fetchall()
        
        # Convert row objects to a list of dictionaries for JSON response
        history_list = []
        for row in result:
            history_list.append({
                "patient_id": row.patient_id,
                "urgency_level": row.urgency_level,
                "arrival_mode": row.arrival_mode,
                "assessment_start_ts": row.assessment_start_ts,
                "lab_required": row.lab_required,
                "imaging_required": row.imaging_required,
                "bed_assigned_type": row.bed_assigned_type,
                "admit_decision": row.admit_decision,
                "discharge_ts": row.discharge_ts
            })
        return history_list
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch history")
    finally:
        db.close()