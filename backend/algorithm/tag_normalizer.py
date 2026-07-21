from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import ActionEnum, JourneyEvent, TagWeight, Track

_ACTION_SCORES: dict[ActionEnum, float] = {
    ActionEnum.like: 1.0,
    ActionEnum.skip: -0.2,
    ActionEnum.dislike: -3.0,
}

_EMA_ALPHA = 0.2


class TagNormalizer:
    def __init__(self, db: Session) -> None:
        self.db = db

    def run(self, min_interactions: int = 5) -> None:
        qualifying_tracks = (
            self.db.query(Track)
            .join(JourneyEvent, JourneyEvent.track_id == Track.id)
            .group_by(Track.id)
            .having(func.count(JourneyEvent.id) >= min_interactions)
            .all()
        )

        tracks_processed = 0
        tags_updated = 0

        for track in qualifying_tracks:
            tags_updated += self._process_track(track)
            tracks_processed += 1

        print(
            f"TagNormalizer: processed {tracks_processed} tracks, "
            f"updated {tags_updated} tag weights"
        )

    def normalize_single_track(self, track_id: int) -> None:
        track = self.db.query(Track).filter(Track.id == track_id).first()
        if track is None:
            print(f"TagNormalizer: track {track_id} not found")
            return
        updated = self._process_track(track)
        print(f"TagNormalizer: track {track_id} — updated {updated} tag weights")

    def _process_track(self, track: Track) -> int:
        events = (
            self.db.query(JourneyEvent)
            .filter(JourneyEvent.track_id == track.id)
            .all()
        )
        if not events:
            return 0

        event_count = len(events)
        raw_score = sum(_ACTION_SCORES.get(e.action, 0.0) for e in events)
        normalized_score = raw_score / event_count

        tags: list[str] = track.tags_raw or []
        now = datetime.utcnow()
        tags_normalized: dict[str, float] = {}

        for tag in tags:
            tw = (
                self.db.query(TagWeight)
                .filter(TagWeight.track_id == track.id, TagWeight.tag == tag)
                .first()
            )
            if tw is None:
                tw = TagWeight(track_id=track.id, tag=tag, weight=0.0, sample_count=0)
                self.db.add(tw)

            tw.weight = (1.0 - _EMA_ALPHA) * tw.weight + _EMA_ALPHA * normalized_score
            tw.sample_count += event_count
            tw.last_updated = now
            tags_normalized[tag] = tw.weight

        track.tags_normalized = tags_normalized
        self.db.commit()

        return len(tags)
