from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_optional_user, get_sc_client
from db.models import Track, User
from soundcloud.client import SoundCloudClient

router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.get("/search")
def search_tracks(
    q: str = Query(..., min_length=1),
    limit: int = Query(default=10, le=20),
    db: Session = Depends(get_db),
):
    if len(q.strip()) < 2:
        return []
    results = (
        db.query(Track)
        .filter(
            Track.streamable == True,
            (Track.title.ilike(f"%{q}%")) | (Track.artist.ilike(f"%{q}%")),
        )
        .order_by(Track.sc_likes_count.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "id": t.id,
            "soundcloud_id": t.soundcloud_id,
            "title": t.title,
            "artist": t.artist,
            "artwork_url": t.artwork_url,
            "permalink_url": t.permalink_url,
            "duration_ms": t.duration_ms,
            "tags_raw": t.tags_raw or [],
        }
        for t in results
    ]



@router.get("/{soundcloud_id}/stream")
def get_stream(
    soundcloud_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    sc_client: SoundCloudClient | None = Depends(get_sc_client),
):
    track = db.query(Track).filter(Track.soundcloud_id == soundcloud_id).first()
    if not track:
        raise HTTPException(status_code=404, detail="Track not found")
    if sc_client is None:
        raise HTTPException(status_code=503, detail="SoundCloud API not configured")

    stream_url = sc_client.get_stream_url(soundcloud_id)
    if not stream_url:
        raise HTTPException(status_code=404, detail="Stream not available")

    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            audio_response = client.get(stream_url)
            audio_response.raise_for_status()
            return Response(
                content=audio_response.content,
                media_type="audio/mpeg",
                headers={
                    "Cache-Control": "no-cache",
                    "Access-Control-Allow-Origin": "*",
                },
            )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch audio: {str(e)}")
