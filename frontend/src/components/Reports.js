import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { API_URL } from '../App';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer
} from 'recharts';

function Reports({ profile }) {
  const [weeklySummaries, setWeeklySummaries]   = useState([]);
  const [monthlySummaries, setMonthlySummaries] = useState([]);
  const [weeklyTotal, setWeeklyTotal]           = useState(0);
  const [monthlyTotal, setMonthlyTotal]         = useState(0);
  const [weightData, setWeightData]             = useState([]);
  const [weightDays, setWeightDays]             = useState(30);
  const [loading, setLoading]                   = useState(true);

  useEffect(() => {
    fetchReportsData();
  }, []);

  useEffect(() => {
    fetchWeightHistory(weightDays);
  }, [weightDays]);

  const fetchReportsData = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/reports-data`);
      setWeeklySummaries(response.data.weekly_summaries);
      setMonthlySummaries(response.data.monthly_summaries);
      setWeeklyTotal(response.data.weekly_total);
      setMonthlyTotal(response.data.monthly_total);
    } catch (error) {
      console.error('Error fetching reports data:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchWeightHistory = async (days) => {
    try {
      const res = await axios.get(`${API_URL}/api/weight-history?days=${days}`);
      setWeightData(
        (res.data.weights || []).map(w => ({
          date: w.date.slice(5),   // "MM-DD"
          weight: w.weight,
        }))
      );
    } catch (error) {
      console.error('Error fetching weight history:', error);
    }
  };

  if (loading) {
    return <div className="loading"><div className="spinner"></div></div>;
  }

  return (
    <div className="reports-container">
      <h2>📊 Deficit Reports</h2>

      {/* Weight Graph */}
      <div className="card">
        <div className="report-section-header">
          <h3>⚖️ Weight Over Time</h3>
          <div className="toggle-group">
            {[30, 90].map(d => (
              <button
                key={d}
                onClick={() => setWeightDays(d)}
                className={`toggle-btn ${weightDays === d ? 'active' : ''}`}
              >
                {d}d
              </button>
            ))}
          </div>
        </div>

        {weightData.length >= 2 ? (
          <>
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={weightData} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis
                  domain={['auto', 'auto']}
                  tick={{ fontSize: 11 }}
                  tickFormatter={v => `${v}kg`}
                />
                <Tooltip formatter={(v) => [`${v} kg`, 'Weight']} />
                <Line
                  type="monotone"
                  dataKey="weight"
                  stroke="var(--primary)"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  activeDot={{ r: 5 }}
                />
              </LineChart>
            </ResponsiveContainer>
            <div className="weight-stats">
              <span>Start: <strong>{weightData[0].weight} kg</strong></span>
              <span>
                Change:{' '}
                <strong className={weightData[weightData.length-1].weight - weightData[0].weight <= 0 ? 'positive-text' : 'negative-text'}>
                  {(weightData[weightData.length-1].weight - weightData[0].weight > 0 ? '+' : '')}
                  {(weightData[weightData.length-1].weight - weightData[0].weight).toFixed(1)} kg
                </strong>
              </span>
              <span>Latest: <strong>{weightData[weightData.length-1].weight} kg</strong></span>
            </div>
          </>
        ) : (
          <p className="empty-message">
            {weightData.length === 1 ? 'Log weight on at least 2 days to see the graph.' : 'No weight data yet. Log your weight when saving a food entry.'}
          </p>
        )}
      </div>

      {/* Weekly Report */}
      <div className="card">
        <h3>📅 This Week</h3>

        {weeklySummaries.length > 0 ? (
          <>
            <div className="report-table">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Calories In</th>
                    <th>Burned</th>
                    <th>Deficit</th>
                  </tr>
                </thead>
                <tbody>
                  {weeklySummaries.map((day) => (
                    <tr key={day.date}>
                      <td>{day.date}</td>
                      <td>{Math.round(day.total_calories_in)}</td>
                      <td>{Math.round(day.total_burned)}</td>
                      <td className={day.deficit > 0 ? 'positive' : 'negative'}>
                        {day.deficit > 0 ? '+' : ''}{Math.round(day.deficit)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="total-row">
                    <td colSpan="3"><strong>Total Deficit:</strong></td>
                    <td className={weeklyTotal > 0 ? 'positive' : 'negative'}>
                      <strong>{weeklyTotal > 0 ? '+' : ''}{Math.round(weeklyTotal)} kcal</strong>
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>

            <div className="report-summary">
              <p><strong>Days logged:</strong> {weeklySummaries.length}</p>
              {weeklyTotal > 0 ? (
                <p className="positive-text">
                  <strong>Estimated fat loss:</strong>{' '}
                  ~{(weeklyTotal / 7700).toFixed(2)} kg / ~{(weeklyTotal / 3500).toFixed(2)} lbs 🔥
                </p>
              ) : (
                <p className="negative-text">
                  <strong>Caloric surplus:</strong> {Math.abs(weeklyTotal)} kcal
                </p>
              )}
            </div>
          </>
        ) : (
          <p className="empty-message">No data for this week yet.</p>
        )}
      </div>

      {/* Monthly Report */}
      <div className="card">
        <h3>📆 This Month</h3>

        {monthlySummaries.length > 0 ? (
          <>
            <div className="report-table">
              <table>
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Calories In</th>
                    <th>Burned</th>
                    <th>Deficit</th>
                  </tr>
                </thead>
                <tbody>
                  {monthlySummaries.map((day) => (
                    <tr key={day.date}>
                      <td>{day.date}</td>
                      <td>{Math.round(day.total_calories_in)}</td>
                      <td>{Math.round(day.total_burned)}</td>
                      <td className={day.deficit > 0 ? 'positive' : 'negative'}>
                        {day.deficit > 0 ? '+' : ''}{Math.round(day.deficit)}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot>
                  <tr className="total-row">
                    <td colSpan="3"><strong>Total Deficit:</strong></td>
                    <td className={monthlyTotal > 0 ? 'positive' : 'negative'}>
                      <strong>{monthlyTotal > 0 ? '+' : ''}{Math.round(monthlyTotal)} kcal</strong>
                    </td>
                  </tr>
                </tfoot>
              </table>
            </div>

            <div className="report-summary">
              <p><strong>Days logged:</strong> {monthlySummaries.length}</p>
              {monthlyTotal > 0 ? (
                <p className="positive-text">
                  <strong>Estimated fat loss:</strong>{' '}
                  ~{(monthlyTotal / 7700).toFixed(2)} kg / ~{(monthlyTotal / 3500).toFixed(2)} lbs 🔥
                </p>
              ) : (
                <p className="negative-text">
                  <strong>Caloric surplus:</strong> {Math.abs(monthlyTotal)} kcal
                </p>
              )}
            </div>
          </>
        ) : (
          <p className="empty-message">No data for this month yet.</p>
        )}
      </div>
    </div>
  );
}

export default Reports;