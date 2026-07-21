import { useState, useRef, useEffect } from 'react';
import * as api from '../api';
import poweredBySoundCloud from '../assets/powered_by_soundcloud.png';
import SignUpPrompt from './SignUpPrompt';

const ACTION_CONFIG = {
  dislike: { label: '✕', idle: '#5a2020', active: '#e05252' },
  skip:    { label: '→', idle: '#2e2e2e', active: '#888'    },
  like:    { label: '♥', idle: '#1a4028', active: '#52c87a' },
};

const ACTION_ICONS = { like: '♥', skip: '→', dislike: '✕' };
const ACTION_COLORS = { like: '#52c87a', skip: '#555', dislike: '#e05252' };

export default function Player({ journey, initialTrack, onEnd, onDiscover, onMyJourneys, onHome, isGuest, onGuestLike, showSignUpPrompt, onSignUp, onDismissPrompt }) {
  const [currentTrack, setCurrentTrack] = useState(initialTrack);
  const [trackStartTime, setTrackStartTime] = useState(() => Date.now());
  const [isActing, setIsActing] = useState(false);
  const [likedCurrentTrack, setLikedCurrentTrack] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const [historyEvents, setHistoryEvents] = useState([]);
  const [titleHovered, setTitleHovered] = useState(false);
  const [artistHovered, setArtistHovered] = useState(false);
  const [discoverHovered, setDiscoverHovered] = useState(false);
  const [myJourneysHovered, setMyJourneysHovered] = useState(false);
  const [homeHovered, setHomeHovered] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [artworkHovered, setArtworkHovered] = useState(false);
  const audioRef = useRef(null);

  async function fetchAndPlay(track) {
    if (!audioRef.current) return;
    audioRef.current.pause();
    try {
      const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';
      const token = localStorage.getItem('crates_token');
      const res = await fetch(
        `${BASE_URL}/tracks/${track.soundcloud_id}/stream`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) return;
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);
      audioRef.current.src = blobUrl;
    } catch (_) {}
  }

  useEffect(() => {
    fetchAndPlay(initialTrack).then(() => {
      audioRef.current?.play().catch(() => {});
    });
  }, []);

  async function togglePlayPause() {
    if (!audioRef.current) return;
    if (audioRef.current.paused) {
      await audioRef.current.play().catch(() => {});
    } else {
      audioRef.current.pause();
    }
  }

  async function act(action) {
    if (isActing) return;

    // Like: mark as liked, log immediately, keep playing
    if (action === 'like') {
      setLikedCurrentTrack(true);
      setHistoryEvents(prev => [...prev, { track: currentTrack, action: 'like' }]);
      if (isGuest) {
        onGuestLike?.();
      } else {
        api.logEvent(
          journey.journey_id,
          journey.session_id,
          currentTrack.id,
          'like',
          Date.now() - trackStartTime,
        ).catch(() => {});
      }
      return;
    }

    if (audioRef.current) audioRef.current.pause();
    setIsActing(true);

    // Skip after like: like was already logged, just advance
    const effectiveAction = (action === 'skip' && likedCurrentTrack) ? 'like' : action;
    const listenDurationMs = Date.now() - trackStartTime;
    if (!likedCurrentTrack) {
      setHistoryEvents(prev => [...prev, { track: currentTrack, action: effectiveAction }]);
    }
    setLikedCurrentTrack(false);

    try {
      const next = isGuest
        ? await api.guestNextTrack(
            journey.journey_id,
            journey.session_id,
            currentTrack.id,
            effectiveAction,
            listenDurationMs,
          )
        : await api.nextTrack(
            journey.journey_id,
            journey.session_id,
            currentTrack.id,
            effectiveAction,
            listenDurationMs,
          );
      setCurrentTrack(next);
      setTrackStartTime(Date.now());
      await fetchAndPlay(next);
      audioRef.current?.play().catch(() => {});
    } catch (err) {
      console.error('nextTrack failed:', err);
    } finally {
      setIsActing(false);
    }
  }

  function handleAudioEnded() {
    // If liked, advance and record the like; otherwise wait for user action
    if (likedCurrentTrack) {
      act('skip'); // resolves to 'like' because likedCurrentTrack=true
    }
  }

  async function handleEnd() {
    try { await api.endJourney(journey.journey_id); } catch (_) {}
    onEnd();
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '1.5rem',
      position: 'relative',
      overflow: 'hidden',
    }}>

      {/* Nav bar */}
      <div style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        height: '36px',
        background: '#0a0a0a',
        borderBottom: '1px solid #111',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 1.25rem',
        zIndex: 20,
      }}>
        <button
          onClick={onDiscover}
          onMouseEnter={() => setDiscoverHovered(true)}
          onMouseLeave={() => setDiscoverHovered(false)}
          style={{
            background: 'none',
            border: 'none',
            color: discoverHovered ? '#c8873a' : '#333',
            fontSize: '0.7rem',
            letterSpacing: '0.12em',
            cursor: 'pointer',
            padding: 0,
            transition: 'color 0.15s ease',
          }}
        >
          DISCOVER
        </button>
        <button
          onClick={onHome}
          onMouseEnter={() => setHomeHovered(true)}
          onMouseLeave={() => setHomeHovered(false)}
          style={{
            position: 'absolute',
            left: '50%',
            transform: 'translateX(-50%)',
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
        {!isGuest && (
          <button
            onClick={onMyJourneys}
            onMouseEnter={() => setMyJourneysHovered(true)}
            onMouseLeave={() => setMyJourneysHovered(false)}
            style={{
              background: 'none',
              border: 'none',
              color: myJourneysHovered ? '#c8873a' : '#333',
              fontSize: '0.7rem',
              letterSpacing: '0.12em',
              cursor: 'pointer',
              padding: 0,
              transition: 'color 0.15s ease',
            }}
          >
            MY JOURNEYS
          </button>
        )}
        {isGuest && <span style={{ width: '6rem' }} />}
      </div>

      <audio
        ref={audioRef}
        onEnded={handleAudioEnded}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
        style={{ display: 'none' }}
      />

      {/* Artwork */}
      <div
        onMouseEnter={() => setArtworkHovered(true)}
        onMouseLeave={() => setArtworkHovered(false)}
        style={{
          width: '100%',
          maxWidth: '300px',
          aspectRatio: '1 / 1',
          marginBottom: '1.75rem',
          borderRadius: '2px',
          overflow: 'hidden',
          background: '#c8873a',
          flexShrink: 0,
          position: 'relative',
          cursor: 'pointer',
        }}
      >
        {currentTrack?.artwork_url && (
          <img
            src={currentTrack.artwork_url}
            alt={currentTrack.title}
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
          />
        )}
        <div
          onClick={togglePlayPause}
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            opacity: (artworkHovered || !isPlaying) ? 1 : 0,
            transition: 'opacity 0.2s ease',
          }}
        >
          <div style={{
            width: '56px',
            height: '56px',
            borderRadius: '50%',
            background: 'rgba(0,0,0,0.5)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '1.4rem',
            color: '#fff',
            userSelect: 'none',
          }}>
            {(artworkHovered && isPlaying) ? '⏸' : '▶'}
          </div>
        </div>
      </div>

      {/* Track info */}
      <div style={{ width: '100%', maxWidth: '300px', marginBottom: '2rem' }}>
        <p style={{ fontSize: '1.15rem', fontWeight: '600', lineHeight: 1.25, marginBottom: '0.3rem' }}>
          <a
            href={currentTrack?.permalink_url}
            target="_blank"
            rel="noopener noreferrer"
            onMouseEnter={() => setTitleHovered(true)}
            onMouseLeave={() => setTitleHovered(false)}
            style={{ color: 'inherit', textDecoration: titleHovered ? 'underline' : 'none' }}
          >
            {currentTrack?.title}
          </a>
        </p>
        <p style={{ color: '#666', fontSize: '0.875rem', marginBottom: '0.5rem' }}>
          <a
            href={`https://soundcloud.com/${currentTrack?.artist}`}
            target="_blank"
            rel="noopener noreferrer"
            onMouseEnter={() => setArtistHovered(true)}
            onMouseLeave={() => setArtistHovered(false)}
            style={{ color: '#666', textDecoration: artistHovered ? 'underline' : 'none' }}
          >
            {currentTrack?.artist}
          </a>
        </p>
      </div>

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: '1.25rem', marginBottom: '0.75rem' }}>
        {['dislike', 'skip', 'like'].map(action => (
          <ActionButton
            key={action}
            action={action}
            disabled={isActing}
            liked={action === 'like' && likedCurrentTrack}
            onClick={() => act(action)}
          />
        ))}
      </div>

      {/* Liked confirmation — fades in/out */}
      <p style={{
        color: '#c8873a',
        fontSize: '0.72rem',
        letterSpacing: '0.08em',
        margin: '0 0 1.75rem',
        opacity: likedCurrentTrack ? 1 : 0,
        transition: 'opacity 0.2s ease',
        userSelect: 'none',
      }}>
        ♥ liked
      </p>

      {/* History toggle */}
      <button
        onClick={() => setShowHistory(true)}
        style={{
          background: 'none',
          border: 'none',
          color: '#333',
          fontSize: '0.75rem',
          letterSpacing: '0.06em',
          cursor: 'pointer',
          padding: '0.5rem',
        }}
      >
        journey history
        {historyEvents.length > 0 && (
          <span style={{ color: '#444', marginLeft: '0.4rem' }}>({historyEvents.length})</span>
        )}
      </button>

      <a
        href="https://soundcloud.com"
        target="_blank"
        rel="noopener noreferrer"
        style={{ marginTop: '2rem', display: 'block' }}
      >
        <img
          src={poweredBySoundCloud}
          alt="Powered by SoundCloud"
          style={{ height: '60px', opacity: 1.0 }}
        />
      </a>

      <a
        href="https://www.buymeacoffee.com/Nyctimene_Chops"
        target="_blank"
        rel="noopener noreferrer"
        style={{ marginTop: '1rem', marginBottom: '2rem', display: 'block' }}
      >
        <img
          src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png"
          alt="Buy Me A Coffee"
          style={{ height: '40px' }}
        />
      </a>

      <HistoryPanel
        visible={showHistory}
        events={historyEvents}
        onClose={() => setShowHistory(false)}
      />

      {showSignUpPrompt && (
        <SignUpPrompt
          onSignUp={onSignUp}
          onDismiss={onDismissPrompt}
        />
      )}
    </div>
  );
}

