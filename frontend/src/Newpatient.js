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
    age: "",
    gender: "",
    phone: "",
    address: "",
    health_card: "",
    emergency_contact: "",
    notes: "",
  });
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setPatientInfo((current) => ({ ...current, [name]: value }));
  };

  const handleNext = async () => {
    if (!patientInfo.name || !patientInfo.p_id) {
      alert("Please provide full name and patient ID.");
      return;
    }

    setSubmitting(true);
    try {
      const response = await apiPost("/add-patient", {
        name: patientInfo.name,
        full_name: patientInfo.name,
        p_id: patientInfo.p_id,
        age: patientInfo.age ? Number(patientInfo.age) : null,
        gender: patientInfo.gender,
        phone: patientInfo.phone,
        address: patientInfo.address,
        health_card: patientInfo.health_card,
        health_card_number: patientInfo.health_card,
        emergency_contact: patientInfo.emergency_contact,
        notes: patientInfo.notes,
      });
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

  const inputStyle = { width: "100%", padding: "10px", border: "1px solid #E0E5F2", borderRadius: "5px" };

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
          <p style={{ color: "#707EAE", fontSize: "14px", marginBottom: "12px" }}>Personal identity data is stored locally in eHospital and is not sent to the triage language model.</p>

          <form>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "20px" }}>
              <div className="form-group" style={{ marginBottom: "20px" }}>
                <label style={{ fontWeight: "bold", fontSize: "12px", display: "block", marginBottom: "8px" }}>Full Name</label>
                <input type="text" name="name" placeholder="Enter full name" value={patientInfo.name} onChange={handleChange} style={inputStyle} />
              </div>

              <div className="form-group" style={{ marginBottom: "20px" }}>
                <label style={{ fontWeight: "bold", fontSize: "12px", display: "block", marginBottom: "8px" }}>Patient ID</label>
                <input type="text" name="p_id" placeholder="Enter patient ID" value={patientInfo.p_id} onChange={handleChange} style={inputStyle} />
              </div>

              <div className="form-group" style={{ marginBottom: "20px" }}>
                <label style={{ fontWeight: "bold", fontSize: "12px", display: "block", marginBottom: "8px" }}>Age</label>
                <input type="number" name="age" placeholder="Enter age" value={patientInfo.age} onChange={handleChange} style={inputStyle} />
              </div>

              <div className="form-group" style={{ marginBottom: "20px" }}>
                <label style={{ fontWeight: "bold", fontSize: "12px", display: "block", marginBottom: "8px" }}>Sex / Gender</label>
                <input type="text" name="gender" placeholder="Enter sex or gender" value={patientInfo.gender} onChange={handleChange} style={inputStyle} />
              </div>

              <div className="form-group" style={{ marginBottom: "20px" }}>
                <label style={{ fontWeight: "bold", fontSize: "12px", display: "block", marginBottom: "8px" }}>Phone</label>
                <input type="text" name="phone" placeholder="Optional phone number" value={patientInfo.phone} onChange={handleChange} style={inputStyle} />
              </div>

              <div className="form-group" style={{ marginBottom: "20px" }}>
                <label style={{ fontWeight: "bold", fontSize: "12px", display: "block", marginBottom: "8px" }}>Health Card Number</label>
                <input type="text" name="health_card" placeholder="Optional health card number" value={patientInfo.health_card} onChange={handleChange} style={inputStyle} />
              </div>

              <div className="form-group" style={{ marginBottom: "20px", gridColumn: "1 / -1" }}>
                <label style={{ fontWeight: "bold", fontSize: "12px", display: "block", marginBottom: "8px" }}>Address</label>
                <input type="text" name="address" placeholder="Optional address" value={patientInfo.address} onChange={handleChange} style={inputStyle} />
              </div>

              <div className="form-group" style={{ marginBottom: "20px", gridColumn: "1 / -1" }}>
                <label style={{ fontWeight: "bold", fontSize: "12px", display: "block", marginBottom: "8px" }}>Emergency Contact</label>
                <input type="text" name="emergency_contact" placeholder="Optional emergency contact" value={patientInfo.emergency_contact} onChange={handleChange} style={inputStyle} />
              </div>
            </div>

            <div className="form-group" style={{ marginBottom: "30px" }}>
              <label style={{ fontWeight: "bold", fontSize: "12px", display: "block", marginBottom: "8px" }}>Optional Notes</label>
              <input type="text" name="notes" placeholder="Enter any local notes" value={patientInfo.notes} onChange={handleChange} style={inputStyle} />
              <small style={{ color: "#A3AED0", fontSize: "10px" }}>Identity data remains local and separate from symptom-only triage intake.</small>
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
