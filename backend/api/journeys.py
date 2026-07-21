from __future__ import annotations

import random
import secrets
import threading
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from algorithm.next_track import NextTrackEngine
from api.dependencies import get_current_user, get_db, get_optional_user, get_sc_client
from db.models import ActionEnum, Journey, JourneyEvent
from db.models import Session as SessionModel
from db.models import Track, TrackRelated, User
from soundcloud.client import SoundCloudClient
from soundcloud.indexer import TrackIndexer

router = APIRouter(prefix="/journeys", tags=["journeys"])


# --- Pydantic schemas ---

class TrackOut(BaseModel):
    id: int
    soundcloud_id: int
    title: str
    artist: str
    artwork_url: str | None
    permalink_url: str | None
    duration_ms: int | None
    tags_raw: list[str] | None

    model_config = {"from_attributes": True}


class JourneyStartRequest(BaseModel):
    seed_track_soundcloud_id: str | int | None = None
    name: str | None = None


class JourneyStartResponse(BaseModel):
    journey_id: int
    session_id: int
    first_track: TrackOut


class NextTrackRequest(BaseModel):
    session_id: int
    track_id: int
    action: Literal["like", "skip", "dislike"]
    listen_duration_ms: int | None = None


class LogEventRequest(BaseModel):
    session_id: int
    track_id: int
    action: Literal["like", "skip", "dislike"]
    listen_duration_ms: int | None = None


class EventOut(BaseModel):
    position: int
    action: str
    track_title: str
    track_artist: str
    permalink_url: str | None
    timestamp: datetime


class JourneyDetailResponse(BaseModel):
    id: int
    started_at: datetime
    seed_track: TrackOut
    event_count: int
    fork_count: int
    is_public: bool
    name: str | None
    events: list[EventOut]
    tastemaker_username: str


class FeedJourneyOut(BaseModel):
    id: int
    tastemaker_username: str
    name: str | None
    seed_track: TrackOut
    event_count: int
    play_count: int
    fork_count: int
    started_at: datetime
    is_public: bool


class WitnessTrackOut(BaseModel):
    position: int
    action: str
    track: TrackOut


class MyJourneyOut(BaseModel):
    id: int
    started_at: datetime
    ended_at: datetime | None
    is_public: bool
    name: str | None
    seed_track: TrackOut
    event_count: int
    session_count: int
    fork_source_journey_id: int | None
    tastemaker_username: str


class MyJourneysResponse(BaseModel):
    journeys: list[MyJourneyOut]
    total: int
    page: int
    pages: int


class RenameJourneyRequest(BaseModel):
    name: str


class ForkRequest(BaseModel):
    fork_position: int | None = None


class ContinueJourneyResponse(BaseModel):
    journey_id: int
    session_id: int
    last_track: TrackOut


# --- Helpers ---

def _track_to_out(track: Track) -> TrackOut:
    return TrackOut(
        id=track.id,
        soundcloud_id=track.soundcloud_id,
        title=track.title,
        artist=track.artist,
        artwork_url=track.artwork_url,
        permalink_url=track.permalink_url,
        duration_ms=track.duration_ms,
        tags_raw=track.tags_raw,
    )


def _get_or_index_track(
    sc_id_or_url: str | int,
    db: Session,
    sc_client: SoundCloudClient | None,
) -> Track:
    is_url = isinstance(sc_id_or_url, str) and str(sc_id_or_url).startswith("http")

    if not is_url:
        sc_id = int(sc_id_or_url)
        track = db.query(Track).filter(Track.soundcloud_id == sc_id).first()
        if track:
            return track
        if sc_client is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="SoundCloud API not configured -- track not in local DB",
            )
        TrackIndexer(sc_client, db).index_single(str(sc_id))
        track = db.query(Track).filter(Track.soundcloud_id == sc_id).first()
    else:
        if sc_client is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="SoundCloud API not configured",
            )
        try:
            resolved = sc_client.resolve(str(sc_id_or_url))
            sc_id = resolved["id"]
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Could not resolve SoundCloud URL",
            )
        track = db.query(Track).filter(Track.soundcloud_id == sc_id).first()
        if not track:
            TrackIndexer(sc_client, db).index_single(str(sc_id_or_url))
            track = db.query(Track).filter(Track.soundcloud_id == sc_id).first()

    if not track:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Track not found or not streamable",
        )
    return track


