from __future__ import annotations

import os
import re
from datetime import datetime, timedelta, timezone

import bcrypt as _bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.dependencies import get_db
from db.models import ListenerTasteProfile, SubscriptionStatus, User

router = APIRouter(prefix="/auth", tags=["auth"])


def _hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt()).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


class RegisterRequest(BaseModel):
    email: str
    password: str
    username: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str


def _create_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=int(os.environ.get("JWT_EXPIRE_MINUTES", "30"))
    )
    return jwt.encode(
        {"sub": str(user_id), "exp": expire},
        os.environ["JWT_SECRET_KEY"],
        algorithm=os.environ.get("JWT_ALGORITHM", "HS256"),
    )


_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{3,30}$")


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if not _USERNAME_RE.match(body.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username must be 3–30 characters: letters, numbers, and underscores only",
        )

    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    user = User(
        email=body.email,
        username=body.username,
        password_hash=_hash_password(body.password),
        subscription_status=SubscriptionStatus.trial,
    )
    db.add(user)
    db.flush()

    db.add(
        ListenerTasteProfile(
            user_id=user.id,
            tag_weights={},
            heard_track_ids=[],
            disliked_track_ids=[],
        )
    )
    db.commit()
    db.refresh(user)

    return TokenResponse(
        access_token=_create_token(user.id),
        token_type="bearer",
        user_id=user.id,
        username=user.username,
    )


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not _verify_password(body.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return TokenResponse(
        access_token=_create_token(user.id),
        token_type="bearer",
        user_id=user.id,
        username=user.username,
    )
