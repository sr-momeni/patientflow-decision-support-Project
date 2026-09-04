# eHospital Triage Agent and ED Decision Support System

A full-stack **Emergency Department (ED) decision-support platform** built with React and FastAPI. The current system integrates patient registration, AI-assisted symptom intake, CTAS-based triage, nurse vital-sign finalization, resource allocation, live operational metrics, bed management, patient tracking, simulation, and analytics into one unified eHospital workflow.

> **Important:** This repository is an academic decision-support prototype. It is not a medical device and must not replace qualified healthcare professionals, emergency services, or local clinical protocols.

---

## Overview

Emergency Departments operate under continuously changing conditions. Patient urgency, bed availability, ICU capacity, waiting time, diagnostic demand, arrival patterns, and congestion all affect operational decisions.

This project explores how a software-based decision-support system can connect the clinical intake workflow with operational patient-flow management.

The current system supports:

- local patient registration and staff-facing workflows,
- manual and AI-assisted symptom intake,
- CTAS Level 1-5 urgency assessment,
- nurse-entered vital signs and finalization,
- preliminary versus finalized triage states,
- resource-allocation recommendations,
- ED and ICU bed management,
- laboratory and imaging service workflows,
- patient history and clinical summaries,
- live operational dashboard metrics,
- scenario-based congestion modeling,
- patient-flow simulation,
- and machine-learning experimentation for high-urgency arrival forecasting.

The application consists of a **Python/FastAPI backend** and a **React frontend**.

---

## Design Principles

The current implementation follows several important separation-of-responsibility principles:

- **Patient identity remains in the local hospital workflow.**
- **The AI Triage Agent is used for symptom-focused intake and clarification.**
- **Final CTAS scoring remains rule-based and separate from the language model.**
- **Missing nurse-entered vital signs can keep an assessment preliminary.**
- **The AI workflow does not fabricate normal vital signs when measurements are unavailable.**
- **Resource allocation, patient history, bed state, and dashboard metrics are driven by the same backend workflow.**
- **Clinical decisions remain under human supervision.**

---

## End-to-End Workflow

```text
Patient Registration
        |
        v
Manual Triage or AI Triage Agent
(Text / Voice)
        |
        v
Structured Clinical Data
        |
        v
CTAS Urgency Scoring
        |
        v
Preliminary Assessment
        |
        v
Nurse Vital-Sign Finalization
(when required)
        |
        v
Resource Allocation & Prioritization
        |
        +----> ED Bed
        |
        +----> ICU Consideration
        |
        +----> Waiting / Priority Recommendation
        |
        v
Persistence & Operational State
        |
        +----> Clinical Summary
        +----> Patient History
        +----> Dashboard Metrics
        +----> Bed Assignments
        +----> Lab / Imaging Workflow
```

---

# Key Features

## CTAS-Based Triage

The system supports patient prioritization using the **Canadian Triage and Acuity Scale (CTAS)**.

| CTAS Level | Classification |
| --- | --- |
| **CTAS 1** | Resuscitation |
| **CTAS 2** | Emergent |
| **CTAS 3** | Urgent |
| **CTAS 4** | Less Urgent |
| **CTAS 5** | Non-Urgent |

The rule-based urgency-scoring workflow evaluates available clinical information such as:

- presenting complaint,
- pain score,
- consciousness level,
- oxygen saturation,
- heart rate,
- systolic blood pressure,
- respiratory rate,
- temperature,
- respiratory distress,
- seizure or hemorrhage indicators,
- age,
- and relevant clinical history.

CTAS output is treated as **decision-support information**, not as an autonomous diagnosis.

---

## AI-Assisted Symptom Intake

The repository includes an AI-assisted triage workflow that can help structure free-text symptom descriptions before they enter the clinical scoring pipeline.

The AI layer can support:

- symptom-focused text intake,
- short clarification questions,
- structured clinical-data extraction,
- concise clinical summaries,
- speech transcription,
- text-to-speech responses,
- and realtime voice interaction when enabled.

The language model does **not** independently assign the final CTAS level. Structured information is passed to the rule-based triage pipeline for scoring.

---

## Nurse Vital-Sign Finalization

The system supports a separate nurse-review step for measured vital signs.

The finalization workflow can incorporate:

- systolic blood pressure,
- temperature,
- heart rate,
- SpO2,
- respiratory rate,
- and nurse notes.

When required measurements are missing, an assessment can remain preliminary until additional information is entered.

---

## Privacy-Aware AI Processing

The AI intake layer includes preprocessing logic designed to redact several common forms of personally identifiable information before supported text is sent to an external AI service.

