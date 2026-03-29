import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Dashboard.css";
import ehosp from "./assets/ehosp.png";
import { apiPost } from "./api";

const TRIAGE_KEYS = ["triage_step1_data", "triage_step2_data", "triage_step3_data", "lastTriageResult"];

const NewPatient = () => {
  const navigate = useNavigate();
  const [patientInfo, setPatientInfo] = useState({
    name: "",
    p_id: "",
    health_card: "",
    notes: "",
  });
  const [submitting, setSubmitting] = useState(false);

  const handleNext = async () => {
    if (!patientInfo.name || !patientInfo.p_id || !patientInfo.health_card) {
      alert("Please provide name, patient ID, and health card number.");
      return;
    }

    setSubmitting(true);
    try {
      const response = await apiPost("/add-patient", patientInfo);
      const resolvedPatientId = response.patient_id || response.id || patientInfo.p_id;
      TRIAGE_KEYS.forEach((key) => localStorage.removeItem(key));
      localStorage.setItem("currentPatientId", resolvedPatientId);
      localStorage.setItem("currentPatientName", patientInfo.name);
      navigate("/triage-form");
    } catch (error) {
      alert(`Failed to save patient: ${error.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="dashboard-container">
      <div className="sidebar">
        <div className="logo-section">
          <img src={ehosp} alt="E-Hospital Logo" style={{ width: "200px", height: "80px", objectFit: "contain", display: "block" }} />
        </div>

        <div className="nav-menu">
          <div className="nav-item" onClick={() => navigate("/dashboard")}>
            <div style={{ width: "38px", marginRight: "15px", textAlign: "center" }}>
              <img src="https://img.icons8.com/material-rounded/24/A3AED0/home.png" alt="home" style={{ width: "20px" }} />
            </div>
            <span className="nav-text">Dashboard</span>
          </div>
          <div className="nav-item active">
            <div className="icon-box-active">
              <span style={{ color: "white" }}>+</span>
            </div>
            <span style={{ fontWeight: "700" }}>Add New Patient</span>
          </div>
        </div>

        <div className="logout-section" onClick={() => navigate("/")}>
          <span style={{ marginRight: "12px" }}>Log out</span>
        </div>
      </div>

      <div className="main-content" style={{ backgroundColor: "#F4F7FE" }}>
        <p style={{ color: "#707EAE", fontSize: "14px" }}>Pages / Add New Patient</p>
        <br />

        <div className="patient-form-container" style={{ padding: "40px", backgroundColor: "white", borderRadius: "15px" }}>
          <h2 style={{ fontSize: "24px", fontWeight: "bold", marginBottom: "5px" }}>Patient Information</h2>
          <p style={{ color: "#707EAE", fontSize: "14px", marginBottom: "30px" }}>Please fill in the required information.</p>

          <form>
            <div className="form-group" style={{ marginBottom: "20px" }}>
              <label style={{ fontWeight: "bold", fontSize: "12px", display: "block", marginBottom: "8px" }}>First Name / Last Name</label>
              <input
                type="text"
                placeholder="Enter your name"
                value={patientInfo.name}
                onChange={(event) => setPatientInfo({ ...patientInfo, name: event.target.value })}
                style={{ width: "100%", padding: "10px", border: "1px solid #E0E5F2", borderRadius: "5px" }}
              />
            </div>

            <div className="form-group" style={{ marginBottom: "20px" }}>
              <label style={{ fontWeight: "bold", fontSize: "12px", display: "block", marginBottom: "8px" }}>Patient ID</label>
              <input
                type="text"
                placeholder="Enter patient ID"
                value={patientInfo.p_id}
                onChange={(event) => setPatientInfo({ ...patientInfo, p_id: event.target.value })}
                style={{ width: "100%", padding: "10px", border: "1px solid #E0E5F2", borderRadius: "5px" }}
              />
            </div>

            <div className="form-group" style={{ marginBottom: "20px" }}>
              <label style={{ fontWeight: "bold", fontSize: "12px", display: "block", marginBottom: "8px" }}>Health Card Number</label>
              <input
                type="text"
                placeholder="Enter health card number"
                value={patientInfo.health_card}
                onChange={(event) => setPatientInfo({ ...patientInfo, health_card: event.target.value })}
                style={{ width: "100%", padding: "10px", border: "1px solid #E0E5F2", borderRadius: "5px" }}
              />
            </div>

            <div className="form-group" style={{ marginBottom: "30px" }}>
              <label style={{ fontWeight: "bold", fontSize: "12px", display: "block", marginBottom: "8px" }}>Optional Notes</label>
              <input
                type="text"
                placeholder="Enter any notes"
                value={patientInfo.notes}
                onChange={(event) => setPatientInfo({ ...patientInfo, notes: event.target.value })}
                style={{ width: "100%", padding: "10px", border: "1px solid #E0E5F2", borderRadius: "5px" }}
              />
              <small style={{ color: "#A3AED0", fontSize: "10px" }}>Use this field for any additional information</small>
            </div>

            <button
              type="button"
              onClick={handleNext}
              disabled={submitting}
              style={{ backgroundColor: "#0047BB", color: "white", padding: "10px 40px", border: "none", borderRadius: "5px", cursor: "pointer", fontWeight: "bold" }}
            >
              {submitting ? "Saving..." : "Next"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
};

export default NewPatient;