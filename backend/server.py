from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import text
import os

# Import database module (moved from eHospital)
# We need to make sure this import works. 
# Plan: We will duplicate backend/database.py from eHospital to backend/database.py in root.
try:
    from backend import database
except ImportError:
    import database

app = FastAPI()

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For development convenience
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- eHospital Models (from eHospital/backend/main.py) ---
class SignupRequest(BaseModel):
    role: str
    email: str
    password: str
    
class PatientCreate(BaseModel):
    name: str
    p_id: int
    health_card: str
    notes: str

class TriageSchema(BaseModel):
    p_id: str
    arrival_time: str
    age: int
    presenting_complaint_Main_Concern: str
    symptom_location: str
    symptom_onset: str
    Pain_assessment_pain_scale: int
    pain_pattern: str
    modifying_factors: str
    red_flag_symptoms: List[str] 
    cns_speech_clarity: str
    fever_infection: List[str]
    respiratory_sob_status: str
    cough_type: str
    cardiovascular: List[str]
    medical_history: List[str]
    medications_allergies: List[str]

# --- eHospital API Routes ---

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

@app.post("/login")
async def login(user_data: dict):
    email = user_data.get("email")
    password = user_data.get("password")
    role = user_data.get("role")
    
    db = database.SessionLocal()
    try:
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

@app.post("/submit-triage")
async def save_triage(data: TriageSchema):
    db = database.SessionLocal()
    try:
        query = text("""
            INSERT INTO triage_a (
                p_id, arrival_time, age, presenting_complaint_Main_Concern, 
                symptom_location, symptom_onset, Pain_assessment_pain_scale, 
                pain_pattern, modifying_factors, red_flag_symptoms, 
                cns_speech_clarity, fever_infection, respiratory_sob_status, 
                cough_type, cardiovascular, medical_history, medications_allergies
            ) VALUES (
                :p_id, :at, :age, :pc, :sl, :so, :ps, :pp, :mf, :rf, :csc, :fi, :rss, :ct, :cv, :mh, :ma
            )
        """)
        
        db.execute(query, {
            "p_id": data.p_id, "at": data.arrival_time, "age": data.age,
            "pc": data.presenting_complaint_Main_Concern, "sl": data.symptom_location,
            "so": data.symptom_onset, "ps": data.Pain_assessment_pain_scale,
            "pp": data.pain_pattern, "mf": data.modifying_factors,
            "rf": ", ".join(data.red_flag_symptoms) if data.red_flag_symptoms else "", 
            "csc": data.cns_speech_clarity, 
            "fi": ", ".join(data.fever_infection) if data.fever_infection else "", 
            "rss": data.respiratory_sob_status, 
            "ct": data.cough_type,
            "cv": ", ".join(data.cardiovascular) if data.cardiovascular else "", 
            "mh": ", ".join(data.medical_history) if data.medical_history else "", 
            "ma": ", ".join(data.medications_allergies) if data.medications_allergies else ""
        })
        db.commit()
        return {"status": "success"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# --- Static Files / Frontend Serving ---

# 1. Mount the Root Simulation Frontend (Vanilla JS)
# We want to serve 'frontend/' at '/simulation'
app.mount("/simulation", StaticFiles(directory="frontend", html=True), name="simulation")

# 2. Mount the eHospital React Build
# We will build the React app to 'backend/static/ehospital' (or similar)
# For now, let's assume we will build it to 'eHospital-main/frontend/build' content
# and copy it to 'backend/static_ehospital'

STATIC_EHOSPITAL = "backend/static_ehospital"

if os.path.exists(STATIC_EHOSPITAL):
    app.mount("/", StaticFiles(directory=STATIC_EHOSPITAL, html=True), name="ehospital")
else:
    print(f"WARNING: Directory {STATIC_EHOSPITAL} not found. eHospital frontend will not be served.")

# Fallback for React Router (Single Page App)
# If a route is not found in static files or API, return index.html
@app.exception_handler(404)
async def custom_404_handler(request, exc):
    if os.path.exists(f"{STATIC_EHOSPITAL}/index.html"):
        return FileResponse(f"{STATIC_EHOSPITAL}/index.html")
    return HTTPException(status_code=404, detail="Page not found")
