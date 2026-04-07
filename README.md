# Patient Flow Decision Support System (Full Documentation)

This document provides a comprehensive breakdown of every file and directory in this project. The system is a multi-layered application combining machine learning, discrete-event simulation, and a full-stack hospital management platform.

##  Overview

This system implements a **Predictive Bed Allocation AI** that:
- Predicts when critical patients (Urgency Level 1) will arrive
- Proactively reserves beds before they arrive
- Reduces wait times for life-threatening cases by 20-40% (target)
- Balances resource efficiency with patient safety

##  How the AI Works

### High-Level Flow

```
Patient Arrives → AI Predicts Critical Patient Coming → Reserve Bed → Assign When Critical Patient Arrives
```

### 1. Machine Learning Model (`backend/ml/predictor.py`)

**What It Predicts**: *"What's the probability a critical (Urgency Level 1) patient will arrive in the next 30 minutes?"*

**Training Data**: Historical patient arrival patterns

**Input Features**:
- **Time patterns**: Hour of day, day of week (e.g., Friday nights are busier)
- **Hospital state**: Current ED occupancy (%), ICU occupancy (%)
- **Recent trends**: Patient arrival rate in last 2 hours

**Model Type**: Random Forest Classifier
- 100 decision trees
- Each tree votes on the prediction
- Final probability = % of trees voting "yes"

**Performance**: 
- Precision: 94.4%
- Recall: 94.1%
- F1-Score: 94.2%

### 2. Predictive Simulation Engine (`backend/simulation/predictive_engine.py`)

**Real-time Decision Process**:

#### When a New Patient Arrives:

**Step 1: Calculate Current State**
```python
ed_occupancy = beds_in_use / 50  # e.g., 40/50 = 80%
icu_occupancy = beds_in_use / 20
recent_rate = arrivals_last_2_hours / 2  # patients per hour
```

**Step 2: Query AI Model**
```python
probability = model.predict(
    hour=14,                  # 2 PM
    day_of_week=5,           # Friday
    ed_occupancy=0.8,        # 80% full
    icu_occupancy=0.60,       # 60% full
    recent_rate=35           # 35 patients/hour
)
# Returns: 0.87 (87% chance critical patient coming soon)
```

**Step 3: Decision Logic**
```python
if probability > 0.70:  # 70% threshold
    reserve_1_ed_bed()
    reserve_1_icu_bed()
    set_timeout(30_minutes)  # Reservation expires if unused
```

**Step 4: Bed Assignment Rules**
- **Urgency Level 1 (Critical)**: Can use ANY bed (including reserved)
- **Urgency Level 2/3**: Can only use NON-reserved beds
- If all regular beds full → they wait, even if reserved beds are empty

### 3. Reservation System

```
Regular Bed Pool:     [■][■][■][■][■][■][■]... (48 beds)
Reserved Bed Pool:    [R][R]                    (2 beds)
                       ↑  ↑
                       Only for Urgency 1
```

**When a Critical Patient Arrives**:
1. Uses a reserved bed instantly
2. Reservation count decreases
3. Bed gets freed when patient is discharged

**When Reservation Times Out (30 min)**:
1. If no critical patient arrived
2. Reserved beds release back to regular pool
3. Waiting low-urgency patients can now use them

### 4. Real Example

**Scenario**: Friday 2 PM, Hospital is 80% Full

```
2:00 PM - Patient #47 (Urgency 3) arrives
         → AI checks: "87% chance critical patient in next 30 min"
         → Reserve 1 ED bed
         → Patient #47 waits (48 beds available, 1 reserved)

2:15 PM - Patient #48 (Urgency 1) arrives!
         → Gets reserved bed instantly (wait time = 0 min)
         → Reservation released

2:30 PM - If Patient #48 hadn't arrived
         → Reservation expires
         → Patient #47 gets the bed
```

##  Project Structure

```
patientflow-decision-support-Project/
├── backend/
│   ├── ml/
│   │   ├── predictor.py           # ML model for urgency prediction
│   │   └── train_model.py         # Training script
│   ├── simulation/
│   │   ├── event_model.py         # Patient and Hospital state models
│   │   ├── engine.py              # Standard FCFS simulation
│   │   ├── predictive_engine.py   # AI-powered simulation
│   │   ├── run_fcfs.py            # Run FCFS simulation
│   │   └── run_predictive.py      # Run predictive simulation
│   ├── data/
│   │   └── synthetic_generator.py # Generate synthetic patient data
│   └── optimization/
│       ├── allocation_rules.py    # Bed allocation logic
│       └── constraints.py         # Hospital capacity constraints
├── frontend/
│   ├── index.html                 # Interactive timeline dashboard
│   ├── script.js                  # Visualization logic
│   └── style.css                  # Modern UI styling
├── data/
│   ├── patients_2500.csv          # Original dataset
│   ├── patients_fcfs.csv          # FCFS simulation results
│   └── patients_predictive.csv    # AI simulation results
├── models/
│   └── urgency_predictor.pkl      # Trained ML model
└── convert_data.py                # CSV to frontend data converter
```