def _get_or_create_guest_user(db: Session) -> User:
    guest = db.query(User).filter(User.email == "guest@crates.internal").first()
    if not guest:
        guest = User(
            email="guest@crates.internal",
            username="guest",
            password_hash=secrets.token_hex(32),
        )
        db.add(guest)
        db.flush()
    return guest


def _require_journey(journey_id: int, user_id: int, db: Session) -> Journey:
    journey = db.query(Journey).filter(
        Journey.id == journey_id,
        Journey.user_id == user_id,
    ).first()
    if not journey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journey not found")
    return journey


def _build_journey_detail(journey: Journey, db: Session) -> JourneyDetailResponse:
    seed_track = db.query(Track).filter(Track.id == journey.seed_track_id).first()
    if not seed_track:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Seed track missing",
        )

    events = (
        db.query(JourneyEvent)
        .options(joinedload(JourneyEvent.track))
        .filter(JourneyEvent.journey_id == journey.id)
        .order_by(JourneyEvent.position)
        .all()
    )

    event_outs = [
        EventOut(
            position=e.position,
            action=e.action.value,
            track_title=e.track.title if e.track else "",
            track_artist=e.track.artist if e.track else "",
            permalink_url=e.track.permalink_url if e.track else None,
            timestamp=e.timestamp,
        )
        for e in events
    ]

    journey_user = db.query(User).filter(User.id == journey.user_id).first()
    fork_count = db.query(Journey).filter(Journey.fork_source_journey_id == journey.id).count()

    return JourneyDetailResponse(
        id=journey.id,
        started_at=journey.started_at,
        seed_track=_track_to_out(seed_track),
        event_count=len(events),
        fork_count=fork_count,
        is_public=journey.is_public,
        name=journey.name,
        events=event_outs,
        tastemaker_username=journey_user.username if journey_user else "",
    )


def _spawn_catalog_expansion(soundcloud_id: int, sc_client: SoundCloudClient) -> None:
    def expand_catalog():
        try:
            from db.connection import SessionLocal
            expand_db = SessionLocal()
            indexer = TrackIndexer(sc_client, expand_db)
            source_track = expand_db.query(Track).filter(
                Track.soundcloud_id == soundcloud_id
            ).first()
            related = sc_client.get_related_tracks(soundcloud_id, limit=20)
            added = 0
            for sc_track in related:
                if indexer._upsert_track(sc_track):
                    added += 1
                if source_track:
                    related_track = expand_db.query(Track).filter(
                        Track.soundcloud_id == sc_track.id
                    ).first()
                    if related_track:
                        try:
                            rel = TrackRelated(
                                source_id=source_track.id,
                                related_id=related_track.id,
                            )
                            expand_db.add(rel)
                            expand_db.flush()
                        except Exception:
                            expand_db.rollback()
            expand_db.commit()
            expand_db.close()
            print(f"[reward_hack] liked {soundcloud_id}, added {added} related tracks")
        except Exception as e:
            print(f"[reward_hack] failed: {e}")

    threading.Thread(target=expand_catalog, daemon=True).start()


# --- Routes ---

@router.post("/start", response_model=JourneyStartResponse, status_code=status.HTTP_201_CREATED)
def start_journey(
    body: JourneyStartRequest = JourneyStartRequest(),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    sc_client: SoundCloudClient | None = Depends(get_sc_client),
):
    if current_user is None:
        current_user = _get_or_create_guest_user(db)

    track_count = db.query(Track).filter(Track.streamable == True).count()
    if track_count == 0:
        raise HTTPException(status_code=503, detail="No tracks available")
    random_offset = random.randint(0, track_count - 1)
    seed_track = db.query(Track).filter(
        Track.streamable == True
    ).offset(random_offset).limit(1).first()

    journey_number = db.query(Journey).filter(Journey.user_id == current_user.id).count() + 1
    now = datetime.now(timezone.utc)
    day = now.day
    suffix = "th" if 11 <= day <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    date_str = now.strftime(f"%B {day}{suffix}")
    default_name = f"Journey {journey_number}, {date_str}"

    resolved_name = f"Journey {journey_number}, {body.name}" if body.name else default_name

    journey = Journey(
        user_id=current_user.id,
        seed_track_id=seed_track.id,
        name=resolved_name,
    )
    db.add(journey)
    db.flush()

    session = SessionModel(user_id=current_user.id, journey_id=journey.id)
    db.add(session)
    db.commit()
    db.refresh(journey)
    db.refresh(session)

    first_track = NextTrackEngine(db, sc_client).get_next_track(
        current_user.id, journey.id, session.id
    )
    return JourneyStartResponse(
        journey_id=journey.id,
        session_id=session.id,
        first_track=_track_to_out(first_track),
    )


