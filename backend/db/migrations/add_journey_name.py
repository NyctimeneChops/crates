from dotenv import load_dotenv
load_dotenv()
import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE journeys ADD COLUMN IF NOT EXISTS "
        "name VARCHAR(255)"
    ))
    conn.commit()
    print("Migration complete.")
