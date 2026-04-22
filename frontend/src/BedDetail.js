import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import "./Dashboard.css";
import ehosp from "./assets/ehosp.png";
import { apiGet, apiPost, apiUrl } from "./api";
import { IMAGING_SERVICES, LAB_SERVICES } from "./serviceCatalog";

const WARD_OPTIONS = ["Cardiology", "Neurology", "ICU", "General Ward", "Surgery", "Observation Unit"];

const displayValue = (value, fallback = "-") => {
  if (value === null || value === undefined) return fallback;
  const text = String(value).trim();
  return text || fallback;
};

const BedDetail = () => {
  const { bed_id } = useParams();
  const navigate = useNavigate();
  const userEmail = localStorage.getItem("userEmail") || "clinical.staff@hospital.com";
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [actionLoading, setActionLoading] = useState(false);
  const [ward, setWard] = useState("Cardiology");
  const [labService, setLabService] = useState(LAB_SERVICES[0]);
  const [imagingService, setImagingService] = useState(IMAGING_SERVICES[0]);
  const [confirmTransfer, setConfirmTransfer] = useState(false);
  const [notice, setNotice] = useState("");

  const chatbotUrl = useMemo(() => {
    const returnUrl = encodeURIComponent(`${window.location.origin}/bed/${bed_id}`);
    return `${apiUrl("/chatbot/ui")}?v=chatbot-text-ui-20260324&returnUrl=${returnUrl}`;
  }, [bed_id]);

  const loadDetail = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiGet(`/beds/${bed_id}`);
      setDetail(response);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }, [bed_id]);

  useEffect(() => {
    loadDetail();
  }, [loadDetail]);

  const handleLogout = () => {
    localStorage.clear();
    navigate("/");
  };

  const handleDischarge = async () => {
    if (!detail?.patient?.patient_id) return;
    setActionLoading(true);
    setNotice("");
    setError("");
    try {
      await apiPost("/beds/discharge", { patient_id: detail.patient.patient_id, scenario: "normal" });
      setNotice("Patient discharged. Bed moved to cleaning and is not yet available.");
      await loadDetail();
    } catch (actionError) {
      setError(actionError.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleTransfer = async () => {
    if (!detail?.patient?.patient_id || !ward) return;
    setActionLoading(true);
    setNotice("");
    setError("");
    try {
      await apiPost("/beds/transfer", { patient_id: detail.patient.patient_id, ward, scenario: "normal" });
      setNotice(`Patient transferred to ${ward}. Bed moved to cleaning and is not yet available.`);
      setConfirmTransfer(false);
      await loadDetail();
    } catch (actionError) {
      setError(actionError.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleCleaningComplete = async () => {
    setActionLoading(true);
    setNotice("");
    setError("");
    try {
      await apiPost("/beds/cleaning-complete", { bed_id, scenario: "normal" });
      setNotice("Cleaning complete. Bed is now available for allocation.");
      await loadDetail();
    } catch (actionError) {
      setError(actionError.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleSendToService = async (service, requestedService) => {
    if (!detail?.patient?.patient_id) return;
    setActionLoading(true);
    setNotice("");
    setError("");
    try {
      const response = await apiPost("/patient/send-to-service", {
        p_id: detail.patient.patient_id,
        service,
        requested_service: requestedService,
        scenario: "normal",
      });
      setDetail(response);
      setNotice(`Patient sent to ${service} for ${requestedService}. They now appear in the ${service} queue.`);
    } catch (actionError) {
      setError(actionError.message);
    } finally {
      setActionLoading(false);
    }
  };

  const vitals = [
    ["Systolic BP", detail?.patient?.systolic_bp ? `${detail.patient.systolic_bp} mmHg` : null],
    ["Temperature", detail?.patient?.temperature ? `${detail.patient.temperature} C` : null],
    ["Heart Rate", detail?.patient?.heart_rate ? `${detail.patient.heart_rate} bpm` : null],
    ["SpO2", detail?.patient?.spo2 ? `${detail.patient.spo2}%` : null],
    ["Respiratory Rate", detail?.patient?.respiratory_rate ? `${detail.patient.respiratory_rate}/min` : null],
  ];

  const normalizedStatus = (detail?.bed_status || "").toLowerCase();
  const locationLabel = detail?.current_location ? String(detail.current_location).toLowerCase() : "";

  return (
    <div className="dashboard-container">
      <div className="sidebar">
        <div className="logo-section">
          <img src={ehosp} alt="E-Hospital Logo" style={{ width: "200px", height: "80px", objectFit: "contain", display: "block" }} />
        </div>
        <div className="nav-menu">
          <div className="nav-item" onClick={() => navigate("/dashboard")}><span style={{ marginRight: "12px" }}>Home</span> Dashboard</div>
          <div className="nav-item" onClick={() => navigate("/new-patient")}><span style={{ marginRight: "12px" }}>+</span> Add New Patient</div>
          <div className="nav-item active" onClick={() => navigate("/bed-assignments")}><span style={{ marginRight: "12px" }}>Bed</span> Assignments</div>
          <div className="nav-item" onClick={() => navigate("/lab")}><span style={{ marginRight: "12px" }}>Lab</span> Lab</div>
          <div className="nav-item" onClick={() => navigate("/imaging")}><span style={{ marginRight: "12px" }}>Img</span> Imaging</div>
          <a className="nav-item" href={chatbotUrl} target="_blank" rel="noreferrer" style={{ textDecoration: "none", color: "inherit" }}><span style={{ marginRight: "12px" }}>AI</span> Triage Agent</a>
        </div>
        <div className="logout-section" onClick={handleLogout}><span style={{ marginRight: "12px" }}>Log out</span></div>
      </div>

      <div className="main-content">
        <p style={{ color: "#707EAE", fontSize: "14px" }}>Pages / Bed Detail</p>
        <div className="welcome-banner" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "20px" }}>
          <div>
            <h1 style={{ marginBottom: "8px" }}>Bed Detail</h1>
            <p style={{ margin: 0 }}>Live assignment detail, patient routing actions, and current operational state for {bed_id}.</p>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "13px", opacity: 0.86, marginBottom: "10px" }}>{userEmail}</div>
            <button className="execute-btn" onClick={() => navigate("/bed-assignments")} style={{ background: "white", color: "#4318FF" }}>Back to Beds</button>
          </div>
        </div>

        {loading ? <div style={{ marginTop: "18px", color: "#707EAE" }}>Loading bed detail...</div> : null}
        {error ? <div style={{ marginTop: "18px", color: "#EE5D50" }}>Failed to load bed detail: {error}</div> : null}
        {notice ? <div style={{ marginTop: "18px", color: "#05CD99", fontWeight: 700 }}>{notice}</div> : null}

        {detail ? (
          <div style={{ display: "grid", gridTemplateColumns: "1.15fr 0.85fr", gap: "22px", marginTop: "24px" }}>
            <div>
              <div className="patient-table-container">
                <h3 style={{ marginTop: 0 }}>Bed Info</h3>
                <div className="stats-grid" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
                  <div className="stat-card"><div className="stat-header"><span>Bed ID</span></div><div className="stat-body"><p>{detail.bed_id}</p></div></div>
                  <div className="stat-card"><div className="stat-header"><span>Status</span></div><div className="stat-body"><p>{detail.bed_status}</p></div></div>
                  <div className="stat-card"><div className="stat-header"><span>Current Location</span></div><div className="stat-body"><p style={{ textTransform: "capitalize" }}>{detail.current_location}</p></div></div>
                </div>
              </div>

              <div className="patient-table-container" style={{ marginTop: "22px" }}>
                <h3 style={{ marginTop: 0 }}>Patient Info</h3>
                {detail.patient ? (
                  <>
                    <div className="stats-grid" style={{ gridTemplateColumns: "repeat(3, 1fr)", marginBottom: "18px" }}>
                      <div className="stat-card"><div className="stat-header"><span>Patient ID</span></div><div className="stat-body"><p>{detail.patient.patient_id}</p></div></div>
                      <div className="stat-card"><div className="stat-header"><span>CTAS</span></div><div className="stat-body"><p>{detail.patient.ctas_level}</p></div></div>
                      <div className="stat-card"><div className="stat-header"><span>Urgency</span></div><div className="stat-body"><p>{detail.patient.urgency}</p></div></div>
                      <div className="stat-card"><div className="stat-header"><span>Wait Time</span></div><div className="stat-body"><p>{Math.round(detail.patient.wait_time || 0)} min</p></div></div>
                      <div className="stat-card"><div className="stat-header"><span>Location</span></div><div className="stat-body"><p style={{ textTransform: "capitalize" }}>{detail.current_location}</p></div></div>
                      <div className="stat-card"><div className="stat-header"><span>Requested Service</span></div><div className="stat-body"><p>{displayValue(detail.patient.requested_service)}</p></div></div>
                    </div>
                    <div className="ai-card critical" style={{ marginBottom: "16px" }}>
                      <h4>Clinical Summary</h4>
                      <p>{detail.patient.summary || "No summary available."}</p>
                    </div>
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "14px" }}>
                      {vitals.map(([label, value]) => (
                        <div key={label} className="stat-card"><div className="stat-header"><span>{label}</span></div><div className="stat-body"><p>{displayValue(value)}</p></div></div>
                      ))}
                    </div>
                  </>
                ) : (
                  <div className="ai-card critical">
                    <h4>No patient assigned</h4>
                    <p>{normalizedStatus === "cleaning" ? "Cleaning is in progress. The bed will return to the allocation cycle after cleaning completion is confirmed." : "This bed currently has no active patient assignment."}</p>
                  </div>
                )}
              </div>
            </div>

            <div className="ai-panel">
              <h3>Actions</h3>
              <p className="ai-subtext"><b>Live bed operations</b></p>
              {detail.patient ? (
                <>
                  <button className="execute-btn" onClick={handleDischarge} disabled={actionLoading}>
                    {actionLoading ? "Updating..." : "Discharge Patient"}
                  </button>
                  <div style={{ marginTop: "12px" }}>
                    <label style={{ display: "block", marginBottom: "8px", color: "#707EAE", fontSize: "13px" }}>Transfer Patient</label>
                    <select value={ward} onChange={(event) => setWard(event.target.value)} style={{ width: "100%", padding: "12px 14px", borderRadius: "12px", border: "1px solid #DCE3F1", marginBottom: "10px" }}>
                      {WARD_OPTIONS.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                    <button className="execute-btn" onClick={() => setConfirmTransfer(true)} disabled={actionLoading} style={{ background: "#05CD99" }}>
                      Transfer Patient
                    </button>
                  </div>
                  <div className="ai-card critical" style={{ marginTop: "14px" }}>
                    <h4>Send to Lab</h4>
                    <p style={{ color: "#707EAE", fontSize: "13px", lineHeight: 1.7 }}>Choose the exact lab test. The patient will appear in the Lab queue immediately.</p>
                    <select value={labService} onChange={(event) => setLabService(event.target.value)} style={{ width: "100%", padding: "12px 14px", borderRadius: "12px", border: "1px solid #DCE3F1", marginBottom: "10px" }}>
                      {LAB_SERVICES.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                    <div style={{ display: "flex", gap: "10px" }}>
                      <button className="execute-btn" onClick={() => handleSendToService("lab", labService)} disabled={actionLoading} style={{ background: "#4318FF", flex: 1 }}>Send to Lab</button>
                      <button className="execute-btn" onClick={() => navigate("/lab")} style={{ background: "#A3AED0", flex: 1 }}>Open Lab Queue</button>
                    </div>
                  </div>
                  <div className="ai-card critical" style={{ marginTop: "14px" }}>
                    <h4>Send to Imaging</h4>
                    <p style={{ color: "#707EAE", fontSize: "13px", lineHeight: 1.7 }}>Choose the imaging study. The patient will appear in the Imaging queue immediately.</p>
                    <select value={imagingService} onChange={(event) => setImagingService(event.target.value)} style={{ width: "100%", padding: "12px 14px", borderRadius: "12px", border: "1px solid #DCE3F1", marginBottom: "10px" }}>
                      {IMAGING_SERVICES.map((option) => <option key={option} value={option}>{option}</option>)}
                    </select>
                    <div style={{ display: "flex", gap: "10px" }}>
                      <button className="execute-btn" onClick={() => handleSendToService("imaging", imagingService)} disabled={actionLoading} style={{ background: "#0095FF", flex: 1 }}>Send to Imaging</button>
                      <button className="execute-btn" onClick={() => navigate("/imaging")} style={{ background: "#A3AED0", flex: 1 }}>Open Imaging Queue</button>
                    </div>
                  </div>
                  {(locationLabel === "lab" || locationLabel === "imaging") ? (
                    <div className="ai-card critical" style={{ marginTop: "14px" }}>
                      <h4>Current downstream routing</h4>
                      <p style={{ marginBottom: "12px" }}>This patient is currently assigned to {locationLabel} {detail.patient.requested_service ? `for ${detail.patient.requested_service}` : ""}.</p>
                      <button className="execute-btn" onClick={() => navigate(`/${locationLabel}`)} style={{ background: locationLabel === "lab" ? "#4318FF" : "#0095FF" }}>
                        Open {locationLabel === "lab" ? "Lab" : "Imaging"} queue
                      </button>
                    </div>
                  ) : null}
                  <button className="execute-btn" onClick={() => navigate(`/patient/${detail.patient.patient_id}`)} style={{ marginTop: "14px", background: "#A3AED0" }}>Open Patient Detail</button>
                </>
              ) : normalizedStatus === "cleaning" ? (
                <div className="ai-card critical">
                  <h4>Cleaning required</h4>
                  <p>This bed is currently unavailable while cleaning is in progress.</p>
                  <button className="execute-btn" onClick={handleCleaningComplete} disabled={actionLoading} style={{ background: "#05CD99" }}>
                    {actionLoading ? "Updating..." : "Mark cleaning complete"}
                  </button>
                </div>
              ) : (
                <div className="ai-card critical"><h4>No patient actions available</h4><p>This bed is currently {detail.bed_status.toLowerCase()}.</p></div>
              )}
            </div>
          </div>
        ) : null}
      </div>

      {confirmTransfer ? (
        <div style={{ position: "fixed", inset: 0, background: "rgba(27,37,89,0.25)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 3000 }}>
          <div className="patient-table-container" style={{ width: "min(460px, calc(100vw - 32px))" }}>
            <h3 style={{ marginTop: 0 }}>Confirm transfer</h3>
            <p style={{ color: "#707EAE", lineHeight: 1.7 }}>Are you sure you want to transfer this patient to {ward}?</p>
            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px" }}>
              <button className="execute-btn" onClick={() => setConfirmTransfer(false)} style={{ background: "#A3AED0" }}>Cancel</button>
              <button className="execute-btn" onClick={handleTransfer} disabled={actionLoading} style={{ background: "#05CD99" }}>{actionLoading ? "Updating..." : "Confirm Transfer"}</button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
};

export default BedDetail;
