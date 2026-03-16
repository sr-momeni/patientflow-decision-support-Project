import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './Dashboard.css';

const TriageForm3 = () => {
    const navigate = useNavigate();

    // 1. Load data from previous steps and local storage
    const [formData, setFormData] = useState(() => {
        const saved = localStorage.getItem('triage_step3_data');
        return saved ? JSON.parse(saved) : {
            p_id: localStorage.getItem('currentPatientId') || '',
            red_flag_symptoms: '',
            leg_swelling: '',
            medical_history: '',
            recent_hospitalization: '',
            recent_surgery: '',
            immunocompromised: '',
            medications_allergies: '',
            drug_allergies: '',
            palpitations:''
        };
    });

    // 2. Sync with LocalStorage
    useEffect(() => {
        localStorage.setItem('triage_step3_data', JSON.stringify(formData));
    }, [formData]);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
    };

    const handleSubmit = async () => {
        // Merge everything for final submission
        const step1 = JSON.parse(localStorage.getItem('triage_step1_data') || '{}');
        const step2 = JSON.parse(localStorage.getItem('triage_step2_data') || '{}');
        
        const finalData = { ...step1, ...step2, ...formData };

        try {
            const response = await fetch('http://127.0.0.1:8000/submit-triage', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(finalData)
            });

            if (response.ok) {
                alert("Assessment Submitted Successfully!");
                localStorage.clear(); // Clean up
                navigate(`/clinical/${formData.p_id}`);
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
                    <span style={{ fontSize: '12px', fontWeight: '600', color: '#0095FF' }}>Step 3 of 3</span>
                    <span style={{ fontSize: '12px', fontWeight: '500', color: '#A3AED0' }}>Medical Background</span>
                </div>
                <div style={{ height: '6px', width: '100%', backgroundColor: '#F4F7FE', borderRadius: '10px' }}>
                    <div style={{ width: '100%', height: '100%', backgroundColor: '#2B68FF', borderRadius: '10px' }}></div>
                </div>
            </div>

            <div style={{ maxWidth: '900px', margin: '30px auto', display: 'flex', flexDirection: 'column', gap: '25px', padding: '0 20px' }}>
                

                    {/* Red Flag Symptoms */}
                    <div className="triage-card-refined" style={{ borderRadius: '15px', backgroundColor: 'white', padding: '25px', border: '1px solid #FFEBEB' }}>
                        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '15px' }}>
                            <img src="https://img.icons8.com/color/48/high-priority.png" alt="red-flag" style={{ width: '24px', marginRight: '10px' }} />
                            <h3 style={{ margin: 0, color: '#1B2559', fontSize: '16px' }}>Red Flag Symptoms <span style={{ color: '#FF4D49', fontSize: '12px', marginLeft: '10px', fontWeight: 'normal' }}>Critical Assessment</span></h3>
                        </div>
                        <label className="triage-label">Select any symptoms that require immediate attention:</label>
                        <select className="triage-input" name="red_flag_symptoms" value={formData.red_flag_symptoms} onChange={handleChange} style={{ marginTop: '10px', width:'100%' }}>
                            <option value="">Select red flag symptoms...</option>
                            <option value="None">None</option>
                            <option value="Chest Pain">Chest Pain</option>
                            <option value="Difficulty Breathing">Difficulty Breathing</option>
                            <option value="Loss of Consciousness">Loss of Consciousness</option>
                            <option value="Uncontrolled Bleeding">Uncontrolled Bleeding</option>
                            <option value="Sudden Weakness">Sudden Weakness</option>
                            <option value="Severe Abdominal Pain">Severe Abdominal Pain</option>
                        </select>
                    </div>

                    {/* Cardiovascular Concerns */}
                    <div className="triage-card-refined" style={{ borderRadius: '15px', backgroundColor: 'white', padding: '25px' }}>
                        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '15px' }}>
                            <img src="https://img.icons8.com/color/48/heart-monitor.png" alt="heart" style={{ width: '24px', marginRight: '10px' }} />
                            <h3 style={{ margin: 0, color: '#1B2559', fontSize: '16px' }}>Cardiovascular Concerns</h3>
                        </div>
                        <div className="input-grid" style={{ display: 'flex', gap: '20px' }}>
                            <div style={{ flex: 1 }}>
                                <label className="triage-label">Palpitations</label>
                                <select className="triage-input" name="palpitations" value={formData.palpitations} onChange={handleChange} style={{ marginTop: '10px', width:'100%' }}>
                                    <option value="">Select...</option>
                                    <option value="Yes">Yes</option>
                                    <option value="No">No</option>
                                </select>
                            </div>
                            <div style={{ flex: 1 }}>
                                <label className="triage-label">Leg Swelling</label>
                                <select className="triage-input" name="leg_swelling" value={formData.leg_swelling} onChange={handleChange} style={{ marginTop: '10px', width:'100%' }}>
                                    <option value="">Select...</option>
                                    <option value="Yes">Yes</option>
                                    <option value="No">No</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    {/* --- 5. Medical History --- */}
                    <div className="triage-card-refined" style={{ borderRadius: '12px', backgroundColor: 'white', padding: '30px', boxShadow: '0px 4px 12px rgba(16, 24, 40, 0.06)', marginBottom: '20px', maxWidth: '850px', margin: '0 auto 20px auto' }}>
                        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '20px' }}>
                          <h3 style={{ margin: 0, color: '#1B2559', fontSize: '18px', fontWeight: '700' }}>📋 Medical History</h3>
                        </div>

                        <div className="input-grid" style={{ display: 'flex', gap: '25px', flexWrap: 'wrap' }}>
                            <div className="input-group" style={{ width: '405px' }}>
                                <label className="triage-label">Chronic Conditions</label>
                                <select className="triage-input" name="medical_history" value={formData.medical_history} onChange={handleChange} style={{ marginTop: '10px', width:'100%' }}>
                                    <option value="">Select...</option>
                                    <option value="Diabetes">Diabetes</option>
                                    <option value="Hypertension">Hypertension</option>
                                    <option value="Heart Disease">Heart Disease</option>
                                    <option value="Asthma/COPD">Asthma/COPD</option>
                                    <option value="None">None</option>
                                </select>
                            </div>
                            <div className="input-group" style={{ width: '405px' }}>
                                <label className="triage-label">Recent Hospitalization</label>
                                <select className="triage-input" name="recent_hospitalization" value={formData.recent_hospitalization} onChange={handleChange} style={{ marginTop: '10px', width:'100%' }}>
                                    <option value="">Select...</option>
                                    <option value="Yes (within 30 days)">Yes (within 30 days)</option>
                                    <option value="Yes (within 6 months)">Yes (within 6 months)</option>
                                    <option value="No">No</option>
                                </select>
                            </div>
                            <div className="input-group" style={{ width: '405px' }}>
                                <label className="triage-label">Recent Surgery</label>
                                <select className="triage-input" name="recent_surgery" value={formData.recent_surgery} onChange={handleChange} style={{ marginTop: '10px', width:'100%' }}>
                                    <option value="">Select...</option>
                                    <option value="Yes">Yes</option>
                                    <option value="No">No</option>
                                </select>
                            </div>
                            <div className="input-group" style={{ width: '405px' }}>
                                <label className="triage-label">Immunocompromised Status</label>
                                <select className="triage-input" name="immunocompromised_status" value={formData.immunocompromised_status} onChange={handleChange} style={{ marginTop: '10px', width:'100%' }}>
                                    <option value="">Select...</option>
                                    <option value="Yes">Yes</option>
                                    <option value="No">No</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    {/* --- 6. Medications & Allergies --- */}
                    <div className="triage-card-refined" style={{ borderRadius: '12px', backgroundColor: 'white', padding: '30px', boxShadow: '0px 4px 12px rgba(16, 24, 40, 0.06)', marginBottom: '20px', maxWidth: '850px', margin: '0 auto 20px auto', width:'100%' }}>
                        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '20px' }}>
                            <img src="https://img.icons8.com/color/48/pills.png" alt="meds" style={{ width: '22px', marginRight: '10px' }} />
                            <h3 style={{ margin: 0, color: '#1B2559', fontSize: '18px', fontWeight: '700' }}>Medications & Allergies</h3>
                        </div>

                        <div className="input-grid" style={{ display: 'flex', gap: '25px', flexWrap: 'wrap', width:'100%' }}>
                            <div className="input-group" style={{ width: '405px' }}>
                                <label className="triage-label">Prescription Medication Use</label>
                                <select className="triage-input" name="medications_allergies" value={formData.medications_allergies} onChange={handleChange} style={{ marginTop: '10px', width:'100%' }}>
                                    <option value="">Select...</option>
                                    <option value="Yes">Yes</option>
                                    <option value="No">No</option>
                                </select>
                            </div>
                            <div className="input-group" style={{ width: '405px' }}> {/* Wider for drug allergies */}
                                <label className="triage-label">Drug Allergies</label>
                                <select className="triage-input" name="drug_allergies" value={formData.drug_allergies} onChange={handleChange} style={{ marginTop: '10px', width:'100%' }}>
                                    <option value="">Select...</option>
                                    <option value="Penicillin">Penicillin</option>
                                    <option value="Sulfa Drugs">Sulfa Drugs</option>
                                    <option value="NSAIDs">NSAIDs</option>
                                    <option value="None">None</option>
                                    <option value="Other">Other</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    {/* --- Submit Button --- */}
                    <div style={{ textAlign: 'center', marginTop: '40px' }}>
                        <button 
                            onClick={handleSubmit} 
                            style={{ 
                                backgroundColor: 'blue', 
                                color: 'white', 
                                padding: '12px 60px', 
                                borderRadius: '10px', 
                                border: 'none', 
                                fontSize: '16px', 
                                fontWeight: 'bold', 
                                cursor: 'pointer',
                                boxShadow: '0px 4px 12px rgba(5, 205, 153, 0.2)'
                            }}
                        >
                            Submit Assessment
                        </button>
                    </div>
                       
               
        </div>
    </div>
        
    );
};

export default TriageForm3;