import React, { useState } from "react"; 
import { useNavigate } from 'react-router-dom';
import "./App.css"; 
import { Link } from 'react-router-dom';
import staff from "./assets/Staff.png"; 
import ehosp from "./assets/ehosp.png";

const LoginPage = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("");

  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault(); 
    
    // Bridge for FastAPI
    const response = await fetch("http://127.0.0.1:8000/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, role })
    });

    const data = await response.json();
    if (response.ok) {
      alert("Login Successful!");
      navigate('/dashboard');
    } else {
      alert("Error: " + data.detail);
    }
  };

  return (
    <div className="login-page-container">
      <div className="login-card">
        <form className="login-form" onSubmit={handleLogin}> {}
          <div className="login-logo">
            <img src={ehosp} alt="logo"  style={{ 
                            width: '250px',      
                            height: '90px',     
                            objectFit: 'contain',
                            alignItems:'center',
                            display: 'block',
                            marginLeft: 'auto',  
                            marginRight: 'auto' 
                        }} />
            
          </div>
          
          <select className="login-input" onChange={(e) => setRole(e.target.value)}>
            <option value="">Select a role</option>
            <option value="Clinical Staff">Clinical Staff</option>
          </select>
          
          
          <input 
            type="email" 
            placeholder="Email address" 
            className="login-input" 
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
          <input 
            type="password" 
            placeholder="Password" 
            className="login-input" 
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
          
          <div className="remember-me">
            <input type="checkbox" id="rem" /> <label htmlFor="rem">Remember me</label>
          </div>
          
          <button type="submit" className="login-submit-btn">Login</button>
          <p className="signup-link">Don't have an account? <Link to="/SignUp" className="signup-link"><span>Sign up</span></Link></p>
        </form>

        <div className="login-image">
          <img src={staff} alt="Staff" style={{ width: '450px', height: 'auto' }}/>
        </div>
      </div>
    </div>
  );
};

export default LoginPage;