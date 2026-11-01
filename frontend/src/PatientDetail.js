import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import "./Dashboard.css";
import ehosp from "./assets/ehosp.png";
import { apiGet, apiPost, apiUrl } from "./api";
import { IMAGING_SERVICES, LAB_SERVICES } from "./serviceCatalog";

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

const fieldLabelStyle = { display: "block", marginBottom: "8px", fontWeight: 700, color: "#1B2559", fontSize: "13px" };
const fieldInputStyle = { width: "100%", padding: "12px 14px", borderRadius: "12px", border: "1px solid #DCE3F1", fontSize: "14px" };

const PatientDetail = () => {
  const { p_id } = useParams();
  const navigate = useNavigate();
  const userEmail = localStorage.getItem("userEmail") || "clinical.staff@hospital.com";
  const [detail, setDetail] = useState(null);
  const [formData, setFormData] = useState({
    full_name: "",
    age: "",
    gender: "",
    phone: "",
    address: "",
    health_card_number: "",
    emergency_contact: "",
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
  const [routeNotice, setRouteNotice] = useState("");
  const [serviceLoading, setServiceLoading] = useState(false);
  const [labService, setLabService] = useState(LAB_SERVICES[0]);
  const [imagingService, setImagingService] = useState(IMAGING_SERVICES[0]);

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
        full_name: response.full_name || response.name || "",
        age: response.age ?? "",
        gender: response.gender || "",
        phone: response.phone || "",
        address: response.address || "",
        health_card_number: response.health_card_number || "",
        emergency_contact: response.emergency_contact || "",
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
        full_name: formData.full_name,
        age: toNumberOrNull(formData.age),
        gender: formData.gender,
        phone: formData.phone,
        address: formData.address,
        health_card_number: formData.health_card_number,
        emergency_contact: formData.emergency_contact,
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
      setRouteNotice("");
    } catch (saveError) {
      setError(saveError.message);
    } finally {
      setSaving(false);
    }
  };

  const handleSendToService = async (service, requestedService) => {
    setServiceLoading(true);
    setError("");
    setRouteNotice("");
    try {
      await apiPost("/patient/send-to-service", {
        p_id,
        service,
        requested_service: requestedService,
        scenario: "normal",
      });
      setRouteNotice(`Patient routed to ${service} for ${requestedService}. The ${service} queue now includes this case.`);
      await loadDetail();
    } catch (serviceError) {
      setError(serviceError.message);
    } finally {
      setServiceLoading(false);
    }
  };

  const renderField = (label, name, value, type = "text", step) => (
    <div>
      <label style={fieldLabelStyle}>{label}</label>
      {editing ? (
        <input type={type} step={step} name={name} value={formData[name]} onChange={handleChange} style={fieldInputStyle} />
      ) : (
        <div className="stat-card"><div className="stat-body"><p>{displayValue(value)}</p></div></div>
      )}
    </div>
  );

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
          <div className="nav-item" onClick={() => navigate("/lab")}><span style={{ marginRight: "12px" }}>Lab</span> Lab</div>
          <div className="nav-item" onClick={() => navigate("/imaging")}><span style={{ marginRight: "12px" }}>Img</span> Imaging</div>
          <a className="nav-item" href={chatbotUrl} target="_blank" rel="noreferrer" style={{ textDecoration: "none", color: "inherit" }}><span style={{ marginRight: "12px" }}>AI</span> Triage Agent</a>
        </div>
        <div className="logout-section" onClick={handleLogout}><span style={{ marginRight: "12px" }}>Log out</span></div>
      </div>

      <div className="main-content">
        <p style={{ color: "#707EAE", fontSize: "14px" }}>Pages / Patient Detail</p>
        <div className="welcome-banner" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "20px" }}>
          <div>
            <h1 style={{ marginBottom: "8px" }}>Patient Detail</h1>
            <p style={{ margin: 0 }}>View local identity data separately from clinical triage data while keeping the existing eHospital workflow intact.</p>
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
        {routeNotice ? <div style={{ marginTop: "18px", color: "#05CD99", fontWeight: 700 }}>{routeNotice}</div> : null}

        {detail ? (
          <div style={{ display: "grid", gridTemplateColumns: "1.15fr 0.85fr", gap: "22px", marginTop: "24px" }}>
            <div>
              <div className="patient-table-container">
                <h3 style={{ marginTop: 0 }}>Local Patient Identity</h3>
                <p style={{ color: "#707EAE", fontSize: "13px", marginTop: 0 }}>Personal identity data stays local and is not sent to the triage language model.</p>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "14px" }}>
                  {renderField("Full Name", "full_name", detail.full_name || detail.name)}
                  {renderField("Age", "age", detail.age, "number")}
                  {renderField("Sex / Gender", "gender", detail.gender)}
                  {renderField("Phone", "phone", detail.phone)}
                  <div style={{ gridColumn: "1 / -1" }}>{renderField("Address", "address", detail.address)}</div>
                  {renderField("Health Card Number", "health_card_number", detail.health_card_number)}
                  {renderField("Emergency Contact", "emergency_contact", detail.emergency_contact)}
                </div>
              </div>

              <div className="patient-table-container" style={{ marginTop: "22px" }}>
                <h3 style={{ marginTop: 0 }}>Editable Clinical Fields</h3>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
                  <div style={{ gridColumn: "1 / -1" }}>
                    <label style={fieldLabelStyle}>Symptoms / Chief Complaint</label>
                    {editing ? (
                      <textarea name="symptoms" value={formData.symptoms} onChange={handleChange} rows={3} style={{ ...fieldInputStyle, resize: "vertical" }} />
                    ) : (
                      <div className="stat-card"><div className="stat-body"><p>{displayValue(detail.chief_complaint)}</p></div></div>
                    )}
                  </div>
                  {renderField("Pain Scale", "pain_scale", detail.pain_scale, "number")}
                  <div>
                    <label style={fieldLabelStyle}>Local Notes</label>
                    {editing ? (
                      <textarea name="notes" value={formData.notes} onChange={handleChange} rows={3} style={{ ...fieldInputStyle, resize: "vertical" }} />
                    ) : (
                      <div className="stat-card"><div className="stat-body"><p>{displayValue(detail.notes)}</p></div></div>
                    )}
                  </div>
                </div>
              </div>

              <div className="patient-table-container" style={{ marginTop: "22px" }}>
                <h3 style={{ marginTop: 0 }}>Nurse Vitals</h3>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "14px" }}>
                  {renderField("Systolic BP", "systolic_bp", detail.systolic_bp, "number")}
                  {renderField("Temperature", "temperature", detail.temperature, "number", "0.1")}
                  {renderField("Heart Rate", "heart_rate", detail.heart_rate, "number")}
                  {renderField("SpO2", "spo2", detail.spo2, "number", "0.1")}
                  {renderField("Respiratory Rate", "respiratory_rate", detail.respiratory_rate, "number")}
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
              <div className="ai-stat-row"><span>Requested Service</span><span className="val">{detail.requested_service || "None"}</span></div>
              <div className="ai-stat-row"><span>Estimated Wait</span><span className="val">{Math.round(detail.estimated_wait_minutes || 0)} min</span></div>
              <div className="ai-card critical">
                <h4>{editing ? "Editing enabled" : "Read-only view"}</h4>
                <p>{editing ? "Update local identity fields, symptoms, notes, and nurse vitals. Personal identity stays local and only anonymized symptom text goes to the Triage Agent." : "Use Edit Patient Info to update the local patient record and the latest clinical details."}</p>
                {editing ? (
                  <button className="execute-btn" onClick={handleSave} disabled={saving}>{saving ? "Saving..." : "Save Changes"}</button>
                ) : (
                  <button className="execute-btn" onClick={() => setEditing(true)}>Edit Patient Info</button>
                )}
                <button className="execute-btn" onClick={() => navigate(`/clinical/${p_id}`)} style={{ marginTop: "8px", background: "#05CD99" }}>Open Clinical Summary</button>
              </div>

              <div className="ai-card critical" style={{ marginTop: "14px" }}>
                <h4>Route to Lab</h4>
                <p style={{ color: "#707EAE", fontSize: "13px", lineHeight: 1.7 }}>Select the exact lab service for this patient. The case will appear in the Lab queue immediately.</p>
                <select value={labService} onChange={(event) => setLabService(event.target.value)} style={{ width: "100%", padding: "12px 14px", borderRadius: "12px", border: "1px solid #DCE3F1", marginBottom: "10px" }}>
                  {LAB_SERVICES.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
                <div style={{ display: "flex", gap: "10px" }}>
                  <button className="execute-btn" onClick={() => handleSendToService("lab", labService)} disabled={serviceLoading} style={{ background: "#4318FF", flex: 1 }}>
                    {serviceLoading ? "Routing..." : "Send to Lab"}
                  </button>
                  <button className="execute-btn" onClick={() => navigate("/lab")} style={{ background: "#A3AED0", flex: 1 }}>Open Lab Queue</button>
                </div>
              </div>

              <div className="ai-card critical" style={{ marginTop: "14px" }}>
                <h4>Route to Imaging</h4>
                <p style={{ color: "#707EAE", fontSize: "13px", lineHeight: 1.7 }}>Select the imaging study for this patient. The case will appear in the Imaging queue immediately.</p>
                <select value={imagingService} onChange={(event) => setImagingService(event.target.value)} style={{ width: "100%", padding: "12px 14px", borderRadius: "12px", border: "1px solid #DCE3F1", marginBottom: "10px" }}>
                  {IMAGING_SERVICES.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
                <div style={{ display: "flex", gap: "10px" }}>
                  <button className="execute-btn" onClick={() => handleSendToService("imaging", imagingService)} disabled={serviceLoading} style={{ background: "#0095FF", flex: 1 }}>
                    {serviceLoading ? "Routing..." : "Send to Imaging"}
                  </button>
                  <button className="execute-btn" onClick={() => navigate("/imaging")} style={{ background: "#A3AED0", flex: 1 }}>Open Imaging Queue</button>
                </div>
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default PatientDetail;
