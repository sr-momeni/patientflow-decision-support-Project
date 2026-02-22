import React from 'react';
import { useNavigate } from 'react-router-dom';
import './Dashboard.css'; 
import ehosp from "./assets/ehosp.png";

const DashboardPage = () => {
    const navigate = useNavigate();
    const userEmail = localStorage.getItem("userEmail") || "Mr. White";

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
                    <h1>Hello {userEmail === "testuser@hospital.com" ? "Dr. White" : userEmail}</h1>
                    <p>Have a good day at work!</p>
                </div>

                {/* Grid Layout  */}
                <div className="dashboard-grid-layout">
                    
                    {/* Left Column */}
                    <div className="stats-table-column">
                        
                        {/* 4 Stats Blocks */}
                        <div className="stats-grid">
                            <div className="stat-card">
                                <div className="stat-header"><span>Beds Capacity</span> 👤</div>
                                <div className="stat-body">
                                    <p>Total: 48</p>
                                    <p style={{color: '#FFA500'}}>Occupied: 42</p>
                                    <p style={{color: '#05CD99'}}>Available: 4</p>
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
                                <h3>Patient Queue</h3>
                                <div className="table-buttons">
                                    <button className="btn-filter">Filter</button>
                                    <button className="btn-filter">Sort</button>
                                </div>
                            </div>
                            <table className="custom-table">
                                <thead>
                                    <tr>
                                        <th>Patient Info</th>
                                        <th>Wait Time</th>
                                        <th>Status</th>
                                        <th>Risk Flags</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr>
                                        <td><strong>John Martinez</strong><br/><small>ID: 2024-001</small></td>
                                        <td>45 min</td>
                                        <td className="status-blue">Needs Physician</td>
                                        <td className="flag-red">Cardiac</td>
                                    </tr>
                                    <tr>
                                        <td><strong>Sarah Wilson</strong><br/><small>ID: 2024-002</small></td>
                                        <td>32 min</td>
                                        <td className="status-green">In Treatment</td>
                                        <td>—</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>

                   
                    <div className="ai-panel">
                        <h3>AI Resource Allocation</h3>
                        <p className="ai-subtext">Updated in real-time</p>
                        <div className="ai-stat-row">
                            <span>Queue Length</span>
                            <span className="val">23</span>
                        </div>
                        <div className="ai-stat-row">
                            <span>High Urgency</span>
                            <span className="val" style={{color: '#EE5D50'}}>5</span>
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