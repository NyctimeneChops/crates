from dotenv import load_dotenv
load_dotenv()
import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE tracks RENAME COLUMN spotify_features TO audio_features"
    ))
    conn.commit()
    print("Migration complete.")
