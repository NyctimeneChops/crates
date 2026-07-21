import { useState, useRef, useEffect } from 'react';
import * as api from '../api';
import poweredBySoundCloud from '../assets/powered_by_soundcloud.png';

export default function WitnessPlayer({ journeyId, onBack, onFork, isOwner = false, onHome }) {
  const [tracks, setTracks] = useState([]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [isPlaying, setIsPlaying] = useState(false);
  const [artworkHovered, setArtworkHovered] = useState(false);
  const [homeHovered, setHomeHovered] = useState(false);
  const audioRef = useRef(null);
  const trackListRef = useRef(null);

  useEffect(() => {
    async function load() {
      setIsLoading(true);
      try {
        const data = isOwner
          ? await api.getJourneyTracks(journeyId)
          : await api.getWitnessTracks(journeyId);
        setTracks(data);
      } catch (err) {
        console.error('Failed to load witness tracks:', err);
      } finally {
        setIsLoading(false);
      }
    }
    load();
  }, [journeyId]);

  useEffect(() => {
    if (tracks.length > 0 && tracks[currentIndex]) {
      fetchAndPlay(tracks[currentIndex].track).then(() => {
        audioRef.current?.play().catch(() => {});
      });
      scrollTrackIntoView(currentIndex);
    }
  }, [currentIndex, tracks.length]);

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

  function togglePlay() {
    if (!audioRef.current) return;
    if (audioRef.current.paused) {
      audioRef.current.play().catch(() => {});
    } else {
      audioRef.current.pause();
    }
  }

  function scrollTrackIntoView(index) {
    if (!trackListRef.current) return;
    const el = trackListRef.current.children[index];
    if (el) el.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
  }

  const currentItem = tracks[currentIndex];
  const currentTrack = currentItem?.track;
  const total = tracks.length;

  const navBtn = (disabled) => ({
    width: '56px',
    height: '56px',
    borderRadius: '50%',
    border: `1px solid ${disabled ? '#191919' : '#2e2e2e'}`,
    background: 'transparent',
    color: disabled ? '#222' : '#777',
    fontSize: '1rem',
    cursor: disabled ? 'default' : 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'color 0.15s ease, border-color 0.15s ease',
  });

  if (isLoading) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}>
        <p style={{ color: '#2a2a2a', fontSize: '0.78rem' }}>loading journey...</p>
      </div>
    );
  }

  if (tracks.length === 0) {
    return (
      <div style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: '1.5rem',
      }}>
        <p style={{ color: '#333', fontSize: '0.8rem' }}>No tracks in this journey.</p>
        <button
          onClick={onBack}
          style={{ background: 'none', border: 'none', color: '#444', cursor: 'pointer', fontSize: '0.75rem', letterSpacing: '0.08em' }}
        >
          ← BACK
        </button>
      </div>
    );
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      padding: 'calc(36px + 1.5rem) 1.5rem 3rem',
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
        justifyContent: 'center',
        zIndex: 20,
      }}>
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

      <audio
        ref={audioRef}
        style={{ display: 'none' }}
        onEnded={() => setIsPlaying(false)}
        onPlay={() => setIsPlaying(true)}
        onPause={() => setIsPlaying(false)}
      />

      {/* Back */}
      <div style={{ width: '100%', maxWidth: '300px', marginBottom: '1.5rem' }}>
        <button
          onClick={onBack}
          style={{
            background: 'none',
            border: 'none',
            color: '#3a3a3a',
            cursor: 'pointer',
            fontSize: '0.7rem',
            letterSpacing: '0.09em',
            padding: 0,
          }}
        >
          ← BACK
        </button>
      </div>

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
          onClick={togglePlay}
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
      <div style={{ width: '100%', maxWidth: '300px', marginBottom: '0.75rem' }}>
        <p style={{ fontSize: '1.1rem', fontWeight: '600', lineHeight: 1.25, marginBottom: '0.3rem' }}>
          <a
            href={currentTrack?.permalink_url}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'inherit', textDecoration: 'none' }}
          >
            {currentTrack?.title}
          </a>
        </p>
        <p style={{ color: '#666', fontSize: '0.875rem' }}>
          {currentTrack?.artist}
        </p>
      </div>

      {/* Position indicator */}
      <p style={{
        fontSize: '0.68rem',
        color: '#333',
        letterSpacing: '0.1em',
        marginBottom: '1.5rem',
        fontVariantNumeric: 'tabular-nums',
      }}>
        {currentIndex + 1} / {total}
      </p>

      {/* Nav buttons */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '2rem' }}>
        <button
          onClick={() => setCurrentIndex(i => i - 1)}
          disabled={currentIndex === 0}
          style={navBtn(currentIndex === 0)}
          aria-label="Previous"
        >
          ←
        </button>
        <button
          onClick={togglePlay}
          aria-label={isPlaying ? 'Pause' : 'Play'}
          style={{
            width: '56px',
            height: '56px',
            borderRadius: '50%',
            border: '1px solid #3a3a3a',
            background: 'transparent',
            color: '#f0f0f0',
            fontSize: '0.9rem',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            transition: 'border-color 0.15s ease',
          }}
        >
          {isPlaying ? '⏸' : '▶'}
        </button>
        <button
          onClick={() => setCurrentIndex(i => i + 1)}
          disabled={currentIndex === total - 1}
          style={navBtn(currentIndex === total - 1)}
          aria-label="Next"
        >
          →
        </button>
      </div>

      {/* Fork button */}
      <button
        onClick={() => onFork(journeyId)}
        style={{
          marginBottom: '1.5rem',
          padding: '0.55rem 1.75rem',
          background: 'transparent',
          border: '1px solid #c8873a',
          borderRadius: '2px',
          color: '#c8873a',
          fontSize: '0.72rem',
          letterSpacing: '0.1em',
          cursor: 'pointer',
        }}
      >
        FORK FROM HERE
      </button>

      {/* SC logo */}
      <a
        href="https://soundcloud.com"
        target="_blank"
        rel="noopener noreferrer"
        style={{ marginBottom: '2.5rem', display: 'block' }}
      >
        <img
          src={poweredBySoundCloud}
          alt="Powered by SoundCloud"
          style={{ height: '20px', opacity: 0.6 }}
        />
      </a>

      {/* Track list */}
      <div
        ref={trackListRef}
        style={{
          width: '100%',
          maxWidth: '480px',
          maxHeight: '320px',
          overflowY: 'auto',
          borderTop: '1px solid #111',
        }}
      >
        {tracks.map((item, idx) => (
          <div
            key={idx}
            onClick={() => setCurrentIndex(idx)}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              padding: '0.55rem 0.75rem',
              borderBottom: '1px solid #0e0e0e',
              cursor: 'pointer',
              background: idx === currentIndex ? '#111' : 'transparent',
            }}
          >
            <span style={{
              fontSize: '0.62rem',
              color: idx === currentIndex ? '#c8873a' : '#2a2a2a',
              width: '1.75rem',
              flexShrink: 0,
              textAlign: 'right',
              fontVariantNumeric: 'tabular-nums',
            }}>
              {item.position + 1}
            </span>
            <div style={{ minWidth: 0, flex: 1 }}>
              <p style={{
                fontSize: '0.78rem',
                color: idx === currentIndex ? '#e0e0e0' : '#444',
                margin: 0,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}>
                {item.track.title}
              </p>
              <p style={{
                fontSize: '0.68rem',
                color: idx === currentIndex ? '#666' : '#2a2a2a',
                margin: 0,
              }}>
                {item.track.artist}
              </p>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
