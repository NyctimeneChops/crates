from __future__ import annotations

import argparse
import time
from collections import deque

from sqlalchemy.orm import Session

from db.models import Track as TrackModel
from soundcloud.client import SoundCloudClient, Track

SEED_TAGS = [
    # Lo-fi / chill
    "lo-fi", "lofi", "chillwave", "chillhop",
    # Indie
    "indie", "indie rock", "indie pop", "bedroom pop",
    # Soul / R&B
    "soul", "neo-soul", "r&b", "funk",
    # Jazz
    "jazz", "jazz hop", "smooth jazz", "jazz fusion",
    # Electronic
    "electronic", "ambient", "synth", "synthwave",
    "downtempo", "trip hop",
    # Hip hop
    "hip-hop", "underground hip hop", "boom bap",
    # Folk / acoustic
    "folk", "acoustic", "singer-songwriter", "indie folk",
    # Rock
    "alternative", "post-rock", "shoegaze", "dream pop",
    "psychedelic", "garage rock",
    # Classical / instrumental
    "classical", "piano", "instrumental", "orchestral",
    # World / other
    "bossa nova", "latin", "afrobeat", "reggae",
    # Experimental
    "experimental", "avant-garde", "noise",
]

SEED_QUERIES = [
    "underground jazz 2024",
    "indie folk acoustic",
    "neo soul independent",
    "ambient electronic instrumental",
    "boom bap hip hop underground",
    "post rock instrumental",
    "shoegaze dream pop",
    "bossa nova jazz",
    "afrobeat independent artist",
    "classical piano original",
    "psychedelic rock independent",
    "synthwave electronic",
    "bedroom pop lo fi",
    "singer songwriter acoustic",
    "funk soul independent",
    "trip hop downtempo",
    "reggae independent artist",
    "experimental avant garde",
    "garage rock indie",
    "latin jazz fusion",
]

EXCLUDE_KEYWORDS = [
    'white noise', 'sleep sounds', 'relaxing', 'meditation',
    'compilation', 'podcast', 'episode', 'audiobook',
    'ambient loop', 'nature sounds', 'rain sounds',
    'thunderstorm', 'binaural', 'asmr', 'guided',
]


def _is_valid_track(sc_track) -> bool:
    """
    Returns True if track should be indexed.
    Filters out non-music content.
    """
    # Duration filter: 60 seconds to 15 minutes
    duration_ms = sc_track.duration_ms or 0
    if duration_ms < 60_000 or duration_ms > 900_000:
        return False

    # Keyword filter on title
    title_lower = (sc_track.title or '').lower()
    for keyword in EXCLUDE_KEYWORDS:
        if keyword in title_lower:
            return False

    return True


class TrackIndexer:
    def __init__(self, client: SoundCloudClient, db: Session) -> None:
        self.client = client
        self.db = db
        self._known_ids: set[int] = self._load_existing_ids()

    def _load_existing_ids(self) -> set[int]:
        rows = self.db.query(TrackModel.soundcloud_id).all()
        return {r[0] for r in rows}

    def _save_track(self, track: Track) -> None:
        if track.id in self._known_ids or not track.streamable or track.access in ("preview", "blocked"):
            return
        record = TrackModel(
            soundcloud_id=track.id,
            title=track.title,
            artist=track.artist,
            artist_sc_id=track.artist_id,
            duration_ms=track.duration_ms,
            permalink_url=track.permalink_url,
            artwork_url=track.artwork_url,
            sc_play_count=track.play_count,
            sc_likes_count=track.likes_count,
            tags_raw=track.tags_raw,
            genre=track.genre,
            streamable=track.streamable,
        )
        try:
            self.db.add(record)
            self.db.commit()
            self._known_ids.add(track.id)
        except Exception:
            self.db.rollback()
            raise

    def _upsert_track(self, sc_track: Track) -> bool:
        if sc_track.id in self._known_ids:
            return False
        if not sc_track.streamable or sc_track.access in ("preview", "blocked"):
            return False
        if not _is_valid_track(sc_track):
            return False
        record = TrackModel(
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

    def upsert_track(self, sc_track: Track) -> bool:
        return self._upsert_track(sc_track)

    def run(
        self,
        max_tracks: int = 200,
        expand_related: bool = True,
        related_depth: int = 2,
    ) -> None:
        queue: deque[tuple[int, int]] = deque()  # (soundcloud_id, depth)
        indexed = 0

        def _enqueue(tracks: list[Track], depth: int) -> None:
            for t in tracks:
                if t.id not in self._known_ids and t.streamable:
                    queue.append((t.id, depth))

        for tag in SEED_TAGS:
            if indexed >= max_tracks:
                break
            try:
                _enqueue(self.client.get_tracks_by_tag(tag, limit=20), 0)
                time.sleep(0.5)
            except Exception as exc:
                print(f"[indexer] tag '{tag}' failed: {exc}")

        for query in SEED_QUERIES:
            if indexed >= max_tracks:
                break
            try:
                _enqueue(self.client.search_tracks(query, limit=20), 0)
                time.sleep(0.5)
            except Exception as exc:
                print(f"[indexer] query '{query}' failed: {exc}")

        while queue and indexed < max_tracks:
            sc_id, depth = queue.popleft()
            if sc_id in self._known_ids:
                continue
            try:
                track = self.client.get_track(sc_id)
                self._save_track(track)
                indexed += 1
                print(f"[indexer] {indexed}/{max_tracks}: {track.artist} - {track.title}")

                if expand_related and depth < related_depth:
                    time.sleep(0.3)
                    _enqueue(self.client.get_related_tracks(sc_id, limit=10), depth + 1)

                time.sleep(0.2)
            except Exception as exc:
                print(f"[indexer] track {sc_id} failed: {exc}")

        print(f"[indexer] done. {indexed} tracks indexed.")

    def index_single(self, soundcloud_url_or_id: str) -> None:
        if soundcloud_url_or_id.startswith("http"):
            data = self.client.resolve(soundcloud_url_or_id)
            track = Track.from_api(data)
        else:
            track = self.client.get_track(int(soundcloud_url_or_id))
        self._save_track(track)
        print(f"[indexer] indexed: {track.artist} - {track.title}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Index SoundCloud tracks into the DB")
    parser.add_argument("--max", type=int, default=200, help="Max tracks to index")
    parser.add_argument("--no-related", action="store_true", help="Skip related track expansion")
    parser.add_argument("--depth", type=int, default=2, help="Related expansion depth")
    parser.add_argument("--url", type=str, default=None, help="Index a single track by URL or ID")
    args = parser.parse_args()

    from db.connection import get_db

    with SoundCloudClient() as client, get_db() as db:
        indexer = TrackIndexer(client, db)
        if args.url:
            indexer.index_single(args.url)
        else:
            indexer.run(
                max_tracks=args.max,
                expand_related=not args.no_related,
                related_depth=args.depth,
            )


if __name__ == "__main__":
    main()
