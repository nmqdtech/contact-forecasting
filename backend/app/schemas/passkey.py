import uuid
from datetime import datetime

from pydantic import BaseModel


class PasskeyOut(BaseModel):
    id: uuid.UUID
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}


class PasskeyRegisterBeginResponse(BaseModel):
    options: dict
    challenge_token: str


class PasskeyRegisterCompleteRequest(BaseModel):
    credential: dict
    challenge_token: str
    name: str = "Passkey"


class PasskeyAuthBeginResponse(BaseModel):
    options: dict
    challenge_token: str


class PasskeyAuthCompleteRequest(BaseModel):
    credential: dict
    challenge_token: str
