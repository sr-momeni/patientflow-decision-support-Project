import React, { useCallback, useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Dashboard.css";
import ehosp from "./assets/ehosp.png";
import { apiGet, apiUrl } from "./api";

const formatMinutes = (value) => `${Math.round(Number(value) || 0)} min`;

const ServiceQueuePage = ({ department, title, endpoint }) => {
  const navigate = useNavigate();
  const userEmail = localStorage.getItem("userEmail") || "clinical.staff@hospital.com";
  const [queueData, setQueueData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const chatbotUrl = useMemo(() => {
    const returnUrl = encodeURIComponent(`${window.location.origin}/${department}`);
    return `${apiUrl("/chatbot/ui")}?v=chatbot-text-ui-20260324&returnUrl=${returnUrl}`;
  }, [department]);

  const loadQueue = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiGet(endpoint);
      setQueueData(response);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => {
    loadQueue();
  }, [loadQueue]);

  const handleLogout = () => {
    localStorage.clear();
    navigate("/");
  };

  const departmentLabel = title;

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
          <div className={`nav-item ${department === "lab" ? "active" : ""}`} onClick={() => navigate("/lab")}><span style={{ marginRight: "12px" }}>Lab</span> Lab</div>
          <div className={`nav-item ${department === "imaging" ? "active" : ""}`} onClick={() => navigate("/imaging")}><span style={{ marginRight: "12px" }}>Img</span> Imaging</div>
          <a className="nav-item" href={chatbotUrl} target="_blank" rel="noreferrer" style={{ textDecoration: "none", color: "inherit" }}><span style={{ marginRight: "12px" }}>AI</span> Triage Agent</a>
        </div>

        <div className="logout-section" onClick={handleLogout}><span style={{ marginRight: "12px" }}>Log out</span></div>
      </div>

      <div className="main-content">
        <p style={{ color: "#707EAE", fontSize: "14px" }}>Pages / {departmentLabel}</p>

        <div className="welcome-banner" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "20px" }}>
          <div>
            <h1 style={{ marginBottom: "8px" }}>{departmentLabel} Queue</h1>
            <p style={{ margin: 0 }}>Live operational queue for patients currently routed to {departmentLabel.toLowerCase()}.</p>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "13px", opacity: 0.86, marginBottom: "10px" }}>{userEmail}</div>
            <button onClick={loadQueue} style={{ background: "white", color: "#4318FF", border: "none", padding: "10px 18px", borderRadius: "12px", fontWeight: 700, cursor: "pointer" }}>
              {loading ? "Refreshing..." : `Refresh ${departmentLabel}`}
            </button>
          </div>
        </div>

        {error ? <div style={{ color: "#EE5D50", marginTop: "18px" }}>Failed to load {departmentLabel.toLowerCase()} queue: {error}</div> : null}

        <div className="stats-grid" style={{ marginTop: "24px" }}>
          <div className="stat-card"><div className="stat-header"><span>Queue Length</span></div><div className="stat-body"><p>{queueData?.queue_length || 0}</p></div></div>
          <div className="stat-card"><div className="stat-header"><span>Average Wait</span></div><div className="stat-body"><p>{formatMinutes(queueData?.average_wait_time)}</p></div></div>
          <div className="stat-card"><div className="stat-header"><span>Service Types</span></div><div className="stat-body"><p>{queueData?.available_services?.length || 0}</p></div></div>
          <div className="stat-card"><div className="stat-header"><span>Department</span></div><div className="stat-body"><p>{departmentLabel}</p></div></div>
        </div>

        <div className="patient-table-container" style={{ marginTop: "22px" }}>
          <div className="table-top-bar">
            <h3>{departmentLabel} Active Patients</h3>
          </div>
          <table className="custom-table">
            <thead>
              <tr>
                <th>Patient ID</th>
                <th>CTAS</th>
                <th>Urgency</th>
                <th>Requested Service</th>
                <th>Current Location</th>
                <th>Estimated Wait</th>
                <th>Summary</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan="7" style={{ textAlign: "center" }}>Loading {departmentLabel.toLowerCase()} queue...</td></tr>
              ) : queueData?.patients?.length ? (
                queueData.patients.map((item) => (
                  <tr key={`${item.patient_id}-${item.requested_service}`}>
                    <td>
                      <button type="button" onClick={() => navigate(`/patient/${item.patient_id}`)} style={{ background: "transparent", border: "none", color: "#4318FF", fontWeight: 700, cursor: "pointer", padding: 0 }}>
                        {item.patient_id}
                      </button>
                    </td>
                    <td>{item.ctas_name}</td>
                    <td className={item.urgency === "HIGH" ? "flag-red" : item.urgency === "MEDIUM" ? "status-blue" : "status-green"}>{item.urgency}</td>
                    <td>{item.requested_service}</td>
                    <td style={{ textTransform: "capitalize" }}>{item.current_location}</td>
                    <td>{formatMinutes(item.estimated_wait_time)}</td>
                    <td>{item.summary || "-"}</td>
                  </tr>
                ))
              ) : (
                <tr><td colSpan="7" style={{ textAlign: "center" }}>No patients currently routed to {departmentLabel.toLowerCase()}.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default ServiceQueuePage;
