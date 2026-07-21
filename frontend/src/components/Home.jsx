import { useState } from 'react';
import * as api from '../api';

export default function Home({ onStart, onMyJourneys, onDiscover, isGuest, onSignIn, onLogout }) {
  const [loading, setLoading] = useState(false);

  async function handleStart() {
    if (loading) return;
    setLoading(true);
    try {
      const data = isGuest ? await api.startGuestJourney() : await api.startJourney();
      onStart(data, data.first_track);
    } catch (_) {
      setLoading(false);
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '2rem',
    }}>
      <h1 style={{ fontSize: '1.75rem', letterSpacing: '0.2em', marginBottom: '0.4rem' }}>
        CRATES
      </h1>
      <p style={{ color: '#3a3a3a', fontSize: '0.8rem', letterSpacing: '0.1em', marginBottom: '4rem' }}>
        dig thru
      </p>

      <button
        onClick={handleStart}
        disabled={loading}
        style={{
          padding: '1rem 2.5rem',
          background: loading ? '#7a5020' : '#c8873a',
          border: 'none',
          borderRadius: '2px',
          color: '#0a0a0a',
          fontSize: '0.8rem',
          fontWeight: '600',
          letterSpacing: '0.14em',
          cursor: loading ? 'default' : 'pointer',
          transition: 'background 0.15s ease',
        }}
      >
        {loading ? '...' : 'START A JOURNEY'}
      </button>

      <p style={{
        color: '#2a2a2a',
        fontSize: '0.72rem',
        letterSpacing: '0.06em',
        marginTop: '1rem',
        marginBottom: 0,
      }}>
        and you might find something new
      </p>

      {onMyJourneys && (
        <button
          onClick={onMyJourneys}
          style={{
            marginTop: '3rem',
            background: 'none',
            border: 'none',
            color: '#2e2e2e',
            cursor: 'pointer',
            fontSize: '0.68rem',
            letterSpacing: '0.12em',
            padding: 0,
          }}
        >
          YOUR JOURNEYS
        </button>
      )}

      {onDiscover && (
        <button
          onClick={onDiscover}
          style={{
            marginTop: '0.875rem',
            background: 'none',
            border: 'none',
            color: '#2e2e2e',
            cursor: 'pointer',
            fontSize: '0.68rem',
            letterSpacing: '0.12em',
            padding: 0,
          }}
        >
          DISCOVER
        </button>
      )}

      {isGuest && onSignIn && (
        <button
          onClick={onSignIn}
          style={{
            marginTop: '3rem',
            background: 'none',
            border: 'none',
            color: '#555',
            cursor: 'pointer',
            fontSize: '0.65rem',
            letterSpacing: '0.1em',
            padding: 0,
          }}
        >
          SIGN IN
        </button>
      )}

      {!isGuest && onLogout && (
        <button
          onClick={onLogout}
          style={{
            marginTop: '3rem',
            background: 'none',
            border: 'none',
            color: '#2a2a2a',
            cursor: 'pointer',
            fontSize: '0.62rem',
            letterSpacing: '0.1em',
            padding: 0,
          }}
        >
          LOG OUT
        </button>
      )}
    </div>
  );
}
