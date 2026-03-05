"""
Authentication routes: login, current user, user management (admin only), TOTP 2FA.
"""
import uuid

import pyotp
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_2fa_temp_token,
    create_access_token,
    get_current_user,
    get_password_hash,
    require_admin,
    verify_2fa_temp_token,
    verify_password,
)
from app.db.database import get_db
from app.models.user import User
from app.schemas.auth import (
    ChangePasswordRequest,
    Token,
    TotpLoginRequest,
    TotpSetupResponse,
    TotpVerifyRequest,
    TwoFactorRequired,
    UserCreate,
    UserOut,
    UserUpdate,
)

router = APIRouter()


@router.post("/login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account disabled")

    if user.totp_enabled:
        temp_token = create_2fa_temp_token(str(user.id))
        return TwoFactorRequired(temp_token=temp_token)

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)


@router.post("/totp", response_model=Token)
async def totp_verify(
    body: TotpLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    user_id = verify_2fa_temp_token(body.temp_token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired 2FA token")

    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user or not user.is_active or not user.totp_enabled or not user.totp_secret:
        raise HTTPException(status_code=401, detail="Invalid 2FA state")

    totp = pyotp.TOTP(user.totp_secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(status_code=401, detail="Invalid authenticator code")

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    current_user.hashed_password = get_password_hash(body.new_password)
    current_user.must_change_password = False
    await db.commit()


@router.post("/me/totp/setup", response_model=TotpSetupResponse)
async def totp_setup(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    secret = pyotp.random_base32()
    current_user.totp_secret = secret
    current_user.totp_enabled = False  # not yet confirmed
    await db.commit()

    totp = pyotp.TOTP(secret)
    otpauth_url = totp.provisioning_uri(
        name=current_user.email,
        issuer_name="Contact Forecasting",
    )
    return TotpSetupResponse(secret=secret, otpauth_url=otpauth_url)


@router.post("/me/totp/enable", status_code=status.HTTP_204_NO_CONTENT)
async def totp_enable(
    body: TotpVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.totp_secret:
        raise HTTPException(status_code=400, detail="Run /me/totp/setup first")
    totp = pyotp.TOTP(current_user.totp_secret)
    if not totp.verify(body.code, valid_window=1):
        raise HTTPException(status_code=400, detail="Invalid authenticator code")
    current_user.totp_enabled = True
    await db.commit()


@router.post("/me/totp/disable", status_code=status.HTTP_204_NO_CONTENT)
async def totp_disable(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_user.totp_enabled = False
    current_user.totp_secret = None
    await db.commit()


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: UserCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Check uniqueness
    existing = await db.execute(
        select(User).where((User.username == body.username) | (User.email == body.email))
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Username or email already exists")

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=get_password_hash(body.password),
        is_admin=body.is_admin,
        created_by=admin.id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@router.get("/users", response_model=list[UserOut])
async def list_users(
    _: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.created_at))
    return result.scalars().all()


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    if user.id == admin.id:
        raise HTTPException(400, "Cannot modify your own admin status")

    if body.is_active is not None:
        user.is_active = body.is_active
    if body.is_admin is not None:
        user.is_admin = body.is_admin

    await db.commit()
    await db.refresh(user)
    return user
