import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TwoFactorRequired(BaseModel):
    requires_2fa: bool = True
    temp_token: str


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    is_admin: bool = False


class UserUpdate(BaseModel):
    is_active: Optional[bool] = None
    is_admin: Optional[bool] = None


class UserOut(BaseModel):
    id: uuid.UUID
    username: str
    email: str
    is_admin: bool
    is_active: bool
    must_change_password: bool
    totp_enabled: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class TotpSetupResponse(BaseModel):
    secret: str
    otpauth_url: str


class TotpVerifyRequest(BaseModel):
    code: str


class TotpLoginRequest(BaseModel):
    temp_token: str
    code: str