function ActionButton({ action, disabled, onClick, liked }) {
  const [hovered, setHovered] = useState(false);
  const { label, idle, active } = ACTION_CONFIG[action];
  const color = liked ? active : (hovered && !disabled ? active : idle);

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      aria-label={action}
      style={{
        width: '60px',
        height: '60px',
        borderRadius: '50%',
        border: `1px solid ${color}`,
        background: liked ? active : 'transparent',
        color: liked ? '#0a0a0a' : color,
        fontSize: '1.4rem',
        lineHeight: 1,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        cursor: disabled ? 'default' : 'pointer',
        opacity: disabled ? 0.4 : 1,
        transition: 'color 0.15s ease, border-color 0.15s ease, background 0.15s ease, opacity 0.15s ease',
      }}
    >
      {label}
    </button>
  );
}

function HistoryPanel({ visible, events, onClose }) {
  return (
    <>
      {visible && (
        <div
          onClick={onClose}
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(0,0,0,0.55)',
            zIndex: 10,
          }}
        />
      )}

      <div
        role="dialog"
        aria-label="Journey history"
        style={{
          position: 'fixed',
          right: 0,
          top: 0,
          bottom: 0,
          width: '100%',
          maxWidth: '340px',
          background: '#0f0f0f',
          borderLeft: '1px solid #1a1a1a',
          zIndex: 11,
          display: 'flex',
          flexDirection: 'column',
          transform: visible ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.24s ease',
        }}
      >
        {/* Header */}
        <div style={{
          padding: '1.125rem 1.25rem',
          borderBottom: '1px solid #1a1a1a',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
        }}>
          <span style={{ fontSize: '0.75rem', letterSpacing: '0.1em', color: '#555' }}>
            JOURNEY HISTORY
          </span>
          <button
            onClick={onClose}
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

        {/* Event list */}
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {events.length === 0 ? (
            <p style={{ color: '#333', fontSize: '0.8rem', padding: '1.25rem' }}>
              No tracks yet.
            </p>
          ) : (
            [...events].reverse().map((event, i) => (
              <div key={i} style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.75rem',
                padding: '0.6rem 1.25rem',
                borderBottom: '1px solid #141414',
              }}>
                <span style={{
                  color: ACTION_COLORS[event.action],
                  fontSize: '0.85rem',
                  width: '1rem',
                  flexShrink: 0,
                  textAlign: 'center',
                }}>
                  {ACTION_ICONS[event.action]}
                </span>
                <div style={{ minWidth: 0 }}>
                  <a
                    href={event.track.permalink_url}
                    target="_blank"
                    rel="noopener noreferrer"
                    style={{
                      fontSize: '0.825rem',
                      margin: 0,
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                      display: 'block',
                      color: '#f0f0f0',
                      textDecoration: 'none',
                    }}
                  >
                    {event.track.title}
                  </a>
                  <p style={{ fontSize: '0.7rem', color: '#555', margin: 0 }}>
                    {event.track.artist}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </>
  );
}
