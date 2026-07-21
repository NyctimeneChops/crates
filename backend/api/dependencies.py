from __future__ import annotations
import os
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from db.connection import SessionLocal
from db.models import User
from soundcloud.client import SoundCloudClient

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

_sc_client_instance: SoundCloudClient | None = None

def get_sc_client() -> SoundCloudClient | None:
    global _sc_client_instance
    client_id = os.environ.get("SOUNDCLOUD_CLIENT_ID", "")
    client_secret = os.environ.get("SOUNDCLOUD_CLIENT_SECRET", "")
    if not client_id or not client_secret:
        return None
    if _sc_client_instance is None:
        try:
            _sc_client_instance = SoundCloudClient()
        except Exception:
            return None
    return _sc_client_instance

def get_optional_user(
    token: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
) -> User | None:
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            os.environ["JWT_SECRET_KEY"],
            algorithms=[os.environ.get("JWT_ALGORITHM", "HS256")],
        )
        user_id = payload.get("sub")
        if not user_id:
            return None
        return db.query(User).filter(User.id == int(user_id)).first()
    except Exception:
        return None


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            os.environ["JWT_SECRET_KEY"],
            algorithms=[os.environ.get("JWT_ALGORITHM", "HS256")],
        )
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except (JWTError, ValueError):
        raise credentials_exception
    try:
        uid = int(user_id)
    except ValueError:
        raise credentials_exception
    user = db.query(User).filter(User.id == uid).first()
    if user is None:
        raise credentials_exception
    return user