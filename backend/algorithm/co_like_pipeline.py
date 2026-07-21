from __future__ import annotations

from itertools import combinations

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import ActionEnum, JourneyEvent, TrackCoLike


class CoLikePipeline:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run(self, min_journey_likes: int = 2) -> None:
        qualifying_journeys = (
            self.db.query(JourneyEvent.journey_id)
            .filter(JourneyEvent.action == ActionEnum.like)
            .group_by(JourneyEvent.journey_id)
            .having(func.count() >= min_journey_likes)
            .all()
        )
        journey_ids = [j.journey_id for j in qualifying_journeys]

        journeys_processed = 0
        pairs_updated = 0

        for journey_id in journey_ids:
            liked_events = (
                self.db.query(JourneyEvent)
                .filter(
                    JourneyEvent.journey_id == journey_id,
                    JourneyEvent.action == ActionEnum.like,
                )
                .order_by(JourneyEvent.position)
                .all()
            )

            for event_a, event_b in combinations(liked_events, 2):
                proximity = 1.0 / (1.0 + abs(event_b.position - event_a.position))
                self._upsert_pair(event_a.track_id, event_b.track_id, proximity)
                self._upsert_pair(event_b.track_id, event_a.track_id, proximity)
                pairs_updated += 2

            self.db.commit()
            journeys_processed += 1

        print(
            f"CoLikePipeline: processed {journeys_processed} journeys, "
            f"{pairs_updated} pairs updated"
        )

    def _upsert_pair(self, track_a_id: int, track_b_id: int, proximity: float) -> None:
        existing = (
            self.db.query(TrackCoLike)
            .filter(
                TrackCoLike.track_a_id == track_a_id,
                TrackCoLike.track_b_id == track_b_id,
            )
            .first()
        )
        if existing:
            existing.co_like_score = 0.8 * existing.co_like_score + 0.2 * proximity
            existing.sample_count += 1
        else:
            self.db.add(TrackCoLike(
                track_a_id=track_a_id,
                track_b_id=track_b_id,
                co_like_score=proximity,
                sample_count=1,
            ))