##  Setup Instructions

### Prerequisites
- Python 3.8+
- pip

### Installation

```bash
# Clone the repository
git clone https://github.com/salkhokhar/patientflow-decision-support-Project.git
cd patientflow-decision-support-Project

# Install dependencies
pip install -r requirements.txt
```

### Train the ML Model

```bash
# Generate synthetic patient data (if not already present)
python -m backend.data.synthetic_generator --n 2500 --output data/patients_2500.csv

# Train the predictive model
python -m backend.ml.train_model
```

### Run Simulations

```bash
# Run predictive AI simulation
python -m backend.simulation.run_predictive

# Convert data for frontend
python convert_data.py
```

### View Dashboard

Open `frontend/index.html` in a web browser to see:
- Interactive Gantt chart timeline
- Toggle between "Original" and "Predictive AI Allocation"
- Zoom/pan controls
- Patient wait time statistics

##  Performance Comparison

| Urgency Level | Original (min) | Predictive AI (min) | Target Improvement |
|---------------|----------------|---------------------|-------------------|
| **Level 1 (Critical)** | 177 | 2,825* | -20% to -40% |
| Level 2 | 520 | 8,711* | N/A |
| Level 3 | 612 | 9,893* | N/A |

*Current implementation has a reservation release bug. Fix in progress.

##  Known Issues

### Reservation Logic Bug
**Issue**: Beds aren't releasing properly after timeout or when critical patients use them.

**Impact**: System performs like FCFS instead of showing wait time improvements.

**Fix Required**:
- Track individual reservation expiry times
- Release beds when used OR timeout
- Update effective capacity dynamically

##  Features

- **Interactive Timeline**: Zoom and pan through patient flow
- **Color-coded Urgency**: Visual distinction between patient priorities
- **Separate ED/ICU Tracking**: Independent capacity management
- **Real-time Statistics**: Live calculation of wait times and occupancy
- **Comparison Mode**: Toggle between allocation strategies

##  License

## 📂 Root Directory
*   **`Chatbot`**: Entry point or utility script for the chatbot interface.
*   **`advanced_analysis.py`**: A powerful metrics engine that parses `simulation_events.log`. It calculates:
    *   Reservation Accuracy (Successful Catches vs. Expired Holds).
    *   Bed Occupancy Rate comparison (FCFS vs. AI).
    *   "Opportunity Cost" (Total wasted bed-minutes from false-positive reservations).
    *   Generates `reservation_pie.png` and `bed_time_bar.png`.
*   **`visualize_comparison.py`**: Generates high-level statistical reports comparing wait times and LOS across all urgency levels. Outputs `comparison_plot.png`.
*   **`patient_arrival_analysis.py`**: Statistical analyzer for raw arrival data. Helps verify if the synthetic generator is accurately mimicking national triage distributions.
*   **`convert_data.py`**: Data transformation utility. It converts backend simulation CSVs into the specific JSON/Array format required by the `frontend/script.js` for timeline rendering.
*   **`debug_analysis.py`**: A lightweight script for troubleshooting simulation logs and identifying malformed events.
*   **`requirements.txt`**: Project dependencies (FastAPI, Scikit-learn, Pandas, Seaborn, etc.).
*   **`pytest.ini`**: Configuration for automated backend testing.
*   **`openAI_key.txt`**: Secret storage for the Chatbot LLM integration (if enabled).

##  Authors
Salar Momeni
Sal Khokhar
Dima Alqaruoti
Akanksha R.Swamy

---

##  Technical Details

*   **`index.html`**: Dashboard layout with occupancy gauges, wait-time panels, and a Gantt chart container.
*   **`script.js`**: Massive UI engine.
    *   Handles timeline zooming/panning.
    *   Calculates average wait times from simulation data on-the-fly.
    *   Renders patient "lane" assignments in the Gantt chart.
*   **`data_predictive.js` / `data_fcfs.js`**: Transformed data payloads generated by `convert_data.py`.

---

## 📊 Data & Assets
*   **`/data/raw/`**: Source CSVs from the `synthetic_generator.py`.
*   **`/data/plots/`**: Visual evidence generated by the evaluation suite (pie charts, line graphs).
*   **`/models/`**: Stores the binary trained model file (`.pkl`).
*   **`/backend/legacy_v1/`**: An archive of the initial project version before the Priority Aging and DES overhaul.

##  Future Enhancements

## 🛠️ Key Scripts Summary
| Script | Purpose |
| :--- | :--- |
| `train_model.py` | Trains the AI to forecast arrival spikes. |
| `run_predictive.py` | Simulates hospital flow using the AI and Priority Aging. |
| `evaluate_agent.py` | Generates 15+ comparative metrics (Baseline vs. AI). |
| `convert_data.py` | Bridges Backend simulation → Frontend visualization. |
| `server.py` | Hosts the entire platform (Chatbot, Dashboard, eHospital). |
| `advanced_analysis.py` | Calculates the "Opportunity Cost" of bed reservations. |
