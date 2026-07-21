import { useState, useEffect, useRef } from 'react';
import * as api from '../api';

function formatDate(dateStr) {
  return new Date(dateStr).toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
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

const ACTION_ICONS = { like: '♥', skip: '→', dislike: '✕' };
const ACTION_COLORS = { like: '#52c87a', skip: '#555', dislike: '#e05252' };

export default function MyJourneys({ onBack, onWitness, onFork, onContinue, onHome }) {
  const [journeys, setJourneys] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [homeHovered, setHomeHovered] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);

  const [editingId, setEditingId] = useState(null);
  const [editingName, setEditingName] = useState('');
  const [confirmingDeleteId, setConfirmingDeleteId] = useState(null);

  const [tracklistJourneyId, setTracklistJourneyId] = useState(null);
  const [tracklistData, setTracklistData] = useState([]);
  const [tracklistLoading, setTracklistLoading] = useState(false);
  const [openDotMenu, setOpenDotMenu] = useState(null);

  const renameInputRef = useRef(null);

  async function load() {
    setLoading(true);
    setError('');
    try {
      const data = await api.getMyJourneys(page);
      setJourneys(data.journeys);
      setTotalPages(data.pages);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    load();
  }, [page]);

  useEffect(() => {
    if (editingId !== null && renameInputRef.current) {
      renameInputRef.current.focus();
      renameInputRef.current.select();
    }
  }, [editingId]);

  async function handlePublish(journeyId) {
    try {
      await api.publishJourney(journeyId);
      load();
    } catch (err) {
      console.error('Publish failed:', err);
    }
  }

  async function handleContinue(journeyId) {
    try {
      const data = await api.continueJourney(journeyId);
      onContinue(data);
    } catch (err) {
      console.error('Continue failed:', err);
    }
  }

  function startRename(j) {
    setEditingId(j.id);
    setEditingName(j.name || j.seed_track.title);
  }

  async function commitRename(journeyId) {
    const name = editingName.trim();
    if (!name) { cancelRename(); return; }
    setEditingId(null);
    try {
      await api.renameJourney(journeyId, name);
      setJourneys(prev => prev.map(j => j.id === journeyId ? { ...j, name } : j));
    } catch (err) {
      console.error('Rename failed:', err);
    }
  }

  function cancelRename() {
    setEditingId(null);
    setEditingName('');
  }

  async function handleDelete(journeyId) {
    setConfirmingDeleteId(null);
    try {
      await api.deleteJourney(journeyId);
      setJourneys(prev => prev.filter(j => j.id !== journeyId));
    } catch (err) {
      console.error('Delete failed:', err);
    }
  }

  async function openTracklist(journeyId) {
    setTracklistJourneyId(journeyId);
    setTracklistData([]);
    setTracklistLoading(true);
    try {
      const data = await api.getTracklist(journeyId);
      setTracklistData(data);
    } catch (err) {
      console.error('Tracklist failed:', err);
    } finally {
      setTracklistLoading(false);
    }
  }

  function closeTracklist() {
    setTracklistJourneyId(null);
    setTracklistData([]);
    setOpenDotMenu(null);
  }

  async function handleForkFromPosition(position) {
    const journeyId = tracklistJourneyId;
    closeTracklist();
    try {
      const data = await api.forkFromPosition(journeyId, position);
      onFork(data);
    } catch (err) {
      console.error('Fork from position failed:', err);
    }
  }

  const panelOpen = tracklistJourneyId !== null;

  return (
    <div style={{ minHeight: '100vh', background: '#0a0a0a', color: '#f0f0f0' }}>

      {/* Header */}
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
            YOUR JOURNEYS
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

        {loading && (
          <p style={{ color: '#2a2a2a', fontSize: '0.78rem', textAlign: 'center', marginTop: '4rem' }}>
            loading...
          </p>
        )}

        {error && (
          <p style={{ color: '#e05252', fontSize: '0.78rem', marginTop: '1.5rem' }}>{error}</p>
        )}

        {!loading && journeys.length === 0 && (
          <p style={{ color: '#2a2a2a', fontSize: '0.82rem', textAlign: 'center', marginTop: '5rem' }}>
            No journeys yet. Start one.
          </p>
        )}

        {journeys.map(j => (
          <div
            key={j.id}
            style={{ borderBottom: '1px solid #111', padding: '1.375rem 0' }}
          >
            {/* Title row: name (editable) + delete */}
            <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.75rem', marginBottom: '0.2rem' }}>
              <div style={{ flex: 1, minWidth: 0 }}>
                {editingId === j.id ? (
                  <input
                    ref={renameInputRef}
                    value={editingName}
                    onChange={e => setEditingName(e.target.value)}
                    onBlur={() => commitRename(j.id)}
                    onKeyDown={e => {
                      if (e.key === 'Enter') { e.preventDefault(); commitRename(j.id); }
                      if (e.key === 'Escape') cancelRename();
                    }}
                    style={{
                      fontSize: '0.88rem',
                      fontWeight: '600',
                      lineHeight: 1.3,
                      background: 'transparent',
                      border: 'none',
                      borderBottom: '1px solid #444',
                      color: '#f0f0f0',
                      outline: 'none',
                      width: '100%',
                      padding: '0 0 0.1rem 0',
                    }}
                  />
                ) : (
                  <p
                    onClick={() => startRename(j)}
                    title="Click to rename"
                    style={{
                      fontSize: '0.88rem',
                      fontWeight: '600',
                      lineHeight: 1.3,
                      margin: 0,
                      cursor: 'text',
                      color: '#f0f0f0',
                    }}
                  >
                    {j.name || j.seed_track.title}
                  </p>
                )}
              </div>
              {confirmingDeleteId === j.id ? (
                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', flexShrink: 0 }}>
                  <button
                    onClick={() => handleDelete(j.id)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#e05252',
                      fontSize: '0.62rem',
                      letterSpacing: '0.08em',
                      cursor: 'pointer',
                      padding: 0,
                    }}
                  >
                    YES
                  </button>
                  <button
                    onClick={() => setConfirmingDeleteId(null)}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#444',
                      fontSize: '0.62rem',
                      letterSpacing: '0.08em',
                      cursor: 'pointer',
                      padding: 0,
                    }}
                  >
                    CANCEL
                  </button>
                </div>
              ) : (
                <button
                  onClick={() => setConfirmingDeleteId(j.id)}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#3a1a1a',
                    fontSize: '0.62rem',
                    letterSpacing: '0.08em',
                    cursor: 'pointer',
                    padding: 0,
                    flexShrink: 0,
                    transition: 'color 0.15s ease',
                  }}
                  onMouseEnter={e => { e.currentTarget.style.color = '#e05252'; }}
                  onMouseLeave={e => { e.currentTarget.style.color = '#3a1a1a'; }}
                >
                  DELETE
                </button>
              )}
            </div>


            {/* Meta badges */}
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              flexWrap: 'wrap',
              marginBottom: '0.875rem',
            }}>
              <span style={{ fontSize: '0.68rem', color: '#333' }}>
                {j.session_count} {j.session_count !== 1 ? 'sessions' : 'session'} · {j.event_count} {j.event_count !== 1 ? 'tracks' : 'track'}
              </span>
              {j.is_public && (
                <span style={{
                  fontSize: '0.58rem',
                  letterSpacing: '0.09em',
                  color: '#c8873a',
                  border: '1px solid rgba(200,135,58,0.3)',
                  padding: '0.1rem 0.4rem',
                  borderRadius: '2px',
                }}>
                  PUBLIC
                </span>
              )}
              {j.fork_source_journey_id && (
                <span style={{
                  fontSize: '0.58rem',
                  letterSpacing: '0.09em',
                  color: '#555',
                  border: '1px solid #1e1e1e',
                  padding: '0.1rem 0.4rem',
                  borderRadius: '2px',
                }}>
                  FORKED
                </span>
              )}
            </div>

            {/* Action buttons */}
            <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <button
                onClick={() => handleContinue(j.id)}
                style={{ ...btnBase, color: '#c8873a', borderColor: 'rgba(200,135,58,0.4)' }}
              >
                CONTINUE
              </button>
              <button onClick={() => openTracklist(j.id)} style={btnBase}>
                TRACKLIST
              </button>
              <button onClick={() => onWitness(j.id)} style={btnBase}>
                WITNESS
              </button>
              {!j.is_public && (
                <button
                  onClick={() => handlePublish(j.id)}
                  style={{ ...btnBase, color: '#333', borderColor: '#191919' }}
                >
                  PUBLISH
                </button>
              )}
            </div>
          </div>
        ))}

        {/* Pagination */}
        {totalPages > 1 && (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '1.25rem',
            padding: '2rem 0 1rem',
          }}>
            <button
              onClick={() => setPage(p => p - 1)}
              disabled={page === 1}
              style={{
                background: 'none',
                border: 'none',
                color: page === 1 ? '#222' : '#555',
                fontSize: '0.72rem',
                letterSpacing: '0.08em',
                cursor: page === 1 ? 'default' : 'pointer',
              }}
            >
              ← Previous
            </button>
            <span style={{ fontSize: '0.68rem', color: '#333', fontVariantNumeric: 'tabular-nums' }}>
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={page === totalPages}
              style={{
                background: 'none',
                border: 'none',
                color: page === totalPages ? '#222' : '#555',
                fontSize: '0.72rem',
                letterSpacing: '0.08em',
                cursor: page === totalPages ? 'default' : 'pointer',
              }}
            >
              Next →
            </button>
          </div>
        )}
      </div>

      {/* Tracklist panel overlay */}
      {panelOpen && (
        <div
          onClick={closeTracklist}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.55)',
            zIndex: 10,
          }}
        />
      )}

      {/* Tracklist panel */}
      <div
        role="dialog"
        aria-label="Tracklist"
        style={{
          position: 'fixed',
          right: 0,
          top: 0,
          bottom: 0,
          width: '100%',
          maxWidth: '360px',
          background: '#0f0f0f',
          borderLeft: '1px solid #1a1a1a',
          zIndex: 11,
          display: 'flex',
          flexDirection: 'column',
          transform: panelOpen ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.24s ease',
        }}
      >
        <div style={{
          padding: '1.125rem 1.25rem',
          borderBottom: '1px solid #1a1a1a',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <span style={{ fontSize: '0.75rem', letterSpacing: '0.1em', color: '#555' }}>
            TRACKLIST
          </span>
          <button
            onClick={closeTracklist}
            style={{
              background: 'none',
              border: 'none',
              color: '#444',
              cursor: 'pointer',
              fontSize: '1.2rem',
              lineHeight: 1,
              padding: '0.2rem 0.4rem',
            }}
          >
            ×
          </button>
        </div>

        <div style={{ flex: 1, overflowY: 'auto' }} onClick={() => setOpenDotMenu(null)}>
          {tracklistLoading && (
            <p style={{ color: '#2a2a2a', fontSize: '0.78rem', padding: '1.25rem' }}>
              loading...
            </p>
          )}
          {!tracklistLoading && tracklistData.length === 0 && (
            <p style={{ color: '#333', fontSize: '0.8rem', padding: '1.25rem' }}>
              No tracks yet.
            </p>
          )}
          {tracklistData.map((item, i) => (
            <div key={i} style={{ position: 'relative', borderBottom: '1px solid #141414' }}>
              <div style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                padding: '0.6rem 1.25rem',
              }}>
                <span style={{
                  fontSize: '0.62rem',
                  color: '#2a2a2a',
                  width: '1.5rem',
                  flexShrink: 0,
                  textAlign: 'right',
                  fontVariantNumeric: 'tabular-nums',
                }}>
                  {item.position + 1}
                </span>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <a
                    href={item.track.permalink_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      fontSize: '0.8rem',
                      color: '#e0e0e0',
                      textDecoration: 'none',
                      display: 'block',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}
                  >
                    {item.track.title}
                  </a>
                  <p style={{ fontSize: '0.68rem', color: '#555', margin: 0 }}>
                    {item.track.artist}
                  </p>
                </div>
                <span style={{
                  fontSize: '0.85rem',
                  color: ACTION_COLORS[item.action] || '#555',
                  flexShrink: 0,
                  width: '1rem',
                  textAlign: 'center',
                }}>
                  {ACTION_ICONS[item.action] || '·'}
                </span>
                <button
                  onClick={e => { e.stopPropagation(); setOpenDotMenu(openDotMenu === item.position ? null : item.position); }}
                  style={{
                    background: 'none',
                    border: 'none',
                    color: '#444',
                    cursor: 'pointer',
                    fontSize: '1rem',
                    padding: '0 0.25rem',
                    flexShrink: 0,
                    lineHeight: 1,
                  }}
                >
                  ⋯
                </button>
              </div>
              {openDotMenu === item.position && (
                <div
                  onClick={e => e.stopPropagation()}
                  style={{
                    position: 'absolute',
                    right: '1.25rem',
                    top: '100%',
                    background: '#111',
                    border: '1px solid #222',
                    borderRadius: '2px',
                    zIndex: 20,
                    minWidth: '130px',
                  }}
                >
                  <button
                    onClick={() => handleForkFromPosition(item.position)}
                    onMouseEnter={e => { e.currentTarget.style.color = '#c8873a'; }}
                    onMouseLeave={e => { e.currentTarget.style.color = '#888'; }}
                    style={{
                      display: 'block',
                      width: '100%',
                      background: 'none',
                      border: 'none',
                      color: '#888',
                      fontSize: '0.7rem',
                      letterSpacing: '0.06em',
                      padding: '0.6rem 0.875rem',
                      cursor: 'pointer',
                      textAlign: 'left',
                      transition: 'color 0.15s ease',
                    }}
                  >
                    Fork from here
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
