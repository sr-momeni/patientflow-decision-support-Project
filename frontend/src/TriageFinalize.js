import React, { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import "./Dashboard.css";
import ehosp from "./assets/ehosp.png";
import { apiGet, apiPost, apiUrl } from "./api";

const VITAL_FIELDS = [
  { key: "systolic_bp", label: "Systolic BP", type: "number", placeholder: "e.g. 118" },
  { key: "temperature", label: "Temperature", type: "number", step: "0.1", placeholder: "e.g. 37.2" },
  { key: "heart_rate", label: "Heart Rate", type: "number", placeholder: "e.g. 96" },
  { key: "spo2", label: "SpO2", type: "number", step: "0.1", placeholder: "e.g. 97" },
  { key: "respiratory_rate", label: "Respiratory Rate", type: "number", placeholder: "e.g. 18" },
];

const toNumberOrNull = (value) => {
  if (value === null || value === undefined) return null;
  const text = String(value).trim();
  if (!text) return null;
  const number = Number(text);
  return Number.isFinite(number) ? number : null;
};

const TriageFinalize = () => {
  const { p_id } = useParams();
  const navigate = useNavigate();
  const userEmail = localStorage.getItem("userEmail") || "clinical.staff@hospital.com";
  const [summaryData, setSummaryData] = useState(null);
  const [formData, setFormData] = useState({
    systolic_bp: "",
    temperature: "",
    heart_rate: "",
    spo2: "",
    respiratory_rate: "",
    nurse_note: "",
  });
  const [finalResult, setFinalResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  const chatbotUrl = useMemo(() => {
    const returnUrl = encodeURIComponent(`${window.location.origin}/triage-finalize/${p_id}`);
    return `${apiUrl("/chatbot/ui")}?v=chatbot-text-ui-20260324&returnUrl=${returnUrl}`;
  }, [p_id]);

  useEffect(() => {
    let mounted = true;

    const loadSummary = async () => {
      setLoading(true);
      setError("");
      try {
        const response = await apiGet(`/clinical/${p_id}`);
        if (!mounted) return;
        setSummaryData(response);
        setFormData((current) => ({
          ...current,
          systolic_bp: response?.systolic_bp ?? "",
          temperature: response?.temperature ?? "",
          heart_rate: response?.heart_rate ?? "",
          spo2: response?.spo2 ?? "",
          respiratory_rate: response?.respiratory_rate ?? "",
        }));
      } catch (fetchError) {
        if (mounted) setError(fetchError.message);
      } finally {
        if (mounted) setLoading(false);
      }
    };

    loadSummary();
    return () => {
      mounted = false;
    };
  }, [p_id]);

  const handleLogout = () => {
    localStorage.clear();
    navigate("/");
  };

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData((current) => ({ ...current, [name]: value }));
  };

  const providedVitals = VITAL_FIELDS.filter(({ key }) => String(formData[key] ?? "").trim()).length;

  const handleSubmit = async () => {
    setSubmitting(true);
    setError("");
    try {
      const result = await apiPost("/triage-finalize", {
        patient_id: p_id,
        scenario: "normal",
        nurse_vitals: {
          systolic_bp: toNumberOrNull(formData.systolic_bp),
          temperature: toNumberOrNull(formData.temperature),
          heart_rate: toNumberOrNull(formData.heart_rate),
          spo2: toNumberOrNull(formData.spo2),
          respiratory_rate: toNumberOrNull(formData.respiratory_rate),
        },
        nurse_note: formData.nurse_note || "",
      });
      setFinalResult(result);
      const refreshed = await apiGet(`/clinical/${p_id}`);
      setSummaryData(refreshed);
    } catch (submitError) {
      setError(submitError.message);
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
            <span style={{ marginRight: "12px" }}>Home</span> Dashboard
          </div>
          <div className="nav-item" onClick={() => navigate("/new-patient")}>
            <span style={{ marginRight: "12px" }}>+</span> Add New Patient
          </div>
          <div className="nav-item" onClick={() => navigate("/bed-assignments")}>
            <span style={{ marginRight: "12px" }}>Bed</span> Assignments
          </div>
          <a className="nav-item" href={chatbotUrl} target="_blank" rel="noreferrer" style={{ textDecoration: "none", color: "inherit" }}>
            <span style={{ marginRight: "12px" }}>AI</span> Triage Agent
          </a>
        </div>

        <div className="logout-section" onClick={handleLogout}>
          <span style={{ marginRight: "12px" }}>Log out</span>
        </div>
      </div>

      <div className="main-content">
        <p style={{ color: "#707EAE", fontSize: "14px" }}>Pages / Nurse Evaluation</p>

        <div className="welcome-banner" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "20px" }}>
          <div>
            <h1 style={{ marginBottom: "8px" }}>Nurse CTAS Finalization</h1>
            <p style={{ margin: 0 }}>Final CTAS requires nurse validation with measured vitals before the case becomes fully actionable.</p>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "13px", opacity: 0.86 }}>{userEmail}</div>
            <div style={{ marginTop: "10px", padding: "10px 14px", borderRadius: "12px", background: summaryData?.preliminary ? "rgba(255, 181, 71, 0.16)" : "rgba(5, 205, 153, 0.14)", color: summaryData?.preliminary ? "#FFB547" : "#05CD99", fontWeight: 700 }}>
              {summaryData?.preliminary ? "Preliminary - nurse vitals required" : "Vitals-informed CTAS available"}
            </div>
          </div>
        </div>

        {loading ? <div style={{ marginTop: "18px", color: "#707EAE" }}>Loading triage summary...</div> : null}
        {error ? <div style={{ marginTop: "18px", color: "#EE5D50" }}>Action failed: {error}</div> : null}

        {summaryData ? (
          <div style={{ display: "grid", gridTemplateColumns: finalResult ? "1.1fr 0.9fr" : "1fr", gap: "22px", marginTop: "24px" }}>
            <div className="patient-table-container">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                <div>
                  <h3 style={{ margin: 0 }}>Initial triage summary</h3>
                  <p style={{ margin: "6px 0 0", color: "#707EAE", fontSize: "13px" }}>Registration identity stays local; only symptom intake and measured vitals feed the clinical scoring step.</p>
                </div>
                <div style={{ padding: "10px 14px", borderRadius: "12px", backgroundColor: "#F4F7FE", color: "#1B2559", fontWeight: 700 }}>
                  Patient {summaryData.patient_id}
                </div>
              </div>

              <div className="stats-grid" style={{ gridTemplateColumns: "repeat(3, 1fr)", marginBottom: "18px" }}>
                <div className="stat-card"><div className="stat-header"><span>Current CTAS</span></div><div className="stat-body"><p>{summaryData.ctas_name || `CTAS ${summaryData.ctas_level}`}</p></div></div>
                <div className="stat-card"><div className="stat-header"><span>Urgency</span></div><div className="stat-body"><p>{summaryData.urgency}</p></div></div>
                <div className="stat-card"><div className="stat-header"><span>Current Bed</span></div><div className="stat-body"><p>{summaryData.recommended_bed || "Pending"}</p></div></div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "16px" }}>
                <div className="stat-card" style={{ minHeight: "140px" }}>
                  <div className="stat-header"><span>Chatbot / intake summary</span></div>
                  <div className="stat-body"><p style={{ fontSize: "14px", lineHeight: 1.7 }}>{summaryData.summary || summaryData.chief_complaint}</p></div>
                </div>
                <div className="stat-card" style={{ minHeight: "140px" }}>
                  <div className="stat-header"><span>Missing vitals</span></div>
                  <div className="stat-body"><p style={{ fontSize: "14px", lineHeight: 1.7 }}>{summaryData.missing_vitals?.length ? summaryData.missing_vitals.join(", ") : "No missing vitals."}</p></div>
                </div>
              </div>

              <div className="patient-table-container" style={{ boxShadow: "none", border: "1px solid #E0E5F2", padding: "18px" }}>
                <h3 style={{ marginTop: 0 }}>Measured nurse vitals</h3>
                <p style={{ color: "#707EAE", fontSize: "13px", lineHeight: 1.7 }}>Use real measured values only. Missing values keep the assessment preliminary and the finalization endpoint will reject submission until all required vitals are entered.</p>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: "14px" }}>
                  {VITAL_FIELDS.map((field) => (
                    <div key={field.key}>
                      <label style={{ display: "block", marginBottom: "8px", fontSize: "13px", color: "#1B2559", fontWeight: 700 }}>{field.label}</label>
                      <input
                        type={field.type}
                        step={field.step || "1"}
                        name={field.key}
                        value={formData[field.key]}
                        onChange={handleChange}
                        placeholder={field.placeholder}
                        style={{ width: "100%", padding: "12px 14px", borderRadius: "12px", border: "1px solid #DCE3F1", fontSize: "14px" }}
                      />
                    </div>
                  ))}
                </div>
                <div style={{ marginTop: "16px" }}>
                  <label style={{ display: "block", marginBottom: "8px", fontSize: "13px", color: "#1B2559", fontWeight: 700 }}>Nurse note</label>
                  <textarea
                    name="nurse_note"
                    value={formData.nurse_note}
                    onChange={handleChange}
                    placeholder="Add a short nurse validation note if needed."
                    rows={4}
                    style={{ width: "100%", padding: "12px 14px", borderRadius: "12px", border: "1px solid #DCE3F1", fontSize: "14px", resize: "vertical" }}
                  />
                </div>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "18px", gap: "12px" }}>
                  <div style={{ color: providedVitals === VITAL_FIELDS.length ? "#05CD99" : "#FFB547", fontWeight: 700, fontSize: "13px" }}>
                    {providedVitals === VITAL_FIELDS.length ? "All required vitals entered. Final CTAS can be submitted." : `${providedVitals}/${VITAL_FIELDS.length} required vitals entered`}
                  </div>
                  <div style={{ display: "flex", gap: "10px" }}>
                    <button className="execute-btn" onClick={() => navigate(`/clinical/${p_id}`)} style={{ background: "#A3AED0" }}>
                      View current summary
                    </button>
                    <button className="execute-btn" onClick={handleSubmit} disabled={submitting} style={{ opacity: submitting ? 0.7 : 1 }}>
                      {submitting ? "Finalizing..." : "Submit final CTAS"}
                    </button>
                  </div>
                </div>
              </div>
            </div>

            {finalResult ? (
              <div className="ai-panel">
                <h3>Final CTAS Result</h3>
                <p className="ai-subtext"><b>Vitals-informed nurse validation complete</b></p>
                <div className="ai-stat-row"><span>CTAS Level</span><span className="val">{finalResult.ctas.level}</span></div>
                <div className="ai-stat-row"><span>Urgency</span><span className="val">{finalResult.urgency}</span></div>
                <div className="ai-stat-row"><span>Bed</span><span className="val">{finalResult.allocation.recommended_bed}</span></div>
                <div className="ai-stat-row"><span>Estimated Wait</span><span className="val">{Math.round(finalResult.allocation.estimated_wait_minutes || 0)} min</span></div>
                <div className="ai-card critical">
                  <h4>{finalResult.ctas.name}</h4>
                  <p>{finalResult.reason}</p>
                  <p>{finalResult.summary}</p>
                  <p>{finalResult.allocation.alerts?.length ? finalResult.allocation.alerts.join(", ") : "No allocation alerts."}</p>
                  <button className="execute-btn" onClick={() => navigate(`/clinical/${p_id}`)}>Open clinical summary</button>
                  <button className="execute-btn" onClick={() => navigate("/bed-assignments")} style={{ marginTop: "8px", background: "#05CD99" }}>Open bed assignments</button>
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default TriageFinalize;