@router.get("/public/{journey_id}", response_model=JourneyDetailResponse)
def get_public_journey(journey_id: int, db: Session = Depends(get_db)):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()
    if not journey or not journey.is_public:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journey not found")
    return _build_journey_detail(journey, db)


@router.get("/public/{journey_id}/tracks", response_model=list[WitnessTrackOut])
def get_public_journey_tracks(journey_id: int, db: Session = Depends(get_db)):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()
    if not journey or not journey.is_public:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journey not found")

    journey.play_count = (journey.play_count or 0) + 1
    db.commit()

    events = (
        db.query(JourneyEvent)
        .options(joinedload(JourneyEvent.track))
        .filter(JourneyEvent.journey_id == journey_id)
        .order_by(JourneyEvent.position)
        .all()
    )

    return [
        WitnessTrackOut(
            position=e.position,
            action=e.action.value,
            track=_track_to_out(e.track),
        )
        for e in events
        if e.track
    ]


@router.get("/mine", response_model=MyJourneysResponse)
def get_my_journeys(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=20),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    import math
    total = db.query(Journey).filter(Journey.user_id == current_user.id).count()
    offset = (page - 1) * limit

    latest_session = db.query(
        SessionModel.journey_id,
        func.max(SessionModel.started_at).label("last_active"),
    ).group_by(SessionModel.journey_id).subquery()

    journeys = (
        db.query(Journey)
        .outerjoin(latest_session, Journey.id == latest_session.c.journey_id)
        .filter(Journey.user_id == current_user.id)
        .order_by(
            func.coalesce(latest_session.c.last_active, Journey.started_at).desc()
        )
        .offset(offset)
        .limit(limit)
        .all()
    )

    result = []
    for j in journeys:
        seed_track = db.query(Track).filter(Track.id == j.seed_track_id).first()
        if not seed_track:
            continue
        event_count = (
            db.query(JourneyEvent)
            .filter(JourneyEvent.journey_id == j.id)
            .count()
        )
        session_count = (
            db.query(SessionModel)
            .filter(SessionModel.journey_id == j.id)
            .count()
        )
        result.append(MyJourneyOut(
            id=j.id,
            started_at=j.started_at,
            ended_at=j.ended_at,
            is_public=j.is_public,
            name=j.name,
            seed_track=_track_to_out(seed_track),
            event_count=event_count,
            session_count=session_count,
            fork_source_journey_id=j.fork_source_journey_id,
            tastemaker_username=current_user.username,
        ))
    return MyJourneysResponse(
        journeys=result,
        total=total,
        page=page,
        pages=max(1, math.ceil(total / limit)),
    )


