import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import "./Dashboard.css";
import ehosp from "./assets/ehosp.png";
import { apiGet, apiPost, apiUrl } from "./api";
import { IMAGING_SERVICES, LAB_SERVICES } from "./serviceCatalog";

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
  const [routeNotice, setRouteNotice] = useState("");
  const [serviceLoading, setServiceLoading] = useState(false);
  const [labService, setLabService] = useState(LAB_SERVICES[0]);
  const [imagingService, setImagingService] = useState(IMAGING_SERVICES[0]);

  const chatbotUrl = useMemo(() => {
    const returnUrl = encodeURIComponent(`${window.location.origin}/triage-finalize/${p_id}`);
    return `${apiUrl("/chatbot/ui")}?v=chatbot-text-ui-20260324&returnUrl=${returnUrl}`;
  }, [p_id]);

  const loadSummary = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiGet(`/clinical/${p_id}`);
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
      setError(fetchError.message);
    } finally {
      setLoading(false);
    }
  }, [p_id]);

  useEffect(() => {
    loadSummary();
  }, [loadSummary]);

  const handleLogout = () => {
    localStorage.clear();
    navigate("/");
  };

  const handleChange = (event) => {
    const { name, value } = event.target;
    setFormData((current) => ({ ...current, [name]: value }));
  };

  const providedVitals = VITAL_FIELDS.filter(({ key }) => String(formData[key] ?? "").trim()).length;
  const canRouteToService = Boolean(finalResult || (summaryData && !summaryData.preliminary));

  const handleSubmit = async () => {
    setSubmitting(true);
    setError("");
    setRouteNotice("");
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
      await loadSummary();
    } catch (submitError) {
      setError(submitError.message);
    } finally {
      setSubmitting(false);
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
      await loadSummary();
    } catch (routeError) {
      setError(routeError.message);
    } finally {
      setServiceLoading(false);
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
          <div className="nav-item" onClick={() => navigate("/lab")}><span style={{ marginRight: "12px" }}>Lab</span> Lab</div>
          <div className="nav-item" onClick={() => navigate("/imaging")}><span style={{ marginRight: "12px" }}>Img</span> Imaging</div>
          <a className="nav-item" href={chatbotUrl} target="_blank" rel="noreferrer" style={{ textDecoration: "none", color: "inherit" }}><span style={{ marginRight: "12px" }}>AI</span> Triage Agent</a>
        </div>

        <div className="logout-section" onClick={handleLogout}><span style={{ marginRight: "12px" }}>Log out</span></div>
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
        {routeNotice ? <div style={{ marginTop: "18px", color: "#05CD99", fontWeight: 700 }}>{routeNotice}</div> : null}

        {summaryData ? (
          <div style={{ display: "grid", gridTemplateColumns: "1.1fr 0.9fr", gap: "22px", marginTop: "24px" }}>
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

            <div className="ai-panel">
              <h3>{finalResult ? "Final CTAS Result" : "Assessment Snapshot"}</h3>
              <p className="ai-subtext"><b>{finalResult ? "Vitals-informed nurse validation complete" : "Finalize CTAS, then route to services if needed"}</b></p>
              <div className="ai-stat-row"><span>CTAS Level</span><span className="val">{finalResult ? finalResult.ctas.level : summaryData.ctas_level}</span></div>
              <div className="ai-stat-row"><span>Urgency</span><span className="val">{finalResult ? finalResult.urgency : summaryData.urgency}</span></div>
              <div className="ai-stat-row"><span>Bed</span><span className="val">{(finalResult ? finalResult.allocation.recommended_bed : summaryData.recommended_bed) || "Pending"}</span></div>
              <div className="ai-stat-row"><span>Current Location</span><span className="val">{summaryData.current_location || "Pending"}</span></div>
              <div className="ai-stat-row"><span>Requested Service</span><span className="val">{summaryData.requested_service || "None"}</span></div>
              <div className="ai-stat-row"><span>Estimated Wait</span><span className="val">{Math.round((finalResult ? finalResult.allocation.estimated_wait_minutes : summaryData.estimated_wait_minutes) || 0)} min</span></div>
              <div className="ai-card critical">
                <h4>{finalResult ? finalResult.ctas.name : summaryData.ctas_name}</h4>
                <p>{finalResult ? finalResult.reason : (summaryData.summary || summaryData.chief_complaint)}</p>
                <p>{finalResult ? finalResult.summary : (summaryData.missing_vitals?.length ? `Missing vitals: ${summaryData.missing_vitals.join(", ")}` : "All required vitals already available.")}</p>
                <p>{finalResult ? (finalResult.allocation.alerts?.length ? finalResult.allocation.alerts.join(", ") : "No allocation alerts.") : "Submit final CTAS before routing the patient downstream."}</p>
                <button className="execute-btn" onClick={() => navigate(`/clinical/${p_id}`)}>Open clinical summary</button>
                <button className="execute-btn" onClick={() => navigate("/bed-assignments")} style={{ marginTop: "8px", background: "#05CD99" }}>Open bed assignments</button>
              </div>

              <div className="ai-card critical" style={{ marginTop: "14px" }}>
                <h4>Route to Lab</h4>
                <p style={{ color: "#707EAE", fontSize: "13px", lineHeight: 1.7 }}>After CTAS is finalized, select the required lab test and add the patient to the Lab queue.</p>
                <select value={labService} onChange={(event) => setLabService(event.target.value)} style={{ width: "100%", padding: "12px 14px", borderRadius: "12px", border: "1px solid #DCE3F1", marginBottom: "10px" }}>
                  {LAB_SERVICES.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
                <div style={{ display: "flex", gap: "10px" }}>
                  <button className="execute-btn" onClick={() => handleSendToService("lab", labService)} disabled={!canRouteToService || serviceLoading} style={{ background: "#4318FF", flex: 1, opacity: !canRouteToService ? 0.55 : 1 }}>
                    {serviceLoading ? "Routing..." : "Send to Lab"}
                  </button>
                  <button className="execute-btn" onClick={() => navigate("/lab")} style={{ background: "#A3AED0", flex: 1 }}>Open Lab Queue</button>
                </div>
              </div>

              <div className="ai-card critical" style={{ marginTop: "14px" }}>
                <h4>Route to Imaging</h4>
                <p style={{ color: "#707EAE", fontSize: "13px", lineHeight: 1.7 }}>After CTAS is finalized, select the imaging study and add the patient to the Imaging queue.</p>
                <select value={imagingService} onChange={(event) => setImagingService(event.target.value)} style={{ width: "100%", padding: "12px 14px", borderRadius: "12px", border: "1px solid #DCE3F1", marginBottom: "10px" }}>
                  {IMAGING_SERVICES.map((option) => <option key={option} value={option}>{option}</option>)}
                </select>
                <div style={{ display: "flex", gap: "10px" }}>
                  <button className="execute-btn" onClick={() => handleSendToService("imaging", imagingService)} disabled={!canRouteToService || serviceLoading} style={{ background: "#0095FF", flex: 1, opacity: !canRouteToService ? 0.55 : 1 }}>
                    {serviceLoading ? "Routing..." : "Send to Imaging"}
                  </button>
                  <button className="execute-btn" onClick={() => navigate("/imaging")} style={{ background: "#A3AED0", flex: 1 }}>Open Imaging Queue</button>
                </div>
                {!canRouteToService ? <p style={{ color: "#FFB547", fontSize: "12px", marginTop: "10px", lineHeight: 1.6 }}>Submit final CTAS first. Downstream service routing is disabled while the case remains preliminary.</p> : null}
              </div>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default TriageFinalize;
