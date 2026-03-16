import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './Dashboard.css'; 
import axios from 'axios';
import ehosp from "./assets/ehosp.png";

const DashboardPage = () => {
    const navigate = useNavigate();
    const userEmail = localStorage.getItem("userEmail") || "Mr. White";
    const [history, setHistory] = useState([]);
    useEffect(() => {
        const fetchHistory = async () => {
            try {
                const response = await axios.get('http://localhost:8000/patient-history');
                setHistory(response.data);
            } catch (error) {
                console.error("Error fetching history:", error);
            }
        };
        fetchHistory();
    }, []);
    const handleLogout = () => {
        localStorage.clear();
        navigate('/');
    };

    return (
        <div className="dashboard-container">
            {/* Sidebar */}
            <div className="sidebar">
                <div className="logo-section">
                    <img 
                        src={ehosp} 
                        alt="E-Hospital Logo" 
                        style={{ 
                            width: '200px',      
                            height: '80px',     
                            objectFit: 'contain',
                            display: 'block' 
                        }} 
                    />
                </div>

                <div className="nav-menu">
                    <div className="nav-item active">
                        <div className="icon-box-active">
                            <img 
                                src="https://img.icons8.com/tiny-glyph/32/ffffff/home.png" 
                                alt="home" 
                                className="white-icon"
                            />
                        </div>
                        <span className="nav-text">Dashboard</span>
                    </div>
                    <div 
                        className="nav-item" 
                        onClick={() => navigate('/new-patient')}
                    >
                        <span style={{marginRight: '12px'}}>➕</span> Add New Patient
                    </div>
                </div>

                <div className="logout-section" onClick={handleLogout}>
                    <span style={{marginRight: '12px'}}>🚪</span> Log out
                </div>
            </div>

            {/* Main Content Area */}
            <div className="main-content">
                <p style={{color: '#707EAE', fontSize: '14px'}}>Pages / Dashboard</p>
                
                <div className="welcome-banner">
                    <h1>Hello {userEmail === "testuser@hospital.com" ? "Dr. White" : userEmail.split('@')[0]}</h1>
                    <p>Have a good day at work!</p>
                </div>

                {/* Grid Layout  */}
                <div className="dashboard-grid-layout">
                    
                    {/* Left Column */}
                    <div className="stats-table-column">
                        
                        {/* 4 Stats Blocks */}
                        <div className="stats-grid">
                            <div className="stat-card">
                                <div className="stat-header"><span>Beds Capacity</span> 🛏️</div>
                                <div className="stat-body">
                                    <p>Total: 48</p>
                                    <p style={{color: '#FFA500'}}>Occupied: 42</p>
                                    <p style={{color: '#05CD99'}}>Available: 4</p>
                                </div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-header"><span>Nurses Status</span> 👩🏻‍⚕️</div>
                                <div className="stat-body">
                                    <p>Total: 48</p>
                                    <p style={{color: '#FFA500'}}>On Duty: 42</p>
                                    <p style={{color: '#05CD99'}}>Available: 4</p>
                                    <p style={{color: '#EE5D50'}}>Busy: 16</p>
                                </div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-header"><span>Physicians Load</span> 🩺</div>
                                <div className="stat-body">
                                    <p>Active: 12</p>
                                    <p style={{color: '#EE5D50'}}>Overloaded: 2</p>
                                </div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-header"><span>Isolation Rooms</span> 🛡️</div>
                                <div className="stat-body">
                                    <p>Total: 8</p>
                                    <p style={{color: '#05CD99'}}>Available: 2</p>
                                </div>
                            </div>
                            <div className="stat-card">
                                <div className="stat-header"><span>Active Alerts</span> ⚠️</div>
                                <div className="stat-body">
                                    <p style={{color: '#EE5D50'}}>Total: 3</p>
                                    <p>Wait Time: 42 min</p>
                                </div>
                            </div>
                        </div>

                        {/* Patient Table */}
                        <div className="patient-table-container">
                            <div className="table-top-bar">
                                <h3>Patient History Queue</h3>
                            </div>
                            <table className="custom-table">
                                <thead>
                                    <tr>
                                        <th>Patient ID</th>
                                        <th>Urgency</th>
                                        <th>Arrival</th>
                                        <th>Assessment Start</th>
                                        <th>Lab/Img</th>
                                        <th>Bed Type</th>
                                        <th>Decision</th>
                                        <th>Discharge</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {history.length > 0 ? (
                                        history.map((item, index) => (
                                            <tr key={index}>
                                                <td><strong>{item.patient_id}</strong></td>
                                                <td className={item.urgency_level >= 7 ? "flag-red" : "status-green"}>
                                                    {item.urgency_level}
                                                </td>
                                                <td>{item.arrival_mode}</td>
                                                <td>{item.assessment_start_ts}</td>
                                                <td>
                                                    L: {item.lab_required} / I: {item.imaging_required}
                                                </td>
                                                <td>{item.bed_assigned_type}</td>
                                                <td className="status-blue">{item.admit_decision}</td>
                                                <td>{item.discharge_ts || "Pending"}</td>
                                            </tr>
                                        ))
                                    ) : (
                                        <tr>
                                            <td colSpan="8" style={{textAlign: 'center'}}>Loading history...</td>
                                        </tr>
                                    )}
                                </tbody>
                            </table>
                        </div>
                    </div>

                   
                    <div className="ai-panel">
                        <h3>AI Resource Allocation</h3>
                        <p className="ai-subtext"><b>Updated in real-time</b></p>
                        <div className="ai-stat-row">
                            <span>Queue Length</span>
                            <span className="val">23</span>
                        </div>
                        <div className="ai-stat-row">
                            <span>High Urgency</span>
                            <span className="val" style={{color: '#EE5D50'}}>5</span>
                        </div>
                        <div className="ai-stat-row">
                            <span>Average Wait Time</span>
                            <span className="val" style={{color: '#EE5D50'}}>42 mins</span>
                        </div>
                        <div className="ai-stat-row">
                            <span>Capacity</span>
                            <span className="val" style={{color: '#EE5D50'}}></span>
                            
                        </div>
                        <div className="ai-stat-row">
                            <span> <b>Resource Constraints</b></span>
                            
                        </div>

                        <div className="ai-card critical">
                            <h4>Critical Action</h4>
                            <p>Assign Patient 2 to Bed 8 immediately</p>
                            <button className="execute-btn">Execute</button>
                        </div>
                    </div>

                </div> 
            </div> 
        </div>
    );
};

export default DashboardPage;