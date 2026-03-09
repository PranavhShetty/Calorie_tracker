import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { GoogleOAuthProvider } from '@react-oauth/google';
import axios from 'axios';
import './App.css';

import Navbar from './components/Navbar';
import Login from './components/Login';
import Home from './components/Home';
import LogFood from './components/LogFood';
import Today from './components/Today';
import Week from './components/Week';
import Reports from './components/Reports';
import Meals from './components/Meals';
import Settings from './components/Settings';

const API_URL = 'http://localhost:5000';

// Send cookies with every request (required for Flask sessions)
axios.defaults.withCredentials = true;

const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID || '';

function App() {
  const [profile, setProfile]   = useState(null);
  const [user, setUser]         = useState(null);   // Google user info
  const [loading, setLoading]   = useState(true);
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('theme');
    if (saved) return saved === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light');
    localStorage.setItem('theme', darkMode ? 'dark' : 'light');
  }, [darkMode]);

  // On mount: check if already logged in (session cookie exists)
  useEffect(() => {
    checkAuth();
  }, []);

  const checkAuth = async () => {
    try {
      const res = await axios.get(`${API_URL}/api/auth/me`);
      setUser(res.data.user);
      await fetchProfile();
    } catch {
      // 401 → not logged in, show login screen
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  const handleLoginSuccess = async (googleUser) => {
    setUser(googleUser);
    await fetchProfile();
  };

  const handleLogout = async () => {
    await axios.post(`${API_URL}/api/auth/logout`);
    setUser(null);
    setProfile(null);
  };

  const fetchProfile = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/profile`);
      setProfile(response.data);
    } catch {
      setProfile(null);
    }
  };

  if (loading) {
    return (
      <div className="loading-screen">
        <div className="spinner"></div>
        <p>Loading CalorieTracker...</p>
      </div>
    );
  }

  if (!user) {
    return (
      <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
        <Login onLoginSuccess={handleLoginSuccess} apiUrl={API_URL} darkMode={darkMode} />
      </GoogleOAuthProvider>
    );
  }

  return (
    <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
      <Router>
        <div className="App">
          <Navbar
            profile={profile}
            user={user}
            darkMode={darkMode}
            toggleDarkMode={() => setDarkMode(d => !d)}
            onLogout={handleLogout}
          />
          <main className="container">
            <Routes>
              <Route path="/" element={profile ? <Home profile={profile} /> : <Navigate to="/settings" />} />
              <Route path="/log" element={profile ? <LogFood profile={profile} /> : <Navigate to="/settings" />} />
              <Route path="/today" element={profile ? <Today profile={profile} /> : <Navigate to="/settings" />} />
              <Route path="/week" element={profile ? <Week profile={profile} /> : <Navigate to="/settings" />} />
              <Route path="/reports" element={profile ? <Reports profile={profile} /> : <Navigate to="/settings" />} />
              <Route path="/meals" element={profile ? <Meals profile={profile} /> : <Navigate to="/settings" />} />
              <Route path="/settings" element={<Settings profile={profile} onUpdate={fetchProfile} />} />
            </Routes>
          </main>
          <footer>
            <div className="container">
              <p>CalorieTracker - LLM-Powered Macro Tracking for Indian Foods</p>
            </div>
          </footer>
        </div>
      </Router>
    </GoogleOAuthProvider>
  );
}

export default App;
export { API_URL };
