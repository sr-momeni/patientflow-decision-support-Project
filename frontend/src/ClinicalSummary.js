import React, { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import "./ClinicalSummary.css";
import { apiGet } from "./api";

const displayValue = (value, fallback = "Not provided") => {
  if (value === null || value === undefined) return fallback;
  const text = String(value).trim();
  return text ? text : fallback;
};

const ClinicalSummary = () => {
  const { p_id } = useParams();
  const navigate = useNavigate();
  const [summaryData, setSummaryData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;

    const fetchSummary = async () => {
      setLoading(true);
      setError("");
      try {
        const response = await apiGet(`/clinical/${p_id}`);
        if (!mounted) {
          return;
        }
        setSummaryData(response);
      } catch (fetchError) {
        if (!mounted) {
          return;
        }
        setError(fetchError.message);
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    fetchSummary();
    return () => {
      mounted = false;
    };
  }, [p_id]);

  const vitalsCards = useMemo(() => {
    if (!summaryData) return [];
    return [
      { label: "Systolic BP", value: summaryData.systolic_bp ? `${summaryData.systolic_bp} mmHg` : null },
      { label: "Temperature", value: summaryData.temperature ? `${summaryData.temperature} C` : null },
      { label: "Heart Rate", value: summaryData.heart_rate ? `${summaryData.heart_rate} bpm` : null },
      { label: "SpO2", value: summaryData.spo2 ? `${summaryData.spo2}%` : null },
      { label: "Respiratory Rate", value: summaryData.respiratory_rate ? `${summaryData.respiratory_rate}/min` : null },
    ];
  }, [summaryData]);

  if (loading) {
    return <div className="loader">Initializing summary...</div>;
  }

  if (error) {
    return (
      <div className="summary-page">
        <div className="summary-card">
          <h2>Clinical Summary</h2>
          <p style={{ color: "#EE5D50" }}>Failed to load clinical summary: {error}</p>
          <button className="nav-back-btn" onClick={() => navigate("/dashboard")}>Back to Dashboard</button>
        </div>
      </div>
    );
  }

  return (
    <div className="summary-page">
      <div className="summary-card">
        <div className="header-cube">
          <div className="brand">
            <h2>eHospital Clinical Summary</h2>
          </div>
          <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
            <div style={{ padding: "10px 14px", borderRadius: "14px", backgroundColor: summaryData?.preliminary ? "#FFF4E8" : "#E6FAF4", color: summaryData?.preliminary ? "#FFB547" : "#05CD99", fontWeight: 700, fontSize: "12px" }}>
              {summaryData?.preliminary ? "Preliminary CTAS" : "Vitals-informed CTAS"}
            </div>
          </div>
        </div>

        <div className="section-container">
          <h3>Patient Information</h3>
          <div className="info-grid">
            <div className="data-cube">
              <span className="label">Name</span>
              <span className="value">{displayValue(summaryData?.name, "Unknown")}</span>
            </div>
            <div className="data-cube">
              <span className="label">Age</span>
              <span className="value">{displayValue(summaryData?.age, "Not provided")}</span>
            </div>
            <div className="data-cube">
              <span className="label">Arrival Time</span>
              <span className="value">{displayValue(summaryData?.arrival_time)}</span>
            </div>
            <div className="data-cube highlight">
              <span className="label">Patient ID</span>
              <span className="value">{displayValue(summaryData?.patient_id || p_id)}</span>
            </div>
          </div>
        </div>

        <div className="section-container">
          <h3 className="section-title">Clinical Assessment Details</h3>
          <div className="info-grid-row-4">
            <div className="data-cube-large">
              <label><b>Chief Complaint</b></label>
              <p style={{ margin: "2px 0", fontWeight: "500", fontSize: "16px" }}>{displayValue(summaryData?.chief_complaint)}</p>
              <div style={{ fontSize: "15px", color: "black", lineHeight: "1.2" }}>
                <div><b>Location:</b> {displayValue(summaryData?.location)}</div>
                <div><b>Onset:</b> {displayValue(summaryData?.onset)}</div>
              </div>
            </div>
            <div className="data-cube-large">
              <label><b>Pain Scale</b></label>
              <p style={{ margin: "2px 0", fontWeight: "500", fontSize: "16px" }}>{summaryData?.pain_scale !== null && summaryData?.pain_scale !== undefined ? `${summaryData.pain_scale}/10` : "Not provided"}</p>
              <div style={{ fontSize: "15px", color: "black", lineHeight: "1.2" }}>
                <div><b>Pattern:</b> {displayValue(summaryData?.pattern)}</div>
                <div><b>Factor:</b> {displayValue(summaryData?.modifying_factors)}</div>
              </div>
            </div>
            <div className="data-cube-large">
              <label><b>Neurologic Status</b></label>
              <p>{displayValue(summaryData?.consciousness_status || summaryData?.neurologic)}</p>
            </div>
            <div className="data-cube-large">
              <label><b>Fever and Infection</b></label>
              <p>{displayValue(summaryData?.fever)}</p>
            </div>
          </div>

          <div className="info-grid-row-4">
            <div className="data-cube-large">
              <label><b>Respiratory Assessment</b></label>
              <p style={{ margin: "2px 0", fontWeight: "500", fontSize: "16px" }}>{displayValue(summaryData?.respiratory)}</p>
              <div style={{ fontSize: "15px", color: "black", lineHeight: "1.2" }}>
                <div><b>Cough Type:</b> {displayValue(summaryData?.cough)}</div>
                <div><b>Breathing Effort:</b> {displayValue(summaryData?.breathing_effort)}</div>
              </div>
            </div>
            <div className="data-cube-large"><label><b>Red Flag Symptoms</b></label><p>{displayValue(summaryData?.red_flag_symptoms, "None documented")}</p></div>
            <div className="data-cube-large">
              <label><b>Cardiovascular</b></label>
              <p>Palpitations: {displayValue(summaryData?.palpitations)}</p>
              <p>Leg swelling: {displayValue(summaryData?.leg_swelling)}</p>
            </div>
            <div className="data-cube-large">
              <label><b>Medications and Allergies</b></label>
              <p style={{ margin: "2px 0", fontWeight: "500", fontSize: "16px" }}>{displayValue(summaryData?.medications_allergies)}</p>
              <div style={{ fontSize: "15px", color: "black", lineHeight: "1.2" }}>
                <div><b>Drug Allergies:</b> {displayValue(summaryData?.drug)}</div>
                <div><b>Medical History:</b> {displayValue(summaryData?.medical_history)}</div>
              </div>
            </div>
          </div>
        </div>

        <div className="section-container">
          <h3>Nurse Vitals</h3>
          <div className="info-grid-row-4">
            {vitalsCards.map((item) => (
              <div className="data-cube-large" key={item.label}>
                <label><b>{item.label}</b></label>
                <p>{displayValue(item.value)}</p>
              </div>
            ))}
          </div>
          {summaryData?.preliminary ? (
            <div style={{ padding: "0 30px 20px 80px" }}>
              <div className="data-cube-large" style={{ borderLeft: "5px solid #FFB547", backgroundColor: "#FFF9F0" }}>
                <label><b>Assessment status</b></label>
                <p style={{ marginBottom: "8px" }}>This CTAS result is preliminary because measured nurse vitals are still missing.</p>
                <p style={{ marginBottom: "12px" }}>{summaryData?.missing_vitals?.length ? `Missing vitals: ${summaryData.missing_vitals.join(", ")}` : "Missing vitals were not specified."}</p>
                <button className="execute-btn" onClick={() => navigate(`/triage-finalize/${summaryData.patient_id || p_id}`)} style={{ background: "#4318FF" }}>
                  Finalize with nurse vitals
                </button>
              </div>
            </div>
          ) : null}
        </div>

        <div className="section-container">
          <h3 className="section-title">Patient Notes</h3>
          <div style={{ paddingLeft: "80px", paddingBottom: "20px" }}>
            <div className="data-cube-large" style={{ maxWidth: "950px", textAlign: "left", borderLeft: "5px solid #0095FF", display: "block", minHeight: "80px" }}>
              <p style={{ color: "#4A5568", fontSize: "14px", margin: 0, paddingTop: "10px" }}>{displayValue(summaryData?.notes, "No additional notes provided.")}</p>
            </div>
          </div>
        </div>

        <div className="section-container">
          <h3>Triage Assessment Result</h3>
          <div className="result-layout">
            <div className="status-cube high" style={{ borderLeftColor: summaryData?.ctas_level <= 2 ? "#e53e3e" : summaryData?.ctas_level === 3 ? "#4318FF" : "#05CD99" }}>
              <div className="status-icon">CTAS</div>
              <div className="status-text">
                <h1>{summaryData?.ctas_name || "Unknown"}</h1>
                <p>Priority Level: {summaryData?.ctas_level || "N/A"}</p>
                <p>{displayValue(summaryData?.ctas_description, "No description available.")}</p>
              </div>
            </div>
          </div>
          <div className="data-cube-large" style={{ marginTop: "20px", marginLeft: "80px", marginRight: "30px" }}>
            <label><b>Allocation Recommendation</b></label>
            <p>Recommended bed: {displayValue(summaryData?.recommended_bed, "Pending")}</p>
            <p>Estimated wait: {Math.round(summaryData?.estimated_wait_minutes || 0)} minutes</p>
            <p>Estimated LOS delta: {Math.round(summaryData?.estimated_los_delta_minutes || 0)} minutes</p>
            <p>{summaryData?.allocation_alerts?.length ? summaryData.allocation_alerts.join(", ") : displayValue(summaryData?.summary, "No allocation alerts.")}</p>
          </div>
        </div>
      </div>
      <button className="nav-back-btn" onClick={() => navigate("/dashboard")}>Back to Dashboard</button>
    </div>
  );
};

export default ClinicalSummary;
