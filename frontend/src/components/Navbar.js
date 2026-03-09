import React from 'react';
import { Link } from 'react-router-dom';

function Navbar({ profile }) {
  return (
    <nav className="navbar">
      <div className="container">
        <div className="nav-brand">
          <h1>🥗 CalorieTracker</h1>
        </div>
        <div className="nav-links">
          <Link to="/" className="nav-link">Home</Link>
          <Link to="/log" className="nav-link">Log Food</Link>
          <Link to="/today" className="nav-link">Today</Link>
          <Link to="/week" className="nav-link">This Week</Link>
          <Link to="/reports" className="nav-link">Reports</Link>
          <Link to="/meals" className="nav-link">Meals</Link>
          <Link to="/settings" className="nav-link">Settings</Link>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;