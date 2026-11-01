import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Dashboard.css";
import ehosp from "./assets/ehosp.png";
import { apiGet, apiUrl } from "./api";

const formatPercent = (value) => `${Math.round((Number(value) || 0) * 100)}%`;
const formatMinutes = (value) => `${Math.round(Number(value) || 0)} min`;

const latestRecommendationFromHistory = (items) =>
  (items || []).find(
    (item) =>
      item &&
      item.patient_id &&
      (item.recommended_bed || item.bed_assigned_type || item.ctas_name || item.urgency_level || item.clinical_summary)
  );

const recommendationSummary = (item) => {
  if (!item) {
    return "Complete a triage assessment to surface the latest prioritization-based recommendation.";
  }

  const ctasLabel = item.ctas_name || (item.urgency_level ? `CTAS ${item.urgency_level}` : "Triage result");
  const bed = item.recommended_bed || item.bed_assigned_type || "ED";
  const wait = formatMinutes(item.estimated_wait_minutes);

  if (item.allocation_alerts?.length) {
    return `${ctasLabel} patient should be routed to ${bed}. ${item.allocation_alerts[0]}`;
  }
  if ((item.urgency_level || 0) > 0 && item.urgency_level <= 2) {
    return `${ctasLabel} patient should receive priority placement in ${bed} with an estimated wait of ${wait}.`;
  }
  if (item.clinical_summary) {
    return `${ctasLabel} patient routed to ${bed}. ${item.clinical_summary}`;
  }
  return `${ctasLabel} patient routed to ${bed} with an estimated wait of ${wait}.`;
};

