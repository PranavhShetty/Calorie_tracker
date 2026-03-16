import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { API_URL } from '../App';
import { getCache, setCache } from '../apiCache';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts';

// ── Ring Gauge ────────────────────────────────────────────────────────────────
function RingGauge({ consumed, target, label = 'Daily Net Calories' }) {
  const r = 80, cx = 110, cy = 115;
  const C = 2 * Math.PI * r;
  const trackArc = C * 0.75;
  const pct = target > 0 ? Math.min(consumed / target, 1) : 0;
  const fillArc = pct * trackArc;
  const remaining = Math.round(target - consumed);
  const isOver = remaining < 0;

  return (
    <div className="ring-gauge-container">
      <svg width="220" height="225" viewBox="0 0 220 225">
        {/* Gray track */}
        <circle
          cx={cx} cy={cy} r={r}
          fill="none" stroke="#2a3346" strokeWidth={13} strokeLinecap="round"
          strokeDasharray={`${trackArc} ${C}`}
          transform={`rotate(135 ${cx} ${cy})`}
        />
        {/* Fill arc */}
        <circle
          cx={cx} cy={cy} r={r}
          fill="none"
          stroke={isOver ? '#ef4444' : '#3b82f6'}
          strokeWidth={13} strokeLinecap="round"
          strokeDasharray={`${fillArc} ${C}`}
          transform={`rotate(135 ${cx} ${cy})`}
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
        {/* Thin inner ring */}
        <circle cx={cx} cy={cy} r={r - 18} fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth={1} />

        {/* Target label — top-right corner */}
        <text x={206} y={44} textAnchor="end" fill="#475569" fontSize="11">
          {Math.round(target).toLocaleString()} kcal
        </text>

        {/* Center: label */}
        <text x={cx} y={cy - 22} textAnchor="middle" fill="#64748b" fontSize="12">{label}</text>
        {/* Center: big number */}
        <text x={cx} y={cy + 22} textAnchor="middle" fill="white" fontSize="42" fontWeight="700">
          {Math.round(consumed).toLocaleString()}
        </text>
        {/* Center: "consumed" */}
        <text x={cx} y={cy + 42} textAnchor="middle" fill="#94a3b8" fontSize="12">consumed</text>

        {/* Bottom: "Consumed" at gap */}
        <text x={cx} y={cy + r + 18} textAnchor="middle" fill="#475569" fontSize="11">Consumed</text>
      </svg>

      {/* Remaining / Over badge */}
      <div className="ring-badge">
        <span className={isOver ? 'ring-badge-over' : 'ring-badge-ok'}>
          <span className="ring-badge-arrow">{isOver ? '↙' : '↗'}</span>
          {isOver ? '' : '+'}{Math.abs(remaining).toLocaleString()} kcal
        </span>
        <span className="ring-badge-sub">{isOver ? 'Over Budget' : 'Remaining'}</span>
      </div>
    </div>
  );
}

