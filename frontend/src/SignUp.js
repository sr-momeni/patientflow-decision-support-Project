import React, { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import "./App.css";
import "./SignUp.css";
import staff from "./assets/Staff.png";
import ehosp from "./assets/ehosp.png";
import { apiPost } from "./api";

const SignUp = () => {
  const navigate = useNavigate();
  const [formData, setFormData] = useState({
    role: "",
    email: "",
    password: "",
    confirm_password: "",
  });
  const [submitting, setSubmitting] = useState(false);

  const handleChange = (event) => {
    setFormData((current) => ({ ...current, [event.target.name]: event.target.value }));
  };

  const handleSignUp = async (event) => {
    event.preventDefault();

    if (formData.password !== formData.confirm_password) {
      alert("Passwords do not match.");
      return;
    }

    setSubmitting(true);
    try {
      await apiPost("/signup", {
        role: formData.role,
        email: formData.email,
        password: formData.password,
      });
      alert("Clinical Staff account created.");
      navigate("/login");
    } catch (error) {
      alert(`Registration failed: ${error.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="auth-wrapper">
      <div className="auth-card">
        <div className="form-container">
          <div className="logo-area">
            <img
              src={ehosp}
              alt="logo"
              style={{
                width: "250px",
                height: "70px",
                objectFit: "contain",
                alignItems: "center",
                display: "block",
                marginLeft: "auto",
                marginRight: "auto",
              }}
            />
          </div>

          <h2 className="title">Create Your Account</h2>

          <form onSubmit={handleSignUp} className="main-form">
            <select name="role" className="input-field" onChange={handleChange} required value={formData.role}>
              <option value="" disabled>
                Select Staff Role
              </option>
              <option value="Clinical Staff">Clinical Staff</option>
            </select>

            <input type="email" name="email" placeholder="Email address" className="input-field" onChange={handleChange} required />
            <input type="password" name="password" placeholder="Password" className="input-field" onChange={handleChange} required />
            <input
              type="password"
              name="confirm_password"
              placeholder="Confirm Password"
              className="input-field"
              onChange={handleChange}
              required
            />

            <button type="submit" className="submit-button" disabled={submitting}>
              {submitting ? "Creating account..." : "Sign Up"}
            </button>
          </form>

          <p className="redirect-text">
            Already have an account? <Link to="/login" className="login-link">Login</Link>
          </p>
        </div>

        <div className="image-container">
          <img src={staff} alt="Clinical Staff" className="side-image" />
        </div>
      </div>
    </div>
  );
};

export default SignUp;