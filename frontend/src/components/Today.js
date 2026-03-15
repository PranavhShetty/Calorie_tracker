import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../App';

function Today({ profile }) {
  const [summary, setSummary]           = useState(null);
  const [foodEntries, setFoodEntries]   = useState([]);
  const [loading, setLoading]           = useState(true);
  const [deletingId, setDeletingId]     = useState(null); // which entry is being deleted
  const today = new Date().toISOString().split('T')[0];

  useEffect(() => {
    fetchTodayData();
  }, []);

  const fetchTodayData = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/today-data`);
      setSummary(response.data.summary);
      setFoodEntries(response.data.food_entries);
    } catch (error) {
      console.error('Error fetching today data:', error);
    } finally {
      setLoading(false);
    }
  };

  // Delete a single food entry and update the UI immediately
  const deleteEntry = async (entry) => {
    if (!window.confirm(`Remove "${entry.food_name}" from today's log?`)) return;

    setDeletingId(entry.id);
    try {
      const res = await axios.post(`${API_URL}/api/delete-food-entry`, {
        entry_id: entry.id,
        date: today,
      });
      // Update both the entry list and the summary with what the server returned
      setFoodEntries(res.data.food_entries);
      setSummary(res.data.summary);
    } catch (e) {
      console.error('Failed to delete entry:', e);
      alert('Failed to remove item. Please try again.');
    } finally {
      setDeletingId(null);
    }
  };

  if (loading) {
    return <div className="loading"><div className="spinner"></div></div>;
  }

  return (
    <div className="status-container">
      <h2>📋 Today's Status — {today}</h2>

      {summary ? (
        <>
          <div className="summary-card-large">
            <div className="summary-header">
              <h3>Daily Summary</h3>
            </div>

            <div className="stats-grid-large">
              <div className="stat-box-large">
                <div className="stat-icon">🍽️</div>
                <div className="stat-label">Calories In</div>
                <div className="stat-value">{Math.round(summary.total_calories_in)}</div>
                <div className="stat-detail">
                  P: {summary.total_protein.toFixed(1)}g |
                  C: {summary.total_carbs.toFixed(1)}g |
                  F: {summary.total_fats.toFixed(1)}g
                </div>
              </div>

              <div className="stat-box-large">
                <div className="stat-icon">🔥</div>
                <div className="stat-label">Total Burned</div>
                <div className="stat-value">{Math.round(summary.total_burned)}</div>
                <div className="stat-detail">
                  BMR: {Math.round(summary.bmr)} +
                  Workout: {Math.round(summary.calories_burned)}
                </div>
              </div>

              <div className={`stat-box-large ${summary.deficit > 0 ? 'stat-positive' : 'stat-negative'}`}>
                <div className="stat-icon">{summary.deficit > 0 ? '🎯' : '⚠️'}</div>
                <div className="stat-label">{summary.deficit > 0 ? 'Deficit' : 'Surplus'}</div>
                <div className="stat-value">{Math.round(Math.abs(summary.deficit))}</div>
                <div className="stat-detail">
                  {summary.deficit > 0 ? 'Great job staying in deficit!' : 'Over your target today'}
                </div>
              </div>
            </div>
          </div>

          {foodEntries.length > 0 && (
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                <h3>🍽️ Food Logged Today ({foodEntries.length} items)</h3>
                <Link to="/log" className="btn btn-secondary" style={{ fontSize: '13px', padding: '6px 12px' }}>
                  + Add More
                </Link>
              </div>
              <div className="food-entries-list">
                {foodEntries.map((entry) => (
                  <div key={entry.id} className="food-entry-card">
                    <div className="food-entry-header">
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <strong>{entry.food_name}</strong>
                        {entry.is_saved_meal && <span className="badge badge-saved">SAVED MEAL</span>}
                      </div>
                      {/* Delete button — shows a spinner while deleting that specific item */}
                      <button
                        className="remove-item-btn"
                        onClick={() => deleteEntry(entry)}
                        disabled={deletingId === entry.id}
                        title="Remove this item"
                      >
                        {deletingId === entry.id ? '…' : '✕'}
                      </button>
                    </div>
                    <div className="food-entry-macros">
                      <span className="macro-pill">{Math.round(entry.calories)} kcal</span>
                      <span className="macro-pill">P: {entry.protein.toFixed(1)}g</span>
                      <span className="macro-pill">C: {entry.carbs.toFixed(1)}g</span>
                      <span className="macro-pill">F: {entry.fats.toFixed(1)}g</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Show "Add food" card if all items were deleted */}
          {foodEntries.length === 0 && (
            <div className="card" style={{ textAlign: 'center', padding: '24px' }}>
              <p style={{ color: '#64748b', marginBottom: '12px' }}>All items removed.</p>
              <Link to="/log" className="btn btn-primary">+ Log Food</Link>
            </div>
          )}

          {summary.workout_description && (
            <div className="card workout-card">
              <h3>💪 Workout</h3>
              <p className="workout-description">{summary.workout_description}</p>
              <p className="workout-calories">
                Calories Burned: <strong>{Math.round(summary.calories_burned)} kcal</strong>
              </p>
            </div>
          )}

          {summary.notes && (
            <div className="card notes-card">
              <h3>📝 Notes</h3>
              <p>{summary.notes}</p>
            </div>
          )}
        </>
      ) : (
        <div className="empty-state">
          <h3>No data logged for today</h3>
          <p>Start tracking to see your daily summary!</p>
          <Link to="/log" className="btn btn-primary">Log Food Now</Link>
        </div>
      )}
    </div>
  );
}

export default Today;
