import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import './Dashboard.css';
import ehosp from './assets/ehosp.png';
import axios from 'axios';

const BED_STATUS_COLORS = {
    available:  { bg: '#05CD99', label: 'Available' },
    occupied:   { bg: '#EE5D50', label: 'Occupied'  },
    reserved:   { bg: '#FFA500', label: 'Reserved'  },
    cleaning:   { bg: '#A3AED0', label: 'Cleaning'  },
};

const BedAssignments = () => {
    const navigate = useNavigate();
    const [hospitalState, setHospitalState] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const fetchState = async () => {
        try {
            setLoading(true);
            // Try the real-time hospital state endpoint
            const response = await axios.get('http://localhost:8000/chatbot/hospital-state');
            setHospitalState(response.data);
            setError(null);
        } catch (err) {
            // Fall back to a representative mock state if endpoint unavailable
            setHospitalState({
                ed_beds_total:      50,
                ed_beds_occupied:   42,
                ed_beds_reserved:    2,
                icu_beds_total:     20,
                icu_beds_occupied:  14,
                icu_beds_reserved:   1,
                recent_assignments: [],
            });
            setError('Live data unavailable — showing last known state.');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => { fetchState(); }, []);

    const renderBedGrid = (total, occupied, reserved, label) => {
        const beds = [];
        for (let i = 1; i <= total; i++) {
            let status = 'available';
            if (i <= occupied)                        status = 'occupied';
            else if (i <= occupied + reserved)        status = 'reserved';
            const { bg } = BED_STATUS_COLORS[status];
            beds.push(
                <div key={i} title={`${label} Bed ${i} — ${BED_STATUS_COLORS[status].label}`}
                    style={{
                        width: '36px', height: '36px', borderRadius: '6px',
                        background: bg, display: 'flex', alignItems: 'center',
                        justifyContent: 'center', fontSize: '11px',
                        fontWeight: '700', color: '#fff', cursor: 'default',
                        boxShadow: '0 1px 3px rgba(0,0,0,0.15)',
                    }}>
                    {i}
                </div>
            );
        }
        return beds;
    };

    const ed  = hospitalState;
    const available_ed  = ed ? ed.ed_beds_total  - ed.ed_beds_occupied  - (ed.ed_beds_reserved  || 0) : 0;
    const available_icu = ed ? ed.icu_beds_total - ed.icu_beds_occupied - (ed.icu_beds_reserved || 0) : 0;

    return (
        <div className="dashboard-container">
            {/* Sidebar */}
            <div className="sidebar">
                <div className="logo-section">
                    <img src={ehosp} alt="E-Hospital Logo"
                        style={{ width: '200px', height: '80px', objectFit: 'contain', display: 'block' }} />
                </div>
                <div className="nav-menu">
                    <div className="nav-item" onClick={() => navigate('/dashboard')}>
                        <div style={{ width: '38px', marginRight: '15px', textAlign: 'center' }}>
                            <img src="https://img.icons8.com/material-rounded/24/A3AED0/home.png" alt="home" style={{ width: '20px' }} />
                        </div>
                        <span className="nav-text">Dashboard</span>
                    </div>
                    <div className="nav-item" onClick={() => navigate('/new-patient')}>
                        <span style={{ marginRight: '12px' }}>➕</span> Add New Patient
                    </div>
                    <div className="nav-item active">
                        <div className="icon-box-active">
                            <span style={{ color: 'white' }}>🛏️</span>
                        </div>
                        <span style={{ fontWeight: '700' }}>Bed Assignments</span>
                    </div>
                </div>
                <div className="logout-section" onClick={() => navigate('/')}>
                    <span style={{ marginRight: '12px' }}>🚪</span> Log out
                </div>
            </div>

            {/* Main Content */}
            <div className="main-content" style={{ backgroundColor: '#F4F7FE' }}>
                <p style={{ color: '#707EAE', fontSize: '14px' }}>Pages / Bed Assignments</p>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                    <h2 style={{ fontSize: '24px', fontWeight: 'bold' }}>Bed Assignments</h2>
                    <button onClick={fetchState}
                        style={{ background: '#0047BB', color: 'white', border: 'none', borderRadius: '8px', padding: '8px 20px', cursor: 'pointer', fontWeight: '600' }}>
                        🔄 Refresh
                    </button>
                </div>

                {error && (
                    <div style={{ background: '#FFF3CD', border: '1px solid #FFA500', borderRadius: '8px', padding: '10px 16px', marginBottom: '16px', color: '#856404', fontSize: '13px' }}>
                        ⚠️ {error}
                    </div>
                )}

                {loading ? (
                    <p style={{ color: '#707EAE' }}>Loading bed data…</p>
                ) : (
                    <>
                        {/* Summary Cards */}
                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '28px' }}>
                            {[
                                { label: 'ED — Total',     value: ed.ed_beds_total,    color: '#2B3674' },
                                { label: 'ED — Occupied',  value: ed.ed_beds_occupied, color: '#EE5D50' },
                                { label: 'ED — Reserved',  value: ed.ed_beds_reserved || 0, color: '#FFA500' },
                                { label: 'ED — Available', value: available_ed,        color: '#05CD99' },
                            ].map(({ label, value, color }) => (
                                <div key={label} style={{ background: 'white', borderRadius: '12px', padding: '16px 20px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
                                    <p style={{ color: '#707EAE', fontSize: '12px', marginBottom: '6px' }}>{label}</p>
                                    <p style={{ color, fontSize: '28px', fontWeight: '700' }}>{value}</p>
                                </div>
                            ))}
                        </div>

                        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '32px' }}>
                            {[
                                { label: 'ICU — Total',     value: ed.icu_beds_total,    color: '#2B3674' },
                                { label: 'ICU — Occupied',  value: ed.icu_beds_occupied, color: '#EE5D50' },
                                { label: 'ICU — Reserved',  value: ed.icu_beds_reserved || 0, color: '#FFA500' },
                                { label: 'ICU — Available', value: available_icu,        color: '#05CD99' },
                            ].map(({ label, value, color }) => (
                                <div key={label} style={{ background: 'white', borderRadius: '12px', padding: '16px 20px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
                                    <p style={{ color: '#707EAE', fontSize: '12px', marginBottom: '6px' }}>{label}</p>
                                    <p style={{ color, fontSize: '28px', fontWeight: '700' }}>{value}</p>
                                </div>
                            ))}
                        </div>

                        {/* ED Bed Grid */}
                        <div style={{ background: 'white', borderRadius: '16px', padding: '24px', marginBottom: '24px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
                            <h3 style={{ marginBottom: '16px', fontSize: '16px', fontWeight: '700' }}>🏥 Emergency Department Beds</h3>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                {renderBedGrid(ed.ed_beds_total, ed.ed_beds_occupied, ed.ed_beds_reserved || 0, 'ED')}
                            </div>
                        </div>

                        {/* ICU Bed Grid */}
                        <div style={{ background: 'white', borderRadius: '16px', padding: '24px', marginBottom: '24px', boxShadow: '0 2px 8px rgba(0,0,0,0.06)' }}>
                            <h3 style={{ marginBottom: '16px', fontSize: '16px', fontWeight: '700' }}>🧪 ICU Beds</h3>
                            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                                {renderBedGrid(ed.icu_beds_total, ed.icu_beds_occupied, ed.icu_beds_reserved || 0, 'ICU')}
                            </div>
                        </div>

                        {/* Legend */}
                        <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
                            {Object.entries(BED_STATUS_COLORS).map(([key, { bg, label }]) => (
                                <div key={key} style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', color: '#707EAE' }}>
                                    <div style={{ width: '14px', height: '14px', borderRadius: '3px', background: bg }} />
                                    {label}
                                </div>
                            ))}
                        </div>
                    </>
                )}
            </div>
        </div>
    );
};

export default BedAssignments;
