# eHospital Triage Agent and ED Decision Support System

A unified Emergency Department decision-support platform built with React, FastAPI, and a live triage workflow. This branch integrates patient registration, symptom-only AI intake, CTAS scoring, nurse vitals finalization, resource allocation, live dashboard metrics, bed assignments, and operational patient tracking into one coherent eHospital experience.

## Overview

This project is designed to support Emergency Department intake and operational decision-making without replacing clinical judgment.

Core principles in the current system:
- Registration and patient identity stay in the local hospital workflow.
- The AI Triage Agent handles symptom-only intake.
- Final CTAS scoring is rule-based and remains separate from the LLM.
- Missing nurse vitals keep an assessment preliminary.
- Resource allocation, patient history, and bed availability are fed from the same backend pipeline.

## End-to-End Workflow

```text
Patient Registration (local)
  -> Manual Triage or AI Triage Agent (text / voice)
  -> Structured clinical data
  -> CTAS scoring
  -> Nurse vitals finalization when needed
  -> Resource allocation and prioritization
  -> Persistence to patient history
  -> Live dashboard, clinical summary, and bed assignments
```

## Key Features

### Clinical workflow
- Manual multi-step triage flow integrated with the main backend.
- AI Triage Agent for symptom-only intake through text and voice.
- CTAS-based urgency scoring via the existing `UrgencyScoringAgent`.
- Nurse finalization step for measured vitals:
  - systolic blood pressure
  - temperature
  - heart rate
  - SpO2
  - respiratory rate
- Clear distinction between preliminary and final CTAS results.
- No fabricated normal vitals injected when measurements are missing.

### Operations and decision support
- Live resource allocation using the existing allocation agent.
- Dashboard with current queue, metrics, latest recommendation, and patient history.
- Bed Assignments page with ED and ICU capacity overview.
- Bed detail page with discharge, transfer, lab, and imaging actions.
- Patient detail page with editable clinical summary and nurse vitals.

### AI and privacy
- OpenAI-backed triage intake for chatbot text flow and voice flow.
- Symptom-only LLM intake with PII sanitization before model calls.
- Patient identity remains outside the cloud triage path.
- LLM supports intake, clarification, transcription, and voice interaction, but not final CTAS decision-making.

### Research and simulation support
- Scenario modeling for normal, ED congestion, and ICU bottleneck conditions.
- Predictive and simulation modules remain available for evaluation and research workflows.
- The live product UI no longer depends on static demo dashboards or CSV-backed pages.

## Current Product Pages

The current React application includes:
- `/dashboard` - operational dashboard
- `/new-patient` - patient registration
- `/triage-form`, `/triage-form-2`, `/triage-form-3` - manual triage workflow
- `/clinical/:p_id` - patient clinical summary
- `/triage-finalize/:p_id` - nurse vitals finalization page
- `/bed-assignments` - bed availability and assignments
- `/bed/:bed_id` - bed detail view
- `/patient/:p_id` - patient detail and edit view
- `/chatbot/ui` - AI Triage Agent UI

## Main Backend API Surface

### Core workflow
- `POST /add-patient`
- `POST /login`
- `POST /signup`
- `POST /triage/manual`
- `POST /triage/chatbot`
- `POST /triage-finalize`
- `POST /scoring`
- `POST /allocate`
- `GET /metrics`
- `GET /patient-history`
- `GET /clinical/{p_id}`

### Bed and patient operations
- `GET /bed-availability`
- `GET /beds/{bed_id}`
- `POST /beds/discharge`
- `POST /beds/transfer`
- `POST /beds/cleaning-complete`
- `POST /patient/send-to-service`
- `POST /patient/update`

### Triage Agent routes
- `GET /chatbot/ui`
- `POST /chatbot/message`
- `POST /chatbot/score`
- `POST /chatbot/realtime-session`
- `POST /chatbot/transcribe`
- `POST /chatbot/speak`

## Architecture

