from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func


class Base(DeclarativeBase):
    pass


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"
    trial = "trial"


class ActionEnum(str, enum.Enum):
    like = "like"
    skip = "skip"
    dislike = "dislike"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    subscription_status = Column(
        Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.trial
    )
    stripe_customer_id = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now(), nullable=False)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    journeys = relationship("Journey", back_populates="user")
    sessions = relationship("Session", back_populates="user")
    taste_profile = relationship("ListenerTasteProfile", back_populates="user", uselist=False)


class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True)
    soundcloud_id = Column(BigInteger, unique=True, nullable=False, index=True)
    title = Column(String, nullable=False)
    artist = Column(String, nullable=False)
    artist_sc_id = Column(BigInteger, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    permalink_url = Column(String, nullable=True)
    artwork_url = Column(String, nullable=True)
    sc_play_count = Column(Integer, default=0)
    sc_likes_count = Column(Integer, default=0)
    tags_raw = Column(ARRAY(Text), nullable=True)
    tags_normalized = Column(JSONB, nullable=True)
    genre = Column(String, nullable=True)
    audio_features = Column(JSONB, nullable=True)
    genome_scores = Column(JSONB, nullable=True)
    streamable = Column(Boolean, default=True)
    access = Column(String(20), default="playable", nullable=False, server_default="playable")
    indexed_at = Column(DateTime, server_default=func.now(), nullable=False)
    last_verified_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("ix_tracks_tags_raw", "tags_raw", postgresql_using="gin"),
        Index("ix_tracks_tags_normalized", "tags_normalized", postgresql_using="gin"),
    )

    journey_seeds = relationship(
        "Journey", back_populates="seed_track", foreign_keys="Journey.seed_track_id"
    )
    journey_events = relationship("JourneyEvent", back_populates="track")
    tag_weights = relationship("TagWeight", back_populates="track")


class Journey(Base):
    __tablename__ = "journeys"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    seed_track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False)
    started_at = Column(DateTime, server_default=func.now(), nullable=False)
    ended_at = Column(DateTime, nullable=True)
    is_public = Column(Boolean, default=False, nullable=False)
    name = Column(String(255), nullable=True)
    play_count = Column(Integer, default=0, nullable=False, server_default="0")
    fork_source_journey_id = Column(Integer, ForeignKey("journeys.id"), nullable=True)
    fork_seed_weights = Column(JSONB, nullable=True)

    user = relationship("User", back_populates="journeys")
    seed_track = relationship("Track", back_populates="journey_seeds", foreign_keys=[seed_track_id])
    events = relationship("JourneyEvent", back_populates="journey")
    sessions = relationship("Session", back_populates="journey")
    fork_source = relationship("Journey", remote_side="Journey.id")


class JourneyEvent(Base):
    __tablename__ = "journey_events"

    id = Column(Integer, primary_key=True)
    journey_id = Column(Integer, ForeignKey("journeys.id"), nullable=False)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False)
    position = Column(Integer, nullable=False)
    action = Column(Enum(ActionEnum), nullable=False)
    listen_duration_ms = Column(Integer, nullable=True)
    timestamp = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_journey_events_journey_action", "journey_id", "action"),
    )

    journey = relationship("Journey", back_populates="events")
    track = relationship("Track", back_populates="journey_events")


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    journey_id = Column(Integer, ForeignKey("journeys.id"), nullable=False)
    started_at = Column(DateTime, server_default=func.now(), nullable=False)
    ended_at = Column(DateTime, nullable=True)
    track_count = Column(Integer, default=0)

    user = relationship("User", back_populates="sessions")
    journey = relationship("Journey", back_populates="sessions")


class TagWeight(Base):
    __tablename__ = "tag_weights"

    id = Column(Integer, primary_key=True)
    track_id = Column(Integer, ForeignKey("tracks.id"), nullable=False)
    tag = Column(String, nullable=False)
    weight = Column(Float, default=1.0, nullable=False)
    sample_count = Column(Integer, default=0, nullable=False)
    last_updated = Column(DateTime, server_default=func.now(), nullable=False)

    __table_args__ = (
        UniqueConstraint("track_id", "tag", name="uq_tag_weights_track_tag"),
    )

    track = relationship("Track", back_populates="tag_weights")


class TrackCoLike(Base):
    __tablename__ = "track_co_likes"

    id            = Column(Integer, primary_key=True)
    track_a_id    = Column(Integer, ForeignKey("tracks.id"), nullable=False)
    track_b_id    = Column(Integer, ForeignKey("tracks.id"), nullable=False)
    co_like_score = Column(Float, default=0.0, nullable=False)
    sample_count  = Column(Integer, default=0, nullable=False)
    last_updated  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    track_a = relationship("Track", foreign_keys=[track_a_id])
    track_b = relationship("Track", foreign_keys=[track_b_id])

    __table_args__ = (
        Index("ix_track_co_likes_a_b", "track_a_id", "track_b_id", unique=True),
        Index("ix_track_co_likes_b", "track_b_id"),
    )


class TrackRelated(Base):
    __tablename__ = "track_related"

    id         = Column(Integer, primary_key=True)
    source_id  = Column(Integer, ForeignKey("tracks.id"), nullable=False)
    related_id = Column(Integer, ForeignKey("tracks.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    source  = relationship("Track", foreign_keys=[source_id])
    related = relationship("Track", foreign_keys=[related_id])

    __table_args__ = (
        Index("ix_track_related_source", "source_id"),
        Index("ix_track_related_pair", "source_id", "related_id", unique=True),
    )


class ListenerTasteProfile(Base):
    __tablename__ = "listener_taste_profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    tag_weights = Column(JSONB, nullable=True)
    genome_prefs = Column(JSONB, nullable=True)
    spotify_centroid = Column(JSONB, nullable=True)
    heard_track_ids = Column(ARRAY(Integer), nullable=True)
    disliked_track_ids = Column(ARRAY(Integer), nullable=True)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), nullable=False)

    user = relationship("User", back_populates="taste_profile")
