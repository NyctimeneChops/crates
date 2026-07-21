const BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const TOKEN_KEY = 'crates_token';

export function setToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

export function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

export function authHeaders() {
  const token = getToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function request(method, path, body) {
  const res = await fetch(`${BASE_URL}${path}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
    },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed (${res.status})`);
  }

  return res.json();
}

export const register = (email, password, username) =>
  request('POST', '/auth/register', { email, password, username });

export const login = async (email, password) => {
  const data = await request('POST', '/auth/login', { email, password });
  if (data.access_token) setToken(data.access_token);
  return data;
};

export const startJourney = async () => {
  const now = new Date();
  const day = now.getDate();
  const suffix = [11, 12, 13].includes(day) ? 'th'
    : { 1: 'st', 2: 'nd', 3: 'rd' }[day % 10] || 'th';
  const month = now.toLocaleString('default', { month: 'long' });
  const dateStr = `${month} ${day}${suffix}`;
  console.log('Journey date generated:', dateStr, 'Local time:', now.toString());

  const res = await fetch(`${BASE_URL}/journeys/start`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${getToken()}`,
    },
    body: JSON.stringify({ name: dateStr }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed (${res.status})`);
  }
  return res.json();
};

export const nextTrack = (journeyId, sessionId, trackId, action, listenDurationMs) =>
  request('POST', `/journeys/${journeyId}/next`, {
    session_id: sessionId,
    track_id: trackId,
    action,
    listen_duration_ms: listenDurationMs ?? null,
  });

export const logEvent = (journeyId, sessionId, trackId, action, listenDurationMs) =>
  request('POST', `/journeys/${journeyId}/event`, {
    session_id: sessionId,
    track_id: trackId,
    action,
    listen_duration_ms: listenDurationMs ?? null,
  });

export const getJourney = (journeyId) =>
  request('GET', `/journeys/${journeyId}`);

export const endJourney = (journeyId) =>
  request('POST', `/journeys/${journeyId}/end`);

export const publishJourney = (journeyId) =>
  request('POST', `/journeys/${journeyId}/publish`);

export const forkJourney = (journeyId) =>
  request('POST', `/journeys/${journeyId}/fork`);

export const forkFromPosition = (journeyId, position) =>
  request('POST', `/journeys/${journeyId}/fork`, { fork_position: position });

export const continueJourney = (journeyId) =>
  request('POST', `/journeys/${journeyId}/continue`);

export const getMyJourneys = (page = 1) =>
  request('GET', `/journeys/mine?page=${page}`);

export const getPublicJourney = (journeyId) =>
  request('GET', `/journeys/public/${journeyId}`);

export const getWitnessTracks = (journeyId) =>
  request('GET', `/journeys/public/${journeyId}/tracks`);

export const getJourneyTracks = (journeyId) =>
  request('GET', `/journeys/${journeyId}/tracks`);

export const getTracklist = (journeyId) =>
  request('GET', `/journeys/${journeyId}/tracklist`);

export const renameJourney = (journeyId, name) =>
  request('PATCH', `/journeys/${journeyId}/name`, { name });

export const deleteJourney = (journeyId) =>
  request('DELETE', `/journeys/${journeyId}`);

export const searchTracks = async (q) => {
  const res = await fetch(`${BASE_URL}/tracks/search?q=${encodeURIComponent(q)}&limit=10`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed (${res.status})`);
  }
  return res.json();
};

export async function startGuestJourney() {
  const res = await fetch(`${BASE_URL}/journeys/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({}),
  });
  return res.json();
}

export async function guestNextTrack(journeyId, sessionId, trackId, action, listenDurationMs) {
  const res = await fetch(`${BASE_URL}/journeys/${journeyId}/next`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      session_id: sessionId,
      track_id: trackId,
      action,
      listen_duration_ms: listenDurationMs,
    }),
  });
  return res.json();
}

export const getFeed = (limit = 20, offset = 0) => {
  return fetch(`${BASE_URL}/journeys/feed?limit=${limit}&offset=${offset}`, {
    headers: { 'Content-Type': 'application/json' },
  }).then(async res => {
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || `Request failed (${res.status})`);
    }
    return res.json();
  });
};
