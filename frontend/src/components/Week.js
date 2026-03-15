import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../App';
import { getCache, setCache } from '../apiCache';

function Week({ profile }) {
  const [weekDays, setWeekDays] = useState([]);
  const [totalDeficit, setTotalDeficit] = useState(0);
  const [daysLogged, setDaysLogged] = useState(0);
  const [weekRange, setWeekRange] = useState({ start: '', end: '' });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchWeekData();
  }, []);

  const fetchWeekData = async () => {
    const cached = getCache('week-data');
    if (cached) {
      setWeekDays(cached.week_days);
      setTotalDeficit(cached.total_deficit);
      setDaysLogged(cached.days_logged);
      setWeekRange({ start: cached.start_of_week, end: cached.end_of_week });
      setLoading(false);
      return;
    }
    try {
      const response = await axios.get(`${API_URL}/api/week-data`);
      setCache('week-data', response.data);
      setWeekDays(response.data.week_days);
      setTotalDeficit(response.data.total_deficit);
      setDaysLogged(response.data.days_logged);
      setWeekRange({
        start: response.data.start_of_week,
        end: response.data.end_of_week
      });
    } catch (error) {
      console.error('Error fetching week data:', error);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading"><div className="spinner"></div></div>;
  }

  return (
    <div className="week-container">
      <div className="week-header">
        <h2>📅 This Week Overview</h2>
        <p className="week-range">{weekRange.start} to {weekRange.end}</p>
      </div>

      <div className="week-summary-card">
        <div className="week-stat">
          <span className="week-stat-label">Days Logged</span>
          <span className="week-stat-value">{daysLogged}/7</span>
        </div>
        <div className="week-stat">
          <span className="week-stat-label">Total Deficit</span>
          <span className={`week-stat-value ${totalDeficit > 0 ? 'positive' : 'negative'}`}>
            {totalDeficit > 0 ? '+' : ''}{Math.round(totalDeficit)} kcal
          </span>
        </div>
        {totalDeficit > 0 && (
          <div className="week-stat">
            <span className="week-stat-label">Estimated Loss</span>
            <span className="week-stat-value positive">
              ~{(totalDeficit / 7700).toFixed(2)} kg
            </span>
          </div>
        )}
      </div>

      <div className="week-grid">
        {weekDays.map((day) => (
          <div
            key={day.date}
            className={`day-card ${day.is_today ? 'today' : ''} ${!day.logged ? 'not-logged' : ''} ${day.is_future ? 'future' : ''}`}
          >
            <div className="day-header">
              <div className="day-info">
                <h3>{day.day_short}</h3>
                <p className="day-date">{day.date}</p>
              </div>

              {day.is_today ? (
                <span className="day-badge today-badge">Today</span>
              ) : day.is_future ? (
                <span className="day-badge future-badge">Future</span>
              ) : !day.logged ? (
                <span className="day-badge missed-badge">Not Logged</span>
              ) : (
                <span className="day-badge logged-badge">✓</span>
              )}
            </div>

            {day.logged && day.summary ? (
              <>
                <div className="day-stats">
                  <div className="day-stat-row">
                    <span className="stat-label">In:</span>
                    <span className="stat-value">{Math.round(day.summary.total_calories_in)}</span>
                  </div>
                  <div className="day-stat-row">
                    <span className="stat-label">Out:</span>
                    <span className="stat-value">{Math.round(day.summary.total_burned)}</span>
                  </div>
                  <div className="day-stat-row deficit-row">
                    <span className="stat-label">Net:</span>
                    <span className={`stat-value ${day.summary.deficit > 0 ? 'positive' : 'negative'}`}>
                      {day.summary.deficit > 0 ? '+' : ''}{Math.round(day.summary.deficit)}
                    </span>
                  </div>
                </div>

                <div className="day-actions">
                  <Link to={`/log?date=${day.date}`} className="btn-edit">
                    ✏️ Edit
                  </Link>
                </div>
              </>
            ) : !day.is_future ? (
              <>
                <div className="day-empty">
                  <p>📭</p>
                  <p>No data</p>
                </div>

                <div className="day-actions">
                  <Link to={`/log?date=${day.date}`} className="btn-log-day">
                    + Log
                  </Link>
                </div>
              </>
            ) : (
              <div className="day-empty">
                <p>⏳</p>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default Week;