Supported patterns include information resembling:

- email addresses,
- phone numbers,
- health or identification numbers,
- dates of birth,
- and other selected identifiers.

The AI prompt also instructs the intake workflow not to request patient identity information such as names, addresses, phone numbers, health-card numbers, email addresses, or exact dates of birth.

This mechanism is intended for research and demonstration purposes only. It is **not** production-grade PHI protection and should not be treated as a substitute for healthcare privacy infrastructure.

---

# Resource Allocation and Operational Decision Support

A major component of the system is the **Resource Allocation Agent**, which combines patient urgency with operational constraints.

The allocation workflow can consider:

- CTAS urgency,
- accumulated waiting time,
- ED congestion,
- ED bed capacity,
- ICU capacity,
- operational constraints,
- available risk information,
- laboratory demand,
- imaging demand,
- and current resource availability.

Possible outputs include:

- recommended bed type,
- ED or ICU consideration,
- waiting status,
- estimated waiting time,
- priority score,
- alerts,
- and a decision explanation.

### Priority-Based Allocation

Conceptually, patient prioritization combines urgency with waiting conditions and optional risk modifiers:

```text
Priority Score
      =
CTAS Urgency
      +
Waiting Time
      +
Optional Risk Modifiers
```

This allows high-acuity patients to receive stronger priority while also reducing the risk of lower-acuity patients remaining indefinitely in the queue.

---

# Bed, Laboratory, and Imaging Workflows

The current application includes operational workflows beyond triage itself.

## Bed Management

The system supports:

- ED and ICU bed availability,
- bed-detail views,
- patient discharge,
- ward transfer,
- bed-cleaning completion,
- and patient-to-bed operational tracking.

## Laboratory and Imaging

Laboratory and imaging are integrated into the patient-flow and resource-allocation workflow.

The system can:

- identify patients requiring laboratory services,
- identify patients requiring imaging services,
- send patients to a selected service,
- model laboratory and imaging capacity,
- estimate queue-related delays,
- and incorporate diagnostic-service demand into simulation and allocation logic.

These services are operational workflows within the application rather than standalone CTAS decision modules.

---

# Dashboard and Patient Tracking

The React frontend provides staff-facing views for operational monitoring and patient management.

The application includes functionality for:

- patient registration,
- manual triage,
- clinical summaries,
- nurse triage finalization,
- patient details and editing,
- patient history,
- current queue information,
- live metrics,
- resource recommendations,
- ED/ICU bed assignments,
- bed operations,
- laboratory/imaging actions,
- and an AI-assisted triage interface.

## Current React Routes

| Route | Purpose |
| --- | --- |
| `/` | eHospital landing page |
| `/login` | Staff login |
| `/signup` | Staff account registration |
| `/dashboard` | Operational dashboard |
| `/new-patient` | Patient registration |
| `/triage-form` | Manual triage workflow |
| `/clinical/:p_id` | Patient clinical summary |
| `/triage-finalize/:p_id` | Nurse triage finalization |
| `/bed-assignments` | Bed availability and assignments |
| `/bed/:bed_id` | Bed details and operational actions |
| `/patient/:p_id` | Patient details and editing |

The AI Triage Agent interface is served separately by the FastAPI backend at:

```text
/chatbot/ui
```

---

# Backend API

The backend is implemented with **FastAPI**.

The canonical application entry point is:

```text
backend/server.py
```

`backend/main.py` remains as a compatibility entry point for older startup commands.

## Core Workflow Endpoints

```text
POST /add-patient
POST /login
POST /signup

POST /triage/manual
POST /triage/chatbot
POST /triage-finalize

POST /scoring
POST /allocate

GET  /metrics
GET  /patient-history
GET  /clinical/{p_id}
```

## Bed Management Endpoints

```text
GET  /bed-availability
GET  /beds/{bed_id}

POST /beds/discharge
POST /beds/transfer
POST /beds/cleaning-complete
```

## Patient Operations

```text
POST /patient/send-to-service
POST /patient/update
```

## AI Triage Endpoints

The chatbot router is mounted under `/chatbot`.

```text
GET  /chatbot/ui
POST /chatbot/message
POST /chatbot/score
POST /chatbot/realtime-session
POST /chatbot/transcribe
POST /chatbot/speak
```

---

# Machine Learning and Research Components

The repository includes an experimental machine-learning module for forecasting **high-urgency patient arrivals**.

The current predictor uses Scikit-learn's:

```text
HistGradientBoostingRegressor
```

