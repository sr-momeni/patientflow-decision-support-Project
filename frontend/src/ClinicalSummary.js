import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import axios from 'axios';
import './ClinicalSummary.css';


const ClinicalSummary = () => {
    const { p_id } = useParams();
    const navigate = useNavigate();
    const [summaryData, setSummaryData] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchSummary = async () => {
            try {
                const response = await axios.get(`http://localhost:8000/clinical/${p_id}`);
                console.log("DATA RECEIVED FROM BACKEND:", response.data);
                setSummaryData(response.data);
                setLoading(false);
            } catch (error) {
                console.error("Error fetching summary:", error);
                setLoading(false);
            }
        };
        fetchSummary();
    }, [p_id]);

    if (loading) return <div className="loader">Initializing Summary...</div>;

    return (
        <div className="summary-page">
            <div className="summary-card">
                {/* Header Cube */}
                <div className="header-cube">
                    <div className="brand">
                        <h2> 🏥Medical Triage System</h2>
                    </div>
                    
                </div>

                {/* Patient Information Grid */}
                <div className="section-container">
                    <h3>Patient Information</h3>
                    <div className="info-grid">
                        <div className="data-cube">
                            <span className="label">Name</span>
                            <span className="value">{summaryData?.name || "John Anderson"}</span>
                        </div>
                        <div className="data-cube">
                            <span className="label">Age</span>
                            <span className="value">{summaryData?.age || "42 /"}</span>
                        </div>
                        <div className="data-cube">
                            <span className="label">Arrival Time</span>
                            <span className="value">{summaryData?.arrival_time || "N/A"}</span>
                        </div>
                        <div className="data-cube highlight">
                            <span className="label">ID:</span>
                            <span className="value">{summaryData?.p_id || p_id}</span>
                        </div>
                    </div>
                </div>

                {/* Attractive Clinical Assessment Row */}
            <div className="section-container">
                <h3 className="section-title">Clinical Assessment Details</h3>
                <div className="info-grid-row-4">
                    <div className="data-cube-large">
                        <label><b>Chief Complaint</b></label><p style={{ margin: '2px 0', fontWeight: '500', fontSize: '16px' }}>{summaryData?.chief_complaint || "N/A"}</p>
                        <div style={{ fontSize: '15px', color: 'black', lineHeight: '1.2' }}>
                            <div><b>Location:</b> {summaryData?.location || "Unknown"}</div>
                            <div><b>On-set:</b> {summaryData?.onset || "N/A"}</div>
                        </div>
                    </div>
                    <div className="data-cube-large"><label><b>Pain Scale</b></label><p style={{ margin: '2px 0', fontWeight: '500', fontSize: '16px' }}>{summaryData?.pain_scale ? `${summaryData.pain_scale}/10` : "0/10"}</p>
                        <div style={{ fontSize: '15px', color: 'black', lineHeight: '1.2' }}>
                                <div><b>Pattern:</b> {summaryData?.pattern || "Unknown"}</div>
                                <div><b>Factor:</b> {summaryData?.modifying_factors || "N/A"}</div>
                        </div>
                    </div>
                    <div className="data-cube-large"><label><b>Neurologic Status</b></label><p>{summaryData?.neurologic || "Stable"}</p></div>
                    <div className="data-cube-large"><label><b>Fever & Infection</b></label><p>{summaryData?.fever || "None"}</p></div>
                    
                </div>

                {/* Second Row: 3 Cubes */}
                <div className="info-grid-row-4">
                    <div className="data-cube-large"><label><b>Respiratory Assessment</b></label><p style={{ margin: '2px 0', fontWeight: '500', fontSize: '16px' }}>{summaryData?.respiratory || "Normal"}</p>
                        <div style={{ fontSize: '15px', color: 'black', lineHeight: '1.2' }}>
                                <div><b>Cough Type:</b> {summaryData?.cough || "Unknown"}</div>
                        </div>
                    </div>
                    <div className="data-cube-large"><label><b>Red Flag Symptoms</b></label><p>{summaryData?.red_flags || "None"}</p></div>
                    <div className="data-cube-large"><label><b>Cardiovascular</b></label><p>{summaryData?.cardiovascular || "Stable"}</p></div>
                    <div className="data-cube-large"><label><b>Medications & Allergies</b></label><p style={{ margin: '2px 0', fontWeight: '500', fontSize: '16px' }}>{summaryData?.medications || "NKDA"}</p>
                        <div style={{ fontSize: '15px', color: 'black', lineHeight: '1.2' }}>
                                <div><b>Medical History:</b> {summaryData?.history || "Unknown"}</div>
                        </div>
                    </div>
                </div>
            </div>

            <div className="section-container">
                <h3 className="section-title">Patient Notes</h3>
                <div style={{ paddingLeft: '80px', paddingBottom: '20px' }}> {/* Pulls it away from the border */}
                    <div className="data-cube-large" style={{ 
                        maxWidth: '950px', // Prevents it from being too long
                        textAlign: 'left',
                        borderLeft: '5px solid #0095FF', // Blue accent line
                        display: 'block', // Ensures it behaves like a box
                        minHeight: '80px'
                    }}>
                        <p style={{ color: '#4A5568', fontSize: '14px', margin: 0, paddingTop:'10px' }}>
                            {summaryData?.notes || "No additional notes provided."}
                        </p>
                    </div>
                </div>
            </div>
                {/* Triage Result Section */}
                <div className="section-container">
                    <h3>Triage Assessment Result</h3>
                    <div className="result-layout">
                        {/* Status Cube */}
                        <div className="status-cube high">
                            <div className="status-icon">⚠️</div>
                            <div className="status-text">
                                <h1>{summaryData?.urgency || "HIGH"}</h1>
                                <p>Priority Level: 2</p>
                            </div>
                        </div>
                    </div>
                </div>

                
            </div>
            <button className="nav-back-btn" onClick={() => navigate('/dashboard')}>Back to Dashboard</button>
        </div>
    );
};

export default ClinicalSummary;