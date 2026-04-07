import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import "./App.css";
import staff from "./assets/Staff.png";
import ehosp from "./assets/ehosp.png";
import { apiPost } from "./api";

const LoginPage = () => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const navigate = useNavigate();

  const handleLogin = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      const data = await apiPost("/login", { email, password, role });
      localStorage.setItem("userEmail", email);
      localStorage.setItem("userRole", data.role || role);
      navigate("/dashboard");
    } catch (error) {
      alert(`Login failed: ${error.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="login-page-container">
      <div className="login-card">
        <form className="login-form" onSubmit={handleLogin}>
          <div className="login-logo">
            <img
              src={ehosp}
              alt="logo"
              style={{
                width: "250px",
                height: "90px",
                objectFit: "contain",
                alignItems: "center",
                display: "block",
                marginLeft: "auto",
                marginRight: "auto",
              }}
            />
          </div>

          <select className="login-input" value={role} onChange={(event) => setRole(event.target.value)} required>
            <option value="">Select a role</option>
            <option value="Clinical Staff">Clinical Staff</option>
          </select>

          <input
            type="email"
            placeholder="Email address"
            className="login-input"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Password"
            className="login-input"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />

          <div className="remember-me">
            <input type="checkbox" id="rem" /> <label htmlFor="rem">Remember me</label>
          </div>

          <button type="submit" className="login-submit-btn" disabled={submitting}>
            {submitting ? "Logging in..." : "Login"}
          </button>
          <p className="signup-link">
            Don&apos;t have an account? <Link to="/signup" className="signup-link"><span>Sign up</span></Link>
          </p>
        </form>

        <div className="login-image">
          <img src={staff} alt="Staff" style={{ width: "450px", height: "auto" }} />
        </div>
      </div>
    </div>
  );
};

export default LoginPage;