The model is designed to estimate the expected number of **CTAS Level 1 and Level 2 patients** arriving within a future prediction window.

Current feature engineering includes cyclical time encoding for:

- hour of day,
- and day of week.

Model utilities support:

- train/test splitting,
- training,
- prediction,
- Mean Squared Error evaluation,
- Mean Absolute Error evaluation,
- R² evaluation,
- model persistence,
- and model loading with `joblib`.

The ML module is experimental and is not used as an autonomous clinical decision-maker.

---

# Patient-Flow Simulation

The repository contains simulation and analytics components for studying Emergency Department operations under different conditions.

Simulation functionality supports experimentation with:

- patient arrival patterns,
- CTAS distributions,
- ED congestion,
- ICU bottlenecks,
- resource occupancy,
- waiting conditions,
- laboratory demand,
- imaging demand,
- allocation strategies,
- and operational constraints.

## Scenario Modeling

Current scenario configuration supports operational conditions such as:

### Normal Operations

Typical patient-arrival and resource-utilization conditions.

### ED Congestion

Higher Emergency Department demand and elevated ED resource utilization.

### ICU Bottleneck

Reduced ICU availability and greater downstream resource pressure.

These scenarios allow resource-allocation behavior to be evaluated under different operational conditions without using real patient records.

---

# Architecture

## Active Runtime

- [`backend/server.py`](backend/server.py) - unified FastAPI application
- [`backend/api/routes.py`](backend/api/routes.py) - main API surface
- [`backend/api/services.py`](backend/api/services.py) - workflow orchestration and backend services
- [`backend/database.py`](backend/database.py) - database configuration, initialization, and session layer

## Core Decision Modules

- [`backend/agents/urgency_scoring_agent.py`](backend/agents/urgency_scoring_agent.py) - CTAS scoring logic
- [`backend/agents/resource_allocation_agent.py`](backend/agents/resource_allocation_agent.py) - resource-allocation logic
- [`backend/optimization/congestion_scenarios.py`](backend/optimization/congestion_scenarios.py) - operational scenario definitions

## AI Intake Layer

- [`backend/chatbot/chatbot_agent.py`](backend/chatbot/chatbot_agent.py) - AI-assisted intake logic
- [`backend/chatbot/chatbot_routes.py`](backend/chatbot/chatbot_routes.py) - chatbot API, realtime, transcription, and speech routes
- [`backend/chatbot/static/index.html`](backend/chatbot/static/index.html) - standalone AI Triage Agent interface

## Machine Learning

- [`backend/ml/predictor.py`](backend/ml/predictor.py) - high-urgency arrival predictor

## Frontend

- [`frontend/src`](frontend/src) - React application
- [`frontend/src/Dashboard.js`](frontend/src/Dashboard.js) - operational dashboard
- [`frontend/src/BedAssignments.js`](frontend/src/BedAssignments.js) - bed assignments
- [`frontend/src/BedDetail.js`](frontend/src/BedDetail.js) - bed operations and service actions
- [`frontend/src/TriageFinalize.js`](frontend/src/TriageFinalize.js) - nurse finalization workflow
- [`frontend/src/PatientDetail.js`](frontend/src/PatientDetail.js) - patient details and editing

---

# Technology Stack

## Backend

- Python
- FastAPI
- Uvicorn
- Pydantic
- SQLAlchemy
- Pandas
- NumPy
- Scikit-learn
- Joblib
- OpenAI API
- HTTPX
- python-dotenv

## Frontend

- React
- React Router
- CRACO
- Axios
- JavaScript
- HTML
- CSS

## Data and Analytics

- Synthetic patient data
- CTAS-based patient scenarios
- Operational simulation
- Patient-arrival analysis
- Resource-utilization analysis
- Congestion modeling
- Machine-learning experimentation

---

# Repository Structure

