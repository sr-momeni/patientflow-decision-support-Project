import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import "./Dashboard.css";
import ehosp from "./assets/ehosp.png";
import { apiGet, apiPost, apiUrl } from "./api";

const toNumberOrNull = (value) => {
  if (value === null || value === undefined) return null;
  const text = String(value).trim();
  if (!text) return null;
  const number = Number(text);
  return Number.isFinite(number) ? number : null;
};

const displayValue = (value, fallback = "Not provided") => {
  if (value === null || value === undefined) return fallback;
  const text = String(value).trim();
  return text || fallback;
};

const PatientDetail = () => {
  const { p_id } = useParams();
  const navigate = useNavigate();
  const userEmail = localStorage.getItem("userEmail") || "clinical.staff@hospital.com";
  const [detail, setDetail] = useState(null);
  const [formData, setFormData] = useState({
    symptoms: "",
    pain_scale: "",
    notes: "",
    systolic_bp: "",
    temperature: "",
    heart_rate: "",
    spo2: "",
    respiratory_rate: "",
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [editing, setEditing] = useState(false);
  const [error, setError] = useState("");

  const chatbotUrl = useMemo(() => {
    const returnUrl = encodeURIComponent(`${window.location.origin}/patient/${p_id}`);
    return `${apiUrl("/chatbot/ui")}?v=chatbot-text-ui-20260324&returnUrl=${returnUrl}`;
  }, [p_id]);

  const loadDetail = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiGet(`/clinical/${p_id}`);
      setDetail(response);
      setFormData({
        symptoms: response.chief_complaint || "",
        pain_scale: response.pain_scale ?? "",
        notes: response.notes || "",
        systolic_bp: response.systolic_bp ?? "",
        temperature: response.temperature ?? "",
        heart_rate: response.heart_rate ?? "",
        spo2: response.spo2 ?? "",
        respiratory_rate: response.respiratory_rate ?? "",
      });
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }, [p_id]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  const handleLogout = () => {
    localStorage.clear();
    navigate("/");
  };

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData((current) => ({ ...current, [name]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    setError("");
    try {
      const response = await apiPost("/patient/update", {
        p_id,
        scenario: "normal",
        symptoms: formData.symptoms,
        pain_scale: toNumberOrNull(formData.pain_scale),
        notes: formData.notes,
        nurse_vitals: {
          systolic_bp: toNumberOrNull(formData.systolic_bp),
          temperature: toNumberOrNull(formData.temperature),
          heart_rate: toNumberOrNull(formData.heart_rate),
          spo2: toNumberOrNull(formData.spo2),
          respiratory_rate: toNumberOrNull(formData.respiratory_rate),
        },
      });
      setDetail(response);
      setEditing(false);
    } catch (saveError) {
      setError(saveError.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="dashboard-container">
      <div className="sidebar">
        <div className="logo-section">
          <img src={ehosp} alt="E-Hospital Logo" style={{ width: "200px", height: "80px", objectFit: "contain", display: "block" }} />
        </div>
        <div className="nav-menu">
          <div className="nav-item" onClick={() => navigate("/dashboard")}><span style={{ marginRight: "12px" }}>Home</span> Dashboard</div>
          <div className="nav-item" onClick={() => navigate("/new-patient")}><span style={{ marginRight: "12px" }}>+</span> Add New Patient</div>
          <div className="nav-item" onClick={() => navigate("/bed-assignments")}><span style={{ marginRight: "12px" }}>Bed</span> Assignments</div>
          <a className="nav-item" href={chatbotUrl} target="_blank" rel="noreferrer" style={{ textDecoration: "none", color: "inherit" }}><span style={{ marginRight: "12px" }}>AI</span> Triage Agent</a>
        </div>
        <div className="logout-section" onClick={handleLogout}><span style={{ marginRight: "12px" }}>Log out</span></div>
      </div>

      <div className="main-content">
        <p style={{ color: "#707EAE", fontSize: "14px" }}>Pages / Patient Detail</p>
        <div className="welcome-banner" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "20px" }}>
          <div>
            <h1 style={{ marginBottom: "8px" }}>Patient Detail</h1>
            <p style={{ margin: 0 }}>View and update the latest local patient record without changing the surrounding eHospital workflow.</p>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "13px", opacity: 0.86, marginBottom: "10px" }}>{userEmail}</div>
            <button className="execute-btn" onClick={() => setEditing((current) => !current)} style={{ background: editing ? "#A3AED0" : "#4318FF" }}>
              {editing ? "Cancel Edit" : "Edit Patient Info"}
            </button>
          </div>
        </div>

        {loading ? <div style={{ marginTop: "18px", color: "#707EAE" }}>Loading patient detail...</div> : null}
        {error ? <div style={{ marginTop: "18px", color: "#EE5D50" }}>Failed to load patient detail: {error}</div> : null}

        {detail ? (
          <div style={{ display: "grid", gridTemplateColumns: "1.15fr 0.85fr", gap: "22px", marginTop: "24px" }}>
            <div>
              <div className="patient-table-container">
                <h3 style={{ marginTop: 0 }}>Patient Info</h3>
                <div className="stats-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: "18px" }}>
                  <div className="stat-card"><div className="stat-header"><span>Patient ID</span></div><div className="stat-body"><p>{detail.patient_id}</p></div></div>
                  <div className="stat-card"><div className="stat-header"><span>Name</span></div><div className="stat-body"><p>{displayValue(detail.name, "Unknown")}</p></div></div>
                  <div className="stat-card"><div className="stat-header"><span>Age</span></div><div className="stat-body"><p>{displayValue(detail.age)}</p></div></div>
                  <div className="stat-card"><div className="stat-header"><span>Arrival</span></div><div className="stat-body"><p>{displayValue(detail.arrival_time)}</p></div></div>
                </div>
                <div className="ai-card critical">
                  <h4>Clinical summary</h4>
                  <p>{displayValue(detail.summary)}</p>
                </div>
              </div>

              <div className="patient-table-container" style={{ marginTop: "22px" }}>
                <h3 style={{ marginTop: 0 }}>Editable clinical fields</h3>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
                  <div style={{ gridColumn: "1 / -1" }}>
                    <label style={{ display: "block", marginBottom: "8px", fontWeight: 700, color: "#1B2559", fontSize: "13px" }}>Symptoms / Chief Complaint</label>
                    {editing ? (
                      <textarea name="symptoms" value={formData.symptoms} onChange={handleChange} rows={3} style={{ width: "100%", padding: "12px 14px", borderRadius: "12px", border: "1px solid #DCE3F1", fontSize: "14px" }} />
                    ) : (
                      <div className="stat-card"><div className="stat-body"><p>{displayValue(detail.chief_complaint)}</p></div></div>
                    )}
                  </div>
                  <div>
                    <label style={{ display: "block", marginBottom: "8px", fontWeight: 700, color: "#1B2559", fontSize: "13px" }}>Pain Scale</label>
                    {editing ? (
                      <input type="number" name="pain_scale" value={formData.pain_scale} onChange={handleChange} style={{ width: "100%", padding: "12px 14px", borderRadius: "12px", border: "1px solid #DCE3F1", fontSize: "14px" }} />
                    ) : (
                      <div className="stat-card"><div className="stat-body"><p>{displayValue(detail.pain_scale)}</p></div></div>
                    )}
                  </div>
                  <div>
                    <label style={{ display: "block", marginBottom: "8px", fontWeight: 700, color: "#1B2559", fontSize: "13px" }}>Notes</label>
                    {editing ? (
                      <textarea name="notes" value={formData.notes} onChange={handleChange} rows={3} style={{ width: "100%", padding: "12px 14px", borderRadius: "12px", border: "1px solid #DCE3F1", fontSize: "14px" }} />
                    ) : (
                      <div className="stat-card"><div className="stat-body"><p>{displayValue(detail.notes)}</p></div></div>
                    )}
                  </div>
                </div>
              </div>

              <div className="patient-table-container" style={{ marginTop: "22px" }}>
                <h3 style={{ marginTop: 0 }}>Nurse Vitals</h3>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "14px" }}>
                  {[
                    ["systolic_bp", "Systolic BP"],
                    ["temperature", "Temperature"],
                    ["heart_rate", "Heart Rate"],
                    ["spo2", "SpO2"],
                    ["respiratory_rate", "Respiratory Rate"],
                  ].map(([key, label]) => (
                    <div key={key}>
                      <label style={{ display: "block", marginBottom: "8px", fontWeight: 700, color: "#1B2559", fontSize: "13px" }}>{label}</label>
                      {editing ? (
                        <input type="number" step={key === "temperature" || key === "spo2" ? "0.1" : "1"} name={key} value={formData[key]} onChange={handleChange} style={{ width: "100%", padding: "12px 14px", borderRadius: "12px", border: "1px solid #DCE3F1", fontSize: "14px" }} />
                      ) : (
                        <div className="stat-card"><div className="stat-body"><p>{displayValue(detail[key])}</p></div></div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            </div>

            <div className="ai-panel">
              <h3>Assessment Snapshot</h3>
              <p className="ai-subtext"><b>Latest triage state</b></p>
              <div className="ai-stat-row"><span>CTAS</span><span className="val">{detail.ctas_name}</span></div>
              <div className="ai-stat-row"><span>Urgency</span><span className="val">{detail.urgency}</span></div>
              <div className="ai-stat-row"><span>Recommended Bed</span><span className="val">{detail.recommended_bed || "Pending"}</span></div>
              <div className="ai-stat-row"><span>Current Location</span><span className="val">{detail.current_location || detail.recommended_bed || "Pending"}</span></div>
              <div className="ai-stat-row"><span>Estimated Wait</span><span className="val">{Math.round(detail.estimated_wait_minutes || 0)} min</span></div>
              <div className="ai-card critical">
                <h4>{editing ? "Editing enabled" : "Read-only view"}</h4>
                <p>{editing ? "Update pain scale, symptoms, notes, and nurse vitals, then save the latest patient record." : "Use Edit Patient Info to update the latest patient record."}</p>
                {editing ? (
                  <button className="execute-btn" onClick={handleSave} disabled={saving}>{saving ? "Saving..." : "Save Changes"}</button>
                ) : (
                  <button className="execute-btn" onClick={() => setEditing(true)}>Edit Patient Info</button>
                )}
                <button className="execute-btn" onClick={() => navigate(`/clinical/${p_id}`)} style={{ marginTop: "8px", background: "#05CD99" }}>Open Clinical Summary</button>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default PatientDetail;
