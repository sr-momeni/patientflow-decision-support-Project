import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Dashboard.css";

const DEFAULT_FORM = {
  p_id: localStorage.getItem("currentPatientId") || "",
  Pain_assessment_pain_scale: 0,
  pain_pattern: "",
  modifying_factors: "",
  cns_speech_clarity: "",
  consciousness_status: "",
  fever_infection: "",
  gi_symptoms: "",
  recent_sick_contact: "",
  respiratory_sob_status: "",
  cough_type: "",
  breathing_effort: "",
  systolic_bp: "",
  temperature: "",
  heart_rate: "",
  spo2: "",
  respiratory_rate: "",
};

const VITAL_FIELDS = ["systolic_bp", "temperature", "heart_rate", "spo2", "respiratory_rate"];

const TriageForm2 = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState(() => {
    const saved = localStorage.getItem("triage_step2_data");
    return saved ? JSON.parse(saved) : DEFAULT_FORM;
  });

  useEffect(() => {
    localStorage.setItem("triage_step2_data", JSON.stringify(formData));
  }, [formData]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData((current) => ({
      ...current,
      [name]: name === "Pain_assessment_pain_scale" ? Number(value) : value,
    }));
  };

  const handleNextStep = () => {
    navigate("/triage-form-3");
  };

  const providedVitals = VITAL_FIELDS.filter((fieldName) => String(formData[fieldName] ?? "").trim()).length;

  return (
    <div className="dashboard-container" style={{ display: "block", backgroundColor: "#F4F7FE", minHeight: "100vh", paddingBottom: "120px", overflowY: "auto" }}>
      <div style={{ backgroundColor: "white", padding: "15px 40px", display: "flex", alignItems: "center", borderBottom: "1px solid #E0E5F2", position: "sticky", top: 0, zIndex: 100 }}>
        <div style={{ backgroundColor: "#0095FF", padding: "8px", borderRadius: "8px", marginRight: "15px" }}>
          <img src="https://img.icons8.com/material-rounded/24/ffffff/hospital.png" alt="icon" style={{ width: "20px" }} />
        </div>
        <div>
          <h2 style={{ fontSize: "18px", margin: 0, color: "#1B2559" }}>Emergency Department</h2>
          <p style={{ fontSize: "12px", margin: 0, color: "#A3AED0" }}>Clinical Condition and Nurse Vitals</p>
        </div>
      </div>

      <div style={{ backgroundColor: "white", padding: "15px 40px", borderBottom: "1px solid #E0E5F2" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "8px" }}>
          <span style={{ fontSize: "12px", fontWeight: "600", color: "#0095FF" }}>Step 2 of 3</span>
          <span style={{ fontSize: "12px", fontWeight: "500", color: "#A3AED0" }}>Clinical Condition and Nurse Vitals</span>
        </div>
        <div style={{ height: "6px", width: "100%", backgroundColor: "#F4F7FE", borderRadius: "10px" }}>
          <div style={{ width: "66.66%", height: "100%", backgroundColor: "#2B68FF", borderRadius: "10px" }} />
        </div>
      </div>

      <div style={{ maxWidth: "900px", margin: "30px auto", display: "flex", flexDirection: "column", gap: "25px", padding: "0 20px" }}>
        <div className="triage-card-refined" style={{ borderRadius: "15px", backgroundColor: "white", padding: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "18px", marginBottom: "20px" }}>
            <div style={{ display: "flex", alignItems: "center" }}>
              <img src="https://img.icons8.com/color/48/nurse-female.png" alt="vitals" style={{ width: "24px", marginRight: "10px" }} />
              <h3 style={{ margin: 0, color: "#1B2559" }}>Nurse-entered vitals</h3>
            </div>
            <div style={{ padding: "8px 12px", borderRadius: "12px", backgroundColor: providedVitals === VITAL_FIELDS.length ? "#E6FAF4" : "#FFF4E8", color: providedVitals === VITAL_FIELDS.length ? "#05CD99" : "#FFB547", fontWeight: "700", fontSize: "12px" }}>
              {providedVitals === VITAL_FIELDS.length ? "Assessment can be finalized" : "Missing vitals keeps CTAS preliminary"}
            </div>
          </div>

          <p style={{ marginTop: 0, color: "#707EAE", fontSize: "13px", lineHeight: 1.7 }}>
            Enter measured vitals if available. Leave blank if not yet checked; the backend will keep the assessment marked as preliminary instead of inventing normal values.
          </p>

          <div className="input-grid">
            <div className="input-group">
              <label className="triage-label">Systolic BP (mmHg)</label>
              <input className="triage-input" type="number" name="systolic_bp" value={formData.systolic_bp} onChange={handleChange} placeholder="e.g. 118" />
            </div>
            <div className="input-group">
              <label className="triage-label">Temperature (C)</label>
              <input className="triage-input" type="number" step="0.1" name="temperature" value={formData.temperature} onChange={handleChange} placeholder="e.g. 37.2" />
            </div>
            <div className="input-group">
              <label className="triage-label">Heart Rate (bpm)</label>
              <input className="triage-input" type="number" name="heart_rate" value={formData.heart_rate} onChange={handleChange} placeholder="e.g. 96" />
            </div>
            <div className="input-group">
              <label className="triage-label">SpO2 (%)</label>
              <input className="triage-input" type="number" step="0.1" name="spo2" value={formData.spo2} onChange={handleChange} placeholder="e.g. 97" />
            </div>
            <div className="input-group">
              <label className="triage-label">Respiratory Rate (/min)</label>
              <input className="triage-input" type="number" name="respiratory_rate" value={formData.respiratory_rate} onChange={handleChange} placeholder="e.g. 18" />
            </div>
          </div>
        </div>

        <div className="triage-card-refined" style={{ borderRadius: "15px", backgroundColor: "white", padding: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", marginBottom: "20px" }}>
            <img src="https://img.icons8.com/color/48/thermometer.png" alt="pain" style={{ width: "24px", marginRight: "10px" }} />
            <h3 style={{ margin: 0, color: "#1B2559" }}>Pain Assessment</h3>
          </div>

          <label className="triage-label">Pain Scale (0-10)</label>
          <div style={{ display: "flex", alignItems: "center", gap: "15px", margin: "20px 0" }}>
            <span style={{ color: "#A3AED0" }}>0</span>
            <input
              type="range"
              min="0"
              max="10"
              name="Pain_assessment_pain_scale"
              value={formData.Pain_assessment_pain_scale}
              onChange={handleChange}
              style={{ flex: 1, accentColor: "#0095FF" }}
            />
            <span style={{ color: "#A3AED0" }}>10</span>
            <div style={{ padding: "8px 18px", background: "#F4F7FE", borderRadius: "8px", fontWeight: "bold", color: "#0095FF" }}>
              {formData.Pain_assessment_pain_scale}
            </div>
          </div>

          <div className="input-grid">
            <div className="input-group">
              <label className="triage-label">Pain Pattern</label>
              <select className="triage-input" name="pain_pattern" value={formData.pain_pattern} onChange={handleChange}>
                <option value="">Select pattern</option>
                <option value="Constant">Constant</option>
                <option value="Intermittent">Intermittent</option>
              </select>
            </div>
            <div className="input-group">
              <label className="triage-label">Modifying Factors</label>
              <select className="triage-input" name="modifying_factors" value={formData.modifying_factors} onChange={handleChange}>
                <option value="">Select factors</option>
                <option value="Worse with movement">Worse with movement</option>
                <option value="Better with rest">Better with rest</option>
              </select>
            </div>
          </div>
        </div>

        <div className="triage-card-refined" style={{ borderRadius: "15px", backgroundColor: "white", padding: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", marginBottom: "20px" }}>
            <img src="https://img.icons8.com/color/48/brain.png" alt="brain" style={{ width: "24px", marginRight: "10px" }} />
            <h3 style={{ margin: 0, color: "#1B2559" }}>Neurologic Status</h3>
          </div>
          <div className="input-grid">
            <div className="input-group">
              <label className="triage-label">Speech Clarity</label>
              <select className="triage-input" name="cns_speech_clarity" value={formData.cns_speech_clarity} onChange={handleChange}>
                <option value="">Assess speech</option>
                <option value="Clear">Clear</option>
                <option value="Slurred">Slurred</option>
              </select>
            </div>
            <div className="input-group">
              <label className="triage-label">Consciousness Status</label>
              <select className="triage-input" name="consciousness_status" value={formData.consciousness_status} onChange={handleChange}>
                <option value="">Assess consciousness</option>
                <option value="Alert">Alert</option>
                <option value="Confused">Confused</option>
                <option value="Unresponsive">Unresponsive</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      <div className="triage-card-refined" style={{ borderRadius: "12px", backgroundColor: "white", padding: "30px", marginBottom: "20px", maxWidth: "850px", margin: "0 auto 20px auto" }}>
        <div style={{ display: "flex", alignItems: "center", marginBottom: "20px" }}>
          <img src="https://img.icons8.com/color/48/coronavirus.png" alt="infection" style={{ width: "22px", marginRight: "10px" }} />
          <h3 style={{ margin: 0, color: "#1B2559", fontSize: "18px", fontWeight: "700" }}>Infection and Fever</h3>
        </div>

        <div className="input-grid" style={{ display: "flex", gap: "25px", justifyContent: "flex-start" }}>
          <div className="input-group" style={{ width: "280px" }}>
            <label className="triage-label" style={{ fontSize: "14px", color: "#1B2559", marginBottom: "8px", display: "block" }}>Fever/Chills</label>
            <select className="triage-input" name="fever_infection" value={formData.fever_infection} onChange={handleChange}>
              <option value="">Select status</option>
              <option value="Yes">Yes</option>
              <option value="No">No</option>
            </select>
          </div>
          <div className="input-group" style={{ width: "280px" }}>
            <label className="triage-label" style={{ fontSize: "14px", color: "#1B2559", marginBottom: "8px", display: "block" }}>GI Symptoms</label>
            <select className="triage-input" name="gi_symptoms" value={formData.gi_symptoms} onChange={handleChange}>
              <option value="">Select symptoms</option>
              <option value="None">None</option>
              <option value="Nausea">Nausea</option>
              <option value="Vomiting">Vomiting</option>
            </select>
          </div>
          <div className="input-group" style={{ width: "280px" }}>
            <label className="triage-label" style={{ fontSize: "14px", color: "#1B2559", marginBottom: "8px", display: "block" }}>Recent Sick Contact</label>
            <select className="triage-input" name="recent_sick_contact" value={formData.recent_sick_contact} onChange={handleChange}>
              <option value="">Select exposure</option>
              <option value="None">None</option>
              <option value="Known Exposure">Known Exposure</option>
            </select>
          </div>
        </div>
      </div>

      <div className="triage-card-refined" style={{ borderRadius: "12px", backgroundColor: "white", padding: "30px", marginBottom: "20px", maxWidth: "850px", margin: "0 auto 20px auto" }}>
        <div style={{ display: "flex", alignItems: "center", marginBottom: "20px" }}>
          <img src="https://img.icons8.com/color/48/lungs.png" alt="lungs" style={{ width: "22px", marginRight: "10px" }} />
          <h3 style={{ margin: 0, color: "#1B2559", fontSize: "18px", fontWeight: "700" }}>Respiratory Assessment</h3>
        </div>

        <div className="input-grid" style={{ display: "flex", gap: "25px", justifyContent: "flex-start" }}>
          <div className="input-group" style={{ width: "280px" }}>
            <label className="triage-label" style={{ fontSize: "14px", color: "#1B2559", marginBottom: "8px", display: "block" }}>Shortness of Breath</label>
            <select className="triage-input" name="respiratory_sob_status" value={formData.respiratory_sob_status} onChange={handleChange}>
              <option value="">Assess breathing</option>
              <option value="None">None</option>
              <option value="Mild">Mild</option>
              <option value="Moderate">Moderate</option>
              <option value="Severe">Severe</option>
            </select>
          </div>
          <div className="input-group" style={{ width: "280px" }}>
            <label className="triage-label" style={{ fontSize: "14px", color: "#1B2559", marginBottom: "8px", display: "block" }}>Cough Type</label>
            <select className="triage-input" name="cough_type" value={formData.cough_type} onChange={handleChange}>
              <option value="">Select cough type</option>
              <option value="None">None</option>
              <option value="Dry">Dry</option>
              <option value="Productive">Productive</option>
            </select>
          </div>
          <div className="input-group" style={{ width: "280px" }}>
            <label className="triage-label" style={{ fontSize: "14px", color: "#1B2559", marginBottom: "8px", display: "block" }}>Breathing Effort</label>
            <select className="triage-input" name="breathing_effort" value={formData.breathing_effort} onChange={handleChange}>
              <option value="">Assess effort</option>
              <option value="Normal">Normal</option>
              <option value="Labored">Labored</option>
            </select>
          </div>
        </div>
      </div>

      <div style={{ position: "fixed", bottom: 0, left: 0, right: 0, backgroundColor: "white", padding: "20px 40px", display: "flex", justifyContent: "space-between", borderTop: "1px solid #E0E5F2", zIndex: 100 }}>
        <button onClick={() => navigate(-1)} style={{ backgroundColor: "#707EAE", color: "white", padding: "12px 30px", border: "none", borderRadius: "10px", cursor: "pointer", fontWeight: "600" }}>
          Back
        </button>
        <button onClick={handleNextStep} style={{ backgroundColor: "#2B68FF", color: "white", padding: "12px 45px", border: "none", borderRadius: "10px", cursor: "pointer", fontWeight: "bold" }}>
          Next Step ->
        </button>
      </div>
    </div>
  );
};

export default TriageForm2;
