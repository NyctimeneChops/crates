import { useState, useEffect } from 'react';
import * as api from '../api';

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

const btnBase = {
  padding: '0.4rem 0.8rem',
  background: 'transparent',
  border: '1px solid #222',
  borderRadius: '2px',
  color: '#666',
  fontSize: '0.68rem',
  letterSpacing: '0.09em',
  cursor: 'pointer',
  transition: 'color 0.15s ease, border-color 0.15s ease',
};

export default function Feed({ onBack, onWitness, onFork, onHome }) {
  const [journeys, setJourneys] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [homeHovered, setHomeHovered] = useState(false);

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      setError(null);
      try {
        const data = await api.getFeed();
        setJourneys(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, []);

  return (
    <div style={{ minHeight: '100vh', background: '#0a0a0a', color: '#f0f0f0' }}>

      {/* Sticky header */}
      <div style={{
        position: 'sticky',
        top: 0,
        background: '#0a0a0a',
        borderBottom: '1px solid #141414',
        padding: '1rem 1.5rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '1rem',
        zIndex: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button
            onClick={onBack}
            style={{
              background: 'none',
              border: 'none',
              color: '#444',
              cursor: 'pointer',
              fontSize: '1rem',
              padding: '0.2rem 0.5rem 0.2rem 0',
              lineHeight: 1,
            }}
          >
            ←
          </button>
          <span style={{ fontSize: '0.72rem', letterSpacing: '0.16em', color: '#888' }}>
            DISCOVER
          </span>
        </div>
        <button
          onClick={onHome}
          onMouseEnter={() => setHomeHovered(true)}
          onMouseLeave={() => setHomeHovered(false)}
          style={{
            background: 'none',
            border: 'none',
            color: homeHovered ? '#e09a4a' : '#c8873a',
            fontSize: '0.7rem',
            letterSpacing: '0.12em',
            cursor: 'pointer',
            padding: 0,
            transition: 'color 0.15s ease',
          }}
        >
          HOME
        </button>
      </div>

      {/* Content */}
      <div style={{ padding: '0 1.5rem 3rem', maxWidth: '520px', margin: '0 auto' }}>

        {isLoading && (
          <p style={{ color: '#2a2a2a', fontSize: '0.78rem', textAlign: 'center', marginTop: '4rem' }}>
            Loading...
          </p>
        )}

        {error && (
          <p style={{ color: '#e05252', fontSize: '0.78rem', marginTop: '1.5rem' }}>{error}</p>
        )}

        {!isLoading && !error && journeys.length === 0 && (
          <p style={{ color: '#2a2a2a', fontSize: '0.82rem', textAlign: 'center', marginTop: '5rem' }}>
            No public journeys yet. Be the first.
          </p>
        )}

        {journeys.map(j => (
          <div
            key={j.id}
            style={{ borderBottom: '1px solid #111', padding: '1.375rem 0' }}
          >
            <p style={{
              fontSize: '0.88rem',
              fontWeight: '600',
              lineHeight: 1.3,
              marginBottom: '0.2rem',
            }}>
              {j.name || j.seed_track.title}
            </p>
            <p style={{ fontSize: '0.7rem', color: '#c8873a', marginBottom: '0.65rem' }}>
              @{j.tastemaker_username}
            </p>

            {/* Stats row */}
            <p style={{
              fontSize: '0.68rem',
              color: '#333',
              marginBottom: '0.875rem',
              letterSpacing: '0.03em',
            }}>
              {j.play_count} {j.play_count === 1 ? 'play' : 'plays'}
              <span style={{ margin: '0 0.4rem' }}>·</span>
              {j.fork_count} {j.fork_count === 1 ? 'fork' : 'forks'}
              <span style={{ margin: '0 0.4rem' }}>·</span>
              {j.event_count} tracks
            </p>

            {/* Action buttons */}
            <div style={{ display: 'flex', gap: '0.5rem' }}>
              <button onClick={() => onWitness(j.id)} style={btnBase}>
                WITNESS
              </button>
              <button onClick={() => onFork(j.id)} style={btnBase}>
                FORK
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