```text
patientflow-decision-support-Project/
|
|-- backend/
|   |-- agents/                 CTAS scoring and allocation logic
|   |-- api/                    schemas, routes, and workflow services
|   |-- chatbot/                AI Triage Agent logic, routes, and UI
|   |-- data/                   synthetic data generation and datasets
|   |-- ml/                     predictive-model utilities
|   |-- optimization/           resource constraints and scenarios
|   |-- simulation/             patient-flow simulation modules
|   |-- database.py             database configuration and bootstrap
|   |-- init_simulation.py      simulation initialization utilities
|   |-- main.py                 compatibility application entry point
|   `-- server.py               canonical FastAPI application
|
|-- frontend/
|   |-- public/
|   |-- src/                    React application pages and API client
|   |-- package.json
|   |-- package-lock.json
|   `-- craco.config.js
|
|-- data/                       evaluation and analysis artifacts
|-- advanced_analysis.py        operational-analysis utilities
|-- convert_data.py             simulation-data transformation
|-- patient_arrival_analysis.py arrival-distribution analysis
|-- visualize_comparison.py     visualization utilities
|-- requirements.txt
|-- pytest.ini
|-- LICENSE
`-- README.md
```

The repository reflects multiple stages of development. The current application is centered on the active `backend/` modules and React `frontend/`.

---

# Running the Project Locally

## Prerequisites

Install:

- Python 3.10+
- Node.js 18+
- npm
- Git

An OpenAI API key is required only for AI-assisted functionality.

---

## 1. Clone the Repository

```bash
git clone https://github.com/sr-momeni/patientflow-decision-support-Project.git
cd patientflow-decision-support-Project
```

---

## 2. Create a Python Virtual Environment

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Windows Command Prompt

```cmd
python -m venv .venv
.venv\Scripts\activate
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3. Install Backend Dependencies

```bash
pip install -r requirements.txt
```

The current codebase also uses Scikit-learn, Joblib, and python-dotenv. If your local environment reports one of these dependencies as missing, install them with:

```bash
pip install scikit-learn joblib python-dotenv
```

---

## 4. Environment Configuration

Create a `.env` file in the repository root when needed.

Example:

```env
OPENAI_API_KEY=

DATABASE_URL=
MYSQL_DATABASE_URL=

ENABLE_OPENAI_REALTIME=false
ENABLE_AUDIO_TRANSCRIPTION=true

CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### Database

`DATABASE_URL` or `MYSQL_DATABASE_URL` can be used to configure an external database connection.

When neither is provided, the backend can fall back to a local SQLite database:

```text
sqlite:///./patientflow.db
```

### AI and Voice Features

AI-assisted functionality requires:

```env
OPENAI_API_KEY=your_key_here
```

Realtime voice support can be enabled with:

```env
ENABLE_OPENAI_REALTIME=true
```

Audio transcription can be controlled with:

```env
ENABLE_AUDIO_TRANSCRIPTION=true
```

Never commit `.env` files, API keys, credentials, or other secrets to version control.

---

## 5. Start the Backend

From the repository root:

```bash
python -m uvicorn backend.server:app --reload
```

The backend normally runs at:

```text
http://127.0.0.1:8000
```

FastAPI interactive documentation:

```text
http://127.0.0.1:8000/docs
```

Alternative API documentation:

```text
http://127.0.0.1:8000/redoc
```

---

## 6. Start the Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm start
```

The React development server normally runs at:

```text
http://localhost:3000
```

The frontend API target can be configured with:

```env
REACT_APP_API_BASE_URL=http://127.0.0.1:8000
```

If this variable is not provided, the current frontend API client defaults to:

```text
http://127.0.0.1:8000
```

Keep the backend running while using the frontend.

---

## 7. Optional Production Frontend Build

```bash
cd frontend
npm run build
```

When a React production build exists, the FastAPI application can serve it from:

```text
frontend/build
```

---

# Testing

## Backend

Run available Python tests from the repository root:

```bash
pytest
```

## Frontend

From the frontend directory:

```bash
npm test
```

## Production Build Check

```bash
npm run build
```

---

# Data and Analytics

The project primarily uses **synthetic and experimental patient data** for development, simulation, and evaluation.

Synthetic data supports:

- reproducible testing,
- safe experimentation,
- congestion scenario generation,
- patient-arrival analysis,
- resource-allocation evaluation,
- and simulation without exposing real patient records.

Generated patient-flow information can include:

- arrival timestamps,
- urgency level,
- arrival mode,
- diagnostic requirements,
- service duration,
- bed assignment,
- waiting time,
- and length of stay.

## Analysis Utilities

### `advanced_analysis.py`

Supports detailed simulation and operational analysis, including allocation behavior, bed utilization, waiting effects, and resource-related metrics.

### `patient_arrival_analysis.py`

Analyzes generated patient-arrival distributions and urgency patterns.

### `visualize_comparison.py`

Provides visual comparisons of simulation and patient-flow results.

### `convert_data.py`

Transforms simulation output into formats used by visualization components.

---

# Clinical Safety and Responsible Use

The system is designed around a **human-in-the-loop** workflow.

```text
AI-Assisted Intake
        |
        v
Structured Clinical Information
        |
        v
Rule-Based CTAS Scoring
        |
        v
Nurse Review / Measured Vitals
        |
        v
Decision-Support Output
```

