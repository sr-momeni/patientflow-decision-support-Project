import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './Dashboard.css';

const TriageForm2 = () => {
    const navigate = useNavigate();
    const [formData, setFormData] = useState(() => {
        const saved = localStorage.getItem('triage_step2_data');
        return saved ? JSON.parse(saved) : {
        p_id: localStorage.getItem('currentPatientId') || '',
        Pain_assessment_pain_scale: 0,
        pain_pattern: '',
        modifying_factors: '',
        cns_speech_clarity: '',
        consciousness_status: '', 
        fever_infection: '',
        gi_symptoms: '',
        recent_sick_contact: '',
        respiratory_sob_status: '',
        cough_type: '',
        breathing_effort: ''
        };
    });
    useEffect(() => {
        localStorage.setItem('triage_step2_data', JSON.stringify(formData));
    }, [formData]);
    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: name === "Pain_assessment_pain_scale" ? Number(value) : value
        }));
    };

    const handleNextStep = async () => {
        const dataToSend = {
        ...formData,
        p_id: localStorage.getItem('currentPatientId') // Ensure this is NOT empty
        };
        try {
            // NOTE: Use a different endpoint if you want to UPDATE Step 1 data
            // Or ensure Step 1 logic is handled.
            const response = await fetch('http://127.0.0.1:8000/submit-triage', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(dataToSend)
            });

            if (response.ok) {
                navigate('/triage-form-3'); 
            } else {
                alert("Submission Failed");
            }
        } catch (error) {
            alert("Connection Error");
        }
    };

    return (
        
        <div className="dashboard-container" style={{ 
            display: 'block', 
            backgroundColor: '#F4F7FE', 
            minHeight: '100vh', 
            paddingBottom: '120px', 
            overflowY: 'auto' 
        }}>
            
            {/* Sticky Top Header */}
            <div style={{ backgroundColor: 'white', padding: '15px 40px', display: 'flex', alignItems: 'center', borderBottom: '1px solid #E0E5F2', position: 'sticky', top: 0, zIndex: 100 }}>
                <div style={{ backgroundColor: '#0095FF', padding: '8px', borderRadius: '8px', marginRight: '15px' }}>
                    <img src="https://img.icons8.com/material-rounded/24/ffffff/hospital.png" alt="icon" style={{ width: '20px' }} />
                </div>
                <div>
                    <h2 style={{ fontSize: '18px', margin: 0, color: '#1B2559' }}>Emergency Department</h2>
                    <p style={{ fontSize: '12px', margin: 0, color: '#A3AED0' }}>Clinical Condition</p>
                </div>
            </div>

            {/* Progress Bar Container */}
            <div style={{ backgroundColor: 'white', padding: '15px 40px', borderBottom: '1px solid #E0E5F2' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <span style={{ fontSize: '12px', fontWeight: '600', color: '#0095FF' }}>Step 2 of 3</span>
                    <span style={{ fontSize: '12px', fontWeight: '500', color: '#A3AED0' }}>Clinical Condition</span>
                </div>
                <div style={{ height: '6px', width: '100%', backgroundColor: '#F4F7FE', borderRadius: '10px' }}>
                    <div style={{ width: '66.66%', height: '100%', backgroundColor: '#2B68FF', borderRadius: '10px' }}></div>
                </div>
            </div>

            <div style={{ maxWidth: '900px', margin: '30px auto', display: 'flex', flexDirection: 'column', gap: '25px', padding: '0 20px' }}>
                
                {/* 1. Pain Assessment */}
                <div className="triage-card-refined" style={{  borderRadius: '15px', backgroundColor: 'white', padding: '20px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '20px' }}>
                        <img src="https://img.icons8.com/color/48/thermometer.png" alt="pain" style={{ width: '24px', marginRight: '10px' }} />
                        <h3 style={{ margin: 0, color: '#1B2559' }}>Pain Assessment</h3>
                    </div>
                    
                    <label className="triage-label">Pain Scale (0-10)</label>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '15px', margin: '20px 0' }}>
                        <span style={{ color: '#A3AED0' }}>0</span>
                        <input 
                            type="range" min="0" max="10" name="Pain_assessment_pain_scale"
                            value={formData.Pain_assessment_pain_scale} onChange={handleChange}
                            style={{ flex: 1, accentColor: '#0095FF' }}
                        />
                        <span style={{ color: '#A3AED0' }}>10</span>
                        <div style={{ padding: '8px 18px', background: '#F4F7FE', borderRadius: '8px', fontWeight: 'bold', color: '#0095FF' }}>
                            {formData.Pain_assessment_pain_scale}
                        </div>
                    </div>
                    
                    <div className="input-grid">
                        <div className="input-group">
                            <label className="triage-label">Pain Pattern</label>
                            <select className="triage-input" name="pain_pattern" value={formData.pain_pattern} onChange={handleChange}>
                                <option value="">Select pattern</option>
                                <option value="Constant">Constant</option>
                                <option value="Intermittent">Intermittent</option>
                            </select>
                        </div>
                        <div className="input-group">
                            <label className="triage-label">Modifying Factors</label>
                            <select className="triage-input" name="modifying_factors" value={formData.modifying_factors} onChange={handleChange}>
                                <option value="">Select factors</option>
                                <option value="Worse with movement">Worse with movement</option>
                                <option value="Better with rest">Better with rest</option>
                            </select>
                        </div>
                    </div>
                </div>

                {/* 2. Neurologic Status */}
                <div className="triage-card-refined" style={{ borderRadius: '15px', backgroundColor: 'white', padding: '20px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', marginBottom: '20px' }}>
                        <img src="https://img.icons8.com/color/48/brain.png" alt="brain" style={{ width: '24px', marginRight: '10px' }} />
                        <h3 style={{ margin: 0, color: '#1B2559' }}>Neurologic Status</h3>
                    </div>
                    <div className="input-grid">
                        <div className="input-group">
                            <label className="triage-label">Speech Clarity</label>
                            <select className="triage-input" name="cns_speech_clarity" value={formData.cns_speech_clarity} onChange={handleChange}>
                                <option value="">Assess speech</option>
                                <option value="Clear">Clear</option>
                                <option value="Slurred">Slurred</option>
                            </select>
                        </div>
                        <div className="input-group">
                            <label className="triage-label">Consciousness Status</label>
                            <select className="triage-input" name="consciousness_status" value={formData.consciousness_status} onChange={handleChange}>
                                <option value="">Assess consciousness</option>
                                <option value="Alert">Alert</option>
                                <option value="Confused">Confused</option>
                            </select>
                        </div>
                    </div>
                </div>
            </div>
            {/* --- 3. Infection & Fever --- */}
            <div className="triage-card-refined" style={{ borderRadius: '12px', backgroundColor: 'white', padding: '30px', boxShadow: '1cqb 1px 3px rgba(16, 24, 40, 0.1), 0px 1px 2px rgba(16, 24, 40, 0.06)', marginBottom: '20px', maxWidth: '850px', margin: '0 auto 20px auto'}}>
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: '20px' }}>
                    <img src="https://img.icons8.com/color/48/coronavirus.png" alt="infection" style={{ width: '22px', marginRight: '10px' }} />
                    <h3 style={{ margin: 0, color: '#1B2559', fontSize: '18px', fontWeight: '700' }}>Infection & Fever</h3>
                </div>
                
                <div className="input-grid" style={{ display: 'flex', gap: '25px', justifyContent: 'flex-start' }}>
                    <div className="input-group" style={{ width: '280px' }}>
                        <label className="triage-label" style={{ fontSize: '14px', color: '#1B2559', marginBottom: '8px', display: 'block' }}>Fever/Chills</label>
                        <select className="triage-input" name="fever_infection" value={formData.fever_infection} onChange={handleChange}>
                            <option value="">Select status</option>
                            <option value="Yes">Yes</option>
                            <option value="No">No</option>
                        </select>
                    </div>
                    <div className="input-group" style={{ width: '280px' }}>
                        <label className="triage-label" style={{ fontSize: '14px', color: '#1B2559', marginBottom: '8px', display: 'block' }}>GI Symptoms</label>
                        <select className="triage-input" name="gi_symptoms" value={formData.gi_symptoms} onChange={handleChange}>
                            <option value="">Select symptoms</option>
                            <option value="None">None</option>
                            <option value="Nausea">Nausea</option>
                        </select>
                    </div>
                    <div className="input-group" style={{ width: '280px' }}>
                        <label className="triage-label" style={{ fontSize: '14px', color: '#1B2559', marginBottom: '8px', display: 'block' }}>Recent Sick Contact</label>
                        <select className="triage-input" name="recent_sick_contact" value={formData.recent_sick_contact} onChange={handleChange}>
                            <option value="">Select exposure</option>
                            <option value="None">None</option>
                            <option value="Known Exposure">Known Exposure</option>
                        </select>
                    </div>
                </div>
            </div>

            {/* --- 4. Respiratory Assessment --- */}
            <div className="triage-card-refined" style={{ borderRadius: '12px', backgroundColor: 'white', padding: '30px', boxShadow: '1cqb 1px 3px rgba(16, 24, 40, 0.1), 0px 1px 2px rgba(16, 24, 40, 0.06)', marginBottom: '20px', maxWidth: '850px', margin: '0 auto 20px auto' }}>
                <div style={{ display: 'flex', alignItems: 'center', marginBottom: '20px' }}>
                    <img src="https://img.icons8.com/color/48/lungs.png" alt="lungs" style={{ width: '22px', marginRight: '10px' }} />
                    <h3 style={{ margin: 0, color: '#1B2559', fontSize: '18px', fontWeight: '700' }}>Respiratory Assessment</h3>
                </div>

                <div className="input-grid" style={{ display: 'flex', gap: '25px', justifyContent: 'flex-start' }}>
                    <div className="input-group" style={{ width: '280px' }}>
                        <label className="triage-label" style={{ fontSize: '14px', color: '#1B2559', marginBottom: '8px', display: 'block' }}>Shortness of Breath</label>
                        <select className="triage-input" name="respiratory_sob_status" value={formData.respiratory_sob_status} onChange={handleChange}>
                            <option value="">Assess breathing</option>
                            <option value="None">None</option>
                            <option value="Mild">Mild</option>
                        </select>
                    </div>
                    <div className="input-group" style={{ width: '280px' }}>
                        <label className="triage-label" style={{ fontSize: '14px', color: '#1B2559', marginBottom: '8px', display: 'block' }}>Cough Type</label>
                        <select className="triage-input" name="cough_type" value={formData.cough_type} onChange={handleChange}>
                            <option value="">Select cough type</option>
                            <option value="None">None</option>
                            <option value="Dry">Dry</option>
                        </select>
                    </div>
                    <div className="input-group" style={{ width: '280px' }}>
                        <label className="triage-label" style={{ fontSize: '14px', color: '#1B2559', marginBottom: '8px', display: 'block' }}>Breathing Effort</label>
                        <select className="triage-input" name="breathing_effort" value={formData.breathing_effort} onChange={handleChange}>
                            <option value="">Assess effort</option>
                            <option value="Normal">Normal</option>
                            <option value="Labored">Labored</option>
                        </select>
                    </div>
                </div>
            </div>
            {/* Bottom Navigation */}
            <div style={{ 
                position: 'fixed', 
                bottom: 0, 
                left: 0, 
                right: 0, 
                backgroundColor: 'white', 
                padding: '20px 40px', 
                display: 'flex', 
                justifyContent: 'space-between', 
                borderTop: '1px solid #E0E5F2',
                zIndex: 100 
            }}>
                <button 
                    onClick={() => navigate(-1)} 
                    style={{ backgroundColor: '#707EAE', color: 'white', padding: '12px 30px', border: 'none', borderRadius: '10px', cursor: 'pointer', fontWeight: '600' }}
                >
                    Back
                </button>
                <button 
                    onClick={handleNextStep} 
                    style={{ backgroundColor: '#2B68FF', color: 'white', padding: '12px 45px', border: 'none', borderRadius: '10px', cursor: 'pointer', fontWeight: 'bold' }}
                >
                    Next Step →
                </button>
            </div>
        </div>
    );
};

export default TriageForm2;