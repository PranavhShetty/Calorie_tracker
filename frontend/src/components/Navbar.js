import React, { useState, useEffect } from 'react';
import { NavLink } from 'react-router-dom';

function Navbar({ profile, user, darkMode, toggleDarkMode, onLogout }) {
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [isWide, setIsWide] = useState(window.innerWidth > 960);

  useEffect(() => {
    const handler = () => setIsWide(window.innerWidth > 960);
    window.addEventListener('resize', handler);
    return () => window.removeEventListener('resize', handler);
  }, []);

  const navLinkClass = ({ isActive }) => 'nav-link' + (isActive ? ' nav-link-active' : '');
  const mobileNavClass = ({ isActive }) => 'mobile-nav-item' + (isActive ? ' active' : '');

  return (
    <>
      <nav className="navbar">
        <div className="container navbar-inner">
          <div className="nav-brand">
            <h1>🥗 CalorieTracker</h1>
          </div>

          {isWide && (
            <div className="nav-links">
              <NavLink to="/" end className={navLinkClass}>Home</NavLink>
              <NavLink to="/log" className={navLinkClass}>Log Food</NavLink>
              <NavLink to="/today" className={navLinkClass}>Today</NavLink>
              <NavLink to="/week" className={navLinkClass}>This Week</NavLink>
              <NavLink to="/reports" className={navLinkClass}>Reports</NavLink>
              <NavLink to="/meals" className={navLinkClass}>Meals</NavLink>
              <NavLink to="/settings" className={navLinkClass}>Settings</NavLink>
            </div>
          )}

          <div className="nav-actions">
            <button className="btn-theme-toggle" onClick={toggleDarkMode} title="Toggle dark mode">
              {darkMode ? '☀️' : '🌙'}
            </button>

            {user && (
              <div className="user-menu-wrap">
                <button
                  className="user-avatar-btn"
                  onClick={() => setShowUserMenu(v => !v)}
                  title={user.name}
                >
                  {user.picture
                    ? <img src={user.picture} alt={user.name} className="user-avatar-img" referrerPolicy="no-referrer" />
                    : <span className="user-avatar-fallback">{user.name?.[0] || '?'}</span>
                  }
                </button>

                {showUserMenu && (
                  <div className="user-menu" onMouseLeave={() => setShowUserMenu(false)}>
                    <div className="user-menu-info">
                      <strong>{user.name}</strong>
                      <span>{user.email}</span>
                    </div>
                    <hr className="user-menu-divider" />
                    <button className="user-menu-logout" onClick={onLogout}>
                      🚪 Sign out
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
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
        <NavLink to="/week" className={mobileNavClass}>
          <span className="mobile-nav-icon">📅</span>
          <span className="mobile-nav-label">This Week</span>
        </NavLink>
        <NavLink to="/meals" className={mobileNavClass}>
          <span className="mobile-nav-icon">🍽️</span>
          <span className="mobile-nav-label">Meals</span>
        </NavLink>
        <NavLink to="/reports" className={mobileNavClass}>
          <span className="mobile-nav-icon">📈</span>
          <span className="mobile-nav-label">Reports</span>
        </NavLink>
      </nav>
    </>
  );
}

export default Navbar;
