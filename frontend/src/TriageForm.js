import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './Dashboard.css';

const TriageForm = () => {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        p_id: localStorage.getItem('currentPatientId') || '',
        arrival_time: '',
        age: '',
        gender:'',
        presenting_complaint_Main_Concern: '',
        symptom_location: '',
        symptom_onset: '',
        
    });
    const handleChange = (e) => {
        const { name, value } = e.target; 
        if (name === "age") {
           
            if (value === "") {
                setFormData(prev => ({
                    ...prev,
                    age: ""
                }));
            } else {
                setFormData(prev => ({
                    ...prev,
                    age: Number(value)
                }));
            }
        } else {
            setFormData(prev => ({
                ...prev,
                [name]: value
            }));
        }
    };


    const handleNextStep = async () => {
        if (formData.age === "" || formData.age <= 0) {
            alert("Please enter a valid age");
            return;
        }

        try {
            const response = await fetch('http://127.0.0.1:8000/submit-triage', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(formData)
            });

            if (response.ok) {
                // Instead of clinical summary, go to the next part of the form
                navigate('/triage-form-2'); 
            } else {
                const result = await response.json();
                alert("Submission Failed: " + JSON.stringify(result.detail));
            }
        } catch (error) {
            alert("Connection Error: Could not reach the server.");
        }
    };

    return (
        <div className="dashboard-container" style={{ display: 'block', backgroundColor: '#F4F7FE', height: '100vh', overflowY: 'auto' }}>
            
            
            <div style={{ backgroundColor: 'white', padding: '15px 40px', display: 'flex', alignItems: 'center', borderBottom: '1px solid #E0E5F2', position: 'sticky', top: 0, zIndex: 100 }}>
                <div style={{ backgroundColor: '#0095FF', padding: '8px', borderRadius: '8px', marginRight: '15px' }}>
                    <img src="https://img.icons8.com/material-rounded/24/ffffff/hospital.png" alt="icon" style={{ width: '20px' }} />
                </div>
                <div>
                    <h2 style={{ fontSize: '18px', margin: 0, color: '#1B2559' }}>Emergency Department</h2>
                    <p style={{ fontSize: '12px', margin: 0, color: '#A3AED0' }}>Patient Intake & Triage Form</p>
                </div>
            </div>
            {/* Progress Bar Container */}
            <div style={{ backgroundColor: 'white', padding: '15px 40px', borderBottom: '1px solid #E0E5F2' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                    <span style={{ fontSize: '12px', fontWeight: '600', color: '#0095FF' }}>Step 1 of 3</span>
                    <span style={{ fontSize: '12px', fontWeight: '500', color: '#A3AED0' }}>Basic Intake</span>
                </div>
                <div style={{ position: 'relative', height: '6px', width: '100%', backgroundColor: '#F4F7FE', borderRadius: '10px' }}>
                    <div style={{ 
                        position: 'absolute', 
                        left: 0, 
                        top: 0, 
                        height: '100%', 
                        width: '33.33%', 
                        backgroundColor: '#2B68FF', 
                        borderRadius: '10px',
                        boxShadow: '0px 2px 4px rgba(43, 104, 255, 0.3)' 
                    }}>
                    </div>
                </div>
            </div>

          <div style={{ maxWidth: '800px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '30px' }}>
    
                    {/* Basic Information Card */}
                    <div className="triage-card-refined">
                        <div className="card-header">
                            <img src="https://img.icons8.com/?size=100&id=EFc9qeUcZr4f&format=png&color=000000" alt="icon" />
                            <h3>Basic Information</h3>
                        </div>
                        
                        <div className="input-grid">
                            <div className="input-group">
                                <label className="triage-label">Patient ID</label>
                                <input type="text" className="triage-input" value={formData.p_id} readOnly />
                                <span className="helper-text">Auto-generated unique identifier</span>
                            </div>
                            <div className="input-group">
                                <label className="triage-label">Arrival Time</label>
                                <input type="time" className="triage-input" name="arrival_time"  value={formData.arrival_time} onChange={handleChange}/> 
                            </div>
                            <div className="input-group">
                            <label className="triage-label">Age</label>
                            <input type="number" name="age" className="triage-input" placeholder="Years" value={formData.age} onChange={handleChange} />
                            </div>
                            <div className="input-group">
                                <label className="triage-label">Gender</label>
                                <select className="triage-input" name="gender" placeholder="Gender" value={formData.gender} onChange={handleChange}>
                                    <option value="">Select gender</option>
                                    <option value="male">Male</option>
                                    <option value="female">Female</option>
                                </select>
                            </div>
                        </div>
                    </div>

                    {/* Chief Complaint Card */}
                    <div className="triage-card-refined">
                        <div className="card-header">
                            <img src="https://img.icons8.com/color/48/stethoscope.png" alt="icon" />
                            <h3>Chief Complaint</h3>
                        </div>
                        
                        <div className="input-group full-width">
                            <label>Primary Complaint</label>
                            <textarea className="input-field text-area" placeholder="Describe the patient's primary complaint in detail..." value={formData.presenting_complaint_Main_Concern} name="presenting_complaint_Main_Concern" onChange={handleChange}></textarea>
                            <span className="helper-text">Include patient's own words when possible</span>
                        </div>

                        <div className="input-grid" style={{ marginTop: '20px' }}>
                            <div className="input-group">
                                <label>Symptom Location</label>
                                <select className="triage-input" name="symptom_location" value={formData.symptom_location} onChange={handleChange} style={{ width: '100%', marginBottom: '15px' }}>
                                    <option value="">Select Location</option>
                                    <option value="Chest">Chest</option>
                                    <option value="Abdomen">Abdomen</option>
                                    <option value="Head">Head</option>
                                    <option value="Limb">Limb</option>
                                    <option value="Back">Back</option>
                                    <option value="Other">Other</option>
                                </select>
                            </div>
                            <div className="input-group">
                                <label>Symptom Onset</label>
                                <select className="triage-input" name="symptom_onset" value={formData.symptom_onset} onChange={handleChange}>
                                    <option value="">Select Onset</option>
                                    <option value="Sudden">Sudden</option>
                                    <option value="Gradual">Gradual</option>
                                    <option value="Chronic">Chronic</option>
                                </select>
                            </div>
                        </div>
                    </div>
                </div>
                {/* Bottom Navigation Section */}
                <div style={{ 
                    maxWidth: '800px', 
                    margin: '40px auto', 
                    display: 'flex', 
                    justifyContent: 'flex-end', 
                    paddingBottom: '50px' 
                }}>
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
                
         </div>
        
    );
};

export default TriageForm;