// ── Monthly Calendar Heatmap ──────────────────────────────────────────────────
function CalendarHeatmap({ monthlySummaries }) {
  const now = new Date();
  const year = now.getFullYear();
  const month = now.getMonth();
  const daysInMonth = new Date(year, month + 1, 0).getDate();
  const firstDow = new Date(year, month, 1).getDay(); // 0 = Sun

  const deficitMap = {};
  monthlySummaries.forEach(d => { deficitMap[d.date] = d.deficit; });

  const cells = [];
  for (let i = 0; i < firstDow; i++) cells.push(null);
  for (let d = 1; d <= daysInMonth; d++) {
    const ds = `${year}-${String(month + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`;
    cells.push({ d, ds, deficit: deficitMap[ds], isToday: d === now.getDate(), isFuture: d > now.getDate() });
  }

  return (
    <div className="cal-heatmap">
      <div className="cal-heatmap-header">
        <span className="cal-heatmap-title">Status</span>
        <div className="cal-legend">
          <span className="cal-legend-dot" style={{ background: '#10b981' }} /> Deficit
          <span className="cal-legend-dot" style={{ background: '#f59e0b' }} /> Surplus
        </div>
      </div>
      <div className="cal-grid">
        {['Su','Mo','Tu','We','Th','Fr','Sa'].map(l => (
          <div key={l} className="cal-dow">{l}</div>
        ))}
        {cells.map((cell, i) => {
          if (!cell) return <div key={`e${i}`} className="cal-cell cal-cell-empty" />;
          let bg = '#1e2a3a';
          if (!cell.isFuture && cell.deficit !== undefined) {
            bg = cell.deficit > 0 ? '#10b981' : '#f59e0b';
          }
          return (
            <div
              key={cell.ds}
              className={`cal-cell${cell.isToday ? ' cal-cell-today' : ''}`}
              style={{ background: bg }}
              title={`${cell.ds}: ${cell.deficit !== undefined ? Math.round(cell.deficit) + ' kcal deficit' : 'No data'}`}
            >
              <span className="cal-cell-num">{cell.d}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// ── Main Dashboard ────────────────────────────────────────────────────────────
function Home({ profile }) {
  const [tab, setTab] = useState('daily');
  const [summary, setSummary] = useState(null);
  const [unloggedDays, setUnloggedDays] = useState([]);
  const [weeklySummaries, setWeeklySummaries] = useState([]);
  const [monthlySummaries, setMonthlySummaries] = useState([]);
  const [weeklyTotal, setWeeklyTotal] = useState(0);
  const [monthlyTotal, setMonthlyTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const cachedHome    = getCache('home-data');
    const cachedReports = getCache('reports-data');
    if (cachedHome && cachedReports) {
      setSummary(cachedHome.summary);
      setUnloggedDays(cachedHome.unlogged_days || []);
      setWeeklySummaries(cachedReports.weekly_summaries || []);
      setMonthlySummaries(cachedReports.monthly_summaries || []);
      setWeeklyTotal(cachedReports.weekly_total || 0);
      setMonthlyTotal(cachedReports.monthly_total || 0);
      setLoading(false);
      return;
    }
    Promise.all([
      cachedHome    ? Promise.resolve({ data: cachedHome })    : axios.get(`${API_URL}/api/home-data`),
      cachedReports ? Promise.resolve({ data: cachedReports }) : axios.get(`${API_URL}/api/reports-data`),
    ]).then(([homeRes, reportsRes]) => {
      if (!cachedHome)    setCache('home-data', homeRes.data);
      if (!cachedReports) setCache('reports-data', reportsRes.data);
      setSummary(homeRes.data.summary);
      setUnloggedDays(homeRes.data.unlogged_days || []);
      setWeeklySummaries(reportsRes.data.weekly_summaries || []);
      setMonthlySummaries(reportsRes.data.monthly_summaries || []);
      setWeeklyTotal(reportsRes.data.weekly_total || 0);
      setMonthlyTotal(reportsRes.data.monthly_total || 0);
    }).catch(e => console.error('Dashboard fetch error:', e))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="loading"><div className="spinner" /></div>;

  const bmr = Math.round(profile.bmr);

  // ── Daily
  const dailyConsumed = summary ? Math.round(summary.total_calories_in) : 0;
  const caloriesBurned = summary ? Math.round(summary.calories_burned) : 0;
  const totalBurned = summary ? Math.round(summary.total_burned) : bmr;
  const dailyDeficit = dailyConsumed - totalBurned; // negative = under budget = good

  // ── Weekly
  const wLogged = weeklySummaries.length;
  const wAvgConsumed = wLogged > 0
    ? Math.round(weeklySummaries.reduce((s, d) => s + d.total_calories_in, 0) / wLogged) : 0;
  const wTargetMet = weeklySummaries.filter(d => d.deficit > 0).length;
  const wNetTotal = -Math.round(weeklyTotal); // flip: positive weeklyTotal = caloric deficit; show as negative to match image convention
  const wChartData = weeklySummaries.map(d => ({
    day: new Date(d.date + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'short' }),
    calories: Math.round(d.total_calories_in),
  }));

  // ── Monthly
  const mLogged = monthlySummaries.length;
  const mAvgConsumed = mLogged > 0
    ? Math.round(monthlySummaries.reduce((s, d) => s + d.total_calories_in, 0) / mLogged) : 0;
  const mDaysInDeficit = monthlySummaries.filter(d => d.deficit > 0).length;

  return (
    <div className="dashboard-container">

      {/* Header */}
      <div className="dash-header">
        <h2 className="dash-title">Dashboard</h2>
        <Link to="/settings" className="dash-settings-btn" title="Settings">⚙</Link>
      </div>

      {/* Tab bar */}
      <div className="dash-tabs">
        {['daily', 'weekly', 'monthly'].map(t => (
          <button
            key={t}
            className={`dash-tab${tab === t ? ' dash-tab-active' : ''}`}
            onClick={() => setTab(t)}
          >
            {t.charAt(0).toUpperCase() + t.slice(1)}
          </button>
        ))}
      </div>

      {/* ── DAILY ─────────────────────────────────────────────────────── */}
      {tab === 'daily' && (
        <div className="dash-content">
          <div className="dash-ring-card">
            {summary ? (
              <RingGauge consumed={dailyConsumed} target={totalBurned} />
            ) : (
              <div className="dash-no-data">
                <p>Nothing logged today</p>
                <Link to="/log" className="btn btn-primary" style={{ marginTop: 14 }}>Log Food</Link>
              </div>
            )}
          </div>

          <h3 className="dash-section-title">Quick Summary</h3>
          <div className="dash-stat-row">
            <div className="dash-stat-card">
              <div className="dash-stat-label">Consumed</div>
              <div className="dash-stat-value">{dailyConsumed.toLocaleString()}</div>
            </div>
            <div className="dash-stat-card">
              <div className="dash-stat-label">Burned</div>
              <div className="dash-stat-value">{totalBurned.toLocaleString()}</div>
              {caloriesBurned > 0 && (
                <div className="dash-stat-sub">BMR {bmr} + {caloriesBurned} workout</div>
              )}
            </div>
            <div className={`dash-stat-card ${dailyDeficit <= 0 ? 'dash-accent-green' : 'dash-accent-red'}`}>
              <div className="dash-stat-label">Deficit</div>
              <div className="dash-stat-value">
                {dailyDeficit > 0 ? '+' : ''}{dailyDeficit.toLocaleString()}
              </div>
            </div>
          </div>

          {summary && (
            <>
              <h3 className="dash-section-title" style={{ marginTop: 20 }}>Macros</h3>
              <div className="dash-stat-row">
                <div className="dash-stat-card">
                  <div className="dash-stat-label">Protein</div>
                  <div className="dash-stat-value">{summary.total_protein.toFixed(1)}g</div>
                </div>
                <div className="dash-stat-card">
                  <div className="dash-stat-label">Carbs</div>
                  <div className="dash-stat-value">{summary.total_carbs.toFixed(1)}g</div>
                </div>
                <div className="dash-stat-card">
                  <div className="dash-stat-label">Fats</div>
                  <div className="dash-stat-value">{summary.total_fats.toFixed(1)}g</div>
                </div>
              </div>
            </>
          )}

          {unloggedDays.length > 0 && (
            <div className="dash-alert">
              <span>⚠️ {unloggedDays.length} day(s) missing this week</span>
              <Link to="/week" className="dash-alert-link">View Week →</Link>
            </div>
          )}

          <div className="dash-actions">
            <Link to="/log" className="btn btn-primary">+ Log Food</Link>
          </div>
        </div>
      )}

      {/* ── WEEKLY ────────────────────────────────────────────────────── */}
      {tab === 'weekly' && (
        <div className="dash-content">
          <div className="dash-ring-card">
            <RingGauge consumed={wAvgConsumed} target={bmr} label="Avg Daily Calories" />
          </div>

          {weeklySummaries.length > 0 ? (
            <>
              <h3 className="dash-section-title">Weekly Trend</h3>
              <div className="dash-chart-card">
                <ResponsiveContainer width="100%" height={190}>
                  <LineChart data={wChartData} margin={{ top: 8, right: 20, bottom: 0, left: -20 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e2a3a" />
                    <XAxis dataKey="day" tick={{ fontSize: 12, fill: '#64748b' }} axisLine={false} tickLine={false} />
                    <YAxis tick={{ fontSize: 11, fill: '#64748b' }} axisLine={false} tickLine={false} />
                    <Tooltip
                      contentStyle={{ background: '#1e293b', border: '1px solid #334155', borderRadius: 8, color: '#f1f5f9', fontSize: 12 }}
                      formatter={v => [`${v} kcal`, 'Calories']}
                    />
                    <ReferenceLine y={bmr} stroke="#10b981" strokeDasharray="6 3"
                      label={{ value: 'Target', fill: '#10b981', fontSize: 11, position: 'right' }} />
                    <Line type="monotone" dataKey="calories" stroke="#3b82f6" strokeWidth={2}
                      dot={{ fill: '#3b82f6', r: 4, strokeWidth: 0 }}
                      activeDot={{ r: 6, fill: '#3b82f6' }} />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="dash-stat-row" style={{ marginTop: 16 }}>
                <div className="dash-stat-card">
                  <div className="dash-stat-label">Avg Daily Net</div>
                  <div className="dash-stat-value">{wAvgConsumed.toLocaleString()}</div>
                </div>
                <div className={`dash-stat-card ${weeklyTotal > 0 ? 'dash-accent-green' : 'dash-accent-red'}`}>
                  <div className="dash-stat-label">Total Net (Deficit)</div>
                  <div className="dash-stat-value">
                    {wNetTotal > 0 ? '+' : ''}{wNetTotal.toLocaleString()}
                  </div>
                </div>
                <div className={`dash-stat-card ${wTargetMet > 0 ? 'dash-accent-green' : ''}`}>
                  <div className="dash-stat-label">Target Met</div>
                  <div className="dash-stat-value">{wTargetMet}/{wLogged} Days</div>
                </div>
              </div>
            </>
          ) : (
            <p className="dash-empty-msg">No data logged this week yet.</p>
          )}
        </div>
      )}

      {/* ── MONTHLY ───────────────────────────────────────────────────── */}
      {tab === 'monthly' && (
        <div className="dash-content">
          <div className="dash-ring-card">
            <RingGauge consumed={mAvgConsumed} target={bmr} label="Avg Daily Calories" />
          </div>

          <CalendarHeatmap monthlySummaries={monthlySummaries} />

          <div className="dash-stat-row" style={{ marginTop: 16 }}>
            <div className="dash-stat-card">
              <div className="dash-stat-label">Days in Deficit</div>
              <div className="dash-stat-value">{mDaysInDeficit}</div>
            </div>
            <div className="dash-stat-card">
              <div className="dash-stat-label">Avg Daily Net</div>
              <div className="dash-stat-value">{mAvgConsumed.toLocaleString()}</div>
            </div>
            <div className={`dash-stat-card ${monthlyTotal > 0 ? 'dash-accent-green' : ''}`}>
              <div className="dash-stat-label">Days Logged</div>
              <div className="dash-stat-value">{mLogged}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default Home;
