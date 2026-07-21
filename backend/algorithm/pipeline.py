from __future__ import annotations

import os
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

from db.connection import get_db  # noqa: E402 — must follow load_dotenv()
from algorithm.tag_normalizer import TagNormalizer
from algorithm.co_like_pipeline import CoLikePipeline
from algorithm.catalog_expander import CatalogExpander
from soundcloud.client import SoundCloudClient


def run_pipeline(min_interactions: int = 2) -> None:
    start = datetime.utcnow()
    print(f"[pipeline] start:   {start.isoformat()}")

    with get_db() as db:
        TagNormalizer(db).run(min_interactions=min_interactions)
        CoLikePipeline(db).run()

        client_id = os.environ.get("SOUNDCLOUD_CLIENT_ID", "")
        client_secret = os.environ.get("SOUNDCLOUD_CLIENT_SECRET", "")
        if client_id and client_secret:
            try:
                with SoundCloudClient() as sc:
                    CatalogExpander(db, sc).run()
            except Exception as e:
                print(f"[pipeline] catalog expansion failed: {e}")
        else:
            print("[pipeline] skipping catalog expansion (no SC credentials)")

    end = datetime.utcnow()
    elapsed = (end - start).total_seconds()
    print(f"[pipeline] end:     {end.isoformat()}")
    print(f"[pipeline] elapsed: {elapsed:.1f}s")


if __name__ == "__main__":
    run_pipeline()
