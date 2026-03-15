"""
JWT authentication + bcrypt password hashing.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")


def create_2fa_temp_token(user_id: str) -> str:
    return create_access_token(
        {"sub": user_id, "scope": "2fa_pending"},
        expires_delta=timedelta(minutes=5),
    )


def create_webauthn_challenge_token(challenge_b64url: str, user_id: str | None = None) -> str:
    """Short-lived token (5 min) carrying a WebAuthn challenge for begin→complete round-trip."""
    data: dict = {"wac": challenge_b64url}
    if user_id:
        data["sub"] = user_id
    return create_access_token(data, expires_delta=timedelta(minutes=5))


def verify_webauthn_challenge_token(token: str) -> tuple[str | None, str | None]:
    """Returns (challenge_b64url, user_id_or_None). Returns (None, None) on failure."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        challenge = payload.get("wac")
        if not challenge:
            return None, None
        return challenge, payload.get("sub")
    except JWTError:
        return None, None


def verify_2fa_temp_token(token: str) -> str | None:
    """Returns user_id string if token is valid 2fa_pending scope, else None."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        if payload.get("scope") != "2fa_pending":
            return None
        return payload.get("sub")
    except JWTError:
        return None


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    from app.models.user import User

    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        user_id: str | None = payload.get("sub")
        if user_id is None or payload.get("scope") == "2fa_pending":
            raise credentials_exc
    except JWTError:
        raise credentials_exc

    import uuid
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise credentials_exc
    return user


async def require_admin(current_user=Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user
