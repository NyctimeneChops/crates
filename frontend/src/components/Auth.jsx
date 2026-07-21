import { useState } from 'react';
import * as api from '../api';

const input = {
  width: '100%',
  padding: '0.75rem',
  background: '#111',
  border: '1px solid #2a2a2a',
  borderRadius: '3px',
  color: '#f0f0f0',
  fontSize: '1rem',
  outline: 'none',
};

const submitBtn = {
  width: '100%',
  marginTop: '1.25rem',
  padding: '0.75rem',
  background: '#c8873a',
  border: 'none',
  borderRadius: '3px',
  color: '#0a0a0a',
  fontSize: '0.95rem',
  fontWeight: '600',
  letterSpacing: '0.05em',
  cursor: 'pointer',
};

export default function Auth({ onSuccess }) {
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [username, setUsername] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const data = mode === 'login'
        ? await api.login(email, password)
        : await api.register(email, password, username);
      api.setToken(data.access_token);
      onSuccess();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  function toggleMode() {
    setMode(mode === 'login' ? 'register' : 'login');
    setError('');
    setUsername('');
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '1.5rem',
    }}>
      <div style={{
        width: '100%',
        maxWidth: '360px',
        padding: '2.5rem',
        border: '1px solid #1e1e1e',
        borderRadius: '4px',
      }}>
        <h1 style={{ fontSize: '1.4rem', letterSpacing: '0.15em', marginBottom: '0.375rem' }}>
          CRATES
        </h1>
        <p style={{ color: '#555', fontSize: '0.85rem', marginBottom: '2rem' }}>
          {mode === 'login' ? 'Sign in to continue' : 'Create an account'}
        </p>

        <form onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={e => setEmail(e.target.value)}
            required
            style={input}
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={e => setPassword(e.target.value)}
            required
            style={{ ...input, marginTop: '0.75rem' }}
          />
          {mode === 'register' && (
            <input
              type="text"
              placeholder="Username"
              value={username}
              onChange={e => setUsername(e.target.value)}
              required
              style={{ ...input, marginTop: '0.75rem' }}
            />
          )}

          {error && (
            <p style={{ color: '#e05252', fontSize: '0.8rem', marginTop: '0.75rem' }}>
              {error}
            </p>
          )}

          <button type="submit" disabled={loading} style={{ ...submitBtn, opacity: loading ? 0.6 : 1 }}>
            {loading ? '...' : mode === 'login' ? 'Sign in' : 'Create account'}
          </button>
        </form>

        <p style={{ marginTop: '1.5rem', fontSize: '0.8rem', color: '#555' }}>
          {mode === 'login' ? "No account? " : 'Have an account? '}
          <button
            onClick={toggleMode}
            style={{
              background: 'none',
              border: 'none',
              color: '#c8873a',
              cursor: 'pointer',
              fontSize: 'inherit',
              padding: 0,
            }}
          >
            {mode === 'login' ? 'Register' : 'Sign in'}
          </button>
        </p>
      </div>
    </div>
  );
}
