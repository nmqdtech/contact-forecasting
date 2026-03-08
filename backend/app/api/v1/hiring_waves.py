"""Hiring wave CRUD — POST/GET/DELETE /hiring-waves"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.hiring_wave import HiringWaveCreate, HiringWaveOut
from app.services import hiring_wave_service

router = APIRouter()


@router.get("", response_model=list[HiringWaveOut])
async def list_all_hiring_waves(db: AsyncSession = Depends(get_db)):
    waves = await hiring_wave_service.list_all_waves(db)
    return [HiringWaveOut.model_validate(w) for w in waves]


@router.get("/{channel}", response_model=list[HiringWaveOut])
async def list_channel_hiring_waves(channel: str, db: AsyncSession = Depends(get_db)):
    waves = await hiring_wave_service.list_waves(db, channel)
    return [HiringWaveOut.model_validate(w) for w in waves]


@router.post("", response_model=HiringWaveOut, status_code=status.HTTP_201_CREATED)
async def create_hiring_wave(body: HiringWaveCreate, db: AsyncSession = Depends(get_db)):
    wave = await hiring_wave_service.create_wave(
        db=db,
        channel=body.channel,
        start_date=body.start_date,
        end_date=body.end_date,
        junior_count=body.junior_count,
        total_agents=body.total_agents,
        label=body.label,
    )
    return HiringWaveOut.model_validate(wave)


@router.delete("/{wave_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_hiring_wave(wave_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    deleted = await hiring_wave_service.delete_wave(db, wave_id)
    if not deleted:
        raise HTTPException(404, "Hiring wave not found")
