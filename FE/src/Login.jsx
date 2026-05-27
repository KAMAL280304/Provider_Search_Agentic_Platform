import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './Login.css';
import logoCog from './assets/logocog.png';

export default function Login({ onLogin }) {
  const [memberId, setMemberId] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await fetch('/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ member_id: memberId, password }),
      });
      const data = await res.json();
      if (!res.ok) {
        setError(data.detail || 'Invalid member ID or password');
        return;
      }
      localStorage.setItem('member', JSON.stringify(data.member));
      onLogin();
      navigate('/');
    } catch (err) {
      setError('Could not reach the server. Make sure the backend is running.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-card">
        <div className="login-logo">
          <img src={logoCog} alt="Cigna" className="login-logo-img" />
        </div>
        <div className="login-subtitle">Sign in to your member portal</div>

        {error && <div className="login-error">{error}</div>}

        <form onSubmit={handleLogin}>
          <label className="login-label">Member ID</label>
          <input
            className="login-input"
            type="text"
            placeholder="e.g. MEM-10002"
            value={memberId}
            onChange={(e) => setMemberId(e.target.value)}
            required
          />

          <label className="login-label">Password</label>
          <input
            className="login-input"
            type="password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <button className="login-btn" type="submit" disabled={loading}>
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
}
