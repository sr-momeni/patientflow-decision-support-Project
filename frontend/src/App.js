import React from "react";
import { BrowserRouter as Router, Routes, Route, Link } from "react-router-dom";
import "./App.css";
import ehospital from "./assets/ehospitallogo.png";
import staff from "./assets/Staff.png";
import LoginPage from "./LoginPage";
import SignUp from './SignUp';
import Dashboard from './Dashboard'; 
import Newpatient from "./Newpatient";
import TriageForm from './TriageForm';
import TriageForm2 from './TriageForm2';
import TriageForm3 from './TriageForm3';
import ClinicalSummary from "./ClinicalSummary";

// 1. This is your Landing Page component
const LandingPage = () => (
  <div className="container">
    <nav className="navbar">
      <div className="ehospital">
        <img src={ehospital} alt="E-Hospital Logo" />
      </div>   

      <div className="nav-buttons">
        {/* We change the button to a Link */}
        <Link to="/login">
          <button className="nav-btn">Log in</button>
        </Link>
        <Link to="/SignUp">
        <button className="nav-btn">Sign up</button>
        </Link>
      </div>
    </nav>

    <div className="hero">
      <img src={staff} alt="Urgency" style={{ width: '500px', height: 'auto' }} />
      <h1>Streamline Workflow, Accelerate Patient Care</h1>
    </div>
  </div>
);

// 2. This is the main App that switches between them
function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignUp />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/new-patient" element={<Newpatient />} />
        <Route path="/triage-form" element={<TriageForm />} />
        <Route path="/triage-form-2" element={<TriageForm2 />} />
        <Route path="/triage-form-3" element={<TriageForm3 />} />
        <Route path="/clinical/:p_id" element={<ClinicalSummary />} />
      </Routes>
    </Router>
  );
}

export default App;