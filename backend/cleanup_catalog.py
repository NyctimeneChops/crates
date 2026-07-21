from dotenv import load_dotenv
load_dotenv()
import os
import psycopg

conn_str = os.environ['DATABASE_URL'].replace('postgresql+psycopg://', 'postgresql://')

EXCLUDE_KEYWORDS = [
    'white noise', 'sleep sounds', 'relaxing', 'meditation',
    'compilation', 'podcast', 'episode', 'audiobook',
    'ambient loop', 'nature sounds', 'rain sounds',
    'thunderstorm', 'binaural', 'asmr', 'guided',
]

with psycopg.connect(conn_str, autocommit=True) as conn:
    with conn.cursor() as cur:
        cur.execute("SELECT id, title, duration_ms FROM tracks")
        rows = cur.fetchall()

to_delete = []
for track_id, title, duration_ms in rows:
    duration_ms = duration_ms or 0
    title_lower = (title or '').lower()
    too_short = duration_ms < 60_000
    too_long = duration_ms > 900_000
    bad_keyword = any(kw in title_lower for kw in EXCLUDE_KEYWORDS)
    if too_short or too_long or bad_keyword:
        reason = 'too_short' if too_short else 'too_long' if too_long else 'keyword'
        to_delete.append((track_id, title, duration_ms, reason))

print(f"Found {len(to_delete)} tracks to delete:")
for track_id, title, duration_ms, reason in to_delete[:20]:
    mins = duration_ms // 60000
    print(f"  [{reason}] {title[:60]} ({mins}min)")
if len(to_delete) > 20:
    print(f"  ... and {len(to_delete) - 20} more")

confirm = input(f"\nDelete {len(to_delete)} tracks? (yes/no): ")
if confirm.lower() != 'yes':
    print("Cancelled.")
else:
    ids = [str(t[0]) for t in to_delete]
    ids_str = ','.join(ids)
    with psycopg.connect(conn_str, autocommit=True) as conn:
        with conn.cursor() as cur:
            # Find journeys seeded by these tracks
            cur.execute(f"SELECT id FROM journeys WHERE seed_track_id IN ({ids_str})")
            journey_ids = [str(r[0]) for r in cur.fetchall()]
            
            if journey_ids:
                jids = ','.join(journey_ids)
                cur.execute(f"DELETE FROM journey_events WHERE journey_id IN ({jids})")
                cur.execute(f"DELETE FROM sessions WHERE journey_id IN ({jids})")
                cur.execute(f"DELETE FROM journeys WHERE id IN ({jids})")
            
            cur.execute(f"DELETE FROM track_related WHERE source_id IN ({ids_str}) OR related_id IN ({ids_str})")
            cur.execute(f"DELETE FROM track_co_likes WHERE track_a_id IN ({ids_str}) OR track_b_id IN ({ids_str})")
            cur.execute(f"DELETE FROM tag_weights WHERE track_id IN ({ids_str})")
            cur.execute(f"DELETE FROM journey_events WHERE track_id IN ({ids_str})")
            cur.execute(f"DELETE FROM tracks WHERE id IN ({ids_str})")
    print(f"Deleted {len(to_delete)} tracks.")