from __future__ import annotations

import math
from typing import Sequence

from db.models import ActionEnum, JourneyEvent, Track


def sigmoid(x: float, k: float = 1.0) -> float:
    return 1.0 / (1.0 + math.exp(-k * x))


class TrackScorer:
    GENRE_WEIGHT = 0.50
    RELATED_WEIGHT = 0.25
    CO_LIKE_WEIGHT = 0.15
    TRAJECTORY_WEIGHT = 0.10
    TRAJECTORY_WINDOW = 5

    def __init__(self, session_weight: float = 1.5) -> None:
        self.session_weight = session_weight

    def score(
        self,
        candidate_track: Track,
        genre_likes: dict,
        genre_dislikes: dict,
        recent_events: Sequence[JourneyEvent],
        global_track_quality: dict | None = None,
        journey_confidence: float = 1.0,
        co_like_boosts: dict | None = None,
        related_boosts: dict | None = None,
        liked_tracks_features: list[dict] | None = None,
    ) -> float:
        if liked_tracks_features is None:
            liked_tracks_features = []

        genre_score = self._genre_score(candidate_track, genre_likes, genre_dislikes)
        trajectory_score = self._trajectory_signal(recent_events)
        co_like_score = self._co_like_score(candidate_track, co_like_boosts)
        related_score = self._related_score(candidate_track, related_boosts)

        has_audio_data = (
            bool(liked_tracks_features) and
            candidate_track.audio_features is not None
        )

        if has_audio_data:
            audio_score = self._audio_similarity_score(candidate_track, liked_tracks_features)
            journey_score = (
                0.50 * audio_score
                + 0.25 * genre_score
                + 0.15 * related_score
                + 0.05 * co_like_score
                + 0.05 * trajectory_score
            )
        else:
            journey_score = (
                self.GENRE_WEIGHT * genre_score
                + self.RELATED_WEIGHT * related_score
                + self.CO_LIKE_WEIGHT * co_like_score
                + self.TRAJECTORY_WEIGHT * trajectory_score
            )

        if journey_confidence < 1.0 and global_track_quality:
            global_score = sigmoid(
                global_track_quality.get(candidate_track.id, 0), k=0.5
            )
            return (journey_confidence * journey_score) + ((1.0 - journey_confidence) * global_score)

        return journey_score

    def _genre_score(self, candidate: Track, genre_likes: dict, genre_dislikes: dict) -> float:
        candidate_genre = (candidate.genre or "").strip().lower()
        if not candidate_genre:
            return 0.4

        likes = genre_likes.get(candidate_genre, 0)
        dislikes = genre_dislikes.get(candidate_genre, 0)
        total = likes + dislikes

        if total == 0:
            return 0.5

        raw_ratio = likes / total
        confidence = min(1.0, total / 5.0)
        genre_score = 0.5 + (raw_ratio - 0.5) * confidence
        return max(0.02, min(0.95, genre_score))

    def _trajectory_signal(self, recent_events: Sequence[JourneyEvent]) -> float:
        window = list(recent_events)[-self.TRAJECTORY_WINDOW:]
        if not window:
            return 0.5

        likes = sum(1 for e in window if e.action == ActionEnum.like)
        dislikes = sum(1 for e in window if e.action == ActionEnum.dislike)
        skips = sum(1 for e in window if e.action == ActionEnum.skip)

        if likes >= 3:
            boost = min(0.4, 0.1 * self.session_weight)
            return min(1.0, 0.5 + boost)

        if (dislikes + skips) >= 3:
            return 0.5

        return 0.5

    def _co_like_score(self, candidate: Track, co_like_boosts: dict | None) -> float:
        if not co_like_boosts or candidate.id not in co_like_boosts:
            return 0.5
        return sigmoid(co_like_boosts[candidate.id], k=2.0)

    def _related_score(self, candidate: Track, related_boosts: dict | None) -> float:
        if not related_boosts or candidate.id not in related_boosts:
            return 0.0
        return sigmoid(related_boosts[candidate.id], k=1.0)

    def _audio_similarity_score(
        self,
        candidate: object,
        liked_tracks_features: list[dict],
    ) -> float:
        """
        Compute average audio similarity between candidate and
        all liked tracks that have audio features.
        Returns 0.5 (neutral) if no data available.
        """
        if not liked_tracks_features:
            return 0.5

        candidate_features = candidate.audio_features
        if not candidate_features:
            return 0.5

        # Excluded: valence, instrumental_probability, mood_aggressive,
        # mood_happy, mood_relaxed, mood_sad -- all 0.5 placeholders until
        # Essentia SVM models are installed. 'arousal' is excluded because
        # it duplicates energy (both hold average_loudness).
        # (key, divisor) -- divide raw value by divisor, cap at 1.0
        SIMILARITY_DIMS = [
            ('energy', 1.0),                  # average_loudness, 0-1
            ('danceability', 3.0),            # essentia danceability, ~0-3
            ('bpm', 200.0),                   # beats per minute
            ('spectral_centroid', 5000.0),    # Hz, typically 500-5000
            ('spectral_rolloff', 10000.0),    # Hz, typically 1000-10000
            ('zero_crossing_rate', 0.3),      # typically 0-0.3
            ('dynamic_complexity', 10.0),     # typically 0-10
            ('key_strength', 1.0),            # 0-1
            ('chords_strength', 1.0),         # 0-1
            ('beat_loudness', 1.0),           # 0-1 range typically
        ]

        def norm(key: str, divisor: float, features: dict) -> float | None:
            try:
                val = float(features.get(key, 0.0))
            except (TypeError, ValueError):
                return None
            return min(1.0, max(0.0, val / divisor))

        similarities = []
        for liked_features in liked_tracks_features:
            diffs = []
            for key, divisor in SIMILARITY_DIMS:
                a = norm(key, divisor, candidate_features)
                b = norm(key, divisor, liked_features)
                if a is None or b is None:
                    continue
                diffs.append((a - b) ** 2)
            if not diffs:
                continue
            distance = sum(diffs) ** 0.5
            max_distance = len(diffs) ** 0.5
            similarities.append(1.0 - (distance / max_distance))

        if not similarities:
            return 0.5

        return sum(similarities) / len(similarities)
