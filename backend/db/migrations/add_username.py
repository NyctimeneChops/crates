from dotenv import load_dotenv
load_dotenv()
import os
from sqlalchemy import create_engine, text

engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    conn.execute(text(
        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
        "username VARCHAR(50)"
    ))
    conn.execute(text(
        "UPDATE users SET username = 'user_' || id::text "
        "WHERE username IS NULL"
    ))
    conn.execute(text(
        "ALTER TABLE users ALTER COLUMN username SET NOT NULL"
    ))
    conn.execute(text(
        "CREATE UNIQUE INDEX IF NOT EXISTS ix_users_username "
        "ON users(username)"
    ))
    conn.commit()
    print("Migration complete.")