### Active runtime
- Single backend entry point: [`backend/server.py`](backend/server.py)
- Main API routes: [`backend/api/routes.py`](backend/api/routes.py)
- Orchestration and live workflow services: [`backend/api/services.py`](backend/api/services.py)
- Database bootstrap and session layer: [`backend/database.py`](backend/database.py)

### Core decision modules
- CTAS scoring: [`backend/agents/urgency_scoring_agent.py`](backend/agents/urgency_scoring_agent.py)
- Resource allocation: [`backend/agents/resource_allocation_agent.py`](backend/agents/resource_allocation_agent.py)
- Scenario configuration: [`backend/optimization/congestion_scenarios.py`](backend/optimization/congestion_scenarios.py)

### AI intake layer
- Chatbot agent: [`backend/chatbot/chatbot_agent.py`](backend/chatbot/chatbot_agent.py)
- Chatbot routes: [`backend/chatbot/chatbot_routes.py`](backend/chatbot/chatbot_routes.py)
- Chatbot UI: [`backend/chatbot/static/index.html`](backend/chatbot/static/index.html)

### Frontend
- React application: [`frontend/src`](frontend/src)
- Dashboard: [`frontend/src/Dashboard.js`](frontend/src/Dashboard.js)
- Bed operations: [`frontend/src/BedAssignments.js`](frontend/src/BedAssignments.js)
- Nurse finalization: [`frontend/src/TriageFinalize.js`](frontend/src/TriageFinalize.js)

## Repository Structure

```text
backend/
  agents/                CTAS scoring and allocation logic
  api/                   Pydantic schemas, routes, orchestration services
  chatbot/               AI Triage Agent routes, prompts, and UI
  ml/                    predictive model utilities
  optimization/          scenarios and evaluation tools
  simulation/            simulation engines and metrics tooling
  database.py            DB config and bootstrap
  server.py              unified FastAPI app

frontend/
  src/                   React application pages and API client

data/
  evaluation data and local artifacts used for analysis
```

## Running the Project Locally

### Prerequisites
- Python 3.10+
- Node.js 18+
- npm

### 1. Backend setup

```bash
pip install -r requirements.txt
uvicorn backend.server:app --reload
```

The backend starts on `http://127.0.0.1:8000` by default.

### 2. Frontend setup

```bash
cd frontend
npm install
npm start
```

For local development, set the frontend API base URL before starting the React app.

PowerShell example:

```powershell
$env:REACT_APP_API_BASE_URL="http://127.0.0.1:8000"
npm start
```

### 3. Optional production-style frontend build

```bash
cd frontend
npm run build
```

If a React build exists, the FastAPI backend can serve it directly.

## Environment Variables

Common environment variables used by the current branch:

```env
DATABASE_URL=
MYSQL_DATABASE_URL=
OPENAI_API_KEY=
ENABLE_OPENAI_REALTIME=true
ENABLE_AUDIO_TRANSCRIPTION=true
CORS_ORIGINS=http://localhost:3000
REACT_APP_API_BASE_URL=http://127.0.0.1:8000
```

Notes:
- `DATABASE_URL` or `MYSQL_DATABASE_URL` can be used for the database connection.
- The backend can fall back to a local SQLite database if no external DB URL is configured.
- Voice features require a valid `OPENAI_API_KEY`.

## Clinical Logic Notes

- The AI Triage Agent does not make the final CTAS decision on its own.
- CTAS is produced by the existing rule-based urgency scoring logic.
- If measured nurse vitals are missing, the assessment remains preliminary until finalized.
- The system is built to support clinical workflow, not replace clinician judgment.

## Validation Status

This branch has already been aligned to the integrated final-stage workflow:
- unified FastAPI backend
- working dashboard
- working text triage agent
- working voice path support
- live triage, scoring, allocation, metrics, history, and clinical summary integration
- live bed availability, bed detail, and patient detail flows

## Team

Project contributors listed in the original repository materials:
- Salar Momeni
- Sal Khokhar
- Dima Alqaruoti
- Akanksha R. Swamy

## License

This repository is currently presented as an academic / project codebase. Add your preferred license here before public release.
