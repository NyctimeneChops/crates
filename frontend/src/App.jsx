import { useState } from 'react';
import { getToken } from './api';
import * as api from './api';
import Auth from './components/Auth';
import Home from './components/Home';
import Player from './components/Player';
import MyJourneys from './components/MyJourneys';
import WitnessPlayer from './components/WitnessPlayer';
import Feed from './components/Feed';

export default function App() {
  const [view, setView] = useState('home');
  const [isGuest, setIsGuest] = useState(!getToken());
  const [guestLikeCount, setGuestLikeCount] = useState(0);
  const [showSignUpPrompt, setShowSignUpPrompt] = useState(false);
  const [previousView, setPreviousView] = useState('home');
  const [feedKey, setFeedKey] = useState(0);
  const [journey, setJourney] = useState(null);
  const [initialTrack, setInitialTrack] = useState(null);
  const [witnessJourneyId, setWitnessJourneyId] = useState(null);
  const [witnessSource, setWitnessSource] = useState('myjourneys');

  function handleAuthSuccess() {
    setIsGuest(false);
    setGuestLikeCount(0);
    setShowSignUpPrompt(false);
    setView('home');
  }

  function handleLogout() {
    localStorage.removeItem('crates_token');
    setIsGuest(true);
    setView('home');
    // reset any user-specific state (journey, initialTrack, etc.)
    setJourney(null);
    setInitialTrack(null);
    setWitnessJourneyId(null);
    setGuestLikeCount(0);
    setShowSignUpPrompt(false);
  }

  function handleGuestLike() {
    const next = guestLikeCount + 1;
    setGuestLikeCount(next);
    if (next >= 5) {
      setShowSignUpPrompt(true);
    }
  }

  function handleJourneyStart(data) {
    setJourney({ journey_id: data.journey_id, session_id: data.session_id });
    setInitialTrack(data.first_track);
    setView('player');
  }

  function handleEnd() {
    setJourney(null);
    setInitialTrack(null);
    setView('home');
  }

  async function handleFork(journeyId) {
    try {
      const data = await api.forkJourney(journeyId);
      setJourney({ journey_id: data.journey_id, session_id: data.session_id });
      setInitialTrack(data.first_track);
      setView('player');
    } catch (err) {
      console.error('Fork failed:', err);
    }
  }

  function handleContinue(journeyData) {
    setJourney(journeyData);
    setInitialTrack(journeyData.first_track);
    setView('player');
  }

  function handleForkFromPosition(data) {
    setJourney({ journey_id: data.journey_id, session_id: data.session_id });
    setInitialTrack(data.first_track);
    setView('player');
  }

  if (view === 'auth') {
    return <Auth onSuccess={handleAuthSuccess} />;
  }

  if (view === 'player') {
    return (
      <Player
        journey={journey}
        initialTrack={initialTrack}
        onEnd={handleEnd}
        onDiscover={isGuest ? () => setShowSignUpPrompt(true) : () => { setPreviousView(view); setFeedKey(k => k + 1); setView('feed'); }}
        onMyJourneys={isGuest ? () => setShowSignUpPrompt(true) : () => { setPreviousView(view); setView('myjourneys'); }}
        onHome={() => setView('home')}
        isGuest={isGuest}
        onGuestLike={handleGuestLike}
        showSignUpPrompt={showSignUpPrompt}
        onSignUp={() => { setShowSignUpPrompt(false); setView('auth'); }}
        onDismissPrompt={() => { setShowSignUpPrompt(false); setGuestLikeCount(0); }}
      />
    );
  }

  if (view === 'myjourneys') {
    return (
      <MyJourneys
        onBack={() => setView(previousView)}
        onWitness={(journeyId) => {
          setWitnessJourneyId(journeyId);
          setWitnessSource('myjourneys');
          setView('witness');
        }}
        onFork={handleForkFromPosition}
        onContinue={handleContinue}
        onHome={() => setView('home')}
      />
    );
  }

  if (view === 'witness') {
    return (
      <WitnessPlayer
        journeyId={witnessJourneyId}
        isOwner={witnessSource === 'myjourneys'}
        onBack={() => setView(witnessSource)}
        onFork={handleFork}
        onHome={() => setView('home')}
      />
    );
  }

  if (view === 'feed') {
    return (
      <Feed
        key={feedKey}
        onBack={() => setView(previousView)}
        onWitness={(journeyId) => {
          setWitnessJourneyId(journeyId);
          setWitnessSource('feed');
          setView('witness');
        }}
        onFork={handleFork}
        onHome={() => setView('home')}
      />
    );
  }

  return (
    <Home
      onStart={handleJourneyStart}
      onMyJourneys={isGuest ? null : () => { setPreviousView(view); setView('myjourneys'); }}
      onDiscover={isGuest ? null : () => { setPreviousView(view); setFeedKey(k => k + 1); setView('feed'); }}
      isGuest={isGuest}
      onSignIn={() => setView('auth')}
      onLogout={handleLogout}
    />
  );
}
