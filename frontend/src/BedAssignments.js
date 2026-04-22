import React, { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import "./Dashboard.css";
import ehosp from "./assets/ehosp.png";
import { apiGet, apiUrl } from "./api";

const statusStyles = {
  available: { background: "#E6FAF4", color: "#05CD99", border: "1px solid #B3F0D8" },
  occupied: { background: "#FFF4E8", color: "#FFB547", border: "1px solid #FFE0B5" },
  reserved: { background: "#EEF4FF", color: "#4318FF", border: "1px solid #D6E4FF" },
  cleaning: { background: "#FFF1F1", color: "#EE5D50", border: "1px solid #FFD7D7" },
};

const BedAssignments = () => {
  const navigate = useNavigate();
  const userEmail = localStorage.getItem("userEmail") || "clinical.staff@hospital.com";
  const [bedData, setBedData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const loadBeds = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await apiGet("/bed-availability");
      setBedData(response);
    } catch (loadError) {
      setError(loadError.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBeds();
  }, []);

  const handleLogout = () => {
    localStorage.clear();
    navigate("/");
  };

  const chatbotUrl = useMemo(() => {
    const returnUrl = encodeURIComponent(`${window.location.origin}/bed-assignments`);
    return `${apiUrl("/chatbot/ui")}?v=chatbot-text-ui-20260324&returnUrl=${returnUrl}`;
  }, []);

  const units = bedData ? [bedData.ed, bedData.icu] : [];

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
          <div className="nav-item active">
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
        <p style={{ color: "#707EAE", fontSize: "14px" }}>Pages / Bed Assignments</p>

        <div className="welcome-banner" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "20px" }}>
          <div>
            <h1 style={{ marginBottom: "8px" }}>Bed Availability</h1>
            <p style={{ margin: 0 }}>Click any bed to open the detailed assignment page with live patient actions.</p>
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "13px", opacity: 0.86, marginBottom: "10px" }}>{userEmail}</div>
            <button onClick={loadBeds} style={{ background: "white", color: "#4318FF", border: "none", padding: "10px 18px", borderRadius: "12px", fontWeight: 700, cursor: "pointer" }}>
              {loading ? "Refreshing..." : "Refresh beds"}
            </button>
          </div>
        </div>

        {error ? <div style={{ color: "#EE5D50", marginTop: "18px" }}>Failed to load bed availability: {error}</div> : null}
        {bedData?.source ? <p style={{ color: "#707EAE", fontSize: "13px", marginTop: "18px" }}>{bedData.source}</p> : null}

        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "22px", marginTop: "24px" }}>
          {units.map((unit) => (
            <div key={unit.unit} className="patient-table-container">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                <div>
                  <h3 style={{ margin: 0 }}>{unit.unit} Beds</h3>
                  <p style={{ margin: "6px 0 0", color: "#707EAE", fontSize: "13px" }}>Live occupancy, ward/service routing, and availability.</p>
                </div>
                <div style={{ padding: "10px 14px", borderRadius: "14px", backgroundColor: "#F4F7FE", color: "#1B2559", fontWeight: 700 }}>
                  {unit.total} total
                </div>
              </div>

              <div className="stats-grid" style={{ gridTemplateColumns: "repeat(4, 1fr)", marginBottom: "18px" }}>
                <div className="stat-card"><div className="stat-header"><span>Occupied</span></div><div className="stat-body"><p>{unit.occupied}</p></div></div>
                <div className="stat-card"><div className="stat-header"><span>Reserved</span></div><div className="stat-body"><p>{unit.reserved}</p></div></div>
                <div className="stat-card"><div className="stat-header"><span>Available</span></div><div className="stat-body"><p>{unit.available}</p></div></div>
                <div className="stat-card"><div className="stat-header"><span>Cleaning</span></div><div className="stat-body"><p>{unit.cleaning}</p></div></div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(120px, 1fr))", gap: "12px" }}>
                {unit.beds.map((bed) => (
                  <button
                    type="button"
                    key={bed.bed_id}
                    onClick={() => navigate(`/bed/${bed.bed_id}`)}
                    style={{
                      borderRadius: "16px",
                      padding: "14px",
                      minHeight: "120px",
                      textAlign: "left",
                      cursor: "pointer",
                      ...statusStyles[bed.status],
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                      <strong>{bed.bed_id}</strong>
                      <span style={{ fontSize: "11px", textTransform: "capitalize" }}>{bed.status}</span>
                    </div>
                    <div style={{ fontSize: "12px", lineHeight: 1.6 }}>
                      <div><strong>Patient:</strong> {bed.status === "cleaning" ? "Cleaning" : bed.patient_id || "-"}</div>
                      <div><strong>CTAS:</strong> {bed.ctas_name || "-"}</div>
                      <div style={{ marginTop: "6px", color: "#707EAE" }}>{bed.summary || (bed.status === "available" ? "Ready for assignment." : "No summary available.")}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default BedAssignments;
