# backend/scratch/

One-off, throwaway scripts live here: ad-hoc debugging queries, quick data checks,
one-time migrations. Nothing in this directory is meant to be part of the application.

## This directory is gitignored

Everything under `backend/scratch/` is ignored by git **except this README**
(see the `!backend/scratch/README.md` negation in the repo `.gitignore`).

That means: **your scratch scripts are never committed.** Don't rely on them being
in version control, and don't put anything here that needs to be tracked. If a script
turns out to be worth keeping (it encodes real policy, it's a reusable tool), move it
out of `scratch/` into `backend/` and commit it deliberately.

## Never hardcode a connection string

The credential-exposure incident that motivated this directory happened because
throwaway scripts pasted a live database URL inline instead of reading it from the
environment. Do not do that again.

**Any script that needs database access MUST read the URL from the environment via
the shared helper** — never paste a `DATABASE_URL`, password, host, or token into a
file here.

## Starter template (copy-paste this)

Scripts in `scratch/` sit two directories below `backend/`, so they add `backend/` to
`sys.path` before importing the `db` helper. This makes the script runnable from any
working directory (from `backend/`, from the project root, from anywhere):

```python
import os
import sys

# Put backend/ on the import path so `from db import ...` works from any cwd.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db import get_database_url
from sqlalchemy import create_engine, text

engine = create_engine(get_database_url())

with engine.connect() as conn:
    # your one-off query here
    count = conn.execute(text("SELECT COUNT(*) FROM tracks")).scalar()
    print(count)
```

`get_database_url()` reads `DATABASE_URL` from the environment (loaded from
`backend/.env` via python-dotenv) and raises a clear error if it is not set. The
connection string never appears in your code.
