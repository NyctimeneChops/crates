from __future__ import annotations

import math
import random
from dataclasses import dataclass

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from algorithm.scorer import TrackScorer
from db.models import (
    ActionEnum,
    JourneyEvent,
    TagWeight,
    Track,
    TrackCoLike,
    TrackRelated,
)
from soundcloud.client import SoundCloudClient


def softmax(scores: list[float], temperature: float = 1.0) -> list[float]:
    if not scores:
        return []
    scaled = [s / temperature for s in scores]
    m = max(scaled)
    exps = [math.exp(s - m) for s in scaled]
    total = sum(exps)
    return [e / total for e in exps]


@dataclass
class JourneyProfile:
    genre_likes: dict
    genre_dislikes: dict
    heard_track_ids: list
    disliked_track_ids: list



class NextTrackEngine:
    CANDIDATE_POOL = 50
    HISTORY_WINDOW = 20
    SESSION_WINDOW = 5
    SAMPLE_TOP_N = 10

    def __init__(self, db: Session, sc_client: SoundCloudClient) -> None:
        self.db = db
        self.sc_client = sc_client
        self.scorer = TrackScorer()

    def get_next_track(self, user_id: int, journey_id: int, session_id: int) -> Track:
        journey_events = (
            self.db.query(JourneyEvent)
            .options(joinedload(JourneyEvent.track))
            .filter(JourneyEvent.journey_id == journey_id)
            .order_by(JourneyEvent.position)
            .all()
        )

        genre_likes: dict[str, int] = {}
        genre_dislikes: dict[str, int] = {}
        heard_track_ids: list[int] = []
        disliked_track_ids: list[int] = []

        for event in journey_events:
            heard_track_ids.append(event.track_id)
            genre = (getattr(event.track, "genre", None) or "").strip().lower()
            if event.action == ActionEnum.like:
                if genre:
                    genre_likes[genre] = genre_likes.get(genre, 0) + 1
            elif event.action == ActionEnum.dislike:
                disliked_track_ids.append(event.track_id)
                if genre:
                    genre_dislikes[genre] = genre_dislikes.get(genre, 0) + 1
            elif event.action == ActionEnum.skip:
                if genre:
                    genre_dislikes[genre] = genre_dislikes.get(genre, 0) + 1

        profile = JourneyProfile(
            genre_likes=genre_likes,
            genre_dislikes=genre_dislikes,
            heard_track_ids=heard_track_ids,
            disliked_track_ids=disliked_track_ids,
        )

        global_track_scores: dict[int, list[float]] = {}
        for row in self.db.query(TagWeight).filter(TagWeight.sample_count >= 3).all():
            global_track_scores.setdefault(row.track_id, []).append(row.weight)
        global_track_quality: dict[int, float] = {
            track_id: sum(weights) / len(weights)
            for track_id, weights in global_track_scores.items()
        }

        num_events = len(journey_events)
        journey_confidence = min(1.0, num_events / 20.0)

        liked_events = [e for e in journey_events if e.action == ActionEnum.like]
        co_like_boosts: dict[int, float] = {}
        if liked_events:
            liked_track_ids = [e.track_id for e in liked_events]
            co_like_rows = (
                self.db.query(TrackCoLike)
                .filter(TrackCoLike.track_a_id.in_(liked_track_ids))
                .all()
            )
            current_position = num_events
            for row in co_like_rows:
                source_event = next(
                    (e for e in liked_events if e.track_id == row.track_a_id), None
                )
                if source_event is None:
                    continue
                proximity = 1.0 / (1.0 + abs(current_position - source_event.position))
                boost = row.co_like_score * proximity
                co_like_boosts[row.track_b_id] = co_like_boosts.get(row.track_b_id, 0.0) + boost

        related_boosts: dict[int, float] = {}
        if liked_events:
            liked_track_ids_rel = [e.track_id for e in liked_events]
            related_rows = (
                self.db.query(TrackRelated)
                .filter(TrackRelated.source_id.in_(liked_track_ids_rel))
                .all()
            )
            for row in related_rows:
                source_event = next(
                    (e for e in liked_events if e.track_id == row.source_id),
                    None,
                )
                if source_event:
                    recency = (source_event.position + 1) / (len(journey_events) + 1)
                    related_boosts[row.related_id] = (
                        related_boosts.get(row.related_id, 0.0) + recency
                    )

        liked_tracks_features = [
            event.track.audio_features
            for event in journey_events
            if (
                event.action == ActionEnum.like
                and event.track
                and event.track.audio_features
            )
        ]

        session_events = journey_events[-self.SESSION_WINDOW:]

        candidates = self._get_candidates(profile, journey_events)

        if not candidates:
            candidates = (
                self.db.query(Track)
                .filter(Track.streamable.is_(True))
                .order_by(func.random())
                .limit(self.CANDIDATE_POOL)
                .all()
            )

        if not candidates:
            raise RuntimeError("No candidate tracks available in the database")

        scores = [
            self.scorer.score(
                c,
                genre_likes=profile.genre_likes,
                genre_dislikes=profile.genre_dislikes,
                recent_events=session_events,
                global_track_quality=global_track_quality,
                journey_confidence=journey_confidence,
                co_like_boosts=co_like_boosts,
                related_boosts=related_boosts,
                liked_tracks_features=liked_tracks_features,
            )
            for c in candidates
        ]

        top_n = min(self.SAMPLE_TOP_N, len(candidates))
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_n]
        top_candidates = [candidates[i] for i in top_indices]
        top_scores = [scores[i] for i in top_indices]

        probs = softmax(top_scores, temperature=0.4)
        return random.choices(top_candidates, weights=probs, k=1)[0]

    def _get_candidates(
        self,
        profile: JourneyProfile,
        journey_events: list[JourneyEvent],
    ) -> list[Track]:
        exclude_ids = list(set(profile.heard_track_ids) | set(profile.disliked_track_ids))

        q = self.db.query(Track).filter(Track.streamable.is_(True))
        if exclude_ids:
            q = q.filter(~Track.id.in_(exclude_ids))

        return q.order_by(func.random()).limit(self.CANDIDATE_POOL).all()

    def log_event(
        self,
        journey_id: int,
        track_id: int,
        position: int,
        action: str,
        listen_duration_ms: int | None = None,
    ) -> JourneyEvent:
        event = JourneyEvent(
            journey_id=journey_id,
            track_id=track_id,
            position=position,
            action=ActionEnum(action),
            listen_duration_ms=listen_duration_ms,
        )
        self.db.add(event)
        self.db.commit()
        return event
