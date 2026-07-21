from dotenv import load_dotenv
load_dotenv()
import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS track_co_likes (
            id SERIAL PRIMARY KEY,
            track_a_id INTEGER NOT NULL REFERENCES tracks(id),
            track_b_id INTEGER NOT NULL REFERENCES tracks(id),
            co_like_score FLOAT NOT NULL DEFAULT 0.0,
            sample_count INTEGER NOT NULL DEFAULT 0,
            last_updated TIMESTAMP DEFAULT NOW(),
            UNIQUE(track_a_id, track_b_id)
        )
    """))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_track_co_likes_b ON track_co_likes(track_b_id)"
    ))
    conn.commit()
    print("Migration complete.")
