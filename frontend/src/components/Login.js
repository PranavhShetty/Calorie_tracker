import React, { useState } from 'react';
import { GoogleLogin } from '@react-oauth/google';
import axios from 'axios';

function Login({ onLoginSuccess, apiUrl, darkMode }) {
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleGuest = async () => {
    setError('');
    setLoading(true);
    try {
      const res = await axios.post(
        `${apiUrl}/api/auth/guest`,
        {},
        { withCredentials: true }
      );
      if (res.data.success) {
        onLoginSuccess(res.data.user);
      }
    } catch (e) {
      console.error('Guest sign-in error:', e.response?.status, e.response?.data || e.message);
      setError('Guest sign-in failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleSuccess = async (credentialResponse) => {
    setError('');
    setLoading(true);
    try {
      const res = await axios.post(
        `${apiUrl}/api/auth/google`,
        { credential: credentialResponse.credential },
        { withCredentials: true }
      );
      if (res.data.success) {
        onLoginSuccess(res.data.user);
      }
    } catch (e) {
      console.error('Google sign-in error:', e.response?.status, e.response?.data || e.message);
      setError('Sign-in failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-screen">
      <div className="login-card">
        <div className="login-logo">🥗</div>
        <h1 className="login-title">CalorieTracker</h1>
        <p className="login-subtitle">
          LLM-powered macro tracking<br />for Indian foods
        </p>

        <div className="login-divider" />

        <p className="login-prompt">Sign in to continue</p>

        {loading ? (
          <div className="login-loading">
            <div className="spinner" style={{ margin: '0 auto' }} />
            <p style={{ marginTop: '0.75rem', color: 'var(--text-secondary)' }}>Signing you in…</p>
          </div>
        ) : (
          <>
            <div className="login-google-btn">
              <GoogleLogin
                onSuccess={handleSuccess}
                onError={() => console.warn('Google OAuth flow failed')}
                theme={darkMode ? 'filled_black' : 'outline'}
                shape="rectangular"
                size="large"
                text="signin_with"
                width="280"
              />
            </div>
            <div className="login-divider-or">
              <span>or</span>
            </div>
            <button className="login-guest-btn" onClick={handleGuest}>
              Continue as Guest
            </button>
          </>
        )}

        {error && (
          <p className="login-error">{error}</p>
        )}

        <p className="login-footer">
          Your data stays private. We only use your Google account to identify you.
        </p>
      </div>
    </div>
  );
}

export default Login;