const DashboardPage = () => {
  const navigate = useNavigate();
  const userEmail = localStorage.getItem("userEmail") || "clinical.staff@hospital.com";
  const [history, setHistory] = useState([]);
  const [metrics, setMetrics] = useState({
    average_waiting_time: 0,
    average_los: 0,
    ed_bed_utilization: 0,
    icu_bed_utilization: 0,
    queue_length: 0,
    high_urgency_count: 0,
  });
  const [labQueue, setLabQueue] = useState({ queue_length: 0, average_wait_time: 0 });
  const [imagingQueue, setImagingQueue] = useState({ queue_length: 0, average_wait_time: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let mounted = true;

    const loadDashboard = async () => {
      setLoading(true);
      setError("");
      try {
        const [metricsResponse, historyResponse, labResponse, imagingResponse] = await Promise.all([
          apiGet("/metrics"),
          apiGet("/patient-history?limit=25"),
          apiGet("/lab-queue"),
          apiGet("/imaging-queue"),
        ]);
        if (!mounted) {
          return;
        }
        setMetrics(metricsResponse);
        setHistory(Array.isArray(historyResponse) ? historyResponse : []);
        setLabQueue(labResponse || { queue_length: 0, average_wait_time: 0 });
        setImagingQueue(imagingResponse || { queue_length: 0, average_wait_time: 0 });
      } catch (loadError) {
        if (!mounted) {
          return;
        }
        setError(loadError.message);
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    loadDashboard();
    return () => {
      mounted = false;
    };
  }, []);

  const handleLogout = () => {
    localStorage.clear();
    navigate("/");
  };

  const latestRecommendation = latestRecommendationFromHistory(history);
  const returnUrl = encodeURIComponent(`${window.location.origin}/dashboard`);
  const chatbotUrl = `${apiUrl("/chatbot/ui")}?v=chatbot-text-ui-20260324&returnUrl=${returnUrl}`;

  return (
    <div className="dashboard-container">
      <div className="sidebar">
        <div className="logo-section">
          <img
            src={ehosp}
            alt="E-Hospital Logo"
            style={{ width: "200px", height: "80px", objectFit: "contain", display: "block" }}
          />
        </div>

        <div className="nav-menu">
          <div className="nav-item active">
            <div className="icon-box-active">
              <img src="https://img.icons8.com/tiny-glyph/32/ffffff/home.png" alt="home" className="white-icon" />
            </div>
            <span className="nav-text">Dashboard</span>
          </div>
          <div className="nav-item" onClick={() => navigate("/new-patient")}>
            <span style={{ marginRight: "12px" }}>+</span> Add New Patient
          </div>
          <div className="nav-item" onClick={() => navigate("/bed-assignments")}>
            <span style={{ marginRight: "12px" }}>Bed</span> Assignments
          </div>
          <div className="nav-item" onClick={() => navigate("/lab")}>
            <span style={{ marginRight: "12px" }}>Lab</span> Lab
          </div>
          <div className="nav-item" onClick={() => navigate("/imaging")}>
            <span style={{ marginRight: "12px" }}>Img</span> Imaging
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
        <p style={{ color: "#707EAE", fontSize: "14px" }}>Pages / Dashboard</p>

        <div className="welcome-banner">
          <h1>Hello {userEmail === "testuser@hospital.com" ? "Dr. White" : userEmail.split("@")[0]}</h1>
          <p>Live metrics now include triage, allocation, bed flow, and downstream Lab / Imaging queue status.</p>
        </div>

        {error ? <div style={{ color: "#EE5D50", marginBottom: "16px" }}>Dashboard load failed: {error}</div> : null}

        <div className="dashboard-grid-layout">
          <div className="stats-table-column">
            <div className="stats-grid">
              <div className="stat-card"><div className="stat-header"><span>Queue Length</span></div><div className="stat-body"><p>{metrics.queue_length}</p></div></div>
              <div className="stat-card"><div className="stat-header"><span>High Urgency</span></div><div className="stat-body"><p style={{ color: "#EE5D50" }}>{metrics.high_urgency_count}</p></div></div>
              <div className="stat-card"><div className="stat-header"><span>Average Wait</span></div><div className="stat-body"><p>{formatMinutes(metrics.average_waiting_time)}</p></div></div>
              <div className="stat-card"><div className="stat-header"><span>Average LOS</span></div><div className="stat-body"><p>{formatMinutes(metrics.average_los)}</p></div></div>
              <div className="stat-card"><div className="stat-header"><span>ED Utilization</span></div><div className="stat-body"><p>{formatPercent(metrics.ed_bed_utilization)}</p></div></div>
              <div className="stat-card"><div className="stat-header"><span>ICU Utilization</span></div><div className="stat-body"><p>{formatPercent(metrics.icu_bed_utilization)}</p></div></div>
              <div className="stat-card"><div className="stat-header"><span>Lab Queue</span></div><div className="stat-body"><p>{labQueue.queue_length}</p><small style={{ color: "#707EAE" }}>Avg {formatMinutes(labQueue.average_wait_time)}</small></div></div>
              <div className="stat-card"><div className="stat-header"><span>Imaging Queue</span></div><div className="stat-body"><p>{imagingQueue.queue_length}</p><small style={{ color: "#707EAE" }}>Avg {formatMinutes(imagingQueue.average_wait_time)}</small></div></div>
            </div>

            <div className="patient-table-container">
              <div className="table-top-bar">
                <h3>Patient History Queue</h3>
              </div>
              <table className="custom-table">
                <thead>
                  <tr>
                    <th>Patient ID</th>
                    <th>CTAS</th>
                    <th>Scenario</th>
                    <th>Recommended Bed</th>
                    <th>Location</th>
                    <th>Wait</th>
                    <th>LOS</th>
                    <th>Alerts</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {loading ? (
                    <tr>
                      <td colSpan="9" style={{ textAlign: "center" }}>Loading dashboard...</td>
                    </tr>
                  ) : history.length > 0 ? (
                    history.map((item) => (
                      <tr key={`${item.patient_id}-${item.assessment_start_ts || item.scenario}`}>
                        <td>
                          <button
                            type="button"
                            onClick={() => navigate(`/patient/${item.patient_id}`)}
                            style={{ background: "transparent", border: "none", color: "#4318FF", fontWeight: 700, cursor: "pointer", padding: 0 }}
                          >
                            {item.patient_id}
                          </button>
                        </td>
                        <td className={item.urgency_level <= 2 ? "flag-red" : item.urgency_level === 3 ? "status-blue" : "status-green"}>
                          {item.ctas_name || `CTAS ${item.urgency_level}`}
                        </td>
                        <td>{item.scenario}</td>
                        <td>{item.recommended_bed || item.bed_assigned_type || "ED"}</td>
                        <td style={{ textTransform: "capitalize" }}>{item.current_location || "-"}</td>
                        <td>{formatMinutes(item.estimated_wait_minutes)}</td>
                        <td>{formatMinutes(item.los_minutes || item.estimated_los_delta_minutes)}</td>
                        <td>{item.allocation_alerts?.length ? item.allocation_alerts.join(", ") : "-"}</td>
                        <td>
                          <button className="execute-btn" onClick={() => navigate(`/patient/${item.patient_id}`)} style={{ minWidth: "110px", padding: "8px 14px" }}>
                            View / Edit
                          </button>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan="9" style={{ textAlign: "center" }}>No patient history available yet.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div className="ai-panel">
            <h3>AI Resource Allocation</h3>
            <p className="ai-subtext"><b>Live operational summary</b></p>
            <div className="ai-stat-row"><span>Queue Length</span><span className="val">{metrics.queue_length}</span></div>
            <div className="ai-stat-row"><span>High Urgency</span><span className="val" style={{ color: "#EE5D50" }}>{metrics.high_urgency_count}</span></div>
            <div className="ai-stat-row"><span>Average Wait Time</span><span className="val">{formatMinutes(metrics.average_waiting_time)}</span></div>
            <div className="ai-stat-row"><span>ED Utilization</span><span className="val">{formatPercent(metrics.ed_bed_utilization)}</span></div>
            <div className="ai-stat-row"><span>ICU Utilization</span><span className="val">{formatPercent(metrics.icu_bed_utilization)}</span></div>
            <div className="ai-stat-row"><span>Lab Queue</span><span className="val">{labQueue.queue_length} / {formatMinutes(labQueue.average_wait_time)}</span></div>
            <div className="ai-stat-row"><span>Imaging Queue</span><span className="val">{imagingQueue.queue_length} / {formatMinutes(imagingQueue.average_wait_time)}</span></div>

            <div className="ai-card critical">
              <h4>{latestRecommendation ? `Latest prioritization output for ${latestRecommendation.patient_id}` : "No live recommendation yet"}</h4>
              <p>{recommendationSummary(latestRecommendation)}</p>
              {latestRecommendation ? (
                <>
                  <div className="ai-stat-row"><span>CTAS / Urgency</span><span className="val" style={{ color: latestRecommendation.urgency_level <= 2 ? "#EE5D50" : latestRecommendation.urgency_level === 3 ? "#4318FF" : "#05CD99" }}>{latestRecommendation.ctas_name || `CTAS ${latestRecommendation.urgency_level}`}</span></div>
                  <div className="ai-stat-row"><span>Recommended Bed</span><span className="val">{latestRecommendation.recommended_bed || latestRecommendation.bed_assigned_type || "ED"}</span></div>
                  <div className="ai-stat-row"><span>Current Location</span><span className="val" style={{ textTransform: "capitalize" }}>{latestRecommendation.current_location || latestRecommendation.recommended_bed || "ED"}</span></div>
                  <div className="ai-stat-row"><span>Estimated Wait</span><span className="val">{formatMinutes(latestRecommendation.estimated_wait_minutes)}</span></div>
                  <div className="ai-stat-row"><span>Alerts</span><span className="val">{latestRecommendation.allocation_alerts?.length ? latestRecommendation.allocation_alerts.join(", ") : "None"}</span></div>
                  {latestRecommendation.clinical_summary ? <p>{latestRecommendation.clinical_summary}</p> : null}
                </>
              ) : null}
              <button className="execute-btn" onClick={() => navigate(latestRecommendation ? `/clinical/${latestRecommendation.patient_id}` : "/new-patient")}>
                {latestRecommendation ? "View latest triage summary" : "Start new triage"}
              </button>
              <button className="execute-btn" onClick={() => navigate("/bed-assignments")} style={{ marginTop: "8px", background: "#05CD99" }}>
                View bed assignments
              </button>
              <button className="execute-btn" onClick={() => navigate("/lab")} style={{ marginTop: "8px", background: "#4318FF" }}>
                Open Lab queue
              </button>
              <button className="execute-btn" onClick={() => navigate("/imaging")} style={{ marginTop: "8px", background: "#0095FF" }}>
                Open Imaging queue
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
