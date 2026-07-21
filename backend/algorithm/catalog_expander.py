from __future__ import annotations

import random
import time
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import ActionEnum, JourneyEvent, Track
from soundcloud.client import SoundCloudClient
from soundcloud.client import Track as SCTrack

DIVERSE_TAGS = [
    "lo-fi", "indie", "soul", "jazz", "hip-hop",
    "electronic", "ambient", "folk", "r&b", "funk",
    "experimental", "bedroom pop", "chillwave", "neo-soul",
    "acoustic", "alternative", "post-rock", "synthpop",
    "shoegaze", "dream pop", "psychedelic", "garage rock",
    "classical", "piano", "instrumental", "bossa nova",
    "afrobeat", "reggae", "trip hop", "boom bap",
]


class CatalogExpander:
    def __init__(self, db: Session, sc_client: SoundCloudClient) -> None:
        self.db = db
        self.sc_client = sc_client
        self._known_ids: set[int] = self._load_known_ids()

    def _load_known_ids(self) -> set[int]:
        rows = self.db.query(Track.soundcloud_id).all()
        return {r[0] for r in rows}

    def run(
        self,
        max_from_liked: int = 300,
        max_from_tags: int = 200,
        lookback_days: int = 7,
    ) -> int:
        added_from_liked = self._expand_from_liked(max_from_liked, lookback_days)
        added_from_tags = self._expand_from_tags(max_from_tags)
        self.db.commit()
        total = added_from_liked + added_from_tags
        print(f"[expander] done. {added_from_liked} from liked, {added_from_tags} from tags.")
        return total

    def _expand_from_liked(self, max_tracks: int, lookback_days: int) -> int:
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)

        popular_liked = (
            self.db.query(JourneyEvent.track_id, func.count().label("like_count"))
            .filter(
                JourneyEvent.action == ActionEnum.like,
                JourneyEvent.timestamp >= cutoff,
            )
            .group_by(JourneyEvent.track_id)
            .order_by(func.count().desc())
            .limit(20)
            .all()
        )

        added = 0
        for row in popular_liked:
            if added >= max_tracks:
                break
            track = self.db.query(Track).filter(Track.id == row.track_id).first()
            if not track:
                continue
            try:
                related = self.sc_client.get_related_tracks(track.soundcloud_id, limit=20)
                for sc_track in related:
                    if added >= max_tracks:
                        break
                    if self._upsert_track(sc_track):
                        added += 1
                time.sleep(0.5)
            except Exception as e:
                print(f"[expander] related fetch failed for {track.soundcloud_id}: {e}")

        return added

    def _expand_from_tags(self, max_tracks: int) -> int:
        selected_tags = random.sample(DIVERSE_TAGS, min(10, len(DIVERSE_TAGS)))
        added = 0

        for tag in selected_tags:
            if added >= max_tracks:
                break
            try:
                offset = random.randint(0, 200)
                tracks = self.sc_client.get_tracks_by_tag(tag, limit=20, offset=offset)
                for sc_track in tracks:
                    if added >= max_tracks:
                        break
                    if self._upsert_track(sc_track):
                        added += 1
                time.sleep(0.5)
            except Exception as e:
                print(f"[expander] tag fetch failed for {tag}: {e}")

        return added

    def _upsert_track(self, sc_track: SCTrack) -> bool:
        if sc_track.id in self._known_ids:
            return False
        if not sc_track.streamable or sc_track.access in ("preview", "blocked"):
            return False
        record = Track(
            soundcloud_id=sc_track.id,
            title=sc_track.title,
            artist=sc_track.artist,
            artist_sc_id=sc_track.artist_id,
            duration_ms=sc_track.duration_ms,
            permalink_url=sc_track.permalink_url,
            artwork_url=sc_track.artwork_url,
            sc_play_count=sc_track.play_count,
            sc_likes_count=sc_track.likes_count,
            tags_raw=sc_track.tags_raw,
            genre=sc_track.genre,
            streamable=sc_track.streamable,
        )
        try:
            self.db.add(record)
            self.db.flush()
            self._known_ids.add(sc_track.id)
            return True
        except Exception:
            self.db.rollback()
            return False