Important limitations:

- The AI Triage Agent does not independently make the final CTAS decision.
- AI-generated summaries require human review.
- Missing measured vitals should not be replaced with fabricated normal values.
- Resource recommendations are operational decision-support outputs.
- The platform must not be used for autonomous healthcare decisions.
- Clinical decisions must remain under qualified healthcare-professional supervision.

---

# Data Privacy

Do not enter real:

- patient names,
- home addresses,
- phone numbers,
- email addresses,
- health-card numbers,
- medical-record identifiers,
- or other personally identifiable health information.

The project includes limited PII-redaction functionality, but it does not provide the encryption, auditing, access control, regulatory compliance, data-governance, or privacy safeguards required for real healthcare deployment.

---

# Team and Contributions

This project was developed collaboratively by a four-member team.

## Salar Momeni
### Primary Developer · System Integration · Resource Allocation

Salar served as the project's **primary technical contributor and system integrator**.

Primary contributions included:

- resource-allocation workflow development,
- CTAS-based patient prioritization,
- ED and ICU allocation logic,
- waiting-time and resource recommendations,
- operational constraints and congestion-scenario integration,
- patient-flow and simulation work,
- backend integration,
- integration of AI-assisted functionality with the broader workflow,
- frontend/backend integration,
- debugging and troubleshooting,
- system testing and validation,
- analytics and evaluation support,
- and integration of the team's technical components into the final application.

Salar also contributed to the overall architecture, refinement, demonstration, and presentation of the system.

## Akanksha R. Swamy
### Frontend Development

Primary contributions included:

- React frontend development,
- user-interface implementation,
- triage and patient-flow interfaces,
- dashboard development,
- and frontend integration with backend APIs.

## Dima Alqaruoti
### Machine Learning

Primary contributions included:

- machine-learning component development,
- predictive-model implementation,
- model training and experimentation,
- and integration of predictive functionality with the patient-flow system.

## Sahil Khokhar
### Development Support

Primary contributions included:

- assisting with resource-allocation development,
- supporting implementation and integration,
- testing and debugging,
- and assisting with refinement of the final system.

---

# Project Evolution

The project evolved through multiple technical iterations.

Earlier versions explored predictive bed reservation, simpler CTAS scopes, static visualization approaches, and alternative simulation strategies.

The current codebase includes a broader integrated workflow with:

- CTAS Level 1-5 triage,
- manual and AI-assisted intake,
- nurse triage finalization,
- resource allocation,
- ED/ICU bed operations,
- laboratory and imaging workflows,
- patient history,
- live dashboard metrics,
- database persistence,
- simulation,
- and experimental machine-learning components.

Because the system has evolved substantially, older documentation and experimental metrics should not automatically be interpreted as performance claims for the current version.

---

# Portfolio Highlights

This project demonstrates practical experience with:

- Python application development
- FastAPI
- REST API design
- React
- Full-stack integration
- Healthcare-oriented software design
- CTAS-based decision-support logic
- Resource allocation
- Operational optimization
- Bed-management workflows
- Laboratory and imaging workflow integration
- Patient-flow simulation
- Synthetic data generation
- Data analysis
- Machine learning
- OpenAI API integration
- PII-aware text preprocessing
- SQLAlchemy and database integration
- Software-agent architecture
- Testing and debugging
- Collaborative software development

---

# Limitations

This repository represents an academic and research prototype.

Current limitations include:

- no production-grade healthcare authentication and authorization,
- no deployment-grade PHI protection,
- synthetic and experimental datasets,
- AI-generated content requiring professional review,
- prototype-level PII redaction,
- experimental machine-learning and simulation components,
- no regulatory validation,
- no clinical certification,
- and no production healthcare deployment.

---

# Future Improvements

Potential future work includes:

- stronger authentication and role-based access control,
- secure password storage and authentication hardening,
- production-grade audit logging,
- stronger privacy and security controls,
- standardized environment and dependency management,
- expanded automated testing,
- reproducible ML evaluation pipelines,
- stronger simulation validation,
- real-time hospital-resource integration,
- enhanced analytics dashboards,
- containerized deployment,
- CI/CD,
- and validation using appropriately governed healthcare datasets.

---

# License

Refer to the [`LICENSE`](./LICENSE) file for licensing information.

---

# Authors

- **Salar Momeni**
- **Akanksha R. Swamy**
- **Dima Alqaruoti**
- **Sahil Khokhar**

Academic Emergency Department patient-flow decision-support project developed at the **University of Ottawa**.
