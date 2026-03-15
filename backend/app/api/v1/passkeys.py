"""
Passkey (WebAuthn) routes.

Registration (authenticated user):
  POST /auth/me/passkeys/register/begin     → options + challenge_token
  POST /auth/me/passkeys/register/complete  → PasskeyOut

Authentication (public):
  POST /auth/passkeys/authenticate/begin    → options + challenge_token
  POST /auth/passkeys/authenticate/complete → Token

Management (authenticated):
  GET    /auth/me/passkeys      → list[PasskeyOut]
  DELETE /auth/me/passkeys/{id} → 204
"""
import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    verify_authentication_response,
    verify_registration_response,
    options_to_json,
)
from webauthn.helpers import bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    ResidentKeyRequirement,
    UserVerificationRequirement,
    PublicKeyCredentialDescriptor,
)

from app.config import settings
from app.core.security import (
    create_access_token,
    create_webauthn_challenge_token,
    get_current_user,
    verify_webauthn_challenge_token,
)
from app.db.database import get_db
from app.models.passkey import Passkey
from app.models.user import User
from app.schemas.auth import Token
from app.schemas.passkey import (
    PasskeyAuthBeginResponse,
    PasskeyAuthCompleteRequest,
    PasskeyOut,
    PasskeyRegisterBeginResponse,
    PasskeyRegisterCompleteRequest,
)

router = APIRouter()

RP_ID = settings.WEBAUTHN_RP_ID
RP_NAME = settings.WEBAUTHN_RP_NAME
ORIGIN = settings.WEBAUTHN_ORIGIN


# ── Registration ──────────────────────────────────────────────────────────────

@router.post("/me/passkeys/register/begin", response_model=PasskeyRegisterBeginResponse)
async def passkey_register_begin(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Collect existing credential IDs for this user to avoid re-registering
    result = await db.execute(select(Passkey).where(Passkey.user_id == current_user.id))
    existing = result.scalars().all()
    exclude = [
        PublicKeyCredentialDescriptor(id=p.credential_id) for p in existing
    ]

    opts = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=str(current_user.id).encode(),
        user_name=current_user.username,
        user_display_name=current_user.username,
        exclude_credentials=exclude,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
    )

    challenge_b64 = bytes_to_base64url(opts.challenge)
    challenge_token = create_webauthn_challenge_token(challenge_b64, str(current_user.id))
    options_dict = json.loads(options_to_json(opts))

    return PasskeyRegisterBeginResponse(options=options_dict, challenge_token=challenge_token)


@router.post("/me/passkeys/register/complete", response_model=PasskeyOut, status_code=201)
async def passkey_register_complete(
    body: PasskeyRegisterCompleteRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    challenge_b64, token_user_id = verify_webauthn_challenge_token(body.challenge_token)
    if not challenge_b64 or token_user_id != str(current_user.id):
        raise HTTPException(status_code=400, detail="Invalid or expired challenge")

    from webauthn.helpers import base64url_to_bytes

    try:
        verification = verify_registration_response(
            credential=body.credential,
            expected_challenge=base64url_to_bytes(challenge_b64),
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Registration verification failed: {e}")

    passkey = Passkey(
        user_id=current_user.id,
        credential_id=verification.credential_id,
        public_key=verification.credential_public_key,
        sign_count=verification.sign_count,
        name=body.name,
    )
    db.add(passkey)
    await db.commit()
    await db.refresh(passkey)
    return passkey


# ── Authentication ─────────────────────────────────────────────────────────────

@router.post("/passkeys/authenticate/begin", response_model=PasskeyAuthBeginResponse)
async def passkey_auth_begin(db: AsyncSession = Depends(get_db)):
    opts = generate_authentication_options(
        rp_id=RP_ID,
        allow_credentials=[],  # discoverable — browser picks the right passkey
        user_verification=UserVerificationRequirement.PREFERRED,
    )

    challenge_b64 = bytes_to_base64url(opts.challenge)
    challenge_token = create_webauthn_challenge_token(challenge_b64)
    options_dict = json.loads(options_to_json(opts))

    return PasskeyAuthBeginResponse(options=options_dict, challenge_token=challenge_token)


@router.post("/passkeys/authenticate/complete", response_model=Token)
async def passkey_auth_complete(
    body: PasskeyAuthCompleteRequest,
    db: AsyncSession = Depends(get_db),
):
    challenge_b64, _ = verify_webauthn_challenge_token(body.challenge_token)
    if not challenge_b64:
        raise HTTPException(status_code=400, detail="Invalid or expired challenge")

    from webauthn.helpers import base64url_to_bytes

    # Look up the credential by ID
    raw_id = body.credential.get("rawId") or body.credential.get("id")
    if not raw_id:
        raise HTTPException(status_code=400, detail="Missing credential id")

    cred_id_bytes = base64url_to_bytes(raw_id)
    result = await db.execute(
        select(Passkey).where(Passkey.credential_id == cred_id_bytes)
    )
    passkey = result.scalar_one_or_none()
    if not passkey:
        raise HTTPException(status_code=401, detail="Unknown passkey")

    # Load user
    user_result = await db.execute(select(User).where(User.id == passkey.user_id))
    user = user_result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Account unavailable")

    try:
        verification = verify_authentication_response(
            credential=body.credential,
            expected_challenge=base64url_to_bytes(challenge_b64),
            expected_rp_id=RP_ID,
            expected_origin=ORIGIN,
            credential_public_key=passkey.public_key,
            credential_current_sign_count=passkey.sign_count,
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Authentication failed: {e}")

    # Update sign count
    passkey.sign_count = verification.new_sign_count
    await db.commit()

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token)


# ── Management ────────────────────────────────────────────────────────────────

@router.get("/me/passkeys", response_model=list[PasskeyOut])
async def list_passkeys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Passkey)
        .where(Passkey.user_id == current_user.id)
        .order_by(Passkey.created_at)
    )
    return result.scalars().all()


@router.delete("/me/passkeys/{passkey_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_passkey(
    passkey_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Passkey).where(
            Passkey.id == passkey_id,
            Passkey.user_id == current_user.id,
        )
    )
    passkey = result.scalar_one_or_none()
    if not passkey:
        raise HTTPException(404, "Passkey not found")
    await db.delete(passkey)
    await db.commit()
