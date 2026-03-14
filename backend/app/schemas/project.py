import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None

    @field_validator("name")
    @classmethod
    def name_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("Project name cannot be empty")
        return v


class ProjectUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}