@router.get("/feed", response_model=list[FeedJourneyOut])
def get_feed(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    fork_counts_sq = (
        db.query(
            Journey.fork_source_journey_id.label("journey_id"),
            func.count(Journey.id).label("cnt"),
        )
        .filter(Journey.fork_source_journey_id.isnot(None))
        .group_by(Journey.fork_source_journey_id)
        .subquery()
    )

    rows = (
        db.query(Journey, func.coalesce(fork_counts_sq.c.cnt, 0).label("fork_count"))
        .outerjoin(fork_counts_sq, Journey.id == fork_counts_sq.c.journey_id)
        .filter(Journey.is_public.is_(True))
        .order_by(func.coalesce(fork_counts_sq.c.cnt, 0).desc(), Journey.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    result = []
    for journey, fork_count in rows:
        seed_track = db.query(Track).filter(Track.id == journey.seed_track_id).first()
        if not seed_track:
            continue
        journey_user = db.query(User).filter(User.id == journey.user_id).first()
        event_count = db.query(JourneyEvent).filter(JourneyEvent.journey_id == journey.id).count()
        result.append(FeedJourneyOut(
            id=journey.id,
            tastemaker_username=journey_user.username if journey_user else "",
            name=journey.name,
            seed_track=_track_to_out(seed_track),
            event_count=event_count,
            play_count=journey.play_count or 0,
            fork_count=int(fork_count),
            started_at=journey.started_at,
            is_public=journey.is_public,
        ))
    return result


@router.get("/feed/{journey_id}", response_model=JourneyDetailResponse)
def get_feed_journey(journey_id: int, db: Session = Depends(get_db)):
    journey = db.query(Journey).filter(
        Journey.id == journey_id,
        Journey.is_public.is_(True),
    ).first()
    if not journey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journey not found")
    return _build_journey_detail(journey, db)


@router.get("/{journey_id}/tracks", response_model=list[WitnessTrackOut])
def get_journey_tracks(
    journey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    journey = db.query(Journey).filter(
        Journey.id == journey_id,
        Journey.user_id == current_user.id,
    ).first()
    if not journey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journey not found")

    events = (
        db.query(JourneyEvent)
        .options(joinedload(JourneyEvent.track))
        .filter(JourneyEvent.journey_id == journey_id)
        .order_by(JourneyEvent.position)
        .all()
    )

    return [
        WitnessTrackOut(
            position=e.position,
            action=e.action.value,
            track=_track_to_out(e.track),
        )
        for e in events
        if e.track
    ]


@router.get("/{journey_id}/tracklist", response_model=list[WitnessTrackOut])
def get_journey_tracklist(
    journey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_journey(journey_id, current_user.id, db)
    events = (
        db.query(JourneyEvent)
        .options(joinedload(JourneyEvent.track))
        .filter(JourneyEvent.journey_id == journey_id)
        .order_by(JourneyEvent.position)
        .all()
    )
    return [
        WitnessTrackOut(
            position=e.position,
            action=e.action.value,
            track=_track_to_out(e.track),
        )
        for e in events
        if e.track
    ]


@router.patch("/{journey_id}/name")
def rename_journey(
    journey_id: int,
    body: RenameJourneyRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    journey = _require_journey(journey_id, current_user.id, db)
    journey.name = body.name
    db.commit()
    return {"ok": True, "name": body.name}


@router.delete("/{journey_id}")
def delete_journey(
    journey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    journey = _require_journey(journey_id, current_user.id, db)
    db.query(JourneyEvent).filter(JourneyEvent.journey_id == journey_id).delete()
    db.query(SessionModel).filter(SessionModel.journey_id == journey_id).delete()
    db.delete(journey)
    db.commit()
    return {"ok": True}


@router.get("/{journey_id}", response_model=JourneyDetailResponse)
def get_journey(
    journey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _build_journey_detail(_require_journey(journey_id, current_user.id, db), db)


@router.post("/{journey_id}/event")
def log_event(
    journey_id: int,
    body: LogEventRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    sc_client: SoundCloudClient | None = Depends(get_sc_client),
):
    _require_journey(journey_id, current_user.id, db)

    existing_event = db.query(JourneyEvent).filter(
        JourneyEvent.journey_id == journey_id,
        JourneyEvent.track_id == body.track_id,
    ).first()
    if existing_event:
        return {"ok": True}

    last_event = (
        db.query(JourneyEvent)
        .filter(JourneyEvent.journey_id == journey_id)
        .order_by(JourneyEvent.position.desc())
        .first()
    )
    next_position = (last_event.position + 1) if last_event else 0

    engine = NextTrackEngine(db, None)
    engine.log_event(
        journey_id=journey_id,
        track_id=body.track_id,
        position=next_position,
        action=body.action,
        listen_duration_ms=body.listen_duration_ms,
    )
    db.commit()

    if body.action == "like" and sc_client is not None:
        track = db.query(Track).filter(Track.id == body.track_id).first()
        if track:
            _spawn_catalog_expansion(track.soundcloud_id, sc_client)

    return {"ok": True}


@router.post("/{journey_id}/next", response_model=TrackOut)
def next_track(
    journey_id: int,
    body: NextTrackRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
    sc_client: SoundCloudClient | None = Depends(get_sc_client),
):
    if current_user is None:
        current_user = _get_or_create_guest_user(db)
    _require_journey(journey_id, current_user.id, db)

    existing_event = db.query(JourneyEvent).filter(
        JourneyEvent.journey_id == journey_id,
        JourneyEvent.track_id == body.track_id,
    ).first()

    engine = NextTrackEngine(db, sc_client)

    if not existing_event:
        last_event = (
            db.query(JourneyEvent)
            .filter(JourneyEvent.journey_id == journey_id)
            .order_by(JourneyEvent.position.desc())
            .first()
        )
        next_position = (last_event.position + 1) if last_event else 0
        engine.log_event(
            journey_id=journey_id,
            track_id=body.track_id,
            position=next_position,
            action=body.action,
            listen_duration_ms=body.listen_duration_ms,
        )

        if body.action == "like" and sc_client is not None:
            track = db.query(Track).filter(Track.id == body.track_id).first()
            if track:
                _spawn_catalog_expansion(track.soundcloud_id, sc_client)

    return _track_to_out(
        engine.get_next_track(current_user.id, journey_id, body.session_id)
    )


@router.post("/{journey_id}/end")
def end_journey(
    journey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journey not found")
    if journey.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your journey")
    now = datetime.now(timezone.utc)
    journey.ended_at = now

    open_session = (
        db.query(SessionModel)
        .filter(
            SessionModel.journey_id == journey_id,
            SessionModel.ended_at.is_(None),
        )
        .order_by(SessionModel.started_at.desc())
        .first()
    )
    if open_session:
        open_session.ended_at = now

    db.commit()
    return {"status": "ended", "journey_id": journey_id}


@router.post("/{journey_id}/publish")
def publish_journey(
    journey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    journey = db.query(Journey).filter(Journey.id == journey_id).first()
    if not journey:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journey not found")
    if journey.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your journey")
    journey.is_public = True
    db.commit()
    return {"public_url": f"/journeys/public/{journey_id}"}


@router.post("/{journey_id}/fork", response_model=JourneyStartResponse, status_code=status.HTTP_201_CREATED)
def fork_journey(
    journey_id: int,
    body: ForkRequest = ForkRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    sc_client: SoundCloudClient | None = Depends(get_sc_client),
):
    source = db.query(Journey).filter(Journey.id == journey_id).first()
    if not source:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Journey not found")

    if source.user_id != current_user.id and not source.is_public:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="This journey is private")

    events_query = db.query(JourneyEvent).filter(JourneyEvent.journey_id == source.id)
    if body.fork_position is not None:
        events_query = events_query.filter(JourneyEvent.position <= body.fork_position)
    source_events = events_query.order_by(JourneyEvent.position).all()

    _ACTION_WEIGHTS = {
        ActionEnum.like: 1.0,
        ActionEnum.skip: -0.2,
        ActionEnum.dislike: -3.0,
    }

    fork_seed_weights: dict[str, float] = {}
    for event in source_events:
        track = db.query(Track).filter(Track.id == event.track_id).first()
        if not track or not track.tags_raw:
            continue
        w = _ACTION_WEIGHTS.get(event.action, 0.0)
        for tag in track.tags_raw:
            fork_seed_weights[tag] = fork_seed_weights.get(tag, 0.0) + w

    new_journey = Journey(
        user_id=current_user.id,
        seed_track_id=source.seed_track_id,
        fork_source_journey_id=source.id,
        fork_seed_weights=fork_seed_weights,
    )
    db.add(new_journey)
    db.flush()

    session = SessionModel(user_id=current_user.id, journey_id=new_journey.id)
    db.add(session)
    db.commit()
    db.refresh(new_journey)
    db.refresh(session)

    first_track = NextTrackEngine(db, sc_client).get_next_track(
        current_user.id, new_journey.id, session.id
    )
    return JourneyStartResponse(
        journey_id=new_journey.id,
        session_id=session.id,
        first_track=_track_to_out(first_track),
    )


@router.post("/{journey_id}/continue", response_model=JourneyStartResponse)
def continue_journey(
    journey_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    sc_client: SoundCloudClient | None = Depends(get_sc_client),
):
    journey = _require_journey(journey_id, current_user.id, db)

    session = SessionModel(user_id=current_user.id, journey_id=journey_id)
    db.add(session)
    db.flush()

    if journey.ended_at is not None:
        journey.ended_at = None

    db.commit()
    db.refresh(session)

    first_track = NextTrackEngine(db, sc_client).get_next_track(
        current_user.id, journey_id, session.id
    )
    return JourneyStartResponse(
        journey_id=journey_id,
        session_id=session.id,
        first_track=_track_to_out(first_track),
    )