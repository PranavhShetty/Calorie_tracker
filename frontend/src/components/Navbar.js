import React from 'react';
import { NavLink } from 'react-router-dom';

function Navbar({ profile, darkMode, toggleDarkMode }) {
  const navLinkClass = ({ isActive }) => 'nav-link' + (isActive ? ' nav-link-active' : '');
  const mobileNavClass = ({ isActive }) => 'mobile-nav-item' + (isActive ? ' active' : '');

  return (
    <>
      <nav className="navbar">
        <div className="container navbar-inner">
          <div className="nav-brand">
            <h1>🥗 CalorieTracker</h1>
          </div>
          <div className="nav-links">
            <NavLink to="/" end className={navLinkClass}>Home</NavLink>
            <NavLink to="/log" className={navLinkClass}>Log Food</NavLink>
            <NavLink to="/today" className={navLinkClass}>Today</NavLink>
            <NavLink to="/week" className={navLinkClass}>This Week</NavLink>
            <NavLink to="/reports" className={navLinkClass}>Reports</NavLink>
            <NavLink to="/meals" className={navLinkClass}>Meals</NavLink>
            <NavLink to="/settings" className={navLinkClass}>Settings</NavLink>
          </div>
          <button className="btn-theme-toggle" onClick={toggleDarkMode} title="Toggle dark mode">
            {darkMode ? '☀️' : '🌙'}
          </button>
        </div>
      </nav>

      {/* Mobile bottom tab bar */}
      <nav className="mobile-bottom-nav">
        <NavLink to="/" end className={mobileNavClass}>
          <span className="mobile-nav-icon">🏠</span>
          <span className="mobile-nav-label">Home</span>
        </NavLink>
        <NavLink to="/log" className={mobileNavClass}>
          <span className="mobile-nav-icon">📝</span>
          <span className="mobile-nav-label">Log</span>
        </NavLink>
        <NavLink to="/today" className={mobileNavClass}>
          <span className="mobile-nav-icon">📊</span>
          <span className="mobile-nav-label">Today</span>
        </NavLink>
        <NavLink to="/meals" className={mobileNavClass}>
          <span className="mobile-nav-icon">🍽️</span>
          <span className="mobile-nav-label">Meals</span>
        </NavLink>
        <NavLink to="/settings" className={mobileNavClass}>
          <span className="mobile-nav-icon">⚙️</span>
          <span className="mobile-nav-label">Settings</span>
        </NavLink>
      </nav>
    </>
  );
}

export default Navbar;
