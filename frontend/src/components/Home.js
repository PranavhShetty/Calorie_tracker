import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../App';

function Home({ profile }) {
  const [summary, setSummary] = useState(null);
  const [foodEntries, setFoodEntries] = useState([]);
  const [weeklyDeficit, setWeeklyDeficit] = useState(0);
  const [monthlyDeficit, setMonthlyDeficit] = useState(0);
  const [unloggedDays, setUnloggedDays] = useState([]);
  const [weightHistory, setWeightHistory] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHomeData();
    fetchWeightHistory();
  }, []);

  const fetchHomeData = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/home-data`);
      setSummary(response.data.summary);
      setFoodEntries(response.data.food_entries);
      setWeeklyDeficit(response.data.weekly_deficit);
      setMonthlyDeficit(response.data.monthly_deficit);
      setUnloggedDays(response.data.unlogged_days);
    } catch (error) {
      console.error('Error fetching home data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchWeightHistory = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/weight-history?days=30`);
      setWeightHistory(response.data.weights);
    } catch (error) {
      console.error('Error fetching weight history:', error);
    }
  };

  if (loading) {
    return <div className="loading"><div className="spinner"></div></div>;
  }

  return (
    <div className="home-container">
      <div className="welcome-section">
        <h2>Welcome back, {profile.name}! 👋</h2>
        <p className="subtitle">Your BMR: {Math.round(profile.bmr)} kcal/day</p>
      </div>

      {/* Unlogged Days Alert */}
      {unloggedDays.length > 0 && (
        <div className="alert-banner alert-danger">
          <div className="alert-icon">⚠️</div>
          <div className="alert-content">
            <h3>Missing Logs This Week!</h3>
            <p>You haven't logged food for {unloggedDays.length} day(s) this week:</p>
            <div className="unlogged-days-list">
              {unloggedDays.map(day => (
                <Link key={day.date} to={`/log?date=${day.date}`} className="unlogged-day-chip">
                  {day.day_name} ({day.date})
                </Link>
              ))}
            </div>
          </div>
          <Link to="/week" className="alert-action-btn">
            View Week →
          </Link>
        </div>
      )}

      {/* Today's Summary */}
      {summary ? (
        <div className="summary-card">
          <h3>📊 Today's Summary</h3>
          
          <div className="stats-grid">
            <div className="stat-box">
              <div className="stat-label">Calories In</div>
              <div className="stat-value">{Math.round(summary.total_calories_in)}</div>
            </div>
            
            <div className="stat-box">
              <div className="stat-label">Total Burned</div>
              <div className="stat-value">{Math.round(summary.total_burned)}</div>
            </div>
            
            <div className={`stat-box ${summary.deficit > 0 ? 'stat-positive' : 'stat-negative'}`}>
              <div className="stat-label">{summary.deficit > 0 ? 'Deficit' : 'Surplus'}</div>
              <div className="stat-value">{Math.round(Math.abs(summary.deficit))}</div>
            </div>
          </div>

          <div className="macros-row">
            <div className="macro-item">
              <span className="macro-label">Protein</span>
              <span className="macro-value">{summary.total_protein.toFixed(1)}g</span>
            </div>
            <div className="macro-item">
              <span className="macro-label">Carbs</span>
              <span className="macro-value">{summary.total_carbs.toFixed(1)}g</span>
            </div>
            <div className="macro-item">
              <span className="macro-label">Fats</span>
              <span className="macro-value">{summary.total_fats.toFixed(1)}g</span>
            </div>
          </div>

          {foodEntries.length > 0 && (
            <div className="food-list">
              <h4>Food Logged:</h4>
              {foodEntries.map((entry, idx) => (
                <div key={idx} className="food-item">
                  <span className="food-name">
                    {entry.food_name}
                    {entry.is_saved_meal && <span className="badge">SAVED</span>}
                  </span>
                  <span className="food-cals">{Math.round(entry.calories)} kcal</span>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : (
        <div className="empty-state">
          <h3>No data logged for today</h3>
          <p>Start tracking your food and see your progress!</p>
          <Link to="/log" className="btn btn-primary">Log Food Now</Link>
        </div>
      )}

      {/* Weekly & Monthly Summary */}
      <div className="deficit-summary-grid">
        <div className="deficit-card">
          <div className="deficit-header">
            <h3>📅 This Week</h3>
          </div>
          <div className={`deficit-amount ${weeklyDeficit > 0 ? 'positive' : 'negative'}`}>
            {weeklyDeficit > 0 ? '+' : ''}{Math.round(weeklyDeficit)} kcal
          </div>
          {weeklyDeficit > 0 && (
            <div className="deficit-detail">
              ~{(weeklyDeficit / 7700).toFixed(2)} kg / ~{(weeklyDeficit / 3500).toFixed(2)} lbs lost 🔥
            </div>
          )}
        </div>

        <div className="deficit-card">
            {/* Weight Graph */}
      {weightHistory.length > 0 && (
        <div className="card">
          <h3>📈 Weight Progress (Last 30 Days)</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={weightHistory}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="date" 
                tick={{ fontSize: 12 }}
                tickFormatter={(date) => new Date(date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
              />
              <YAxis 
                domain={['dataMin - 2', 'dataMax + 2']}
                label={{ value: 'Weight (kg)', angle: -90, position: 'insideLeft' }}
              />
              <Tooltip 
                labelFormatter={(date) => new Date(date).toLocaleDateString()}
                formatter={(value) => [`${value.toFixed(1)} kg`, 'Weight']}
              />
              <Line 
                type="monotone" 
                dataKey="weight" 
                stroke="#10b981" 
                strokeWidth={2}
                dot={{ fill: '#10b981', r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
          
          {weightHistory.length >= 2 && (
            <div className="weight-change">
              <p>
                <strong>Progress:</strong> 
                {(() => {
                  const first = weightHistory[0].weight;
                  const last = weightHistory[weightHistory.length - 1].weight;
                  const change = first - last;
                  return change > 0 
                    ? <span className="positive"> ↓ {change.toFixed(1)} kg lost 🔥</span>
                    : <span className="negative"> ↑ {Math.abs(change).toFixed(1)} kg gained</span>;
                })()}
              </p>
            </div>
          )}
        </div>
      )}
          <div className="deficit-header">
            <h3>📆 This Month</h3>
          </div>
          <div className={`deficit-amount ${monthlyDeficit > 0 ? 'positive' : 'negative'}`}>
            {monthlyDeficit > 0 ? '+' : ''}{Math.round(monthlyDeficit)} kcal
          </div>
          {monthlyDeficit > 0 && (
            <div className="deficit-detail">
              ~{(monthlyDeficit / 7700).toFixed(2)} kg / ~{(monthlyDeficit / 3500).toFixed(2)} lbs lost 🔥
            </div>
          )}
        </div>
      </div>

      {/* Quick Actions */}
      <div className="quick-actions">
        <Link to="/log" className="action-card">
          <div className="action-icon">📝</div>
          <div className="action-title">Log Food</div>
        </Link>
        <Link to="/reports" className="action-card">
          <div className="action-icon">📊</div>
          <div className="action-title">View Reports</div>
        </Link>
        <Link to="/meals" className="action-card">
          <div className="action-icon">📚</div>
          <div className="action-title">Saved Meals</div>
        </Link>
      </div>
    </div>
  );
}

export default Home;