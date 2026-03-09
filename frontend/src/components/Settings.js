import React, { useState } from 'react';
import axios from 'axios';
import { API_URL } from '../App';
import { useNavigate } from 'react-router-dom';

function Settings({ profile, onUpdate }) {
  const [name, setName] = useState(profile?.name || '');
  const [bmr, setBmr] = useState(profile?.bmr || '');
  const [saving, setSaving] = useState(false);
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);

    try {
      await axios.post(`${API_URL}/api/save-profile`, {
        name: name,
        bmr: parseFloat(bmr)
      });
      
      alert('Profile updated successfully!');
      onUpdate(); // Refresh profile in App.js
      navigate('/');
    } catch (error) {
      console.error('Error saving profile:', error);
      alert('Error saving profile');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="setup-container">
      <div className="card">
        <h2>⚙️ Profile Settings</h2>
        <p>Update your profile information</p>

        <form onSubmit={handleSubmit} className="setup-form">
          <div className="form-group">
            <label htmlFor="name">Your Name</label>
            <input
              type="text"
              id="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
            />
          </div>

          <div className="form-group">
            <label htmlFor="bmr">Your BMR (Basal Metabolic Rate)</label>
            <input
              type="number"
              id="bmr"
              step="0.1"
              value={bmr}
              onChange={(e) => setBmr(e.target.value)}
              required
            />
            <small>
              Current BMR: {profile?.bmr ? Math.round(profile.bmr) : 0} kcal/day
              <br />
              Recalculate if needed:{' '}
              <a href="https://www.calculator.net/bmr-calculator.html" target="_blank" rel="noopener noreferrer">
                BMR Calculator
              </a>
            </small>
          </div>

          <div className="button-group">
            <button type="submit" className="btn btn-primary" disabled={saving}>
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
            <button type="button" onClick={() => navigate('/')} className="btn btn-secondary">
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default Settings;