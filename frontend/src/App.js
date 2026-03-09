import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import './App.css';

import Navbar from './components/Navbar';
import Home from './components/Home';
import LogFood from './components/LogFood';
import Today from './components/Today';
import Week from './components/Week';
import Reports from './components/Reports';
import Meals from './components/Meals';
import Settings from './components/Settings';

const API_URL = 'http://localhost:5000';

function App() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/profile`);
      setProfile(response.data);
    } catch (error) {
      console.error('Error fetching profile:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Router>
      <div className="App">
        {loading ? (
          <div className="loading-screen">
            <div className="spinner"></div>
            <p>Loading CalorieTracker...</p>
          </div>
        ) : (
          <>
            <Navbar profile={profile} />
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
          </>
        )}
      </div>
    </Router>
  );
}

export default App;
export { API_URL };