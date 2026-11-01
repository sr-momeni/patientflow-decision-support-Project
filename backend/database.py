from __future__ import annotations

import os
from typing import Dict, Generator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker


DATABASE_URL = os.getenv("DATABASE_URL") or os.getenv("MYSQL_DATABASE_URL") or "sqlite:///./patientflow.db"

_ENGINE_KWARGS = {"future": True, "pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    _ENGINE_KWARGS["connect_args"] = {"check_same_thread": False}

engine = create_engine(DATABASE_URL, **_ENGINE_KWARGS)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _sqlite_create_statements() -> Dict[str, str]:
    return {
        "users": """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "patients": """
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                p_id TEXT NOT NULL UNIQUE,
                health_card TEXT,
                notes TEXT,
                age INTEGER,
                gender TEXT,
                phone TEXT,
                address TEXT,
                emergency_contact TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "triage_a": """
            CREATE TABLE IF NOT EXISTS triage_a (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                p_id TEXT NOT NULL,
                arrival_time TEXT,
                age INTEGER DEFAULT 0,
                gender TEXT,
                presenting_complaint_Main_Concern TEXT,
                symptom_location TEXT,
                symptom_onset TEXT,
                Pain_assessment_pain_scale INTEGER DEFAULT 0,
                pain_pattern TEXT,
                modifying_factors TEXT,
                red_flag_symptoms TEXT,
                cns_speech_clarity TEXT,
                consciousness_status TEXT,
                fever_infection TEXT,
                gi_symptoms TEXT,
                recent_sick_contact TEXT,
                respiratory_sob_status TEXT,
                cough_type TEXT,
                breathing_effort TEXT,
                palpitations TEXT,
                leg_swelling TEXT,
                recent_hospitalization TEXT,
                recent_surgery TEXT,
                immunocompromised_status TEXT,
                medications_allergies TEXT,
                drug_allergies TEXT,
                medical_history TEXT,
                clinical_summary TEXT,
                clinical_data_json TEXT,
                source TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "patient_history": """
            CREATE TABLE IF NOT EXISTS patient_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id TEXT NOT NULL,
                scenario TEXT,
                urgency_level INTEGER DEFAULT 0,
                ctas_name TEXT,
                arrival_mode TEXT,
                assessment_start_ts TEXT,
                lab_required INTEGER DEFAULT 0,
                imaging_required INTEGER DEFAULT 0,
                bed_assigned_type TEXT,
                recommended_bed TEXT,
                bed_id TEXT,
                bed_status TEXT,
                current_location TEXT,
                requested_service TEXT,
                service_requested_at TEXT,
                estimated_wait_minutes REAL DEFAULT 0,
                estimated_los_delta_minutes REAL DEFAULT 0,
                allocation_alerts TEXT,
                admit_decision TEXT,
                discharge_ts TEXT,
                waiting_time_minutes REAL DEFAULT 0,
                los_minutes REAL DEFAULT 0,
                clinical_summary TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """,
    }


def _mysql_create_statements() -> Dict[str, str]:
    return {
        "users": """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                role TEXT NOT NULL,
                email VARCHAR(255) NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "patients": """
            CREATE TABLE IF NOT EXISTS patients (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                name TEXT NOT NULL,
                p_id VARCHAR(255) NOT NULL UNIQUE,
                health_card TEXT,
                notes TEXT,
                age INTEGER,
                gender TEXT,
                phone TEXT,
                address TEXT,
                emergency_contact TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "triage_a": """
            CREATE TABLE IF NOT EXISTS triage_a (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                p_id VARCHAR(255) NOT NULL,
                arrival_time TEXT,
                age INTEGER DEFAULT 0,
                gender TEXT,
                presenting_complaint_Main_Concern TEXT,
                symptom_location TEXT,
                symptom_onset TEXT,
                Pain_assessment_pain_scale INTEGER DEFAULT 0,
                pain_pattern TEXT,
                modifying_factors TEXT,
                red_flag_symptoms TEXT,
                cns_speech_clarity TEXT,
                consciousness_status TEXT,
                fever_infection TEXT,
                gi_symptoms TEXT,
                recent_sick_contact TEXT,
                respiratory_sob_status TEXT,
                cough_type TEXT,
                breathing_effort TEXT,
                palpitations TEXT,
                leg_swelling TEXT,
                recent_hospitalization TEXT,
                recent_surgery TEXT,
                immunocompromised_status TEXT,
                medications_allergies TEXT,
                drug_allergies TEXT,
                medical_history TEXT,
                clinical_summary TEXT,
                clinical_data_json LONGTEXT,
                source TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
        "patient_history": """
            CREATE TABLE IF NOT EXISTS patient_history (
                id INTEGER PRIMARY KEY AUTO_INCREMENT,
                patient_id VARCHAR(255) NOT NULL,
                scenario TEXT,
                urgency_level INTEGER DEFAULT 0,
                ctas_name TEXT,
                arrival_mode TEXT,
                assessment_start_ts TEXT,
                lab_required TINYINT(1) DEFAULT 0,
                imaging_required TINYINT(1) DEFAULT 0,
                bed_assigned_type TEXT,
                recommended_bed TEXT,
                bed_id TEXT,
                bed_status TEXT,
                current_location TEXT,
                requested_service TEXT,
                service_requested_at TEXT,
                estimated_wait_minutes FLOAT DEFAULT 0,
                estimated_los_delta_minutes FLOAT DEFAULT 0,
                allocation_alerts LONGTEXT,
                admit_decision TEXT,
                discharge_ts TEXT,
                waiting_time_minutes FLOAT DEFAULT 0,
                los_minutes FLOAT DEFAULT 0,
                clinical_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """,
    }


def _column_definitions(backend_name: str) -> Dict[str, Dict[str, str]]:
    real_type = "REAL" if backend_name == "sqlite" else "FLOAT"
    bool_type = "INTEGER DEFAULT 0" if backend_name == "sqlite" else "TINYINT(1) DEFAULT 0"
    text_type = "TEXT"
    long_text = "TEXT" if backend_name == "sqlite" else "LONGTEXT"
    timestamp = "TEXT DEFAULT CURRENT_TIMESTAMP" if backend_name == "sqlite" else "TIMESTAMP DEFAULT CURRENT_TIMESTAMP"
    integer = "INTEGER DEFAULT 0"
    nullable_integer = "INTEGER"
    return {
        "users": {
            "role": text_type,
            "email": text_type,
            "password_hash": text_type,
            "created_at": timestamp,
        },
        "patients": {
            "name": text_type,
            "p_id": text_type,
            "health_card": text_type,
            "notes": text_type,
            "age": nullable_integer,
            "gender": text_type,
            "phone": text_type,
            "address": text_type,
            "emergency_contact": text_type,
            "created_at": timestamp,
        },
        "triage_a": {
            "arrival_time": text_type,
            "age": integer,
            "gender": text_type,
            "presenting_complaint_Main_Concern": text_type,
            "symptom_location": text_type,
            "symptom_onset": text_type,
            "Pain_assessment_pain_scale": integer,
            "pain_pattern": text_type,
            "modifying_factors": text_type,
            "red_flag_symptoms": text_type,
            "cns_speech_clarity": text_type,
            "consciousness_status": text_type,
            "fever_infection": text_type,
            "gi_symptoms": text_type,
            "recent_sick_contact": text_type,
            "respiratory_sob_status": text_type,
            "cough_type": text_type,
            "breathing_effort": text_type,
            "palpitations": text_type,
            "leg_swelling": text_type,
            "recent_hospitalization": text_type,
            "recent_surgery": text_type,
            "immunocompromised_status": text_type,
            "medications_allergies": text_type,
            "drug_allergies": text_type,
            "medical_history": text_type,
            "clinical_summary": text_type,
            "clinical_data_json": long_text,
            "source": text_type,
            "created_at": timestamp,
        },
        "patient_history": {
            "scenario": text_type,
            "urgency_level": integer,
            "ctas_name": text_type,
            "arrival_mode": text_type,
            "assessment_start_ts": text_type,
            "lab_required": bool_type,
            "imaging_required": bool_type,
            "bed_assigned_type": text_type,
            "recommended_bed": text_type,
            "bed_id": text_type,
            "bed_status": text_type,
            "current_location": text_type,
            "requested_service": text_type,
            "service_requested_at": text_type,
            "estimated_wait_minutes": f"{real_type} DEFAULT 0",
            "estimated_los_delta_minutes": f"{real_type} DEFAULT 0",
            "allocation_alerts": long_text,
            "admit_decision": text_type,
            "discharge_ts": text_type,
            "waiting_time_minutes": f"{real_type} DEFAULT 0",
            "los_minutes": f"{real_type} DEFAULT 0",
            "clinical_summary": text_type,
            "created_at": timestamp,
        },
    }


def init_db() -> None:
    backend_name = engine.url.get_backend_name()
    create_statements = _sqlite_create_statements() if backend_name == "sqlite" else _mysql_create_statements()
    column_definitions = _column_definitions(backend_name)

    with engine.begin() as connection:
        inspector = inspect(connection)
        existing_tables = set(inspector.get_table_names())

        for table_name, statement in create_statements.items():
            if table_name not in existing_tables:
                connection.execute(text(statement))

        inspector = inspect(connection)
        for table_name, definitions in column_definitions.items():
            if table_name not in inspector.get_table_names():
                continue
            existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
            for column_name, definition in definitions.items():
                if column_name not in existing_columns:
                    connection.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}"))


if __name__ == "__main__":
    init_db()
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
        print(f"Database ready: {DATABASE_URL}")
