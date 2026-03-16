import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './Dashboard.css';

const TriageForm = () => {
    const navigate = useNavigate();
    const [formData, setFormData] = useState({
        p_id: localStorage.getItem('currentPatientId') || '',
        arrival_time: '',
        age: '',
        presenting_complaint_Main_Concern: '',
        symptom_location: '',
        symptom_onset: '',
        Pain_assessment_pain_scale: 0,
        pain_pattern: '',
        modifying_factors: '',
        red_flag_symptoms: [], 
        cns_speech_clarity: '',
        fever_infection: [],
        respiratory_sob_status: '',
        cough_type: '',
        cardiovascular: [],
        medical_history: [],
        medications_allergies: []
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


    const handleCheckboxChange = (columnName, value) => {
        setFormData(prev => {
            const currentList = prev[columnName];
            const newList = currentList.includes(value)
                ? currentList.filter(item => item !== value)
                : [...currentList, value];
            return { ...prev, [columnName]: newList };
        });
    };
    const handleSubmit = async (e) => {
        e.preventDefault();
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
            const result = await response.json();
            if (response.ok) {
            alert("Success: " + result.message);
            const patientId = formData.p_id;
            localStorage.removeItem('currentPatientId');
            navigate(`/clinical/${patientId}`);
        } else {
            
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

            <div style={{ padding: '30px 40px' }}>
                {/* Identification Bar  */}
                <div style={{ backgroundColor: '#EBF3FF', padding: '12px 20px', borderRadius: '10px', display: 'flex', gap: '15px', marginBottom: '20px' }}>
                    <div style={{ flex: 1 }}>
                        <label className="triage-label">Patient ID</label>
                        <input type="text" className="triage-input" value={formData.p_id} readOnly />
                    </div>
                    <div style={{ flex: 1 }}>
                        <label className="triage-label">Arrival Time</label>
                        <input type="time" className="triage-input" name="arrival_time"  value={formData.arrival_time} onChange={handleChange}/>
                    </div>
                    <div style={{ flex: 1 }}>
                        <label className="triage-label">Age</label>
                        <input type="number" name="age" className="triage-input" placeholder="Years" value={formData.age} onChange={handleChange} />
                    </div>
                </div>

                <form onSubmit={handleSubmit}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '25px', alignItems: 'start' }}>
                        
                        {/* LEFT COLUMN */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '25px' }}>
                            
                            
                            <div className="triage-card">
                                <h4 style={{ color: '#0095FF' }}>🩺 Presenting Complaint</h4>
                                <p className="triage-sub">Main concern / reason for visit</p>
                                <div className="triage-grid-2">
                                    <label className="option-box"><input type="radio" name="presenting_complaint_Main_Concern" value="Pain" onChange={handleChange} /> Pain</label>
                                    <label className="option-box"><input type="radio" name="presenting_complaint_Main_Concern" value="Breathing difficulty" onChange={handleChange}/> Breathing difficulty</label>
                                    <label className="option-box"><input type="radio" name="presenting_complaint_Main_Concern" value="Injury" onChange={handleChange}/> Injury</label>
                                    <label className="option-box"><input type="radio" name="presenting_complaint_Main_Concern" value="Infection" onChange={handleChange}/> Infection</label>
                                    <label className="option-box"><input type="radio" name="presenting_complaint_Main_Concern" value="Mental Health" onChange={handleChange}/> Mental Health</label>
                                    <label className="option-box"><input type="radio" name="presenting_complaint_Main_Concern" value="Other" onChange={handleChange}/> Other</label>
                                </div>
                                <p className="triage-sub" style={{ marginTop: '15px' }}>Symptom location</p>
                                <div className="triage-grid-3">
                                    <label className="option-box"><input type="radio" name="symptom_location" value="Chest" onChange={handleChange}/> Chest</label>
                                    <label className="option-box"><input type="radio" name="symptom_location" value="Abdomen" onChange={handleChange} /> Abdomen</label>
                                    <label className="option-box"><input type="radio" name="symptom_location" value="Head" onChange={handleChange} /> Head</label>
                                    <label className="option-box"><input type="radio" name="symptom_location" value="Limb" onChange={handleChange}/> Limb</label>
                                    <label className="option-box"><input type="radio" name="symptom_location" value="Back" onChange={handleChange} /> Back</label>
                                    <label className="option-box"><input type="radio" name="symptom_location" value="Other" onChange={handleChange} /> Other</label>
                                </div>
                                <p className="triage-sub" style={{ marginTop: '15px' }}>Symptom Onset</p>
                                <div className="triage-grid-3">
                                    <label className="option-box"><input type="radio" name="symptom_onset" value="Sudden" onChange={handleChange} /> Sudden</label>
                                    <label className="option-box"><input type="radio" name="symptom_onset" value="Gradual" onChange={handleChange} /> Gradual</label>
                                    <label className="option-box"><input type="radio" name="symptom_onset" value="Chronic" onChange={handleChange} /> Chronic</label>
                                </div>
                            </div>

                         
                            <div className="triage-card">
                                <h4 style={{ color: '#FF5E5E' }}>🌡️ Pain Assessment</h4>
                                <p className="triage-sub">Pain Scale (0-10)</p>
                                <p style={{ fontSize: '12px' }}>Pain scale (0-10)</p>
                                <input type="range" name="Pain_assessment_pain_scale" value={formData.Pain_assessment_pain_scale} onChange={handleChange}min="0" max="10" style={{ width: '100%' }} />
                                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px' }}>
                                    <span>0</span><span>5</span><span>10</span>
                                </div>
                                <p className="triage-sub">Pain Pattern</p>
                                <div className="triage-grid-3">
                                    <label className="option-box"><input type="radio" name="pain_pattern" value="Constant" onChange={handleChange}/> Constant</label>
                                    <label className="option-box"><input type="radio" name="pain_pattern" value="Intermittent" onChange={handleChange}/> Intermittent</label>
                                    <label className="option-box"><input type="radio" name="pain_pattern" value="New" onChange={handleChange}/> New</label>
                                </div>
                                <p className="triage-sub">Modifying Factors</p>
                                <div className="triage-grid-3">
                                    <label className="option-box"><input type="radio" name="modifying_factors" value="Movement" onChange={handleChange}/> Movement</label>
                                    <label className="option-box"><input type="radio" name="modifying_factors" value="Rest" onChange={handleChange}/> Rest</label>
                                    <label className="option-box"><input type="radio" name="modifying_factors" value="Medication" onChange={handleChange}/> Medication</label>
                                    <label className="option-box"><input type="radio" name="modifying_factors" value="None" onChange={handleChange}/> None</label>
                                </div>
                            </div>

                            
                            <div className="triage-card" style={{ border: '1px solid #FF5E5E' }}>
                                <h4 style={{ color: '#FF5E5E' }}>⚠️ Red Flag Symptoms</h4>
                                <div className="triage-stack">
                                    <label className="option-box-red"><input type="checkbox" checked={formData.red_flag_symptoms.includes("Chest pain")} onChange={() => handleCheckboxChange("red_flag_symptoms", "Chest pain")}/> Chest pain</label>
                                    <label className="option-box-red"><input type="checkbox" checked={formData.red_flag_symptoms.includes("Difficulty breathing")} onChange={() => handleCheckboxChange("red_flag_symptoms", "Difficulty breathing")}/> Difficulty breathing</label>
                                    <label className="option-box-red"><input type="checkbox" checked={formData.red_flag_symptoms.includes("Loss of consciousness")} onChange={() => handleCheckboxChange("red_flag_symptoms", "Loss of consciousness")}/> Loss of consciousness</label>
                                    <label className="option-box-red"><input type="checkbox" checked={formData.red_flag_symptoms.includes("Uncontrolled bleeding")} onChange={() => handleCheckboxChange("red_flag_symptoms", "Uncontrolled bleeding")}/> Uncontrolled bleeding</label>
                                    <label className="option-box-red"><input type="checkbox" checked={formData.red_flag_symptoms.includes("Sudden Weakness")} onChange={() => handleCheckboxChange("red_flag_symptoms", "Sudden Weakness")}/> Sudden Weakness</label>
                                    <label className="option-box-red"><input type="checkbox" checked={formData.red_flag_symptoms.includes("Severe Abdominal Pain")} onChange={() => handleCheckboxChange("red_flag_symptoms", "Severe Abdominal Pain")}/> Severe Abdominal Pain</label>
                                    <label className="option-box-red"><input type="checkbox" checked={formData.red_flag_symptoms.includes("None")} onChange={() => handleCheckboxChange("red_flag_symptoms", "None")}/> None</label>
                                </div>
                            </div>

                            <div className="triage-card">
                                <h4 style={{ color: '#5E72E4' }}>💊 Medications & Allergies</h4>
                                <div className="triage-stack" style={{ marginTop: '10px' }}>
                                    <label className="option-box"><input type="checkbox" checked={formData.medications_allergies.includes("Prescription medication use")} onChange={() => handleCheckboxChange("medications_allergies", "Prescription medication use")}/> Prescription medication use</label>
                                    <label className="option-box"><input type="checkbox" checked={formData.medications_allergies.includes("Blood thinner use")} onChange={() => handleCheckboxChange("medications_allergies", "Blood thinner use")}/> Blood thinner use</label>
                                    <label className="option-box"><input type="checkbox" checked={formData.medications_allergies.includes("Drug allergies")} onChange={() => handleCheckboxChange("medications_allergies", "Drug allergies")}/> Drug allergies</label>
                                </div>
                            </div>
                        </div>

                        {/* RIGHT COLUMN */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '25px' }}>
                            
                            
                            <div className="triage-card">
                                <h4 style={{ color: '#A33CFF' }}>🧠 Consciousness & Neurologic Status</h4>
                                <p className="triage-sub">Speech Clarity</p>
                                <div className="triage-grid-2" style={{ marginTop: '10px' }}>
                                    <label className="option-box"><input type="radio" name="cns_speech_clarity" value="Clear" onChange={handleChange}/> Clear</label>
                                    <label className="option-box"><input type="radio" name="cns_speech_clarity" value="Slurred" onChange={handleChange} /> Slurred</label>
                                </div>
                                <div className="triage-stack" style={{ marginTop: '10px' }}>
                                    <label className="option-box"><input type="checkbox" checked={formData.cns_speech_clarity.includes("Confusion")} onChange={() => handleCheckboxChange("cns_speech_clarity", "Confusion")}/> Confusion</label>
                                    <label className="option-box"><input type="checkbox" checked={formData.cns_speech_clarity.includes("Disorientation")} onChange={() => handleCheckboxChange("cns_speech_clarity", "Disorientation")}/> Disorientation</label>
                                    <label className="option-box"><input type="checkbox" checked={formData.cns_speech_clarity.includes("Weakness")} onChange={() => handleCheckboxChange("cns_speech_clarity", "Weakness")}/> Weakness</label>
                                    <label className="option-box"><input type="checkbox" checked={formData.cns_speech_clarity.includes("Numbness")} onChange={() => handleCheckboxChange("cns_speech_clarity", "Numbness")}/> Numbness</label>
                                    <label className="option-box"><input type="checkbox" checked={formData.cns_speech_clarity.includes("Facial Drop")} onChange={() => handleCheckboxChange("cns_speech_clarity", "Facial Drop")}/> Facial Drop</label>
                                </div>
                            </div>

                            <div className="triage-card">
                                <h4 style={{ color: '#5E72E4' }}>💊 Fever and Infection</h4>
                                <div className="triage-stack" style={{ marginTop: '10px' }}>
                                    <label className="option-box"><input type="checkbox" checked={formData.fever_infection.includes("Fever")} onChange={() => handleCheckboxChange("fever_infection", "Fever")}/> Fever</label>
                                    <label className="option-box"><input type="checkbox" checked={formData.fever_infection.includes("Nausea")} onChange={() => handleCheckboxChange("fever_infection", "Nausea")}/> Nausea</label>
                                    <label className="option-box"><input type="checkbox" checked={formData.fever_infection.includes("Diarrhea")} onChange={() => handleCheckboxChange("fever_infection", "Diarrhea")}/> Diarrhea</label>
                                    <label className="option-box"><input type="checkbox" checked={formData.fever_infection.includes("Recent Sick Contact")} onChange={() => handleCheckboxChange("fever_infection", "Recent Sick Contact")}/> Recent Sick Contact</label>
                                </div>
                            </div>

                            
                            <div className="triage-card">
                                <h4 style={{ color: '#0095FF' }}>🫁 Respiratory Assessment</h4>
                                <p className="triage-sub">Shortness of breath</p>
                                <div className="triage-grid-3">
                                    <label className="option-box"><input type="radio" name="respiratory_sob_status" value="At rest" onChange={handleChange}/> At rest</label>
                                    <label className="option-box"><input type="radio" name="respiratory_sob_status" value="With Activity" onChange={handleChange}/> With Activity</label>
                                    <label className="option-box"><input type="radio" name="respiratory_sob_status" value="None" onChange={handleChange} /> None</label>
                                </div>
                                <p className="triage-sub">Cough Type</p>
                                <div className="triage-grid-3">
                                    <label className="option-box"><input type="radio" name="cough_type" value="Dry" onChange={handleChange}/> Dry</label>
                                    <label className="option-box"><input type="radio" name="cough_type" value="Productive" onChange={handleChange} /> Productive</label>
                                    <label className="option-box"><input type="radio" name="cough_type" value="Wheezing" onChange={handleChange} /> Wheezing</label>
                                </div>
                            </div>

                            
                            <div className="triage-card">
                                <h4 style={{ color: '#FF5E5E' }}>❤️ Cardiovascular Concerns</h4>
                                <div className="triage-stack" style={{ marginTop: '10px' }}>
                                    <label className="option-box"><input type="checkbox" checked={formData.cardiovascular.includes("Palpitations")} onChange={() => handleCheckboxChange("cardiovascular", "Palpitations")}/> Palpitations</label>
                                    <label className="option-box"><input type="checkbox" checked={formData.cardiovascular.includes("Leg swelling")} onChange={() => handleCheckboxChange("cardiovascular", "Leg swelling")}/> Leg swelling</label>
                                </div>
                            </div>

                            
                            <div className="triage-card">
                                <h4 style={{ color: '#05CD99' }}>📋 Medical History</h4>
                                <div className="triage-stack">
                                    <label className="option-box"><input type="checkbox" checked={formData.medical_history.includes("Chronic conditions")} onChange={() => handleCheckboxChange("medical_history", "Chronic conditions")}/> Chronic conditions</label>
                                    <label className="option-box"><input type="checkbox" checked={formData.medical_history.includes("Recent hospitalization")} onChange={() => handleCheckboxChange("medical_history", "Recent hospitalization")}/> Recent hospitalization</label>
                                    <label className="option-box"><input type="checkbox" checked={formData.medical_history.includes("Recent surgery")} onChange={() => handleCheckboxChange("medical_history", "Recent surgery")}/> Recent surgery</label>
                                    <label className="option-box"><input type="checkbox" checked={formData.medical_history.includes("Immunocompromised Status")} onChange={() => handleCheckboxChange("medical_history", "Immunocompromised Status")}/> Immunocompromised Status</label>
                                </div>
                            </div>
                        </div>
                    </div>

                    <div style={{ textAlign: 'center', marginTop: '40px', paddingBottom: '50px' }}>
                        <button type="submit" className="triage-submit-btn">
                            Submit Assessment
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};

export default TriageForm;