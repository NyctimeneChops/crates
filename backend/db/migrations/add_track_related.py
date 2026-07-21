from dotenv import load_dotenv
load_dotenv()
import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS track_related (
            id SERIAL PRIMARY KEY,
            source_id INTEGER NOT NULL REFERENCES tracks(id),
            related_id INTEGER NOT NULL REFERENCES tracks(id),
            created_at TIMESTAMP DEFAULT NOW(),
            UNIQUE(source_id, related_id)
        )
    """))
    conn.execute(text(
        "CREATE INDEX IF NOT EXISTS ix_track_related_source "
        "ON track_related(source_id)"
    ))
    conn.commit()
    print("Migration complete.")
