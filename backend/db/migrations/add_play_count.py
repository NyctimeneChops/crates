from dotenv import load_dotenv
load_dotenv()
import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE journeys ADD COLUMN IF NOT EXISTS "
        "play_count INTEGER DEFAULT 0 NOT NULL"
    ))
    conn.commit()
    print("Migration complete.")
